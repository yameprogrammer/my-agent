import asyncio
import logging
import os
from typing import TypedDict, List, Optional, Any, Awaitable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings
from app.core.database import async_engine
from app.models import Project, Episode, Content
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.services.llm_factory import LLMFactory
from langchain_core.runnables import RunnableConfig
from app.services.agents import (
    PlotterAgent, WriterAgent, JudgeAgent, EditorAgent, EpisodePlan, JudgeResult, ReviewerAgent, ReviewReport
)
from app.services.episode_memory import (
    build_previous_episodes_context,
    update_episode_summary,
)
from app.services.rag import build_plotter_lore_context

logger = logging.getLogger(__name__)

# --- 안전 가드 (config 로 오버라이드 가능) ---
# 보수적 기본: 정상 3~4씬 + Judge 교정 1~2회 정도는 통과, 폭주는 즉시 차단
WORKFLOW_RECURSION_LIMIT = max(8, int(getattr(settings, "WORKFLOW_RECURSION_LIMIT", 30) or 30))
MAX_SCENES_PER_EPISODE = max(1, int(getattr(settings, "MAX_SCENES_PER_EPISODE", 8) or 8))
MAX_HITL_FEEDBACK_ROUNDS = max(1, int(getattr(settings, "MAX_HITL_FEEDBACK_ROUNDS", 5) or 5))
# Judge→Editor 자기 교정 상한 (기존 3 유지 — 씬당 과금 폭주 방지)
MAX_JUDGE_EDITOR_LOOPS = 3


def _llm_timeout_seconds() -> float:
    """에이전트 단건 호출 asyncio 타임아웃(초). 설정 0 이하면 120 폴백."""
    try:
        sec = float(getattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 120.0) or 0)
    except (TypeError, ValueError):
        sec = 120.0
    return sec if sec > 0 else 120.0


async def _await_with_timeout(
    coro: Awaitable[Any],
    *,
    label: str,
    timeout: Optional[float] = None,
) -> Any:
    """LLM/외부 호출 hang 방지. TimeoutError 를 그대로 전파."""
    limit = _llm_timeout_seconds() if timeout is None else timeout
    logger.info("%s: start (timeout=%.0fs)", label, limit)
    try:
        result = await asyncio.wait_for(coro, timeout=limit)
        logger.info("%s: done", label)
        return result
    except asyncio.TimeoutError:
        logger.error("%s: timed out after %.0fs", label, limit)
        raise
    except Exception:
        logger.exception("%s: failed", label)
        raise


async def _status_heartbeat(
    on_status,
    status_name: str,
    base_message: str,
    interval: float = 15.0,
):
    """장시간 대기 중 UI에 경과 시간을 알려 스피너 '먹통' 착각을 줄인다."""
    if not on_status:
        return
    elapsed = 0
    try:
        while True:
            await asyncio.sleep(interval)
            elapsed += int(interval)
            await on_status(
                status_name,
                f"{base_message} ({elapsed}초 경과, 응답 대기 중…)",
            )
    except asyncio.CancelledError:
        return


def workflow_run_config(extra_configurable: Optional[dict] = None) -> dict:
    """astream/ainvoke 에 넣을 공통 config (recursion_limit 포함)."""
    cfg: dict = {
        "recursion_limit": WORKFLOW_RECURSION_LIMIT,
        "configurable": dict(extra_configurable or {}),
    }
    return cfg


def _cap_scenes(scenes_list: List[dict]) -> List[dict]:
    """씬 개수 상한 적용 및 index 재부여."""
    if not scenes_list:
        return []
    capped = scenes_list[:MAX_SCENES_PER_EPISODE]
    for i, s in enumerate(capped):
        if isinstance(s, dict):
            s["index"] = i
    return capped

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
    # H3 Co-writing
    write_mode: str              # from_scratch | polish_draft | continue_draft
    seed_draft: str              # 사용자 초안 (윤문/이어쓰기)


# ==========================================
# 2. 그래프 노드 함수 구현 (Nodes)
# ==========================================

