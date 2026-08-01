from dataclasses import replace
from datetime import time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from chatbot.models import AiLog, ChatMessage, PromptTemplate
from meals.models import Menu
from migration_tools.services import (
    MigrationValidationError,
    SourceSnapshot,
    apply_snapshot,
    ensure_distinct_databases,
    validate_snapshot,
    verify_snapshot,
)
from payments.models import PointOrder
from reservations.models import Reservation
from wallet.models import PointTransaction


def make_snapshot() -> SourceSnapshot:
    now = timezone.now()
    user_id = uuid4()
    menu_id = "legacy-menu-1"
    return SourceSnapshot(
        users=[{
            "id": user_id,
            "email": "STUDENT@example.com",
            "role": "student",
            "student_id": "20260001",
            "name": "기존 사용자",
            "current_point": 7000,
            "created_at": now - timedelta(days=30),
        }],
        menus=[{
            "id": menu_id,
            "day_of_week": None,
            "type": "kr",
            "title_ko": "메뉴",
            "title_en": "Meal",
            "price": 4500,
            "meal_date": timezone.localdate() + timedelta(days=1),
            "meal_time": time(12),
            "capacity": 10,
            "reservation_deadline": now + timedelta(hours=12),
            "deposit_amount": 1000,
            "is_active": True,
            "created_at": now - timedelta(days=20),
        }],
        reservations=[{
            "id": uuid4(),
            "user_id": user_id,
            "menu_id": menu_id,
            "options": {"main": 1},
            "total_price": 6500,
            "status": "reserved",
            "meal_date": timezone.localdate() + timedelta(days=1),
            "meal_time": time(12),
            "menu_snapshot": {"title_ko": "메뉴"},
            "deposit_amount": 1000,
            "refunded_amount": 0,
            "enforces_meal_limit": True,
            "created_at": now - timedelta(days=1),
            "cancelled_at": None,
            "used_at": None,
        }],
        transactions=[{
            "id": uuid4(),
            "user_id": user_id,
            "amount": -6500,
            "type": "deduct",
            "description": None,
            "created_at": now - timedelta(days=1),
        }],
        point_orders=[{
            "id": uuid4(),
            "order_id": "POINT_LEGACY",
            "user_id": user_id,
            "amount": 5000,
            "point_amount": 5000,
            "status": "paid",
            "payment_key": "legacy-payment",
            "payment_provider": None,
            "paid_at": now - timedelta(days=2),
            "toss_response": None,
            "created_at": now - timedelta(days=2),
            "updated_at": now - timedelta(days=2),
        }],
        prompt_templates=[{
            "id": uuid4(),
            "service_name": "meal_helper_chatbot",
            "version": 1,
            "prompt_content": "도움말",
            "temperature": Decimal("0.20"),
            "is_active": True,
            "created_at": now - timedelta(days=3),
            "updated_at": now - timedelta(days=3),
        }],
        ai_logs=[{
            "id": uuid4(),
            "request_id": uuid4(),
            "user_id": user_id,
            "stage": "main_chat",
            "model": "gemini",
            "prompt_version": 1,
            "input_tokens": 10,
            "output_tokens": 20,
            "latency_ms": 50,
            "estimated_cost_usd": Decimal("0.00010000"),
            "status_code": 200,
            "error_message": None,
            "created_at": now - timedelta(hours=2),
        }],
        chat_messages=[{
            "id": uuid4(),
            "user_id": user_id,
            "conversation_id": uuid4(),
            "role": "user",
            "content": "오늘 메뉴?",
            "created_at": now - timedelta(hours=2),
        }],
    )


@pytest.mark.django_db(transaction=True)
def test_snapshot_is_idempotent_and_preserves_existing_django_password():
    snapshot = make_snapshot()
    apply_snapshot(snapshot)

    user = get_user_model().objects.get(id=snapshot.users[0]["id"])
    assert not user.has_usable_password()
    assert user.email == "student@example.com"
    user.set_password("new-django-password")
    user.save()

    changed_users = [{**snapshot.users[0], "name": "변경된 이름", "current_point": 8000}]
    apply_snapshot(replace(snapshot, users=changed_users))

    user.refresh_from_db()
    assert user.check_password("new-django-password")
    assert user.name == "변경된 이름"
    assert user.current_point == 8000
    assert Menu.objects.count() == 1
    assert Reservation.objects.count() == 1
    assert PointTransaction.objects.count() == 1
    assert PointOrder.objects.count() == 1
    assert PromptTemplate.objects.count() == 1
    assert AiLog.objects.count() == 1
    assert ChatMessage.objects.count() == 1
    assert verify_snapshot(replace(snapshot, users=changed_users))["ok"] is True


@pytest.mark.django_db(transaction=True)
def test_snapshot_dry_run_rolls_back_all_rows():
    apply_snapshot(make_snapshot(), dry_run=True)
    assert get_user_model().objects.count() == 0
    assert Menu.objects.count() == 0


def test_snapshot_rejects_orphan_foreign_keys():
    snapshot = make_snapshot()
    invalid = replace(snapshot, transactions=[{**snapshot.transactions[0], "user_id": uuid4()}])
    with pytest.raises(MigrationValidationError, match="transactions"):
        validate_snapshot(invalid)


def test_database_url_with_unescaped_reserved_character_is_rejected():
    with pytest.raises(MigrationValidationError, match="percent-encoding"):
        ensure_distinct_databases("postgresql://user:password@host:invalid/db", "default")


@pytest.mark.django_db(transaction=True)
def test_management_command_rolls_back_import_when_verification_fails(monkeypatch):
    snapshot = make_snapshot()
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://source:password@source.example.com:5432/source")
    monkeypatch.setattr(
        "migration_tools.management.commands.migrate_supabase_data.load_supabase_snapshot",
        lambda _url: snapshot,
    )
    monkeypatch.setattr(
        "migration_tools.management.commands.migrate_supabase_data.verify_snapshot",
        lambda _snapshot, _alias: {"ok": False},
    )

    with pytest.raises(CommandError, match="대조 검증"):
        call_command("migrate_supabase_data", database="default")

    assert get_user_model().objects.count() == 0
    assert Menu.objects.count() == 0


def test_verification_command_rejects_identical_source_and_target(monkeypatch):
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://source:password@source.example.com:5432/source")

    def reject_identical_database(_url, _alias):
        raise MigrationValidationError("같은 데이터베이스")

    monkeypatch.setattr(
        "migration_tools.management.commands.verify_supabase_migration.ensure_distinct_databases",
        reject_identical_database,
    )

    with pytest.raises(CommandError, match="같은 데이터베이스"):
        call_command("verify_supabase_migration", database="default")
