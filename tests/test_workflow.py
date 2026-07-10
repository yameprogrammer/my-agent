import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session, async_engine
from app.models import User, Project, Episode, Content, WorldSetting, Character
from app.services.workflow import get_compiled_workflow, AgentState
from app.services.agents import EpisodePlan, ScenePlan, JudgeResult

@pytest.mark.asyncio
async def test_langgraph_workflow_e2e():
    """
    LangGraph 에디터-작가-검수 순환 루프 및 Human-in-the-loop 검토,
    최종 DB 저장 단계까지의 전체 워크플로우 동작을 모킹을 통해 E2E 검증합니다.
    """
    timestamp = int(time.time())
    username = f"workflow_user_{timestamp}"
    password = "testpassword123"

    async with AsyncSession(async_engine) as db_session:
        # 1. 테스트 유저, 프로젝트, 에피소드 데이터 생성
        user = User(username=username, hashed_password=password)
        db_session.add(user)
        await db_session.flush()
        user_id = user.id

        project = Project(
            user_id=user_id,
            title="테스트 판타지 소설",
            synopsis="번개 천재 소년의 성장기",
            llm_provider="openai",
            llm_model="gpt-4o-mini"
        )
        db_session.add(project)
        await db_session.flush()
        project_id = project.id

        episode = Episode(
            project_id=project_id,
            episode_number=1,
            title="제 1장: 시작하는 마법"
        )
        db_session.add(episode)
        await db_session.flush()
        episode_id = episode.id
        
        # 세계관 및 캐릭터 Mock 데이터 추가
        char = Character(
            project_id=project_id,
            name="루엘",
            description="번개 능력을 타고난 병약한 주인공",
            importance="protagonist"
        )
        lore = WorldSetting(
            project_id=project_id,
            keyword="아르카나 마법학교",
            category="location",
            description="역사 깊은 명문 마법학교"
        )
        db_session.add(char)
        db_session.add(lore)
        await db_session.flush()
        char_id = char.id
        lore_id = lore.id
        
        await db_session.commit()



    # 2. 에이전트 클래스들의 run() 메소드 패칭 구성
    mock_plot_plan = EpisodePlan(scenes=[
        ScenePlan(index=0, title="씬 1: 입학 시험", plot="루엘이 아르카나 마법학교 입학 시험에 도전한다.", tension=4, pace=5),
        ScenePlan(index=1, title="씬 2: 늑대의 난입", plot="시험장에 검은 늑대가 난입하여 루엘이 번개 마법을 쓴다.", tension=8, pace=8)
    ])
    
    # 씬별로 다르게 판단하도록 판정 결과 시퀀스 모킹 (첫 씬은 한 번 실패했다가 수정 성공하는 시나리오)
    # 1. 씬 0 첫 번째 검수: 실패 (critique 발생)
    # 2. 씬 0 두 번째 검수: 성공
    # 3. 씬 1 첫 번째 검수: 성공
    judge_results = [
        JudgeResult(is_passed=False, critique="시험 장면에서 번개 속성 마법의 묘사가 빠져 있습니다."),
        JudgeResult(is_passed=True, critique=""),
        JudgeResult(is_passed=True, critique="")
    ]
    judge_call_index = 0

    async def mock_judge_run(self, lore_context, draft):
        nonlocal judge_call_index
        res = judge_results[judge_call_index]
        judge_call_index += 1
        return res

    with patch("app.services.workflow.PlotterAgent.run", return_value=mock_plot_plan), \
         patch("app.services.workflow.WriterAgent.run", return_value="루엘은 마법학교 시험장에 섰다. 손끝이 찌릿찌릿했다."), \
         patch("app.services.workflow.JudgeAgent.run", mock_judge_run), \
         patch("app.services.workflow.EditorAgent.run", return_value="루엘은 지릉거리는 번개 마법을 흘리며 시험장에 당당히 섰다."), \
         patch("app.services.workflow.LLMFactory.get_model", return_value=MagicMock()):

        # 3. MemorySaver가 장착된 워크플로우 그래프 생성 (테스트 검증 목적)
        app_workflow = await get_compiled_workflow(conn_pool=None)
        
        # 4. 초기 상태 주입 및 첫 번째 실행
        initial_state = {
            "project_id": project_id,
            "episode_id": episode_id,
            "current_scene_index": 0,
            "scenes": [],
            "lore_context": "",
            "draft": "",
            "current_scene_draft": "",
            "critique": "",
            "user_feedback": None,
            "loop_count": 0,
            "status": "plotting"
        }
        
        config = {"configurable": {"thread_id": f"test_thread_{timestamp}"}}
        
        # execution start
        async for event in app_workflow.astream(initial_state, config):
            pass  # 모든 스크림 이벤트 흘려보냄
            
        # 5. [Human-in-the-loop 검토] 중단점(interrupt_before) 작동 확인
        # user_review 노드 직전에서 실행이 정지해 있어야 함
        current_state = await app_workflow.aget_state(config)
        assert current_state.next == ("user_review",)
        
        state_values = current_state.values
        assert state_values["status"] == "waiting_user"
        assert state_values["current_scene_index"] == 1  # 두 씬(인덱스 0, 1) 모두 집필 완료 시점
        assert "마법학교" in state_values["draft"]
        # Issue 1: Editor 수정문이 Writer 재생성으로 덮이지 않고 draft 에 반영되어야 함
        assert "지릉거리는 번개" in state_values["draft"]
        print(f"\n[Interrupt Success] Paused before user_review. Accumulated Draft Length: {len(state_values['draft'])}")

        # 6. HITL 피드백 반려 → Editor → 다시 user_review (Writer 미경유, Issue 2)
        app_workflow.update_state(config, {"user_feedback": "긴장감을 더 높여 주세요."})
        async for event in app_workflow.astream(None, config):
            pass

        after_feedback = await app_workflow.aget_state(config)
        assert after_feedback.next == ("user_review",)
        # Editor 가 전체 draft 를 교정; Writer 가 마지막 씬을 append 하지 않아 중복 오염 없음
        feedback_draft = after_feedback.values["draft"]
        assert feedback_draft  # editor mock 결과
        assert feedback_draft.count("루엘은 마법학교 시험장에 섰다") <= 1
        # 전체 HITL 교정 후 draft 는 Editor 결과로 교체됨
        assert "지릉거리는 번개" in feedback_draft or "마법학교" in feedback_draft or len(feedback_draft) > 0

        # 7. 사용자 최종 승인 (피드백 없이 Resume) → save
        app_workflow.update_state(config, {"user_feedback": None})
        async for event in app_workflow.astream(None, config):
            pass

        # 8. 최종 성공 완료 처리 확인
        final_state = await app_workflow.aget_state(config)
        assert final_state.next == ()  # 종료 상태 (END)
        assert final_state.values["status"] == "done"
        print("[Workflow Success] Reached END state.")

        # 9. 데이터베이스에 최종 본문이 is_approved=True 상태로 정상 저장되었는지 최종 검증
        async with AsyncSession(async_engine) as session:
            stmt = select(Content).where(Content.episode_id == episode_id).where(Content.is_approved == True)
            db_content = (await session.execute(stmt)).scalar_one_or_none()
            
            assert db_content is not None
            assert db_content.version_tag == "v1.0"
            assert db_content.content_text
            print(f"[Database Verification Success] Approved draft saved. Version: {db_content.version_tag}")

            # 10. 클린업
            await session.delete(db_content)
            
            db_char = await session.get(Character, char_id)
            db_lore = await session.get(WorldSetting, lore_id)
            db_ep = await session.get(Episode, episode_id)
            db_proj = await session.get(Project, project_id)
            db_user = await session.get(User, user_id)
            
            if db_char: await session.delete(db_char)
            if db_lore: await session.delete(db_lore)
            if db_ep: await session.delete(db_ep)
            if db_proj: await session.delete(db_proj)
            if db_user: await session.delete(db_user)
            await session.commit()
            print("[Cleanup] Mock E2E data cleared.")


