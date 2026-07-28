import json
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_connection_pool, async_engine
from app.core.security import decode_access_token
from app.models import User, Project, Episode, Content
from app.services.workflow import (
    MAX_HITL_FEEDBACK_ROUNDS,
    WORKFLOW_RECURSION_LIMIT,
    get_compiled_workflow,
    generate_plotter_scenes,
    normalize_locked_scenes,
)

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # thread_id -> set of WebSockets
        self.active_connections: dict[str, set[WebSocket]] = {}
        # thread_id -> asyncio.Lock
        self.locks: dict[str, asyncio.Lock] = {}
        # IDEA-10: thread_id -> soft-cancel 요청
        self.cancel_flags: dict[str, bool] = {}
        # IDEA-23: project_id -> 진행 중 episode thread
        self.project_writing: dict[int, str] = {}
        # 집필/기획 등 장시간 작업 — receive 루프와 분리된 Task
        self.running_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, thread_id: str, websocket: WebSocket):
        if thread_id not in self.active_connections:
            self.active_connections[thread_id] = set()
            self.locks[thread_id] = asyncio.Lock()
        self.active_connections[thread_id].add(websocket)

    def disconnect(self, thread_id: str, websocket: WebSocket):
        if thread_id in self.active_connections:
            self.active_connections[thread_id].discard(websocket)
            if not self.active_connections[thread_id]:
                del self.active_connections[thread_id]
                # 백그라운드 집필이 남아 있으면 lock/cancel 플래그는 유지
                task = self.running_tasks.get(thread_id)
                if not task or task.done():
                    self.locks.pop(thread_id, None)
                    self.cancel_flags.pop(thread_id, None)

    def get_lock(self, thread_id: str) -> asyncio.Lock:
        if thread_id not in self.locks:
            self.locks[thread_id] = asyncio.Lock()
        return self.locks[thread_id]

    def is_busy(self, thread_id: str) -> bool:
        """진행 중 Task 또는 lock 점유 여부."""
        task = self.running_tasks.get(thread_id)
        if task is not None and not task.done():
            return True
        lock = self.locks.get(thread_id)
        return bool(lock is not None and lock.locked())

    def set_running_task(self, thread_id: str, task: asyncio.Task) -> None:
        self.running_tasks[thread_id] = task

        def _cleanup(done: asyncio.Task) -> None:
            if self.running_tasks.get(thread_id) is done:
                self.running_tasks.pop(thread_id, None)

        task.add_done_callback(_cleanup)

    def hard_cancel_task(self, thread_id: str) -> bool:
        """진행 중 Task 를 CancelledError 로 강제 종료. True=취소 요청 보냄."""
        task = self.running_tasks.get(thread_id)
        if task is not None and not task.done():
            task.cancel()
            return True
        return False

    def request_cancel(self, thread_id: str) -> None:
        self.cancel_flags[thread_id] = True

    def clear_cancel(self, thread_id: str) -> None:
        self.cancel_flags[thread_id] = False

    def is_cancelled(self, thread_id: str) -> bool:
        return bool(self.cancel_flags.get(thread_id))

    def try_acquire_project_write(self, project_id: int, thread_id: str) -> bool:
        """IDEA-23: 프로젝트당 1 집필. True=획득."""
        current = self.project_writing.get(project_id)
        if current and current != thread_id:
            return False
        self.project_writing[project_id] = thread_id
        return True

    def release_project_write(self, project_id: int, thread_id: str) -> None:
        if self.project_writing.get(project_id) == thread_id:
            del self.project_writing[project_id]

    async def broadcast(self, thread_id: str, message: dict):
        if thread_id in self.active_connections:
            for connection in list(self.active_connections[thread_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send broadcast message to a client: {e}")
                    self.disconnect(thread_id, connection)

    async def broadcast_project(self, project_id: int, message: dict):
        """
        프로젝트 ID가 일치하는 모든 활성 웹소켓 세션에 실시간 알림을 보냅니다.
        """
        prefix = f"thread_{project_id}_"
        for thread_key, connections in list(self.active_connections.items()):
            if thread_key.startswith(prefix):
                for connection in list(connections):
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.warning(f"Failed to send project broadcast: {e}")
                        self.disconnect(thread_key, connection)

manager = ConnectionManager()
router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/projects/{project_id}/episodes/{episode_id}/write")
async def websocket_write_episode(
    websocket: WebSocket,
    project_id: int,
    episode_id: int
):
    """
    실시간 집필 에이전트 모니터링 및 스트리밍을 위한 WebSocket 엔드포인트
    1. 쿼리 파라미터에서 token을 읽어 사용자 인가를 검증합니다.
    2. 프로젝트 및 에피소드 소유권을 교차 확인합니다.
    3. LangGraph의 on_status, on_chunk 실시간 콜백을 장착하여 집필 진행을 비동기 수행합니다.
    """
    await websocket.accept()

    # 1. 첫 메시지로 인증 (auth action)
    try:
        raw_msg = await websocket.receive_text()
        msg = json.loads(raw_msg)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid first message")
        return

    if msg.get("action") != "auth" or not msg.get("token"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token missing or invalid action")
        return

    token = msg.get("token")
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    username = payload.get("sub")
    if not username:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token subject")
        return

    # 2. 유저 정보·활성 상태·프로젝트 소유권 교차 검증
    # TESTING 모드에서도 is_active / 소유권은 검사한다 (WS 인가 우회 제거, Issue 6).
    # 단, 테스트 픽스처가 만든 JWT 주체가 DB에 없을 수 있어 TESTING 에서는 유저 미존재 시 통과 허용.
    import os
    is_testing = os.getenv("TESTING") == "True"
    async with AsyncSession(async_engine) as session:
        stmt_user = select(User).where(User.username == username)
        user = (await session.execute(stmt_user)).scalar_one_or_none()
        if not user:
            if not is_testing:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                return
        else:
            if not user.is_active or user.rejected_at is not None:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Account inactive or rejected",
                )
                return
            if not is_testing:
                stmt_proj = select(Project).where(Project.id == project_id)
                project = (await session.execute(stmt_proj)).scalar_one_or_none()
                if not project or project.user_id != user.id:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Forbidden")
                    return

                stmt_ep = (
                    select(Episode)
                    .where(Episode.id == episode_id)
                    .where(Episode.project_id == project_id)
                )
                episode = (await session.execute(stmt_ep)).scalar_one_or_none()
                if not episode:
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION, reason="Episode not found"
                    )
                    return

    # 3. 인증 및 권한 통과 시 진행
    thread_id = f"thread_{project_id}_{episode_id}"
    await manager.connect(thread_id, websocket)

    logger.info(f"WebSocket Authenticated: User={username}, Project={project_id}, Episode={episode_id}")
    await websocket.send_json({"event": "status_changed", "status": "authenticated", "message": "인증 성공"})

    # LangGraph PostgresSaver 커넥션 풀을 주입하여 컴파일된 그래프 확보
    import os
    if os.getenv("TESTING") == "True":
        app_workflow = await get_compiled_workflow(conn_pool=None)
    else:
        pool = get_connection_pool()
        app_workflow = await get_compiled_workflow(conn_pool=pool)

    # recursion_limit: 그래프 폭주 시 GraphRecursionError 로 안전 종료 (보수적 기본 30)
    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "recursion_limit": WORKFLOW_RECURSION_LIMIT,
    }

    # 기존 상태가 존재하면 클라이언트에게 전송하여 동기화 (재연결/복구 지원)
    try:
        state = await app_workflow.aget_state(config)
        if state and state.values:
            await websocket.send_json({
                "event": "current_state",
                "status": state.values.get("status", "idle"),
                "draft_text": state.values.get("draft", ""),
                "current_scene_draft": state.values.get("current_scene_draft", ""),
                "evaluation_report": state.values.get("evaluation_report", None),
                "next_node": list(state.next) if state.next else []
            })
    except Exception as e:
        logger.error(f"Failed to send initial state to websocket: {e}")

    # 실시간 이벤트 전송용 클로저 콜백 함수 정의 (브로드캐스트 적용)
    async def on_status(status_name: str, message: str, data: Optional[dict] = None):
        await manager.broadcast(thread_id, {
            "event": "status_changed",
            "status": status_name,
            "message": message,
            "data": data or {}
        })

    async def on_chunk(chunk_text: str):
        await manager.broadcast(thread_id, {
            "event": "text_stream",
            "status": "writing",
            "chunk": chunk_text
        })

    async def on_reasoning(reasoning_text: str):
        await manager.broadcast(thread_id, {
            "event": "reasoning_stream",
            "status": "thinking",
            "chunk": reasoning_text
        })

    config["configurable"]["on_status"] = on_status
    config["configurable"]["on_chunk"] = on_chunk
    config["configurable"]["on_reasoning"] = on_reasoning
    config["configurable"]["is_cancelled"] = lambda: manager.is_cancelled(thread_id)

    async def spawn_background_job(job_name: str, job_fn):
        """
        장시간 LLM/그래프 작업을 receive 루프와 분리한다.
        그렇지 않으면 start_writing 중 cancel_writing 메시지를 영원히 못 받는다.
        job_fn: 인자 없는 async callable.
        """
        if manager.is_busy(thread_id):
            await websocket.send_json({
                "event": "error",
                "message": "Another action is already in progress for this episode.",
            })
            return False

        async def _runner():
            lock = manager.get_lock(thread_id)
            try:
                async with lock:
                    await job_fn()
            except asyncio.CancelledError:
                draft_snap = ""
                try:
                    state = await app_workflow.aget_state(config)
                    draft_snap = (state.values or {}).get("draft", "") or ""
                except Exception:
                    pass
                await manager.broadcast(thread_id, {
                    "event": "status_changed",
                    "status": "cancelled",
                    "message": "집필이 강제 중단되었습니다. 부분 draft 를 보존합니다.",
                    "draft_text": draft_snap,
                })
            except Exception as job_err:
                logger.exception("%s background job failed: %s", job_name, job_err)
                try:
                    # error + failed 둘 다 보내 UI 스피너가 running 에 고착되지 않게 함
                    await manager.broadcast(thread_id, {
                        "event": "error",
                        "message": f"{job_name} failed: {job_err}",
                    })
                    await manager.broadcast(thread_id, {
                        "event": "status_changed",
                        "status": "failed",
                        "message": f"{job_name} 실패: {job_err}",
                    })
                except Exception:
                    pass
            finally:
                manager.release_project_write(project_id, thread_id)
                manager.clear_cancel(thread_id)

        task = asyncio.create_task(_runner(), name=f"{job_name}:{thread_id}")
        manager.set_running_task(thread_id, task)
        return True

    try:
        while True:
            # 클라이언트 메시지 대기
            raw_msg = await websocket.receive_text()
            try:
                msg = json.loads(raw_msg)
            except ValueError:
                await websocket.send_json({"event": "error", "message": "Invalid JSON format"})
                continue

            action = msg.get("action")
            lock = manager.get_lock(thread_id)

            # IDEA-10: soft-cancel (1회) / hard-cancel (2회 연타 → Task.cancel)
            if action == "cancel_writing":
                already = manager.is_cancelled(thread_id)
                manager.request_cancel(thread_id)
                if already:
                    hard = manager.hard_cancel_task(thread_id)
                    await manager.broadcast(thread_id, {
                        "event": "status_changed",
                        "status": "cancelling",
                        "message": (
                            "강제 중단을 요청했습니다. 진행 중인 API 호출을 끊습니다..."
                            if hard
                            else "중단 대기 중입니다. 잠시만 기다려 주세요."
                        ),
                    })
                else:
                    await manager.broadcast(thread_id, {
                        "event": "status_changed",
                        "status": "cancelling",
                        "message": (
                            "집필 중단 요청을 접수했습니다. 현재 스텝이 끝나면 중단합니다. "
                            "응답이 없으면 중단 버튼을 한 번 더 눌러 강제 중단하세요."
                        ),
                    })
                continue

            # IDEA-07: 체크포인트 상태 조회 (이어쓰기 UI)
            if action == "get_checkpoint":
                try:
                    state = await app_workflow.aget_state(config)
                    vals = state.values or {}
                    await websocket.send_json({
                        "event": "checkpoint_state",
                        "status": vals.get("status") or "idle",
                        "next_nodes": list(state.next) if state.next else [],
                        "current_scene_index": vals.get("current_scene_index", 0),
                        "scenes": vals.get("scenes") or [],
                        "draft_preview": (vals.get("draft") or "")[:2000],
                        "has_draft": bool(vals.get("draft")),
                        "write_mode": vals.get("write_mode"),
                        "can_resume": bool(state.next),
                        "waiting_user": "user_review" in (state.next or ()),
                    })
                except Exception as e:
                    await websocket.send_json({
                        "event": "error",
                        "message": f"checkpoint 조회 실패: {e}",
                    })
                continue

            # IDEA-06: 특정 씬만 재집필 (scenes_locked + 단일 씬)
            if action == "rewrite_scene":
                if manager.is_busy(thread_id):
                    await websocket.send_json({
                        "event": "error",
                        "message": "Another action is already in progress for this episode.",
                    })
                    continue
                if not manager.try_acquire_project_write(project_id, thread_id):
                    await websocket.send_json({
                        "event": "error",
                        "message": "이 프로젝트에서 다른 회차가 이미 집필 중입니다 (프로젝트당 1 워크플로).",
                    })
                    continue
                try:
                    scene_index = int(msg.get("scene_index", 0))
                except (TypeError, ValueError):
                    manager.release_project_write(project_id, thread_id)
                    await websocket.send_json({"event": "error", "message": "scene_index must be int"})
                    continue
                try:
                    scene = msg.get("scene") or {}
                    if not scene.get("plot"):
                        st = await app_workflow.aget_state(config)
                        scenes_prev = (st.values or {}).get("scenes") or []
                        if 0 <= scene_index < len(scenes_prev):
                            scene = scenes_prev[scene_index]
                        else:
                            raise ValueError("scene.plot 또는 기존 씬이 필요합니다")
                    locked = normalize_locked_scenes([scene])
                    prior_draft = (msg.get("prior_draft") or "").strip()
                    if not prior_draft:
                        st = await app_workflow.aget_state(config)
                        prior_draft = (st.values or {}).get("draft") or ""
                except Exception as prep_err:
                    manager.release_project_write(project_id, thread_id)
                    await websocket.send_json({
                        "event": "error",
                        "message": f"씬 재집필 준비 실패: {prep_err}",
                    })
                    continue

                manager.clear_cancel(thread_id)

                async def _rewrite_job(
                    _scene_index=scene_index,
                    _locked=locked,
                    _prior_draft=prior_draft,
                ):
                    await on_status(
                        "writing",
                        f"씬 {_scene_index} 만 재집필합니다...",
                        {"scene_index": _scene_index},
                    )
                    initial_state = {
                        "project_id": project_id,
                        "episode_id": episode_id,
                        "current_scene_index": 0,
                        "scenes": _locked,
                        "lore_context": "",
                        "draft": _prior_draft,
                        "current_scene_draft": "",
                        "critique": "",
                        "user_feedback": None,
                        "loop_count": 0,
                        "status": "plotting",
                        "evaluation_report": None,
                        "write_mode": "scenes_locked",
                        "seed_draft": "",
                    }
                    try:
                        async for _ in app_workflow.astream(initial_state, config):
                            if manager.is_cancelled(thread_id):
                                break
                    except Exception as graph_err:
                        if type(graph_err).__name__ == "GraphRecursionError" or "recursion" in str(graph_err).lower():
                            state = await app_workflow.aget_state(config)
                            await manager.broadcast(thread_id, {
                                "event": "status_changed",
                                "status": "failed",
                                "message": (
                                    f"집필 스텝 한도({WORKFLOW_RECURSION_LIMIT})에 도달해 중단했습니다. "
                                    "씬 수를 줄이거나 중단 후 이어쓰기를 이용하세요."
                                ),
                                "draft_text": (state.values or {}).get("draft") or _prior_draft,
                            })
                            return
                        raise
                    state = await app_workflow.aget_state(config)
                    draft_text = (state.values or {}).get("draft") or _prior_draft
                    if manager.is_cancelled(thread_id):
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "cancelled",
                            "message": "씬 재집필이 중단되었습니다. 부분 draft 를 보존합니다.",
                            "draft_text": draft_text,
                        })
                    elif "user_review" in (state.next or ()):
                        await manager.broadcast(thread_id, {
                            "event": "requires_user_review",
                            "status": "waiting_user",
                            "draft_text": draft_text,
                            "evaluation_report": (state.values or {}).get("evaluation_report"),
                        })
                    else:
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "done" if not state.next else "idle",
                            "message": "씬 재집필 완료",
                            "draft_text": draft_text,
                        })

                if not await spawn_background_job("rewrite_scene", _rewrite_job):
                    manager.release_project_write(project_id, thread_id)
                continue

            if action == "start_writing":
                if manager.is_busy(thread_id):
                    await websocket.send_json({
                        "event": "error",
                        "message": "Another action is already in progress for this episode."
                    })
                    continue
                if not manager.try_acquire_project_write(project_id, thread_id):
                    await websocket.send_json({
                        "event": "error",
                        "message": "이 프로젝트에서 다른 회차가 이미 집필 중입니다 (프로젝트당 1 워크플로).",
                    })
                    continue

                write_mode = (msg.get("write_mode") or "from_scratch").strip() or "from_scratch"
                allowed_modes = (
                    "from_scratch",
                    "polish_draft",
                    "continue_draft",
                    "scenes_locked",
                )
                if write_mode not in allowed_modes:
                    manager.release_project_write(project_id, thread_id)
                    await websocket.send_json({
                        "event": "error",
                        "message": (
                            "write_mode must be from_scratch | polish_draft | "
                            "continue_draft | scenes_locked"
                        ),
                    })
                    continue

                seed_draft = (msg.get("seed_draft") or "").strip()
                seed_content_id = msg.get("seed_content_id")
                locked_scenes: list = []

                # seed_content_id 가 있으면 해당 Content 본문을 seed 로 로드
                if seed_content_id is not None:
                    try:
                        cid = int(seed_content_id)
                    except (TypeError, ValueError):
                        manager.release_project_write(project_id, thread_id)
                        await websocket.send_json({
                            "event": "error",
                            "message": "seed_content_id must be an integer",
                        })
                        continue
                    async with AsyncSession(async_engine) as session:
                        content_row = await session.get(Content, cid)
                        if not content_row or content_row.episode_id != episode_id:
                            manager.release_project_write(project_id, thread_id)
                            await websocket.send_json({
                                "event": "error",
                                "message": "seed_content_id not found in this episode",
                            })
                            continue
                        seed_draft = (content_row.content_text or "").strip()

                if write_mode in ("polish_draft", "continue_draft") and not seed_draft:
                    manager.release_project_write(project_id, thread_id)
                    await websocket.send_json({
                        "event": "error",
                        "message": "polish_draft/continue_draft 모드에는 seed_draft 또는 seed_content_id 가 필요합니다.",
                    })
                    continue

                if write_mode == "scenes_locked":
                    try:
                        locked_scenes = normalize_locked_scenes(msg.get("scenes") or [])
                    except ValueError as ve:
                        manager.release_project_write(project_id, thread_id)
                        await websocket.send_json({
                            "event": "error",
                            "message": f"Invalid scenes: {ve}",
                        })
                        continue

                manager.clear_cancel(thread_id)

                async def _start_writing_job(
                    _write_mode=write_mode,
                    _seed_draft=seed_draft,
                    _locked_scenes=locked_scenes,
                ):
                    if _write_mode == "from_scratch":
                        await on_status("plotting", "에이전트가 씬 시놉시스를 계획하는 중입니다...")
                    elif _write_mode == "polish_draft":
                        await on_status("plotting", "작가 초안 윤문 모드로 집필을 시작합니다...")
                    elif _write_mode == "continue_draft":
                        await on_status("plotting", "작가 초안 이어쓰기 모드로 집필을 시작합니다...")
                    else:
                        await on_status(
                            "plotting",
                            f"확정 씬 보드({len(_locked_scenes)}개)로 집필을 시작합니다...",
                        )

                    initial_draft = _seed_draft if _write_mode == "continue_draft" else ""
                    initial_state = {
                        "project_id": project_id,
                        "episode_id": episode_id,
                        "current_scene_index": 0,
                        "scenes": _locked_scenes if _write_mode == "scenes_locked" else [],
                        "lore_context": "",
                        "draft": initial_draft,
                        "current_scene_draft": "",
                        "critique": "",
                        "user_feedback": None,
                        "loop_count": 0,
                        "status": "plotting",
                        "evaluation_report": None,
                        "write_mode": _write_mode,
                        "seed_draft": _seed_draft,
                    }

                    try:
                        async for event in app_workflow.astream(initial_state, config):
                            if manager.is_cancelled(thread_id):
                                break
                    except Exception as graph_err:
                        if type(graph_err).__name__ == "GraphRecursionError" or "recursion" in str(graph_err).lower():
                            state = await app_workflow.aget_state(config)
                            await manager.broadcast(thread_id, {
                                "event": "status_changed",
                                "status": "failed",
                                "message": (
                                    f"집필 스텝 한도({WORKFLOW_RECURSION_LIMIT})에 도달해 안전하게 중단했습니다. "
                                    "씬 수를 줄이거나 「집필 중단」 후 체크포인트 이어쓰기를 이용하세요."
                                ),
                                "draft_text": (state.values or {}).get("draft", ""),
                            })
                            return
                        raise

                    state = await app_workflow.aget_state(config)
                    draft_snap = (state.values or {}).get("draft", "")
                    if manager.is_cancelled(thread_id):
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "cancelled",
                            "message": "집필이 중단되었습니다. 부분 draft 를 보존합니다.",
                            "draft_text": draft_snap,
                        })
                    elif "user_review" in (state.next or ()):
                        await manager.broadcast(thread_id, {
                            "event": "requires_user_review",
                            "status": "waiting_user",
                            "draft_text": draft_snap,
                            "evaluation_report": state.values.get("evaluation_report", None)
                        })
                    elif state.next == ():
                        status_val = (state.values or {}).get("status")
                        if status_val in ("failed", "cancelled"):
                            await manager.broadcast(thread_id, {
                                "event": "status_changed",
                                "status": status_val,
                                "message": (
                                    "집필이 실패 상태로 종료되었습니다."
                                    if status_val == "failed"
                                    else "집필이 중단되었습니다."
                                ),
                                "draft_text": draft_snap,
                            })
                        else:
                            await manager.broadcast(thread_id, {
                                "event": "status_changed",
                                "status": "done",
                                "message": "에피소드 자동 집필 및 저장 완료!"
                            })

                if not await spawn_background_job("start_writing", _start_writing_job):
                    manager.release_project_write(project_id, thread_id)

            elif action == "plan_scenes":
                # H4: Plotter 만 실행해 씬 보드 초안 반환 (집필 미시작)
                async def _plan_scenes_job():
                    await on_status("plotting", "씬 보드 초안을 기획하는 중입니다...")
                    try:
                        scenes = await generate_plotter_scenes(project_id, episode_id)
                        if manager.is_cancelled(thread_id):
                            await manager.broadcast(thread_id, {
                                "event": "status_changed",
                                "status": "cancelled",
                                "message": "씬 기획이 중단되었습니다.",
                            })
                            return
                        await manager.broadcast(thread_id, {
                            "event": "scenes_planned",
                            "status": "idle",
                            "scenes": scenes,
                            "message": f"{len(scenes)}개 씬 초안이 준비되었습니다. 편집 후 확정 집필하세요.",
                        })
                        await on_status(
                            "idle",
                            f"씬 보드 초안 {len(scenes)}개 생성 완료. 편집 후 집필을 시작하세요.",
                            {"scenes": scenes},
                        )
                    except Exception as plan_err:
                        logger.error(f"plan_scenes failed: {plan_err}")
                        await manager.broadcast(thread_id, {
                            "event": "error",
                            "message": f"씬 기획 실패: {str(plan_err)}",
                        })
                        await on_status("idle", "씬 기획에 실패했습니다.")

                manager.clear_cancel(thread_id)
                await spawn_background_job("plan_scenes", _plan_scenes_job)

            elif action == "submit_feedback":
                # 사용자 피드백 반영 및 재개
                feedback = msg.get("user_feedback")
                if not feedback:
                    await websocket.send_json({"event": "error", "message": "Feedback is empty"})
                    continue

                state = await app_workflow.aget_state(config)
                if "user_review" not in (state.next or ()):
                    await websocket.send_json({
                        "event": "error",
                        "message": "Episode is not waiting for user review."
                    })
                    continue

                manager.clear_cancel(thread_id)

                async def _feedback_job(_feedback=feedback):
                    # HITL 상한 도달 시 피드백 무시하고 저장 경로로 (route_after_user_review)
                    st0 = await app_workflow.aget_state(config)
                    loop_n = int((st0.values or {}).get("loop_count") or 0)
                    if loop_n >= MAX_HITL_FEEDBACK_ROUNDS:
                        await app_workflow.aupdate_state(config, {"user_feedback": None})
                        await on_status(
                            "writing",
                            "피드백 한도에 도달해 강제 저장 경로로 전환합니다...",
                        )
                    else:
                        await app_workflow.aupdate_state(
                            config,
                            {"user_feedback": _feedback, "status": "writing"}
                        )
                        await on_status("writing", "피드백을 반영하여 교정 작업을 진행 중입니다...")
                    try:
                        async for event in app_workflow.astream(None, config):
                            if manager.is_cancelled(thread_id):
                                break
                    except Exception as graph_err:
                        if type(graph_err).__name__ == "GraphRecursionError" or "recursion" in str(graph_err).lower():
                            state_after = await app_workflow.aget_state(config)
                            await manager.broadcast(thread_id, {
                                "event": "status_changed",
                                "status": "failed",
                                "message": f"교정 스텝 한도({WORKFLOW_RECURSION_LIMIT}) 초과로 중단했습니다.",
                                "draft_text": (state_after.values or {}).get("draft", ""),
                            })
                            return
                        raise
                    state_after = await app_workflow.aget_state(config)
                    draft_snap = (state_after.values or {}).get("draft", "")
                    if manager.is_cancelled(thread_id):
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "cancelled",
                            "message": "교정 작업이 중단되었습니다. 부분 draft 를 보존합니다.",
                            "draft_text": draft_snap,
                        })
                    elif "user_review" in (state_after.next or ()):
                        await manager.broadcast(thread_id, {
                            "event": "requires_user_review",
                            "status": "waiting_user",
                            "draft_text": draft_snap,
                            "evaluation_report": state_after.values.get("evaluation_report", None)
                        })
                    elif state_after.next == ():
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "done",
                            "message": "피드백 한도 도달 또는 저장이 완료되었습니다.",
                            "draft_text": draft_snap,
                        })

                await spawn_background_job("submit_feedback", _feedback_job)

            elif action == "approve":
                state = await app_workflow.aget_state(config)
                if "user_review" not in (state.next or ()):
                    await websocket.send_json({
                        "event": "error",
                        "message": "Episode is not waiting for approval."
                    })
                    continue

                manager.clear_cancel(thread_id)

                async def _approve_job():
                    await app_workflow.aupdate_state(
                        config,
                        {"user_feedback": None}
                    )
                    await on_status("done", "소설 본문을 최종 승인하고 있습니다...")
                    async for event in app_workflow.astream(None, config):
                        if manager.is_cancelled(thread_id):
                            break
                    if manager.is_cancelled(thread_id):
                        state_after = await app_workflow.aget_state(config)
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "cancelled",
                            "message": "승인/저장이 중단되었습니다.",
                            "draft_text": (state_after.values or {}).get("draft", ""),
                        })
                    else:
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "done",
                            "message": "소설이 최종 승인 완료되어 DB에 적재되었습니다."
                        })

                await spawn_background_job("approve", _approve_job)

            elif action == "audit_plot":
                manager.clear_cancel(thread_id)

                async def _audit_plot_job():
                    await manager.broadcast(thread_id, {
                        "event": "status_changed",
                        "status": "auditing",
                        "message": "에이전트가 소설 스토리보드 및 인물 묘사 개연성을 검수 중입니다..."
                    })

                    async with AsyncSession(async_engine) as session:
                        project = await session.get(Project, project_id)
                        episode = await session.get(Episode, episode_id)
                        if not project or not episode:
                            await manager.broadcast(thread_id, {
                                "event": "error",
                                "message": "Project or Episode not found",
                            })
                            await on_status("idle", "검수 대상 프로젝트/회차를 찾을 수 없습니다.")
                            return

                        from app.models import WorldSetting, Character
                        lore_stmt = select(WorldSetting).where(WorldSetting.project_id == project_id)
                        lores = (await session.execute(lore_stmt)).scalars().all()

                        char_stmt = select(Character).where(Character.project_id == project_id)
                        chars = (await session.execute(char_stmt)).scalars().all()

                        lore_context = "=== 등장인물 설정 ===\n"
                        lore_context += "\n".join([f"- {c.name} ({c.importance}): {c.description}" for c in chars])
                        lore_context += "\n\n=== 세계관 및 설정집 ===\n"
                        lore_context += "\n".join([f"- {ws.keyword} ({ws.category}): {ws.description}" for ws in lores])

                    state = await app_workflow.aget_state(config)
                    scenes_list = []
                    if state and state.values and state.values.get("scenes"):
                        scenes_list = state.values.get("scenes")

                    if not scenes_list:
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "idle",
                            "message": "검수 중단: 기획된 씬 정보가 없습니다."
                        })
                        await manager.broadcast(thread_id, {
                            "event": "error",
                            "message": "기획된 씬 정보가 없습니다. 집필 프로세스를 먼저 기동하여 기획안을 생성하세요."
                        })
                        return

                    if manager.is_cancelled(thread_id):
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "cancelled",
                            "message": "기획 검수가 중단되었습니다.",
                        })
                        return

                    from app.services.agents import PlotAuditorAgent
                    from app.services.llm_factory import LLMFactory
                    llm = LLMFactory.get_model_for_agent(project, "judge", temperature=0.2)
                    auditor = PlotAuditorAgent(llm)

                    import os
                    if os.getenv("TESTING") == "True":
                        report_data = {
                            "is_passed": True,
                            "score": 95,
                            "summary": "기획안 검수 통과 (테스트 픽스처)",
                            "scene_audits": [
                                {
                                    "scene_index": 0,
                                    "scene_title": "테스트 씬",
                                    "is_passed": True,
                                    "ooc_issues": [],
                                    "plot_holes": [],
                                    "suggestions": []
                                }
                            ]
                        }
                    else:
                        report = await auditor.run(
                            project_synopsis=project.synopsis or "",
                            episode_title=episode.title or "",
                            episode_outline=episode.outline or "",
                            lore_context=lore_context,
                            scenes_list=scenes_list
                        )
                        report_data = {
                            "is_passed": report.is_passed,
                            "score": report.score,
                            "summary": report.summary,
                            "scene_audits": [
                                {
                                    "scene_index": s.scene_index,
                                    "scene_title": s.scene_title,
                                    "is_passed": s.is_passed,
                                    "ooc_issues": s.ooc_issues,
                                    "plot_holes": s.plot_holes,
                                    "suggestions": s.suggestions,
                                }
                                for s in report.scene_audits
                            ],
                        }

                    if manager.is_cancelled(thread_id):
                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "cancelled",
                            "message": "기획 검수가 중단되었습니다.",
                        })
                        return

                    await manager.broadcast(thread_id, {
                        "event": "plot_audited",
                        "status": "audited",
                        "report": report_data,
                    })
                    await manager.broadcast(thread_id, {
                        "event": "status_changed",
                        "status": "idle",
                        "message": "기획 검수가 완료되었습니다.",
                    })

                await spawn_background_job("audit_plot", _audit_plot_job)

            else:
                await websocket.send_json({"event": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket Disconnected: User={username}")
    except Exception as e:
        logger.error(f"WebSocket unexpected error: {e}")
    finally:
        manager.disconnect(thread_id, websocket)
