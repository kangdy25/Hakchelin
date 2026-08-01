# Hakchelin 도메인 라우팅 런북

서비스의 canonical URL은 `https://hakchelin.cloud`다. 프런트는 Vercel, API는 Lightsail/Caddy로 분리한다.

| 호스트 | DNS | 목적 |
| --- | --- | --- |
| `hakchelin.cloud` | Vercel 권장 A | Nuxt production |
| `www.hakchelin.cloud` | Vercel 권장 CNAME | apex로 308 영구 redirect |
| `api.hakchelin.cloud` | Lightsail Static IP A | Django/Caddy API |

## Vercel 설정

Hakchelin project의 Domains에는 다음 구성이 있어야 한다.

- `hakchelin.cloud`: production domain
- `www.hakchelin.cloud`: `hakchelin.cloud`로 redirect, status `308`
- `smart-campus-meal.vercel.app`: 기존 URL 호환 redirect

Vercel domain redirect는 애플리케이션 Nuxt route보다 앞에서 처리한다. `308`은 영구 redirect이면서 HTTP method를 보존하므로 canonical host 정책을 명확히 하고 중복 콘텐츠를 피한다.

## 가비아 DNS

Vercel config API가 제시한 우선순위 1 값을 사용한다.

```text
Type:  CNAME
Host:  www
Value: 79c72787ec396ec2.vercel-dns-017.com
TTL:   1800
```

기존 apex `@`와 API `api` 레코드는 수정하지 않는다. CNAME 값 끝의 점은 가비아 UI에서 생략해도 된다. Vercel이 향후 권장값 변경을 표시하면 Dashboard의 현재 값을 우선한다.

## 검증

DNS 전파와 인증서 발급 뒤 저장소의 점검을 실행한다.

```bash
infra/lightsail/scripts/verify-domain-routing.sh
```

완료 조건은 다음과 같다.

1. `https://hakchelin.cloud/`가 정상 응답한다.
2. `https://www.hakchelin.cloud/`가 HTTP 308을 반환한다.
3. `Location`이 정확히 `https://hakchelin.cloud/`다.
4. GitHub Actions `Production health`가 15분마다 같은 계약을 확인한다.

브라우저 cache 때문에 이전 redirect가 보이면 시크릿 창이나 curl로 먼저 판별한다. DNS와 TLS가 정상인데 redirect 대상만 틀렸다면 Vercel Project Settings → Domains의 `www` redirect를 수정한다.

레코드 추가 직후 public DNS에는 보이지만 로컬 OS resolver가 이전 NXDOMAIN을 잠시 유지할 수 있다. 이 경우 가비아 레코드를 반복 수정하지 말고 `dig`로 authoritative/public resolver를 확인한 뒤 TTL 동안 기다린다.
