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


@router.post("/{episode_id}/audit-plot")
async def audit_episode_plot(
    project_id: int,
    episode_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    해당 에피소드의 씬스 기획안과 설정집을 비교하여 사전 개연성/인물 붕괴 정밀 검수 진행
    """
    await check_project_owner(project_id, current_user, session)
    
    from app.models import Project, WorldSetting, Character
    project = await session.get(Project, project_id)
    episode = await session.get(Episode, episode_id)
    if not project or not episode:
        raise HTTPException(status_code=404, detail="Project or Episode not found")

    # 세계관 및 캐릭터 맥락 병합
    lore_stmt = select(WorldSetting).where(WorldSetting.project_id == project_id)
    lores = (await session.execute(lore_stmt)).scalars().all()
    
    char_stmt = select(Character).where(Character.project_id == project_id)
    chars = (await session.execute(char_stmt)).scalars().all()
    
    lore_context = "=== 등장인물 설정 ===\n"
    lore_context += "\n".join([f"- {c.name} ({c.importance}): {c.description}" for c in chars])
    lore_context += "\n\n=== 세계관 및 설정집 ===\n"
    lore_context += "\n".join([f"- {ws.keyword} ({ws.category}): {ws.description}" for ws in lores])

    # LangGraph 워크플로우 상태에서 기획 scenes 리스트를 조회
    from app.services.workflow import get_compiled_workflow
    from app.core.database import get_connection_pool
    import os
    
    thread_id = f"thread_{project_id}_{episode_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    if os.getenv("TESTING") == "True":
        app_workflow = await get_compiled_workflow(conn_pool=None)
    else:
        pool = get_connection_pool()
        app_workflow = await get_compiled_workflow(conn_pool=pool)

    state = await app_workflow.aget_state(config)
    scenes_list = []
    if state and state.values and state.values.get("scenes"):
        scenes_list = state.values.get("scenes")

    if not scenes_list:
        raise HTTPException(
            status_code=400,
            detail="기획된 씬 정보가 존재하지 않습니다. 우측 '실시간 집필실'에 먼저 입장하여 집필 가동 버튼을 누르거나 기획을 기동해 주세요."
        )

    # 감사관 기동
    from app.services.agents import PlotAuditorAgent
    from app.services.llm_factory import LLMFactory
    
    if os.getenv("TESTING") == "True":
        # Mocking for tests
        return {
            "is_passed": True,
            "score": 95,
            "summary": "기획안 검수 통과 (테스트 픽스처)",
            "scene_audits": [
                {
                    "scene_index": 0,
                    "scene_title": "테스트 씬",
                    "is_passed": True,
                    "ooc_issues": [],
                    "plot_holes": [],
                    "suggestions": []
                }
            ]
        }
        
    llm = LLMFactory.get_model_for_agent(project, "judge", temperature=0.2)
    auditor = PlotAuditorAgent(llm)
    
    try:
        report = await auditor.run(
            project_synopsis=project.synopsis or "",
            episode_title=episode.title or "",
            episode_outline=episode.outline or "",
            lore_context=lore_context,
            scenes_list=scenes_list
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기획 감사 연산 중 에러 발생: {str(e)}")
