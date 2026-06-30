import os
os.environ["TESTING"] = "True"

import pytest
from app.core.database import close_db

@pytest.fixture(scope="session", autouse=True)
async def cleanup_db_engine():
    yield
    await close_db()
