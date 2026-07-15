from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, or_
from datetime import datetime
from typing import Optional
import asyncio

from app.core.database import get_async_session
from app.core.dependencies import get_current_admin
from app.models import User, Project, Episode
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserListResponse,
    AdminUserResponse,
    UserStatusChangeRequest,
    UserRoleChangeRequest
)

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    전체 유저 수, 승인 대기 수, 프로젝트 수, 에피소드 수 통계를 수집한다.
    """
    total_users_stmt = select(func.count(User.id))
    pending_users_stmt = select(func.count(User.id)).where(User.is_active == False, User.rejected_at == None)
    total_projects_stmt = select(func.count(Project.id))
    total_episodes_stmt = select(func.count(Episode.id))

    results = await asyncio.gather(
        session.execute(total_users_stmt),
        session.execute(pending_users_stmt),
        session.execute(total_projects_stmt),
        session.execute(total_episodes_stmt)
    )

    total_users = results[0].scalar() or 0
    pending_users = results[1].scalar() or 0
    total_projects = results[2].scalar() or 0
    total_episodes = results[3].scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        pending_users=pending_users,
        total_projects=total_projects,
        total_episodes=total_episodes
    )

@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = 1,
    size: int = 20,
    status_filter: Optional[str] = None,  # "pending" | "active" | "rejected"
    search: Optional[str] = None,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    가입 대기자 및 가입된 회원들의 페이징 리스트와 검색 결과를 조회한다.
    """
    if page < 1:
        page = 1
    if size < 1:
        size = 20

    stmt = select(User)

    if status_filter == "pending":
        stmt = stmt.where(User.is_active == False, User.rejected_at == None)
    elif status_filter == "active":
        stmt = stmt.where(User.is_active == True)
    elif status_filter == "rejected":
        stmt = stmt.where(User.rejected_at != None)

    if search:
        search_like = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.username.like(search_like),
                User.email.like(search_like)
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_res = await session.execute(count_stmt)
    total = count_res.scalar() or 0

    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    users = result.scalars().all()

    items = [
        AdminUserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            is_active=u.is_active,
            is_admin=u.is_admin,
            created_at=u.created_at,
            rejected_at=u.rejected_at
        ) for u in users
    ]

    return AdminUserListResponse(
        items=items,
        total=total,
        page=page,
        size=size
    )

@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: int,
    payload: UserStatusChangeRequest,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    회원을 승인, 거절(반려), 또는 임시정지한다. (자기 자신에 대한 액션 차단)
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-suspension or modification is not allowed."
        )

    stmt = select(User).where(User.id == user_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    action = payload.action
    if action == "approve":
        user.is_active = True
        user.rejected_at = None
    elif action == "reject":
        user.is_active = False
        user.rejected_at = datetime.utcnow()
    elif action == "suspend":
        user.is_active = False

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        rejected_at=user.rejected_at
    )

@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: int,
    payload: UserRoleChangeRequest,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 회원을 관리자로 승격하거나 관리자 권한을 회수한다. (자기 자신에 대한 강등 차단)
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-demotion is not allowed."
        )

    stmt = select(User).where(User.id == user_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_admin = payload.is_admin

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        rejected_at=user.rejected_at
    )
