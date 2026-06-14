import pytest
from unittest.mock import MagicMock
from packages.agents.style_judge_agent import StyleJudgeAgent
from packages.schemas.agent_schemas import SceneBeatSpec, StyleJudgmentResult

def test_style_judge_agent_basic():
    # Mock dependencies
    mock_repo = MagicMock()
    mock_mem = MagicMock()
    
    agent = StyleJudgeAgent(repository=mock_repo, memory_store=mock_mem)
    
    draft_text = "그는 천천히 걸었다. 그리고 멈췄다.\n\n그는 하늘을 보았다."
    scene_beats = [
        SceneBeatSpec(
            scene_order=1,
            objective="걷기",
            conflict="멈춤",
            outcome="하늘 보기",
            emotion_shift="평온"
        )
    ]
    style_rules = ["문장은 짧게", "묘사는 간결하게"]
    
    result = agent.judge(
        novel_id="test_novel",
        draft_id="test_draft",
        draft_text=draft_text,
        scene_beats=scene_beats,
        style_rules=style_rules
    )
    
    assert isinstance(result, StyleJudgmentResult)
    assert 0 <= result.pacing_score <= 100
    assert 0 <= result.readability_score <= 100
    assert 0 <= result.tone_consistency_score <= 100
    assert 0 <= result.webnovel_fit_score <= 100
    assert 0 <= result.overall_score <= 100
    assert isinstance(result.rewrite_suggestions, list)
    
    # Verify repository call
    mock_repo.create_validation.assert_called_once()
    args = mock_repo.create_validation.call_args[1]
    assert args['validation_type'] == "style"
    assert args['novel_id'] == "test_novel"

def test_style_judge_agent_empty_inputs():
    mock_repo = MagicMock()
    mock_mem = MagicMock()
    agent = StyleJudgeAgent(repository=mock_repo, memory_store=mock_mem)
    
    result = agent.judge(
        novel_id="test_novel",
        draft_id=None,
        draft_text="",
        scene_beats=[],
        style_rules=[]
    )
    
    assert result.overall_score >= 0
    mock_repo.create_validation.assert_called_once()
