import streamlit as st
import api_client

st.set_page_config(page_title="AI Agent Novelist", page_icon="📝", layout="wide")

if "token" not in st.session_state:
    st.session_state["token"] = None

if "user" not in st.session_state:
    st.session_state["user"] = None

def render_login():
    st.title("로그인")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("로그인", use_container_width=True):
            if username and password:
                res = api_client.login(username, password)
                if res.status_code == 200:
                    st.session_state["token"] = res.json().get("access_token")
                    st.success("로그인 성공!")
                    st.rerun()
                elif res.status_code == 403:
                    st.warning("⏳ 계정이 아직 관리자 승인 대기 중입니다. 승인 후 다시 로그인해 주세요.")
                else:
                    st.error("로그인 실패: 유효하지 않은 자격 증명")
            else:
                st.warning("사용자 이름과 비밀번호를 입력하세요.")
                
    with col2:
        if st.button("회원가입", use_container_width=True):
            if username and password:
                res = api_client.register(username, password)
                if res.status_code in [200, 201]:
                    st.success("✅ 회원가입 요청이 접수되었습니다! 관리자 승인 후 로그인이 가능합니다.")
                    st.info("관리자가 텔레그램으로 승인 요청을 검토 중입니다. 승인 후 다시 로그인해 주세요.")
                else:
                    st.error(f"회원가입 실패: {res.text}")
            else:
                st.warning("사용자 이름과 비밀번호를 입력하세요.")

def render_dashboard():
    # Sidebar
    with st.sidebar:
        st.write(f"환영합니다, **{st.session_state.get('user', {}).get('username')}**님")
        if st.button("로그아웃"):
            st.session_state["token"] = None
            st.session_state["user"] = None
            st.rerun()
            
    st.title("내 소설 프로젝트")
    
    with st.expander("새 프로젝트 생성"):
        title = st.text_input("프로젝트 제목")
        description = st.text_area("설명")
        llm_provider = st.selectbox("LLM Provider", ["openai", "google", "anthropic", "ollama"])
        llm_model = st.text_input("LLM Model", value="gpt-4o-mini")
        api_key = st.text_input("API Key (선택, 입력 시 기본값 오버라이드)", type="password")
        
        if st.button("생성"):
            if title:
                res = api_client.create_project(
                    title=title, 
                    synopsis=description, 
                    llm_provider=llm_provider, 
                    llm_model=llm_model, 
                    api_key_override=api_key if api_key else None
                )
                if res.status_code in [200, 201]:
                    st.success("프로젝트가 생성되었습니다.")
                    st.rerun()
                else:
                    st.error(f"생성 실패: {res.text}")
            else:
                st.warning("제목을 입력해주세요.")

    st.subheader("프로젝트 목록")
    res = api_client.get_projects()
    if res.status_code == 200:
        projects = res.json()
        if not projects:
            st.info("생성된 프로젝트가 없습니다.")
        for p in projects:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"### {p['title']}")
                    st.write(p.get('synopsis', ''))
                    st.caption(f"Provider: {p['llm_provider']} | Model: {p['llm_model']}")
                with col2:
                    if st.button("입장", key=f"enter_{p['id']}"):
                        st.session_state["current_project_id"] = p['id']
                        st.session_state["current_project_title"] = p['title']
                        st.rerun()
                    if st.button("삭제", key=f"del_{p['id']}", type="primary"):
                        api_client.delete_project(p['id'])
                        st.rerun()
    else:
        st.error("프로젝트 목록을 불러오지 못했습니다.")

# Main routing logic
if st.session_state["token"] is None:
    render_login()
else:
    # Validate token and fetch user
    if st.session_state["user"] is None:
        res = api_client.get_me()
        if res.status_code == 200:
            st.session_state["user"] = res.json()
        else:
            st.session_state["token"] = None
            st.rerun()
    
    # If an episode is selected, render monitor view
    if "current_episode_id" in st.session_state and st.session_state["current_episode_id"]:
        import monitor_view
        monitor_view.render(
            st.session_state["current_project_id"],
            st.session_state["current_episode_id"],
            st.session_state["current_project_title"],
            st.session_state["current_episode_title"]
        )
    # If a project is selected, render project view
    elif "current_project_id" in st.session_state and st.session_state["current_project_id"]:
        import project_view
        project_view.render(st.session_state["current_project_id"], st.session_state["current_project_title"])
    else:
        render_dashboard()
