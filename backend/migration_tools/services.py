from __future__ import annotations

import os
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import psycopg
from django.contrib.auth import get_user_model
from django.db import connections, transaction
from psycopg.rows import dict_row

from chatbot.models import AiLog, ChatMessage, PromptTemplate
from meals.models import Menu
from payments.models import PointOrder
from reservations.models import Reservation
from wallet.models import PointTransaction


class MigrationValidationError(RuntimeError):
    pass


SOURCE_QUERIES = {
    "users": """
        SELECT p.id, a.email, p.role, p.student_id, p.name, p.current_point,
               COALESCE(p.created_at, a.created_at) AS created_at
        FROM public.users p
        JOIN auth.users a ON a.id = p.id
        ORDER BY p.id
    """,
    "menus": """
        SELECT id, day_of_week, type, title_ko, title_en, price, meal_date,
               meal_time, capacity, reservation_deadline, deposit_amount,
               is_active, created_at
        FROM public.menus ORDER BY id
    """,
    "reservations": """
        SELECT id, user_id, menu_id, options, total_price, status, meal_date,
               meal_time, menu_snapshot, deposit_amount, refunded_amount,
               enforces_meal_limit, created_at, cancelled_at, used_at
        FROM public.reservations ORDER BY id
    """,
    "transactions": """
        SELECT id, user_id, amount, type, description, created_at
        FROM public.transactions ORDER BY id
    """,
    "point_orders": """
        SELECT id, order_id, user_id, amount, point_amount, status, payment_key,
               payment_provider, paid_at, toss_response, created_at, updated_at
        FROM public.point_orders ORDER BY id
    """,
    "prompt_templates": """
        SELECT id, service_name, version, prompt_content, temperature, is_active,
               created_at, updated_at
        FROM public.prompt_templates ORDER BY id
    """,
    "ai_logs": """
        SELECT id, request_id, user_id, stage, model, prompt_version, input_tokens,
               output_tokens, latency_ms, estimated_cost_usd, status_code,
               error_message, created_at
        FROM public.ai_logs ORDER BY id
    """,
    "chat_messages": """
        SELECT id, user_id, conversation_id, role, content, created_at
        FROM public.chat_messages ORDER BY id
    """,
}


@dataclass(frozen=True)
class SourceSnapshot:
    users: list[dict[str, Any]]
    menus: list[dict[str, Any]]
    reservations: list[dict[str, Any]]
    transactions: list[dict[str, Any]]
    point_orders: list[dict[str, Any]]
    prompt_templates: list[dict[str, Any]]
    ai_logs: list[dict[str, Any]]
    chat_messages: list[dict[str, Any]]

    def rows(self, name: str) -> list[dict[str, Any]]:
        return getattr(self, name)


def load_supabase_snapshot(database_url: str | None = None) -> SourceSnapshot:
    database_url = database_url or os.getenv("SUPABASE_DATABASE_URL")
    if not database_url:
        raise MigrationValidationError("SUPABASE_DATABASE_URL이 설정되지 않았습니다.")

    with psycopg.connect(database_url, row_factory=dict_row) as source:
        with source.transaction():
            source.execute("SET TRANSACTION READ ONLY")
            profile_orphans = source.execute(
                "SELECT count(*) AS count FROM public.users p LEFT JOIN auth.users a ON a.id = p.id WHERE a.id IS NULL"
            ).fetchone()["count"]
            auth_without_profiles = source.execute(
                "SELECT count(*) AS count FROM auth.users a LEFT JOIN public.users p ON p.id = a.id "
                "WHERE p.id IS NULL AND a.email IS NOT NULL"
            ).fetchone()["count"]
            missing_emails = source.execute(
                "SELECT count(*) AS count FROM public.users p JOIN auth.users a ON a.id = p.id WHERE a.email IS NULL"
            ).fetchone()["count"]
            if profile_orphans or auth_without_profiles or missing_emails:
                raise MigrationValidationError(
                    "사용자 원본 무결성 오류: "
                    f"프로필만 존재={profile_orphans}, 프로필 없는 이메일 계정={auth_without_profiles}, "
                    f"이메일 없는 프로필={missing_emails}"
                )
            data = {name: list(source.execute(query).fetchall()) for name, query in SOURCE_QUERIES.items()}

    snapshot = SourceSnapshot(**data)
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: SourceSnapshot) -> None:
    user_ids = {row["id"] for row in snapshot.users}
    menu_ids = {row["id"] for row in snapshot.menus}
    errors: list[str] = []

    emails = [str(row["email"]).strip().lower() for row in snapshot.users]
    student_ids = [row["student_id"] for row in snapshot.users]
    if len(emails) != len(set(emails)):
        errors.append("사용자 이메일이 중복됩니다.")
    if len(student_ids) != len(set(student_ids)):
        errors.append("학번이 중복됩니다.")
    if any((row["current_point"] or 0) < 0 for row in snapshot.users):
        errors.append("음수 포인트 사용자가 있습니다.")

    for table in ("reservations", "transactions", "point_orders", "chat_messages"):
        missing = {row["user_id"] for row in snapshot.rows(table)} - user_ids
        if missing:
            errors.append(f"{table}에 이관 대상 사용자가 아닌 외래키 {len(missing)}개가 있습니다.")
    missing_ai_users = {row["user_id"] for row in snapshot.ai_logs if row["user_id"] is not None} - user_ids
    if missing_ai_users:
        errors.append(f"ai_logs에 이관 대상 사용자가 아닌 외래키 {len(missing_ai_users)}개가 있습니다.")
    missing_menus = {row["menu_id"] for row in snapshot.reservations} - menu_ids
    if missing_menus:
        errors.append(f"reservations에 존재하지 않는 메뉴 외래키 {len(missing_menus)}개가 있습니다.")

    if errors:
        raise MigrationValidationError(" ".join(errors))


