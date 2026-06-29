from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import Episode, Content, User
from app.schemas.content import ContentCreate, ContentResponse

router = APIRouter(prefix="/projects/{project_id}/episodes/{episode_id}/contents", tags=["Contents"])

async def check_episode_in_project(project_id: int, episode_id: int, session: AsyncSession) -> Episode:
    """
    요청된 에피소드가 제공된 프로젝트 ID 소속인지 교차 확인하는 헬퍼 함수
    """
    statement = select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    result = await session.execute(statement)
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found in the specified project"
        )
    return episode

@router.post("", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    project_id: int,
    episode_id: int,
    content_in: ContentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    회차 내에 새로운 본문 버전 저장 API (parent_id를 통한 버전 트리 구조 지향)
    """
    # 1. 프로젝트 소유 권한 및 에피소드 유효성 검증
    await check_project_owner(project_id, current_user, session)
    await check_episode_in_project(project_id, episode_id, session)
    
    # 2. parent_id(부모 버전)가 제공된 경우, 실제 해당 에피소드에 종속된 버전이 맞는지 교차 확인
    if content_in.parent_id:
        parent_stmt = select(Content).where(Content.id == content_in.parent_id, Content.episode_id == episode_id)
        parent_res = await session.execute(parent_stmt)
        parent = parent_res.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent content version not found in this episode"
            )
            
    # 3. 새로운 본문 버전 생성 (DB 필드명 content_text에 매핑)
    db_content = Content(
        episode_id=episode_id,
        parent_id=content_in.parent_id,
        version_tag=content_in.version_tag,
        content_text=content_in.text,  # DTO text -> DB content_text 맵핑
        author_type=content_in.author_type,
        is_approved=False
    )
    session.add(db_content)
    await session.commit()
    await session.refresh(db_content)
    return ContentResponse.from_orm_model(db_content)

@router.get("", response_model=List[ContentResponse])
async def list_contents(
    project_id: int,
    episode_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 회차의 모든 본문 버전 리스트(히스토리) 조회 API
    """
    await check_project_owner(project_id, current_user, session)
    await check_episode_in_project(project_id, episode_id, session)
    
    statement = select(Content).where(Content.episode_id == episode_id).order_by(Content.created_at.asc())
    result = await session.execute(statement)
    contents = result.scalars().all()
    return [ContentResponse.from_orm_model(c) for c in contents]

@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    project_id: int,
    episode_id: int,
    content_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    단일 본문 버전 상세 조회 API
    """
    await check_project_owner(project_id, current_user, session)
    await check_episode_in_project(project_id, episode_id, session)
    
    statement = select(Content).where(Content.id == content_id, Content.episode_id == episode_id)
    result = await session.execute(statement)
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content version not found"
        )
    return ContentResponse.from_orm_model(content)

@router.put("/{content_id}/approve", response_model=ContentResponse)
async def approve_content(
    project_id: int,
    episode_id: int,
    content_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 본문 버전을 해당 회차의 최종본으로 승인(Approve) 처리하는 API (기존 승인 버전은 자동 해제)
    """
    await check_project_owner(project_id, current_user, session)
    await check_episode_in_project(project_id, episode_id, session)
    
    # 1. 대상 본문 존재 확인
    stmt = select(Content).where(Content.id == content_id, Content.episode_id == episode_id)
    res = await session.execute(stmt)
    target_content = res.scalar_one_or_none()
    
    if not target_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content version not found"
        )
        
    # 2. 동일 에피소드 아래에 기존 승인(is_approved=True) 처리된 본문 버전들을 일괄 비승인(False) 처리
    reset_stmt = select(Content).where(Content.episode_id == episode_id, Content.is_approved == True)
    reset_res = await session.execute(reset_stmt)
    previously_approved = reset_res.scalars().all()
    for pa in previously_approved:
        pa.is_approved = False
        session.add(pa)
        
    # 3. 대상 본문 승인 처리
    target_content.is_approved = True
    session.add(target_content)
    
    await session.commit()
    await session.refresh(target_content)
    return ContentResponse.from_orm_model(target_content)
