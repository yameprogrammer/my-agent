"""
Phase 6: 지속 학습 엔진 (사후 회고 및 RAG 노하우) 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import Project, WritingKnowHow
from app.services.workflow import run_retrospective_and_learn_task
from app.services.rag import get_relevant_know_how_context
from app.services.agents.retrospective import RetrospectiveReport, SituationalKnowHowSchema


@pytest.mark.asyncio
async def test_run_retrospective_and_learn_task_success():
    """
    1. 회고 에이전트 분석 결과가 올바르게 스타일 가이드와 WritingKnowHow 테이블에 반영되는지 테스트합니다.
    """
    # 프로젝트 객체 생성
    project = Project(
        id=1,
        user_id=1,
        title="테스트 프로젝트",
        synopsis="마왕을 무찌르는 용사의 이야기",
        style_guide="원칙 1: 주인공은 반말을 사용한다.",
        llm_model="gpt-4o-mini",
        llm_provider="openai"
    )

    # 회고 결과 모킹
    report = RetrospectiveReport(
        global_style_updates=["원칙 2: 주인공은 경망스러운 한자어를 쓰지 않는다."],
        situational_know_how=[
            SituationalKnowHowSchema(
                category="action",
                context_trigger="검술 대결",
                problem_identified="전투 중 기사단장이 상스러운 욕을 사용함",
                lesson_learned="기사단장은 흥분해도 절대 욕을 하지 않고 존댓말을 유지할 것"
            )
        ]
    )

    # 에이전트 및 임베딩 함수 모킹 패치
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=report)

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    # project 로드 모킹
    mock_session.get = AsyncMock(return_value=project)
    
    # query execute 모킹
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=result_mock)

    mock_vector = [0.1] * 1536

    with patch("app.services.agents.RetrospectiveAgent", return_value=mock_agent), \
         patch("app.services.rag.generate_embedding", return_value=mock_vector), \
         patch("app.services.workflow.AsyncSession", return_value=mock_session), \
         patch("app.services.workflow.async_engine"), \
         patch("app.services.llm_factory.LLMFactory.get_model_for_agent", return_value=MagicMock()):
         
         await run_retrospective_and_learn_task(
             project_id=1,
             episode_id=10,
             outline="- Scene 1: 대련장에서 기사와 혈투",
             initial_draft="최초 AI 드래프트 텍스트",
             approved_text="최종 승인본 텍스트",
             feedback_history=["피드백 1", "피드백 2"]
         )

    # 1. 스타일 가이드가 병합 갱신되었는지 확인
    assert "원칙 2: 주인공은 경망스러운 한자어를 쓰지 않는다." in project.style_guide
    assert "원칙 1: 주인공은 반말을 사용한다." in project.style_guide

    # 2. WritingKnowHow 가 추가되었는지 확인
    # session.add 가 호출되었는지 검사 (WritingKnowHow 객체와 project 객체)
    added_objects = [call[0][0] for call in mock_session.add.call_args_list]
    know_how_instances = [obj for obj in added_objects if isinstance(obj, WritingKnowHow)]
    
    assert len(know_how_instances) == 1
    assert know_how_instances[0].category == "action"
    assert know_how_instances[0].context_trigger == "검술 대결"
    assert know_how_instances[0].problem_identified == "전투 중 기사단장이 상스러운 욕을 사용함"
    assert know_how_instances[0].lesson_learned == "기사단장은 흥분해도 절대 욕을 하지 않고 존댓말을 유지할 것"
    assert know_how_instances[0].embedding == mock_vector

    # 3. commit 호출 확인
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_relevant_know_how_context():
    """
    2. RAG 검색 시 임베딩 조회가 수행되고, 검색 결과 텍스트가 포맷팅되어 리턴되는지 검증합니다.
    """
    project = Project(
        id=1,
        user_id=1,
        title="테스트 프로젝트",
        llm_model="gpt-4o-mini",
        llm_provider="openai"
    )

    # RAG 결과 레코드 모킹
    kh = WritingKnowHow(
        project_id=1,
        episode_id=10,
        category="action",
        context_trigger="검술 대결",
        problem_identified="단장이 욕설을 사용함",
        lesson_learned="단장은 흥분해도 욕을 하지 말고 존댓말을 쓸 것"
    )

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=project)
    
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [kh]
    mock_session.execute = AsyncMock(return_value=result_mock)

    mock_vector = [0.1] * 1536

    with patch("app.services.rag.generate_embedding", return_value=mock_vector):
        context = await get_relevant_know_how_context(
            session=mock_session,
            project_id=1,
            scene_outline="아서 단장과의 대련 씬",
            limit=1,
            rag_threshold=0.4
        )

    # RAG 결과가 텍스트에 포함되었는지 검증
    assert "과거 집필 피드백을 통해 획득한 특수 지침" in context
    assert "검술 대결" in context
    assert "단장은 흥분해도 욕을 하지 말고 존댓말을 쓸 것" in context
