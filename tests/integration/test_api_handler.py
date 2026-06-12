import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestApiHandler:
    @pytest.fixture
    def test_client(self) -> TestClient:
        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=False)

    def test_health_check_returns_healthy_status(self, test_client: TestClient):
        response = test_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}

    def test_unhandled_exception_returns_internal_server_error_when_debug_is_disabled(
        self, test_client: TestClient, monkeypatch
    ):
        from app import settings
        from app.api_handler import app

        route_path = f"/__test-boom-no-debug-{uuid.uuid4()}"

        @app.get(route_path)
        def raise_unhandled_error():
            raise RuntimeError("test boom")

        monkeypatch.setattr(settings, "debug", False)

        response = test_client.get(route_path)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["error"] == "Internal Server Error"

    def test_unhandled_exception_returns_error_message_when_debug_is_enabled(
        self, test_client: TestClient, monkeypatch
    ):
        from app import settings
        from app.api_handler import app

        route_path = f"/__test-boom-debug-{uuid.uuid4()}"

        @app.get(route_path)
        def raise_unhandled_error():
            raise RuntimeError("test boom")

        monkeypatch.setattr(settings, "debug", True)

        response = test_client.get(route_path)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["error"] == "test boom"

    def test_unknown_route_returns_404(self, test_client: TestClient):
        response = test_client.get("/api/v1/nonexistent-route")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        body = response.json()
        # Starlette default 404 returns {"detail": "Not Found"}
        assert body.get("detail") == "Not Found" or body.get("error") == "Not Found"
