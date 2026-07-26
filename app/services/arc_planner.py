"""
IDEA-04: 멀티 에피소드 아크 플래너 — 작품 시놉시스 기반 회차 outline 일괄 생성.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Episode, Project

logger = logging.getLogger(__name__)


class ArcEpisodePlan(BaseModel):
    episode_number: int
    title: str
    outline: str
    arc_beat: str = Field(default="", description="setup|rising|midpoint|climax|resolution 등")


class ArcPlanResult(BaseModel):
    overall_arc: str = ""
    episodes: List[ArcEpisodePlan] = Field(default_factory=list)


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
        raise


async def generate_arc_plan(
    project: Project,
    *,
    episode_count: int = 5,
    start_number: int = 1,
    extra_instruction: str = "",
) -> ArcPlanResult:
    """LLM 으로 회차 아크 계획 생성. TESTING 시 픽스처."""
    n = max(1, min(int(episode_count), 30))
    start = max(1, int(start_number))

    if os.getenv("TESTING") == "True":
        return ArcPlanResult(
            overall_arc="테스트 아크: 도입→갈등→절정",
            episodes=[
                ArcEpisodePlan(
                    episode_number=start + i,
                    title=f"테스트 {start + i}화",
                    outline=f"{start + i}화 개요 — 주인공이 사건을 마주한다.",
                    arc_beat=["setup", "rising", "midpoint", "climax", "resolution"][min(i, 4)],
                )
                for i in range(n)
            ],
        )

    from app.services.llm_factory import LLMFactory
    from langchain_core.prompts import ChatPromptTemplate

    llm = LLMFactory.get_model_for_agent(project, "plotter", temperature=0.6)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "당신은 장편 웹소설 시리즈 아키텍트입니다. 시놉시스를 바탕으로 "
            "연재용 회차 단위 아크를 설계합니다.\n"
            "JSON만 출력:\n"
            '{{"overall_arc":"전체 아크 한 단락","episodes":['
            '{{"episode_number":N,"title":"...","outline":"회차 개요 3~6문장","arc_beat":"setup|rising|midpoint|climax|resolution"}}'
            "]}}\n"
            f"episode_number 는 {start}부터 연속 {n}개.",
        ),
        (
            "user",
            "작품 제목: {title}\n시놉시스:\n{synopsis}\n"
            "추가 지시: {extra}\n"
            "회차 수: {count}, 시작 화수: {start}",
        ),
    ])
    chain = prompt | llm
    result = await chain.ainvoke({
        "title": project.title,
        "synopsis": project.synopsis or "(시놉시스 없음)",
        "extra": extra_instruction or "(없음)",
        "count": n,
        "start": start,
    })
    raw = getattr(result, "content", None) or str(result)
    if isinstance(raw, list):
        raw = "".join(
            (b.get("text") if isinstance(b, dict) else str(b)) for b in raw
        )
    data = _extract_json(raw)
    return ArcPlanResult.model_validate(data)


async def apply_arc_plan(
    session: AsyncSession,
    project_id: int,
    plan: ArcPlanResult,
    *,
    create_missing: bool = True,
    overwrite_outline: bool = True,
) -> dict:
    """
    계획된 회차를 DB에 반영.
    동일 episode_number 가 있으면 title/outline 갱신, 없으면 생성.
    """
    created, updated = 0, 0
    for ep in plan.episodes:
        stmt = select(Episode).where(
            Episode.project_id == project_id,
            Episode.episode_number == ep.episode_number,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        outline = ep.outline
        if ep.arc_beat:
            outline = f"[{ep.arc_beat}] {outline}"
        if existing:
            if overwrite_outline:
                existing.outline = outline
            if ep.title:
                existing.title = ep.title
            session.add(existing)
            updated += 1
        elif create_missing:
            session.add(Episode(
                project_id=project_id,
                episode_number=ep.episode_number,
                title=ep.title or f"{ep.episode_number}화",
                outline=outline,
            ))
            created += 1
    await session.commit()
    return {
        "created": created,
        "updated": updated,
        "overall_arc": plan.overall_arc,
        "episodes": [e.model_dump() for e in plan.episodes],
    }
