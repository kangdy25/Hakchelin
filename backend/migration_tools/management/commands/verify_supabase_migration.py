import json
import os

import psycopg
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connections

from migration_tools.services import (
    MigrationValidationError,
    ensure_distinct_databases,
    load_supabase_snapshot,
    verify_snapshot,
)


class Command(BaseCommand):
    help = "Supabase 원본과 Django 대상의 식별자·포인트·상태·제약 조건을 대조합니다."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="neon", help="Django 대상 DB alias (기본값: neon)")

    def handle(self, *args, **options):
        database_alias = options["database"]
        if database_alias not in connections:
            raise CommandError(f"Django DB alias '{database_alias}'가 설정되지 않았습니다.")
        try:
            source_url = os.getenv("SUPABASE_DATABASE_URL", "")
            ensure_distinct_databases(source_url, database_alias)
            snapshot = load_supabase_snapshot(source_url)
            report = verify_snapshot(snapshot, database_alias)
        except (MigrationValidationError, psycopg.Error, DatabaseError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        if not report["ok"]:
            raise CommandError("Supabase와 Django 데이터 대조 결과가 일치하지 않습니다.")
        self.stdout.write(self.style.SUCCESS("Supabase와 Django 데이터가 일치합니다."))
