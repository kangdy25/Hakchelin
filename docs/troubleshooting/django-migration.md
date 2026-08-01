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

## 4단계 — 원격 행 단위 ETL의 왕복 지연

### 증상

302건의 작은 데이터셋인데도 Neon dry-run에 약 3분이 걸렸다. 출력이 없는 동안 동일 명령을 다시 실행했지만 트랜잭션 advisory lock이 두 번째 실행을 정상 거부했다.

### 원인

안전한 멱등성을 우선해 각 행을 `update_or_create`하고 생성·수정 시각을 별도 보존했다. 이 과정에서 행마다 조회, savepoint, 저장, timestamp 갱신이 발생해 원격 DB 왕복 횟수가 데이터 건수보다 훨씬 많아졌다.

### 판단

현재 운영 원본 302건은 30분 점검 창 안에 충분히 처리되며, dry-run과 실제 스테이징 이관에서 전체 유효성·외래키·대상 제약을 통과했다. 명령 내부 대조에 이어 별도 검증 명령을 실행해 PK 집합, 포인트 총합 2,246,000점, 예약·주문 상태별 수량이 다시 일치함을 확인했다. 데이터가 수천 건 이상으로 늘어나면 stage별 `bulk_create(update_conflicts=True)`와 사전 unique 검증으로 바꾸되, 사용자 비밀번호 보존과 프롬프트 부분 unique 제약을 별도 처리해야 한다.

## 5단계 — Lightsail·도메인 운영 전환

### SSH 키 권한 때문에 초기 접속이 거부된 문제

새 Lightsail 인스턴스는 Running 상태였지만, `.pem` 파일 권한이 `0644`라 OpenSSH가 `UNPROTECTED PRIVATE KEY FILE`로 키를 무시했다. `chmod 600 LightsailDefaultKey-ap-northeast-2.pem`으로 소유자 전용 권한을 적용하고 `*.pem`을 Git ignore에 추가했다. 인프라 접근 문제는 보안 그룹뿐 아니라 로컬 개인 키 권한도 함께 점검해야 한다.

### 운영 보안 설정이 Docker health check를 실패시킨 문제

Caddy 인증서 발급과 migration은 성공했지만 API health check가 `localhost` HTTP 요청을 보내며 Django의 `ALLOWED_HOSTS`와 HTTPS redirect에 걸려 unhealthy가 됐다. health check가 환경 변수의 운영 Host와 `X-Forwarded-Proto: https`를 보내도록 수정해, 실제 프록시 요청과 같은 조건에서 점검한다. 컨테이너 health check도 운영 middleware를 통과하는 HTTP 요청으로 설계해야 한다.

### Gemini 기본 모델이 신규 프로젝트에서 거절된 문제

챗봇 SSE는 HTTP 200이었지만 `AiLog`에는 `gemini-2.5-flash`가 신규 사용자에게 제공되지 않는다는 502가 남았다. 권장 대체 모델 `gemini-3.6-flash`로 기본값·런북·환경 예시를 교체하고 최신 모델에서 deprecated된 `temperature` 파라미터를 제거했다. 외부 AI 모델의 lifecycle은 운영 환경 변수와 구조화된 로그로 관리해야 한다.

### Gemini timeout이 다음 대화 이력까지 오염시킨 문제

두 번째 챗봇 요청이 20초 read timeout으로 실패한 뒤, 답변 없는 사용자 메시지가 DB 이력에 남아 이후 대화 역할 순서를 깨뜨릴 수 있었다. timeout을 기본 45초의 `GEMINI_REQUEST_TIMEOUT_SECONDS`로 분리하고, Gemini 성공 뒤에만 user·assistant 메시지를 하나의 transaction으로 저장했다. 외부 API 실패는 다음 요청에서 재사용되는 상태까지 복구해야 한다.

### Toss 성공 콜백에서 Vercel SSR이 세션을 잃은 문제

