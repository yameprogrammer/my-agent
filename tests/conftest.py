import os
os.environ["TESTING"] = "True"


import pytest
from sqlmodel import select
from app.core.database import close_db, get_async_session
from app.models import User


@pytest.fixture(scope="session", autouse=True)
async def cleanup_db_engine():
    yield
    await close_db()


async def activate_user(username: str) -> None:
    """테스트용: 가입 직후 관리자 승인(is_active=True)을 시뮬레이션한다."""
    async for session in get_async_session():
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            raise AssertionError(f"activate_user: user not found: {username}")
        user.is_active = True
        user.rejected_at = None
        session.add(user)
        await session.commit()
        return