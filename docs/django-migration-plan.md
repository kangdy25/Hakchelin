# 학슐랭 Django 전환: 프런트·백엔드 분리 모노레포

> 상태: 구현 전 기획 문서
> 목표: 월 인프라 예산 2만 원 이하에서 Nuxt·Supabase 중심 구조를 Django·Neon 중심 구조로 단계 전환한다.

## 1. 목표 아키텍처

```text
Vercel
└─ Nuxt 프런트엔드

Lightsail 1GB · Docker Compose
├─ Caddy: HTTPS·리버스 프록시
├─ Django + Gunicorn: REST API·SSE 챗봇
├─ Celery Worker: 이메일·비동기 작업
├─ Celery Beat: 정기 작업
└─ Redis: 작업 큐·캐시

Neon Free
└─ PostgreSQL: 서비스 데이터 전체

외부 서비스
├─ Gemini API: 챗봇
├─ Toss Payments: 결제 승인
├─ Resend: 비밀번호 재설정 이메일
└─ S3: 암호화된 DB 백업
```

- 월 고정 비용은 Lightsail 1GB `$7`을 기준으로 한다.
- RDS, ElastiCache, ECS, Load Balancer는 사용하지 않는다.
- Neon Free의 0.5GB 저장소와 자동 정지 제약은 MVP에서 허용한다.
- Lightsail은 Gunicorn 워커 1개, Celery 동시성 1개, Redis 메모리 상한으로 운영한다.

## 2. 모노레포 구조

```text
frontend/               Nuxt 프런트엔드
backend/                Django + DRF + Celery
packages/
  api-client/          OpenAPI 기반 TypeScript 타입·클라이언트
infra/
  lightsail/           Docker Compose, Caddy, 배포 설정
supabase/              전환 완료 전의 레거시 SQL·Edge Function
docs/
  django-migration-plan.md
```

- `pnpm workspace`는 `frontend`, `packages/api-client`를 관리한다.
- Django는 `backend/pyproject.toml`과 `uv`로 의존성을 관리한다.
- Django는 DRF와 `drf-spectacular`로 OpenAPI 스키마를 제공한다.
- `packages/api-client`는 OpenAPI에서 TypeScript 타입과 `openapi-fetch` 클라이언트를 생성한다.
- Nuxt는 생성된 API 클라이언트만 사용하며, `useSupabaseClient`, Supabase RPC, Edge Function 직접 호출을 제거한다.
- Vercel의 Root Directory는 `frontend`로 설정한다.
- GitHub Actions는 웹, API, API 계약 변경을 각각 검사한다. API 이미지는 CI에서 빌드하고 Lightsail은 이미지를 내려받아 배포한다.

## 3. Django API와 기능 이전

### 앱 구성

- `accounts`: 사용자, 역할, 로그인, 비밀번호 재설정
- `meals`: 메뉴와 식사 일정
- `reservations`: 예약, 취소, 식권 상태
- `wallet`: 포인트, 거래, 기부
- `payments`: Toss 주문 생성과 승인
- `chatbot`: Gemini 챗봇, 프롬프트, AI 로그, 대화 기록
- `operations`: 관리자 기능과 노쇼 처리

### 공개 API 계약

- 인증: 로그인, 로그아웃, 토큰 갱신, 비밀번호 재설정, 현재 사용자 조회
- 사용자: 메뉴, 내 예약·식권·포인트·거래 이력 조회
- 변경: 예약, 예약 취소, 포인트 주문 생성, Toss 결제 승인, 포인트 기부
- 관리자: 메뉴, 사용자, 식권, 포인트, AI 로그 관리
- 챗봇: 기존 SSE `token`, `done`, `error` 이벤트 계약 유지

### 서버 규칙

