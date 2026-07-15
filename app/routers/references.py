from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, or_
from typing import Optional, List

from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from app.models import Project, User, ReferenceMaterial
from app.schemas.reference_material import (
    ReferenceMaterialCreate,
    ReferenceMaterialResponse,
    ReferenceMaterialListResponse,
    ReferenceResearchRequest
)

# 리서치 백그라운드 태스크 서비스 모듈 임포트 (Phase 3에서 실제 구현 예정)
# 순환 참조 방지 및 격리를 위해 stub 함수도 이 모듈 내부에 둡니다.
async def run_research_background(project_id: int, topic: str, category: str, target_sources: List[str]):
    """
    LangGraph 리서치 에이전트 비동기 구동 및 웹소켓 실시간 알림 방출
    """
    try:
        from app.services.researcher import run_researcher_agent
        await run_researcher_agent(project_id, topic, category, target_sources)
        
        # 실시간 웹소켓 푸시 전송 (Phase 2)
        try:
            from app.routers.websocket import manager
            await manager.broadcast_project(
                project_id=project_id,
                message={
                    "event": "research_completed",
                    "project_id": project_id,
                    "topic": topic,
                    "message": f"🤖 AI 리서치 담당관: '{topic}' 주제의 고증 연구 보고서가 완료되었습니다!"
                }
            )
        except Exception as ws_err:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to broadcast research completion WebSocket alert: {ws_err}")
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error executing background research agent: {str(e)}")

router = APIRouter(prefix="/projects/{project_id}/references", tags=["References"])

async def verify_project_owner(project_id: int, current_user: User, session: AsyncSession) -> Project:
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
    return project

@router.get("", response_model=ReferenceMaterialListResponse)
async def list_references(
    project_id: int,
    page: int = 1,
    size: int = 20,
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    프로젝트의 참고 자료 목록을 조회합니다. (필터링 및 검색 지원)
    """
    await verify_project_owner(project_id, current_user, session)
    
    # 쿼리 구성
    stmt = select(ReferenceMaterial).where(ReferenceMaterial.project_id == project_id)
    if category:
        stmt = stmt.where(ReferenceMaterial.category == category)
    if search:
        stmt = stmt.where(
            or_(
                ReferenceMaterial.title.like(f"%{search}%"),
                ReferenceMaterial.content.like(f"%{search}%")
            )
        )
    
    # 페이징 카운트
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_res = await session.execute(count_stmt)
    total = count_res.scalar() or 0
    
    # 데이터 페치
    stmt = stmt.order_by(ReferenceMaterial.created_at.desc()).offset((page - 1) * size).limit(size)
    res = await session.execute(stmt)
    items = res.scalars().all()
    
    return ReferenceMaterialListResponse(
        items=[ReferenceMaterialResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size
    )

@router.post("", response_model=ReferenceMaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_reference(
    project_id: int,
    ref_in: ReferenceMaterialCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    참고 자료를 직접 수동으로 등록합니다.
    """
    await verify_project_owner(project_id, current_user, session)
    
    new_ref = ReferenceMaterial(
        project_id=project_id,
        title=ref_in.title,
        content=ref_in.content,
        category=ref_in.category,
        source_type=ref_in.source_type,
        source_url=ref_in.source_url
    )
    session.add(new_ref)
    await session.commit()
    await session.refresh(new_ref)
    return ReferenceMaterialResponse.model_validate(new_ref)

@router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    project_id: int,
    ref_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 참고 자료를 삭제합니다.
    """
    await verify_project_owner(project_id, current_user, session)
    
    stmt = select(ReferenceMaterial).where(
        ReferenceMaterial.id == ref_id,
        ReferenceMaterial.project_id == project_id
    )
    res = await session.execute(stmt)
    ref = res.scalar_one_or_none()
    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference material not found"
        )
        
    await session.delete(ref)
    await session.commit()
    return

@router.post("/research", status_code=status.HTTP_202_ACCEPTED)
async def trigger_research_agent(
    project_id: int,
    req: ReferenceResearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    리서치 에이전트를 백그라운드 태스크로 기동하여 고증 정보를 수집하고 참고 자료로 등록합니다.
    """
    await verify_project_owner(project_id, current_user, session)
    
    # 비동기 백그라운드 태스크 예약
    background_tasks.add_task(
        run_research_background,
        project_id=project_id,
        topic=req.topic,
        category=req.category,
        target_sources=req.target_sources
    )
    
    return {"status": "processing", "message": "Research agent workflow started in the background."}
