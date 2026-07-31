# Django 마이그레이션 트러블슈팅 일지

학슐랭의 Nuxt·Supabase 구조를 Django·Neon 구조로 전환하며 발견한 문제와 해결 과정을 기록한다. 각 항목은 포트폴리오에서 설계 판단과 검증 방법을 설명하기 위한 근거다.

단계별 구현 범위, API 구조와 검증 결과는 [Django 마이그레이션 구현 일지](../django-migration-implementation-journal.md)에 정리했다.

## 1단계 — 모노레포 전환 뒤 Vercel 빌드 실패

### 증상

Nuxt를 `frontend/`로 이동한 뒤 PR 미리보기 배포가 `nuxt: command not found`로 실패했다.

### 원인

Vercel 프로젝트의 Root Directory가 저장소 루트로 남아 있었다. Vercel은 루트의 workspace 의존성은 설치했지만, 루트에서 기존 `nuxt build` 명령을 실행해 Nuxt 바이너리를 찾지 못했다.

### 해결

Vercel 프로젝트 설정의 Root Directory를 `frontend`로 변경했다. 이후 Preview 배포가 성공했고, Vercel은 프런트 패키지의 Nuxt 설정을 기준으로 빌드했다.

### 배운 점

모노레포 전환은 파일 이동만으로 끝나지 않는다. CI, 호스팅 플랫폼의 작업 디렉터리, 패키지 관리자 workspace 경계를 하나의 변경 단위로 검증해야 한다.

## 1단계 — CI에서만 Nuxt 타입 검사가 실패

### 증상

로컬에서는 `nuxt typecheck`가 통과했지만 GitHub Actions에서는 `vue-tsc`가 TypeScript 6과 호환되지 않아 실패했다.

### 원인

`frontend` 패키지에 `vue-tsc`와 호환되는 TypeScript 버전이 직접 선언되지 않았다. CI는 이를 임시 설치하면서 workspace의 TypeScript 6을 해석했고, 로컬 캐시와 다른 의존성 그래프가 만들어졌다.

### 해결

`frontend/package.json`에 `typescript` 5.x와 `vue-tsc`를 명시하고 lockfile을 갱신했다. 이후 로컬과 CI가 같은 도구 체인을 사용하도록 고정했다.

### 배운 점

개발 도구도 패키지의 직접 의존성으로 선언해야 한다. 특히 타입 검사 도구를 전역 설치나 npx 자동 설치에 맡기면 CI 재현성이 약해진다.

## 2단계 — Codex 실행 환경의 GitHub CLI 인증 불일치

### 증상

사용자 터미널에서는 GitHub CLI 로그인이 성공했지만, 제한된 실행 환경에서는 기존의 만료된 토큰이 계속 보였다.

### 원인

샌드박스가 호스트의 keyring 기반 인증 정보를 직접 읽지 못했다.

### 해결

호스트 권한으로 GitHub CLI를 실행해 keyring 인증을 확인한 뒤 PR 생성·검사 확인·merge commit 병합을 수행했다.

### 배운 점

로컬 개발 환경에서는 셸, 샌드박스, 호스트 keyring의 자격 증명 범위가 다를 수 있다. 인증 실패 시 토큰을 재발급하기 전에 어느 실행 경계에서 실패하는지 먼저 확인해야 한다.

## 3단계 — 포인트 변경을 화면 코드에서 분리해야 했던 이유

### 문제

기존 구현은 Supabase RPC가 예약·취소·충전의 원자성을 담당했다. Django로 옮길 때 화면 또는 view에서 포인트 잔액을 먼저 갱신하면, 중간 실패·동시 요청·중복 Toss 승인에서 잔액과 거래 이력이 어긋날 수 있었다.

### 해결

예약·취소·기부·결제 승인 규칙을 Django 서비스 계층으로 분리하고, 각 변경을 `transaction.atomic()`과 `select_for_update()` 안에서 처리했다. 포인트 잔액 변경과 거래 이력 생성을 같은 트랜잭션으로 묶었고, 이미 `paid`인 주문은 같은 결과를 반환하도록 멱등성을 보장했다.

### 검증

예약 후 취소 시 잔액이 원래 값으로 복구되고 거래 이력이 두 건 생성되는지, 같은 결제 승인을 두 번 요청해도 충전 거래가 한 번만 생성되는지를 테스트했다.

### 배운 점

