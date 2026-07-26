"""
IMP-07 / IDEA-01: 회차 간 연속성 — 승인본 요약 저장 및 이전 회차 컨텍스트 조립.
"""
from __future__ import annotations

import logging
import os
import re
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Content, Episode, Project

logger = logging.getLogger(__name__)

# 다음 회차에 주입할 직전 회차 수
DEFAULT_PREV_EPISODES = 3
# 추출 요약 상한 (문자)
EXTRACTIVE_MAX_CHARS = 1200
# LLM 요약 대상 본문 상한
SUMMARY_SOURCE_MAX = 6000


def extractive_summary(text: str, max_chars: int = EXTRACTIVE_MAX_CHARS) -> str:
    """
    LLM 없이 본문 앞·뒤 구간을 조합한 추출 요약.
    결말/훅 보존을 위해 후반부를 더 비중 있게 담는다.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned

    # 문단 단위로 분리
    paras = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    if not paras:
        head = cleaned[: max_chars // 3]
        tail = cleaned[-(max_chars * 2 // 3) :]
        return f"{head}\n…\n{tail}"

    head_budget = max_chars // 3
    tail_budget = max_chars - head_budget - 10
    head_parts: List[str] = []
    tail_parts: List[str] = []
    n = 0
    for p in paras:
        if n + len(p) + 1 > head_budget:
            break
        head_parts.append(p)
        n += len(p) + 1
    n = 0
    for p in reversed(paras):
        if n + len(p) + 1 > tail_budget:
            break
        tail_parts.insert(0, p)
        n += len(p) + 1

    head_s = "\n\n".join(head_parts) if head_parts else cleaned[:head_budget]
    tail_s = "\n\n".join(tail_parts) if tail_parts else cleaned[-tail_budget:]
    return f"{head_s}\n\n…(중략)…\n\n{tail_s}"


async def llm_summarize_episode(
    project: Project,
    episode: Episode,
    content_text: str,
) -> Optional[str]:
    """Plotter LLM 으로 회차 요약 생성. 실패 시 None."""
    if os.getenv("TESTING") == "True":
        return None
    source = (content_text or "").strip()
    if not source:
        return None
    if len(source) > SUMMARY_SOURCE_MAX:
        source = source[:SUMMARY_SOURCE_MAX] + "\n…(이하 생략)"

    try:
        from app.services.llm_factory import LLMFactory
        from langchain_core.prompts import ChatPromptTemplate

        llm = LLMFactory.get_model_for_agent(project, "plotter", temperature=0.3)
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "당신은 장편 웹소설 연재 continuity 담당 편집자입니다. "
                "아래 회차 본문을 다음 화 작가가 바로 이어 쓸 수 있도록 요약하십시오.\n"
                "포함: 주요 사건 경과, 인물 상태/위치/관계 변화, 미해결 갈등, 회차 말미 훅.\n"
                "제외: 문체 평, 메타 코멘트.\n"
                "분량: 한국어 8~15문장. 요약 본문만 출력.",
            ),
            (
                "user",
                "회차: {episode_number}화 「{title}」\n\n본문:\n{text}",
            ),
        ])
        chain = prompt | llm
        result = await chain.ainvoke({
            "episode_number": episode.episode_number,
            "title": episode.title,
            "text": source,
        })
        text = getattr(result, "content", None) or str(result)
        if isinstance(text, list):
            # multimodal content blocks
            text = "".join(
                (b.get("text") if isinstance(b, dict) else str(b)) for b in text
            )
        text = (text or "").strip()
        return text[:2000] if text else None
    except Exception as e:
        logger.warning(
            "LLM episode summary failed (episode_id=%s): %s",
            getattr(episode, "id", None),
            e,
        )
        return None


async def update_episode_summary(
    session: AsyncSession,
    episode_id: int,
    content_text: str,
    *,
    project: Optional[Project] = None,
    use_llm: bool = True,
) -> str:
    """
    승인된 본문으로 Episode.summary 를 갱신한다.
    LLM 우선, 실패 시 추출 요약.
    """
    episode = await session.get(Episode, episode_id)
    if not episode:
        return ""

    summary: Optional[str] = None
    if use_llm:
        proj = project
        if proj is None:
            proj = await session.get(Project, episode.project_id)
        if proj is not None:
            summary = await llm_summarize_episode(proj, episode, content_text)

    if not summary:
        summary = extractive_summary(content_text)

    episode.summary = summary or None
    session.add(episode)
    await session.commit()
    await session.refresh(episode)
    return summary or ""


async def get_approved_text_for_episode(
    session: AsyncSession,
    episode_id: int,
) -> Optional[str]:
    stmt = (
        select(Content)
        .where(Content.episode_id == episode_id, Content.is_approved == True)  # noqa: E712
        .order_by(Content.created_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    c = res.scalar_one_or_none()
    return c.content_text if c else None


async def build_previous_episodes_context(
    session: AsyncSession,
    project_id: int,
    current_episode_number: int,
    *,
    n: int = DEFAULT_PREV_EPISODES,
) -> str:
    """
    직전 N화의 요약(또는 승인본 추출 요약)을 Plotter/Writer 주입용 문자열로 조립.
    """
    if current_episode_number <= 1:
        return "(첫 회차 — 이전 회차 없음)"

    stmt = (
        select(Episode)
        .where(
            Episode.project_id == project_id,
            Episode.episode_number < current_episode_number,
        )
        .order_by(Episode.episode_number.desc())
        .limit(n)
    )
    res = await session.execute(stmt)
    prev_eps = list(reversed(res.scalars().all()))  # 오래된 순

    if not prev_eps:
        return "(이전 회차 데이터 없음)"

    blocks: List[str] = []
    for ep in prev_eps:
        body = (ep.summary or "").strip()
        if not body:
            approved = await get_approved_text_for_episode(session, ep.id)
            if approved:
                body = extractive_summary(approved, max_chars=800)
            else:
                body = (ep.outline or "").strip() or "(승인 본문·요약 없음)"
        blocks.append(
            f"### {ep.episode_number}화 「{ep.title}」\n{body}"
        )

    return (
        "=== [이전 회차 연속성 메모리] ===\n"
        "아래는 이미 승인된 직전 회차들의 요약입니다. "
        "톤·인물 상태·미해결 복선을 이어 쓰십시오.\n\n"
        + "\n\n".join(blocks)
    )
