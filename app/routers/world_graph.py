"""IDEA-17: 세계관 키워드 관계 간단 그래프 (노드/엣지 JSON)."""
from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import User, WorldSetting, Character

router = APIRouter(prefix="/projects/{project_id}/world-graph", tags=["WorldGraph"])


@router.get("")
async def get_world_graph(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    lores = (
        await session.execute(
            select(WorldSetting).where(WorldSetting.project_id == project_id)
        )
    ).scalars().all()
    chars = (
        await session.execute(
            select(Character).where(Character.project_id == project_id)
        )
    ).scalars().all()

    nodes = []
    edges = []
    for ws in lores:
        nodes.append({
            "id": f"lore-{ws.id}",
            "label": ws.keyword,
            "type": "lore",
            "category": ws.category,
        })
    for c in chars:
        nodes.append({
            "id": f"char-{c.id}",
            "label": c.name,
            "type": "character",
            "category": c.importance,
            "location": getattr(c, "status_location", None),
        })
        # 캐릭터 설명이 로어 키워드를 포함하면 엣지
        desc = (c.description or "") + " " + (getattr(c, "status_notes", None) or "")
        for ws in lores:
            if ws.keyword and ws.keyword in desc:
                edges.append({
                    "source": f"char-{c.id}",
                    "target": f"lore-{ws.id}",
                    "relation": "mentions",
                })
        if getattr(c, "status_location", None):
            for ws in lores:
                if ws.category == "location" and ws.keyword == c.status_location:
                    edges.append({
                        "source": f"char-{c.id}",
                        "target": f"lore-{ws.id}",
                        "relation": "located_at",
                    })

    # lore-lore: 설명이 서로의 키워드를 포함
    for a in lores:
        for b in lores:
            if a.id >= b.id:
                continue
            if a.keyword and a.keyword in (b.description or ""):
                edges.append({
                    "source": f"lore-{a.id}",
                    "target": f"lore-{b.id}",
                    "relation": "related",
                })
            elif b.keyword and b.keyword in (a.description or ""):
                edges.append({
                    "source": f"lore-{b.id}",
                    "target": f"lore-{a.id}",
                    "relation": "related",
                })

    return {"nodes": nodes, "edges": edges}
