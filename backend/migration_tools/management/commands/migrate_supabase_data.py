import json
import os

import psycopg
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connections, transaction

from migration_tools.services import (
    MigrationValidationError,
    apply_snapshot,
    ensure_distinct_databases,
    load_supabase_snapshot,
    verify_snapshot,
)


class Command(BaseCommand):
    help = "Supabase 데이터를 Django 스키마가 적용된 Neon으로 멱등 이관합니다."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="neon", help="Django 대상 DB alias (기본값: neon)")
        parser.add_argument("--dry-run", action="store_true", help="전체 쓰기를 롤백해 이관 가능 여부만 확인")
        parser.add_argument("--skip-verify", action="store_true", help="실제 이관 후 자동 대조를 생략")

    def handle(self, *args, **options):
        database_alias = options["database"]
        source_url = os.getenv("SUPABASE_DATABASE_URL", "")
        if database_alias not in connections:
            raise CommandError(f"Django DB alias '{database_alias}'가 설정되지 않았습니다.")
        try:
            ensure_distinct_databases(source_url, database_alias)
            snapshot = load_supabase_snapshot(source_url)
            with transaction.atomic(using=database_alias):
                counts = apply_snapshot(snapshot, database_alias=database_alias, dry_run=options["dry_run"])
                result = {"dry_run": options["dry_run"], "migrated": counts}
                if not options["dry_run"] and not options["skip_verify"]:
                    result["verification"] = verify_snapshot(snapshot, database_alias)
                    if not result["verification"]["ok"]:
                        raise MigrationValidationError("이관 후 대조 검증에 실패했습니다.")
        except (MigrationValidationError, psycopg.Error, DatabaseError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        self.stdout.write(self.style.SUCCESS("Supabase 데이터 이관 작업을 완료했습니다."))
