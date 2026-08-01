from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.utils import timezone

from accounts.models import User
from meals.models import Menu
from payments.services import confirm_paid_order, create_point_order
from reservations.models import Reservation
from reservations.services import ReservationError, reserve_menu
from wallet.models import PointTransaction

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL 행 잠금 전용 통합 테스트"),
]


def _run_concurrently(function, arguments):
    barrier = Barrier(len(arguments))

    def runner(argument):
        close_old_connections()
        barrier.wait()
        try:
            return function(argument)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=len(arguments)) as executor:
        return list(executor.map(runner, arguments))


def test_concurrent_reservations_do_not_exceed_capacity():
    users = [
        User.objects.create_user(
            f"student{index}@example.com",
            "password",
            student_id=f"2026000{index}",
            name=f"학생{index}",
            current_point=10_000,
        )
        for index in (1, 2)
    ]
    menu = Menu.objects.create(
        title_ko="한정 메뉴",
        title_en="Limited meal",
        type="kr",
        meal_date=timezone.localdate() + timedelta(days=1),
        meal_time="12:00",
        reservation_deadline=timezone.now() + timedelta(hours=12),
        capacity=1,
    )

    def attempt(user_id):
        user = User.objects.get(id=user_id)
        try:
            reserve_menu(user=user, menu_id=menu.id, options={"main": 0, "rice": 0}, submitted_total=5500)
            return "reserved"
        except ReservationError:
            return "rejected"

    results = _run_concurrently(attempt, [user.id for user in users])
    assert sorted(results) == ["rejected", "reserved"]
    assert Reservation.objects.filter(menu=menu, status=Reservation.Status.RESERVED).count() == 1
    assert sum(User.objects.filter(id__in=[user.id for user in users]).values_list("current_point", flat=True)) == 14_500


def test_concurrent_payment_confirmation_credits_points_once():
    user = User.objects.create_user("payer@example.com", "password", student_id="20269999", name="결제자")
    order = create_point_order(user=user, amount=5000)

    def confirm(_attempt):
        thread_user = User.objects.get(id=user.id)
        confirm_paid_order(
            user=thread_user,
            order_id=order.order_id,
            payment_key="same-payment-key",
            approved_amount=5000,
            toss_response={"status": "DONE"},
        )
        return "confirmed"

    assert _run_concurrently(confirm, [1, 2]) == ["confirmed", "confirmed"]
    user.refresh_from_db()
    assert user.current_point == 5000
    assert PointTransaction.objects.filter(user=user, type=PointTransaction.Type.CHARGE).count() == 1
