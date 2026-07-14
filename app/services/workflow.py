import os
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.core.database import async_engine
from app.models import Project, Episode, Content, WorldSetting, Character
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.services.llm_factory import LLMFactory
from langchain_core.runnables import RunnableConfig
from app.services.agents import (
    PlotterAgent, WriterAgent, JudgeAgent, EditorAgent, EpisodePlan, JudgeResult, ReviewerAgent, ReviewReport
)

# ==========================================
# 1. AgentState 정의 (LangGraph State)
# ==========================================

class AgentState(TypedDict):
    project_id: int
    episode_id: int
    current_scene_index: int
    scenes: List[dict]           # [{ "index": 0, "title": "...", "plot": "...", "tension": 7, "pace": 5 }]
    lore_context: str            # RAG 추출 설정 맥락
    draft: str                   # 에피소드 전체 본문 누적
    current_scene_draft: str     # 현재 집필 중인 씬 본문
    critique: str                # AI Judge의 설정 모순 검수 피드백
    user_feedback: Optional[str] # 사용자 입력 피드백 (반려 시 사용)
    loop_count: int              # AI 교정 루프 카운터 (무한 루프 방지)
    status: str                  # "plotting" | "writing" | "judging" | "waiting_user" | "done" | "failed"
    evaluation_report: Optional[dict] # 에피소드 종합 평가 보고서


# ==========================================
# 2. 그래프 노드 함수 구현 (Nodes)
# ==========================================

async def plotter_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Plotter 에이전트를 호출하여 에피소드를 여러 개의 씬으로 나눈 상세 스토리보드를 기획합니다.
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status("plotting", "에이전트가 씬 시놉시스를 계획하는 중입니다...")

    import os
    if os.getenv("TESTING") == "True":
        from unittest.mock import MagicMock
        llm = MagicMock()
        plotter = PlotterAgent(llm)
        plan = await plotter.run(
            project_synopsis="",
            episode_number=1,
            episode_title="",
            episode_outline="",
            lore_context=""
        )
        scenes_list = [
            {
                "index": s.index,
                "title": s.title,
                "plot": s.plot,
                "tension": s.tension,
                "pace": s.pace
            } for s in plan.scenes
        ]
        if on_status:
            await on_status("plotting", "스토리보드 기획이 완료되었습니다.", {"scenes": scenes_list})
        return {
            "scenes": scenes_list,
            "current_scene_index": 0,
            "draft": "",
            "current_scene_draft": "",
            "status": "plotting",
            "loop_count": 0
        }

    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        episode = await session.get(Episode, state["episode_id"])
        
        if not project or not episode:
            return {"status": "failed"}

        # 전체 설정집 및 등장인물 정보를 Plotter에게 전달하기 위해 로드
        lore_stmt = select(WorldSetting).where(WorldSetting.project_id == state["project_id"])
        lores = (await session.execute(lore_stmt)).scalars().all()
        
        char_stmt = select(Character).where(Character.project_id == state["project_id"])
        chars = (await session.execute(char_stmt)).scalars().all()
        
        lore_context = "=== 등장인물 설정 ===\n"
        lore_context += "\n".join([f"- {c.name} ({c.importance}): {c.description}" for c in chars])
        lore_context += "\n\n=== 세계관 및 설정집 ===\n"
        lore_context += "\n".join([f"- {ws.keyword} ({ws.category}): {ws.description}" for ws in lores])

        llm = LLMFactory.get_model_for_agent(project, "plotter", temperature=0.7)
        plotter = PlotterAgent(llm)
        plan = await plotter.run(
            project_synopsis=project.synopsis or "",
            episode_number=episode.episode_number,
            episode_title=episode.title,
            episode_outline=episode.outline or "",
            lore_context=lore_context
        )
        
        scenes_list = [
            {
                "index": s.index,
                "title": s.title,
                "plot": s.plot,
                "tension": s.tension,
                "pace": s.pace
            } for s in plan.scenes
        ]

        if on_status:
            await on_status("plotting", "스토리보드 기획이 완료되었습니다.", {"scenes": scenes_list})

        return {
            "scenes": scenes_list,
            "current_scene_index": 0,
            "draft": "",
            "current_scene_draft": "",
            "status": "plotting",
            "loop_count": 0
        }


from app.services.rag import retrieve_relevant_lores

