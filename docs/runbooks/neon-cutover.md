# Neon 데이터 컷오버 런북

이 문서는 Supabase PostgreSQL 데이터를 Django 스키마가 적용된 Neon으로 옮기고, 원본·대상을 대조한 뒤 Django의 기본 DB 연결을 전환하는 절차다. 운영 컷오버 전에는 반드시 스테이징에서 같은 순서로 리허설한다.

## 1. 책임과 중단 기준

- 작업자: migration 실행, 대조 결과 보관, 애플리케이션 설정 전환
- 검토자: 원본 쓰기 중단 확인, 대조 결과 확인, 전환 승인
- 예상 점검 시간: 30분
- 즉시 중단 조건: 사용자 원본 무결성 오류, ETL 예외, 원본·대상 수량 불일치, 포인트 불일치, 예약·주문 상태 불일치, 필수 인덱스·제약 누락
- 중단 시 Neon을 운영 DB로 연결하지 않는다. Supabase는 변경 없이 복구 지점으로 유지한다.

이관 중에는 이중 기록하지 않는다. 검증 전에는 Supabase가 기준 원본이고, 검증과 연결 전환이 끝난 뒤에는 Neon이 유일한 기준 원본이다.

## 2. 사전 준비

`backend/.env`에 다음 두 값을 넣는다. 출력·채팅·문서·Git에 실제 연결 문자열을 남기지 않는다.

```dotenv
NEON_DATABASE_URL=postgresql://...neon.../...?sslmode=require
SUPABASE_DATABASE_URL=postgresql://...supabase.../postgres?sslmode=require
```

- `NEON_DATABASE_URL`: Django migration과 ETL에 사용할 Neon 스테이징 연결 문자열
- `SUPABASE_DATABASE_URL`: Supabase Dashboard의 Connect에서 받은 Direct connection 또는 Session pooler 문자열
- 실행 환경이 Supabase direct endpoint의 IPv6 경로를 지원하지 않으면 포트 5432의 Session pooler를 사용한다. 여러 조회를 한 read-only 트랜잭션에서 실행하므로 transaction pooler는 사용하지 않는다.
- 두 URL이 같은 host·port·database를 가리키면 명령이 실행을 거부한다.

환경 변수 존재 여부는 값을 노출하지 않고 다음처럼 확인한다.

```bash
awk -F= '/^(NEON_DATABASE_URL|SUPABASE_DATABASE_URL)=/ { print $1, length($0) > length($1) + 1 ? "configured" : "empty" }' backend/.env
```

## 3. Neon 스키마 준비

적용 계획을 먼저 보고 migration을 실행한다.

```bash
uv --directory backend run python manage.py migrate --database neon --plan
uv --directory backend run python manage.py migrate --database neon --noinput
uv --directory backend run python manage.py showmigrations --database neon
```

이미 병합된 migration 파일은 수정하지 않는다. 실패하면 새 migration으로만 보정한다.

## 4. 스테이징 리허설

dry-run은 원본을 읽고 모든 유효성·외래키·대상 제약을 통과하는지 확인한 뒤 대상 트랜잭션을 전부 롤백한다.

```bash
uv --directory backend run python manage.py migrate_supabase_data --database neon --dry-run
```

성공하면 실제 스테이징 이관과 자동 대조를 실행한다.

```bash
uv --directory backend run python manage.py migrate_supabase_data --database neon
uv --directory backend run python manage.py verify_supabase_migration --database neon
```

ETL 순서는 다음과 같이 고정된다.

1. `auth.users`와 `public.users`를 결합한 사용자
2. 메뉴
3. 예약
4. 포인트 거래와 충전 주문
5. 프롬프트, AI 로그, 대화

사용자 UUID와 모든 도메인 PK를 그대로 보존한다. 최초 이관 사용자는 unusable password를 가지며, 같은 ETL을 다시 실행해도 이미 설정된 Django 비밀번호는 덮어쓰지 않는다. `update_or_create`와 트랜잭션 범위 advisory lock으로 재실행과 중복 실행을 안전하게 처리한다.

## 5. 자동 대조 항목

검증 명령은 JSON으로 다음 항목을 출력하며 하나라도 다르면 실패 코드로 종료한다.

- 테이블별 원본·대상 레코드 수
- 테이블별 누락·추가 PK 또는 UUID
- 사용자별 현재 포인트와 전체 포인트 합계
- 예약 상태별 수량
- 포인트 주문 상태별 수량
- 예약 중복 방지, 메뉴·예약 조회, 결제 멱등성, AI 조회에 필요한 인덱스·제약 조건

리허설 로그에는 비밀값이나 결제 응답 원문이 없음을 확인한 뒤 제한된 운영 기록 저장소에 보관한다.

## 6. 운영 점검 창

1. 최신 Supabase 백업 시점과 복원 방법을 확인한다.
2. Django에 `DJANGO_WRITE_BLOCKED=true`를 적용하고 재시작한다.
3. `/api/`의 POST·PUT·PATCH·DELETE가 `503`과 `Retry-After`를 반환하고 GET·`/healthz`가 정상인지 확인한다.
4. 레거시 Supabase RPC 실행 권한과 Edge Function 쓰기 경로가 비활성인지 확인한다.
5. Supabase의 활성 쓰기 세션이 없는지 확인한다.
6. dry-run을 한 번 더 실행한다.
7. 실제 ETL과 별도 검증 명령을 차례로 실행한다.
8. 대조 결과를 검토자가 승인하면 배포 환경의 `DATABASE_URL`을 검증된 Neon pooler URL로 변경한다.
9. Django API와 Celery worker·beat를 재시작한다.
10. 로그인, 메뉴 조회, 예약 생성·취소, 거래 조회, 관리자 조회, 챗봇 SSE를 점검한다.
11. `DJANGO_WRITE_BLOCKED=false`로 바꾸고 재시작한 뒤 쓰기 기능을 다시 점검한다.

## 7. 롤백

Neon 연결 전환 전 실패라면 쓰기 차단을 유지한 채 ETL 원인을 해결하고 재실행한다. Supabase에는 아무 변경도 하지 않는다.

Neon 연결 전환 직후 심각한 오류가 발견되었고 아직 새 쓰기가 없다면 `DATABASE_URL`을 Supabase 복구용 구성으로 되돌리는 것이 아니라 기존 애플리케이션 릴리스와 Supabase 런타임 경로를 함께 복원해야 한다. 새 쓰기가 한 건이라도 발생했다면 단순 연결 롤백은 데이터를 갈라놓으므로 금지하며, 점검 모드로 전환한 뒤 백업 복원 또는 단방향 보정 계획을 세운다.

Supabase Auth·RLS·RPC·Edge Function·pg_cron 제거는 Django 인증 전환과 비밀번호 재설정 검증이 끝나는 5단계에서만 수행한다.
