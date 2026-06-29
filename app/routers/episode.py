from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import Episode, User
from app.schemas.episode import EpisodeCreate, EpisodeUpdate, EpisodeResponse

router = APIRouter(prefix="/projects/{project_id}/episodes", tags=["Episodes"])

@router.post("", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    project_id: int,
    episode_in: EpisodeCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 소설 프로젝트 내에 신규 회차(Episode) 생성 API (소유권 검증 포함)
    """
    # 프로젝트 소유권 체크 (인가)
    await check_project_owner(project_id, current_user, session)
    
    db_episode = Episode(
        project_id=project_id,
        episode_number=episode_in.episode_number,
        title=episode_in.title
    )
    session.add(db_episode)
    await session.commit()
    await session.refresh(db_episode)
    return db_episode

@router.get("", response_model=List[EpisodeResponse])
async def list_episodes(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 소설 프로젝트의 회차 목록 전체 조회 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Episode).where(Episode.project_id == project_id).order_by(Episode.episode_number.asc())
    result = await session.execute(statement)
    episodes = result.scalars().all()
    return episodes

@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    project_id: int,
    episode_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    단일 회차 상세 조회 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    result = await session.execute(statement)
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    return episode

@router.put("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    project_id: int,
    episode_id: int,
    episode_in: EpisodeUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    회차 정보 수정 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    result = await session.execute(statement)
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
        
    update_data = episode_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(episode, key, value)
        
    session.add(episode)
    await session.commit()
    await session.refresh(episode)
    return episode

@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    project_id: int,
    episode_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    회차 삭제 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    result = await session.execute(statement)
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
        
    await session.delete(episode)
    await session.commit()
    return None
