# ============================================================
#  PINE WALK — Submission Analyser
#  Streamlit App  |  main.py
#
#  Run with:  streamlit run main.py
# ============================================================

import os
import json
import streamlit as st
from pathlib import Path

from skills import get_skill, available_classes
from file_parser import extract_folder, extract_file
from claude_caller import (
    call_claude_extraction,
    run_gap_analysis,
    build_csv_row,
    save_csv,
    build_claims_csv_rows,
    save_claims_csv,
    save_summary_report,
)

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="Pine Walk — Submission Analyser",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────
st.markdown("""
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
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>PINE WALK &nbsp;|&nbsp; SUBMISSION ANALYSER</h1>
  <p>AI-powered extraction · Gap analysis · Rating model data</p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────
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
        help="The root case folder (e.g. 20260303_InuredName). The app will read from 01_correspondence and 02_data subfolders.",
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
    use_corr  = st.checkbox("01_correspondence (emails / docs)", value=True)
    use_data  = st.checkbox("02_data (attachments / data files)", value=True)

    st.markdown("---")
    if st.button("▶ Run Analysis", type="primary", use_container_width=True):
        st.session_state["run_triggered"] = True

    run_button = st.session_state.get("run_triggered", False)

# ── MAIN AREA ─────────────────────────────────────────────────

if not run_button:
    # ── Welcome state ─────────────────────────────────────────
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
- **AI Summary Report** → saved to `01_correspondence/YYYYMMDD_AI_Summary.txt`
- **Gap Analysis** → critical and advisory missing fields, colour-coded
- **Rating Model CSV** → saved to `02_data/submission_data.csv` (appends each run)
    """)

