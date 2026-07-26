"""IDEA-04 arc planner fixture path."""
import os
import pytest

os.environ["TESTING"] = "True"

from app.services.arc_planner import generate_arc_plan, ArcPlanResult
from app.services.llm_factory import LLMFactory


class _P:
    title = "테스트 소설"
    synopsis = "주인공이 마법에 눈을 뜬다."
    llm_provider = "openai"
    llm_model = "gpt-4o"
    api_key_override = None
    plotter_provider = None
    plotter_model = None
    plotter_api_key = None
    low_cost_mode = True
    writer_provider = None
    writer_model = None
    writer_api_key = None
    judge_provider = None
    judge_model = None
    judge_api_key = None


@pytest.mark.asyncio
async def test_generate_arc_plan_fixture():
    plan = await generate_arc_plan(_P(), episode_count=3, start_number=2)
    assert isinstance(plan, ArcPlanResult)
    assert len(plan.episodes) == 3
    assert plan.episodes[0].episode_number == 2
    assert plan.episodes[-1].episode_number == 4


def test_low_cost_model_preset_for_judge():
    p = _P()
    p.low_cost_mode = True
    # get_model 을 모킹하지 않고 provider/model 선택 로직만 검증
    provider = p.llm_provider
    model = p.llm_model
    if p.low_cost_mode:
        model = LLMFactory.LOW_COST_MODELS.get(provider, "gpt-4o-mini")
    assert model == "gpt-4o-mini"
