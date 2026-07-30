import uuid
from datetime import date, datetime, time
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from django.test import override_settings
from rest_framework.test import APIClient

from legacy_bridge.authentication import SupabasePrincipal


def menu():
    return SimpleNamespace(
        id="1",
        day_of_week="mon",
        type="kr",
        title_ko="한식",
        title_en="Korean meal",
        price=4500,
        meal_date=date(2026, 8, 3),
        meal_time=time(12, 0),
        capacity=100,
        reservation_deadline=datetime(2026, 8, 3, 11, 0),
        deposit_amount=1000,
        is_active=True,
        created_at=datetime(2026, 7, 30, 0, 0),
    )


@patch("legacy_bridge.views.list_menus")
def test_menu_endpoint_uses_read_only_repository(list_menus):
    list_menus.return_value = [menu()]

    response = APIClient().get("/api/v1/menus/?active_only=true&from_date=2026-08-01")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "1"
    list_menus.assert_called_once_with(active_only=True, from_date="2026-08-01")


@patch("legacy_bridge.views.get_profile")
def test_profile_endpoint_scopes_legacy_lookup_to_authenticated_subject(get_profile):
    user_id = uuid.uuid4()
    get_profile.return_value = SimpleNamespace(
        id=user_id,
        role="student",
        student_id="20260001",
        name="학생",
        current_point=1000,
        created_at=datetime(2026, 7, 30, 0, 0),
    )
    client = APIClient()
    client.force_authenticate(user=SupabasePrincipal(id=user_id))

    response = client.get("/api/v1/me/")

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)
    get_profile.assert_called_once_with(user_id)


@override_settings(
    SUPABASE_JWT_SECRET="test-secret-with-at-least-32-bytes",
    SUPABASE_JWT_ISSUER="https://project.supabase.co/auth/v1",
    SUPABASE_JWT_AUDIENCE="authenticated",
)
@patch("legacy_bridge.views.get_profile")
def test_profile_endpoint_validates_supabase_bearer_token(get_profile):
    user_id = uuid.uuid4()
    token = jwt.encode(
        {"sub": str(user_id), "aud": "authenticated", "iss": "https://project.supabase.co/auth/v1"},
        "test-secret-with-at-least-32-bytes",
        algorithm="HS256",
    )
    get_profile.return_value = SimpleNamespace(
        id=user_id,
        role="student",
        student_id="20260001",
        name="학생",
        current_point=1000,
        created_at=datetime(2026, 7, 30, 0, 0),
    )

    response = APIClient().get("/api/v1/me/", HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 200
    get_profile.assert_called_once_with(user_id)
