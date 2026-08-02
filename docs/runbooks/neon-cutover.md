# Neon 컷오버 완료 기록

이 문서는 데이터 컷오버가 끝난 뒤 남긴 운영 기록이다. 원본 BaaS를 읽던 ETL 명령과 별도 연결 환경 변수는 종료 단계에서 제거했으므로 이 문서의 과거 절차를 다시 실행하지 않는다.

## 완료된 검증

- 사용자 UUID와 프로필, 메뉴, 예약, 포인트 거래, 충전 주문, AI 로그와 대화를 Neon으로 이관했다.
- 원본·대상의 레코드 수와 PK 집합, 사용자별 포인트, 예약·주문 상태, 필수 인덱스·제약 조건을 대조했다.
- 운영 Django와 Celery의 데이터베이스 연결을 Neon pooler `DATABASE_URL` 하나로 통일했다.
- 운영 도메인에서 인증, 메뉴, 예약·취소, 포인트, Toss 테스트 결제, 관리자, 챗봇 SSE를 확인했다.
- Neon 논리 백업을 격리 PostgreSQL에 복원하고 핵심 테이블 수량과 기본 무결성을 재검증했다.

## 현재 운영 원칙

Neon이 유일한 서비스 데이터 원본이다. 장애 시 과거 BaaS로 연결을 되돌리거나 이중 기록하지 않는다. 쓰기를 차단한 뒤 [Neon 백업·복원 런북](./neon-backup-restore.md)에 따라 검증된 백업을 새 Neon 프로젝트나 격리 브랜치에 복원하고, 대조가 끝난 연결 문자열만 `DATABASE_URL`에 적용한다.

완료된 ETL의 상세 수량과 판단은 [Django 마이그레이션 구현 일지](../django-migration-implementation-journal.md), 과정에서 발견한 문제는 [트러블슈팅 일지](../troubleshooting/django-migration.md)에 보존한다.
