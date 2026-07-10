import streamlit as st
import websocket
import json
import time

def handle_ws_loop(ws_url, token, initial_action):
    ws = websocket.WebSocket()
    
    # 1. 자동 재연결 시도 (연결 수립 시 3회 시도)
    connected = False
    for attempt in range(3):
        try:
            ws.connect(ws_url)
            connected = True
            break
        except Exception:
            time.sleep(1)
            
    if not connected:
        st.error("웹소켓 서버 연결에 실패했습니다. 다시 시도해 주세요.")
        st.session_state.ws_status = "disconnected"
        return

    # 2. 첫 메시지로 인증 토큰 전송
    try:
        ws.send(json.dumps({"action": "auth", "token": token}))
    except Exception as e:
        st.error(f"인증 전송 실패: {e}")
        st.session_state.ws_status = "disconnected"
        ws.close()
        return

    # 3. 초기 실행 액션 전송
    if initial_action:
        try:
            ws.send(json.dumps(initial_action))
        except Exception as e:
            st.error(f"액션 전송 실패: {e}")
            st.session_state.ws_status = "disconnected"
            ws.close()
            return
    
    status_placeholder = st.empty()
    text_placeholder = st.empty()
    text_placeholder.markdown(st.session_state.draft_text)
    
    while True:
        try:
            msg = ws.recv()
            if not msg:
                break
            data = json.loads(msg)
            
            if data["event"] == "current_state":
                st.session_state.draft_text = data["draft_text"]
                status_val = data["status"]
                
                # 서버가 유저 피드백 대기중이거나 중단점에 도달한 경우
                if status_val == "waiting_user" or "user_review" in data["next_node"]:
                    st.session_state.ws_status = "waiting_user"
                    break
                elif status_val == "done":
                    st.session_state.ws_status = "done"
                    break
                elif status_val == "idle":
                    st.session_state.ws_status = "idle"
                    break
                else:
                    # 현재 진행형 작업 복구 (writing / plotting 등)
                    st.session_state.ws_status = "writing"
                    status_placeholder.info(f"에이전트 상태 복구됨: {status_val}")
                    text_placeholder.markdown(st.session_state.draft_text)

            elif data["event"] == "status_changed":
                status_placeholder.info(f"상태: {data['message']}")
                if data["status"] == "done":
                    st.session_state.ws_status = "done"
                    break
                elif data["status"] == "waiting_user":
                    st.session_state.ws_status = "waiting_user"
                    break
                    
            elif data["event"] == "text_stream":
                # 피드백 반영 시 화면이 한순간 깜빡여서 완전히 사라지는 것을 방지하기 위해 
                # 새로운 스트림의 첫 청크가 도착하는 시점에만 이전 텍스트를 클리어
                if st.session_state.get("clear_on_next_chunk", False):
                    st.session_state.draft_text = ""
                    st.session_state.clear_on_next_chunk = False
                
                st.session_state.draft_text += data["chunk"]
                text_placeholder.markdown(st.session_state.draft_text)
                
            elif data["event"] == "requires_user_review":
                if "draft_text" in data and data["draft_text"]:
                    st.session_state.draft_text = data["draft_text"]
                st.session_state.ws_status = "waiting_user"
                break
                
            elif data["event"] == "error":
                st.error(data["message"])
                st.session_state.ws_status = "idle"
                break
                
        except Exception as e:
            # 4. 루프 도중 끊어졌을 때의 재연결 로직
            st.warning("서버와의 연결이 중단되었습니다. 재연결을 시도합니다...")
            reconnected = False
            for attempt in range(5):
                time.sleep(2)
                try:
                    ws = websocket.WebSocket()
                    ws.connect(ws_url)
                    ws.send(json.dumps({"action": "auth", "token": token}))
                    reconnected = True
                    break
                except Exception:
                    pass
            if not reconnected:
                st.error(f"재연결에 실패했습니다. (에러: {e})")
                st.session_state.ws_status = "disconnected"
                break
            else:
                st.success("성공적으로 재연결되었습니다!")
                continue
            
    ws.close()
    st.rerun()

def render(project_id, episode_id, project_title, episode_title):
    st.title(f"📖 {project_title} - {episode_title}")
    
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("⬅️ 프로젝트로 돌아가기", use_container_width=True):
            st.session_state["current_episode_id"] = None
            st.session_state["current_episode_title"] = None
            for key in ["ws_status", "draft_text", "current_feedback", "clear_on_next_chunk"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
            
    token = st.session_state.get("token")
    ws_url = f"ws://localhost:8080/ws/projects/{project_id}/episodes/{episode_id}/write"
    
    if "ws_status" not in st.session_state:
        st.session_state.ws_status = "checking_state"
    if "draft_text" not in st.session_state:
        st.session_state.draft_text = ""
        
    status = st.session_state.ws_status
    
    if status == "checking_state":
        # 초기화 시 백엔드에 연결해 상태를 확인하고 화면을 맞춰 렌더링
        handle_ws_loop(ws_url, token, None)

    elif status == "idle":
        st.write("아직 집필이 시작되지 않았습니다. 시작 버튼을 누르면 에이전트가 플롯을 짜고 초안을 작성합니다.")
        if st.button("🚀 자동 집필 시작", type="primary"):
            st.session_state.ws_status = "writing"
            st.session_state.draft_text = ""
            st.rerun()
            
    elif status == "writing":
        handle_ws_loop(ws_url, token, {"action": "start_writing"})
        
    elif status == "submitting_feedback":
        handle_ws_loop(ws_url, token, {"action": "submit_feedback", "user_feedback": st.session_state.current_feedback})
        
    elif status == "approving":
        handle_ws_loop(ws_url, token, {"action": "approve"})
        
    elif status == "waiting_user":
        st.success("🤖 에이전트가 초안 작성을 완료했습니다. 검토 후 피드백을 주거나 승인하세요.")
        
        with st.container(border=True):
            st.markdown("### 현재 초안")
            st.markdown(st.session_state.draft_text)
        
        st.markdown("---")
        st.subheader("인간 피드백 (Human-in-the-loop)")
        feedback = st.text_area("수정 지시사항 (피드백)")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 피드백 반영하여 재작성", use_container_width=True):
                st.session_state.current_feedback = feedback
                st.session_state.ws_status = "submitting_feedback"
                st.session_state.clear_on_next_chunk = True
                st.rerun()
        with c2:
            if st.button("✅ 최종 승인 및 저장", type="primary", use_container_width=True):
                st.session_state.ws_status = "approving"
                st.rerun()
                
    elif status == "done":
        st.success("✅ 에피소드 집필 및 저장이 완료되었습니다!")
        with st.container(border=True):
            st.markdown("### 최종 본문")
            st.markdown(st.session_state.draft_text)

    elif status == "disconnected":
        st.warning("⚠️ 서버와의 연결이 원활하지 않습니다.")
        if st.button("🔄 다시 연결 시도", type="primary"):
            st.session_state.ws_status = "checking_state"
            st.rerun()
