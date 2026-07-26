"""
H3: write_mode polish_draft / continue_draft 단위 검증
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock

os.environ["TESTING"] = "True"

from app.services.workflow import (
    _synthetic_seed_scenes,
    normalize_locked_scenes,
    plotter_node,
    writer_node,
)


def test_synthetic_seed_scenes():
    polish = _synthetic_seed_scenes("polish_draft")
    assert len(polish) == 1
    assert "윤문" in polish[0]["title"]

    cont = _synthetic_seed_scenes("continue_draft")
    assert len(cont) == 1
    assert "이어" in cont[0]["title"]


@pytest.mark.asyncio
async def test_plotter_skips_for_polish_mode():
    state = {
        "project_id": 1,
        "episode_id": 1,
        "write_mode": "polish_draft",
        "seed_draft": "작가 초안 문장입니다.",
        "current_scene_index": 0,
        "scenes": [],
        "draft": "",
        "lore_context": "",
        "loop_count": 0,
        "status": "plotting",
    }
    on_status = AsyncMock()
    result = await plotter_node(state, {"configurable": {"on_status": on_status}})
    assert len(result["scenes"]) == 1
    assert result["draft"] == ""  # polish: empty base
    assert result["write_mode"] == "polish_draft"
    assert result["seed_draft"] == "작가 초안 문장입니다."


@pytest.mark.asyncio
async def test_plotter_continue_keeps_seed_as_draft():
    seed = "앞에 쓴 초안."
    state = {
        "project_id": 1,
        "episode_id": 1,
        "write_mode": "continue_draft",
        "seed_draft": seed,
        "current_scene_index": 0,
        "scenes": [],
        "draft": "",
        "lore_context": "",
        "loop_count": 0,
        "status": "plotting",
    }
    result = await plotter_node(state, {"configurable": {"on_status": AsyncMock()}})
    assert result["draft"] == seed
    assert result["scenes"][0]["title"]


def test_normalize_locked_scenes():
    raw = [
        {"title": "도입", "plot": "주인공이 학교에 간다", "tension": 3, "pace": 4},
        {"title": "절정", "plot": "충돌", "tension": 9, "pace": 8},
    ]
    out = normalize_locked_scenes(raw)
    assert len(out) == 2
    assert out[0]["index"] == 0
    assert out[1]["index"] == 1
    assert out[0]["plot"] == "주인공이 학교에 간다"

    with pytest.raises(ValueError):
        normalize_locked_scenes([])
    with pytest.raises(ValueError):
        normalize_locked_scenes([{"title": "x", "plot": ""}])


@pytest.mark.asyncio
async def test_plotter_scenes_locked_uses_client_scenes():
    locked = normalize_locked_scenes([
        {"title": "A", "plot": "사건 A", "tension": 5, "pace": 5},
    ])
    state = {
        "project_id": 1,
        "episode_id": 1,
        "write_mode": "scenes_locked",
        "seed_draft": "",
        "scenes": locked,
        "current_scene_index": 0,
        "draft": "",
        "lore_context": "",
        "loop_count": 0,
        "status": "plotting",
    }
    result = await plotter_node(state, {"configurable": {"on_status": AsyncMock()}})
    assert result["scenes"][0]["title"] == "A"
    assert result["write_mode"] == "scenes_locked"


@pytest.mark.asyncio
async def test_writer_node_polish_passes_write_mode(monkeypatch):
    """WriterAgent.run 이 write_mode=polish_draft 로 호출되는지 확인."""
    captured = {}

    async def fake_run(self, **kwargs):
        captured.update(kwargs)
        return "윤문된 본문"

    from app.services import agents as agents_mod
    monkeypatch.setattr(agents_mod.WriterAgent, "run", fake_run)

    state = {
        "project_id": 1,
        "episode_id": 1,
        "write_mode": "polish_draft",
        "seed_draft": "원초안",
        "current_scene_index": 0,
        "scenes": _synthetic_seed_scenes("polish_draft"),
        "draft": "",
        "lore_context": "설정",
        "loop_count": 0,
        "status": "writing",
        "current_scene_draft": "",
    }
    out = await writer_node(state, {"configurable": {}})
    assert out["current_scene_draft"] == "윤문된 본문"
    assert captured.get("write_mode") == "polish_draft"
    assert captured.get("seed_draft") == "원초안"
