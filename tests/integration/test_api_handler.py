import uuid

from fastapi import status
from fastapi.testclient import TestClient


def _create_client():
    from app.api_handler import app

    return TestClient(app, raise_server_exceptions=False)


def test_health_check_returns_healthy_status():
    client = _create_client()

    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


def test_unhandled_exception_returns_internal_server_error_when_debug_is_disabled(
    monkeypatch,
):
    from app import settings
    from app.api_handler import app

    route_path = f"/__test-boom-no-debug-{uuid.uuid4()}"

    @app.get(route_path)
    def raise_unhandled_error():
        raise RuntimeError("test boom")

    monkeypatch.setattr(settings, "debug", False)
    client = _create_client()

    response = client.get(route_path)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == "Internal Server Error"


def test_unhandled_exception_returns_error_message_when_debug_is_enabled(monkeypatch):
    from app import settings
    from app.api_handler import app

    route_path = f"/__test-boom-debug-{uuid.uuid4()}"

    @app.get(route_path)
    def raise_unhandled_error():
        raise RuntimeError("test boom")

    monkeypatch.setattr(settings, "debug", True)
    client = _create_client()

    response = client.get(route_path)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == "test boom"
