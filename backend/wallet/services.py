from django.contrib.auth import get_user_model
from django.db import transaction

from .models import PointTransaction


class WalletError(ValueError):
    pass


@transaction.atomic
def donate_points(*, user, amount: int) -> PointTransaction:
    """
    사용자의 포인트를 차감하여 기부를 처리하고 거래 이력을 생성합니다.

    동시성 문제를 방지하기 위해 비관적 락(select_for_update)과 DB 트랜잭션 환경에서 원자적으로 실행됩니다.
    """
    user = get_user_model().objects.select_for_update().get(id=user.id)
    if amount <= 0 or user.current_point < amount:
        raise WalletError("기부할 수 있는 포인트가 부족합니다.")
    user.current_point -= amount
    user.save(update_fields=["current_point"])
    return PointTransaction.objects.create(user=user, amount=-amount, type=PointTransaction.Type.DEDUCT, description="마음을 잇는 식탁 기부")
