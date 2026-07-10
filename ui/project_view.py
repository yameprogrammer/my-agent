import streamlit as st
import api_client
import importlib
importlib.reload(api_client)

def render(project_id, project_title):
    st.title(f"📚 {project_title}")
    
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("⬅️ 대시보드", use_container_width=True):
            st.session_state["current_project_id"] = None
            st.session_state["current_project_title"] = None
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["세계관 (Lorebook)", "캐릭터 시트", "회차 관리"])
    
    with tab1:
        st.subheader("세계관 설정")
        with st.expander("새 설정 추가"):
            kw = st.text_input("키워드")
            cat = st.selectbox("카테고리", ["lore", "location", "item"])
            desc = st.text_area("설명")
            if st.button("추가", key="add_lore"):
                if kw and desc:
                    res = api_client.create_world_setting(project_id, kw, cat, desc)
                    if res.status_code == 201:
                        st.rerun()
                    else:
                        st.error("설정 추가에 실패했습니다.")
        
        settings = api_client.get_world_settings(project_id).json()
        for s in settings:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.write(f"**[{s['category']}]** {s['keyword']}")
                    st.write(s['description'])
                with c2:
                    if st.button("삭제", key=f"del_ws_{s['id']}"):
                        api_client.delete_world_setting(project_id, s['id'])
                        st.rerun()

    with tab2:
        st.subheader("캐릭터 목록")
        importance_options = ["protagonist", "deuteragonist", "major", "minor"]
        with st.expander("새 캐릭터 추가"):
            c_name = st.text_input("캐릭터 이름")
            c_imp = st.selectbox("중요도", importance_options, index=3)
            c_desc = st.text_area("설명 (외양, 성격, 특징 등)")
            if st.button("추가", key="add_char"):
                if c_name and c_desc:
                    res = api_client.create_character(project_id, c_name, c_desc, c_imp)
                    if res.status_code == 201:
                        st.rerun()
                    else:
                        st.error("캐릭터 추가에 실패했습니다.")
        
        try:
            characters = api_client.get_characters(project_id).json()
        except (ValueError, TypeError, KeyError) as e:
            st.warning(f"캐릭터 목록을 불러오지 못했습니다: {e}")
            characters = []
        except Exception as e:
            # requests 계열 네트워크/HTTP 오류
            st.warning(f"캐릭터 목록 요청 실패: {e}")
            characters = []
            
        for c in characters:
            with st.container(border=True):
                is_editing = st.session_state.get(f"editing_char_{c['id']}", False)
                if is_editing:
                    edit_name = st.text_input("이름", value=c['name'], key=f"edit_name_{c['id']}")
                    try:
                        idx = importance_options.index(c['importance'])
                    except ValueError:
                        idx = 3
                    edit_imp = st.selectbox("중요도", importance_options, index=idx, key=f"edit_imp_{c['id']}")
                    edit_desc = st.text_area("설명", value=c['description'], key=f"edit_desc_{c['id']}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("저장", key=f"save_char_{c['id']}", type="primary", use_container_width=True):
                            api_client.update_character(project_id, c['id'], edit_name, edit_desc, edit_imp)
                            st.session_state[f"editing_char_{c['id']}"] = False
                            st.rerun()
                    with c2:
                        if st.button("취소", key=f"cancel_char_{c['id']}", use_container_width=True):
                            st.session_state[f"editing_char_{c['id']}"] = False
                            st.rerun()
                else:
                    c1, c2, c3 = st.columns([6, 1, 1])
                    with c1:
                        st.write(f"**{c['name']}** (중요도: {c['importance']})")
                        st.write(c['description'])
                    with c2:
                        if st.button("편집", key=f"edit_btn_{c['id']}", use_container_width=True):
                            st.session_state[f"editing_char_{c['id']}"] = True
                            st.rerun()
                    with c3:
                        if st.button("삭제", key=f"del_char_{c['id']}", use_container_width=True):
                            api_client.delete_character(project_id, c['id'])
                            st.rerun()

    with tab3:
        st.subheader("에피소드")
        with st.expander("새 회차 생성"):
            e_num = st.number_input("회차 번호", min_value=1, step=1)
            e_title = st.text_input("회차 제목")
            if st.button("생성", key="add_ep"):
                if e_title:
                    res = api_client.create_episode(project_id, e_num, e_title)
                    if res.status_code == 201:
                        st.rerun()
                    else:
                        st.error("회차 생성에 실패했습니다.")
        
        episodes = api_client.get_episodes(project_id).json()
        for e in episodes:
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    st.write(f"#### 제 {e['episode_number']} 화. {e['title']}")
                with c2:
                    if st.button("집필 모니터 입장", key=f"enter_ep_{e['id']}", type="primary"):
                        st.session_state["current_episode_id"] = e['id']
                        st.session_state["current_episode_title"] = f"제 {e['episode_number']} 화. {e['title']}"
                        st.rerun()
                with c3:
                    if st.button("삭제", key=f"del_ep_{e['id']}"):
                        api_client.delete_episode(project_id, e['id'])
                        st.rerun()
                
                with st.expander("📝 본문 확인하기"):
                    try:
                        contents_res = api_client.get_contents(project_id, e['id'])
                        if contents_res.status_code == 200:
                            contents = contents_res.json()
                            approved = next((c for c in contents if c.get('is_approved')), None)
                            if approved:
                                st.markdown(f"*(최종 승인 버전: {approved['version_tag']})*")
                                st.markdown(approved['text'])
                            elif contents:
                                latest = contents[-1]
                                st.markdown(f"*(미승인 최신 초안: {latest['version_tag']})*")
                                st.markdown(latest['text'])
                            else:
                                st.info("아직 저장된 본문이 없습니다. '집필 모니터 입장'을 눌러 작성을 시작하세요.")
                        else:
                            st.error("본문을 불러오는 데 실패했습니다.")
                    except Exception as err:
                        import traceback
                        st.error(f"본문 로딩 중 오류가 발생했습니다: {err}")
                        st.error(traceback.format_exc())