else:
    # ── VALIDATION ────────────────────────────────────────────
    errors = []
    if not api_key:
        errors.append("API key is required.")
    if not folder_path:
        errors.append("Case folder path is required.")
    elif not os.path.exists(folder_path):
        errors.append(f"Folder not found: `{folder_path}`")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    skill = get_skill(class_choice)
    folder_name = os.path.basename(folder_path.rstrip("\\/"))

    # ── STEP 1: FILE EXTRACTION ───────────────────────────────
    st.markdown("### 1 · Reading Submission Files")

    all_files = {}
    if use_corr:
        corr_files = extract_folder(folder_path, "01_correspondence")
        all_files.update(corr_files)
    if use_data:
        data_files = extract_folder(folder_path, "02_data")
        # Exclude any existing AI summary or CSV to avoid circular references
        data_files = {
            k: v for k, v in data_files.items()
            if not k.endswith("AI_Summary.txt") and not k.endswith(".csv")
        }
        all_files.update(data_files)

    if not all_files:
        st.error("No supported files found in the selected subfolders.")
        st.stop()

    file_cols = st.columns(min(len(all_files), 4))
    for i, (fname, info) in enumerate(all_files.items()):
        with file_cols[i % 4]:
            icon = "✅" if info["text"] else "⚠️"
            st.metric(
                label=f"{icon} {fname}",
                value=f"{info['size_kb']} KB",
                delta=info["status"][:50] if info["status"] else "No text extracted",
            )

    # Combine all extracted text
    combined_parts = []
    for fname, info in all_files.items():
        if info["text"]:
            combined_parts.append(f"\n\n{'='*50}\nFILE: {fname}\n{'='*50}\n{info['text']}")

    combined_text = "\n".join(combined_parts)

    if not combined_text.strip():
        st.error("No text could be extracted from any files. Check file formats.")
        st.stop()

    st.success(f"Extracted {len(combined_text):,} characters from {len(all_files)} file(s)")

    # ── STEP 2: CLAUDE EXTRACTION ─────────────────────────────
    st.markdown("### 2 · AI Extraction")

    with st.spinner(f"Sending to Claude ({skill['label']} skill)..."):
        try:
            extracted, raw_response = call_claude_extraction(
                combined_text=combined_text,
                system_prompt=skill["system_prompt"],
                api_key=api_key,
            )
            st.session_state["extracted"] = extracted
            st.session_state["raw_response"] = raw_response
            st.session_state["all_files"] = all_files
            st.session_state["folder_path"] = folder_path
            st.session_state["folder_name"] = folder_name
            st.session_state["skill"] = skill
            st.success("Extraction complete")
        except Exception as e:
            st.error(f"Claude API error: {str(e)}")
            st.stop()

    # ── STEP 3: GAP ANALYSIS ──────────────────────────────────
    st.markdown("### 3 · Gap Analysis")

    # Load from session_state so save button works after rerun
    extracted    = st.session_state.get("extracted", extracted)
    all_files    = st.session_state.get("all_files", all_files)
    folder_path  = st.session_state.get("folder_path", folder_path)
    folder_name  = st.session_state.get("folder_name", folder_name)
    skill        = st.session_state.get("skill", skill)

    gap = run_gap_analysis(extracted, skill["required_fields"])

    # Score display
    score = gap["data_quality_score"]
    score_color = "#22C55E" if score >= 75 else "#F59E0B" if score >= 50 else "#EF4444"
    score_label = "GOOD" if score >= 75 else "MODERATE" if score >= 50 else "POOR"

    col_score, col_crit, col_adv, col_ok = st.columns(4)
    with col_score:
        st.markdown(f"""
        <div style="text-align:center; padding:12px; background:#111827; border-radius:6px; border:1px solid #1E2D45;">
          <div style="font-size:0.7rem; color:#6B7B99; text-transform:uppercase; letter-spacing:0.1em;">Data Quality</div>
          <div style="font-size:2rem; font-weight:700; color:{score_color};">{score}</div>
          <div style="font-size:0.75rem; color:{score_color};">{score_label}</div>
        </div>""", unsafe_allow_html=True)
    with col_crit:
        st.metric("Critical Gaps", gap["critical_count"], delta="blocking" if gap["critical_count"] else "none", delta_color="inverse")
    with col_adv:
        st.metric("Advisory Gaps", gap["advisory_count"], delta="review", delta_color="off")
    with col_ok:
        st.metric("Fields Present", f"{gap['present_count']}/{gap['total_fields']}")

    # Gap detail columns
    gcol1, gcol2 = st.columns(2)

    with gcol1:
        if gap["critical_gaps"]:
            st.markdown("**🔴 Critical Missing Fields**")
            for _, label in gap["critical_gaps"]:
                st.markdown(f'<div class="gap-critical">✗ {label}</div>', unsafe_allow_html=True)
        else:
            st.markdown("**✅ No critical gaps**")

    with gcol2:
        if gap["advisory_gaps"]:
            st.markdown("**🟡 Advisory Missing Fields**")
            for _, label in gap["advisory_gaps"]:
                st.markdown(f'<div class="gap-advisory">⚑ {label}</div>', unsafe_allow_html=True)
        else:
            st.markdown("**✅ No advisory gaps**")

    # ── STEP 4: EXTRACTED DATA DISPLAY ───────────────────────
    st.markdown("### 4 · Extracted Data")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Risk Summary", "📉 Loss History", "🏷 Coverage", "🚩 UW Flags", "📊 Claims CSV", "🔍 Raw JSON"])

    with tab1:
        c1, c2 = st.columns(2)

        def show_field(label, key, col):
            val = extracted.get(key)
            display = str(val) if val else None
            col.markdown(
                f'<div class="field-row">'
                f'<span class="field-label">{label}</span>'
                f'<span class="{"field-value" if display else "field-missing"}">'
                f'{display or "— not found"}</span></div>',
                unsafe_allow_html=True
            )

        with c1:
            st.markdown("**Insured**")
            for lbl, key in [
                ("Insured Name", "insured_name"),
                ("Country", "insured_country"),
                ("Industry / SIC", "industry_sector"),
                ("Annual Revenue", "annual_revenue"),
                ("Employees", "number_of_employees"),
                ("Broker", "broker_name"),
            ]:
                show_field(lbl, key, c1)

            st.markdown("")
            st.markdown("**Policy**")
            for lbl, key in [
                ("Period From", "policy_period_start"),
                ("Period To", "policy_period_end"),
                ("Trigger", "coverage_trigger"),
                ("Retro Date", "retroactive_date"),
                ("Jurisdiction", "jurisdiction"),
                ("Territory", "territorial_scope"),
            ]:
                show_field(lbl, key, c1)

        with c2:
            st.markdown("**Limits & Structure**")
            for lbl, key in [
                ("Limit Any One Claim", "limit_any_one_claim"),
                ("Annual Aggregate", "limit_aggregate"),
                ("Excess / Attachment", "excess_point"),
                ("Deductible / SIR", "deductible"),
                ("Sub-limits", "sublimits"),
            ]:
                show_field(lbl, key, c2)

            st.markdown("")
            st.markdown("**Premium**")
            for lbl, key in [
                ("Premium Sought (Gross)", "premium_sought_gross"),
                ("Brokerage %", "brokerage_pct"),
                ("Basis", "premium_basis"),
                ("Prior Insurer", "prior_insurer"),
                ("Prior Premium", "prior_premium"),
            ]:
                show_field(lbl, key, c2)

        # Risk flags
        st.markdown("")
        st.markdown("**Risk Flags**")
        flags = [
            ("Pending Litigation", "pending_litigation"),
            ("Prior Declinatures", "prior_declinatures"),
        ]
        for lbl, key in flags:
            val = extracted.get(key)
            if val and str(val).lower() not in ("none", "null", "no", "none disclosed"):
                st.warning(f"⚠️ **{lbl}:** {val}")
            else:
                st.success(f"✅ **{lbl}:** {val or 'Not disclosed'}")

    with tab2:
        loss_hist = extracted.get("loss_history", [])
        if loss_hist:
            import pandas as pd
            rows = []
            for yr in loss_hist:
                rows.append({
                    "Year":            yr.get("year", ""),
                    "Premium":         yr.get("premium", ""),
                    "Losses (Paid)":   yr.get("losses_paid", ""),
                    "Losses (O/S)":    yr.get("losses_outstanding", ""),
                    "Losses (Total)":  yr.get("losses_total_incurred", ""),
                    "Claims Count":    yr.get("claims_count", ""),
                    "Large Loss":      "⚠️ YES" if yr.get("large_loss_flag") else "",
                    "Notes":           yr.get("notes", ""),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            large = extracted.get("large_losses", [])
            if large:
                st.markdown("**Large Losses Detail**")
                for ll in large:
                    st.markdown(f"- **{ll.get('year','?')}** | {ll.get('amount','?')} | "
                                f"{ll.get('status','?')} | {ll.get('description','')}")
        else:
            st.warning("No loss history extracted from submission materials.")

    with tab3:
        coverage_map = [
            ("General / Public Liability", "coverage_gl"),
            ("Products Liability",          "coverage_pl"),
            ("Employers Liability",          "coverage_el"),
            ("Professional Indemnity",       "coverage_pi"),
            ("Directors & Officers",         "coverage_do"),
        ]
        for label, key in coverage_map:
            val = extracted.get(key, "Unknown")
            icon = "✅" if val == "Y" else "❌" if val == "N" else "❓"
            st.markdown(f"{icon} **{label}** — {val}")

        features = extracted.get("notable_features", [])
        if features:
            st.markdown("")
            st.markdown("**Notable Features / Endorsements**")
            for feat in features:
                st.markdown(f"• {feat}")

    with tab6:
        st.code(json.dumps(extracted, indent=2), language="json")
        st.caption(f"Extraction confidence: {extracted.get('extraction_confidence', 'Not stated')}")
        if extracted.get("extraction_notes"):
            st.info(extracted["extraction_notes"])

    with tab4:
        uw_flags  = extracted.get("uw_analyst_flags", [])
        conflicts = extracted.get("data_conflicts", [])
        questions = extracted.get("questions_for_broker", [])

        # Summary counts
        red_flags   = [f for f in uw_flags if str(f.get("severity","")).upper() == "RED"]
        amber_flags = [f for f in uw_flags if str(f.get("severity","")).upper() == "AMBER"]
        info_flags  = [f for f in uw_flags if str(f.get("severity","")).upper() == "INFO"]

        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("🔴 RED Flags",   len(red_flags))
        fc2.metric("🟡 AMBER Flags", len(amber_flags))
        fc3.metric("ℹ️ INFO",        len(info_flags))
        fc4.metric("❓ Questions",   len([q for q in questions if q and str(q).strip()]))

        # UW flags
        if uw_flags:
            st.markdown("**Underwriter Analyst Flags**")
            severity_order = {"RED": 0, "AMBER": 1, "INFO": 2}
            sorted_flags = sorted(uw_flags, key=lambda x: severity_order.get(str(x.get("severity","INFO")).upper(), 2))
            for flag in sorted_flags:
                sev      = str(flag.get("severity", "INFO")).upper()
                category = flag.get("category", "")
                title    = flag.get("flag", "")
                detail   = flag.get("detail", "")
                color    = "#EF4444" if sev == "RED" else "#F59E0B" if sev == "AMBER" else "#6B7B99"
                bg       = "#2A1215" if sev == "RED" else "#2A1F0A" if sev == "AMBER" else "#111827"
                st.markdown(
                    f'''<div style="background:{bg}; border-left:3px solid {color}; padding:10px 14px; margin:6px 0; border-radius:3px;">
                    <div style="font-size:0.7rem; color:{color}; font-weight:700; letter-spacing:0.08em;">{sev} &nbsp;·&nbsp; {category.upper()}</div>
                    <div style="font-size:0.85rem; color:#E2E8F0; font-weight:600; margin:3px 0;">{title}</div>
                    <div style="font-size:0.78rem; color:#94A3B8; line-height:1.5;">{detail}</div>
                    </div>''', unsafe_allow_html=True)
        else:
            st.success("No underwriter flags raised.")

        # Data conflicts
        valid_conflicts = [c for c in conflicts if c.get("field") and c.get("value_a")]
        if valid_conflicts:
            st.markdown("")
            st.markdown("**Data Conflicts Identified**")
            for c in valid_conflicts:
                st.markdown(
                    f'''<div style="background:#1A1A2E; border-left:3px solid #8B5CF6; padding:10px 14px; margin:6px 0; border-radius:3px;">
                    <div style="font-size:0.7rem; color:#8B5CF6; font-weight:700;">CONFLICT · {c.get("field","").upper()}</div>
                    <div style="font-size:0.8rem; color:#E2E8F0; margin:3px 0;">
                      <b>A:</b> {c.get("value_a","")} <span style="color:#6B7B99">({c.get("source_a","")})</span><br>
                      <b>B:</b> {c.get("value_b","")} <span style="color:#6B7B99">({c.get("source_b","")})</span>
                    </div>
                    <div style="font-size:0.78rem; color:#94A3B8;">Resolution: {c.get("resolution","Manual review required")}</div>
                    </div>''', unsafe_allow_html=True)

        # Questions for broker
        valid_questions = [q for q in questions if q and str(q).strip()]
        if valid_questions:
            st.markdown("")
            st.markdown("**Questions for Broker**")
            for i, q in enumerate(valid_questions, 1):
                st.markdown(
                    f'<div style="background:#111827; border:1px solid #1E2D45; padding:8px 14px; margin:4px 0; border-radius:3px; font-size:0.82rem; color:#E2E8F0;">{i}. {q}</div>',
                    unsafe_allow_html=True)

    with tab5:
        claims_rows = build_claims_csv_rows(extracted, skill.get("claims_csv_schema", []))
        if claims_rows:
            import pandas as pd
            df_claims = pd.DataFrame(claims_rows)
            st.caption(f"{len(claims_rows)} row(s) — one per year + individual large losses. "
                       "Segment_1, Segment_2 and Manual Claim Adjustments left blank for you to complete.")
            st.dataframe(df_claims, use_container_width=True, hide_index=True)
        else:
            st.warning("No loss history found to build claims rows from.")

    # ── STEP 5: BUILD & SAVE OUTPUTS ─────────────────────────
    st.markdown("### 5 · Save Outputs")

    claims_rows = build_claims_csv_rows(extracted, skill.get('claims_csv_schema', []))

    csv_row = build_csv_row(
        extracted=extracted,
        gap_analysis=gap,
        csv_schema=skill["csv_schema"],
        source_folder=folder_path,
        class_label=skill["label"],
    )

    save_col1, save_col2 = st.columns(2)

    with save_col1:
        if st.button("💾 Save Summary Report + CSV", type="primary", use_container_width=True):
            try:
                # Save summary
                summary_path = save_summary_report(
                    extracted=extracted,
                    gap_analysis=gap,
                    source_files=all_files,
                    class_label=skill["label"],
                    output_folder=folder_path,
                    folder_name=folder_name,
                )
                # Save submission CSV
                csv_path = save_csv(
                    row=csv_row,
                    csv_schema=skill["csv_schema"],
                    output_folder=folder_path,
                    filename_prefix="submission_data",
                )
                # Save claims CSV
                claims_path = ""
                if claims_rows and skill.get("claims_csv_schema"):
                    claims_path = save_claims_csv(
                        rows=claims_rows,
                        claims_csv_schema=skill["claims_csv_schema"],
                        output_folder=folder_path,
                    )
                st.success(f"✅ Summary saved:\n`{summary_path}`")
                st.success(f"✅ Submission CSV saved:\n`{csv_path}`")
                if claims_path:
                    st.success(f"✅ Claims CSV saved:\n`{claims_path}`")
            except Exception as e:
                st.error(f"Save failed: {str(e)}")

    with save_col2:
        # Preview CSV row
        with st.expander("Preview CSV row"):
            preview_items = [(k, v) for k, v in csv_row.items() if v]
            for k, v in preview_items:
                st.markdown(f'<div class="field-row"><span class="field-label">{k}</span>'
                            f'<span class="field-value">{v}</span></div>',
                            unsafe_allow_html=True)

    # ── EXTRACTION CONFIDENCE ─────────────────────────────────
    if extracted.get("extraction_notes"):
        st.markdown("---")
        st.info(f"**Extraction Note:** {extracted['extraction_notes']}")