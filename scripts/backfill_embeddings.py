import asyncio
import os
import sys

# Add project root to sys.path to resolve app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_engine
from app.models import WorldSetting, Project
from app.services.rag import generate_embedding
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

async def backfill_embeddings():
    print("Starting WorldSetting embeddings backfill script...")
    
    async with AsyncSession(async_engine) as session:
        # Find WorldSettings with missing embeddings
        statement = select(WorldSetting).where(WorldSetting.embedding == None)
        result = await session.execute(statement)
        lores = result.scalars().all()
        
        total = len(lores)
        print(f"Found {total} WorldSetting(s) without embeddings.")
        
        if total == 0:
            print("No backfill needed.")
            return

        success_count = 0
        fail_count = 0
        
        # Load unique projects beforehand to optimize queries
        project_ids = list(set(ws.project_id for ws in lores))
        project_stmt = select(Project).where(Project.id.in_(project_ids))
        project_res = await session.execute(project_stmt)
        project_map = {p.id: p for p in project_res.scalars().all()}
        
        for idx, ws in enumerate(lores, 1):
            project = project_map.get(ws.project_id)
            if not project:
                print(f"[{idx}/{total}] Skipping: Project ID {ws.project_id} not found for WorldSetting {ws.id}")
                fail_count += 1
                continue
                
            text = f"{ws.keyword}\n{ws.description}".strip()
            print(f"[{idx}/{total}] Embedding WS ID {ws.id} (Keyword: '{ws.keyword}')")
            
            embedding = None
            try:
                embedding = await generate_embedding(text, project)
            except Exception as e:
                print(f"Error during embedding API call: {e}")
                
            if embedding:
                ws.embedding = embedding
                session.add(ws)
                success_count += 1
                # Save progressively
                if idx % 10 == 0:
                    await session.commit()
            else:
                print(f"[{idx}/{total}] Failed to generate embedding for WS ID {ws.id} (Possible missing API key)")
                fail_count += 1
                
        await session.commit()
        print(f"Backfill finished. Success: {success_count}, Failed/Skipped: {fail_count}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(backfill_embeddings())
