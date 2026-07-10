import logging
import httpx
from typing import Optional, Any, Dict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class TelegramBotService:
    """텔레그램 Bot API를 통한 관리자 알림 서비스.
    
    모든 외부 API 호출은 async/await + httpx.AsyncClient 패턴으로 구현하여
    프로젝트의 Async Only 규칙을 준수한다.
    """
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    TIMEOUT = 10.0  # 초
    MAX_RETRIES = 2
    
    def __init__(self, token: str, admin_chat_id: str):
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.api_url = self.BASE_URL.format(token=token)

    async def _request(self, method: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """내부 API 호출 헬퍼. 실패 시 None 반환 (best-effort)."""
        url = f"{self.api_url}/{method}"
        # 재시도 루프 밖에서 클라이언트를 생성하여 커넥션 풀을 재사용함
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            for attempt in range(self.MAX_RETRIES + 1):
                try:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPError as e:
                    logger.warning(
                        "Telegram API 호출 실패 (시도 %d/%d): %s %s",
                        attempt + 1, self.MAX_RETRIES + 1, method, e
                    )
        logger.error("Telegram API 최종 실패: %s", method)
        return None

    async def send_registration_alert(self, user: Any) -> None:
        """가입 알림 + 인라인 키보드 발송"""
        # UTC 시간을 KST(+9)로 변환
        kst_time = "알 수 없음"
        if user.created_at:
            utc_dt = user.created_at
            if utc_dt.tzinfo is None:
                utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            kst_dt = utc_dt.astimezone(timezone(timedelta(hours=9)))
            kst_time = kst_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        text = (
            "📋 새로운 가입 요청\n\n"
            f"👤 사용자명: {user.username}\n"
            f"📧 이메일: {user.email or '미입력'}\n"
            f"🆔 ID: #{user.id}\n"
            f"🕐 요청 시각: {kst_time} (KST)\n\n"
            "처리해 주세요:"
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ 승인", "callback_data": f"approve_{user.id}"},
                {"text": "❌ 거절", "callback_data": f"reject_{user.id}"}
            ]]
        }
        
        await self._request("sendMessage", {
            "chat_id": self.admin_chat_id,
            "text": text,
            "reply_markup": keyboard
        })

    async def send_message(self, chat_id: str, text: str) -> Optional[Dict[str, Any]]:
        """일반 텍스트 메시지 발송"""
        return await self._request("sendMessage", {
            "chat_id": chat_id,
            "text": text
        })

    async def edit_message(self, chat_id: str, message_id: int, text: str) -> Optional[Dict[str, Any]]:
        """기존 메시지 텍스트 교체 (버튼 제거)"""
        return await self._request("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        })

    async def answer_callback_query(self, callback_query_id: str, text: str) -> Optional[Dict[str, Any]]:
        """콜백 쿼리 응답 (토스트 알림)"""
        return await self._request("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text
        })

    async def set_webhook(self, url: str, secret_token: str) -> Optional[Dict[str, Any]]:
        """Webhook URL 등록"""
        return await self._request("setWebhook", {
            "url": url,
            "secret_token": secret_token
        })

    async def delete_webhook(self) -> Optional[Dict[str, Any]]:
        """Webhook 해제"""
        return await self._request("deleteWebhook", {})
