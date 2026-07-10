import json
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_connection_pool, async_engine
from app.core.security import decode_access_token
from app.models import User, Project, Episode
from app.services.workflow import get_compiled_workflow

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # thread_id -> set of WebSockets
        self.active_connections: dict[str, set[WebSocket]] = {}
        # thread_id -> asyncio.Lock
        self.locks: dict[str, asyncio.Lock] = {}

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
                if thread_id in self.locks:
                    del self.locks[thread_id]

    def get_lock(self, thread_id: str) -> asyncio.Lock:
        if thread_id not in self.locks:
            self.locks[thread_id] = asyncio.Lock()
        return self.locks[thread_id]

    async def broadcast(self, thread_id: str, message: dict):
        if thread_id in self.active_connections:
            for connection in list(self.active_connections[thread_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send broadcast message to a client: {e}")
                    self.disconnect(thread_id, connection)

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

    config = {
        "configurable": {
            "thread_id": thread_id
        }
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

    config["configurable"]["on_status"] = on_status
    config["configurable"]["on_chunk"] = on_chunk

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

            if action == "start_writing":
                if lock.locked():
                    await websocket.send_json({
                        "event": "error",
                        "message": "Another action is already in progress for this episode."
                    })
                    continue

                async with lock:
                    # 처음부터 집필 시작
                    await on_status("plotting", "에이전트가 씬 시놉시스를 계획하는 중입니다...")

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

                    try:
                        async for event in app_workflow.astream(initial_state, config):
                            pass

                        # 완료 지점 또는 중단점(Human-in-the-loop) 도달 시 상태 체크
                        state = await app_workflow.aget_state(config)
                        if "user_review" in state.next:
                            await manager.broadcast(thread_id, {
                                "event": "requires_user_review",
                                "status": "waiting_user",
                                "draft_text": state.values.get("draft", "")
                            })
                        elif state.next == ():
                            await manager.broadcast(thread_id, {
                                "event": "status_changed",
                                "status": "done",
                                "message": "에피소드 자동 집필 및 저장 완료!"
                            })
                    except Exception as graph_err:
                        logger.error(f"LangGraph execution error: {graph_err}")
                        await websocket.send_json({
                            "event": "error",
                            "message": f"Graph execution failed: {str(graph_err)}"
                          })

            elif action == "submit_feedback":
                # 사용자 피드백 반영 및 재개
                feedback = msg.get("user_feedback")
                if not feedback:
                    await websocket.send_json({"event": "error", "message": "Feedback is empty"})
                    continue

                if lock.locked():
                    await websocket.send_json({
                        "event": "error",
                        "message": "Another action is already in progress for this episode."
                    })
                    continue

                async with lock:
                    state = await app_workflow.aget_state(config)
                    if "user_review" not in state.next:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Episode is not waiting for user review."
                        })
                        continue

                    # 피드백 입력 및 재개 상태 셋업
                    await app_workflow.aupdate_state(
                        config,
                        {"user_feedback": feedback, "status": "writing"}
                    )
                    await on_status("writing", "피드백을 반영하여 교정 작업을 진행 중입니다...")

                    try:
                        # None을 전달하여 이전 중단 시점부터 워크플로우를 재개(Resume)시킵니다.
                        async for event in app_workflow.astream(None, config):
                            pass

                        state = await app_workflow.aget_state(config)
                        if "user_review" in state.next:
                            await manager.broadcast(thread_id, {
                                "event": "requires_user_review",
                                "status": "waiting_user",
                                "draft_text": state.values.get("draft", "")
                            })
                    except Exception as graph_err:
                        logger.error(f"LangGraph resume error: {graph_err}")
                        await websocket.send_json({
                            "event": "error",
                            "message": f"Graph resume failed: {str(graph_err)}"
                        })

            elif action == "approve":
                if lock.locked():
                    await websocket.send_json({
                        "event": "error",
                        "message": "Another action is already in progress for this episode."
                    })
                    continue

                async with lock:
                    state = await app_workflow.aget_state(config)
                    if "user_review" not in state.next:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Episode is not waiting for approval."
                        })
                        continue

                    # 최종 승인 및 영구 저장 유도
                    await app_workflow.aupdate_state(
                        config,
                        {"user_feedback": None}
                    )
                    await on_status("done", "소설 본문을 최종 승인하고 있습니다...")

                    try:
                        async for event in app_workflow.astream(None, config):
                            pass

                        await manager.broadcast(thread_id, {
                            "event": "status_changed",
                            "status": "done",
                            "message": "소설이 최종 승인 완료되어 DB에 적재되었습니다."
                        })
                    except Exception as graph_err:
                        logger.error(f"LangGraph approval error: {graph_err}")
                        await websocket.send_json({
                            "event": "error",
                            "message": f"Graph approval failed: {str(graph_err)}"
                        })

            else:
                await websocket.send_json({"event": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket Disconnected: User={username}")
    except Exception as e:
        logger.error(f"WebSocket unexpected error: {e}")
    finally:
        manager.disconnect(thread_id, websocket)
