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


def generate_chat_answer(*, user, message: str, history: list[dict]) -> str:
    """
    사용자 질의 및 이전 대화 내역을 바탕으로 Google Gemini REST API를 호출하여 답변을 생성합니다.

    사용자 맞춤 DB 컨텍스트를 시스템 프롬프트로 주입하며, 왕복 레이턴시와
    성공/실패 여부를 AiLog 테이블에 기록합니다.
    """
    if not settings.GEMINI_API_KEY:
        # 외부 호출을 시도하지 않고 클라이언트가 처리할 수 있는 서비스 오류로 변환
        raise ChatbotError("AI 서비스 연동 설정이 완료되지 않았습니다. 관리자에게 문의해주세요.")

    # 정확한 네트워크/추론 지연 시간 계측 시작 (시스템 시계 변동 영향이 없는 monotonic 사용)
    started_at = monotonic()
    # 이전 대화 기록을 Gemini API의 메시지 규격으로 변환 
    # 토큰 절약 및 컨텍스트 길이 초과 방지를 위해 최근 10개 턴만 전송
    contents = [
        {
            "role": "user" if item["role"] == "user" else "model",
            "parts": [{"text": item["content"]}],
        }
        for item in history[-10:]
    ]
    # 사용자의 이번 턴 신규 메시지 추가
    contents.append({"role": "user", "parts": [{"text": message}]})

    # 페르소나 및 데이터 한정 가드레일 프롬프트 구성 (Grounding)
    prompt = (
        "학슐랭의 한국어 식사 도우미다. 제공된 사용자 데이터 안에서만 정확하고 간결하게 답한다. "
        "다른 사용자의 정보는 추측하지 않는다.\n\n"
        f"{_user_context(user)}"
    )
    try:
        # Gemini generateContent 엔드포인트 동기 HTTP POST 호출
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
            params={"key": settings.GEMINI_API_KEY},
            json={
                "systemInstruction": {"parts": [{"text": prompt}]},
                "contents": contents,
            },
            timeout=settings.GEMINI_REQUEST_TIMEOUT_SECONDS,
        )
        result = response.json()
        # HTTP 에러 상태 코드 응답 시 상세 실패 메시지 추출
        if response.is_error:
            error_message = result.get("error", {}).get("message") if isinstance(result, dict) else None
            raise ChatbotError(error_message or "Gemini 응답 생성에 실패했습니다.")
        # Gemini 응답 구조(candidates -> content -> parts -> text) 파싱 및 양끝 공백 제거
        answer = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (ChatbotError, httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        # 예외 발생 시 관측성(Observability) 실패 로그 적재 (502 Bad Gateway 기준)
        AiLog.objects.create(
            user=user,
            stage=AiLog.Stage.MAIN_CHAT,
            model=settings.GEMINI_MODEL,
            latency_ms=int((monotonic() - started_at) * 1000),
            status_code=502,
            error_message=str(error),
        )
        raise ChatbotError("챗봇 응답을 생성하지 못했습니다.") from error

    # 추론 성공 시 지연 시간 및 200 상태 코드를 AiLog에 기록
    AiLog.objects.create(
        user=user,
        stage=AiLog.Stage.MAIN_CHAT,
        model=settings.GEMINI_MODEL,
        latency_ms=int((monotonic() - started_at) * 1000),
        status_code=200,
    )
    return answer
