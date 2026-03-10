# ============================================================
#  Submission Analyser — entry point
#
#  Run with:  streamlit run main.py
#
#  This file is intentionally minimal.  All page logic lives in:
#    ui/pages/analyser.py       — Submission Analyser page
#    ui/pages/skill_editor.py   — Skill Editor page
#  All business / AI logic lives in:
#    core/                      — pure Python, no UI dependencies
# ============================================================

import streamlit as st

st.set_page_config(
    page_title="Submission Analyser",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.pages.analyser import analyser_page
from ui.pages.skill_editor import skill_editor_page

pg = st.navigation([
    st.Page(analyser_page,    title="Submission Analyser", icon="📋"),
    st.Page(skill_editor_page, title="Skill Viewer",         icon="📖"),
])
pg.run()
