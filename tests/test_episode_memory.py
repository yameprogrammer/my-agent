"""
IMP-07: 회차 연속성 메모리 — 추출 요약·이전 회차 컨텍스트 조립 단위 테스트.
DB 불필요 경로 + AsyncSession 모킹 최소 경로.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.episode_memory import (
    extractive_summary,
    build_previous_episodes_context,
    update_episode_summary,
)


def test_extractive_summary_short_text_passthrough():
    text = "짧은 본문입니다."
    assert extractive_summary(text) == text


def test_extractive_summary_long_includes_head_and_tail():
    paras = [f"문단 {i} " + ("가" * 80) for i in range(20)]
    long = "\n\n".join(paras)
    out = extractive_summary(long, max_chars=400)
    assert "문단 0" in out
    assert "중략" in out or "…" in out
    # 후반 문단 일부 포함
    assert any(f"문단 {i}" in out for i in range(15, 20))
    assert len(out) <= 450


@pytest.mark.asyncio
async def test_build_previous_context_first_episode():
    session = AsyncMock()
    ctx = await build_previous_episodes_context(session, project_id=1, current_episode_number=1)
    assert "첫 회차" in ctx
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_build_previous_context_uses_summaries():
    ep1 = MagicMock()
    ep1.id = 10
    ep1.episode_number = 1
    ep1.title = "시작"
    ep1.summary = "주인공이 마을을 떠났다. 말미 훅: 검은 편지."
    ep1.outline = None

    ep2 = MagicMock()
    ep2.id = 11
    ep2.episode_number = 2
    ep2.title = "추적"
    ep2.summary = "추적자가 나타났다."
    ep2.outline = None

    # session.execute returns scalars().all() with episodes ordered desc then reversed in func
    result = MagicMock()
    result.scalars.return_value.all.return_value = [ep2, ep1]  # desc order from query
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    ctx = await build_previous_episodes_context(
        session, project_id=1, current_episode_number=3, n=3
    )
    assert "이전 회차 연속성" in ctx
    assert "1화" in ctx and "시작" in ctx
    assert "검은 편지" in ctx
    assert "2화" in ctx and "추적" in ctx


@pytest.mark.asyncio
async def test_update_episode_summary_extractive_fallback():
    episode = MagicMock()
    episode.id = 5
    episode.project_id = 1
    episode.episode_number = 1
    episode.title = "테스트"
    episode.summary = None

    session = AsyncMock()
    session.get = AsyncMock(return_value=episode)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    text = "승인된 본문 첫 문장.\n\n" + ("중간 " * 100) + "\n\n결말 훅 문장."
    with patch("app.services.episode_memory.llm_summarize_episode", new=AsyncMock(return_value=None)):
        summary = await update_episode_summary(
            session, 5, text, project=None, use_llm=False
        )
    assert summary
    assert episode.summary == summary
    session.commit.assert_awaited()