async def rag_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    현재 집필하려는 씬 정보에 맞추어 캐릭터 설정 및 세계관 설정집에서 관련 맥락을 검색해 주입합니다.
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status("writing", f"씬 {state['current_scene_index']} 관련 설정을 추출하는 중입니다...")

    async with AsyncSession(async_engine) as session:
        project_id = state["project_id"]
        current_scene = state["scenes"][state["current_scene_index"]]
        
        lore_context = await retrieve_relevant_lores(
            session=session,
            project_id=project_id,
            scene_title=current_scene["title"],
            scene_plot=current_scene["plot"]
        )
        
        return {
            "lore_context": lore_context,
            "status": "writing"
        }


async def writer_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Writer 에이전트를 호출하여 RAG 설정 및 이전 맥락을 토대로 현재 씬의 본문을 작성합니다.
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    on_chunk = configurable.get("on_chunk")
    if on_status:
        await on_status("writing", f"씬 {state['current_scene_index']} 본문을 집필하는 중입니다...")

    import os
    if os.getenv("TESTING") == "True":
        from unittest.mock import MagicMock
        on_reasoning = configurable.get("on_reasoning")
        writer = WriterAgent(MagicMock())
        previous_context = state["draft"] or "이전 씬 진행 사항 없음"
        current_scene = state["scenes"][state["current_scene_index"]]
        scene_draft = await writer.run(
            project_synopsis="",
            episode_number=1,
            episode_title="",
            lore_context=state["lore_context"],
            previous_scenes_context=previous_context,
            scene_index=state["current_scene_index"],
            scene_title=current_scene["title"],
            scene_plot=current_scene["plot"],
            tension_level=current_scene["tension"],
            pace_level=current_scene["pace"],
            on_chunk=on_chunk,
            on_reasoning=on_reasoning
        )
        return {
            "current_scene_draft": scene_draft,
            "status": "writing"
        }

    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        episode = await session.get(Episode, state["episode_id"])
        
        current_scene = state["scenes"][state["current_scene_index"]]
        
        llm = LLMFactory.get_model_for_agent(project, "writer", temperature=0.7)
        writer = WriterAgent(llm)
        
        previous_context = "이전 씬 진행 사항 없음"
        if state["draft"]:
            previous_context = state["draft"]
            
        on_reasoning = configurable.get("on_reasoning")
        scene_draft = await writer.run(
            project_synopsis=project.synopsis or "",
            episode_number=episode.episode_number,
            episode_title=episode.title,
            lore_context=state["lore_context"],
            previous_scenes_context=previous_context,
            scene_index=state["current_scene_index"],
            scene_title=current_scene["title"],
            scene_plot=current_scene["plot"],
            tension_level=current_scene["tension"],
            pace_level=current_scene["pace"],
            on_chunk=on_chunk,
            on_reasoning=on_reasoning
        )
        
        return {
            "current_scene_draft": scene_draft,
            "status": "writing"
        }


async def _finalize_judge_result(state: AgentState, result: JudgeResult, on_status) -> dict:
    """
    Judge 통과/실패 공통 후처리.
    - 통과: current_scene_draft 를 draft 에 병합
    - 실패 + loop_count >= 3: 불완전 씬이라도 best-effort 병합 후 사용자 검토로 이관 (Issue 4)
    """
    if result.is_passed:
        separator = "\n\n" if state["draft"] else ""
        new_draft = state["draft"] + separator + (state.get("current_scene_draft") or "")
        is_last = state["current_scene_index"] + 1 >= len(state["scenes"])
        if on_status:
            await on_status("judging_passed", f"씬 {state['current_scene_index']} 검수를 통과했습니다.")
        return {
            "draft": new_draft,
            "current_scene_draft": "",
            "critique": "",
            "status": "waiting_user" if is_last else "judging_passed",
        }

    if on_status:
        await on_status(
            "judging_failed",
            f"씬 {state['current_scene_index']} 검수 실패: {result.critique}",
            {"critique": result.critique},
        )

    # 자기 교정 루프 소진: 미병합 씬을 draft 에 포함시켜 승인 시 유실 방지
    if state.get("loop_count", 0) >= 3:
        scene_draft = state.get("current_scene_draft") or ""
        updates: dict = {
            "critique": result.critique,
            "status": "judging_failed",
        }
        if scene_draft:
            separator = "\n\n" if state["draft"] else ""
            updates["draft"] = state["draft"] + separator + scene_draft
            updates["current_scene_draft"] = ""
            if on_status:
                await on_status(
                    "judging_failed",
                    f"교정 루프 한도 도달. 부분 본문을 포함하여 사용자 검토로 이관합니다.",
                    {"critique": result.critique, "partial": True},
                )
        return updates

    return {
        "critique": result.critique,
        "status": "judging_failed",
    }


