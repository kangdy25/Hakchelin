from django.db import transaction
from django.utils import timezone

from meals.models import Menu
from wallet.models import PointTransaction

from .models import Reservation


class ReservationError(ValueError):
    pass


@transaction.atomic
def reserve_menu(*, user, menu_id: str, options: dict, submitted_total: int) -> Reservation:
    menu = Menu.objects.select_for_update().get(id=menu_id, is_active=True)
    user = type(user).objects.select_for_update().get(id=user.id)
    now = timezone.now()
    main_count = int(options.get("main", 0))
    rice_amount = int(options.get("rice", 0))
    if main_count not in (0, 1) or rice_amount not in (0, 1, 2):
        raise ReservationError("올바르지 않은 메뉴 옵션입니다.")
    if now >= menu.reservation_deadline:
        raise ReservationError("예약 마감 시간이 지났습니다.")
    if Reservation.objects.filter(menu=menu, status=Reservation.Status.RESERVED).count() >= menu.capacity:
        raise ReservationError("예약 가능 수량이 모두 소진되었습니다.")
    if Reservation.objects.filter(
        user=user, meal_date=menu.meal_date, meal_time=menu.meal_time, status__in=[Reservation.Status.RESERVED, Reservation.Status.USED]
    ).exists():
        raise ReservationError("해당 식사 시간에는 이미 예약한 식권이 있습니다.")
    total = menu.price + menu.deposit_amount + (main_count * 1000)
    if submitted_total != total:
        raise ReservationError("결제 금액이 메뉴 가격과 일치하지 않습니다.")
    if user.current_point < total:
        raise ReservationError("포인트가 부족합니다.")

    user.current_point -= total
    user.save(update_fields=["current_point"])
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
    PointTransaction.objects.create(user=user, amount=-total, type=PointTransaction.Type.DEDUCT, description="메뉴 예약")
    return reservation


@transaction.atomic
def cancel_reservation(*, user, reservation_id) -> Reservation:
    reservation = Reservation.objects.select_for_update().select_related("menu").get(id=reservation_id, user=user)
    user = type(user).objects.select_for_update().get(id=user.id)
    if reservation.status != Reservation.Status.RESERVED:
        raise ReservationError("취소할 수 있는 예약이 아닙니다.")
    refund = reservation.total_price if timezone.now() < reservation.menu.reservation_deadline else max(
        reservation.total_price - reservation.deposit_amount, 0
    )
    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_at = timezone.now()
    reservation.refunded_amount = refund
    reservation.save(update_fields=["status", "cancelled_at", "refunded_amount"])
    user.current_point += refund
    user.save(update_fields=["current_point"])
    PointTransaction.objects.create(user=user, amount=refund, type=PointTransaction.Type.REFUND, description="예약 취소 환불")
    return reservation
