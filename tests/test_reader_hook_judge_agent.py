import pytest
from unittest.mock import MagicMock
from packages.agents.reader_hook_judge_agent import ReaderHookJudgeAgent
from packages.schemas.agent_schemas import EpisodeCard

def test_reader_hook_judge_agent_basic():
    # Mock repository and memory_store
    mock_repo = MagicMock()
    mock_memory = MagicMock()
    
    agent = ReaderHookJudgeAgent(repository=mock_repo, memory_store=mock_memory)
    
    novel_id = "test_novel"
    draft_id = "test_draft"
    draft_text = "The hero stood at the edge of the cliff. He looked down and saw the ancient key. 'Is this the way?' he wondered. Suddenly, the ground shook violently!"
    episode_plan = EpisodeCard(
        episode_number=1,
        arc_number=1,
        arc_title="The Beginning",
        episode_id="ep1",
        title_working="The Key",
        objective="Find the key",
        theme="Discovery",
        hook_opening="Start with a mystery",
        conflict="The cliff is crumbling",
        outcome="He finds the key",
        cliffhanger="The ground shakes and he falls",
        target_length=5000,
        scene_count=4
    )
    open_threads = ["Where did the key come from?", "Who is the mysterious stranger?"]
    
    result = agent.judge(novel_id, draft_id, draft_text, episode_plan, open_threads)
    
    # Verify result types and ranges
    assert result.hook_strength >= 0 and result.hook_strength <= 100
    assert result.curiosity_gap_score >= 0 and result.curiosity_gap_score <= 100
    assert result.emotional_aftertaste_score >= 0 and result.emotional_aftertaste_score <= 100
    assert result.next_episode_pull_score >= 0 and result.next_episode_pull_score <= 100
    assert result.overall_hook_score >= 0 and result.overall_hook_score <= 100
    assert isinstance(result.hook_suggestions, list)
    
    # Verify repository call
    mock_repo.create_validation.assert_called_once()
    args, kwargs = mock_repo.create_validation.call_args
    assert kwargs['novel_id'] == novel_id
    assert kwargs['validation_type'] == "hook"
    assert kwargs['target_entity_id'] == draft_id

def test_reader_hook_judge_agent_empty_input():
    mock_repo = MagicMock()
    mock_memory = MagicMock()
    agent = ReaderHookJudgeAgent(repository=mock_repo, memory_store=mock_memory)
    
    episode_plan = EpisodeCard(
        episode_number=1, arc_number=1, arc_title="T", episode_id="e1", 
        title_working="T", objective="O", theme="T", hook_opening="H", 
        conflict="C", outcome="O", cliffhanger="C", target_length=5000, scene_count=4
    )
    
    result = agent.judge("n1", "d1", "", episode_plan, [])
    
    assert result.overall_hook_score >= 0
    assert result.overall_hook_score <= 100
