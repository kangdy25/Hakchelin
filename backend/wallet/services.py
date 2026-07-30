from django.db import transaction

from .models import PointTransaction


class WalletError(ValueError):
    pass


@transaction.atomic
def donate_points(*, user, amount: int) -> PointTransaction:
    user = type(user).objects.select_for_update().get(id=user.id)
    if amount <= 0 or user.current_point < amount:
        raise WalletError("기부할 수 있는 포인트가 부족합니다.")
    user.current_point -= amount
    user.save(update_fields=["current_point"])
    return PointTransaction.objects.create(user=user, amount=-amount, type=PointTransaction.Type.DEDUCT, description="마음을 잇는 식탁 기부")
