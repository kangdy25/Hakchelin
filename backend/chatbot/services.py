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
    today = timezone.localdate()
    menus = Menu.objects.filter(is_active=True, meal_date__gte=today).order_by("meal_date", "meal_time")[:10]
    reservations = Reservation.objects.filter(user=user).order_by("-created_at")[:10]
    menu_lines = [
        f"- {menu.meal_date} {menu.meal_time} {menu.title_ko} ({menu.price}P)"
        for menu in menus
    ]
    reservation_lines = [
        f"- {item.meal_date} {item.meal_time} {item.menu_snapshot.get('title_ko', '')} [{item.status}]"
        for item in reservations
    ]
    return "\n".join(
        [
            f"사용자: {user.name} / 보유 포인트: {user.current_point}P",
            "예정 메뉴:",
            *(menu_lines or ["- 없음"]),
            "최근 식권:",
            *(reservation_lines or ["- 없음"]),
        ]
    )


def generate_chat_answer(*, user, message: str, history: list[dict]) -> str:
    if not settings.GEMINI_API_KEY:
        return "로컬 Django 챗봇 연결이 정상입니다. Gemini API 키를 설정하면 메뉴와 식권을 바탕으로 답변합니다."

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
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
            params={"key": settings.GEMINI_API_KEY},
            json={
                "systemInstruction": {"parts": [{"text": prompt}]},
                "contents": contents,
            },
            timeout=20,
        )
        result = response.json()
        if response.is_error:
            error_message = result.get("error", {}).get("message") if isinstance(result, dict) else None
            raise ChatbotError(error_message or "Gemini 응답 생성에 실패했습니다.")
        answer = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (ChatbotError, httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        AiLog.objects.create(
            user=user,
            stage=AiLog.Stage.MAIN_CHAT,
            model=settings.GEMINI_MODEL,
            latency_ms=int((monotonic() - started_at) * 1000),
            status_code=502,
            error_message=str(error),
        )
        raise ChatbotError("챗봇 응답을 생성하지 못했습니다.") from error

    AiLog.objects.create(
        user=user,
        stage=AiLog.Stage.MAIN_CHAT,
        model=settings.GEMINI_MODEL,
        latency_ms=int((monotonic() - started_at) * 1000),
        status_code=200,
    )
    return answer
