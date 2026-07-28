"""집필 중단(cancel_writing) — soft/hard cancel 및 백그라운드 Task 분리 검증."""
import os

os.environ["TESTING"] = "True"

import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.core.security import create_access_token
from app.routers.websocket import manager
from app.services.agents import EpisodePlan, ScenePlan, JudgeResult


def test_connection_manager_soft_and_hard_cancel():
    thread_id = f"thread_cancel_unit_{int(time.time() * 1000)}"
    assert manager.is_cancelled(thread_id) is False

    manager.request_cancel(thread_id)
    assert manager.is_cancelled(thread_id) is True

    async def _sleeper():
        await asyncio.sleep(30)

    task = asyncio.get_event_loop().create_task(_sleeper()) if False else None

    # 동기 테스트: Task 등록 후 hard cancel
    loop = asyncio.new_event_loop()
    try:
        async def _run():
            t = asyncio.create_task(asyncio.sleep(30))
            manager.set_running_task(thread_id, t)
            assert manager.is_busy(thread_id) is True
            assert manager.hard_cancel_task(thread_id) is True
            with pytest.raises(asyncio.CancelledError):
                await t
            manager.clear_cancel(thread_id)
            assert manager.is_cancelled(thread_id) is False

        loop.run_until_complete(_run())
    finally:
        loop.close()
        manager.running_tasks.pop(thread_id, None)
        manager.cancel_flags.pop(thread_id, None)


def test_websocket_cancel_while_writing():
    """집필 중 cancel_writing 이 receive 가능하고 cancelled 이벤트를 받는다."""
    timestamp = int(time.time())
    username = f"ws_cancel_{timestamp}"
    project_id = 91001
    episode_id = 91002
    token = create_access_token(data={"sub": username})

    mock_plot = EpisodePlan(scenes=[
        ScenePlan(index=0, title="씬1", plot="취소 테스트 플롯", tension=5, pace=5)
    ])
    mock_judge = JudgeResult(is_passed=True, critique="")

    hang_event = asyncio.Event()

    async def slow_writer_run(self, *args, **kwargs):
        # 취소 요청을 받을 시간을 준다
        for _ in range(50):
            if hang_event.is_set():
                break
            await asyncio.sleep(0.05)
        on_chunk = kwargs.get("on_chunk")
        if on_chunk:
            await on_chunk("부분 초안")
        return "부분 초안"

    with patch("app.services.workflow.PlotterAgent.run", return_value=mock_plot), \
         patch("app.services.workflow.WriterAgent.run", slow_writer_run), \
         patch("app.services.workflow.JudgeAgent.run", return_value=mock_judge), \
         patch("app.services.workflow.retrieve_relevant_lores", new_callable=AsyncMock, return_value="lore"), \
         patch("app.services.workflow.LLMFactory.get_model", return_value=MagicMock()), \
         patch("app.services.workflow.LLMFactory.get_model_for_agent", return_value=MagicMock()):

        with TestClient(app) as client:
            ws_url = f"/ws/projects/{project_id}/episodes/{episode_id}/write"
            with client.websocket_connect(ws_url) as websocket:
                websocket.send_json({"action": "auth", "token": token})
                auth = websocket.receive_json()
                assert auth.get("status") == "authenticated"

                websocket.send_json({"action": "start_writing"})

                saw_writing = False
                saw_cancelling = False
                saw_cancelled = False
                start = time.time()
                while time.time() - start < 15:
                    data = websocket.receive_json()
                    status = data.get("status")
                    event = data.get("event")
                    if status in ("plotting", "writing") or event == "status_changed":
                        if status in ("plotting", "writing", "thinking"):
                            saw_writing = True
                    if status == "cancelling":
                        saw_cancelling = True
                    if status == "cancelled":
                        saw_cancelled = True
                        break
                    # 집필이 시작되면 취소
                    if saw_writing and not saw_cancelling:
                        websocket.send_json({"action": "cancel_writing"})

                hang_event.set()
                assert saw_writing, "집필 시작 이벤트를 받지 못함"
                assert saw_cancelling or saw_cancelled, "취소 관련 이벤트를 받지 못함"
                # soft cancel 후 현재 스텝 종료 또는 cancelled
                if not saw_cancelled:
                    # 한 번 더 강제 취소
                    websocket.send_json({"action": "cancel_writing"})
                    end2 = time.time() + 10
                    while time.time() < end2:
                        data = websocket.receive_json()
                        if data.get("status") == "cancelled":
                            saw_cancelled = True
                            break
                assert saw_cancelled, "cancelled 상태 미수신"
