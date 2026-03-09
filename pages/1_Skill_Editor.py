# ============================================================
#  pages/1_Skill_Editor.py  — thin wrapper
#
#  Delegates to ui/pages/skill_editor.py so the page can also
#  be reached via Streamlit's legacy pages/ directory discovery
#  if st.navigation is not used.
# ============================================================

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from ui.pages.skill_editor import skill_editor_page

skill_editor_page()
