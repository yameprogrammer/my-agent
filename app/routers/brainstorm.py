from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field
import os

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import User, WorldSetting, Character
from app.schemas.project import BrainstormRequest, BrainstormApplyRequest
from app.services.llm_factory import LLMFactory
from app.services.agents import BrainstormAgent, PlanningAuditorAgent


class PlanningAuditRequest(BaseModel):
    """선택적으로 UI 상의 임시 추천안을 함께 검수할 때 사용."""
    lores: Optional[List[dict]] = Field(default=None, description="임시 세계관 추천안 (없으면 DB만 사용)")
    characters: Optional[List[dict]] = Field(default=None, description="임시 캐릭터 추천안 (없으면 DB만 사용)")

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

    # 4. 기존 DB 저장된 정보와 임시 기획안 정보 병합 (중복 추천/기획 겹침 방지)
    from sqlmodel import select
    stmt_lores = select(WorldSetting).where(WorldSetting.project_id == project_id)
    stmt_chars = select(Character).where(Character.project_id == project_id)
    db_lores = (await session.execute(stmt_lores)).scalars().all()
    db_chars = (await session.execute(stmt_chars)).scalars().all()

    merged_lores = []
    for l in db_lores:
        merged_lores.append({"keyword": l.keyword, "category": l.category, "description": l.description})
    existing_keywords = {l["keyword"].strip().lower() for l in merged_lores}
    for l in (req.current_lores or []):
        k_clean = l.get("keyword", "").strip().lower()
        if k_clean and k_clean not in existing_keywords:
            merged_lores.append(l)
            existing_keywords.add(k_clean)

    merged_chars = []
    for c in db_chars:
        merged_chars.append({"name": c.name, "importance": c.importance, "description": c.description})
    existing_names = {c["name"].strip().lower() for c in merged_chars}
    for c in (req.current_characters or []):
        n_clean = c.get("name", "").strip().lower()
        if n_clean and n_clean not in existing_names:
            merged_chars.append(c)
            existing_names.add(n_clean)

    # 5. 에이전트 구동
    agent = BrainstormAgent(model)
    try:
        result = await agent.run(
            project_title=project.title,
            project_synopsis=project.synopsis,
            user_instruction=req.user_instruction,
            current_lores=merged_lores,
            current_characters=merged_chars,
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

    # 2. 세계관 일괄 저장 (동일 키워드 존재 시 업데이트, 없을 시 신규 추가)
    from sqlmodel import select
    added_lores = 0
    updated_lores = 0
    for lore in req.lores:
        keyword_clean = lore["keyword"].strip()
        stmt = select(WorldSetting).where(
            WorldSetting.project_id == project_id,
            WorldSetting.keyword == keyword_clean
        )
        db_lore = (await session.execute(stmt)).scalar_one_or_none()
        
        if db_lore:
            db_lore.category = lore["category"]
            db_lore.description = lore["description"]
            updated_lores += 1
        else:
            db_lore = WorldSetting(
                project_id=project_id,
                keyword=keyword_clean,
                category=lore["category"],
                description=lore["description"],
            )
            session.add(db_lore)
            added_lores += 1

    # 3. 캐릭터 일괄 저장 (동일 이름 존재 시 업데이트, 없을 시 신규 추가)
    added_characters = 0
    updated_characters = 0
    for char in req.characters:
        name_clean = char["name"].strip()
        stmt = select(Character).where(
            Character.project_id == project_id,
            Character.name == name_clean
        )
        db_char = (await session.execute(stmt)).scalar_one_or_none()
        
        if db_char:
            db_char.importance = char["importance"]
            db_char.description = char["description"]
            updated_characters += 1
        else:
            db_char = Character(
                project_id=project_id,
                name=name_clean,
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
        "updated_lores": updated_lores,
        "added_characters": added_characters,
        "updated_characters": updated_characters,
    }


@router.post("/audit")
async def audit_planning_and_characters(
    project_id: int,
    req: Optional[PlanningAuditRequest] = Body(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    프로젝트 시놉시스·세계관 설정집·캐릭터 시트를 교차 검수합니다.
    요청 body에 lores/characters가 있으면 DB 저장분과 병합해 함께 진단합니다.
    """
    if req is None:
        req = PlanningAuditRequest()

    project = await check_project_owner(project_id, current_user, session)

    if not project.synopsis or not project.synopsis.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트 시놉시스가 비어 있습니다. [프로젝트 설정]에서 시놉시스를 먼저 입력해 주세요.",
        )

    from sqlmodel import select

    db_lores = (await session.execute(
        select(WorldSetting).where(WorldSetting.project_id == project_id)
    )).scalars().all()
    db_chars = (await session.execute(
        select(Character).where(Character.project_id == project_id)
    )).scalars().all()

    merged_lores = [
        {"keyword": l.keyword, "category": l.category, "description": l.description}
        for l in db_lores
    ]
    existing_kw = {l["keyword"].strip().lower() for l in merged_lores}
    for l in (req.lores or []):
        k = (l.get("keyword") or "").strip().lower()
        if k and k not in existing_kw:
            merged_lores.append(l)
            existing_kw.add(k)

    merged_chars = [
        {"name": c.name, "importance": c.importance, "description": c.description}
        for c in db_chars
    ]
    existing_names = {c["name"].strip().lower() for c in merged_chars}
    for c in (req.characters or []):
        n = (c.get("name") or "").strip().lower()
        if n and n not in existing_names:
            merged_chars.append(c)
            existing_names.add(n)

    if not merged_lores and not merged_chars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="검수할 세계관 설정 또는 캐릭터가 없습니다. AI 기획 추천을 생성하거나 설정집/캐릭터를 먼저 등록해 주세요.",
        )

    if os.getenv("TESTING") == "True":
        return {
            "is_passed": True,
            "score": 92,
            "summary": "기획 및 인물 설정 검수 통과 (테스트 픽스처)",
            "character_issues": [],
            "lore_issues": [],
            "contradictions": [],
            "suggestions": ["시놉시스와 주인공 동기를 한 문장으로 더 명확히 연결하면 좋습니다."],
        }

    try:
        model = LLMFactory.get_model_for_agent(project, "judge", temperature=0.2)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM 모델 생성 실패: {e}. 프로젝트 설정에서 API Key가 올바르게 설정되어 있는지 확인하세요.",
        )

    agent = PlanningAuditorAgent(model)
    try:
        report = await agent.run(
            project_title=project.title,
            project_synopsis=project.synopsis,
            lores=merged_lores,
            characters=merged_chars,
        )
        return report.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"기획·인물 검수 에이전트 실행 중 오류: {e}",
        )
