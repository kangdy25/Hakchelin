import base64

import httpx
from django.conf import settings

from .services import PaymentError


def confirm_toss_payment(*, payment_key: str, order_id: str, amount: int) -> dict:
    """
    토스페이먼츠 최종 승인 API를 동기 HTTP 요청으로 호출합니다.

    시크릿 키 기반 Basic 인증, 네트워크 멱등키 헤더 주입, 10초 타임아웃 제한 및 장애 발생 시 도메인 예외 래핑을 수행합니다.
    """
    # 서버 환경 설정 검증: 토스 시크릿 키 존재 여부 확인
    if not settings.TOSS_PAYMENTS_SECRET_KEY:
        raise PaymentError("Toss Payments 비밀 키가 설정되지 않았습니다.")

    # 토스페이먼츠 Basic Auth 규격 생성
    credential = base64.b64encode(f"{settings.TOSS_PAYMENTS_SECRET_KEY}:".encode()).decode()

    try:
        # 토스 승인 API POST 요청
        response = httpx.post(
            settings.TOSS_PAYMENTS_CONFIRM_URL,
            headers={
                "Authorization": f"Basic {credential}",
                "Content-Type": "application/json",
                "Idempotency-Key": order_id,
            },
            json={"paymentKey": payment_key, "orderId": order_id, "amount": amount},
            timeout=10,
        )
        result = response.json()
    except (httpx.HTTPError, ValueError) as error:
        # 타임아웃, 커넥션 에러, DNS 오류, JSON 파싱 에러 등을 래핑하여 상위 계층에 전달
        raise PaymentError("Toss Payments 승인 서버에 연결하지 못했습니다.") from error

    # 토스 비즈니스 에러 응답 처리 (HTTP 4xx / 5xx)
    if response.is_error:
        message = result.get("message") if isinstance(result, dict) else None
        raise PaymentError(message or "Toss Payments 결제 승인에 실패했습니다.")
    return result
