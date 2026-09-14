from datetime import timedelta

import httpx
import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from chatbot.models import AiLog, ChatMessage
from chatbot.services import ChatbotError, stream_chat_answer
from chatbot.tasks import delete_expired_chat_messages
from meals.models import Menu
from reservations.models import Reservation
from wallet.models import PointTransaction


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/auth/csrf/")
    assert response.status_code == 200
    return client, client.cookies["csrftoken"].value


def login_client(user):
    client, csrf_token = csrf_client()
    response = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "correct-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return client, client.cookies["csrftoken"].value


def create_menu():
    return Menu.objects.create(
        title_ko="테스트 메뉴",
        title_en="Test meal",
        type=Menu.Type.KOREAN,
        meal_date=timezone.localdate() + timedelta(days=1),
        meal_time="12:00",
        reservation_deadline=timezone.now() + timedelta(hours=1),
    )


class FakeGeminiStreamResponse:
    """실제 네트워크 없이 httpx 스트리밍 응답 계약을 재현하는 테스트 대역."""

    def __init__(self, *, lines=(), is_error=False, payload=None):
        self.lines = lines
        self.is_error = is_error
        self.payload = payload or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b""

    def json(self):
        return self.payload

    def iter_lines(self):
        yield from self.lines


@pytest.mark.django_db
def test_login_requires_csrf_and_creates_session_cookie():
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    rejected = APIClient(enforce_csrf_checks=True).post(
        "/api/auth/login/",
        {"email": user.email, "password": "correct-password"},
        format="json",
    )
    assert rejected.status_code == 403

    client, _ = login_client(user)
    assert "sessionid" in client.cookies
    me = client.get("/api/me/")
    assert me.status_code == 200
    assert me.json()["id"] == str(user.id)


