# 애플리케이션 컨테이너 보안 런북

Django API, migration, Celery worker·beat는 이미지와 Compose 양쪽에서 UID/GID `10001`의 비루트 사용자로 실행한다. Caddy와 Redis는 각 upstream 이미지의 실행 방식과 영속 볼륨 권한을 유지하되 외부에는 Caddy의 80·443 포트만 공개한다.

## 적용한 제한

- Dockerfile 기본 사용자: `app` (`10001:10001`)
- Compose 실행 사용자도 `10001:10001`로 고정
- 루트 파일시스템 read-only
- 쓰기가 필요한 임시 파일은 크기 제한 `tmpfs /tmp`만 사용
- Linux capability 전체 제거
- `no-new-privileges`로 setuid 등을 통한 권한 상승 차단
- PID 1 신호·좀비 처리를 위한 최소 init 사용
- Celery Beat schedule은 read-only 애플리케이션 경로가 아닌 `/tmp`에 저장

애플리케이션에 파일 업로드나 로컬 파일 저장 기능을 추가할 때 read-only 설정을 해제하지 않는다. 필요한 경로만 별도 볼륨으로 선언하고 소유자·크기·백업 정책을 함께 정의한다.

## 로컬 검증

```bash
docker build -t hakchelin-api:hardening-test backend

docker run --rm \
  --read-only \
  --tmpfs /tmp:size=64m,mode=1777 \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  hakchelin-api:hardening-test id

docker run --rm \
  --read-only \
  --tmpfs /tmp:size=64m,mode=1777 \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  hakchelin-api:hardening-test python manage.py check
```

`id`가 `uid=10001(app) gid=10001(app)`를 출력하고 Django check가 성공해야 한다.

## 운영 적용 후 점검

```bash
cd /opt/hakchelin
git pull --ff-only origin main

sudo docker compose --env-file /etc/hakchelin/compose.env \
  -f infra/lightsail/docker-compose.yml \
  up -d --build --force-recreate

sudo docker compose --env-file /etc/hakchelin/compose.env \
  -f infra/lightsail/docker-compose.yml \
  exec api id

sudo docker compose --env-file /etc/hakchelin/compose.env \
  -f infra/lightsail/docker-compose.yml \
  exec worker id

curl --fail https://api.hakchelin.cloud/healthz
```

API와 worker가 UID 10001로 표시되고 health check가 `{"status": "ok"}`를 반환해야 한다. Celery 로그에서 `superuser privileges` 경고가 사라졌는지도 확인한다.

## 롤백

권한 문제로 기동하지 못하면 이전 merge commit을 임시 배포해 서비스를 복구한다. 원인을 찾기 위해 컨테이너를 root로 상시 실행하는 변경은 하지 않는다. 쓰기 실패가 난 정확한 경로를 확인하고 해당 경로만 제한된 tmpfs 또는 볼륨으로 설계한 새 PR을 만든다.
