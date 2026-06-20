from __future__ import annotations

from typing import Optional

import streamlit as st

# Key used in st.session_state for the currently selected novel/project
CURRENT_NOVEL_ID_KEY = "current_novel_id"


def get_current_novel_id() -> Optional[str]:
    """Return the currently selected novel_id from session state, or None."""
    return st.session_state.get(CURRENT_NOVEL_ID_KEY)


def set_current_novel_id(novel_id: str) -> None:
    """Set the current novel/project in session state."""
    if novel_id:
        st.session_state[CURRENT_NOVEL_ID_KEY] = novel_id


def clear_current_novel_id() -> None:
    """Clear the current project selection."""
    if CURRENT_NOVEL_ID_KEY in st.session_state:
        del st.session_state[CURRENT_NOVEL_ID_KEY]


def require_current_novel_id() -> str:
    """
    Return current novel_id or stop execution with a warning.
    Use this at the top of project-scoped pages/sections.
    """
    novel_id = get_current_novel_id()
    if not novel_id:
        st.warning("⚠️ 프로젝트를 먼저 선택해주세요. Projects Dashboard에서 프로젝트를 선택하거나 새로 만드세요.")
        st.stop()
    return novel_id


def get_current_project_header(repo) -> None:
    """
    Optional helper: render a small current project indicator.
    Pass the repo to fetch title if desired (for later steps).
    """
    novel_id = get_current_novel_id()
    if novel_id:
        st.caption(f"📁 현재 프로젝트: **{novel_id}**")
    else:
        st.caption("📁 프로젝트가 선택되지 않았습니다.")