# Supabase 종료 런북

이 런북은 운영 전환이 끝난 뒤 Supabase를 애플리케이션 의존성 및 복구 경로에서 제외하는 절차를 기록한다. 원격 프로젝트 삭제는 복구할 수 없는 별도 작업이며, 저장소 정리·배포·Neon 백업 검증과 구분한다.

> 완료: 2026-08-02 `Smart-Campus-Meal` 원격 프로젝트를 영구 삭제하고 프로젝트 목록에서 제거됨을 확인했다. 삭제 직후 프런트와 Django API health도 정상이다.

## 저장소 종료 기준

- `supabase/` SQL·Edge Function·CLI 연결 메타데이터가 없다.
- Django `migration_tools` 앱과 이관 명령·테스트가 없다.
- 프런트엔드와 lockfile에 Supabase SDK, 직접 쿼리, RPC, Function 호출이 없다.
- backend 환경 변수 예시에 원본 DB URL이나 별도 이관 대상 URL이 없다.
- `scripts/check-runtime-boundaries.sh`와 전체 CI가 통과한다.

문서의 Supabase 표기는 과거 아키텍처, ETL 결과와 트러블슈팅을 설명하는 기록이며 실행 의존성이 아니다.

## 운영 환경 정리

배포된 retirement commit의 API image가 healthy인지 먼저 확인한다. 이후 값은 출력하지 않고 환경 변수 이름만 검사한다.

```bash
sudo grep -E '^(SUPABASE_|NEON_DATABASE_URL=)' /etc/hakchelin/backend.env
```

결과가 있으면 해당 줄을 서버 환경 파일에서 제거하고 Compose를 재기동한다. 서비스에는 Neon pooler를 가리키는 `DATABASE_URL`만 남긴다. 로컬 `backend/.env`, Vercel 환경 변수와 GitHub Actions secret에도 사용하지 않는 `SUPABASE_*`, `NEON_DATABASE_URL`이 있으면 삭제한다.

정리 뒤 다음을 다시 확인한다.

```bash
curl --fail https://api.hakchelin.cloud/healthz
scripts/check-runtime-boundaries.sh
```

브라우저에서는 회원가입·로그인, 메뉴 조회, 예약 생성·취소, 포인트 내역, Toss 테스트 결제, 관리자 화면과 챗봇 연속 대화를 점검한다.

## 원격 프로젝트 처리

Supabase 프로젝트가 존재하는 것만으로 애플리케이션 의존성이 생기지는 않는다. 다만 불필요한 데이터와 자격 증명을 장기 보관하지 않으려면 다음 조건을 모두 확인한 뒤 Dashboard에서 프로젝트를 삭제한다.

1. retirement commit이 운영 배포됐고 상태 점검이 성공했다.
2. 최신 Neon 논리 백업과 격리 복원 리허설이 성공했다.
3. 운영·Vercel·GitHub 환경에 Supabase URL·키가 없다.
4. Auth, Edge Function, RPC와 원본 PostgreSQL 요청이 더 이상 발생하지 않는다.
5. Supabase를 롤백 경로로 사용하지 않는다는 운영 원칙에 동의한다.

프로젝트 삭제 뒤에는 Supabase 원본으로 복구하지 않는다. 장애 복구는 [Neon 백업·복원 런북](./neon-backup-restore.md)에 따른다.

실제 종료에서는 CLI로 계정의 프로젝트 목록을 먼저 조회해 이름·리전·상태와 project ref가 모두 일치하는 단일 대상을 확정했다. 삭제 응답의 프로젝트 이름을 재확인하고 다시 목록을 조회해 대상이 사라진 것을 검증했다. 다른 Supabase 프로젝트는 변경하지 않았다.