@pytest.mark.django_db
def test_signup_validates_duplicate_identity():
    User.objects.create_user(
        "existing@example.com",
        "correct-password",
        student_id="20260001",
        name="기존 학생",
    )
    client, csrf_token = csrf_client()
    response = client.post(
        "/api/auth/signup/",
        {
            "email": "new@example.com",
            "password": "correct-password",
            "student_id": "20260001",
            "name": "새 학생",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_authenticated_reservation_flow_is_user_scoped():
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
        current_point=10_000,
    )
    other = User.objects.create_user(
        "other@example.com",
        "correct-password",
        student_id="20260002",
        name="다른 학생",
        current_point=10_000,
    )
    menu = create_menu()
    client, csrf_token = login_client(user)

    created = client.post(
        "/api/reservations/",
        {"menu_id": menu.id, "options": {"main": 0, "rice": 1}, "total_price": 5_500},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert created.status_code == 201
    reservation_id = created.json()["id"]

    mine = client.get("/api/reservations/me/")
    assert [item["id"] for item in mine.json()] == [reservation_id]

    other_client, other_csrf = login_client(other)
    forbidden_cancel = other_client.post(
        f"/api/reservations/{reservation_id}/cancel/",
        format="json",
        HTTP_X_CSRFTOKEN=other_csrf,
    )
    assert forbidden_cancel.status_code == 400


@pytest.mark.django_db
def test_admin_api_enforces_role_and_ticket_actions():
    student = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
        current_point=10_000,
    )
    admin = User.objects.create_user(
        "admin@example.com",
        "correct-password",
        student_id="admin",
        name="관리자",
        role=User.Role.ADMIN,
    )
    menu = create_menu()
    reservation = Reservation.objects.create(
        user=student,
        menu=menu,
        options={},
        total_price=5_500,
        meal_date=menu.meal_date,
        meal_time=menu.meal_time,
        deposit_amount=menu.deposit_amount,
        menu_snapshot={},
    )

    student_client, _ = login_client(student)
    assert student_client.get("/api/admin/users/").status_code == 403

    admin_client, csrf_token = login_client(admin)
    used = admin_client.post(
        f"/api/admin/reservations/{reservation.id}/use/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert used.status_code == 200
    assert used.json()["status"] == Reservation.Status.USED


@pytest.mark.django_db
def test_chat_sse_contract_and_conversation_isolation(monkeypatch):
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    monkeypatch.setattr("api_views.stream_chat_answer", lambda **_kwargs: iter(["테스트 ", "답변"]))
    client, csrf_token = login_client(user)
    conversation_id = "05f35575-84df-4fef-a7f7-651899d3f760"
    response = client.post(
        "/api/chat/stream/",
        {"message": "오늘 메뉴 알려줘", "conversation_id": conversation_id},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    body = b"".join(response.streaming_content).decode()

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert body.count("event: token") == 2
    assert body.index("event: token") < body.index("event: done")
    assert ChatMessage.objects.filter(user=user, conversation_id=conversation_id).count() == 2
    assert ChatMessage.objects.get(user=user, role=ChatMessage.Role.ASSISTANT).content == "테스트 답변"

    history = client.get(f"/api/chat/{conversation_id}/")
    assert [item["role"] for item in history.json()] == ["user", "assistant"]


@pytest.mark.django_db
def test_chat_history_returns_latest_thirty_messages_in_chronological_order():
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    conversation_id = "05f35575-84df-4fef-a7f7-651899d3f760"
    for index in range(35):
        ChatMessage.objects.create(
            user=user,
            conversation_id=conversation_id,
            role=ChatMessage.Role.USER,
            content=f"메시지 {index}",
        )

    client, _ = login_client(user)
    response = client.get(f"/api/chat/{conversation_id}/")

    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == [f"메시지 {index}" for index in range(5, 35)]


@pytest.mark.django_db
def test_menu_list_rejects_invalid_from_date():
    response = APIClient().get("/api/menus/", {"from_date": "not-a-date"})

    assert response.status_code == 400
    assert "from_date" in response.json()


@pytest.mark.django_db
@override_settings(
    GEMINI_API_KEY="test-key",
    GEMINI_MODEL="gemini-3.6-flash",
    GEMINI_REQUEST_TIMEOUT_SECONDS=45,
)
def test_chat_streams_gemini_chunks_and_records_success(monkeypatch):
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    request_payload = {}

    response = FakeGeminiStreamResponse(
        lines=[
            'data: {"candidates":[{"content":{"parts":[{"text":"답"}]}}]}',
            'data: {"candidates":[{"content":{"parts":[{"text":"변"}]}}]}',
        ]
    )

    def fake_stream(method, url, **kwargs):
        request_payload["method"] = method
        request_payload["url"] = url
        request_payload.update(kwargs)
        return response

    monkeypatch.setattr("chatbot.services.httpx.stream", fake_stream)

    assert list(stream_chat_answer(user=user, message="오늘 메뉴 알려줘", history=[])) == ["답", "변"]
    assert request_payload["method"] == "POST"
    assert request_payload["url"].endswith("/models/gemini-3.6-flash:streamGenerateContent")
    assert request_payload["params"] == {"alt": "sse"}
    assert request_payload["headers"] == {"x-goog-api-key": "test-key"}
    assert "generationConfig" not in request_payload["json"]
    assert request_payload["timeout"] == 45
    assert AiLog.objects.filter(user=user, status_code=200).count() == 1


@pytest.mark.django_db
def test_chat_midstream_failure_does_not_persist_an_unpaired_message(monkeypatch):
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    client, csrf_token = login_client(user)

    def failing_stream(**_kwargs):
        yield "부분 답변"
        raise ChatbotError("챗봇 응답을 생성하지 못했습니다.")

    monkeypatch.setattr("api_views.stream_chat_answer", failing_stream)

    response = client.post(
        "/api/chat/stream/",
        {"message": "두 번째 질문", "conversation_id": "05f35575-84df-4fef-a7f7-651899d3f760"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    body = b"".join(response.streaming_content).decode()
    assert body.index("event: token") < body.index("event: error")
    assert "event: done" not in body
    assert "event: error" in body
    assert 'data: {"message": "챗봇 응답을 생성하지 못했습니다."}' in body
    assert not ChatMessage.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_chat_client_disconnect_does_not_persist_partial_answer(monkeypatch):
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    monkeypatch.setattr("api_views.stream_chat_answer", lambda **_kwargs: iter(["첫 조각", "두 번째 조각"]))
    client, csrf_token = login_client(user)
    response = client.post(
        "/api/chat/stream/",
        {"message": "질문", "conversation_id": "05f35575-84df-4fef-a7f7-651899d3f760"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    iterator = response.streaming_content
    assert b"event: token" in next(iterator)
    # 첫 조각만 받은 상태에서 브라우저 연결이 종료되는 상황을 재현한다.
    response.close()

    assert not ChatMessage.objects.filter(user=user).exists()


@pytest.mark.django_db
@override_settings(GEMINI_API_KEY="")
def test_chat_stream_requires_gemini_api_key():
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )

    with pytest.raises(ChatbotError, match="챗봇 응답을 생성하지 못했습니다"):
        list(stream_chat_answer(user=user, message="질문", history=[]))

    assert AiLog.objects.filter(user=user, status_code=502).count() == 1


@pytest.mark.django_db
@override_settings(GEMINI_API_KEY="test-key")
@pytest.mark.parametrize(
    "response",
    [
        FakeGeminiStreamResponse(is_error=True, payload={"error": {"message": "요청 실패"}}),
        FakeGeminiStreamResponse(lines=["data: not-json"]),
        FakeGeminiStreamResponse(lines=[]),
    ],
    ids=["http-error", "invalid-json", "empty-response"],
)
def test_chat_stream_converts_gemini_failures_to_domain_error(monkeypatch, response):
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    monkeypatch.setattr("chatbot.services.httpx.stream", lambda *_args, **_kwargs: response)

    with pytest.raises(ChatbotError, match="챗봇 응답을 생성하지 못했습니다"):
        list(stream_chat_answer(user=user, message="질문", history=[]))

    assert AiLog.objects.filter(user=user, status_code=502).count() == 1


@pytest.mark.django_db
@override_settings(GEMINI_API_KEY="test-key")
def test_chat_stream_converts_network_failure_to_domain_error(monkeypatch):
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )

    def fail_to_connect(*_args, **_kwargs):
        raise httpx.ConnectError("network unavailable")

    monkeypatch.setattr("chatbot.services.httpx.stream", fail_to_connect)

    with pytest.raises(ChatbotError, match="챗봇 응답을 생성하지 못했습니다"):
        list(stream_chat_answer(user=user, message="질문", history=[]))

    assert AiLog.objects.filter(user=user, status_code=502).count() == 1


@pytest.mark.django_db
def test_point_payment_calls_toss_once_and_is_idempotent(monkeypatch):
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    client, csrf_token = login_client(user)
    created = client.post(
        "/api/payments/point-orders/",
        {"amount": 5000},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    calls = []
    monkeypatch.setattr(
        "api_views.confirm_toss_payment",
        lambda **payload: calls.append(payload) or {"status": "DONE"},
    )
    payload = {
        "payment_key": "payment-key",
        "order_id": created.json()["order_id"],
        "amount": 5000,
    }

    first = client.post(
        "/api/payments/point-orders/confirm/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    second = client.post(
        "/api/payments/point-orders/confirm/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    user.refresh_from_db()
    assert first.status_code == second.status_code == 200
    assert len(calls) == 1
    assert user.current_point == 5000
    assert PointTransaction.objects.filter(user=user, type="charge").count() == 1


@pytest.mark.django_db
def test_chat_messages_older_than_seven_days_are_deleted():
    user = User.objects.create_user(
        "student@example.com",
        "correct-password",
        student_id="20260001",
        name="학생",
    )
    old = ChatMessage.objects.create(
        user=user,
        conversation_id="05f35575-84df-4fef-a7f7-651899d3f760",
        role=ChatMessage.Role.USER,
        content="오래된 메시지",
    )
    ChatMessage.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(days=8))
    ChatMessage.objects.create(
        user=user,
        conversation_id="05f35575-84df-4fef-a7f7-651899d3f760",
        role=ChatMessage.Role.ASSISTANT,
        content="최근 메시지",
    )

    assert delete_expired_chat_messages() == 1
    assert list(ChatMessage.objects.values_list("content", flat=True)) == ["최근 메시지"]
