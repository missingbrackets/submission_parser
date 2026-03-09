# ============================================================
#  ui/pages/analyser.py
#  Submission Analyser page — Streamlit UI.
#  Called as a callable from main.py st.navigation().
# ============================================================

import os

import streamlit as st

from skills import get_skill, available_classes
from core.analysis import run_gap_analysis
from ui.styles import APP_CSS
from ui.components.gap_analysis import render_gap_analysis
from ui.components.data_tabs import render_data_tabs, render_save_section


def render_results(extracted, gap, all_files, folder_path, folder_name, skill, output_folder=None):
    """Render gap analysis, data tabs, and save section for one submission."""
    if output_folder is None:
        output_folder = folder_path

    st.markdown("### 3 · Gap Analysis")
    gap = run_gap_analysis(extracted, skill["required_fields"])
    render_gap_analysis(gap)

    render_data_tabs(extracted, gap, all_files, folder_name, skill)

    render_save_section(extracted, gap, all_files, folder_path, folder_name, skill, output_folder)


def analyser_page():
    """Main Submission Analyser page."""
    st.markdown(APP_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="main-header">
      <h1>SUBMISSION ANALYSER</h1>
      <p>AI-powered extraction · Gap analysis · Rating model data</p>
    </div>
    """, unsafe_allow_html=True)

    # ── SIDEBAR ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")

        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Your Claude API key. Get one at console.anthropic.com",
        )

        st.markdown("---")
        st.markdown("### 📁 Case Folder")

        folder_path = st.text_input(
            "Case folder path",
            placeholder=r"T:\Actuarial\Pricing\MGAs\Sevanta\2026\01_Case Pricing\2026\20260303_Acme",
            help="The root case folder. The app will read from 01_correspondence and 02_data subfolders.",
        )

        st.markdown("---")
        st.markdown("### 📚 Class of Business")
        class_choice = st.selectbox(
            "Select skill / class template",
            options=available_classes(),
            help="Determines the required field checklist and CSV schema",
        )

        st.markdown("---")
        st.markdown("### 🔍 Source Subfolders")
        use_corr = st.checkbox("01_correspondence (emails / docs)", value=True)
        use_data = st.checkbox("02_data (attachments / data files)", value=True)

        st.markdown("---")
        st.markdown("### 📂 Submission Mode")
        batch_mode = st.toggle(
            "Multiple Submissions",
            value=False,
            help="Process a parent folder containing multiple submission subfolders.",
        )
        if batch_mode:
            st.caption("Point the folder path at the **parent** folder. Each subfolder will be treated as one submission.")
            force_rerun = st.checkbox("Re-run all (ignore cache)", value=False)
        else:
            force_rerun = False

        # ── TAB SELECTOR ──────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📑 Display Tabs")
        st.caption("Choose which tabs to show after analysis.")

        _skill_preview = get_skill(class_choice)
        _tab_configs   = _skill_preview["skill_class"].tab_config()

        _tab_states = {}
        for tc in _tab_configs:
            _key = f"tab_show_{tc.section.name}"
            _default = st.session_state.get(_key, tc.default_on)
            _checked = st.checkbox(
                f"{tc.icon} {tc.section.value}",
                value=_default,
                key=_key,
                help=tc.description or tc.section.value,
            )
            _tab_states[tc.section.name] = _checked

        st.session_state["tab_states"] = _tab_states

        st.markdown("---")
        _btn_label = "▶ Run Batch" if st.session_state.get("batch_mode_ui") else "▶ Run Analysis"
        if st.button(_btn_label, type="primary", use_container_width=True):
            st.session_state["run_triggered"] = True
            st.session_state["batch_mode_ui"] = batch_mode
            st.session_state["force_rerun_ui"] = force_rerun

        run_button = st.session_state.get("run_triggered", False)

    # ── MAIN AREA ─────────────────────────────────────────────
    if not run_button:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**Step 1**\n\nEnter your API key and the case folder path in the sidebar.")
        with col2:
            st.info("**Step 2**\n\nSelect the class of business to apply the right skill template.")
        with col3:
            st.info("**Step 3**\n\nClick **Run Analysis** — outputs are saved to the case folder.")

        st.markdown("---")
        st.markdown("#### What this tool produces")
        st.markdown("""
- **AI Summary Report** → saved to `submission_tool_auto_outputs/YYYYMMDD_AI_Summary.txt`
- **Gap Analysis** → critical and advisory missing fields, colour-coded
- **Rating Model CSV** → saved to `submission_tool_auto_outputs/submission_data.csv` (appends each run)
        """)

    if run_button:
        if not api_key:
            st.error("API key is required.")
            st.stop()
        if not folder_path:
            st.error("Folder path is required.")
            st.stop()
        if not os.path.exists(folder_path):
            st.error(f"Folder not found: `{folder_path}`")
            st.stop()

        _batch = st.session_state.get("batch_mode_ui", False)
        _force = st.session_state.get("force_rerun_ui", False)

        if _batch:
            _run_batch(folder_path, class_choice, api_key, use_corr, use_data, _force)
        else:
            _run_single(folder_path, class_choice, api_key, use_corr, use_data, _force)


# ── Single mode ───────────────────────────────────────────────

def _run_single(folder_path, class_choice, api_key, use_corr, use_data, force_rerun):
    from file_parser import extract_folder
    from core.extractor import call_claude_extraction
    from core.analysis import run_gap_analysis

    skill       = get_skill(class_choice)
    folder_name = os.path.basename(folder_path.rstrip("\\/"))

    st.markdown("### 1 · Reading Submission Files")
    all_files = {}
    if use_corr:
        all_files.update(extract_folder(folder_path, "01_correspondence"))
    if use_data:
        df = extract_folder(folder_path, "02_data")
        df = {k: v for k, v in df.items()
              if not k.endswith("AI_Summary.txt") and not k.endswith(".csv")}
        all_files.update(df)

    if not all_files:
        st.error("No supported files found in the selected subfolders.")
        return

    file_cols = st.columns(min(len(all_files), 4))
    for i, (fname, info) in enumerate(all_files.items()):
        with file_cols[i % 4]:
            icon = "✅" if info["text"] else "⚠️"
            st.metric(label=f"{icon} {fname}", value=f"{info['size_kb']} KB",
                      delta=info["status"][:50] if info["status"] else "No text extracted")

    combined_parts = [f"\n\n{'='*50}\nFILE: {fname}\n{'='*50}\n{info['text']}"
                      for fname, info in all_files.items() if info["text"]]
    combined_text = "\n".join(combined_parts)

    if not combined_text.strip():
        st.error("No text could be extracted from any files.")
        return

    st.success(f"Extracted {len(combined_text):,} characters from {len(all_files)} file(s)")

    st.markdown("### 2 · AI Extraction")
    _cache_key = f"{folder_path}|{class_choice}"
    if not force_rerun and st.session_state.get("extracted") and st.session_state.get("_cache_key") == _cache_key:
        extracted = st.session_state["extracted"]
        all_files = st.session_state["all_files"]
        skill     = st.session_state["skill"]
        st.success("Using cached extraction — change folder or skill to re-extract.")
    else:
        with st.spinner(f"Sending to Claude ({skill['label']} skill)..."):
            try:
                extracted, _ = call_claude_extraction(combined_text, skill["system_prompt"], api_key)
                st.session_state["extracted"]   = extracted
                st.session_state["all_files"]   = all_files
                st.session_state["folder_path"] = folder_path
                st.session_state["folder_name"] = folder_name
                st.session_state["skill"]       = skill
                st.session_state["_cache_key"]  = _cache_key
                st.success("Extraction complete")
            except Exception as e:
                st.error(f"Claude API error: {str(e)}")
                return

    gap = run_gap_analysis(extracted, skill["required_fields"])
    render_results(extracted, gap, all_files, folder_path, folder_name, skill)


# ── Batch mode ────────────────────────────────────────────────

def _run_batch(parent_folder, class_choice, api_key, use_corr, use_data, force_rerun):
    import pandas as pd
    from file_parser import extract_folder
    from core.extractor import call_claude_extraction
    from core.analysis import run_gap_analysis
    from core.outputs import (
        build_csv_row, save_csv, build_claims_csv_rows, save_claims_csv,
        build_locations_csv_rows, save_locations_csv,
        build_triage_row, save_triage_csv,
        build_triage_locations_rows, save_triage_locations_csv,
        build_direct_triage_row, save_direct_triage_csv,
    )
    from core.report import save_summary_report

    try:
        subfolders = sorted([
            d for d in os.listdir(parent_folder)
            if os.path.isdir(os.path.join(parent_folder, d))
            and not d.startswith(".")
            and d != "submission_tool_auto_outputs"
        ])
    except Exception as e:
        st.error(f"Cannot read folder: {e}")
        return

    if not subfolders:
        st.error("No subfolders found in the selected parent folder.")
        return

    skill = get_skill(class_choice)

    st.markdown(f"### Found {len(subfolders)} submission folder(s)")
    st.caption("CSVs will be consolidated into the parent folder's `submission_tool_auto_outputs`.")

    batch_results   = st.session_state.get("batch_results", {})
    _cache_key_batch = f"BATCH|{parent_folder}|{class_choice}"
    already_run = (
        not force_rerun
        and st.session_state.get("_cache_key_batch") == _cache_key_batch
        and batch_results
    )

    if already_run:
        st.success(f"Using cached batch results ({len(batch_results)} submissions). Change folder or skill to re-run.")
    else:
        batch_results = {}
        progress_bar = st.progress(0, text="Starting batch...")
        status_area  = st.empty()

        for idx, subfolder_name in enumerate(subfolders):
            subfolder_path = os.path.join(parent_folder, subfolder_name)
            pct = int((idx / len(subfolders)) * 100)
            progress_bar.progress(pct, text=f"Processing {subfolder_name} ({idx+1}/{len(subfolders)})...")
            status_area.info(f"🔄 **{subfolder_name}** — reading files...")

            all_files = {}
            if use_corr:
                all_files.update(extract_folder(subfolder_path, "01_correspondence"))
            if use_data:
                df = extract_folder(subfolder_path, "02_data")
                df = {k: v for k, v in df.items()
                      if not k.endswith("AI_Summary.txt") and not k.endswith(".csv")}
                all_files.update(df)

            if not all_files:
                status_area.warning(f"⚠️ {subfolder_name} — no files found, skipping.")
                batch_results[subfolder_name] = {"error": "No files found", "folder_path": subfolder_path}
                continue

            combined_parts = [f"\n\n{'='*50}\nFILE: {fname}\n{'='*50}\n{info['text']}"
                              for fname, info in all_files.items() if info["text"]]
            combined_text = "\n".join(combined_parts)

            if not combined_text.strip():
                status_area.warning(f"⚠️ {subfolder_name} — no text extractable, skipping.")
                batch_results[subfolder_name] = {"error": "No text extracted", "folder_path": subfolder_path}
                continue

            status_area.info(f"🤖 **{subfolder_name}** — sending to Claude...")
            try:
                extracted, _ = call_claude_extraction(combined_text, skill["system_prompt"], api_key)
            except Exception as e:
                status_area.error(f"❌ {subfolder_name} — Claude error: {e}")
                batch_results[subfolder_name] = {"error": str(e), "folder_path": subfolder_path}
                continue

            gap = run_gap_analysis(extracted, skill["required_fields"])

            status_area.info(f"💾 **{subfolder_name}** — saving outputs...")
            try:
                save_summary_report(extracted, gap, all_files, skill["label"], subfolder_path, subfolder_name)
                csv_row = build_csv_row(extracted, gap, skill["csv_schema"], subfolder_path, skill["label"])
                save_csv(csv_row, skill["csv_schema"], subfolder_path, "submission_data")
                claims_rows = build_claims_csv_rows(extracted, skill.get("claims_csv_schema", []))
                if claims_rows:
                    save_claims_csv(claims_rows, skill["claims_csv_schema"], subfolder_path)
                if extracted.get("sov_locations") is not None or extracted.get("tiv_total"):
                    loc_rows, loc_schema = build_locations_csv_rows(extracted)
                    if loc_rows:
                        save_locations_csv(loc_rows, loc_schema, subfolder_path)
                save_csv(csv_row, skill["csv_schema"], parent_folder, "submission_data_all")
                if claims_rows:
                    save_claims_csv(claims_rows, skill["claims_csv_schema"], parent_folder)
                skill_code = skill.get("code", "")
                if skill_code == "PVQ":
                    try:
                        _tr = build_triage_row(extracted, gap, subfolder_path, skill["label"])
                        save_triage_csv(_tr, parent_folder)
                        _tl_rows, _tl_schema = build_triage_locations_rows(extracted)
                        if _tl_rows:
                            save_triage_locations_csv(_tl_rows, _tl_schema, parent_folder)
                    except Exception:
                        pass
                elif skill_code == "PVDT":
                    try:
                        _dtr = build_direct_triage_row(extracted, gap, subfolder_path, skill["label"])
                        save_direct_triage_csv(_dtr, parent_folder)
                    except Exception:
                        pass
            except Exception as e:
                st.warning(f"⚠️ {subfolder_name} — save error: {e}")

            batch_results[subfolder_name] = {
                "extracted":   extracted,
                "gap":         gap,
                "all_files":   all_files,
                "folder_path": subfolder_path,
                "folder_name": subfolder_name,
            }

        progress_bar.progress(100, text="Batch complete ✅")
        status_area.empty()
        st.session_state["batch_results"]    = batch_results
        st.session_state["_cache_key_batch"] = _cache_key_batch

    # ── Results summary table ─────────────────────────────────
    st.markdown("### Batch Results")
    summary_rows = []
    for name, res in batch_results.items():
        if "error" in res:
            summary_rows.append({"Folder": name, "Status": f"❌ {res['error']}", "Quality": "—", "Critical Gaps": "—", "Insured": "—"})
        else:
            g = res["gap"]
            summary_rows.append({
                "Folder":        name,
                "Status":        "✅ OK",
                "Quality":       g["data_quality_score"],
                "Critical Gaps": g["critical_count"],
                "Insured":       res["extracted"].get("insured_name") or "—",
            })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    ok_results = {k: v for k, v in batch_results.items() if "error" not in v}
    if not ok_results:
        st.warning("No submissions processed successfully.")
        return

    st.markdown("---")
    st.markdown("### 📂 View Submission")
    selected = st.selectbox(
        "Select submission to review",
        options=list(ok_results.keys()),
        key="batch_selected_submission",
    )

    if selected:
        res = ok_results[selected]
        st.markdown(f"#### {selected}")
        render_results(
            extracted=res["extracted"],
            gap=res["gap"],
            all_files=res["all_files"],
            folder_path=res["folder_path"],
            folder_name=res["folder_name"],
            skill=skill,
            output_folder=parent_folder,
        )
