import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Any

from src.my_agent.repository import NovelRepository
from src.my_agent.database import DEFAULT_SQLITE_PATH
from src.my_agent.domain import RecordStatus
from packages.orchestrator.workflows import (
    build_theme_to_arcs_workflow,
    build_episode_to_draft_workflow,
    build_draft_validation_workflow,
)
from packages.embeddings import EmbedderFactory

# --- Configuration ---
st.set_page_config(page_title="AI Novel Admin Console", layout="wide")

# Initialize Repository and Shared Resources
@st.cache_resource
def get_resources():
    repo = NovelRepository(DEFAULT_SQLITE_PATH)
    embedder_factory = EmbedderFactory(mode="local")
    # Mock memory store as it's usually a complex object
    memory_store = MagicMockMemoryStore() 
    return repo, embedder_factory, memory_store

class MagicMockMemoryStore:
    """Simple mock for memory store to avoid complex initialization in UI"""
    def query(self, *args, **kwargs): return []
    def add(self, *args, **kwargs): pass

repo, embedder_factory, memory_store = get_resources()

# --- Sidebar Navigation ---
st.sidebar.title("Novel System Admin")
menu = st.sidebar.radio("Menu", ["Project Overview", "Workflow Execution", "Validation Review", "System Logs"])

# --- 1. Project Overview ---
if menu == "Project Overview":
    st.header("📚 Project Overview")
    novels = repo.list_novels()
    if not novels:
        st.info("No novels found in the database.")
    else:
        df = pd.DataFrame([
            {"Novel ID": n.novel_id, "Title": n.title, "Genre": n.genre, "Status": n.status} 
            for n in novels
        ])
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

# --- 2. Workflow Execution ---
elif menu == "Workflow Execution":
    st.header("⚙️ Workflow Execution")
    
    novels = repo.list_novels()
    if not novels:
        st.error("Please create a novel first.")
    else:
        novel_id = st.selectbox("Select Novel", [n.novel_id for n in novels])
        
        workflow_type = st.selectbox(
            "Select Workflow", 
            ["theme_to_arcs", "episode_to_draft", "draft_validation"]
        )
        
        if st.button("🚀 Run Workflow"):
            with st.spinner(f"Executing {workflow_type}..."):
                try:
                    if workflow_type == "theme_to_arcs":
                        workflow = build_theme_to_arcs_workflow(repo, memory_store, embedder_factory=embedder_factory)
                        # Simplified input for UI
                        from packages.schemas.agent_schemas import ThemeToArcsRequest
                        request = ThemeToArcsRequest(novel_id=novel_id, user_preferences="High fantasy, epic scale")
                        result = workflow.invoke({"request": request})
                        st.success("Workflow Completed!")
                        st.json(result)
                        
                    elif workflow_type == "episode_to_draft":
                        workflow = build_episode_to_draft_workflow(repo, memory_store, embedder_factory=embedder_factory)
                        from packages.schemas.agent_schemas import EpisodeToDraftRequest
                        request = EpisodeToDraftRequest(novel_id=novel_id, approved_arcs=[]) # Simplified
                        result = workflow.invoke({"request": request})
                        st.success("Workflow Completed!")
                        st.json(result)
                        
                    elif workflow_type == "draft_validation":
                        workflow = build_draft_validation_workflow(repo, memory_store, embedder_factory=embedder_factory)
                        from packages.schemas.agent_schemas import DraftValidationRequest
                        # Get latest draft
                        drafts = repo.list_drafts(novel_id) if hasattr(repo, 'list_drafts') else []
                        draft_id = drafts[0].id if drafts else "unknown"
                        request = DraftValidationRequest(novel_id=novel_id, draft_id=draft_id, draft_text="Sample text")
                        result = workflow.invoke({"request": request})
                        st.success("Workflow Completed!")
                        st.json(result)
                except Exception as e:
                    st.error(f"Error executing workflow: {e}")

# --- 3. Validation Review ---
elif menu == "Validation Review":
    st.header("✅ Validation Review")
    
    novels = repo.list_novels()
    if not novels:
        st.info("No novels found.")
    else:
        novel_id = st.selectbox("Select Novel", [n.novel_id for n in novels])
        
        # Fetch validations from repo
        # Note: Assuming repo has a list_validations method or we use raw SQL
        if hasattr(repo, 'list_validations'):
            validations = repo.list_validations(novel_id)
        else:
            # Fallback to raw query if method missing in repo
            import sqlite3
            conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
            validations = pd.read_sql_query(
                f"SELECT * FROM validations WHERE novel_id = '{novel_id}'", conn
            ).to_dict('records')
            conn.close()
            
        if not validations:
            st.info("No validation records found for this novel.")
        else:
            for v in validations:
                with st.expander(f"Validation: {v['validation_type']} | Score: {v['score']:.2f} | Status: {v['status']}"):
                    st.write(f"**Target Entity:** {v['target_entity_type']} ({v['target_entity_id']})")
                    st.write(f"**Issues:** {v['issues_json']}")
                    
                    col_app, col_rej = st.columns(2)
                    with col_app:
                        if st.button(f"Approve {v['id']}", key=f"app_{v['id']}"):
                            # Update status to APPROVED
                            import sqlite3
                            conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
                            conn.execute(
                                "UPDATE validations SET status = ? WHERE id = ?", 
                                (RecordStatus.APPROVED.value, v['id'])
                            )
                            conn.commit()
                            conn.close()
                            st.rerun()
                    with col_rej:
                        if st.button(f"Reject {v['id']}", key=f"rej_{v['id']}"):
                            # Update status to REJECTED
                            import sqlite3
                            conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
                            conn.execute(
                                "UPDATE validations SET status = ? WHERE id = ?", 
                                (RecordStatus.REJECTED.value, v['id'])
                            )
                            conn.commit()
                            conn.close()
                            st.rerun()

# --- 4. System Logs ---
elif menu == "System Logs":
    st.header("📜 System Logs")
    
    novels = repo.list_novels()
    if not novels:
        st.info("No novels found.")
    else:
        novel_id = st.selectbox("Select Novel", [n.novel_id for n in novels])
        
        # Fetch recent generation runs
        import sqlite3
        conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
        logs = pd.read_sql_query(
            f"SELECT id, run_type, raw_output, created_at FROM generation_runs WHERE novel_id = '{novel_id}' ORDER BY created_at DESC LIMIT 10", 
            conn
        ).to_dict('records')
        conn.close()
        
        if not logs:
            st.info("No logs found for this novel.")
        else:
            for log in logs:
                with st.expander(f"Run: {log['run_type']} | {log['created_at']}"):
                    st.text_area("Raw Output", log['raw_output'], height=200)
