from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime

from app.core.config import settings
from app.core.database import get_async_session
from app.models import User
from app.services.telegram_service import TelegramBotService

router = APIRouter(prefix="/auth/telegram", tags=["Telegram"])

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """
    텔레그램 봇의 Webhook을 처리한다.
    
    보안 검증:
    1. X-Telegram-Bot-Api-Secret-Token 헤더 확인
    2. callback_query.from.id와 ADMIN_TELEGRAM_CHAT_ID 대조
    3. user_id의 존재 및 미승인 상태 확인
    """
    # 1. Webhook Secret Token 검증
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret_token or secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret token."
        )

    data = await request.json()
    
    # callback_query가 없는 일반 메시지 등은 무시
    if "callback_query" not in data:
        return {"ok": True}

    callback_query = data["callback_query"]
    callback_data = callback_query.get("data", "")
    query_id = callback_query.get("id")
    from_user_id = str(callback_query.get("from", {}).get("id", ""))

    # 2. 관리자 권한 검증 (ADMIN_TELEGRAM_CHAT_ID와 대조)
    if from_user_id != settings.ADMIN_TELEGRAM_CHAT_ID:
        telegram = TelegramBotService(settings.TELEGRAM_BOT_TOKEN, settings.ADMIN_TELEGRAM_CHAT_ID)
        await telegram.answer_callback_query(query_id, "⛔ 권한이 없습니다.")
        return {"ok": True}

    # 3. callback_data 파싱 (approve_{user_id} 또는 reject_{user_id})
    try:
        if callback_data.startswith("approve_"):
            action = "approve"
            user_id = int(callback_data.replace("approve_", ""))
        elif callback_data.startswith("reject_"):
            action = "reject"
            user_id = int(callback_data.replace("reject_", ""))
        else:
            return {"ok": True}
    except ValueError:
        return {"ok": True}

    # 4. DB 유저 조회 및 상태 검증
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    telegram = TelegramBotService(settings.TELEGRAM_BOT_TOKEN, settings.ADMIN_TELEGRAM_CHAT_ID)

    if not user:
        await telegram.answer_callback_query(query_id, "⚠️ 존재하지 않는 사용자입니다.")
        return {"ok": True}

    # 멱등성 검증: 이미 처리된 계정인지 확인
    if user.is_active or user.rejected_at is not None:
        await telegram.answer_callback_query(query_id, "⚠️ 이미 처리된 요청입니다.")
        # 메시지 텍스트도 업데이트하여 상태 반영
        current_status = "승인 완료" if user.is_active else "거절 완료"
        await telegram.edit_message(
            settings.ADMIN_TELEGRAM_CHAT_ID, 
            callback_query.get("message", {}).get("message_id"), 
            f"⚠️ 이미 {current_status}된 사용자입니다. (ID: #{user.id})"
        )
        return {"ok": True}

    # 5. 액션 처리
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    if action == "approve":
        user.is_active = True
        result_text = f"✅ {user.username} 승인 완료 ({timestamp} UTC)"
        answer_text = "✅ 승인 완료!"
    else: # action == "reject"
        user.rejected_at = datetime.utcnow()
        result_text = f"❌ {user.username} 거절 완료 ({timestamp} UTC)"
        answer_text = "❌ 거절 완료!"

    session.add(user)
    await session.commit()

    # 6. 텔레그램 응답 처리
    await telegram.answer_callback_query(query_id, answer_text)
    await telegram.edit_message(
        settings.ADMIN_TELEGRAM_CHAT_ID, 
        callback_query.get("message", {}).get("message_id"), 
        result_text
    )

    return {"ok": True}
