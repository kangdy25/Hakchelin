from django.test import Client


def test_healthz_returns_ok():
    response = Client().get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_available():
    response = Client().get("/api/schema/")

    assert response.status_code == 200
    assert b"SupabaseJWT" in response.content
