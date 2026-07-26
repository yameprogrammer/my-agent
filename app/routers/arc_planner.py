"""IDEA-04: 멀티 에피소드 아크 플래너 API."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import User
from app.services.arc_planner import apply_arc_plan, generate_arc_plan

router = APIRouter(prefix="/projects/{project_id}/arc-plan", tags=["ArcPlanner"])


class ArcPlanRequest(BaseModel):
    episode_count: int = Field(default=5, ge=1, le=30)
    start_number: int = Field(default=1, ge=1)
    extra_instruction: Optional[str] = None
    apply: bool = Field(default=False, description="True면 회차 outline 자동 반영")
    create_missing: bool = True
    overwrite_outline: bool = True


@router.post("")
async def create_arc_plan(
    project_id: int,
    body: ArcPlanRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    project = await check_project_owner(project_id, current_user, session)
    try:
        plan = await generate_arc_plan(
            project,
            episode_count=body.episode_count,
            start_number=body.start_number,
            extra_instruction=body.extra_instruction or "",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Arc plan generation failed: {e}",
        ) from e

    result = {
        "overall_arc": plan.overall_arc,
        "episodes": [e.model_dump() for e in plan.episodes],
        "applied": None,
    }
    if body.apply:
        applied = await apply_arc_plan(
            session,
            project_id,
            plan,
            create_missing=body.create_missing,
            overwrite_outline=body.overwrite_outline,
        )
        result["applied"] = applied
    return result
