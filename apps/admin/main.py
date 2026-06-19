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
from my_agent.domain import RecordStatus
from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from packages.embeddings import EmbedderFactory
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
menu = st.sidebar.radio("Menu", ["Project Overview", "Workflow Execution", "Validation Review", "System Logs"])

if menu == "Project Overview":
    st.header("📚 Project Overview")
    novels = repo.list_novels()
    if not novels:
        st.info("No novels found in the database.")
    else:
        df = pd.DataFrame(
            [{"Novel ID": n.novel_id, "Title": n.title, "Genre": n.genre, "Status": n.status} for n in novels]
        )
        st.table(df)

        selected_novel_id = st.selectbox("Select Novel for Details", [n.novel_id for n in novels])
        if selected_novel_id:
            st.subheader(f"Details: {selected_novel_id}")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Characters**")
                chars = repo.list_characters(selected_novel_id)
                st.write(chars if chars else "No characters defined.")
            with col2:
                st.write("**Episodes**")
                eps = repo.list_episodes(selected_novel_id)
                st.write(eps if eps else "No episodes defined.")

elif menu == "Workflow Execution":
    st.header("⚙️ Workflow Execution")

    novels = repo.list_novels()
    if not novels:
        st.error("Please create a novel first. Run: .\\scripts\\run.ps1 bootstrap")
    else:
        novel_id = st.selectbox("Select Novel", [n.novel_id for n in novels])

        workflow_type = st.selectbox(
            "Select Workflow",
            ["theme_to_arcs", "episode_to_draft", "draft_validation"],
        )

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

    novels = repo.list_novels()
    if not novels:
        st.info("No novels found.")
    else:
        novel_id = st.selectbox("Select Novel", [n.novel_id for n in novels])
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
                            import sqlite3

                            conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
                            conn.execute(
                                "UPDATE validations SET status = ? WHERE id = ?",
                                (RecordStatus.APPROVED.value, v["id"]),
                            )
                            conn.commit()
                            conn.close()
                            st.rerun()
                    with col_rej:
                        if st.button(f"Reject {v['id']}", key=f"rej_{v['id']}"):
                            import sqlite3

                            conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
                            conn.execute(
                                "UPDATE validations SET status = ? WHERE id = ?",
                                (RecordStatus.REJECTED.value, v["id"]),
                            )
                            conn.commit()
                            conn.close()
                            st.rerun()

elif menu == "System Logs":
    st.header("📜 System Logs")

    novels = repo.list_novels()
    if not novels:
        st.info("No novels found.")
    else:
        novel_id = st.selectbox("Select Novel", [n.novel_id for n in novels])
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