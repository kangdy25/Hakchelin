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
    if amount <= 0 or amount > 1_000_000:
        raise PaymentError("충전 금액은 1원 이상 1,000,000원 이하여야 합니다.")
    return PointOrder.objects.create(user=user, order_id=f"POINT_{uuid.uuid4().hex}", amount=amount, point_amount=amount)


@transaction.atomic
def confirm_paid_order(*, user, order_id: str, payment_key: str, approved_amount: int, toss_response: dict) -> PointOrder:
    order = PointOrder.objects.select_for_update().select_related("user").get(order_id=order_id)
    if order.user_id != user.id:
        raise PaymentError("본인의 충전 주문만 승인할 수 있습니다.")
    if order.status == PointOrder.Status.PAID:
        return order
    if order.status != PointOrder.Status.PENDING or order.amount != approved_amount:
        raise PaymentError("처리할 수 없는 충전 주문입니다.")
    if PointOrder.objects.exclude(id=order.id).filter(payment_key=payment_key).exists():
        raise PaymentError("이미 사용된 결제 키입니다.")
    order.status = PointOrder.Status.PAID
    order.payment_key = payment_key
    order.paid_at = timezone.now()
    order.toss_response = toss_response
    order.save(update_fields=["status", "payment_key", "paid_at", "toss_response", "updated_at"])
    user = get_user_model().objects.select_for_update().get(id=order.user_id)
    user.current_point += order.point_amount
    user.save(update_fields=["current_point"])
    PointTransaction.objects.create(user=user, amount=order.point_amount, type=PointTransaction.Type.CHARGE, description="포인트 충전")
    return order
