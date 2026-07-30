from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from meals.models import Menu
from payments.services import confirm_paid_order, create_point_order
from reservations.services import cancel_reservation, reserve_menu
from wallet.models import PointTransaction


@pytest.mark.django_db(transaction=True)
def test_reservation_and_cancellation_update_points_and_ledger():
    user = User.objects.create_user("student@example.com", "password", student_id="20260001", name="학생", current_point=10000)
    menu = Menu.objects.create(title_ko="메뉴", title_en="Meal", type="kr", meal_date=timezone.localdate(), meal_time="12:00", reservation_deadline=timezone.now() + timedelta(hours=1))
    reservation = reserve_menu(user=user, menu_id=menu.id, options={"main": 1, "rice": 1}, submitted_total=6500)
    user.refresh_from_db()
    assert user.current_point == 3500
    cancel_reservation(user=user, reservation_id=reservation.id)
    user.refresh_from_db()
    assert user.current_point == 10000
    assert PointTransaction.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_payment_confirmation_is_idempotent():
    user = User.objects.create_user("student@example.com", "password", student_id="20260001", name="학생")
    order = create_point_order(user=user, amount=5000)
    confirm_paid_order(order_id=order.order_id, payment_key="payment-key", approved_amount=5000, toss_response={})
    confirm_paid_order(order_id=order.order_id, payment_key="payment-key", approved_amount=5000, toss_response={})
    user.refresh_from_db()
    assert user.current_point == 5000
    assert PointTransaction.objects.filter(type="charge").count() == 1
