# 🍱 학슐랭 (Hakchelin) - 대학생 맞춤형 스마트 학식 시스템

> **"기다림은 줄이고, 입맛은 맞추고, 잔반은 비우고!"**  
> 대학생 맞춤형 스마트 학식 시스템 학슐랭(Hakchelin)은 사전 예약 및 맞춤형 옵션 선택을 통해 학식 운영의 효율성을 극대화하고, 학생들에게 편리하고 개인화된 식사 경험을 제공하는 프로젝트입니다.


## ✨ 핵심 기능 (Key Features)

### 1. 스마트 사전 예약 및 차등 가격제
* **혼합 운영 체제**: 전체 식수의 90%를 사전 예약제로 운영하여 예측 가능한 조리 환경을 조성하고, 10%의 현장 결제를 지원합니다.
* **예약 유도 인센티브**: 사전 예약 활성화를 위해 현장 결제 시 추가 비용(500원~1,000원)이 책정됩니다.
* **노쇼(No-Show) 방지**: 예약금 제도(1,000원)를 도입하여 미취식 시 예약금을 제외한 금액만 환불함으로써 대기 시 손실을 최소화합니다.

### 2. 사용자 맞춤형 식단 옵션
* **수량 및 구성 커스텀**: 앱 내 주문 시 개인의 취향과 식사량에 맞춰 옵션을 선택할 수 있습니다. (예: 양 적게/많게, 고기 추가, 곱빼기 등)
* **부분 자율배식 연동**: 메인 메뉴는 위생과 정량 관리를 위해 직접 배식받고, 사이드 반찬은 잔반 감소를 위해 자율 배식하는 시스템과 연동됩니다.

### 3. 글로벌 지원 (Global Support)
* 외국인 학생들의 접근성과 편의성을 높이기 위해 **국문/영문 다국어 서비스**를 병행 지원합니다.

## 🛠 기술 스택 (Tech Stack)

본 프로젝트는 생산성이 높고 확장 가능한 모던 웹 기술 스택을 기반으로 구축되었습니다.

| 분류 | 기술 기술 | 설명 |
| :--- | :--- | :--- |
| **Frontend** | <img src="https://img.shields.io/badge/Nuxt.js-00DC82?style=flat-square&logo=Nuxt.js&logoColor=white"/> | Vue 3 기반의 프레임워크로, SSR/SSG 지원 및 뛰어난 SEO와 UI 개발 생산성 제공 |
| **Styling** | <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=Tailwind-CSS&logoColor=white"/> | 유틸리티 퍼스트 CSS 프레임워크를 활용하여 빠르고 일관된 반응형 UI 구현 |
| **Backend / DB** | <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=Supabase&logoColor=white"/> | 오픈소스 Firebase 대안(BaaS)으로, PostgreSQL 기반 실시간 데이터 연동 및 인증(Auth) 해결 |
| **Deployment** | <img src="https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=Vercel&logoColor=white"/> | Nuxt.js에 최적화된 글로벌 Edge 네트워크 기반의 서버리스 호스팅 및 자동 배포 |


## 🚀 향후 추진 및 해결 과제 (Roadmap)

- [ ] **학내 인프라 협의**
  * 지하식당 개방 및 스마트 학식 전용 배식 라인 구축을 위한 학교 측 미팅 진행
- [ ] **학사 시스템 연동 및 API 협의**
  * 채플 지연 등 갑작스러운 학사 일정 변동 시 후속 수업 시간과 학식 예약 시간이 유연하게 연동될 수 있도록 학사 운영팀과 기술적·행정적 협의 추진

---