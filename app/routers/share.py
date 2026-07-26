"""IDEA-18: 읽기 전용 공유 링크."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import User, Project, ProjectShareLink, Episode, Content

router = APIRouter(tags=["Share"])


class ShareCreateRequest(BaseModel):
    label: Optional[str] = None
    expires_days: Optional[int] = Field(default=7, ge=1, le=90)


class ShareLinkResponse(BaseModel):
    id: int
    token: str
    label: Optional[str]
    expires_at: Optional[datetime]
    is_revoked: bool
    created_at: datetime
    url_path: str

    model_config = {"from_attributes": True}


@router.post("/projects/{project_id}/share-links", response_model=ShareLinkResponse)
async def create_share_link(
    project_id: int,
    body: ShareCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    token = secrets.token_urlsafe(24)
    expires = None
    if body.expires_days:
        expires = datetime.utcnow() + timedelta(days=body.expires_days)
    row = ProjectShareLink(
        project_id=project_id,
        token=token,
        label=body.label,
        expires_at=expires,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return ShareLinkResponse(
        id=row.id,
        token=row.token,
        label=row.label,
        expires_at=row.expires_at,
        is_revoked=row.is_revoked,
        created_at=row.created_at,
        url_path=f"/share/{row.token}",
    )


@router.get("/projects/{project_id}/share-links", response_model=List[ShareLinkResponse])
async def list_share_links(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    rows = (
        await session.execute(
            select(ProjectShareLink)
            .where(ProjectShareLink.project_id == project_id)
            .order_by(ProjectShareLink.created_at.desc())
        )
    ).scalars().all()
    return [
        ShareLinkResponse(
            id=r.id,
            token=r.token,
            label=r.label,
            expires_at=r.expires_at,
            is_revoked=r.is_revoked,
            created_at=r.created_at,
            url_path=f"/share/{r.token}",
        )
        for r in rows
    ]


@router.delete("/projects/{project_id}/share-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(
    project_id: int,
    link_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await check_project_owner(project_id, current_user, session)
    row = await session.get(ProjectShareLink, link_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Share link not found")
    row.is_revoked = True
    session.add(row)
    await session.commit()
    return None


@router.get("/share/{token}")
async def public_share_view(
    token: str,
    session: AsyncSession = Depends(get_async_session),
):
    """인증 없이 읽기 전용 프로젝트 요약 + 승인 원고."""
    stmt = select(ProjectShareLink).where(ProjectShareLink.token == token)
    link = (await session.execute(stmt)).scalar_one_or_none()
    if not link or link.is_revoked:
        raise HTTPException(status_code=404, detail="Invalid or revoked share link")
    if link.expires_at and link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share link expired")

    project = await session.get(Project, link.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ep_stmt = (
        select(Episode)
        .where(Episode.project_id == project.id)
        .order_by(Episode.episode_number.asc())
        .options(selectinload(Episode.contents))
    )
    episodes = (await session.execute(ep_stmt)).scalars().all()
    ep_payload = []
    for ep in episodes:
        approved = next((c for c in ep.contents if c.is_approved), None)
        if not approved and ep.contents:
            approved = sorted(ep.contents, key=lambda c: c.created_at, reverse=True)[0]
        ep_payload.append({
            "episode_number": ep.episode_number,
            "title": ep.title,
            "outline": ep.outline,
            "text": approved.content_text if approved else None,
        })

    return {
        "title": project.title,
        "synopsis": project.synopsis,
        "read_only": True,
        "episodes": ep_payload,
        "label": link.label,
    }
