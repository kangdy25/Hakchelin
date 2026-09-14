from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from meals.models import Menu
from wallet.models import PointTransaction

from .models import Reservation


class ReservationError(ValueError):
    pass


@transaction.atomic
def reserve_menu(*, user, menu_id: str, options: dict, submitted_total: int) -> Reservation:
    """
    메뉴 예약, 포인트 차감, 스냅샷 저장 및 원장 기록을 원자적으로 수행합니다.

    동시성 이슈를 방지하기 위해 Menu와 User 행에 비관적 락(select_for_update)을 획득한 후 잔여 정원, 마감 시한, 1인 1식 여부를 검증합니다.
    """
    # 대상 메뉴와 사용자 행에 동시성 락(Row Lock) 획득
    menu = Menu.objects.select_for_update().get(id=menu_id, is_active=True)
    user = get_user_model().objects.select_for_update().get(id=user.id)
    now = timezone.now()

    # 메뉴 옵션 도메인 규칙 검증 (메인 추가 0~1회, 밥 양 조절 0~2)
    main_count = int(options.get("main", 0))
    rice_amount = int(options.get("rice", 0))
    if main_count not in (0, 1) or rice_amount not in (0, 1, 2):
        raise ReservationError("올바르지 않은 메뉴 옵션입니다.")

    # 예약 가능 시한 검증
    if now >= menu.reservation_deadline:
        raise ReservationError("예약 마감 시간이 지났습니다.")

    # 잔여 수량(Capacity) 검증: 메뉴 락이 걸려있으므로 동시 요청 간 초과 예약 방어
    if Reservation.objects.filter(menu=menu, status=Reservation.Status.RESERVED).count() >= menu.capacity:
        raise ReservationError("예약 가능 수량이 모두 소진되었습니다.")

    # 동일 시간대 1인 1식 정책 검증 (DB UniqueConstraint 이전 애플리케이션 레벨 검증)
    if Reservation.objects.filter(
        user=user, meal_date=menu.meal_date, meal_time=menu.meal_time, status__in=[Reservation.Status.RESERVED, Reservation.Status.USED]
    ).exists():
        raise ReservationError("해당 식사 시간에는 이미 예약한 식권이 있습니다.")

    # 최종 결제 금액 산출 및 위변조 대조 (메뉴 기본가 + 보증금 + 메인 추가금)
    total = menu.price + menu.deposit_amount + (main_count * 1000)
    if submitted_total != total:
        raise ReservationError("결제 금액이 메뉴 가격과 일치하지 않습니다.")
    
    # 잔여 포인트 잔액 검증
    if user.current_point < total:
        raise ReservationError("포인트가 부족합니다.")

    # 사용자 포인트 차감 (필드 타겟 업데이트)
    user.current_point -= total
    user.save(update_fields=["current_point"])

    # 예약 엔티티 생성 및 확정 시점의 메뉴 정보 박제(Snapshot)
    reservation = Reservation.objects.create(
        user=user,
        menu=menu,
        options=options,
        total_price=total,
        meal_date=menu.meal_date,
        meal_time=menu.meal_time,
        deposit_amount=menu.deposit_amount,
        menu_snapshot={"title_ko": menu.title_ko, "title_en": menu.title_en, "type": menu.type, "price": menu.price},
    )

    # 지갑 내역(PointTransaction)에 차감 이력 영구 기록
    PointTransaction.objects.create(user=user, amount=-total, type=PointTransaction.Type.DEDUCT, description="메뉴 예약")
    return reservation


@transaction.atomic
def cancel_reservation(*, user, reservation_id) -> Reservation:
    """
    사용자가 본인의 예약을 직접 취소하고 조건부 환불을 진행합니다.

    마감 시간 이전에 취소 시 보증금 포함 전액 환불, 마감 시간 이후 취소 시 노쇼 방지를 위해 보증금을 공제하고 차액만 환불합니다.
    """
    # 취소 대상 예약 및 사용자 행 락 획득 (메뉴 마감 시한 대조를 위해 menu 조인)
    reservation = Reservation.objects.select_for_update().select_related("menu").get(id=reservation_id, user=user)
    user = get_user_model().objects.select_for_update().get(id=user.id)
    if reservation.status != Reservation.Status.RESERVED:
        raise ReservationError("취소할 수 있는 예약이 아닙니다.")

    # 위약금/환불액 계산 규칙: 마감 전이면 전액 환불, 마감 후면 (총 결제액 - 보증금) 환불
    refund = (
        reservation.total_price 
        if timezone.now() < reservation.menu.reservation_deadline 
        else max(reservation.total_price - reservation.deposit_amount, 0)
    )

    # 예약 상태 전이 및 취소 이력 필드 저장
    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_at = timezone.now()
    reservation.refunded_amount = refund
    reservation.save(update_fields=["status", "cancelled_at", "refunded_amount"])

    # 환불액 포인트 반환 및 내역 기록
    user.current_point += refund
    user.save(update_fields=["current_point"])
    PointTransaction.objects.create(user=user, amount=refund, type=PointTransaction.Type.REFUND, description="예약 취소 환불")
    return reservation


