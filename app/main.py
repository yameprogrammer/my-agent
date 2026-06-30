

from fastapi import FastAPI, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager
from app.core.database import init_db, get_async_session, close_db, get_connection_pool
from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.project import router as project_router
from app.routers.world_setting import router as world_setting_router
from app.routers.character import router as character_router
from app.routers.episode import router as episode_router
from app.routers.content import router as content_router
from app.routers.websocket import router as websocket_router
from app.core.dependencies import get_current_user
from app.schemas.auth import UserResponse
from app.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 psycopg 커넥션 풀 구동 및 DB 테이블 로드
    import os
    is_testing = os.getenv("TESTING") == "True"
    
    if not is_testing:
        pool = get_connection_pool()
        await pool.open()
        
    await init_db()
    yield
    # 애플리케이션 종료 시 커넥션 풀 닫기 및 DB 엔진 커넥션 정리
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

@app.get("/health", tags=["System"])
async def health_check(session: AsyncSession = Depends(get_async_session)):
    """
    백엔드 엔진 및 PostgreSQL 데이터베이스의 연결 정상성 검증용 헬스체크 API
    """
    try:
        # 데이터베이스 응답 테스트
        await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "message": "Novel Agentic Machine API is fully operational."
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.get("/users/me", response_model=UserResponse, tags=["Users"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    보안 미들웨어 검증: JWT 토큰으로 인증된 현재 사용자 정보를 리턴하는 API
    """
    return current_user
