# ============================================================
#  ui/styles.py
#  Shared CSS injected into every Streamlit page.
# ============================================================

APP_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Mono', monospace; }

    .main-header {
        background: #0B0F1A;
        color: #00C2FF;
        padding: 18px 24px 12px;
        border-bottom: 2px solid #00C2FF;
        margin: -1rem -1rem 1.5rem -1rem;
        font-family: 'DM Mono', monospace;
    }
    .main-header h1 { color: #fff; font-size: 1.4rem; margin: 0; letter-spacing: 0.1em; }
    .main-header p  { color: #6B7B99; font-size: 0.75rem; margin: 4px 0 0; }

    .gap-critical {
        background: #2A1215; border-left: 3px solid #EF4444;
        padding: 6px 10px; margin: 3px 0; border-radius: 2px;
        font-size: 0.8rem; color: #FCA5A5;
    }
    .gap-advisory {
        background: #2A1F0A; border-left: 3px solid #F59E0B;
        padding: 6px 10px; margin: 3px 0; border-radius: 2px;
        font-size: 0.8rem; color: #FCD34D;
    }
    .gap-ok {
        background: #0A2A14; border-left: 3px solid #22C55E;
        padding: 6px 10px; margin: 3px 0; border-radius: 2px;
        font-size: 0.8rem; color: #86EFAC;
    }
    .field-row {
        display: flex; justify-content: space-between;
        padding: 4px 0; border-bottom: 1px solid #1E2D45;
        font-size: 0.8rem;
    }
    .field-label { color: #6B7B99; }
    .field-value { color: #E2E8F0; font-weight: 500; }
    .field-missing { color: #EF4444; font-style: italic; }

    .score-badge {
        display: inline-block; padding: 4px 14px;
        border-radius: 20px; font-weight: 700; font-size: 1.1rem;
    }
    div[data-testid="stExpander"] { border: 1px solid #1E2D45 !important; }
</style>
"""

EDITOR_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'DM Mono', monospace; }
    .main-header {
        background: #0B0F1A; color: #00C2FF;
        padding: 18px 24px 12px;
        border-bottom: 2px solid #00C2FF;
        margin: -1rem -1rem 1.5rem -1rem;
    }
    .main-header h1 { color: #fff; font-size: 1.4rem; margin: 0; letter-spacing: 0.1em; }
    .main-header p  { color: #6B7B99; font-size: 0.75rem; margin: 4px 0 0; }
    .field-row {
        display: flex; justify-content: space-between;
        padding: 4px 0; border-bottom: 1px solid #1E2D45; font-size: 0.8rem;
    }
    .field-label { color: #6B7B99; }
    .field-value { color: #E2E8F0; font-weight: 500; }
    .badge-override {
        display:inline-block; padding:2px 8px; border-radius:10px;
        background:#1A2744; border:1px solid #00C2FF;
        color:#00C2FF; font-size:0.7rem; margin-left:8px;
    }
    .badge-new {
        display:inline-block; padding:2px 8px; border-radius:10px;
        background:#0A2A14; border:1px solid #22C55E;
        color:#86EFAC; font-size:0.7rem; margin-left:8px;
    }
    .badge-base {
        display:inline-block; padding:2px 8px; border-radius:10px;
        background:#1A1A1A; border:1px solid #374151;
        color:#9CA3AF; font-size:0.7rem; margin-left:8px;
    }
</style>
"""
