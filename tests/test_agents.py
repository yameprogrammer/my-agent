import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

from app.services.llm_factory import LLMFactory
from app.services.agents import (
    PlotterAgent, WriterAgent, JudgeAgent, EditorAgent,
    EpisodePlan, ScenePlan, JudgeResult
)

def test_llm_factory_creation():
    """
    LLMFactory가 제공자에 따라 올바른 LangChain 모델 객체를 생성하는지 검증합니다.
    """
    # 1. OpenAI
    openai_model = LLMFactory.get_model("openai", "gpt-4o-mini", api_key_override="test-openai-key")
    assert isinstance(openai_model, ChatOpenAI)
    assert openai_model.openai_api_key.get_secret_value() == "test-openai-key"

    # 2. Google
    google_model = LLMFactory.get_model("google", "gemini-1.5-flash", api_key_override="test-google-key")
    assert isinstance(google_model, ChatGoogleGenerativeAI)
    assert google_model.google_api_key.get_secret_value() == "test-google-key"

    # 3. Anthropic
    anthropic_model = LLMFactory.get_model("anthropic", "claude-3-haiku-20240307", api_key_override="test-anthropic-key")
    assert isinstance(anthropic_model, ChatAnthropic)
    assert anthropic_model.anthropic_api_key.get_secret_value() == "test-anthropic-key"

    # 4. Ollama
    ollama_model = LLMFactory.get_model("ollama", "llama3")
    assert isinstance(ollama_model, ChatOllama)
    assert ollama_model.model == "llama3"


@pytest.mark.asyncio
async def test_plotter_agent_run():
    """
    PlotterAgent가 입력을 받아 구조화된 EpisodePlan 계획을 생성하는지 검증합니다.
    """
    mock_model = MagicMock()
    agent = PlotterAgent(mock_model)
    
    # 구조화된 출력 Mock 데이터 정의
    expected_plan = EpisodePlan(scenes=[
        ScenePlan(index=0, title="씬 1: 숲속의 조우", plot="루엘이 숲을 걷다가 검은 늑대를 만난다.", tension=4, pace=5),
        ScenePlan(index=1, title="씬 2: 위기 극복", plot="늑대와 번개 마법으로 결투를 벌인다.", tension=8, pace=8)
    ])
    
    # 체인의 ainvoke를 직접 mock
    agent.chain = MagicMock()
    agent.chain.ainvoke = AsyncMock(return_value=expected_plan)

    result = await agent.run(
        project_synopsis="병약한 마법 천재의 성장물",
        episode_number=2,
        episode_title="제 2화: 늑대의 숲",
        episode_outline="숲에서 늑대를 만나는 이야기",
        lore_context="루엘: 번개 마법 사용, 체력 약함"
    )

    assert isinstance(result, EpisodePlan)
    assert len(result.scenes) == 2
    assert result.scenes[0].title == "씬 1: 숲속의 조우"
    assert result.scenes[1].tension == 8
    
    agent.chain.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_writer_agent_run():
    """
    WriterAgent가 집필 지침 및 이전 맥락을 반영하여 씬 텍스트를 집필하는지 검증합니다.
    """
    mock_model = MagicMock()
    agent = WriterAgent(mock_model)
    
    # 체인의 ainvoke를 직접 mock
    agent.chain = MagicMock()
    
    class MockContent:
        content = "어둠이 내려앉은 숲속에서 루엘의 지팡이가 빛났다."
        
    agent.chain.ainvoke = AsyncMock(return_value=MockContent())

    result = await agent.run(
        project_synopsis="성장 스토리",
        episode_number=1,
        episode_title="시작",
        lore_context="설정집 내용",
        previous_scenes_context="이전 줄거리 요약",
        scene_index=1,
        scene_title="늑대와의 첫 만남",
        scene_plot="늑대가 튀어나옴",
        tension_level=8,
        pace_level=9
    )

    assert result == "어둠이 내려앉은 숲속에서 루엘의 지팡이가 빛났다."
    agent.chain.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_judge_agent_run():
    """
    JudgeAgent가 초안을 세계관 설정과 비교하여 구조화된 검수 결과를 반환하는지 검증합니다.
    """
    mock_model = MagicMock()
    agent = JudgeAgent(mock_model)
    
    # 설정 충돌 발견 상황의 Mock 데이터
    expected_result = JudgeResult(
        is_passed=False,
        critique="설정상 루엘은 불 마법을 사용할 수 없는데, 본문에서 화염구를 날렸습니다."
    )
    
    agent.chain = MagicMock()
    agent.chain.ainvoke = AsyncMock(return_value=expected_result)

    result = await agent.run(
        lore_context="루엘: 오직 번개 마법만 구사 가능",
        draft="루엘은 손을 뻗어 거대한 화염구를 늑대에게 날려보냈다."
    )

    assert isinstance(result, JudgeResult)
    assert result.is_passed is False
    assert "화염구" in result.critique
    
    agent.chain.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_editor_agent_run():
    """
    EditorAgent가 피드백(Critique)을 수용하여 윤문 및 수정을 가하는지 검증합니다.
    """
    mock_model = MagicMock()
    agent = EditorAgent(mock_model)
    
    class MockContent:
        content = "루엘은 화염 대신 지릉거리는 번개를 쏘아 늑대를 저지했다."
        
    agent.chain = MagicMock()
    agent.chain.ainvoke = AsyncMock(return_value=MockContent())

    result = await agent.run(
        lore_context="루엘: 오직 번개 마법만 구사 가능",
        draft="루엘은 손을 뻗어 거대한 화염구를 늑대에게 날려보냈다.",
        critique="화염 마법 사용은 모순입니다. 번개 마법으로 바꾸십시오.",
        user_feedback="문장을 좀 더 극적으로 연출해 줘."
    )

    assert result == "루엘은 화염 대신 지릉거리는 번개를 쏘아 늑대를 저지했다."
    agent.chain.ainvoke.assert_called_once()
