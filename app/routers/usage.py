"""IDEA-11/12: 프로젝트 토큰·호출 로그 조회."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import AgentUsageLog, User

router = APIRouter(prefix="/projects/{project_id}/usage", tags=["Usage"])


class UsageSummaryRow(BaseModel):
    agent_role: str
    calls: int
    est_input_tokens: int
    est_output_tokens: int
    avg_latency_ms: float
    failures: int


class UsageLogRow(BaseModel):
    id: int
    episode_id: Optional[int]
    agent_role: str
    model_name: Optional[str]
    provider: Optional[str]
    latency_ms: int
    prompt_hash: Optional[str]
    est_input_tokens: int
    est_output_tokens: int
    success: bool
    error_message: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/summary", response_model=List[UsageSummaryRow])
async def usage_summary(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    stmt = (
        select(
            AgentUsageLog.agent_role,
            func.count(AgentUsageLog.id),
            func.coalesce(func.sum(AgentUsageLog.est_input_tokens), 0),
            func.coalesce(func.sum(AgentUsageLog.est_output_tokens), 0),
            func.coalesce(func.avg(AgentUsageLog.latency_ms), 0.0),
            func.sum(func.cast(~AgentUsageLog.success, type_=None)),
        )
        .where(AgentUsageLog.project_id == project_id)
        .group_by(AgentUsageLog.agent_role)
    )
    # simpler aggregation in Python for portability
    rows = (
        await session.execute(
            select(AgentUsageLog).where(AgentUsageLog.project_id == project_id)
        )
    ).scalars().all()
    by_role: dict = {}
    for r in rows:
        b = by_role.setdefault(
            r.agent_role,
            {"calls": 0, "in": 0, "out": 0, "lat": 0, "fail": 0},
        )
        b["calls"] += 1
        b["in"] += r.est_input_tokens
        b["out"] += r.est_output_tokens
        b["lat"] += r.latency_ms
        if not r.success:
            b["fail"] += 1
    return [
        UsageSummaryRow(
            agent_role=role,
            calls=v["calls"],
            est_input_tokens=v["in"],
            est_output_tokens=v["out"],
            avg_latency_ms=round(v["lat"] / v["calls"], 1) if v["calls"] else 0.0,
            failures=v["fail"],
        )
        for role, v in sorted(by_role.items())
    ]


@router.get("/logs", response_model=List[UsageLogRow])
async def usage_logs(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    agent_role: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    stmt = select(AgentUsageLog).where(AgentUsageLog.project_id == project_id)
    if agent_role:
        stmt = stmt.where(AgentUsageLog.agent_role == agent_role)
    stmt = stmt.order_by(AgentUsageLog.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        UsageLogRow(
            id=r.id,
            episode_id=r.episode_id,
            agent_role=r.agent_role,
            model_name=r.model_name,
            provider=r.provider,
            latency_ms=r.latency_ms,
            prompt_hash=r.prompt_hash,
            est_input_tokens=r.est_input_tokens,
            est_output_tokens=r.est_output_tokens,
            success=r.success,
            error_message=r.error_message,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