async def judge_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Judge 에이전트를 호출하여 작성된 씬 초안과 설정집 간의 모순 유무를 검수합니다.
    통과 시, 해당 씬 본문을 에피소드 전체 본문(draft)에 즉시 병합합니다.
    Editor 수정본은 Writer 를 거치지 않고 이 노드로 재진입합니다 (옵션 A1).
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status("judging", f"씬 {state['current_scene_index']}의 개연성 및 세계관 설정 모순을 검수하는 중입니다...")

    import os
    if os.getenv("TESTING") == "True":
        from unittest.mock import MagicMock
        judge = JudgeAgent(MagicMock())
        result = await judge.run(
            lore_context=state["lore_context"],
            draft=state["current_scene_draft"]
        )
        return await _finalize_judge_result(state, result, on_status)

    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        
        llm = LLMFactory.get_model_for_agent(project, "judge", temperature=0.2)
        judge = JudgeAgent(llm)
        result = await judge.run(
            lore_context=state["lore_context"],
            draft=state["current_scene_draft"]
        )
        
        return await _finalize_judge_result(state, result, on_status)


def format_evaluation_report(report: Optional[dict]) -> str:
    if not report:
        return "N/A"
    
    formatted = f"종합 평점: {report.get('score', 0)}점\n"
    formatted += f"가독성 점수: {report.get('readability', 0)}/10\n"
    formatted += f"긴장감 점수: {report.get('tension', 0)}/10\n"
    
    strengths = report.get('strengths', [])
    if strengths:
        formatted += "\n[강점 요소]\n"
        for s in strengths:
            formatted += f"- {s}\n"
            
    weaknesses = report.get('weaknesses', [])
    if weaknesses:
        formatted += "\n[보완점 및 지적 사항]\n"
        for w in weaknesses:
            formatted += f"- {w}\n"
            
    suggestions = report.get('suggestions', [])
    if suggestions:
        formatted += "\n[수정 및 조율 가이드라인]\n"
        for sug in suggestions:
            formatted += f"- {sug}\n"
            
    summary = report.get('summary', "")
    if summary:
        formatted += f"\n[종합 의견]\n{summary}\n"
        
    return formatted.strip()


async def editor_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Editor 에이전트를 호출하여 AI Judge의 피드백이나 사용자 피드백을 기반으로 초안 본문을 수정합니다.

    - 씬 단위 교정 (current_scene_draft 존재): 수정문을 current_scene_draft 에 저장 → judge 재검수
    - 회차 전체 HITL 교정 (draft 만 존재): draft 를 갱신 → user_review 재검토 (Writer 경유 금지, Issue 2)
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    on_chunk = configurable.get("on_chunk")
    is_full_episode_edit = bool(not state.get("current_scene_draft") and state.get("draft"))

    if on_status:
        if is_full_episode_edit:
            await on_status("writing", "사용자 피드백을 반영하여 회차 본문을 교정하는 중입니다...")
        else:
            await on_status("writing", f"피드백을 반영하여 씬 {state['current_scene_index']} 본문을 교정하는 중입니다...")

    async def _run_editor(llm) -> str:
        editor = EditorAgent(llm)
        evaluation_report_str = format_evaluation_report(state.get("evaluation_report"))
        return await editor.run(
            lore_context=state["lore_context"],
            draft=state["current_scene_draft"] if state.get("current_scene_draft") else state["draft"],
            critique=state.get("critique") or "설정 개연성 및 흐름 보완 필요",
            user_feedback=state.get("user_feedback"),
            evaluation_report=evaluation_report_str,
            on_chunk=on_chunk,
        )

    import os
    if os.getenv("TESTING") == "True":
        from unittest.mock import MagicMock
        edited_draft = await _run_editor(MagicMock())
    else:
        async with AsyncSession(async_engine) as session:
            project = await session.get(Project, state["project_id"])
            llm = LLMFactory.get_model_for_agent(project, "editor", temperature=0.7)
            edited_draft = await _run_editor(llm)

    if is_full_episode_edit:
        return {
            "draft": edited_draft,
            "current_scene_draft": "",
            "loop_count": state["loop_count"] + 1,
            "critique": "",
            "user_feedback": None,
            "status": "waiting_user",
        }

    return {
        "current_scene_draft": edited_draft,
        "loop_count": state["loop_count"] + 1,
        "critique": "",
        "user_feedback": None,
        "status": "writing",
    }