결제와 예약 같은 상태 변경은 HTTP 요청 단위가 아니라 도메인 트랜잭션 단위로 설계해야 한다. 서비스 계층은 이후 DRF API, Celery 작업, 관리자 명령이 같은 규칙을 재사용하게 해 준다.

## 읽기 연동 — 생성 계약과 기존 UI 타입의 경계

OpenAPI의 JSON 필드는 TypeScript에서 `unknown`으로 생성되지만 기존 UI의 메뉴 옵션은 더 구체적인 타입을 사용했다. 생성 API 응답은 경계에서 명시적으로 변환하고, 화면 내부 타입은 기존 계약을 유지해 생성 코드의 느슨한 타입이 UI 전체로 퍼지지 않게 했다.

## 쓰기 연동 — 전환기 테스트가 최종 구조를 방해한 문제

### 증상

Supabase JWT 브리지 URL을 최종 Django ORM view로 교체하자 기존 `test_legacy_bridge.py`가 모두 실패했다. 테스트는 새 API의 동작이 아니라 legacy repository mock 호출을 검증하고 있었다.

### 원인

전환기의 안전망이었던 테스트가 구현 상세에 결합되어 최종 아키텍처를 고정하는 제약으로 바뀌었다. 같은 URL에서 브리지와 최종 ORM API를 동시에 유지하면 인증 방식과 응답 계약도 이중화된다.

### 해결

legacy app과 JWT 설정을 제거하고, 테스트를 세션 로그인·CSRF·사용자별 예약 격리·관리자 권한·결제 멱등성·SSE 이벤트 계약을 검증하는 HTTP 통합 테스트로 교체했다.

### 배운 점

마이그레이션 테스트는 단계별 수명이 있다. 임시 어댑터의 테스트를 영구 계약으로 취급하지 말고, 컷오버 시점에는 사용자가 실제로 의존하는 HTTP 계약 중심으로 다시 작성해야 한다.

## OpenAPI — APIView의 암묵적 스키마가 생성 클라이언트를 깨뜨린 문제

### 증상

DRF `APIView`만으로 엔드포인트를 추가했을 때 drf-spectacular가 요청·응답 serializer를 추론하지 못했고, 메뉴 생성 요청에 읽기 전용 `id`, `created_at`까지 필요하다는 TypeScript 타입이 생성됐다.

### 원인

런타임에서는 자유로운 `request.data`가 동작하지만 OpenAPI 생성기는 그 구조를 알 수 없다. 읽기 serializer를 쓰기 요청에도 재사용하면 read-only 필드와 required 필드의 의미가 섞인다.

### 해결

각 API에 `extend_schema`와 명시적 serializer를 연결하고 `MenuSerializer`와 `MenuWriteSerializer`를 분리했다. OpenAPI는 실행 중인 서버를 호출하지 않고 Django management command로 생성하도록 바꿔 CI 재현성도 높였다.

### 배운 점

생성 클라이언트를 쓰는 프로젝트에서 OpenAPI는 문서가 아니라 컴파일 경계다. view 구현과 동시에 요청·응답 스키마를 설계해야 프런트 타입 검사가 계약 회귀를 잡아낼 수 있다.

## 세션 인증 — 로그인 직후 CSRF 토큰 회전

### 증상

CSRF 검사를 강제한 통합 테스트에서 로그인은 성공했지만 바로 이어진 예약·관리자·챗봇 POST가 403을 반환했다.

### 원인

Django는 로그인 시 세션 고정 공격을 막기 위해 CSRF 토큰을 회전한다. 테스트가 로그인 전에 발급된 토큰을 계속 헤더에 사용하고 있었다.

### 해결

로그인 응답 뒤 갱신된 `csrftoken` 쿠키를 다시 읽도록 테스트를 수정했다. Nuxt 클라이언트도 mutation 직전에 쿠키에서 최신 토큰을 읽어 `X-CSRFToken`에 넣는다.

### 배운 점

쿠키 인증 전환은 `credentials: include`만으로 끝나지 않는다. CSRF 발급 시점, 로그인 시 토큰 회전, 브라우저 쿠키와 헤더의 동기화를 하나의 흐름으로 검증해야 한다.

## 서비스 계층 — 실제 세션 사용자에서만 발생한 LazyObject 오류

### 증상

서비스 단위 테스트는 통과했지만 실제 세션으로 예약 API를 호출하면 `SimpleLazyObject`에 `objects`가 없다는 500 오류가 발생했다.

### 원인

행 잠금을 위해 `type(user).objects`를 사용했다. 직접 만든 `User` 인스턴스에서는 동작하지만 Django request의 `request.user`는 지연 평가 wrapper일 수 있다.

