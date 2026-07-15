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


# ---------------------------------------------------
# 어드민 스마트 백업 및 복원 API (Phase 2)
# ---------------------------------------------------
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from app.services.migration import export_project_data, import_project_data
from app.models import ReferenceMaterial, WorldSetting, Character, Content
from sqlmodel import delete
import json

@router.get("/backup")
async def export_system_backup(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    시스템의 모든 소설 프로젝트(세계관, 캐릭터, 에피소드, 씬) 및 고증 참고자료 데이터를 한 번에 백업합니다.
    """
    try:
        # 모든 프로젝트 로드
        proj_stmt = select(Project)
        proj_res = await session.execute(proj_stmt)
        projects = proj_res.scalars().all()

        backup_projects = []
        for proj in projects:
            # 기존 export_project_data 활용
            export_schema = await export_project_data(proj.id, session)
            proj_dict = export_schema.model_dump(mode="json")
            
            # 복원을 위해 원래 프로젝트의 ID 및 소유자 이름 저장
            proj_dict["old_id"] = proj.id
            owner_res = await session.execute(select(User).where(User.id == proj.user_id))
            owner = owner_res.scalar_one_or_none()
            proj_dict["owner_username"] = owner.username if owner else current_admin.username
            
            backup_projects.append(proj_dict)

        # 모든 참고 자료 로드
        ref_stmt = select(ReferenceMaterial)
        ref_res = await session.execute(ref_stmt)
        references = ref_res.scalars().all()

        backup_references = []
        for ref in references:
            backup_references.append({
                "title": ref.title,
                "content": ref.content,
                "category": ref.category,
                "source_type": ref.source_type,
                "source_url": ref.source_url,
                "project_id": ref.project_id,
                "created_at": ref.created_at.isoformat() if ref.created_at else None
            })

        backup_data = {
            "version": "1.0.0",
            "backup_date": datetime.utcnow().isoformat(),
            "projects": backup_projects,
            "references": backup_references
        }

        # JSONResponse로 아카이브 출력 다운로드 반환
        filename = f"novel_system_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        return JSONResponse(
            content=backup_data,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"시스템 백업 실패: {str(e)}"
        )


@router.post("/restore")
async def import_system_restore(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    백업 파일을 업로드하여 기존 데이터를 모두 초기화하고 전체 소설 프로젝트 및 참고자료를 복원합니다.
    """
    try:
        content = await file.read()
        data = json.loads(content)

        if "projects" not in data or "references" not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="올바르지 않은 백업 파일 형식입니다."
            )

        # 1. 기존 프로젝트 및 종속 관계 테이블 데이터 삭제 (Truncate/Clean)
        # 회원(User) 데이터는 어드민 로그인 세션 유지를 위해 건드리지 않음
        await session.execute(delete(Content))
        await session.execute(delete(Episode))
        await session.execute(delete(Character))
        await session.execute(delete(WorldSetting))
        await session.execute(delete(ReferenceMaterial))
        await session.execute(delete(Project))
        await session.commit()

        # 2. 프로젝트 복원 기동
        from app.schemas.migration import ProjectExportSchema
        project_id_map = {} # old_id -> new_id 매핑

        for proj_data in data["projects"]:
            old_id = proj_data.pop("old_id", None)
            owner_username = proj_data.pop("owner_username", None)

            # 프로젝트 소유자 유저 조회 (없을 시 현재 복원하는 어드민 계정으로 매핑)
            user_stmt = select(User).where(User.username == owner_username)
            user_res = await session.execute(user_stmt)
            owner = user_res.scalar_one_or_none()
            target_user_id = owner.id if owner else current_admin.id

            # ProjectExportSchema로 바인딩
            schema = ProjectExportSchema.model_validate(proj_data)
            new_proj = await import_project_data(target_user_id, schema, session)
            await session.commit()
            await session.refresh(new_proj)

            if old_id:
                project_id_map[old_id] = new_proj.id

        # 3. 참고 자료 복원 및 외래키 정렬
        for ref_data in data["references"]:
            old_proj_id = ref_data.pop("project_id", None)
            new_proj_id = project_id_map.get(old_proj_id)

            if not new_proj_id:
                # 맵핑되는 신규 프로젝트가 없을 시 복원 생략
                continue

            # ReferenceMaterial 생성 및 커밋
            created_at_val = None
            if ref_data.get("created_at"):
                created_at_val = datetime.fromisoformat(ref_data["created_at"])

            new_ref = ReferenceMaterial(
                project_id=new_proj_id,
                title=ref_data["title"],
                content=ref_data["content"],
                category=ref_data["category"],
                source_type=ref_data["source_type"],
                source_url=ref_data["source_url"],
                created_at=created_at_val or datetime.utcnow()
            )
            session.add(new_ref)

        await session.commit()
        return {"status": "success", "message": "데이터베이스 복원이 정상 완료되었습니다."}

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"복원 작업 실패: {str(e)}"
        )
