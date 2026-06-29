from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# docker-compose.yml의 포트 및 계정 정보와 일치하는 기본값 설정
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/novel_db"
)

# asyncpg 비동기 엔진 생성
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,       # 갤럭시 Z 폴드 4 환경을 고려한 동시 접속 수 풀링
    max_overflow=5
)

# pgvector 확장 강제 활성화 및 SQLModel 테이블 마이그레이션 함수
async def init_db():
    from app.models import SQLModel  # SQLModel 메타데이터 로드
    async with async_engine.begin() as conn:
        # PostgreSQL pgvector 확장(EXTENSION) 활성화
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # 정의된 모든 테이블 생성
        await conn.run_sync(SQLModel.metadata.create_all)

# FastAPI 비동기 세션 주입용 의존성(Dependency) 함수
async def get_async_session() -> AsyncSession:
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        
async def close_db():
    await async_engine.dispose()
