from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pathsetup import ensure_project_paths

ensure_project_paths()

import streamlit as st
import pandas as pd

from apps.admin.workflow_helpers import (
    build_draft_validation_state,
    build_episode_to_draft_state,
    build_theme_to_arcs_state,
)
from my_agent.database import DEFAULT_SQLITE_PATH
from my_agent.domain import DraftKind, RecordStatus
from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.embeddings import EmbedderFactory

# New project-centric context (Step 2+)
from apps.admin import project_context as pc
from packages.orchestrator.workflows import (
    build_draft_validation_workflow,
    build_episode_to_draft_workflow,
    build_theme_to_arcs_workflow,
)

st.set_page_config(page_title="AI Novel Admin Console", layout="wide")


@st.cache_resource
def get_resources() -> tuple[NovelRepository, MemoryStore, EmbedderFactory]:
    repo = NovelRepository(DEFAULT_SQLITE_PATH)
    memory_store = MemoryStore(DEFAULT_SQLITE_PATH)
    embedder_factory = EmbedderFactory(mode="local")
    return repo, memory_store, embedder_factory


repo, memory_store, embedder_factory = get_resources()

st.sidebar.title("Novel System Admin")

# Show current project context (new in Step 2/3)
current_novel = pc.get_current_novel_id()
if current_novel:
    st.sidebar.success(f"📁 Selected: {current_novel}")
    if st.sidebar.button("🔄 프로젝트 변경 / 목록으로"):
        pc.clear_current_novel_id()
        st.rerun()
else:
    st.sidebar.info("프로젝트를 선택하세요")

menu = st.sidebar.radio("Menu", ["Projects", "Story Build", "Episode Build", "Workflow Execution", "Validation Review", "System Logs"])

# Top level current project banner + guard message (Step 3)
current_at_top = pc.get_current_novel_id()
if current_at_top:
    st.info(f"📁 현재 작업 중인 프로젝트: **{current_at_top}**  |  Projects 메뉴에서 변경하세요.")
elif menu != "Projects":
    st.warning("⚠️ 프로젝트를 먼저 선택해주세요. 'Projects' 메뉴로 이동해서 프로젝트를 선택하거나 새로 만드세요.")