async def next_scene_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    다음 씬으로 인덱스를 전환하고 AI 루프 카운터를 초기화합니다.
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status("plotting", f"씬 {state['current_scene_index'] + 1} 단계로 전이합니다...")

    return {
        "current_scene_index": state["current_scene_index"] + 1,
        "loop_count": 0,
        "critique": "",
        "status": "plotting"
    }


async def reviewer_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    모든 씬 집필이 완료된 후, draft 전체 본문을 기반으로 ReviewerAgent를 구동하여 평가 점수 및 보고서를 생성합니다.
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status(
            "reviewing",
            "🤖 집필 완료! AI 에디터가 본문 종합 검수 보고서를 작성하는 중입니다. 잠시만 기다려 주세요 (예상 소요 시간 20초)..."
        )

    import os
    if os.getenv("TESTING") == "True":
        report_dict = {
            "score": 85,
            "readability": 8,
            "tension": 9,
            "strengths": ["테스트 강점 1", "테스트 강점 2"],
            "weaknesses": ["테스트 보완점 1 (인용: '테스트 문구')"],
            "suggestions": ["테스트 개선제안 1"],
            "summary": "테스트 총평입니다."
        }
        return {"evaluation_report": report_dict, "status": "waiting_user"}

    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        llm = LLMFactory.get_model_for_agent(project, "reviewer", temperature=0.5)
        reviewer = ReviewerAgent(llm)
        
        try:
            report = await reviewer.run(
                project_synopsis=project.synopsis or "",
                lore_context=state.get("lore_context", ""),
                draft=state.get("draft", "")
            )
            report_dict = report.model_dump()
        except Exception as e:
            import logging
            logging.getLogger("workflow").error(f"ReviewerAgent run failed: {e}")
            report_dict = {
                "score": 0,
                "readability": 0,
                "tension": 0,
                "strengths": ["리뷰 에이전트 오류 발생"],
                "weaknesses": [],
                "suggestions": [],
                "summary": "평가 시스템 장애로 보고서를 생성하지 못했습니다."
            }
            
        return {"evaluation_report": report_dict, "status": "waiting_user"}


async def user_review_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    사용자의 최종 피드백(승인/반려)을 검토하기 위해 그래프 진행을 멈추는 체크포인트 노드입니다.
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status("waiting_user", "최종 승인 및 사용자 피드백 입력을 대기하고 있습니다.", {"draft": state["draft"]})

    return {
        "status": "waiting_user"
    }


