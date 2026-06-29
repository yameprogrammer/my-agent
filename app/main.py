from fastapi import FastAPI, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager
from app.core.database import init_db, get_async_session, close_db
from app.core.config import settings
from app.routers.auth import router as auth_router
from app.core.dependencies import get_current_user
from app.schemas.auth import UserResponse
from app.models import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 DB 테이블 로드 및 pgvector 확장 확인
    await init_db()
    yield
    # 애플리케이션 종료 시 DB 엔진 커넥션 닫기
    await close_db()

app = FastAPI(
    title="Novel Agentic Machine API",
    description="AI 소설 집필 에이전틱 머신 백엔드 엔진 API",
    version="1.0.0",
    lifespan=lifespan
)

# 회원 가입 및 로그인 라우터 추가
app.include_router(auth_router)

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
