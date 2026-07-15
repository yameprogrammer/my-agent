import asyncio
import sys
from sqlmodel import select

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import get_async_session
from app.models import User

async def main():
    async for session in get_async_session():
        statement = select(User)
        result = await session.execute(statement)
        users = result.scalars().all()
        print("=== Database Users ===")
        if not users:
            print("No users found in database.")
        for u in users:
            print(f"ID: {u.id} | Username: {u.username} | Active: {u.is_active} | Rejected: {u.rejected_at}")
        return

if __name__ == "__main__":
    import os
    os.environ["TESTING"] = "False" # Use development DB
    asyncio.run(main())
