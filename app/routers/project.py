from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from app.models import Project, User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.core.crypto import encrypt_api_key

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    현재 로그인된 사용자의 신규 소설 프로젝트 생성 API
    """
    db_project = Project(
        user_id=current_user.id,
        title=project_in.title,
        synopsis=project_in.synopsis,
        llm_provider=project_in.llm_provider,
        llm_model=project_in.llm_model,
        api_key_override=encrypt_api_key(project_in.api_key_override)
    )
    session.add(db_project)
    await session.commit()
    await session.refresh(db_project)
    return ProjectResponse.from_orm_model(db_project)

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    현재 로그인된 사용자가 소유한 소설 프로젝트 전체 목록 조회 API
    """
    statement = select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
    result = await session.execute(statement)
    projects = result.scalars().all()
    return [ProjectResponse.from_orm_model(p) for p in projects]

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 소설 프로젝트의 상세 조회 API (소유권 인가 검증 포함)
    """
    statement = select(Project).where(Project.id == project_id)
    result = await session.execute(statement)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    # 인가(Authorization) 가드: 소유자가 아닐 경우 403 Forbidden 반환
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this project"
        )
        
    return ProjectResponse.from_orm_model(project)

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    소설 프로젝트 정보 수정 API (소유권 인가 검증 포함)
    """
    statement = select(Project).where(Project.id == project_id)
    result = await session.execute(statement)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this project"
        )
        
    # 전달된 필드만 추출하여 동적 업데이트 수행
    update_data = project_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "api_key_override" and value is not None:
            value = encrypt_api_key(value)
        setattr(project, key, value)
        
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return ProjectResponse.from_orm_model(project)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    소설 프로젝트 삭제 API (소유권 인가 검증 포함)
    """
    statement = select(Project).where(Project.id == project_id)
    result = await session.execute(statement)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this project"
        )
        
    # 프로젝트 삭제 수행
    await session.delete(project)
    await session.commit()
    return None
