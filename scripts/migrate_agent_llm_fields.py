import asyncio
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import async_engine

async def run_migration():
    agents = ["plotter", "writer", "judge", "editor", "reviewer"]
    async with async_engine.begin() as conn:
        print("Starting Project table migration...")
        for agent in agents:
            try:
                # PostgreSQL/SQLite 공용 호환 쿼리 처리
                await conn.execute(text(f"ALTER TABLE project ADD COLUMN {agent}_provider VARCHAR(50);"))
                await conn.execute(text(f"ALTER TABLE project ADD COLUMN {agent}_model VARCHAR(100);"))
                await conn.execute(text(f"ALTER TABLE project ADD COLUMN {agent}_api_key TEXT;"))
                print(f"Successfully added fields for: {agent}")
            except Exception as e:
                # 이미 컬럼이 존재하는 경우(중복 방지) 예외 스킵
                print(f"Field for {agent} might already exist. Details: {e}")
        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(run_migration())
