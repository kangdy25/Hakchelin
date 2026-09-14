import json
from collections.abc import Iterator
from time import monotonic

import httpx
from django.conf import settings
from django.utils import timezone

from meals.models import Menu
from reservations.models import Reservation

from .models import AiLog


class ChatbotError(RuntimeError):
    pass


def _user_context(user) -> str:
    """
    LLM 프롬프트에 주입할 질문 사용자의 동적 컨텍스트(포인트, 예정 식단, 식권 이력)를 생성합니다.

    벡터 DB 없이 관계형 DB의 최신 데이터를 직접 조회하여 프롬프트의 Grounding(근거) 데이터로 사용합니다.
    """
    today = timezone.localdate()
    # 오늘 이후 제공 예정인 활성 메뉴 최대 10건 조회
    menus = Menu.objects.filter(is_active=True, meal_date__gte=today).order_by("meal_date", "meal_time")[:10]
    # 사용자의 최근 예약/식권 이력 최대 10건 조회 (N+1 방지를 위해 스냅샷 활용)
    reservations = Reservation.objects.filter(user=user).order_by("-created_at")[:10]
    # 프롬프트 주입용 텍스트 라인 구성
    menu_lines = [
        f"- {menu.meal_date} {menu.meal_time} {menu.title_ko} ({menu.price}P)"
        for menu in menus
    ]
    reservation_lines = [
        f"- {item.meal_date} {item.meal_time} {item.menu_snapshot.get('title_ko', '')} [{item.status}]"
        for item in reservations
    ]
    # 사용자 계정 잔액, 식단, 식권 현황 결합
    return "\n".join(
        [
            f"사용자: {user.name} / 보유 포인트: {user.current_point}P",
            "예정 메뉴:",
            *(menu_lines or ["- 없음"]),
            "최근 식권:",
            *(reservation_lines or ["- 없음"]),
        ]
    )


def stream_chat_answer(*, user, message: str, history: list[dict]) -> Iterator[str]:
    """
    사용자 질의와 이전 대화 내역을 Gemini에 전달하고 생성되는 텍스트 조각을 반환합니다.

    사용자 맞춤 DB 컨텍스트를 시스템 프롬프트로 주입하고 스트림 전체의 지연 시간과
    성공 또는 실패 결과를 AiLog 테이블에 한 건 기록합니다.
    """
    started_at = monotonic()
    contents = [
        {
            "role": "user" if item["role"] == "user" else "model",
            "parts": [{"text": item["content"]}],
        }
        for item in history[-10:]
    ]
    contents.append({"role": "user", "parts": [{"text": message}]})

    prompt = (
        "학슐랭의 한국어 식사 도우미다. 제공된 사용자 데이터 안에서만 정확하고 간결하게 답한다. "
        "다른 사용자의 정보는 추측하지 않는다.\n\n"
        f"{_user_context(user)}"
    )
    try:
        # 설정 누락도 외부 API 장애와 동일하게 실패 로그 한 건으로 추적한다.
        if not settings.GEMINI_API_KEY:
            raise ChatbotError("AI 서비스 연동 설정이 완료되지 않았습니다.")

        has_text = False
        # Gemini REST 스트리밍은 응답을 SSE로 받기 위해 alt=sse가 필요하다.
        # API 키는 URL이나 로그에 노출될 가능성을 줄이기 위해 전용 헤더로 전달한다.
        with httpx.stream(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:streamGenerateContent",
            params={"alt": "sse"},
            headers={"x-goog-api-key": settings.GEMINI_API_KEY},
            json={
                "systemInstruction": {"parts": [{"text": prompt}]},
                "contents": contents,
            },
            timeout=settings.GEMINI_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            if response.is_error:
                # 스트리밍 응답은 본문을 명시적으로 읽은 뒤에만 JSON 오류 내용을 파싱할 수 있다.
                response.read()
                result = response.json()
                error_message = result.get("error", {}).get("message") if isinstance(result, dict) else None
                raise ChatbotError(error_message or "Gemini 응답 생성에 실패했습니다.")

            # Gemini가 보내는 각 SSE 레코드의 `data:` JSON에서 텍스트 조각만 추출한다.
            # 메타데이터만 담긴 레코드나 빈 줄은 사용자에게 token 이벤트로 전달하지 않는다.
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                raw_data = line.removeprefix("data:").strip()
                if not raw_data:
                    continue
                result = json.loads(raw_data)
                parts = result["candidates"][0]["content"].get("parts", [])
                for part in parts:
                    text = part.get("text")
                    if not isinstance(text, str) or not text:
                        continue
                    has_text = has_text or bool(text.strip())
                    yield text

        if not has_text:
            raise ChatbotError("Gemini가 비어 있는 응답을 반환했습니다.")
    except (AttributeError, ChatbotError, httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        # 이미 일부 조각이 전달된 뒤라도 View가 동일한 error 이벤트로 마무리할 수 있도록
        # 네트워크 오류와 응답 형식 오류를 하나의 도메인 예외로 변환한다.
        AiLog.objects.create(
            user=user,
            stage=AiLog.Stage.MAIN_CHAT,
            model=settings.GEMINI_MODEL,
            latency_ms=int((monotonic() - started_at) * 1000),
            status_code=502,
            error_message=str(error),
        )
        raise ChatbotError("챗봇 응답을 생성하지 못했습니다.") from error

    # generator가 끝까지 소비된 경우에만 성공으로 기록한다. 클라이언트가 중간에
    # 연결을 끊어 generator가 닫히면 이 지점에 도달하지 않는다.
    AiLog.objects.create(
        user=user,
        stage=AiLog.Stage.MAIN_CHAT,
        model=settings.GEMINI_MODEL,
        latency_ms=int((monotonic() - started_at) * 1000),
        status_code=200,
    )