def _synthetic_seed_scenes(write_mode: str) -> List[dict]:
    """윤문/이어쓰기 모드용 단일 씬 보드 (Plotter LLM 생략)."""
    if write_mode == "polish_draft":
        return [{
            "index": 0,
            "title": "초안 윤문",
            "plot": "작가 초안 전체를 윤문·정교화한다. 핵심 사건·인물·대사는 유지하고 문체·개연성·호흡을 다듬는다.",
            "tension": 5,
            "pace": 5,
        }]
    # continue_draft
    return [{
        "index": 0,
        "title": "이어쓰기",
        "plot": "작가 초안 직후에 자연스럽게 이어지는 다음 분량을 집필한다. 초안 원문을 반복하지 않는다.",
        "tension": 6,
        "pace": 6,
    }]


def normalize_locked_scenes(raw_scenes: list) -> List[dict]:
    """
    클라이언트/플로터가 넘긴 씬 목록을 Writer 가 쓰는 표준 dict 로 정규화한다 (H4).
    """
    if not raw_scenes or not isinstance(raw_scenes, list):
        raise ValueError("scenes must be a non-empty list")

    normalized: List[dict] = []
    for i, s in enumerate(raw_scenes):
        if not isinstance(s, dict):
            raise ValueError(f"scenes[{i}] must be an object")
        title = str(s.get("title") or f"씬 {i + 1}").strip() or f"씬 {i + 1}"
        plot = str(s.get("plot") or "").strip()
        if not plot:
            raise ValueError(f"scenes[{i}].plot (줄거리) is required")
        try:
            tension = int(s.get("tension", 5))
        except (TypeError, ValueError):
            tension = 5
        try:
            pace = int(s.get("pace", 5))
        except (TypeError, ValueError):
            pace = 5
        tension = max(1, min(10, tension))
        pace = max(1, min(10, pace))
        normalized.append({
            "index": i,
            "title": title,
            "plot": plot,
            "tension": tension,
            "pace": pace,
        })
    return normalized


async def generate_plotter_scenes(project_id: int, episode_id: int) -> List[dict]:
    """
    Plotter 만 단독 실행해 씬 보드를 반환 (H4 plan_scenes).
    집필 그래프 전체 실행 없이 사람이 편집할 초안 씬을 만든다.
    """
    import os
    if os.getenv("TESTING") == "True":
        from unittest.mock import MagicMock
        plotter = PlotterAgent(MagicMock())
        plan = await plotter.run(
            project_synopsis="",
            episode_number=1,
            episode_title="",
            episode_outline="",
            lore_context="",
        )
        return [
            {
                "index": s.index,
                "title": s.title,
                "plot": s.plot,
                "tension": s.tension,
                "pace": s.pace,
            }
            for s in plan.scenes
        ]

    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, project_id)
        episode = await session.get(Episode, episode_id)
        if not project or not episode:
            raise ValueError("Project or episode not found")

        # IMP-08: 전 설정 dump 대신 개요 기반 필터 + 중요도 캐릭터
        lore_context = await build_plotter_lore_context(
            session,
            project_id,
            episode_title=episode.title,
            episode_outline=episode.outline or "",
        )
        # IMP-07: 이전 회차 요약 주입
        prev_ctx = await build_previous_episodes_context(
            session, project_id, episode.episode_number
        )

        llm = LLMFactory.get_model_for_agent(project, "plotter", temperature=0.7)
        plotter = PlotterAgent(llm)
        plan = await plotter.run(
            project_synopsis=project.synopsis or "",
            episode_number=episode.episode_number,
            episode_title=episode.title,
            episode_outline=episode.outline or "",
            lore_context=lore_context,
            previous_episodes_context=prev_ctx,
        )
        return _cap_scenes([
            {
                "index": s.index,
                "title": s.title,
                "plot": s.plot,
                "tension": s.tension,
                "pace": s.pace,
            }
            for s in plan.scenes
        ])


def _check_cancelled(config: RunnableConfig) -> bool:
    """IDEA-10: soft-cancel 플래그."""
    is_cancelled = (config.get("configurable") or {}).get("is_cancelled")
    try:
        return bool(is_cancelled()) if callable(is_cancelled) else False
    except Exception:
        return False