async def save_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    사용자가 최종 승인한 에피소드 본문 텍스트를 데이터베이스(Content 테이블)에 영구 적재합니다.
    """
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status("done", "승인된 본문을 데이터베이스에 최종 저장하는 중입니다...")

    async with AsyncSession(async_engine) as session:
        # 1. 기존 이 에피소드의 최종 승인본 비활성화 (is_approved 일괄 해제)
        reset_stmt = (
            select(Content)
            .where(Content.episode_id == state["episode_id"])
            .where(Content.is_approved == True)
        )
        approved_contents = (await session.execute(reset_stmt)).scalars().all()
        for c in approved_contents:
            c.is_approved = False
            session.add(c)
            
        # 2. 직전 parent_id 구하기
        parent_stmt = (
            select(Content)
            .where(Content.episode_id == state["episode_id"])
            .order_by(Content.created_at.desc())
            .limit(1)
        )
        parent_res = (await session.execute(parent_stmt)).scalar_one_or_none()
        parent_id = parent_res.id if parent_res else None
        
        # 3. 신규 버전 태그 결정
        version_tag = "v1.0"
        if parent_res:
            try:
                v_num = float(parent_res.version_tag.replace("v", ""))
                version_tag = f"v{round(v_num + 0.1, 1)}"
            except ValueError:
                version_tag = "v1.1"
                
        # 4. 저장
        db_content = Content(
            episode_id=state["episode_id"],
            parent_id=parent_id,
            content_text=state["draft"],
            author_type="ai",
            version_tag=version_tag,
            is_approved=True
        )
        session.add(db_content)
        await session.commit()
        
        if on_status:
            await on_status("done", "회차 본문이 성공적으로 최종 저장되었습니다.", {"version": version_tag})

        return {
            "status": "done"
        }


# ==========================================
# 3. 분기 라우팅 규칙 정의 (Routers)
# ==========================================

def route_after_judge(state: AgentState) -> str:
    """
    AI Judge 검수 이후의 상태 전환 라우팅 함수
    """
    if state["status"] == "judging_failed":
        if state["loop_count"] >= 3:
            # AI 자체 검수 루프 3회 초과 시, 무한 루프 과금을 차단하고 사용자 검토 단계로 이관하여 해결 유도
            is_last = state["current_scene_index"] + 1 >= len(state["scenes"])
            return "reviewer" if is_last else "user_review"
        else:
            return "editor"
    else:
        # 검수 성공 시
        # 아직 남은 씬이 있다면 다음 씬 노드로 전환, 완료되었으면 최종 사용자 검토 노드로 전환
        if state["current_scene_index"] + 1 < len(state["scenes"]):
            return "next_scene"
        else:
            return "reviewer"


def route_after_editor(state: AgentState) -> str:
    """
    Editor 이후 라우팅 (옵션 A1).
    - 씬 단위 교정: judge 재검수 (Writer 재생성 금지 — Issue 1)
    - 회차 전체 HITL 교정: user_review 재검토 (Writer append 오염 방지 — Issue 2)
    """
    if state.get("current_scene_draft"):
        return "judge"
    return "reviewer"


def route_after_user_review(state: AgentState) -> str:
    """
    최종 사용자 검토 시 피드백(반려) 여부에 따른 라우팅 함수
    """
    if state.get("user_feedback"):
        # 반려 및 피드백 글이 있다면 Editor 노드로 이관하여 본문 수정
        return "editor"
    else:
        # 피드백이 없거나 승인 시 데이터베이스 저장 노드로 이관
        return "save"


# ==========================================
# 4. 전체 워크플로우 그래프 빌드 및 컴파일 함수
# ==========================================

def build_workflow_graph() -> StateGraph:
    """
    LangGraph StateGraph 빌드
    """
    workflow = StateGraph(AgentState)
    
    # 노드 등록
    workflow.add_node("plotter", plotter_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("judge", judge_node)
    workflow.add_node("editor", editor_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("next_scene", next_scene_node)
    workflow.add_node("user_review", user_review_node)
    workflow.add_node("save", save_node)
    
    # 시작점 설정
    workflow.set_entry_point("plotter")
    
    # 엣지 연결
    workflow.add_edge("plotter", "rag")
    workflow.add_edge("rag", "writer")
    workflow.add_edge("writer", "judge")
    
    # AI 검수 결과 분기 처리
    workflow.add_conditional_edges(
        "judge",
        route_after_judge,
        {
            "editor": "editor",
            "next_scene": "next_scene",
            "reviewer": "reviewer",
            "user_review": "user_review"
        }
    )
    
    # Editor 이후: 씬 교정 → judge / 회차 HITL 교정 → reviewer (Writer 우회)
    workflow.add_conditional_edges(
        "editor",
        route_after_editor,
        {
            "judge": "judge",
            "reviewer": "reviewer",
        },
    )
    
    # reviewer 노드가 완료되면 user_review 노드로 무조건 진입
    workflow.add_edge("reviewer", "user_review")
    
    # 씬 인덱스 증가 노드에서 다음 RAG 과정으로 순환
    workflow.add_edge("next_scene", "rag")
    
    # 최종 사용자 피드백 결과 분기 처리 (Human-in-the-loop)
    workflow.add_conditional_edges(
        "user_review",
        route_after_user_review,
        {
            "editor": "editor",
            "save": "save"
        }
    )
    
    # 저장 후 최종 종료
    workflow.add_edge("save", END)
    
    return workflow


async def get_compiled_workflow(conn_pool: Optional[AsyncConnectionPool] = None):
    """
    체크포인터를 장착하여 컴파일된 워크플로우를 리턴합니다.
    - 데이터베이스 커넥션 풀이 제공되면 AsyncPostgresSaver를 체크포인터로 사용합니다.
    - 제공되지 않으면 메모리 세이버(MemorySaver)를 기본 사용합니다 (테스트 검증 용도).
    """
    workflow = build_workflow_graph()
    
    import os
    if os.getenv("TESTING") == "True":
        checkpointer = MemorySaver()
    elif conn_pool is not None:
        checkpointer = AsyncPostgresSaver(conn_pool)
    else:
        checkpointer = MemorySaver()
        
    # 사용자 최종 검토(user_review) 직전에 멈추도록(interrupt_before) 컴파일 구성
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["user_review"]
    )