### 해결

예약·포인트·결제 서비스에서 `django.contrib.auth.get_user_model()`로 모델을 가져와 잠금 조회하도록 통일했다.

### 배운 점

서비스 단위 테스트와 HTTP 통합 테스트는 서로 다른 오류를 잡는다. 프레임워크가 주입하는 proxy·lazy 객체까지 확인하려면 실제 인증 middleware를 통과한 테스트가 필요하다.

## 로컬 브라우저 — localhost와 127.0.0.1 혼용

### 증상

Nuxt와 Django가 각각 정상 실행되고 API 테스트도 통과했지만 브라우저 회원가입에서는 `Failed to fetch`가 표시됐다.

### 원인

프런트는 `127.0.0.1`, CORS·CSRF 허용 origin은 `localhost`를 사용했다. 두 주소는 네트워크상 같은 컴퓨터를 가리키지만 브라우저 origin과 SameSite 쿠키 기준에서는 서로 다르다.

### 해결

개발 기본 주소를 `http://localhost:3000`과 `http://localhost:8000`으로 통일하고, 환경 변수 예시에는 `localhost`와 `127.0.0.1`을 모두 허용 origin으로 기록했다. 이후 브라우저에서 회원가입, 로그인, SSR 프로필, 메뉴·예약 조회, 로그아웃을 순서대로 확인했다.

### 배운 점

로컬 연동 검증은 curl만으로 대체할 수 없다. CORS, SameSite, HttpOnly, CSRF는 브라우저 보안 모델 안에서만 드러나는 문제가 있으므로 실제 origin을 사용한 E2E 점검이 필요하다.

## 결제와 예약 후처리 — Edge Function과 pg_cron 책임 이동

Toss 결제 승인은 브라우저가 전달한 값을 바로 신뢰하지 않고 Django가 비밀 키로 Toss 승인 API를 호출한 뒤에만 포인트를 적립한다. 주문 소유권·금액을 먼저 검증하고 주문 ID를 멱등성 키로 사용한다.

Supabase `pg_cron`이 담당하던 노쇼 처리는 Celery Beat 15분 작업으로 옮겼다. 식사 종료 1시간이 지난 예약을 행 잠금으로 처리하고 예약금을 제외한 금액과 거래 이력을 같은 트랜잭션에 기록한다. 대화 7일 삭제도 Celery Beat 작업으로 이전했다.

## 현재 로컬 연동 상태

Nuxt의 인증·메뉴·예약·포인트·관리자·챗봇 코드는 모두 생성 OpenAPI 클라이언트 패키지를 통해 Django `/api/`을 사용한다. `@nuxtjs/supabase`, Supabase CLI 패키지, 생성 DB 타입과 직접 `.from()`·`.rpc()`·Edge Function 호출은 프런트와 lockfile에서 제거했다.

`supabase/` 디렉터리는 Neon 데이터 이관과 장애 복구 대조를 위한 legacy 원본으로만 남겨 두며 런타임에서는 사용하지 않는다. 외부 기능을 실제로 사용하려면 로컬 `.env`에 `TOSS_PAYMENTS_SECRET_KEY`, `GEMINI_API_KEY`를 설정해야 한다.

## 4단계 — SQLite 테스트만으로 행 잠금을 검증할 수 없던 문제

### 문제

서비스 단위 테스트는 통과했지만 기본 테스트 DB인 SQLite는 `select_for_update()`를 실제 행 잠금으로 실행하지 않는다. 따라서 동시에 두 예약이 정원 검사를 통과하거나 동일 결제가 두 번 적립되는 회귀를 잡을 수 없었다.

### 해결

CI backend job에 PostgreSQL 17 서비스를 추가하고 `TEST_DATABASE_URL`이 있으면 Django 테스트 DB를 PostgreSQL로 만들도록 설정했다. 두 개의 독립 DB 연결과 barrier를 사용하는 스레드 테스트로 정원 1개 메뉴의 동시 예약과 동일 주문의 동시 결제를 실행했다. 로컬에서도 일회용 PostgreSQL 17 컨테이너로 전체 20개 테스트를 실행해 모두 통과함을 확인했다.

### 배운 점

트랜잭션 코드는 데이터베이스 엔진의 의미론에 의존한다. SQLite 테스트는 빠른 회귀 검사용으로 유용하지만 행 잠금·부분 unique index·동시성 보장은 실제 운영 계열 PostgreSQL에서 별도로 검증해야 한다.