def _normalized_endpoint(database_url: str) -> tuple[str | None, int | None, str]:
    parsed = urlparse(database_url.replace("postgres://", "postgresql://", 1))
    return parsed.hostname, parsed.port or 5432, parsed.path.lstrip("/")


def ensure_distinct_databases(source_url: str, target_alias: str) -> None:
    target = connections[target_alias].settings_dict
    source_endpoint = _normalized_endpoint(source_url)
    target_endpoint = (target.get("HOST") or None, int(target.get("PORT") or 5432), str(target.get("NAME") or ""))
    if source_endpoint == target_endpoint:
        raise MigrationValidationError("원본 Supabase와 대상 데이터베이스가 같습니다. 이관을 중단합니다.")


@contextmanager
def migration_lock(database_alias: str):
    connection = connections[database_alias]
    if connection.vendor != "postgresql":
        yield
        return

    lock_id = 4_862_534_220
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [lock_id])
        if not cursor.fetchone()[0]:
            raise MigrationValidationError("다른 데이터 이관 작업이 이미 실행 중입니다.")
    yield


def _upsert_user(row: dict[str, Any], database_alias: str) -> None:
    User = get_user_model()
    manager = User.objects.using(database_alias)
    user = manager.filter(id=row["id"]).first()
    created = user is None
    if created:
        user = User(id=row["id"])
        user.set_unusable_password()
    user.email = str(row["email"]).strip().lower()
    user.role = row["role"] or User.Role.STUDENT
    user.student_id = row["student_id"]
    user.name = row["name"]
    user.current_point = row["current_point"] or 0
    user.is_active = True
    user.save(using=database_alias)
    if row.get("created_at"):
        manager.filter(id=user.id).update(created_at=row["created_at"])


def _upsert_rows(model, rows: list[dict[str, Any]], database_alias: str, date_fields: tuple[str, ...]) -> None:
    manager = model.objects.using(database_alias)
    for source_row in rows:
        row = dict(source_row)
        primary_key = row.pop("id")
        preserved_dates = {field: row.pop(field) for field in date_fields if field in row}
        manager.update_or_create(id=primary_key, defaults=row)
        if preserved_dates:
            manager.filter(id=primary_key).update(**preserved_dates)


def apply_snapshot(snapshot: SourceSnapshot, database_alias: str = "default", dry_run: bool = False) -> dict[str, int]:
    validate_snapshot(snapshot)
    counts = {name: len(snapshot.rows(name)) for name in SOURCE_QUERIES}

    with transaction.atomic(using=database_alias), migration_lock(database_alias):
        for row in snapshot.users:
            _upsert_user(row, database_alias)
        menu_rows = [{**row, "day_of_week": row.get("day_of_week") or ""} for row in snapshot.menus]
        transaction_rows = [{**row, "description": row.get("description") or ""} for row in snapshot.transactions]
        point_order_rows = [
            {
                **row,
                "payment_provider": row.get("payment_provider") or "toss",
                "toss_response": row.get("toss_response") or {},
            }
            for row in snapshot.point_orders
        ]
        ai_log_rows = [{**row, "error_message": row.get("error_message") or ""} for row in snapshot.ai_logs]

        _upsert_rows(Menu, menu_rows, database_alias, ("created_at",))
        _upsert_rows(Reservation, snapshot.reservations, database_alias, ("created_at",))
        _upsert_rows(PointTransaction, transaction_rows, database_alias, ("created_at",))
        _upsert_rows(PointOrder, point_order_rows, database_alias, ("created_at", "updated_at"))

        active_services = {row["service_name"] for row in snapshot.prompt_templates if row["is_active"]}
        if active_services:
            PromptTemplate.objects.using(database_alias).filter(service_name__in=active_services).update(is_active=False)
        _upsert_rows(PromptTemplate, snapshot.prompt_templates, database_alias, ("created_at", "updated_at"))
        _upsert_rows(AiLog, ai_log_rows, database_alias, ("created_at",))
        _upsert_rows(ChatMessage, snapshot.chat_messages, database_alias, ("created_at",))

        if dry_run:
            transaction.set_rollback(True, using=database_alias)

    return counts


