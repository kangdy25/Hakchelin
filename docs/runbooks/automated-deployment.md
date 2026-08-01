# GitHub Actions·Lightsail 자동 배포 런북

`main` push의 frontend·backend CI가 모두 성공하면 GitHub Actions가 Django 이미지를 GHCR에 두 태그로 발행한다.

- `sha-<40자리 commit>`: 운영 배포와 롤백에 사용하는 불변 태그
- `latest`: 사람이 최신 이미지를 찾기 위한 편의 태그이며 운영 배포에는 사용하지 않음

Lightsail에는 GitHub self-hosted runner를 두지 않는다. 저장소가 공개되어 있으므로 PR의 임의 코드가 운영 서버 runner에서 실행될 가능성을 없애고, 서버는 CI 성공 뒤에만 존재하는 SHA 이미지 태그를 pull한다.

## 최초 활성화

PR 병합 뒤 GitHub Actions의 `publish-api` job이 성공했는지 확인한다. GitHub Packages의 `hakchelin-api` package를 **Public**으로 바꾸면 Lightsail이 별도 장기 PAT 없이 이미지를 읽을 수 있다. 이미지에는 소스 저장소 label이 포함되어 package와 공개 저장소의 권한 관계를 명확히 한다.

서버에서 최신 main을 한 번 수동 반영하고 deploy·health timer를 설치한다.

```bash
sudo apt-get update
sudo apt-get install -y util-linux

cd /opt/hakchelin
git fetch origin
git switch main
git pull --ff-only origin main

sudo cp infra/lightsail/systemd/hakchelin-deploy.service /etc/systemd/system/
sudo cp infra/lightsail/systemd/hakchelin-deploy.timer /etc/systemd/system/
sudo cp infra/lightsail/systemd/hakchelin-healthcheck.service /etc/systemd/system/
sudo cp infra/lightsail/systemd/hakchelin-healthcheck.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hakchelin-deploy.timer hakchelin-healthcheck.timer
sudo systemctl start hakchelin-deploy.service
sudo systemctl start hakchelin-healthcheck.service
```

상태를 확인한다.

```bash
sudo systemctl status hakchelin-deploy.service --no-pager
sudo journalctl -u hakchelin-deploy.service --since "30 minutes ago" --no-pager
sudo cat /var/lib/hakchelin/api-image.env
curl --fail https://api.hakchelin.cloud/healthz
```

`api-image.env`에는 비밀값이 아니라 현재 배포된 SHA image만 들어간다. `/etc/hakchelin/backend.env`의 Django·Neon·Gemini·Toss 비밀값은 GitHub Actions나 GHCR로 전달하지 않는다.

systemd service는 root만 읽을 수 있는 `/etc/hakchelin` 환경 파일과 Docker socket에 접근하기 위해 root로 실행한다. 다만 Git 상태 확인·fetch·fast-forward는 `/opt/hakchelin`의 실제 소유자 권한으로 낮춰 실행한다. 저장소가 `ubuntu` 소유일 때 root Git의 dubious ownership 보호를 우회하지 않으며, 작업 트리·Git metadata와 hook을 root 권한으로 처리하지 않는다.

## 배포 흐름과 실패 처리

1. Vercel preview, frontend, backend CI가 성공한다.
2. Actions가 Linux amd64 이미지를 빌드하고 GHCR에 push하며 provenance를 발행한다.
3. Lightsail timer가 `origin/main` SHA의 정확한 image tag를 pull한다.
4. 로컬 변경이 없을 때만 저장소를 fast-forward한다.
5. migration → API·Celery → Caddy 순서로 Compose를 재기동한다.
6. 외부 HTTPS health를 최대 90초 확인한다.
7. 실패하면 이전 image로 컨테이너를 복원하고 실패 SHA를 기록한다.

같은 실패 SHA는 5분마다 반복 배포하지 않는다. 수정한 새 commit이 main에 병합되면 자동 배포를 다시 시도한다. DB migration은 되돌리지 않으므로 새 migration은 항상 직전 애플리케이션과 호환되게 단계적으로 작성한다.

배포 script는 `curl`, `docker`, `flock`, `git` 의존성을 시작 전에 확인한다. 하나라도 없으면 성공으로 오인하지 않고 즉시 실패한다.

## 수동 롤백

자동 롤백이 실패했을 때만 이전에 확인한 SHA 태그를 사용한다.

```bash
sudo sh -c 'printf "%s\n" "API_IMAGE=ghcr.io/kangdy25/hakchelin-api:sha-<검증된-이전-SHA>" > /var/lib/hakchelin/api-image.env'
sudo chmod 600 /var/lib/hakchelin/api-image.env

cd /opt/hakchelin
sudo docker compose \
  --env-file /etc/hakchelin/compose.env \
  --env-file /var/lib/hakchelin/api-image.env \
  -f infra/lightsail/docker-compose.yml \
  up -d --no-build --force-recreate
```

롤백 뒤 health와 핵심 기능을 확인하고 timer의 재시도를 막기 위해 실패 commit 기록을 보존한다. 원인 수정 PR이 병합되면 새 SHA가 자동으로 대상이 된다.