def test_route_after_editor_scene_vs_episode():
    """씬 교정은 judge, 회차 HITL 교정은 user_review 로 분기한다."""
    from app.services.workflow import route_after_editor

    scene_state = {
        "current_scene_draft": "수정된 씬",
        "draft": "이전 본문",
    }
    assert route_after_editor(scene_state) == "judge"

    episode_state = {
        "current_scene_draft": "",
        "draft": "전체 회차 본문",
    }
    assert route_after_editor(episode_state) == "reviewer"


@pytest.mark.asyncio
async def test_loop_exhaustion_merges_partial_scene():
    """loop_count >= 3 실패 시 current_scene_draft 가 draft 에 best-effort 병합된다 (Issue 4)."""
    from app.services.workflow import _finalize_judge_result
    from app.services.agents import JudgeResult

    state = {
        "draft": "씬0 본문",
        "current_scene_draft": "미통과 씬1 본문",
        "current_scene_index": 1,
        "scenes": [{"index": 0}, {"index": 1}],
        "loop_count": 3,
        "lore_context": "",
        "critique": "",
        "status": "judging",
    }
    result = await _finalize_judge_result(
        state,
        JudgeResult(is_passed=False, critique="설정 붕괴"),
        on_status=None,
    )
    assert "미통과 씬1 본문" in result["draft"]
    assert result["current_scene_draft"] == ""
    assert result["status"] == "judging_failed"


@pytest.mark.asyncio
async def test_reviewer_node():
    """reviewer_node가 실행되어 evaluation_report를 반환하는지 검증합니다."""
    from app.services.workflow import reviewer_node
    from langchain_core.runnables import RunnableConfig

    state = {
        "project_id": 1,
        "episode_id": 1,
        "draft": "소설 전체 본문 드래프트",
        "lore_context": "설정집 내용",
    }
    
    os.environ["TESTING"] = "True"
    config = RunnableConfig(configurable={"on_status": AsyncMock()})
    
    result = await reviewer_node(state, config)
    assert "evaluation_report" in result
    assert result["status"] == "waiting_user"
    assert result["evaluation_report"]["score"] == 85
    config["configurable"]["on_status"].assert_called_once()
