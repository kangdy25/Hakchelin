import base64

import httpx
from django.conf import settings

from .services import PaymentError


def confirm_toss_payment(*, payment_key: str, order_id: str, amount: int) -> dict:
    if not settings.TOSS_PAYMENTS_SECRET_KEY:
        raise PaymentError("Toss Payments 비밀 키가 설정되지 않았습니다.")

    credential = base64.b64encode(f"{settings.TOSS_PAYMENTS_SECRET_KEY}:".encode()).decode()
    try:
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
        raise PaymentError("Toss Payments 승인 서버에 연결하지 못했습니다.") from error

    if response.is_error:
        message = result.get("message") if isinstance(result, dict) else None
        raise PaymentError(message or "Toss Payments 결제 승인에 실패했습니다.")
    return result
