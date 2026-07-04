import streamlit as st
import websocket
import json

def handle_ws_loop(ws_url, initial_action):
    ws = websocket.WebSocket()
    try:
        ws.connect(ws_url)
    except Exception as e:
        st.error(f"웹소켓 연결 실패: {e}")
        st.session_state.ws_status = "idle"
        return

    ws.send(json.dumps(initial_action))
    
    status_placeholder = st.empty()
    text_placeholder = st.empty()
    text_placeholder.markdown(st.session_state.draft_text)
    
    while True:
        try:
            msg = ws.recv()
            if not msg:
                break
            data = json.loads(msg)
            
            if data["event"] == "status_changed":
                status_placeholder.info(f"상태: {data['message']}")
                if data["status"] == "done":
                    st.session_state.ws_status = "done"
                    break
                    
            elif data["event"] == "text_stream":
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
            st.error(f"통신 중 오류 발생: {e}")
            st.session_state.ws_status = "idle"
            break
            
    ws.close()
    st.rerun()

def render(project_id, episode_id, project_title, episode_title):
    st.title(f"📖 {project_title} - {episode_title}")
    
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("⬅️ 프로젝트로 돌아가기", use_container_width=True):
            st.session_state["current_episode_id"] = None
            st.session_state["current_episode_title"] = None
            for key in ["ws_status", "draft_text", "current_feedback"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
            
    token = st.session_state.get("token")
    ws_url = f"ws://localhost:8080/ws/projects/{project_id}/episodes/{episode_id}/write?token={token}"
    
    if "ws_status" not in st.session_state:
        st.session_state.ws_status = "idle"
    if "draft_text" not in st.session_state:
        st.session_state.draft_text = ""
        
    status = st.session_state.ws_status
    
    if status == "idle":
        st.write("아직 집필이 시작되지 않았습니다. 시작 버튼을 누르면 에이전트가 플롯을 짜고 초안을 작성합니다.")
        if st.button("🚀 자동 집필 시작", type="primary"):
            st.session_state.ws_status = "writing"
            st.session_state.draft_text = ""
            st.rerun()
            
    elif status == "writing":
        handle_ws_loop(ws_url, {"action": "start_writing"})
        
    elif status == "submitting_feedback":
        handle_ws_loop(ws_url, {"action": "submit_feedback", "user_feedback": st.session_state.current_feedback})
        
    elif status == "approving":
        handle_ws_loop(ws_url, {"action": "approve"})
        
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
                st.session_state.draft_text = ""
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
