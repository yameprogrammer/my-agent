import asyncio
import logging
from app.core.database import async_session_factory
from app.routers.telegram import handle_telegram_callback
from app.services.telegram_service import TelegramBotService

logger = logging.getLogger(__name__)

async def start_polling(telegram_service: TelegramBotService):
    """텔레그램 getUpdates API를 사용하여 롱 폴링(Long Polling)을 수행하는 백그라운드 루프"""
    offset = None
    logger.info("Telegram polling 백그라운드 태스크가 시작되었습니다.")
    
    while True:
        try:
            # 30초 롱 폴링
            updates = await telegram_service.get_updates(offset=offset, timeout=30)
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    # 다음 getUpdates 호출 시 중복 수신 방지를 위해 offset 갱신
                    offset = update["update_id"] + 1
                    
                    if "callback_query" in update:
                        callback_query = update["callback_query"]
                        # DB 세션을 생성하여 콜백 처리
                        async with async_session_factory() as session:
                            try:
                                await handle_telegram_callback(callback_query, session)
                            except Exception as e:
                                logger.error("Telegram callback 처리 중 오류 발생: %s", e)
            
            # CPU 점유율 과부하 방지 및 취소 시점 대기
            await asyncio.sleep(0.5)
            
        except asyncio.CancelledError:
            logger.info("Telegram polling 백그라운드 태스크가 취소(종료)되었습니다.")
            break
        except Exception as e:
            # Task가 취소되었을 때 cancelled error는 위에서 잡히지만, 다른 HTTP 에러 등의 예외 처리
            logger.error("Telegram polling 중 예상치 못한 오류 발생: %s", e)
            await asyncio.sleep(5)  # 오류 발생 시 잠시 대기 후 재시도
