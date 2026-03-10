from pathlib import Path
import streamlit as st

_DOC_DIR = Path(__file__).parent.parent.parent / "documentation"

_DOCS = [
    ("User Guide",       "USER_GUIDE.md"),
    ("Adding Skills",    "adding_skills.md"),
    ("AI Process",       "AI_PROCESS.md"),
    ("Codebase",         "CODEBASE.md"),
]


def docs_page() -> None:
    st.title("Documentation")

    tabs = st.tabs([label for label, _ in _DOCS])
    for tab, (_, filename) in zip(tabs, _DOCS):
        with tab:
            path = _DOC_DIR / filename
            if path.exists():
                st.markdown(path.read_text(encoding="utf-8"))
            else:
                st.warning(f"{filename} not found.")