def _terminal_status(status: Optional[str]) -> bool:
    """그래프를 더 이상 진행하면 안 되는 상태."""
    return status in ("cancelled", "failed", "done")


def route_after_plotter(state: AgentState) -> str:
    """plotter 실패·취소·빈 씬이면 END (rag IndexError / 무의미 루프 방지)."""
    if _terminal_status(state.get("status")):
        return "stop"
    scenes = state.get("scenes") or []
    if not scenes:
        return "stop"
    return "continue"


def route_after_next_scene(state: AgentState) -> str:
    if _terminal_status(state.get("status")):
        return "stop"
    scenes = state.get("scenes") or []
    idx = int(state.get("current_scene_index") or 0)
    if not scenes or idx < 0 or idx >= len(scenes):
        return "stop"
    return "continue"


async def plotter_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Plotter 에이전트를 호출하여 에피소드를 여러 개의 씬으로 나눈 상세 스토리보드를 기획합니다.
    polish_draft / continue_draft 모드는 Plotter 를 스킵하고 단일 합성 씬을 사용합니다 (H3).
    scenes_locked 는 클라이언트가 확정한 scenes 를 그대로 사용합니다 (H4).
    """
    if _check_cancelled(config):
        return {"status": "cancelled"}
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    write_mode = (state.get("write_mode") or "from_scratch").strip() or "from_scratch"
    seed_draft = state.get("seed_draft") or ""

    # H4: 사람 확정 씬 보드 — Plotter 스킵
    if write_mode == "scenes_locked":
        try:
            scenes_list = normalize_locked_scenes(state.get("scenes") or [])
        except ValueError as e:
            if on_status:
                await on_status("failed", f"씬 보드 오류: {e}")
            return {"status": "failed", "scenes": [], "loop_count": 0}
        if on_status:
            await on_status(
                "plotting",
                f"확정된 씬 보드({len(scenes_list)}개)로 집필을 진행합니다 (Plotter 생략).",
                {"scenes": scenes_list, "write_mode": write_mode},
            )
        scenes_list = _cap_scenes(scenes_list)
        if not scenes_list:
            if on_status:
                await on_status("failed", "확정 씬 보드가 비어 있습니다.")
            return {"status": "failed", "scenes": [], "loop_count": 0}
        return {
            "scenes": scenes_list,
            "current_scene_index": 0,
            "draft": "",
            "current_scene_draft": "",
            "status": "plotting",
            "loop_count": 0,
            "write_mode": write_mode,
            "seed_draft": seed_draft,
        }

    # H3: 초안 기반 모드 — Plotter LLM 호출 생략
    if write_mode in ("polish_draft", "continue_draft"):
        scenes_list = _cap_scenes(_synthetic_seed_scenes(write_mode))
        if on_status:
            label = "윤문" if write_mode == "polish_draft" else "이어쓰기"
            await on_status(
                "plotting",
                f"작가 초안 기반 {label} 모드로 진행합니다 (씬 기획 생략).",
                {"scenes": scenes_list, "write_mode": write_mode},
            )
        # polish: draft 는 빈 값 → 윤문 결과가 전체 본문이 됨
        # continue: draft 를 seed 로 시작 → 새 분량이 append
        initial_draft = "" if write_mode == "polish_draft" else seed_draft
        return {
            "scenes": scenes_list,
            "current_scene_index": 0,
            "draft": initial_draft,
            "current_scene_draft": "",
            "status": "plotting",
            "loop_count": 0,
            "write_mode": write_mode,
            "seed_draft": seed_draft,
        }

    if on_status:
        await on_status("plotting", "회차·설정 맥락을 준비하는 중입니다...")

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
        scenes_list = _cap_scenes([
            {
                "index": s.index,
                "title": s.title,
                "plot": s.plot,
                "tension": s.tension,
                "pace": s.pace
            } for s in plan.scenes
        ])
        if not scenes_list:
            if on_status:
                await on_status("failed", "기획된 씬이 없습니다.")
            return {"status": "failed", "scenes": [], "loop_count": 0}
        if on_status:
            await on_status("plotting", "스토리보드 기획이 완료되었습니다.", {"scenes": scenes_list})
        return {
            "scenes": scenes_list,
            "current_scene_index": 0,
            "draft": "",
            "current_scene_draft": "",
            "status": "plotting",
            "loop_count": 0,
            "write_mode": write_mode,
            "seed_draft": seed_draft,
        }

    timeout = _llm_timeout_seconds()
    try:
        async with AsyncSession(async_engine) as session:
            project = await session.get(Project, state["project_id"])
            episode = await session.get(Episode, state["episode_id"])

            if not project or not episode:
                if on_status:
                    await on_status("failed", "프로젝트 또는 회차를 찾을 수 없습니다.")
                return {"status": "failed", "scenes": [], "loop_count": 0}

            provider = (
                getattr(project, "plotter_provider", None)
                or project.llm_provider
                or "?"
            )
            model_name = (
                getattr(project, "plotter_model", None)
                or project.llm_model
                or "?"
            )
            logger.info(
                "plotter_node: project=%s episode=%s provider=%s model=%s",
                state["project_id"],
                state["episode_id"],
                provider,
                model_name,
            )

            # IMP-08: 개요·제목 기반 설정 필터 (전량 dump 금지)
            # 임베딩 API hang 가능 → 별도 타임아웃
            if on_status:
                await on_status(
                    "plotting",
                    "세계관·캐릭터 맥락(RAG)을 모으는 중입니다…",
                )
            try:
                lore_context = await _await_with_timeout(
                    build_plotter_lore_context(
                        session,
                        state["project_id"],
                        episode_title=episode.title,
                        episode_outline=episode.outline or "",
                    ),
                    label="plotter.lore_context",
                    timeout=min(timeout, 60.0),
                )
            except asyncio.TimeoutError:
                if on_status:
                    await on_status(
                        "failed",
                        "설정 검색(RAG/임베딩)이 시간 초과되었습니다. "
                        "OPENAI_API_KEY(임베딩) 또는 네트워크를 확인하세요.",
                    )
                return {"status": "failed", "scenes": [], "loop_count": 0}

            # IMP-07: 직전 회차 연속성
            prev_ctx = await build_previous_episodes_context(
                session, state["project_id"], episode.episode_number
            )

            # API 키 없음은 hang 대신 즉시 실패가 낫다
            has_key = bool(
                getattr(project, "plotter_api_key", None)
                or project.api_key_override
                or getattr(settings, "OPENAI_API_KEY", None)
                or getattr(settings, "GOOGLE_API_KEY", None)
                or getattr(settings, "ANTHROPIC_API_KEY", None)
                or getattr(settings, "NVIDIA_API_KEY", None)
            )
            if (provider or "").lower() not in ("ollama",) and not has_key:
                msg = (
                    f"Plotter용 API 키가 없습니다 (provider={provider}). "
                    "프로젝트 설정에서 API 키를 등록하세요."
                )
                logger.error("plotter_node: %s", msg)
                if on_status:
                    await on_status("failed", msg)
                return {"status": "failed", "scenes": [], "loop_count": 0}

            llm = LLMFactory.get_model_for_agent(project, "plotter", temperature=0.7)
            plotter = PlotterAgent(llm)

            if on_status:
                await on_status(
                    "plotting",
                    f"AI 플로터 호출 중… ({provider}/{model_name}, 최대 {int(timeout)}초)",
                )

            hb = asyncio.create_task(
                _status_heartbeat(
                    on_status,
                    "plotting",
                    f"AI 플로터 응답 대기 중 ({provider}/{model_name})",
                )
            )
            try:
                plan = await _await_with_timeout(
                    plotter.run(
                        project_synopsis=project.synopsis or "",
                        episode_number=episode.episode_number,
                        episode_title=episode.title,
                        episode_outline=episode.outline or "",
                        lore_context=lore_context,
                        previous_episodes_context=prev_ctx,
                    ),
                    label=f"plotter.llm[{provider}/{model_name}]",
                    timeout=timeout,
                )
            finally:
                hb.cancel()
                try:
                    await hb
                except asyncio.CancelledError:
                    pass

            scenes_list = _cap_scenes([
                {
                    "index": s.index,
                    "title": s.title,
                    "plot": s.plot,
                    "tension": s.tension,
                    "pace": s.pace,
                }
                for s in plan.scenes
            ])

            if not scenes_list:
                if on_status:
                    await on_status(
                        "failed",
                        "기획된 씬이 없습니다. 개요를 보강한 뒤 다시 시도하세요.",
                    )
                return {"status": "failed", "scenes": [], "loop_count": 0}

            if len(plan.scenes) > MAX_SCENES_PER_EPISODE and on_status:
                await on_status(
                    "plotting",
                    f"씬이 {len(plan.scenes)}개 기획되어 상한({MAX_SCENES_PER_EPISODE})개로 자릅니다.",
                    {"scenes": scenes_list},
                )
            elif on_status:
                await on_status(
                    "plotting",
                    "스토리보드 기획이 완료되었습니다.",
                    {"scenes": scenes_list},
                )

            return {
                "scenes": scenes_list,
                "current_scene_index": 0,
                "draft": "",
                "current_scene_draft": "",
                "status": "plotting",
                "loop_count": 0,
                "write_mode": write_mode,
                "seed_draft": seed_draft,
            }
    except asyncio.TimeoutError:
        if on_status:
            await on_status(
                "failed",
                f"Plotter LLM 응답이 {int(timeout)}초 안에 오지 않았습니다. "
                "API 키·모델명·제공자 엔드포인트·네트워크를 확인하세요. "
                "(Ollama면 `ollama serve` 기동 여부를 확인하세요.)",
            )
        return {"status": "failed", "scenes": [], "loop_count": 0}
    except Exception as e:
        logger.exception("plotter_node unexpected error: %s", e)
        if on_status:
            await on_status("failed", f"Plotter 실패: {type(e).__name__}: {e}")
        return {"status": "failed", "scenes": [], "loop_count": 0}


from app.services.rag import retrieve_relevant_lores

async def rag_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    현재 집필하려는 씬 정보에 맞추어 캐릭터 설정 및 세계관 설정집에서 관련 맥락을 검색해 주입합니다.
    """
    if _check_cancelled(config):
        return {"status": "cancelled"}
    scenes = state.get("scenes") or []
    idx = int(state.get("current_scene_index") or 0)
    if not scenes or idx < 0 or idx >= len(scenes):
        return {"status": "failed", "scenes": scenes}
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    if on_status:
        await on_status("writing", f"씬 {state['current_scene_index']} 관련 설정을 추출하는 중입니다...")

    async with AsyncSession(async_engine) as session:
        project_id = state["project_id"]
        episode_id = state.get("episode_id")
        current_scene = scenes[idx]
        
        lore_context = await retrieve_relevant_lores(
            session=session,
            project_id=project_id,
            scene_title=current_scene["title"],
            scene_plot=current_scene["plot"],
            episode_id=episode_id
        )
        
        return {
            "lore_context": lore_context,
            "status": "writing"
        }


