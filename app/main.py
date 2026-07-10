import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager
import logging
from app.core.database import init_db, get_async_session, close_db, get_connection_pool
from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.project import router as project_router
from app.routers.world_setting import router as world_setting_router
from app.routers.character import router as character_router
from app.routers.episode import router as episode_router
from app.routers.content import router as content_router
from app.routers.websocket import router as websocket_router
from app.routers.telegram import router as telegram_router
from app.core.dependencies import get_current_user
from app.schemas.auth import UserResponse
from app.models import User

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 psycopg 커넥션 풀 구동 및 DB 테이블 로드
    import os
    is_testing = os.getenv("TESTING") == "True"
    
    if not is_testing:
        pool = get_connection_pool()
        await pool.open()
        
        # LangGraph Checkpointer 초기화
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        
    await init_db()
    
    # Telegram Webhook 등록 (토큰 + 비어 있지 않은 secret 이 모두 있을 때만)
    telegram_service = None
    if settings.TELEGRAM_BOT_TOKEN:
        secret = (settings.TELEGRAM_WEBHOOK_SECRET or "").strip()
        if len(secret) < 8:
            logger.error(
                "TELEGRAM_WEBHOOK_SECRET 이 비어 있거나 너무 짧습니다. "
                "set_webhook 을 건너뜁니다 (fail-closed)."
            )
        else:
            from app.services.telegram_service import TelegramBotService
            telegram_service = TelegramBotService(
                settings.TELEGRAM_BOT_TOKEN,
                settings.ADMIN_TELEGRAM_CHAT_ID,
            )
            webhook_url = f"{settings.BASE_URL}/auth/telegram/webhook"
            await telegram_service.set_webhook(webhook_url, secret)
            logger.info("Telegram webhook 등록: %s", webhook_url)
    
    yield
    
    # Shutdown
    if telegram_service:
        await telegram_service.delete_webhook()
        logger.info("Telegram webhook 해제 완료")
    
    if not is_testing:
        pool = get_connection_pool()
        await pool.close()
        
    await close_db()

app = FastAPI(
    title="Novel Agentic Machine API",
    description="AI 소설 집필 에이전틱 머신 백엔드 엔진 API",
    version="1.0.0",
    lifespan=lifespan
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(world_setting_router)
app.include_router(character_router)
app.include_router(episode_router)
app.include_router(content_router)
app.include_router(websocket_router)
app.include_router(telegram_router)

@app.get("/health", tags=["System"])
async def health_check(session: AsyncSession = Depends(get_async_session)):
    """
    백엔드 엔진 및 PostgreSQL 데이터베이스의 연결 정상성 검증용 헬스체크 API.
    DB 장애 시 HTTP 503 을 반환하여 로드밸런서/PM2 헬스체크가 실패를 인식하도록 한다.
    """
    try:
        await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "message": "Novel Agentic Machine API is fully operational."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )

@app.get("/users/me", response_model=UserResponse, tags=["Users"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    보안 미들웨어 검증: JWT 토큰으로 인증된 현재 사용자 정보를 리턴하는 API
    """
    return current_user

if __name__ == "__main__":
    import uvicorn
    # Windows 환경에서 Psycopg3 비동기 풀(ProactorEventLoop 충돌) 방지를 위해 진입점에서 정책 강제 적용
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080)
