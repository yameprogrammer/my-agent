import os
os.environ["TESTING"] = "True"
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.core.security import create_access_token
from app.services.agents import EpisodePlan, ScenePlan, JudgeResult

def test_websocket_workflow_e2e():
    """
    WebSocket 연결, 토큰 검증, 실시간 상태 변경 전송, 집필 스트리밍,
    Human-in-the-loop 검토 중단 및 승인 피드백 재개, 최종 저장까지
    E2E 실시간 통신 흐름을 검증합니다. (DB 독립식 격리 테스트)
    """
    timestamp = int(time.time())
    username = f"ws_user_{timestamp}"
    project_id = 9999
    episode_id = 9999

    # 1. 인증 토큰 생성
    token = create_access_token(data={"sub": username})

    # 2. 에이전트 모킹 데이터 구성
    mock_plot_plan = EpisodePlan(scenes=[
        ScenePlan(index=0, title="씬 1: 웹소켓 설계", plot="루엘이 실시간 스트림 연결을 성공시킨다.", tension=4, pace=5)
    ])
    
    mock_judge_result = JudgeResult(is_passed=True, critique="")

    async def mock_writer_run(self, *args, **kwargs):
        # 스트리밍 흉내내기: 콜백 호출
        on_chunk = kwargs.get("on_chunk")
        if on_chunk:
            await on_chunk("루엘은 ")
            await on_chunk("하늘을 향해 ")
            await on_chunk("지팡이를 높이 치켜들었다.")
        return "루엘은 하늘을 향해 지팡이를 높이 치켜들었다."

    async def mock_retrieve_relevant_lores(*args, **kwargs):
        return "신비로운 번개 마법 설정"

    # 3. 에이전트 및 LLM 팩토리 패칭 적용
    with patch("app.services.workflow.PlotterAgent.run", return_value=mock_plot_plan), \
         patch("app.services.workflow.WriterAgent.run", mock_writer_run), \
         patch("app.services.workflow.JudgeAgent.run", return_value=mock_judge_result), \
         patch("app.services.workflow.retrieve_relevant_lores", mock_retrieve_relevant_lores), \
         patch("app.services.workflow.LLMFactory.get_model", return_value=MagicMock()):

        # 4. FastAPI TestClient 구동
        with TestClient(app) as client:
            
            # 5. WebSocket 연결 수립
            ws_url = f"/ws/projects/{project_id}/episodes/{episode_id}/write?token={token}"
            with client.websocket_connect(ws_url) as websocket:
                
                # 6. 집필 개시 액션 전송
                websocket.send_json({"action": "start_writing"})
                
                # 7. 실시간 수신 이벤트 검증 (루프 타임아웃 10초)
                plotting_received = False
                writing_received = False
                chunks = []
                user_review_received = False
                
                start_time = time.time()
                while time.time() - start_time < 10:
                    data = websocket.receive_json()
                    event = data.get("event")
                    print(f"[TEST WS RECV] {data}")
                    
                    if event == "status_changed":
                        status_val = data.get("status")
                        if status_val == "plotting":
                            plotting_received = True
                        elif status_val == "writing":
                            writing_received = True
                            
                    elif event == "text_stream":
                        chunks.append(data.get("chunk"))
                        
                    elif event == "requires_user_review":
                        user_review_received = True
                        assert "루엘은" in data.get("draft_text")
                        break
                        
                assert plotting_received is True
                assert writing_received is True
                assert len(chunks) > 0
                assert "".join(chunks) == "루엘은 하늘을 향해 지팡이를 높이 치켜들었다."
                assert user_review_received is True
                print("\n[WebSocket Integration Verification] Successfully verified streaming novel text chunks and pause points.")

                # 8. 사용자 최종 승인(approve) 전달
                websocket.send_json({"action": "approve"})
                
                # 최종 본문 완료 저장 수신 확인 (루프 타임아웃 5초)
                done_received = False
                start_time = time.time()
                while time.time() - start_time < 5:
                    data = websocket.receive_json()
                    print(f"[TEST WS RECV APPROVE] {data}")
                    if data.get("event") == "status_changed" and data.get("status") == "done":
                        done_received = True
                        break
                
                assert done_received is True
                print("[WebSocket Approval Verification] Completed approved novel save flow.")


if __name__ == "__main__":
    test_websocket_workflow_e2e()
    print("ALL TESTS PASSED SUCCESSFULLY!")
