# Hakchelin 작업 지침

## 구조

- `frontend/`: Nuxt 4 / Vue 3 사용자·관리자 웹
- `backend/`: Django / DRF / Celery 도메인 API
- `packages/api-client/`: OpenAPI에서 생성한 TypeScript 클라이언트
- `supabase/`: 전환 완료 전까지의 레거시 SQL·Edge Function이며 새 기능을 추가하지 않는다.

## 개발 원칙

- 프런트엔드는 생성 API 클라이언트만 통해 Django API와 통신한다.
- 새 Supabase `.from()`, `.rpc()`, Edge Function 직접 호출을 추가하지 않는다.
- Django view는 얇게 유지하고 예약·결제·포인트·권한 규칙은 서비스 계층에 둔다.
- 금전 또는 정원에 영향을 주는 작업은 PostgreSQL 트랜잭션과 행 잠금을 사용한다.
- API 계약 변경 시 OpenAPI 생성 클라이언트도 함께 갱신하고 커밋한다.
- 이미 병합된 Django migration은 수정하거나 삭제하지 않는다.
- `.env`, 서비스 키, 결제 응답 원문, 운영 DB 덤프를 커밋하지 않는다.

## 검증

- 프런트엔드 변경: `pnpm typecheck:web`, `pnpm build:web`
- 백엔드 변경: `uv --directory backend run pytest`
- API 계약 변경: `pnpm generate:api-client` 후 프런트 타입 검사를 실행한다.
- 결제·예약·권한·인증 변경: PostgreSQL 통합 테스트를 추가한다.

## Git 규칙

- `main`에 직접 커밋하거나 push하지 않는다.
- 브랜치는 `codex/` 접두사를 사용한다.
- 커밋은 한국어 Conventional Commits 형식(`feat(backend): Django API 기반 추가`)을 사용한다.
- PR은 CI 통과 후 merge commit으로 병합하고 원격 브랜치를 삭제한다.