async def writer_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Writer 에이전트를 호출하여 RAG 설정 및 이전 맥락을 토대로 현재 씬의 본문을 작성합니다.
    polish_draft / continue_draft 시 seed_draft 를 Writer 에 주입합니다 (H3).
    """
    if _check_cancelled(config):
        return {"status": "cancelled"}
    scenes = state.get("scenes") or []
    idx = int(state.get("current_scene_index") or 0)
    if not scenes or idx < 0 or idx >= len(scenes):
        return {"status": "failed", "scenes": scenes}
    configurable = config.get("configurable", {})
    on_status = configurable.get("on_status")
    on_chunk = configurable.get("on_chunk")
    write_mode = (state.get("write_mode") or "from_scratch").strip() or "from_scratch"
    seed_draft = state.get("seed_draft") or ""

    status_msg = f"씬 {state['current_scene_index']} 본문을 집필하는 중입니다..."
    if write_mode == "polish_draft":
        status_msg = "작가 초안을 윤문·정교화하는 중입니다..."
    elif write_mode == "continue_draft":
        status_msg = "작가 초안에 이어 다음 분량을 집필하는 중입니다..."
    if on_status:
        await on_status("writing", status_msg)

    import os
    current_scene = scenes[idx]

    # 맥락: 이어쓰기는 seed 를 이전 본문으로, 윤문은 seed 를 윤문 대상으로
    if write_mode == "continue_draft":
        previous_context = seed_draft or state.get("draft") or "이전 씬 진행 사항 없음"
    elif write_mode == "polish_draft":
        previous_context = seed_draft or "작가 초안 없음"
    else:
        previous_context = state["draft"] or "이전 씬 진행 사항 없음"

    if os.getenv("TESTING") == "True":
        from unittest.mock import MagicMock
        on_reasoning = configurable.get("on_reasoning")
        writer = WriterAgent(MagicMock())
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
            on_reasoning=on_reasoning,
            write_mode=write_mode,
            seed_draft=seed_draft,
            previous_episodes_context="(테스트 — 이전 회차 없음)",
        )
        return {
            "current_scene_draft": scene_draft,
            "status": "writing"
        }

    async with AsyncSession(async_engine) as session:
        project = await session.get(Project, state["project_id"])
        episode = await session.get(Episode, state["episode_id"])

        prev_ctx = await build_previous_episodes_context(
            session, state["project_id"], episode.episode_number
        )
        # IDEA-05: 회차 오버라이드 > 프로젝트 기본
        ep_hook = getattr(episode, "force_ending_hook", None)
        force_hook = (
            bool(ep_hook)
            if ep_hook is not None
            else bool(getattr(project, "force_ending_hook", False))
        )
        scenes = state.get("scenes") or []
        is_last_scene = state["current_scene_index"] + 1 >= len(scenes)
        force_hook = force_hook and is_last_scene
        style_guide = (getattr(project, "style_guide", None) or "").strip() or "(스타일 가이드 없음)"
        
        llm = LLMFactory.get_model_for_agent(project, "writer", temperature=0.7)
        writer = WriterAgent(llm)
            
        on_reasoning = configurable.get("on_reasoning")
        from app.services.usage_log import track_agent_call
        async with track_agent_call(
            project_id=state["project_id"],
            agent_role="writer",
            episode_id=state["episode_id"],
            model_name=getattr(project, "writer_model", None) or project.llm_model,
            provider=getattr(project, "writer_provider", None) or project.llm_provider,
            input_text=f"{current_scene.get('title','')}\n{current_scene.get('plot','')}\n{previous_context[:500]}",
        ) as tracker:
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
                on_reasoning=on_reasoning,
                write_mode=write_mode,
                seed_draft=seed_draft,
                previous_episodes_context=prev_ctx,
                style_guide=style_guide,
                force_ending_hook=force_hook,
            )
            tracker.set_output(scene_draft or "")
        
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
    if state.get("loop_count", 0) >= MAX_JUDGE_EDITOR_LOOPS:
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
    if _check_cancelled(config):
        return {"status": "cancelled"}
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
    if _check_cancelled(config):
        return {"status": "cancelled"}
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
    if _check_cancelled(config):
        return {"status": "cancelled"}
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
    if _check_cancelled(config):
        return {"status": "cancelled"}
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
        episode = await session.get(Episode, state["episode_id"])
        ep_hook = getattr(episode, "force_ending_hook", None) if episode else None
        force_hook = (
            bool(ep_hook)
            if ep_hook is not None
            else bool(getattr(project, "force_ending_hook", False))
        )
        llm = LLMFactory.get_model_for_agent(project, "reviewer", temperature=0.5)
        reviewer = ReviewerAgent(llm)
        
        try:
            report = await reviewer.run(
                project_synopsis=project.synopsis or "",
                lore_context=state.get("lore_context", ""),
                draft=state.get("draft", ""),
                force_ending_hook=force_hook,
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
        write_mode = (state.get("write_mode") or "from_scratch").strip()
        author_type = "hybrid" if write_mode in ("polish_draft", "continue_draft") else "ai"
        if write_mode == "polish_draft":
            version_tag = version_tag if version_tag.startswith("v") else "v1.0"
            # 태그 가독성
            if "polish" not in version_tag and "human" not in version_tag:
                version_tag = f"{version_tag}-polish"
        elif write_mode == "continue_draft" and "continue" not in version_tag:
            version_tag = f"{version_tag}-continue"

        db_content = Content(
            episode_id=state["episode_id"],
            parent_id=parent_id,
            content_text=state["draft"],
            author_type=author_type,
            version_tag=version_tag,
            is_approved=True
        )
        session.add(db_content)
        await session.commit()

        # IMP-07: 승인본 기준 회차 요약 메모리 갱신 (다음 화 연속성)
        try:
            project = await session.get(Project, state["project_id"])
            await update_episode_summary(
                session,
                state["episode_id"],
                state["draft"] or "",
                project=project,
                use_llm=True,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Episode summary update failed: %s", e)
        
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
    if _terminal_status(state.get("status")):
        return "cancelled"
    if state["status"] == "judging_failed":
        if state.get("loop_count", 0) >= MAX_JUDGE_EDITOR_LOOPS:
            # AI 자체 검수 루프 초과 시, 무한 루프 과금을 차단하고 사용자 검토 단계로 이관
            scenes = state.get("scenes") or []
            is_last = state.get("current_scene_index", 0) + 1 >= len(scenes)
            return "reviewer" if is_last else "user_review"
        else:
            return "editor"
    else:
        # 검수 성공 시
        scenes = state.get("scenes") or []
        if state.get("current_scene_index", 0) + 1 < len(scenes):
            return "next_scene"
        else:
            return "reviewer"


def route_after_editor(state: AgentState) -> str:
    """
    Editor 이후 라우팅 (옵션 A1).
    - 씬 단위 교정: judge 재검수 (Writer 재생성 금지 — Issue 1)
    - 회차 전체 HITL 교정: user_review 재검토 (Writer append 오염 방지 — Issue 2)
    """
    if _terminal_status(state.get("status")):
        return "cancelled"
    if state.get("current_scene_draft"):
        return "judge"
    return "reviewer"


def route_after_user_review(state: AgentState) -> str:
    """
    최종 사용자 검토 시 피드백(반려) 여부에 따른 라우팅 함수.
    HITL 반려 횟수 상한 초과 시 강제 저장으로 과금 폭주 차단.
    """
    if state.get("user_feedback"):
        if state.get("loop_count", 0) >= MAX_HITL_FEEDBACK_ROUNDS:
            return "save"
        return "editor"
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
    
    # plotter 실패·빈 씬·취소 → 즉시 END (rag/writer 폭주 방지)
    workflow.add_conditional_edges(
        "plotter",
        route_after_plotter,
        {
            "continue": "rag",
            "stop": END,
        },
    )
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
            "user_review": "user_review",
            "cancelled": END,
        }
    )
    
    # Editor 이후: 씬 교정 → judge / 회차 HITL 교정 → reviewer (Writer 우회)
    workflow.add_conditional_edges(
        "editor",
        route_after_editor,
        {
            "judge": "judge",
            "reviewer": "reviewer",
            "cancelled": END,
        },
    )
    
    # reviewer 노드가 완료되면 user_review 노드로 무조건 진입
    # (cancelled 시 reviewer 가 status 만 바꾸고 끝 — user_review interrupt 전에 상태 확인은 라우터에서)
    workflow.add_conditional_edges(
        "reviewer",
        lambda s: "stop" if _terminal_status(s.get("status")) else "continue",
        {
            "continue": "user_review",
            "stop": END,
        },
    )
    
    # 씬 인덱스 증가 후 범위 벗어나면 END
    workflow.add_conditional_edges(
        "next_scene",
        route_after_next_scene,
        {
            "continue": "rag",
            "stop": END,
        },
    )
    
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
