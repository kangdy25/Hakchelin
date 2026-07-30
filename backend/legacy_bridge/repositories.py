from .models import LegacyMenu, LegacyPointTransaction, LegacyReservation, LegacyUser


def list_menus(*, active_only: bool, from_date: str | None):
    query = LegacyMenu.objects.order_by("meal_date", "meal_time")
    if active_only:
        query = query.filter(is_active=True)
    if from_date:
        query = query.filter(meal_date__gte=from_date)
    return query


def get_profile(user_id):
    return LegacyUser.objects.get(id=user_id)


def list_reservations(user_id):
    return LegacyReservation.objects.filter(user_id=user_id).order_by("-created_at")


def list_transactions(user_id):
    return LegacyPointTransaction.objects.filter(user_id=user_id).order_by("-created_at")
