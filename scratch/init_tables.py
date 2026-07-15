import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import init_db

async def main():
    print("Initializing Database tables...")
    await init_db()
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(main())