@transaction.atomic
def use_reservation(*, reservation_id) -> Reservation:
    """식당 현장에서 학생증/QR 태깅 시 식권을 사용 완료(USED) 상태로 전이합니다"""
    reservation = Reservation.objects.select_for_update().get(id=reservation_id)
    if reservation.status != Reservation.Status.RESERVED:
        raise ReservationError("사용 처리할 수 있는 예약이 아닙니다.")
    
    reservation.status = Reservation.Status.USED
    reservation.used_at = timezone.now()
    reservation.save(update_fields=["status", "used_at"])
    return reservation


@transaction.atomic
def admin_cancel_reservation(*, reservation_id) -> Reservation:
    """
    [관리자 전용] 식당 사정, 품절, 시스템 오류 등으로 예약을 강제 취소합니다.

    관리자 귀책 또는 특수 취소이므로 마감 시간과 무관하게 보증금을 포함한 전액을 100% 환불합니다.
    """
    reservation = Reservation.objects.select_for_update().get(id=reservation_id)
    user = get_user_model().objects.select_for_update().get(id=reservation.user_id)

    if reservation.status != Reservation.Status.RESERVED:
        raise ReservationError("취소 처리할 수 있는 예약이 아닙니다.")

    # 전액 100% 환불 처리
    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_at = timezone.now()
    reservation.refunded_amount = reservation.total_price
    reservation.save(update_fields=["status", "cancelled_at", "refunded_amount"])

    user.current_point += reservation.total_price
    user.save(update_fields=["current_point"])
    PointTransaction.objects.create(
        user=user,
        amount=reservation.total_price,
        type=PointTransaction.Type.REFUND,
        description="관리자 예약 취소 환불",
    )
    return reservation


@transaction.atomic
def process_no_shows(*, now=None) -> int:
    """
    배치(Batch/Cron) 스케줄러에 의해 주기적으로 실행되어 미방문 건을 일괄 정리합니다.

    식사 시작 시간으로부터 1시간이 지난 시점까지 미사용 상태인 건을 NO_SHOW로 상태 전이하고, 보증금을 공제한 나머지 금액만 부분 환불합니다.
    """
    now = now or timezone.now()

    # 오늘 날짜를 포함하여 과거 일자의 예약 중 아직 RESERVED 상태로 방치된 레코드 추출
    reservations = (
        Reservation.objects.select_for_update()
        .select_related("user")
        .filter(status=Reservation.Status.RESERVED, meal_date__lte=timezone.localdate(now))
    )

    processed = 0
    for reservation in reservations:
        # 식사 종료 기준 시각 = 식사 제공 시간 + 1시간 버퍼
        meal_ended_at = timezone.make_aware(
            datetime.combine(reservation.meal_date, reservation.meal_time),
            timezone.get_current_timezone(),
        ) + timedelta(hours=1)

        # 아직 배식 종료 시간(식사 시간 + 1시간)이 지나지 않은 당일 예약은 스킵
        if meal_ended_at > now:
            continue

        # 보증금을 몰수(패널티)하고 잔여 금액만 환불액으로 산정
        refund = max(reservation.total_price - reservation.deposit_amount, 0)
        user = get_user_model().objects.select_for_update().get(id=reservation.user_id)

        reservation.status = Reservation.Status.NO_SHOW
        reservation.cancelled_at = now
        reservation.refunded_amount = refund
        reservation.save(update_fields=["status", "cancelled_at", "refunded_amount"])

        # 차액 환불 반영 및 거래 이력 생성
        user.current_point += refund
        user.save(update_fields=["current_point"])
        PointTransaction.objects.create(
            user=user,
            amount=refund,
            type=PointTransaction.Type.REFUND,
            description="노쇼 처리 (예약금 제외 환불)",
        )
        processed += 1
    return processed
