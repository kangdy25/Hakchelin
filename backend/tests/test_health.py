from django.test import Client


def test_healthz_returns_ok():
    response = Client().get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_available():
    response = Client().get("/api/schema/")

    assert response.status_code == 200
    assert b"cookieAuth" in response.content
    assert b"/api/auth/login/" in response.content
    assert b"/api/reservations/" in response.content
    assert b"SupabaseJWT" not in response.content