if menu == "Projects":
    st.header("📁 Projects — 집필 프로젝트 관리")
    st.caption("프로젝트 목록 관리 + 선택된 프로젝트 홈 (Step 4). 작업 메뉴는 프로젝트 선택 후 이용하세요.")

    # ========== Create new project form ==========
    with st.expander("➕ 새 집필 프로젝트 만들기", expanded=not bool(repo.list_novels())):
        with st.form("create_project_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_id = st.text_input("Project ID (영문/숫자, 고유)", value="my-novel-001", help="내부 ID로 사용됩니다. 변경 불가")
                new_title = st.text_input("제목", value="새 소설 제목")
            with col2:
                new_genre = st.selectbox("장르", ["fantasy", "romance", "action", "mystery", "other"], index=0)
                new_desc = st.text_input("간단 설명 (선택)", value="")

            submitted = st.form_submit_button("🚀 프로젝트 생성", use_container_width=True)

            if submitted:
                if not new_id or not new_title:
                    st.error("Project ID와 제목은 필수입니다.")
                else:
                    try:
                        created = repo.create_novel(
                            NovelCreate(
                                novel_id=new_id.strip(),
                                title=new_title.strip(),
                                genre=new_genre,
                            )
                        )
                        pc.set_current_novel_id(created.novel_id)
                        st.success(f"✅ 프로젝트 '{created.title}' ({created.novel_id}) 생성 완료!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"생성 실패: {e}")

    st.divider()

    # ========== Projects List ==========
    novels = repo.list_novels()

    if not novels:
        st.warning("등록된 프로젝트가 없습니다. 위 폼으로 첫 프로젝트를 만들어 보세요.")
        st.info("bootstrap으로 demo 프로젝트를 만들 수도 있습니다: `python scripts/bootstrap.py`")
    else:
        st.subheader(f"전체 프로젝트 ({len(novels)}개)")

        for novel in novels:
            summary = repo.get_project_summary(novel.novel_id)

            # Card-like container
            with st.container(border=True):
                col_info, col_stats, col_action = st.columns([3, 2, 1.5])

                with col_info:
                    st.markdown(f"### {novel.title}")
                    st.caption(f"ID: `{novel.novel_id}` · Genre: {novel.genre} · Status: {novel.status}")

                with col_stats:
                    st.markdown(
                        f"**Arcs:** {summary['arc_count']}　"
                        f"**Episodes:** {summary['episode_count']}　"
                        f"**Drafts:** {summary['draft_count']}"
                    )
                    if summary["pending_validation_count"] > 0:
                        st.warning(f"⏳ 승인 대기: {summary['pending_validation_count']}")
                    if summary.get("latest_draft_title"):
                        st.caption(f"최근 원고: {summary['latest_draft_title']}")

                with col_action:
                    is_selected = pc.get_current_novel_id() == novel.novel_id
                    if is_selected:
                        st.success("✅ 선택됨")
                    else:
                        if st.button("이 프로젝트 선택", key=f"select_{novel.novel_id}"):
                            pc.set_current_novel_id(novel.novel_id)
                            st.success(f"'{novel.title}' 선택 완료")
                            st.rerun()

                    # Placeholder for future "Enter Workspace" button
                    st.caption("자세한 작업은 이후 단계에서")

    # ========== Step 4: 프로젝트 홈 (Project Dashboard) ==========
    current = pc.get_current_novel_id()
    if current and novels:
        selected_novel = next((n for n in novels if n.novel_id == current), None)
        if selected_novel:
            summary = repo.get_project_summary(current)
            st.divider()
            st.header(f"📊 {selected_novel.title} 프로젝트 홈")
            st.caption("현재 프로젝트의 진행 상태와 빠른 시작")

            # Stats
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("아크 수", summary["arc_count"])
            c2.metric("에피소드 수", summary["episode_count"])
            c3.metric("드래프트 수", summary["draft_count"])
            c4.metric("검수 대기", summary["pending_validation_count"], delta="처리 필요" if summary["pending_validation_count"] > 0 else None)

            if summary.get("latest_draft_title"):
                st.success(f"최근 원고: {summary['latest_draft_title']}")

            # Quick actions
            st.subheader("⚡ 빠른 액션")
            qa_col1, qa_col2, qa_col3 = st.columns(3)
            with qa_col1:
                if st.button("📝 스토리 빌드 실행", use_container_width=True, key="qa_story"):
                    st.session_state["preferred_workflow"] = "theme_to_arcs"
                    st.info("아래 'Workflow Execution' 메뉴로 이동해서 실행하세요.")
            with qa_col2:
                if st.button("✍️ 다음 에피소드 집필", use_container_width=True, key="qa_episode"):
                    st.session_state["preferred_workflow"] = "episode_to_draft"
                    st.info("Episode Build 메뉴로 이동해서 에피소드를 선택하고 집필하세요.")
            with qa_col3:
                if st.button("✅ 검수 및 승인", use_container_width=True, key="qa_validate"):
                    st.session_state["preferred_workflow"] = "draft_validation"
                    st.info("Validation Review 메뉴에서 검수 결과를 확인/승인하세요.")

elif menu == "Story Build":
    st.header("📖 Story Build — 전체 스토리 기획")
    st.caption("프로젝트의 큰 그림(로그라인, 세계관, 아크 구조)을 확인하고 새로 빌드합니다. (Step 5)")

    novel_id = pc.require_current_novel_id()

    if st.button("🔄 다른 프로젝트 변경", key="change_story"):
        pc.clear_current_novel_id()
        st.rerun()

    st.caption(f"현재 프로젝트: **{novel_id}**")

    # Current arcs from DB
    arcs = repo.list_arcs(novel_id)
    st.subheader("현재 아크 구조")
    if arcs:
        for arc in sorted(arcs, key=lambda a: a.order_index):
            with st.container(border=True):
                st.markdown(f"**{arc.order_index + 1}. {arc.title}** ({arc.arc_level})")
                st.caption(f"Status: {arc.status}")
    else:
        st.info("아직 아크가 없습니다. 아래에서 스토리 빌드를 실행하세요.")

    # ARC_PLAN draft details
    arc_drafts = repo.list_drafts(novel_id, DraftKind.ARC_PLAN)
    if arc_drafts:
        import json
        try:
            plan = json.loads(arc_drafts[0].content)
            st.subheader("상세 아크 플랜 (최근)")
            for a in plan.get("main_arcs", []):
                st.markdown(f"- **{a.get('arc_number')}. {a.get('title')}**")
                st.write(f"  목표: {a.get('objective', '')} | 갈등: {a.get('conflict', '')} | 보상: {a.get('payoff', '')}")
                st.caption(f"  화 범위: {a.get('episode_range', '')}")
        except Exception:
            pass

    with st.expander("Concepts / Themes / World Rules"):
        st.write("Concepts:", repo.list_concepts(novel_id))
        st.write("Themes:", repo.list_themes(novel_id))
        st.write("World Rules:", repo.list_world_rules(novel_id)[:5])

    st.divider()

    if st.button("🚀 전체 스토리 빌드 실행 (theme_to_arcs)", type="primary"):
        with st.spinner("스토리 빌드 실행 중..."):
            try:
                workflow = build_theme_to_arcs_workflow(
                    repo, memory_store, embedder_factory=embedder_factory
                )
                state = build_theme_to_arcs_state(novel_id, user_preferences="회귀, 성장, 판타지")
                result = workflow.invoke(state)
                st.success("스토리 빌드 완료! 결과가 DB에 저장되었습니다.")

                # Pretty render
                if result.get("arc_output"):
                    st.subheader("생성된 메인 아크")
                    for a in result["arc_output"].get("main_arcs", []):
                        with st.container(border=True):
                            st.markdown(f"**{a.get('arc_number')}. {a.get('title')}**")
                            st.write(f"목표: {a.get('objective')}")
                            st.write(f"갈등: {a.get('conflict')}")
                            st.caption(f"화 범위: {a.get('episode_range')} | 보상: {a.get('payoff')}")

                if result.get("master_output"):
                    mo = result["master_output"]
                    st.subheader("마스터 플랜")
                    st.write(f"**Logline**: {mo.get('logline')}")
                    st.write(f"**Premise**: {mo.get('premise')}")
                    st.write(f"**Ending direction**: {mo.get('ending_direction')}")

                with st.expander("상세 결과 보기"):
                    st.json(result)

                st.info("다음 단계: Episode Build 메뉴에서 에피소드 집필을 진행하세요.")

            except Exception as e:
                st.error(f"실행 실패: {str(e)}")

elif menu == "Episode Build":
    st.header("✍️ Episode Build & Manuscripts")
    st.caption("회차 계획 → 장면 설계 → 본문 작성 및 원고 확인 (Step 6)")

    novel_id = pc.require_current_novel_id()
    if st.button("🔄 다른 프로젝트 변경", key="change_episode"):
        pc.clear_current_novel_id()
        st.rerun()
    st.caption(f"현재 프로젝트: **{novel_id}**")

    episodes = repo.list_episodes(novel_id)
    drafts = repo.list_drafts(novel_id, DraftKind.EPISODE_DRAFT)

    if not episodes:
        st.info("아직 에피소드가 없습니다. Story Build 후 여기서 에피소드를 집필하세요.")
    else:
        # Episode selector
        ep_options = []
        for ep in episodes:
            has_draft = any(d.title and (ep.title_working or '') in d.title for d in drafts)
            status = "✓ 원고 있음" if has_draft else "미집필"
            ep_options.append(f"{ep.episode_number}. {ep.title_working or 'Untitled'} [{status}]")
        selected_idx = st.selectbox(
            "에피소드 선택",
            range(len(ep_options)),
            format_func=lambda i: ep_options[i],
            help="에피소드를 선택하면 계획/비트/원고를 볼 수 있습니다."
        )
        selected_ep = episodes[selected_idx]
        st.subheader(f"에피소드 {selected_ep.episode_number} — {selected_ep.title_working}")

        # Find matching draft (by title or latest fallback)
        matching_draft = None
        for d in drafts:
            if selected_ep.title_working and selected_ep.title_working in d.title:
                matching_draft = d
                break
        if not matching_draft and drafts:
            matching_draft = drafts[0]  # fallback to latest

        # Scene beats (all for now, filter rough)
        beats = [b for b in repo.list_scene_beats(novel_id) if str(selected_ep.episode_number) in str(b.get('episode_id', '')) or True]  # simple

        # Display
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("**Episode Plan / Cycle**")
            if matching_draft:
                st.caption(f"Draft title: {matching_draft.title}")
            else:
                st.caption("아직 집필된 원고 없음")

            st.markdown("**Scene Beats**")
            if beats:
                for b in beats[:6]:  # limit
                    st.markdown(f"- {b.get('objective', '')[:60]}...")
            else:
                st.caption("Scene beats 정보가 아직 없습니다.")

        with col2:
            st.markdown("**원고 (Manuscript)**")
            if matching_draft:
                # Render as nice markdown
                st.markdown(matching_draft.content)
                with st.expander("원고 텍스트 편집 (간단 저장)"):
                    new_content = st.text_area("Draft content", value=matching_draft.content, height=300)
                    if st.button("저장", key=f"save_draft_{matching_draft.id}"):
                        if repo.update_draft_content(matching_draft.id, new_content):
                            st.success("저장 완료!")
                            st.rerun()
            else:
                st.info("이 에피소드의 원고가 아직 없습니다. 아래에서 집필을 실행하세요.")

        # Action buttons
        st.divider()
        if st.button(f"🚀 에피소드 {selected_ep.episode_number} 집필 실행", type="primary"):
            with st.spinner(f"에피소드 {selected_ep.episode_number} 집필 중..."):
                try:
                    workflow = build_episode_to_draft_workflow(
                        repo, memory_store, embedder_factory=embedder_factory
                    )
                    state = build_episode_to_draft_state(
                        repo, novel_id, selected_episode_number=selected_ep.episode_number
                    )
                    result = workflow.invoke(state)
                    st.success("에피소드 집필 완료!")

                    if result.get("draft_output"):
                        draft_out = result["draft_output"]
                        st.subheader("생성된 원고")
                        st.markdown(draft_out.get("draft_text", ""))
                        st.caption(f"Hook: {draft_out.get('ending_hook', '')}")

                    with st.expander("상세 결과"):
                        st.json(result)

                    st.info("원고가 저장되었습니다. 위에서 확인하세요. 필요시 Validation Review에서 검수하세요.")

                except Exception as e:
                    st.error(f"집필 실패: {e}")

elif menu == "Workflow Execution":
    st.header("⚙️ Workflow Execution (고급/수동)")
    st.caption("기본적으로는 'Story Build' 또는 'Episode Build' 메뉴를 추천합니다. 여기서는 직접 워크플로우를 실행할 수 있습니다.")

    # Step 3 enforcement: must have a selected project
    novel_id = pc.require_current_novel_id()

    # Quick switch option
    if st.button("🔄 다른 프로젝트로 변경", key="change_from_workflow"):
        pc.clear_current_novel_id()
        st.rerun()

    st.caption(f"현재 프로젝트: **{novel_id}**")

    # Improved with Korean explanations (user request)
    workflow_options = [
        ("전체 스토리 빌드 (theme_to_arcs) — 테마/마스터플랜/아크 설계", "theme_to_arcs"),
        ("에피소드 집필 (episode_to_draft) — 회차 계획 → 상세 설계 → 본문 작성", "episode_to_draft"),
        ("초안 검수 (draft_validation) — 연속성/설정 충돌 검수", "draft_validation"),
    ]
    workflow_labels = [opt[0] for opt in workflow_options]
    workflow_map = {opt[0]: opt[1] for opt in workflow_options}

    selected_label = st.selectbox(
        "워크플로우 선택 (한글 설명 참고)",
        workflow_labels,
        index=0 if "preferred_workflow" not in st.session_state else 
              next((i for i, opt in enumerate(workflow_options) if opt[1] == st.session_state.get("preferred_workflow")), 0),
        help="각 워크플로우는 순차적으로 사용하세요. 스토리 빌드 → 에피소드 집필 → 검수 순이 일반적입니다."
    )
    workflow_type = workflow_map[selected_label]
    # Clear preferred after use
    if "preferred_workflow" in st.session_state:
        del st.session_state["preferred_workflow"]

    user_preferences = st.text_input(
        "User Preferences (theme_to_arcs)",
        value="회귀, 성장, 판타지",
        disabled=workflow_type != "theme_to_arcs",
    )
    selected_episode = st.number_input(
        "Episode Number (episode_to_draft)",
        min_value=1,
        value=1,
        step=1,
        disabled=workflow_type != "episode_to_draft",
    )

    if st.button("🚀 Run Workflow"):
        with st.spinner(f"Executing {workflow_type}..."):
            try:
                if workflow_type == "theme_to_arcs":
                    workflow = build_theme_to_arcs_workflow(
                        repo, memory_store, embedder_factory=embedder_factory
                    )
                    state = build_theme_to_arcs_state(novel_id, user_preferences=user_preferences)
                    result = workflow.invoke(state)

                elif workflow_type == "episode_to_draft":
                    workflow = build_episode_to_draft_workflow(
                        repo, memory_store, embedder_factory=embedder_factory
                    )
                    state = build_episode_to_draft_state(
                        repo, novel_id, selected_episode_number=int(selected_episode)
                    )
                    result = workflow.invoke(state)

                else:
                    workflow = build_draft_validation_workflow(
                        repo, memory_store, embedder_factory=embedder_factory
                    )
                    state = build_draft_validation_state(repo, novel_id)
                    result = workflow.invoke(state)

                if result.get("status") == "manual_review" or result.get("halted_reason"):
                    st.warning(
                        f"Workflow halted: {result.get('halted_reason') or result.get('status')}"
                    )
                else:
                    st.success("Workflow completed!")
                st.json(result)

            except Exception as e:
                st.error(f"Error executing workflow: {e}")

elif menu == "Validation Review":
    st.header("✅ Validation Review")
    st.caption("현재 프로젝트의 검수 결과를 확인하고 승인/반려하세요. (Story Build나 Episode Build 후 사용 추천)")

    # Step 3 enforcement
    novel_id = pc.require_current_novel_id()

    if st.button("🔄 다른 프로젝트로 변경", key="change_from_validation"):
        pc.clear_current_novel_id()
        st.rerun()

    st.caption(f"현재 프로젝트: **{novel_id}**")
    validations = repo.list_validations(novel_id)

    if not validations:
        st.info("No validation records found for this novel.")
    else:
        for v in validations:
            score = v.get("score")
            score_label = f"{float(score):.2f}" if score is not None else "N/A"
            with st.expander(
                f"Validation: {v['validation_type']} | Score: {score_label} | Status: {v['status']}"
            ):
                st.write(f"**Target Entity:** {v['target_entity_type']} ({v['target_entity_id']})")
                st.write(f"**Issues:** {v['issues_json']}")

                col_app, col_rej = st.columns(2)
                with col_app:
                    if st.button(f"Approve {v['id']}", key=f"app_{v['id']}"):
                        if repo.update_validation_status(v["id"], RecordStatus.APPROVED):
                            st.success("승인 완료")
                            st.rerun()
                with col_rej:
                    if st.button(f"Reject {v['id']}", key=f"rej_{v['id']}"):
                        if repo.update_validation_status(v["id"], RecordStatus.REJECTED):
                            st.success("반려 완료")
                            st.rerun()

elif menu == "System Logs":
    st.header("📜 System Logs")

    # Step 3 enforcement
    novel_id = pc.require_current_novel_id()

    if st.button("🔄 다른 프로젝트로 변경", key="change_from_logs"):
        pc.clear_current_novel_id()
        st.rerun()

    st.caption(f"현재 프로젝트: **{novel_id}**")
    logs = repo.list_generation_runs(novel_id)

    if not logs:
        st.info("No logs found for this novel.")
    else:
        for log in logs:
            created_at = log.get("created_at", "N/A")
            with st.expander(f"Run: {log['run_type']} | {created_at}"):
                st.write(f"**Model:** {log.get('model_name', 'N/A')}")
                st.write(f"**Decision:** {log.get('reviewer_decision', 'N/A')}")
                st.text_area("Raw Output", str(log.get("raw_output", "")), height=200)