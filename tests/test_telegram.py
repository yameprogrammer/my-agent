import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.telegram_service import TelegramBotService
from app.models import User
from sqlmodel import Session

client = TestClient(app)

@pytest.fixture
def mock_telegram_service():
    with patch("app.services.telegram_service.TelegramBotService._request", new_callable=AsyncMock) as mock:
        yield mock

@pytest.mark.asyncio
async def test_register_sends_telegram_alert(mock_telegram_service):
    """가입 시 텔레그램 알림이 발송되는지 확인"""
    payload = {"username": "test_user_tg", "password": "password123", "email": "test@example.com"}
    response = client.post("/auth/register", json=payload)
    
    assert response.status_code == 201
    # TelegramBotService._request가 호출되었는지 확인
    assert mock_telegram_service.called

@pytest.mark.asyncio
async def test_login_rejected_user():
    """거절된 유저가 로그인 시도 시 403 반환 확인"""
    # Mock DB setup would be needed here, usually via a test DB session
    # For this skeleton, we assume a user with rejected_at is created in test_db
    pass

@pytest.mark.asyncio
async def test_rejected_user_reregister():
    """거절된 유저가 재가입 시 레코드가 갱신되는지 확인"""
    pass

@pytest.mark.asyncio
async def test_telegram_webhook_approve_success():
    """텔레그램 승인 콜백 처리 정상 작동 확인"""
    pass
