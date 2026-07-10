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


@pytest.fixture
def mock_telegram_bot_service():
    with patch("app.routers.telegram.TelegramBotService.answer_callback_query", new_callable=AsyncMock) as mock_answer, \
         patch("app.routers.telegram.TelegramBotService.edit_message", new_callable=AsyncMock) as mock_edit:
        yield mock_answer, mock_edit


def test_telegram_webhook_approve_success(mock_telegram_bot_service):
    """텔레그램 웹훅을 통한 가입 승인 처리 E2E 테스트."""
    mock_answer, mock_edit = mock_telegram_bot_service
    timestamp = int(time.time() * 1000)
    username = f"tg_approve_{timestamp}"
    password = "password123"
    
    # 1. 가입 요청
    reg = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"approve_{timestamp}@ex.com"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    # 2. 승인 전 로그인 -> 403 (대기 중)
    login_before = client.post("/auth/login", data={"username": username, "password": password})
    assert login_before.status_code == 403
    assert "pending admin approval" in login_before.json()["detail"]

    # 3. 텔레그램 웹훅 승인 요청 발송
    webhook_payload = {
        "callback_query": {
            "id": "query_123",
            "from": {"id": 12345},
            "data": f"approve_{user_id}",
            "message": {"message_id": 999}
        }
    }
    
    with patch("app.routers.telegram.settings.TELEGRAM_WEBHOOK_SECRET", "secret123"), \
         patch("app.routers.telegram.settings.ADMIN_TELEGRAM_CHAT_ID", "12345"), \
         patch("app.routers.telegram.settings.TELEGRAM_BOT_TOKEN", "bot123"):
        response = client.post(
            "/auth/telegram/webhook",
            json=webhook_payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"}
        )
        
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert mock_answer.called
    assert mock_edit.called

    # 4. 승인 후 로그인 -> 200 (성공)
    login_after = client.post("/auth/login", data={"username": username, "password": password})
    assert login_after.status_code == 200
    assert "access_token" in login_after.json()


def test_telegram_webhook_reject_success(mock_telegram_bot_service):
    """텔레그램 웹훅을 통한 가입 거절 처리 E2E 테스트."""
    mock_answer, mock_edit = mock_telegram_bot_service
    timestamp = int(time.time() * 1000)
    username = f"tg_reject_{timestamp}"
    password = "password123"
    
    # 1. 가입 요청
    reg = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"reject_{timestamp}@ex.com"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    # 2. 텔레그램 웹훅 거절 요청 발송
    webhook_payload = {
        "callback_query": {
            "id": "query_124",
            "from": {"id": 12345},
            "data": f"reject_{user_id}",
            "message": {"message_id": 999}
        }
    }
    
    with patch("app.routers.telegram.settings.TELEGRAM_WEBHOOK_SECRET", "secret123"), \
         patch("app.routers.telegram.settings.ADMIN_TELEGRAM_CHAT_ID", "12345"), \
         patch("app.routers.telegram.settings.TELEGRAM_BOT_TOKEN", "bot123"):
        response = client.post(
            "/auth/telegram/webhook",
            json=webhook_payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"}
        )
        
    assert response.status_code == 200
    assert mock_answer.called
    assert mock_edit.called

    # 3. 거절 후 로그인 -> 403 (거절됨)
    login_after = client.post("/auth/login", data={"username": username, "password": password})
    assert login_after.status_code == 403
    assert "거절되었습니다" in login_after.json()["detail"]


def test_rejected_user_reregister(mock_telegram_bot_service):
    """거절된 유저의 재가입 E2E 테스트."""
    mock_answer, mock_edit = mock_telegram_bot_service
    timestamp = int(time.time() * 1000)
    username = f"tg_rereg_{timestamp}"
    password = "password123"
    
    # 1. 가입 및 거절 처리
    reg = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"rereg_{timestamp}@ex.com"},
    )
    user_id = reg.json()["id"]

    webhook_payload = {
        "callback_query": {
            "id": "query_125",
            "from": {"id": 12345},
            "data": f"reject_{user_id}",
            "message": {"message_id": 999}
        }
    }
    with patch("app.routers.telegram.settings.TELEGRAM_WEBHOOK_SECRET", "secret123"), \
         patch("app.routers.telegram.settings.ADMIN_TELEGRAM_CHAT_ID", "12345"):
        client.post(
            "/auth/telegram/webhook",
            json=webhook_payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"}
        )

    # 2. 동일 아이디로 재가입
    reg_again = client.post(
        "/auth/register",
        json={"username": username, "password": "newpassword123", "email": f"rereg_new_{timestamp}@ex.com"},
    )
    assert reg_again.status_code == 201
    
    # 3. 재가입 직후 로그인 시도 -> 403 (거절이 아닌 대기 중 상태로 초기화되었는지 검증)
    login_after = client.post("/auth/login", data={"username": username, "password": "newpassword123"})
    assert login_after.status_code == 403
    assert "pending admin approval" in login_after.json()["detail"]