## 4단계 — Supabase 사용자 데이터가 두 스키마에 나뉜 문제

### 문제

`public.users`만 이관하면 Django 로그인 식별자인 이메일이 없고, `auth.users`만 이관하면 역할·학번·이름·포인트가 없다. 두 테이블 중 일부만 존재하는 계정까지 임의의 기본값으로 채우면 사용자 UUID는 보존되더라도 계정 의미가 달라진다.

### 해결

원본을 read-only 트랜잭션으로 읽으며 두 테이블을 UUID로 결합했다. 프로필만 있는 행, 프로필 없는 이메일 계정, 이메일 없는 프로필의 개수를 먼저 검사하고 하나라도 있으면 ETL을 중단한다. 정상 계정은 Supabase UUID를 Django PK로 그대로 사용하고 최초 이관 시 unusable password를 설정한다.

### 배운 점

데이터 마이그레이션에서 누락 값을 조용히 보정하는 것보다 원본 무결성 오류를 명시적으로 드러내는 편이 안전하다. 특히 인증 데이터는 자동 추측보다 운영자가 예외 계정을 확인할 수 있는 실패 보고가 필요하다.

## 4단계 — Neon pooler와 advisory lock 수명

### 문제

ETL 중복 실행을 막기 위해 세션 advisory lock을 사용하면 transaction pooler가 연결을 반환한 뒤 잠금이 예상과 다른 세션에 남을 수 있다.

### 해결

ETL 전체를 하나의 대상 트랜잭션으로 묶고 `pg_try_advisory_xact_lock`을 사용했다. 잠금은 트랜잭션 종료와 함께 자동 해제되고, dry-run은 같은 트랜잭션을 rollback한다.

### 배운 점

연결 pooler를 사용하는 환경에서는 애플리케이션 요청과 데이터베이스 세션이 항상 1:1이 아니다. 세션 상태에 의존하는 기능은 트랜잭션 범위 기능으로 바꾸거나 direct 연결을 사용해야 한다.

## 4단계 — 실행 환경에서 uv 캐시와 Supabase CLI가 보이지 않은 문제

Codex 샌드박스는 사용자 전역 `~/.cache/uv`와 interactive shell의 Supabase CLI 경로를 그대로 사용할 수 없었다. uv 검증은 쓰기 가능한 `/tmp/hakchelin-uv-cache`를 `UV_CACHE_DIR`로 지정해 해결했다. 데이터 이관은 CLI 로그인 상태에 의존하지 않고 `SUPABASE_DATABASE_URL`을 명시적으로 받는 Django 명령으로 구현해, 로컬·CI·점검 창에서 같은 실행 경로를 사용하도록 했다.

## 4단계 — Supabase direct DB 호스트를 해석하지 못한 문제

### 증상

`SUPABASE_DATABASE_URL`에 `db.<project-ref>.supabase.co` 형태의 direct 연결 문자열을 넣고 dry-run을 실행했지만, 비밀번호 인증 전 단계에서 호스트 이름을 해석하지 못했다.

### 원인

Supabase direct connection은 IPv6 경로를 사용한다. 실행 환경이나 네트워크가 IPv4 중심이면 direct 주소를 사용할 수 없고, 프로젝트가 제공하는 Supavisor pooler 경로가 필요하다.

### 해결

Supabase Dashboard의 Connect 화면에서 Session pooler 연결 문자열을 선택한다. 트랜잭션 중 여러 원본 조회를 같은 세션에서 수행하므로 transaction pooler 대신 포트 5432의 session pooler를 사용한다. 비밀번호에 URL 예약 문자가 있으면 percent-encoding한 문자열을 `.env`에 저장한다.

초기 구현은 잘못된 포트 문자열에서 발생한 `ValueError`를 잡지 못했고, command 테스트도 개발자의 실제 `.env`를 상속했다. URL 파싱 오류를 비밀값 없는 `CommandError`로 변환하고, command 테스트에는 항상 가짜 `SUPABASE_DATABASE_URL`을 주입해 로컬 자격 증명과 완전히 격리했다. 진단 로그에 노출 가능성이 생긴 DB 비밀번호는 즉시 폐기·재설정했다.

### 배운 점

데이터베이스 연결 검증은 비밀번호만 확인해서는 부족하다. DNS, IP 버전, pooler 모드, 사용자 이름 형식을 별도 계층으로 나눠 진단해야 인증 오류와 네트워크 오류를 혼동하지 않는다.
