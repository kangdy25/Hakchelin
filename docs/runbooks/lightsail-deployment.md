# Lightsail 운영 배포 런북

이 문서는 `hakchelin.cloud`의 Django API를 Lightsail에 안전하게 올리는 절차다. 프런트는 Vercel, API는 `api.hakchelin.cloud`, 데이터베이스는 Neon을 사용한다.

## 1. 배포 전제

- Lightsail 인스턴스: Seoul, Ubuntu 24.04, 최소 2GB RAM, Static IP 연결
- Lightsail 방화벽: TCP 80/443 공개, TCP 22는 운영자 IP만 허용. 8000과 6379는 열지 않는다.
- DNS: `api.hakchelin.cloud`의 A 레코드를 Lightsail Static IP로 연결한다. Caddy가 Let's Encrypt 인증서를 받으므로 DNS 전파 뒤에 컨테이너를 올린다.
- Vercel: `hakchelin.cloud`를 production domain으로 연결하고 `NUXT_PUBLIC_API_BASE_URL=https://api.hakchelin.cloud`를 설정한다.

## 2. 서버 최초 준비

로컬에서 SSH 키 권한을 제한한다.

```bash
chmod 600 LightsailDefaultKey-ap-northeast-2.pem
ssh -i LightsailDefaultKey-ap-northeast-2.pem ubuntu@<STATIC_IP>
```

서버에서 Docker를 설치하고 배포 디렉터리를 만든다.

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo mkdir -p /opt/hakchelin /etc/hakchelin
sudo chown -R ubuntu:ubuntu /opt/hakchelin
git clone https://github.com/kangdy25/Hakchelin.git /opt/hakchelin
```

`/etc/hakchelin/backend.env`는 소유자만 읽을 수 있어야 하며 저장소에 두지 않는다.

```dotenv
DJANGO_SECRET_KEY=<openssl rand -base64 48 결과>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=api.hakchelin.cloud
DATABASE_URL=<Neon production pooler URL, sslmode=require>
DATABASE_CONN_MAX_AGE=0
DJANGO_WRITE_BLOCKED=false
DJANGO_CORS_ALLOWED_ORIGINS=https://hakchelin.cloud,https://www.hakchelin.cloud
DJANGO_CSRF_TRUSTED_ORIGINS=https://hakchelin.cloud,https://www.hakchelin.cloud
DJANGO_CSRF_COOKIE_DOMAIN=.hakchelin.cloud
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true
DJANGO_SECURE_HSTS_PRELOAD=false
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
TOSS_PAYMENTS_SECRET_KEY=<production key>
GEMINI_API_KEY=<production key>
GEMINI_MODEL=gemini-3.6-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=45
```

```bash
sudo chmod 600 /etc/hakchelin/backend.env
sudo tee /etc/hakchelin/compose.env >/dev/null <<'EOF'
API_HOST=api.hakchelin.cloud
API_IMAGE=hakchelin-api:production
BACKEND_ENV_FILE=/etc/hakchelin/backend.env
EOF
sudo chmod 600 /etc/hakchelin/compose.env
```

## 3. 배포와 확인

```bash
cd /opt/hakchelin
git fetch origin
git switch main
git pull --ff-only origin main
sudo docker compose --env-file /etc/hakchelin/compose.env -f infra/lightsail/docker-compose.yml up -d --build
sudo docker compose --env-file /etc/hakchelin/compose.env -f infra/lightsail/docker-compose.yml ps
curl --fail https://api.hakchelin.cloud/healthz
```

`migrate` 컨테이너는 매 배포에서 Django migration을 한 번만 적용하고 종료한다. `api`, `worker`, `beat`는 migration 성공 뒤에만 시작한다. 장애 분석은 아래 명령으로 한다.

API health check는 컨테이너 내부 HTTP로 `/healthz`를 호출하되, 실제 Caddy 요청과 동일하게 첫 번째 `DJANGO_ALLOWED_HOSTS` 값을 `Host`로 사용하고 `X-Forwarded-Proto: https`를 보낸다. 따라서 운영 HTTPS redirect를 켠 상태에서도 내부 점검이 200 응답을 받을 수 있다.

```bash
sudo docker compose --env-file /etc/hakchelin/compose.env -f infra/lightsail/docker-compose.yml logs --tail=100 api migrate caddy
```

## 4. 운영 검증과 롤백

1. 브라우저에서 회원가입·로그인 뒤 `api.hakchelin.cloud`의 `sessionid`는 HttpOnly·Secure, `csrftoken`은 `.hakchelin.cloud` 범위인지 확인한다.
2. 예약·취소와 관리자 API 변경 요청이 CSRF 헤더 없이 403, 정상 웹 요청에서는 성공하는지 확인한다.
3. `/healthz`, `/api/schema/`, 챗봇 SSE, Celery Beat 로그를 점검한다.
4. 문제가 있으면 이전 main 커밋을 checkout해 같은 `docker compose up -d --build`를 실행한다. DB migration은 되돌리지 않으며, 데이터 복원은 검증된 Neon 백업 절차로만 수행한다.

Supabase Auth/RLS/RPC/Edge Function 삭제는 운영 검증 및 백업 복원 리허설이 끝난 뒤 별도 승인으로 수행한다.