Toss 성공 URL로 새 페이지 이동이 일어나면 Vercel SSR은 `api.hakchelin.cloud` host-only Django 세션 쿠키를 받지 못했다. 전역 middleware가 승인 요청보다 먼저 로그인 페이지로 redirect해 포인트가 적립되지 않았다. `/payment/**`를 Nuxt client-only route로 지정해 브라우저가 API 세션·CSRF 쿠키를 포함해 승인 API를 호출하도록 바꿨다. 서드파티 콜백은 SSR과 브라우저가 보는 인증 상태 차이를 고려해야 한다.

### Toss API 키가 서로 다른 환경·상점에서 섞인 문제

콜백 경로를 고친 뒤에는 Toss 승인 API가 `인증되지 않은 시크릿 키 혹은 클라이언트 키`를 반환했다. 결제창의 클라이언트 키와 서버의 시크릿 키가 test/live 환경 또는 서로 다른 상점(MID)에서 발급된 조합이면 `INVALID_API_KEY`가 발생한다. 브라우저에는 같은 MID의 `test_ck_`를 Vercel 환경 변수로, 서버에는 짝이 되는 `test_sk_`를 `/etc/hakchelin/backend.env`로 설정해 테스트 결제와 포인트 적립을 확인했다. 키의 prefix와 MID를 점검하되 시크릿 원문은 로그·채팅·저장소에 남기지 않는다.

## 운영 안정화 — Neon 백업 도구의 PostgreSQL 버전 불일치

### 문제

격리 복원 리허설을 위해 PostgreSQL 17 이미지의 `pg_dump`를 실행했지만 Neon 서버가 PostgreSQL 18.4로 올라가 있어 `server version mismatch`로 백업이 중단됐다.

### 해결

백업과 일회용 복원 컨테이너를 모두 PostgreSQL 18 이미지로 맞췄다. `pg_dump` 실패 시 불완전한 파일을 성공으로 취급하지 않도록 `.partial`에 먼저 생성하고 검증 뒤 최종 이름으로 이동한다. 생성 뒤에는 `pg_restore --list`, SHA-256, 핵심 테이블 수량 manifest를 차례로 검증한다. Alpine의 BusyBox `sha256sum`은 GNU의 `--check` 장문 옵션을 지원하지 않아 이식 가능한 `-c`를 사용했다.

### 배운 점

PostgreSQL 논리 백업 클라이언트는 서버보다 오래된 major 버전을 고정하면 안 된다. 운영 DB 업그레이드와 백업 도구 버전을 함께 관리하고, 실제 복원 리허설로 버전 변화가 복구 절차에 미치는 영향을 조기에 발견해야 한다.

## 운영 안정화 — Celery worker가 root로 실행된 문제

### 증상

운영 worker는 정상 동작했지만 시작할 때마다 `You're running the worker with superuser privileges` 보안 경고를 출력했다. 같은 이미지의 Django API와 migration도 root 권한으로 실행되고 있었다.

### 해결

Dockerfile에 UID/GID 10001의 전용 사용자를 추가하고 Compose에서도 사용자 ID를 고정했다. 애플리케이션 서비스의 루트 파일시스템을 read-only로 전환하고 capability 제거와 권한 상승 차단을 함께 적용했다. Celery Beat가 기본 작업 디렉터리에 schedule 파일을 기록하므로 쓰기 가능한 `/tmp`를 명시했다.

### 배운 점

컨테이너 내부 root는 호스트 root와 동일하지 않지만 불필요한 권한이며, volume·kernel 취약점·잘못된 capability와 결합될 때 피해 범위를 키운다. 사용자 변경만으로 끝내지 않고 쓰기 경로와 capability를 함께 최소화해야 방어 계층이 생긴다.

## 운영 안정화 — 컨테이너 로그가 디스크 제한 없이 증가하던 문제

### 문제

