import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from wallet.models import PointTransaction

from .models import PointOrder


class PaymentError(ValueError):
    pass


@transaction.atomic
def create_point_order(*, user, amount: int) -> PointOrder:
    """
    클라이언트 결제창 호출 전 서버 사이드 결제 사전 주문(PointOrder)을 생성합니다.

    충전 한도(1원 ~ 1,000,000원)를 검증하고 PG사에 전달할 고유 주문 식별자(order_id)를 발급합니다.
    """
    if amount <= 0 or amount > 1_000_000:
        raise PaymentError("충전 금액은 1원 이상 1,000,000원 이하여야 합니다.")
    # 외부 PG사에 전달할 유일한 주문 식별 번호 생성 (POINT_<hex>) 및 1:1 비율 포인트 산정
    return PointOrder.objects.create(
        user=user, 
        order_id=f"POINT_{uuid.uuid4().hex}", 
        amount=amount, 
        point_amount=amount
    )


@transaction.atomic
def confirm_paid_order(*, user, order_id: str, payment_key: str, approved_amount: int, toss_response: dict) -> PointOrder:
    """
    토스페이먼츠 승인 완료 후 주문 상태를 갱신하고 포인트를 원자적으로 적립합니다.

    주문 소유권, 멱등성(중복 승인), 결제 승인 금액 일치 여부, payment_key 중복 사용을 검증한 뒤,
    User 행과 PointOrder 행에 비관적 락을 획득하여 포인트 원장(PointTransaction)을 생성합니다.
    """
    # 대상 주문 행 락(Row Lock) 획득 및 사용자 조인
    order = PointOrder.objects.select_for_update().select_related("user").get(order_id=order_id)

    # 본인 확인: 타인의 주문을 가로채 승인 처리하는 것을 방지
    if order.user_id != user.id:
        raise PaymentError("본인의 충전 주문만 승인할 수 있습니다.")

    # 멱등성 보장: 네트워크 재시도나 중복 콜백 시 중복 지급 없이 기존 완료 주문 즉시 반환
    if order.status == PointOrder.Status.PAID:
        return order

    # 상태 및 금액 무결성 검증: 결제 대기 상태인지, 사전 주문 금액과 실제 승인 금액이 일치하는지 확인
    if order.status != PointOrder.Status.PENDING or order.amount != approved_amount:
        raise PaymentError("처리할 수 없는 충전 주문입니다.")

    # payment_key 재사용 방어: 다른 주문에서 이미 소비된 결제 키로 이중 승인을 시도하는 부정행위 차단
    if PointOrder.objects.exclude(id=order.id).filter(payment_key=payment_key).exists():
        raise PaymentError("이미 사용된 결제 키입니다.")

    # 주문 엔티티 완료 처리 및 PG 스냅샷 박제
    order.status = PointOrder.Status.PAID
    order.payment_key = payment_key
    order.paid_at = timezone.now()
    order.toss_response = toss_response
    order.save(update_fields=["status", "payment_key", "paid_at", "toss_response", "updated_at"])

    # 사용자 행 락(Row Lock) 획득 후 포인트 적립
    user = get_user_model().objects.select_for_update().get(id=order.user_id)
    user.current_point += order.point_amount
    user.save(update_fields=["current_point"])

    # 지갑 내역에 충전 이력 생성 (회계 무결성 보장)
    PointTransaction.objects.create(
        user=user, 
        amount=order.point_amount, 
        type=PointTransaction.Type.CHARGE, 
        description="포인트 충전"
    )
    return order
