import pytest
from django.test import override_settings


@pytest.mark.django_db
@override_settings(DJANGO_WRITE_BLOCKED=True)
def test_maintenance_mode_blocks_api_writes_but_allows_reads(client):
    blocked = client.post("/api/auth/login/", data={}, content_type="application/json")
    assert blocked.status_code == 503
    assert blocked.headers["Retry-After"] == "1800"
    assert client.get("/healthz").status_code == 200


@pytest.mark.django_db
@override_settings(DJANGO_WRITE_BLOCKED=True)
def test_maintenance_mode_does_not_block_non_api_posts(client):
    assert client.post("/admin/login/", data={}).status_code != 503
