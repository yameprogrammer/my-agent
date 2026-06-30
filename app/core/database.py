from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from app.core.config import settings

# pydantic settings에서 로드된 DB 연결 URL 사용
DATABASE_URL = settings.DATABASE_URL

import os
from sqlalchemy.pool import NullPool

# asyncpg 비동기 엔진 생성
if os.getenv("TESTING") == "True":
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )
else:
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


from psycopg_pool import AsyncConnectionPool
from typing import Optional

# psycopg 비동기 커넥션 풀 (LangGraph PostgresSaver 연동용)
psycopg_db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
connection_pool: Optional[AsyncConnectionPool] = None

def get_connection_pool() -> AsyncConnectionPool:
    global connection_pool
    if connection_pool is None:
        connection_pool = AsyncConnectionPool(
            conninfo=psycopg_db_url,
            open=False,
            min_size=1,
            max_size=10
        )
    return connection_pool

