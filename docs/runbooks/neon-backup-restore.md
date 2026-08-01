# Neon 백업·복원 리허설 런북

이 런북은 운영 Neon 데이터베이스의 논리 백업을 만들고, 운영과 완전히 분리된 일회용 PostgreSQL에 복원해 복구 가능성을 확인하는 절차다. 백업 파일, manifest, checksum은 비밀 정보로 취급하며 저장소에 커밋하지 않는다.

## 백업 생성

로컬 `backend/.env`의 `NEON_DATABASE_URL`을 사용할 때는 다음처럼 실행한다.

```bash
infra/lightsail/scripts/backup-neon.sh \
  backend/.env \
  /tmp/hakchelin-backups \
  NEON_DATABASE_URL
```

Lightsail의 운영 환경 파일에서는 `DATABASE_URL`이 기본값이므로 세 번째 인자를 생략한다.

```bash
sudo -u ubuntu infra/lightsail/scripts/backup-neon.sh \
  /etc/hakchelin/backend.env \
  /var/backups/hakchelin
```

명령은 다음 세 파일을 권한 `0600`으로 만든다.

- `hakchelin-neon-<UTC 시각>.dump`: PostgreSQL custom-format 논리 백업
- `.dump.manifest.json`: 8개 핵심 도메인 테이블의 백업 시점 수량
- `.dump.sha256`: 전송·보관 중 변조와 손상 검증용 checksum

연결 문자열은 명령 인자나 로그에 출력하지 않는다. 백업 디렉터리는 운영 서버 디스크에만 장기 보관하지 말고 접근이 제한된 암호화 저장소로 복제한다.

## 격리 복원 리허설

```bash
infra/lightsail/scripts/restore-neon-rehearsal.sh \
  /tmp/hakchelin-backups/hakchelin-neon-<UTC 시각>.dump
```

복원 명령은 다음 순서로 검증한다.

1. SHA-256 checksum 일치
2. Neon 운영 버전과 같은 일회용 PostgreSQL 18 컨테이너에 `pg_restore --exit-on-error`
3. 백업 manifest와 복원된 8개 핵심 테이블 수량 일치
4. Django migration 이력 존재와 사용자 포인트 기본 무결성
5. 성공·실패와 관계없이 일회용 컨테이너 삭제

이 스크립트는 Neon이나 다른 원격 DB에 복원하지 않는다. 운영 복원이 필요한 사고에서는 새 Neon 프로젝트 또는 격리 브랜치를 먼저 만들고, 연결 대상이 운영 DB가 아님을 두 사람이 확인한 뒤 같은 dump를 복원한다.

## 주기와 보관

- 스키마 migration 또는 큰 운영 변경 전 수동 백업과 복원 리허설
- 월 1회 복원 리허설
- 백업 성공보다 **복원과 데이터 대조 성공**을 완료 기준으로 사용
- 파일명, 생성 시각, checksum, 복원 결과, 작업자를 운영 기록에 남김
- 보관 기한이 끝난 파일은 저장소가 아닌 백업 저장소의 수명 주기로 삭제

Neon 자체 복구 기능과 논리 백업은 역할이 다르다. Neon의 프로젝트 복구 기능은 빠른 시점 복구에 사용하고, `pg_dump`는 공급자·프로젝트와 분리된 복구 사본 및 스키마·데이터 점검에 사용한다.
