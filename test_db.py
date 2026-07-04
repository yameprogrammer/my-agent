import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_psycopg():
    from psycopg_pool import AsyncConnectionPool
    psycopg_db_url = "postgresql://postgres:password@127.0.0.1:5432/novel_db"
    print("Testing psycopg pool...")
    try:
        pool = AsyncConnectionPool(conninfo=psycopg_db_url, min_size=1, max_size=2)
        await pool.open()
        async with pool.connection() as conn:
            print("psycopg connection successful")
        await pool.close()
    except Exception as e:
        print(f"psycopg failed: {e}")

async def main():
    await test_psycopg()

if __name__ == "__main__":
    asyncio.run(main())
