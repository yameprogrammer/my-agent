from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import User, WorldSetting, Character
from app.schemas.project import BrainstormRequest, BrainstormApplyRequest
from app.services.llm_factory import LLMFactory
from app.services.agents import BrainstormAgent

router = APIRouter(
    prefix="/projects/{project_id}/brainstorm",
    tags=["Brainstorm"],
)


@router.post("")
async def brainstorm_lore_and_characters(
    project_id: int,
    req: BrainstormRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """AI 기획 에이전트가 세계관 설정과 캐릭터를 추천 생성합니다."""

    # 1. 소유권 검증 및 프로젝트 ORM 획득
    project = await check_project_owner(project_id, current_user, session)

    # 2. 시놉시스 검증
    if not project.synopsis or not project.synopsis.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트 시놉시스가 비어 있습니다. [프로젝트 설정]에서 시놉시스를 먼저 입력해 주세요.",
        )

    # 3. 기획(Plotter) 에이전트 전용 LLM 로드 (Fallback 적용)
    try:
        model = LLMFactory.get_model_for_agent(project, "plotter")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM 모델 생성 실패: {e}. 프로젝트 설정에서 API Key가 올바르게 설정되어 있는지 확인하세요.",
        )

    # 4. 에이전트 구동
    agent = BrainstormAgent(model)
    try:
        result = await agent.run(
            project_title=project.title,
            project_synopsis=project.synopsis,
            user_instruction=req.user_instruction,
            current_lores=req.current_lores,
            current_characters=req.current_characters,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"브레인스토밍 에이전트 실행 중 오류: {e}",
        )

    # 5. Pydantic → dict 변환 후 반환
    return result.model_dump()


@router.post("/apply")
async def apply_brainstorm_results(
    project_id: int,
    req: BrainstormApplyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """사용자가 선택한 기획안을 프로젝트 DB에 일괄 저장합니다."""

    # 1. 소유권 검증
    await check_project_owner(project_id, current_user, session)

    # 2. 세계관 일괄 저장
    added_lores = 0
    for lore in req.lores:
        db_lore = WorldSetting(
            project_id=project_id,
            keyword=lore["keyword"],
            category=lore["category"],
            description=lore["description"],
        )
        session.add(db_lore)
        added_lores += 1

    # 3. 캐릭터 일괄 저장
    added_characters = 0
    for char in req.characters:
        db_char = Character(
            project_id=project_id,
            name=char["name"],
            importance=char["importance"],
            description=char["description"],
        )
        session.add(db_char)
        added_characters += 1

    # 4. 커밋
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 저장 실패: {e}",
        )

    return {
        "status": "success",
        "added_lores": added_lores,
        "added_characters": added_characters,
    }
