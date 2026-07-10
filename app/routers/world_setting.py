import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List, Optional
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import WorldSetting, User, Project
from app.schemas.world_setting import WorldSettingCreate, WorldSettingUpdate, WorldSettingResponse
from app.services.rag import generate_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/world-settings", tags=["World Settings"])


async def _embed_lore_text(project: Project, keyword: str, description: str) -> Optional[list]:
    """키워드+설명을 임베딩. 실패 시 None (키워드 RAG 경로는 유지)."""
    text = f"{keyword}\n{description}".strip()
    if not text:
        return None
    try:
        return await generate_embedding(text, project)
    except Exception as e:
        logger.warning("WorldSetting embedding failed (project_id=%s): %s", project.id, e)
        return None


@router.post("", response_model=WorldSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_world_setting(
    project_id: int,
    setting_in: WorldSettingCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 소설 프로젝트 내에 신규 세계관 설정(Lorebook) 추가 API (프로젝트 소유권 검증 포함)
    """
    project = await check_project_owner(project_id, current_user, session)
    embedding = await _embed_lore_text(project, setting_in.keyword, setting_in.description)

    db_setting = WorldSetting(
        project_id=project_id,
        keyword=setting_in.keyword,
        category=setting_in.category,
        description=setting_in.description,
        embedding=embedding,
    )
    session.add(db_setting)
    await session.commit()
    await session.refresh(db_setting)
    return db_setting

@router.get("", response_model=List[WorldSettingResponse])
async def list_world_settings(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 소설 프로젝트의 세계관 설정 목록 전체 조회 API (프로젝트 소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(WorldSetting).where(WorldSetting.project_id == project_id)
    result = await session.execute(statement)
    settings = result.scalars().all()
    return settings

@router.get("/{setting_id}", response_model=WorldSettingResponse)
async def get_world_setting(
    project_id: int,
    setting_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    단일 세계관 설정 상세 조회 API (프로젝트 소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(WorldSetting).where(WorldSetting.id == setting_id, WorldSetting.project_id == project_id)
    result = await session.execute(statement)
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World setting not found"
        )
    return setting

@router.put("/{setting_id}", response_model=WorldSettingResponse)
async def update_world_setting(
    project_id: int,
    setting_id: int,
    setting_in: WorldSettingUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    세계관 설정 수정 API (프로젝트 소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(WorldSetting).where(WorldSetting.id == setting_id, WorldSetting.project_id == project_id)
    result = await session.execute(statement)
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World setting not found"
        )
        
    update_data = setting_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(setting, key, value)

    # 키워드/설명 변경 시 임베딩 재계산
    if "keyword" in update_data or "description" in update_data:
        project = await session.get(Project, project_id)
        if project:
            setting.embedding = await _embed_lore_text(
                project, setting.keyword, setting.description
            )

    session.add(setting)
    await session.commit()
    await session.refresh(setting)
    return setting

@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_world_setting(
    project_id: int,
    setting_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    세계관 설정 삭제 API (프로젝트 소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(WorldSetting).where(WorldSetting.id == setting_id, WorldSetting.project_id == project_id)
    result = await session.execute(statement)
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World setting not found"
        )
        
    await session.delete(setting)
    await session.commit()
    return None
