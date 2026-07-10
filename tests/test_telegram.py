import time
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_telegram_request():
    with patch(
        "app.services.telegram_service.TelegramBotService._request",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = {"ok": True}
        yield mock


def test_register_sends_telegram_alert(mock_telegram_request):
    """가입 시 텔레그램 알림이 발송되는지 확인 (토큰 설정 + 고유 username)."""
    timestamp = int(time.time() * 1000)
    payload = {
        "username": f"tg_user_{timestamp}",
        "password": "password123",
        "email": f"tg_{timestamp}@example.com",
    }
    with patch("app.routers.auth.settings.TELEGRAM_BOT_TOKEN", "test-bot-token"), \
         patch("app.routers.auth.settings.ADMIN_TELEGRAM_CHAT_ID", "12345"):
        response = client.post("/auth/register", json=payload)

    assert response.status_code == 201, response.text
    assert mock_telegram_request.called


def test_login_pending_inactive_returns_403():
    """미승인(is_active=False) 계정 로그인 시 403."""
    timestamp = int(time.time() * 1000)
    username = f"pending_{timestamp}"
    password = "password123"
    reg = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"p_{timestamp}@ex.com"},
    )
    assert reg.status_code == 201
    login = client.post("/auth/login", data={"username": username, "password": password})
    assert login.status_code == 403


def test_rejected_user_reregister():
    """거절된 유저 재가입 스켈레톤 — 향후 webhook E2E 로 확장."""
    pass


def test_telegram_webhook_approve_success():
    """텔레그램 승인 콜백 스켈레톤 — 향후 secret+callback E2E 로 확장."""
    pass