MODEL_BY_SOURCE = {
    "users": get_user_model(),
    "menus": Menu,
    "reservations": Reservation,
    "transactions": PointTransaction,
    "point_orders": PointOrder,
    "prompt_templates": PromptTemplate,
    "ai_logs": AiLog,
    "chat_messages": ChatMessage,
}

EXPECTED_CONSTRAINTS = {
    "meals_menu": {"menu_active_date_idx"},
    "reservations_reservation": {"reservation_one_meal_per_user", "reservation_menu_status_idx"},
    "chatbot_prompttemplate": {"prompt_template_service_version", "prompt_template_one_active"},
    "chatbot_ailog": {"ai_log_user_stage_created_idx", "ai_log_created_idx"},
    "chatbot_chatmessage": {"chat_message_conversation_idx"},
}

EXPECTED_UNIQUE_COLUMNS = {
    "accounts_user": {("email",), ("student_id",)},
    "payments_pointorder": {("order_id",), ("payment_key",)},
}


def verify_snapshot(snapshot: SourceSnapshot, database_alias: str = "default") -> dict[str, Any]:
    report: dict[str, Any] = {"ok": True, "tables": {}, "aggregates": {}, "constraints": {}}
    for name, model in MODEL_BY_SOURCE.items():
        source_ids = {str(row["id"]) for row in snapshot.rows(name)}
        target_ids = {str(value) for value in model.objects.using(database_alias).values_list("id", flat=True)}
        missing = sorted(source_ids - target_ids)
        extra = sorted(target_ids - source_ids)
        table_ok = not missing and not extra
        report["tables"][name] = {
            "source_count": len(source_ids),
            "target_count": len(target_ids),
            "missing_ids": missing[:20],
            "extra_ids": extra[:20],
            "ok": table_ok,
        }
        report["ok"] = report["ok"] and table_ok

    source_points = {str(row["id"]): row["current_point"] or 0 for row in snapshot.users}
    target_points = {
        str(user_id): points
        for user_id, points in get_user_model().objects.using(database_alias).values_list("id", "current_point")
    }
    point_mismatches = sorted(user_id for user_id, points in source_points.items() if target_points.get(user_id) != points)
    reservation_statuses = Counter(row["status"] for row in snapshot.reservations)
    target_reservation_statuses = Counter(
        Reservation.objects.using(database_alias).values_list("status", flat=True)
    )
    order_statuses = Counter(row["status"] for row in snapshot.point_orders)
    target_order_statuses = Counter(PointOrder.objects.using(database_alias).values_list("status", flat=True))
    aggregates_ok = (
        not point_mismatches
        and reservation_statuses == target_reservation_statuses
        and order_statuses == target_order_statuses
    )
    report["aggregates"] = {
        "source_point_total": sum(source_points.values()),
        "target_point_total": sum(target_points.values()),
        "point_mismatch_user_ids": point_mismatches[:20],
        "reservation_statuses": {"source": dict(reservation_statuses), "target": dict(target_reservation_statuses)},
        "point_order_statuses": {"source": dict(order_statuses), "target": dict(target_order_statuses)},
        "ok": aggregates_ok,
    }
    report["ok"] = report["ok"] and aggregates_ok

    connection = connections[database_alias]
    with connection.cursor() as cursor:
        for table, expected in EXPECTED_CONSTRAINTS.items():
            constraints = connection.introspection.get_constraints(cursor, table)
            missing_names = sorted(expected - set(constraints))
            report["constraints"][table] = {"missing_names": missing_names, "ok": not missing_names}
            report["ok"] = report["ok"] and not missing_names
        for table, expected_columns in EXPECTED_UNIQUE_COLUMNS.items():
            constraints = connection.introspection.get_constraints(cursor, table)
            unique_columns = {tuple(details["columns"]) for details in constraints.values() if details["unique"]}
            missing_columns = sorted(expected_columns - unique_columns)
            item = report["constraints"].setdefault(table, {"ok": True})
            item["missing_unique_columns"] = missing_columns
            item["ok"] = item["ok"] and not missing_columns
            report["ok"] = report["ok"] and not missing_columns
    return report
