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
from app.services.agents import (
    PlotterAgent, WriterAgent, JudgeAgent, EditorAgent, EpisodePlan, JudgeResult
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


# ==========================================
# 2. 그래프 노드 함수 구현 (Nodes)
# ==========================================

async def plotter_node(state: AgentState) -> dict:
    """
    Plotter 에이전트를 호출하여 에피소드를 여러 개의 씬으로 나눈 상세 스토리보드를 기획합니다.
    """
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

        llm = LLMFactory.get_model(
            provider=project.llm_provider,
            model_name=project.llm_model,
            api_key_override=project.api_key_override,
            temperature=0.7
        )
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

        return {
            "scenes": scenes_list,
            "current_scene_index": 0,
            "draft": "",
            "current_scene_draft": "",
            "status": "plotting",
            "loop_count": 0
        }


from app.services.rag import retrieve_relevant_lores

async def rag_node(state: AgentState) -> dict:
    """
    현재 집필하려는 씬 정보에 맞추어 캐릭터 설정 및 세계관 설정집에서 관련 맥락을 검색해 주입합니다.
    (pgvector 하이브리드 RAG 엔진 적용 완료)
    """
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


async def writer_node(state: AgentState) -> dict:
    """
    Writer 에이전트를 호출하여 RAG 설정 및 이전 맥락을 토대로 현재 씬의 본문을 작성합니다.
    """
    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        episode = await session.get(Episode, state["episode_id"])
        
        current_scene = state["scenes"][state["current_scene_index"]]
        
        llm = LLMFactory.get_model(
            provider=project.llm_provider,
            model_name=project.llm_model,
            api_key_override=project.api_key_override,
            temperature=0.7
        )
        writer = WriterAgent(llm)
        
        previous_context = "이전 씬 진행 사항 없음"
        if state["draft"]:
            previous_context = state["draft"]
            
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
            pace_level=current_scene["pace"]
        )
        
        return {
            "current_scene_draft": scene_draft,
            "status": "writing"
        }


async def judge_node(state: AgentState) -> dict:
    """
    Judge 에이전트를 호출하여 작성된 씬 초안과 설정집 간의 모순 유무를 검수합니다.
    통과 시, 해당 씬 본문을 에피소드 전체 본문(draft)에 즉시 병합합니다.
    """
    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        
        llm = LLMFactory.get_model(
            provider=project.llm_provider,
            model_name=project.llm_model,
            api_key_override=project.api_key_override,
            temperature=0.2  # 검수는 보수적으로 처리하기 위해 낮은 온도로 설정
        )
        judge = JudgeAgent(llm)
        result = await judge.run(
            lore_context=state["lore_context"],
            draft=state["current_scene_draft"]
        )
        
        if result.is_passed:
            # 통과 시 씬 본문을 에피소드 본문에 바로 병합
            separator = "\n\n" if state["draft"] else ""
            new_draft = state["draft"] + separator + state["current_scene_draft"]
            is_last = state["current_scene_index"] + 1 >= len(state["scenes"])
            
            return {
                "draft": new_draft,
                "current_scene_draft": "",
                "critique": "",
                "status": "waiting_user" if is_last else "judging_passed"
            }
        else:
            return {
                "critique": result.critique,
                "status": "judging_failed"
            }


async def editor_node(state: AgentState) -> dict:
    """
    Editor 에이전트를 호출하여 AI Judge의 피드백이나 사용자 피드백을 기반으로 초안 본문을 수정합니다.
    """
    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        
        llm = LLMFactory.get_model(
            provider=project.llm_provider,
            model_name=project.llm_model,
            api_key_override=project.api_key_override,
            temperature=0.7
        )
        editor = EditorAgent(llm)
        
        critique = state["critique"]
        user_feedback = state.get("user_feedback")
        
        edited_draft = await editor.run(
            lore_context=state["lore_context"],
            draft=state["current_scene_draft"] if state["current_scene_draft"] else state["draft"],
            critique=critique or "설정 개연성 및 흐름 보완 필요",
            user_feedback=user_feedback
        )
        
        # 만약 전체 에피소드 수정 과정(current_scene_draft가 비어 있고 draft만 존재)인 경우
        if not state["current_scene_draft"] and state["draft"]:
            return {
                "draft": edited_draft,
                "loop_count": state["loop_count"] + 1,
                "critique": "",
                "user_feedback": None,
                "status": "writing"
            }
        else:
            return {
                "current_scene_draft": edited_draft,
                "loop_count": state["loop_count"] + 1,
                "critique": "",
                "user_feedback": None,
                "status": "writing"
            }


async def next_scene_node(state: AgentState) -> dict:
    """
    다음 씬으로 인덱스를 전환하고 AI 루프 카운터를 초기화합니다.
    """
    return {
        "current_scene_index": state["current_scene_index"] + 1,
        "loop_count": 0,
        "critique": "",
        "status": "plotting"
    }


async def user_review_node(state: AgentState) -> dict:
    """
    사용자의 최종 피드백(승인/반려)을 검토하기 위해 그래프 진행을 멈추는 체크포인트 노드입니다.
    """
    return {
        "status": "waiting_user"
    }


async def save_node(state: AgentState) -> dict:
    """
    사용자가 최종 승인한 에피소드 본문 텍스트를 데이터베이스(Content 테이블)에 영구 적재합니다.
    """
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
            return "user_review"
        else:
            return "editor"
    else:
        # 검수 성공 시
        # 아직 남은 씬이 있다면 다음 씬 노드로 전환, 완료되었으면 최종 사용자 검토 노드로 전환
        if state["current_scene_index"] + 1 < len(state["scenes"]):
            return "next_scene"
        else:
            return "user_review"


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
            "user_review": "user_review"
        }
    )
    
    # 수정 완료 시 다시 집필(Writer) 노드로 전이
    workflow.add_edge("editor", "writer")
    
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
    
    if conn_pool is not None:
        checkpointer = AsyncPostgresSaver(conn_pool)
        # 최초 1회 실행 시 postgressaver 테이블 세팅 강제화
        await checkpointer.setup()
    else:
        checkpointer = MemorySaver()
        
    # 사용자 최종 검토(user_review) 직전에 멈추도록(interrupt_before) 컴파일 구성
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["user_review"]
    )
