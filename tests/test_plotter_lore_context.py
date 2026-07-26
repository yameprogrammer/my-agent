"""IMP-08: Plotter 컨텍스트 필터 — 중요 인물 우선·상한."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rag import build_plotter_lore_context


@pytest.mark.asyncio
async def test_build_plotter_lore_prefers_major_characters():
    project = MagicMock()
    project.id = 1

    protag = MagicMock()
    protag.name = "아린"
    protag.importance = "protagonist"
    protag.description = "주인공"

    minor = MagicMock()
    minor.name = "행인A"
    minor.importance = "minor"
    minor.description = "스쳐 지나가는 행인"

    named_minor = MagicMock()
    named_minor.name = "마법사"
    named_minor.importance = "minor"
    named_minor.description = "개요에 등장"

    char_result = MagicMock()
    char_result.scalars.return_value.all.return_value = [protag, minor, named_minor]

    session = AsyncMock()
    session.get = AsyncMock(return_value=project)

    async def fake_execute(stmt):
        # Character select vs others — always return chars for first call pattern
        return char_result

    session.execute = AsyncMock(side_effect=fake_execute)

    hybrid = "=== [세계관 및 설정집] ===\n- 왕국: 설정\n"

    with patch(
        "app.services.rag.retrieve_relevant_lores",
        new=AsyncMock(return_value=hybrid),
    ):
        ctx = await build_plotter_lore_context(
            session,
            project_id=1,
            episode_title="마법사의 경고",
            episode_outline="아린이 마법사를 만난다.",
        )

    assert "필터됨" in ctx or "등장인물" in ctx
    assert "아린" in ctx
    assert "마법사" in ctx  # outline keyword
    assert "왕국" in ctx
