# Django 마이그레이션 트러블슈팅 일지

학슐랭의 Nuxt·Supabase 구조를 Django·Neon 구조로 전환하며 발견한 문제와 해결 과정을 기록한다. 각 항목은 포트폴리오에서 설계 판단과 검증 방법을 설명하기 위한 근거다.

## 1단계 — 모노레포 전환 뒤 Vercel 빌드 실패

### 증상

Nuxt를 `frontend/`로 이동한 뒤 PR 미리보기 배포가 `nuxt: command not found`로 실패했다.

### 원인

Vercel 프로젝트의 Root Directory가 저장소 루트로 남아 있었다. Vercel은 루트의 workspace 의존성은 설치했지만, 루트에서 기존 `nuxt build` 명령을 실행해 Nuxt 바이너리를 찾지 못했다.

### 해결

Vercel 프로젝트 설정의 Root Directory를 `frontend`로 변경했다. 이후 Preview 배포가 성공했고, Vercel은 프런트 패키지의 Nuxt 설정을 기준으로 빌드했다.

### 배운 점

모노레포 전환은 파일 이동만으로 끝나지 않는다. CI, 호스팅 플랫폼의 작업 디렉터리, 패키지 관리자 workspace 경계를 하나의 변경 단위로 검증해야 한다.

## 1단계 — CI에서만 Nuxt 타입 검사가 실패

### 증상

로컬에서는 `nuxt typecheck`가 통과했지만 GitHub Actions에서는 `vue-tsc`가 TypeScript 6과 호환되지 않아 실패했다.

### 원인

`frontend` 패키지에 `vue-tsc`와 호환되는 TypeScript 버전이 직접 선언되지 않았다. CI는 이를 임시 설치하면서 workspace의 TypeScript 6을 해석했고, 로컬 캐시와 다른 의존성 그래프가 만들어졌다.

### 해결

`frontend/package.json`에 `typescript` 5.x와 `vue-tsc`를 명시하고 lockfile을 갱신했다. 이후 로컬과 CI가 같은 도구 체인을 사용하도록 고정했다.

### 배운 점

개발 도구도 패키지의 직접 의존성으로 선언해야 한다. 특히 타입 검사 도구를 전역 설치나 npx 자동 설치에 맡기면 CI 재현성이 약해진다.

## 2단계 — Codex 실행 환경의 GitHub CLI 인증 불일치

### 증상

사용자 터미널에서는 GitHub CLI 로그인이 성공했지만, 제한된 실행 환경에서는 기존의 만료된 토큰이 계속 보였다.

### 원인

샌드박스가 호스트의 keyring 기반 인증 정보를 직접 읽지 못했다.

### 해결

호스트 권한으로 GitHub CLI를 실행해 keyring 인증을 확인한 뒤 PR 생성·검사 확인·merge commit 병합을 수행했다.

### 배운 점

로컬 개발 환경에서는 셸, 샌드박스, 호스트 keyring의 자격 증명 범위가 다를 수 있다. 인증 실패 시 토큰을 재발급하기 전에 어느 실행 경계에서 실패하는지 먼저 확인해야 한다.
