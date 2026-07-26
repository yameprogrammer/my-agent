"""IDEA-03: 복선 레지스트리 CRUD."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import PlotThread, User
from app.schemas.plot_thread import (
    PlotThreadCreate,
    PlotThreadUpdate,
    PlotThreadResponse,
)

router = APIRouter(prefix="/projects/{project_id}/plot-threads", tags=["PlotThreads"])

ALLOWED_STATUS = {"open", "planted", "resolved", "dropped"}


@router.get("", response_model=List[PlotThreadResponse])
async def list_plot_threads(
    project_id: int,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    stmt = select(PlotThread).where(PlotThread.project_id == project_id)
    if status_filter:
        stmt = stmt.where(PlotThread.status == status_filter)
    stmt = stmt.order_by(PlotThread.updated_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.post("", response_model=PlotThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_plot_thread(
    project_id: int,
    body: PlotThreadCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    st = (body.status or "open").lower()
    if st not in ALLOWED_STATUS:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(ALLOWED_STATUS)}")
    row = PlotThread(
        project_id=project_id,
        title=body.title.strip(),
        description=body.description or "",
        status=st,
        planted_episode_id=body.planted_episode_id,
        target_episode_id=body.target_episode_id,
        resolved_episode_id=body.resolved_episode_id,
        notes=body.notes,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.put("/{thread_id}", response_model=PlotThreadResponse)
async def update_plot_thread(
    project_id: int,
    thread_id: int,
    body: PlotThreadUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    row = await session.get(PlotThread, thread_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plot thread not found")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        st = data["status"].lower()
        if st not in ALLOWED_STATUS:
            raise HTTPException(status_code=422, detail=f"status must be one of {sorted(ALLOWED_STATUS)}")
        data["status"] = st
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plot_thread(
    project_id: int,
    thread_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    row = await session.get(PlotThread, thread_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plot thread not found")
    await session.delete(row)
    await session.commit()
    return None