Compose 서비스가 Docker 기본 `json-file` 로그를 사용하면서 크기·파일 수 제한이 없었다. API access log나 외부 API 반복 오류가 쌓이면 작은 Lightsail 루트 디스크를 소진해 정상 컨테이너까지 중단시킬 수 있었다.

### 해결

모든 서비스 로그를 파일당 10MB, 최대 5개로 회전하도록 설정했다. 5분 서버 내부 점검에는 루트 디스크 85%와 가용 메모리 10% 임계값을 넣고, 외부 HTTPS 점검은 GitHub Actions에서 15분마다 별도로 실행한다.

### 배운 점

health endpoint 하나는 프로세스 바깥의 DNS·TLS 상태를 보여 주지만 worker와 디스크 상태는 설명하지 못한다. 외부 사용자 경로와 서버 내부 의존성을 각각 관측하고 같은 런북에서 연결해야 장애 원인을 빠르게 좁힐 수 있다.

## 운영 안정화 — 공개 저장소와 production self-hosted runner의 신뢰 경계

### 문제

Lightsail에 GitHub self-hosted runner를 설치하면 SSH 없이 배포하기 쉽지만, 공개 저장소의 workflow와 PR 입력을 처리하는 runner가 운영 서버·Docker socket·환경 파일 가까이 놓인다. workflow 구성 실수 하나가 신뢰하지 않은 코드를 운영 호스트에서 실행하게 만들 수 있다.

### 해결

GitHub-hosted runner는 main CI 성공 뒤 비밀값 없는 Django image만 GHCR에 발행한다. Lightsail은 inbound 배포 연결이나 GitHub 장기 token 없이 공개 image의 불변 SHA tag만 pull한다. 서버 측 script도 clean main fast-forward, 단일 배포 lock, health 검증, 이전 image 복구, 실패 SHA 재시도 차단을 적용했다.

로컬 가드 테스트에서는 macOS에 `flock`이 없어 command-not-found가 발생했지만 `if ! flock` 분기가 이를 다른 배포가 진행 중인 상태로 오인했다. 필수 실행 파일을 시작 전에 명시적으로 검사하고 없으면 종료 코드 69로 실패하도록 보완했으며 Ubuntu 준비 절차에 `util-linux`를 포함했다.

### 배운 점

CI/CD 자동화는 명령 횟수만 줄이는 일이 아니라 신뢰 경계를 정하는 일이다. 공개 기여 경로와 운영 자격 증명을 같은 runner에 두지 않고, 검증 산출물만 경계를 통과시키면 자동화와 격리를 함께 얻을 수 있다.

## 운영 안정화 — Vercel 검증과 실제 www DNS가 달랐던 문제

### 증상

Vercel project API에서는 새 `www.hakchelin.cloud`가 `verified: true`였지만 외부 curl은 host를 해석하지 못했다. CLI도 domain 추가 성공 직후 team domain fetch에서 403을 출력해 설정 실패처럼 보였다.

### 원인

apex `hakchelin.cloud` 소유권 덕분에 project domain의 소유 검증은 통과했지만, 가비아 authoritative DNS에는 `www` 레코드가 아직 없었다. CLI의 후속 team domain 조회와 project에 연결된 subdomain 상태도 서로 다른 API 범위였다.

### 해결

project domain API에서 `www`가 실제로 추가됐는지 재확인하고 redirect·status를 308로 설정했다. 별도 domain config API의 `misconfigured: true`와 우선순위 1 `recommendedCNAME`을 기준으로 가비아 레코드를 확정했다. 최종 완료 조건은 dashboard의 verified 표기가 아니라 외부 DNS 해석, TLS, 308 status와 `Location`을 모두 통과하는 것으로 정했다.

### 배운 점

도메인 소유 검증, DNS routing, TLS 발급, HTTP redirect는 서로 다른 단계다. 한 화면의 초록색 상태만으로 완료를 판단하지 않고 실제 사용자 경로를 끝까지 요청해야 한다.
