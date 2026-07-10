import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_engine
from app.models import Project
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.crypto import encrypt_api_key, get_fernet

async def migrate_keys():
    if not get_fernet():
        print("API_KEY_ENCRYPTION_SECRET is not configured or invalid.")
        return
    
    async with AsyncSession(async_engine) as session:
        statement = select(Project).where(Project.api_key_override != None)
        result = await session.execute(statement)
        projects = result.scalars().all()
        
        migrated_count = 0
        for p in projects:
            # Simple heuristic: Fernet tokens start with gAAAAA...
            if not p.api_key_override.startswith("gAAAAA"):
                p.api_key_override = encrypt_api_key(p.api_key_override)
                session.add(p)
                migrated_count += 1
                
        await session.commit()
        print(f"Migration completed. {migrated_count} keys encrypted.")

if __name__ == "__main__":
    asyncio.run(migrate_keys())
