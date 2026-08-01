# 운영 모니터링·장애 대응 런북

이 런북은 `hakchelin.cloud`와 `api.hakchelin.cloud`의 기본 가용성, Lightsail 컨테이너, Celery, 디스크·메모리를 관측하고 장애 시 복구하는 절차다.

## 관측 구조

- GitHub Actions `Production health`: 외부 네트워크에서 15분마다 프런트와 API HTTPS를 확인한다.
- Lightsail systemd timer: 5분마다 컨테이너 상태, API·Redis health, 마지막 migration, Celery ping, 외부 HTTPS, 디스크·메모리를 확인한다.
- Docker 로그: 서비스별 `10MB × 5개`로 회전해 인스턴스 디스크가 무제한 로그로 차는 것을 막는다.
- Django `AiLog`: Gemini 요청 상태·지연·오류를 보되 사용자 메시지나 API 키를 운영 알림에 복사하지 않는다.

GitHub Actions 실패 알림을 받으려면 GitHub 개인 설정에서 Actions 알림을 활성화한다. 무료 외부 점검의 최대 탐지 지연은 약 15분이며, 더 짧은 SLA가 필요해질 때 별도 uptime 서비스를 연결한다.

## 서버 내부 점검 설치

3번 작업 배포 뒤 한 번만 실행한다.

```bash
sudo cp /opt/hakchelin/infra/lightsail/systemd/hakchelin-healthcheck.service /etc/systemd/system/
sudo cp /opt/hakchelin/infra/lightsail/systemd/hakchelin-healthcheck.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hakchelin-healthcheck.timer
sudo systemctl start hakchelin-healthcheck.service
sudo systemctl status hakchelin-healthcheck.service --no-pager
sudo systemctl list-timers hakchelin-healthcheck.timer --no-pager
```

실패 원인은 비밀값 없이 journal에 남는다.

```bash
sudo journalctl -u hakchelin-healthcheck.service --since "30 minutes ago" --no-pager
```

## 정기 점검

```bash
cd /opt/hakchelin
sudo infra/lightsail/scripts/check-service-health.sh

sudo docker compose --env-file /etc/hakchelin/compose.env \
  -f infra/lightsail/docker-compose.yml \
  ps

sudo docker compose --env-file /etc/hakchelin/compose.env \
  -f infra/lightsail/docker-compose.yml \
  logs --since=30m --tail=200 api worker beat caddy redis
```

매월 Neon 백업·복원 리허설, 디스크 사용량, TLS 만료 자동 갱신 로그, Celery 노쇼·대화 삭제 실행 흔적을 확인한다.

## 사고 대응 순서

1. GitHub Actions와 서버 내부 점검 중 어느 신호가 실패했는지 기록한다.
2. `docker compose ps`와 최근 30분 로그를 확보한다. 환경 파일이나 전체 결제 응답은 출력하지 않는다.
3. 사용자 영향 기능을 확인한다: 로그인, 메뉴 조회, 예약, 결제 테스트, 챗봇.
4. 데이터 오염 가능성이 있으면 `DJANGO_WRITE_BLOCKED=true`로 쓰기를 먼저 막고 재기동한다.
5. 아래 유형별 복구를 수행한 뒤 외부 health와 핵심 기능을 다시 검증한다.
6. 발생 시각, 영향, 원인, 복구, 재발 방지 테스트를 트러블슈팅 일지에 추가한다.

### API 또는 Caddy 장애

- `migrate`, `api`, `caddy` 순서로 최근 로그를 확인한다.
- API만 unhealthy면 `DJANGO_ALLOWED_HOSTS`, HTTPS proxy header, DB 연결, migration 실패를 확인한다.
- 인증서 문제면 DNS가 현재 Static IP를 가리키는지와 Caddy ACME 로그를 확인한다.
- 새 배포 직후 시작됐다면 이전 검증된 merge commit의 이미지를 재배포한다. Django migration 파일은 되돌리지 않는다.

### Celery 또는 Redis 장애

- `redis-cli ping`과 `celery -A config inspect ping`으로 broker와 worker를 분리 진단한다.
- Redis 재시작 전 AOF 오류와 디스크 여유를 확인한다.
- worker가 복구된 뒤 노쇼·대화 삭제 task가 중복 실행돼도 서비스 계층의 상태 조건과 트랜잭션이 안전한지 확인한다.

### 디스크·메모리 부족

- `docker system df`와 서비스별 회전 로그를 확인한다.
- 운영 DB dump를 인스턴스에 장기 적재하지 않고 암호화 백업 저장소로 옮긴다.
- 임의의 Docker volume이나 Caddy 인증서 데이터를 삭제하지 않는다.
- 메모리 부족이 반복되면 Gunicorn worker·Celery concurrency를 늘리지 말고 인스턴스 상향 또는 작업 분리를 검토한다.

### Neon·Gemini·Toss 외부 장애

- `/healthz`만으로 외부 기능 정상을 단정하지 않고 해당 기능의 구조화된 오류 로그를 확인한다.
- Neon 장애에서는 쓰기를 차단하고 검증된 백업 복원 절차를 준비한다.
- Gemini timeout은 사용자 대화를 부분 저장하지 않으며 재시도 안내를 유지한다.
- Toss는 테스트 키만 사용한다. 키 원문이나 결제 응답 원문을 로그·이슈에 남기지 않는다.