- 예약·포인트·결제는 Django 서비스 계층에서 `transaction.atomic`과 행 잠금으로 처리한다.
- 정원, 중복 예약, 마감 시간, 포인트 잔액, 결제 승인 중복, 관리자 권한을 서버에서 검증한다.
- 챗봇은 Gemini Python SDK를 직접 사용하며 LangChain은 도입하지 않는다.
- 챗봇의 입력 길이, 일일 제한, 읽기 전용 도구, 가드레일, 7일 대화 보존, AI 로그 정책을 유지한다.
- 챗봇 도구는 메뉴·본인 식권·본인 포인트만 Django 서비스 내부에서 조회한다.

## 4. 단계별 이전

### 단계 1 — Django와 모노레포 기반 구축

1. 현재 Nuxt 앱을 `frontend`로 이동하고 pnpm workspace를 구성한다.
2. `backend`에 Django, DRF, Celery, Redis, OpenAPI 기반을 만든다.
3. Docker Compose와 Caddy, health check, 로그 로테이션, 자동 재시작을 구성한다.
4. GitHub Actions에서 웹·API 테스트와 이미지 배포 경로를 분리한다.

### 단계 2 — Supabase 호환 API 전환

1. Django가 기존 Supabase PostgreSQL과 Supabase JWT를 읽도록 구성한다.
2. 챗봇 Edge Function, Toss 결제 승인 Function, 예약·취소·포인트·관리자 RPC를 Django API로 이전한다.
3. Nuxt의 각 화면을 생성된 API 클라이언트로 순차 전환한다.
4. Supabase의 직접 조회·RPC·Function 호출이 사라질 때까지 기존 경로는 호환용으로만 유지한다.

### 단계 3 — Neon 데이터 이전

1. Neon에 Django migration으로 최종 스키마를 만든다.
2. Supabase Auth UUID를 Django Custom User의 기본키로 유지한다.
3. `public.users`의 학번·이름·역할·포인트, 메뉴, 예약, 거래, AI 데이터를 ETL로 이전한다.
4. 기존 비밀번호는 이전하지 않고 Django 사용자는 unusable password 상태로 생성한다.
5. 전환 시간에는 쓰기 요청을 중지하고, 데이터 수량·UUID·포인트 합계·예약·거래·인덱스·제약 조건을 대조한다.
6. 검증이 끝나면 Django의 DB 연결을 Neon으로 교체한다. 이후에는 이중 기록을 하지 않는다.

### 단계 4 — Django 인증과 Supabase 제거

1. 기존 사용자에게 Resend 비밀번호 재설정 링크를 발송한다.
2. Django 로그인, 로그아웃, 토큰 갱신, 현재 사용자 API를 활성화한다.
3. Access/refresh 토큰은 Secure·HttpOnly 쿠키로만 전달한다.
4. Nuxt는 `credentials: include`로 호출하고, CORS·CSRF·`SameSite=None; Secure` 정책을 적용한다.
5. 안정화와 백업 검증 후 Supabase Auth, RLS, RPC, Edge Function, pg_cron 및 프런트엔드 SDK 의존성을 제거한다.

## 5. 운영과 검증

- Neon은 SSL과 pooler 연결 문자열을 사용하고, Django에는 짧은 `CONN_MAX_AGE`를 설정한다.
- API 전용 커스텀 도메인을 Lightsail에 연결하고 Caddy가 TLS를 관리한다.
- 암호화된 일일 `pg_dump`를 S3에 보관하고 30일 뒤 삭제한다.
- AWS 비용 알림은 `$10`, `$12`에 설정하고, Neon·Gemini 사용량도 모니터링한다.

### 완료 기준

- Nuxt에서 Supabase `.from()`, `.rpc()`, Edge Function 직접 호출이 제거된다.
- 기존 사용자 UUID와 메뉴·예약·포인트·거래·챗봇 데이터가 Neon에서 정확히 유지된다.
- 동시 예약, 정원 초과, 중복 결제 승인, 타인 데이터 접근, 관리자 권한, 취소·환불 규칙을 자동 테스트한다.
- 챗봇의 인젝션 차단, 본인 데이터 격리, 일일 제한, SSE 최종 답변, 7일 대화 삭제를 검증한다.
- OpenAPI 변경 시 TypeScript 클라이언트 재생성과 Nuxt 타입 검사가 CI에서 수행된다.
