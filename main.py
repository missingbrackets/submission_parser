# ============================================================
#  Submission Analyser
#  Streamlit App  |  main.py
#
#  Run with:  streamlit run main.py
# ============================================================

import os
import json
import streamlit as st
from pathlib import Path

from skills import get_skill, available_classes
from skills.base import FieldSection, FieldType, FieldSource
from file_parser import extract_folder, extract_file
from claude_caller import (
    call_claude_extraction,
    run_gap_analysis,
    build_csv_row,
    save_csv,
    build_claims_csv_rows,
    save_claims_csv,
    build_locations_csv_rows,
    save_locations_csv,
    build_triage_row,
    save_triage_csv,
    build_triage_locations_rows,
    save_triage_locations_csv,
    build_direct_triage_row,
    save_direct_triage_csv,
    build_summary_text,
    save_summary_report,
)

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="Submission Analyser",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

def render_results(extracted, gap, all_files, folder_path, folder_name, skill, output_folder=None):
    """Render gap analysis, data tabs, and save section for one submission.
    output_folder: where outputs are saved (defaults to folder_path).
    In batch mode, pass the parent folder to consolidate CSVs."""
    import pandas as pd
    if output_folder is None:
        output_folder = folder_path

    st.markdown("### 3 · Gap Analysis")

    gap = run_gap_analysis(extracted, skill["required_fields"])

    score       = gap["data_quality_score"]
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

    # Build active tab list from sidebar checkbox state
    _tab_states   = st.session_state.get("tab_states", {})
    _tab_configs  = skill["skill_class"].tab_config()
    _active_tabs  = [tc for tc in _tab_configs if _tab_states.get(tc.section.name, tc.default_on)]
    _fields_by_key = skill["skill_class"].fields_by_key()

    # Build tab labels — active skill tabs + fixed tabs
    _tab_labels = [f"{tc.icon} {tc.section.value}" for tc in _active_tabs]
    _tab_labels += ["📋 Summary", "📊 Claims CSV", "🔍 Raw JSON"]

    _tabs = st.tabs(_tab_labels)
    _summary_tab_idx = len(_active_tabs)
    _claims_tab_idx  = len(_active_tabs) + 1
    _json_tab_idx    = len(_active_tabs) + 2

    # ── Render each active skill tab dynamically ──────────────
    import pandas as pd

    for _i, _tc in enumerate(_active_tabs):
        with _tabs[_i]:
            _section_fields = [
                f for f in skill["output_schema"]
                if f.section == _tc.section and f.in_summary
            ]

            # ── LOCATIONS section gets SOV table renderer
            if _tc.section == FieldSection.LOCATIONS:
                import pandas as pd
                # Summary metrics
                _lm1, _lm2, _lm3, _lm4 = st.columns(4)
                _lm1.metric("Locations",      extracted.get("location_count", "—"))
                _lm2.metric("Total TIV",      f"{extracted.get('tiv_total','—')} {extracted.get('tiv_currency','')}")
                _lm3.metric("Largest Loc TIV",extracted.get("largest_location_tiv", "—"))
                _lm4.metric("SOV Provided",   extracted.get("sov_provided", "—"))

                # SOV table
                sov_locs = [l for l in (extracted.get("sov_locations") or []) if isinstance(l, dict)]
                if sov_locs:
                    _sov_rows = []
                    for _loc in sov_locs:
                        _sov_rows.append({
                            "Location":     _loc.get("location_name") or _loc.get("name") or "",
                            "City":         _loc.get("city") or "",
                            "Country":      _loc.get("country") or "",
                            "Occupancy":    _loc.get("occupancy") or _loc.get("use") or "",
                            "Construction": _loc.get("construction") or "",
                            "TIV":          _loc.get("tiv") or _loc.get("tiv_total") or "",
                            "TIV PD":       _loc.get("tiv_pd") or "",
                            "TIV BI":       _loc.get("tiv_bi") or "",
                            "TIV Stock":    _loc.get("tiv_stock") or "",
                            "Lat":          _loc.get("latitude") or _loc.get("lat") or "",
                            "Long":         _loc.get("longitude") or _loc.get("lon") or "",
                            "Fire Prot.":   _loc.get("fire_protection") or "",
                            "Security":     _loc.get("security_protection") or "",
                            "Notes":        _loc.get("notes") or "",
                        })
                    _df_sov = pd.DataFrame(_sov_rows)
                    # Drop fully empty columns to keep table clean
                    _df_sov = _df_sov.loc[:, (_df_sov != "").any(axis=0)]
                    st.dataframe(_df_sov, use_container_width=True, hide_index=True)
                    st.caption(f"{len(sov_locs)} location(s) extracted. "
                               "Lat/Long populated where broker provided — otherwise blank for manual entry.")
                else:
                    st.warning("No per-location SOV data extracted — only aggregate TIV available.")
                    st.caption("Request full Schedule of Values from broker for per-location pricing.")

                # Accumulation comment
                if extracted.get("accumulation_comment"):
                    st.info(f"**Accumulation / Concentration:** {extracted['accumulation_comment']}")
                if extracted.get("highest_risk_country"):
                    st.warning(f"**Highest Risk Country:** {extracted['highest_risk_country']}")

                # Show remaining scalar fields from schema (auto-rendered)
                _scalar_loc_fields = [
                    f for f in _section_fields
                    if f.field_type not in (FieldType.ARRAY,)
                    and f.key not in ("tiv_total","tiv_currency","tiv_pd","tiv_bi","tiv_stock",
                                      "location_count","sov_provided","largest_location_tiv",
                                      "largest_location_name","accumulation_comment","highest_risk_country")
                ]
                if _scalar_loc_fields:
                    with st.expander("All location fields"):
                        _c1, _c2 = st.columns(2)
                        _mid = (len(_scalar_loc_fields) + 1) // 2
                        for _ci, (_col, _col_fields) in enumerate([(_c1, _scalar_loc_fields[:_mid]), (_c2, _scalar_loc_fields[_mid:])]):
                            with _col:
                                for _f in _col_fields:
                                    _val = extracted.get(_f.key)
                                    _display = str(_val).strip() if _val is not None else None
                                    _missing = not _display or _display.lower() in ("null","none","unknown","false","")
                                    _col.markdown(
                                        f'<div class="field-row"><span class="field-label">{_f.label}</span>'
                                        f'<span class="{"field-missing" if _missing else "field-value"}">{_display if not _missing else "— not found"}</span></div>',
                                        unsafe_allow_html=True)

            # ── RATER section gets clean input card layout
            elif _tc.section == FieldSection.RATER:
                _rater_fields = [f for f in _section_fields]
                _populated    = [(f, extracted.get(f.key)) for f in _rater_fields if extracted.get(f.key)]
                _missing_r    = [f for f in _rater_fields if not extracted.get(f.key)]

                if _populated:
                    st.markdown("**Structured Rater Inputs**")
                    st.caption("These fields are ready to copy into your pricing model.")
                    _rc1, _rc2 = st.columns(2)
                    _mid = (len(_populated) + 1) // 2
                    for _ci, (_col, _items) in enumerate([(_rc1, _populated[:_mid]), (_rc2, _populated[_mid:])]):
                        with _col:
                            for _f, _val in _items:
                                _col.markdown(
                                    f'<div class="field-row">'
                                    f'<span class="field-label">{_f.label}</span>'
                                    f'<span class="field-value" style="color:#00C2FF;">{_val}</span>'
                                    f'</div>',
                                    unsafe_allow_html=True)
                    if _missing_r:
                        with st.expander(f"{len(_missing_r)} rater field(s) not populated"):
                            for _f in _missing_r:
                                st.caption(f"— {_f.label}: {_f.description or 'not extracted'}")
                else:
                    st.warning("No rater inputs populated — check extraction quality.")

            # ── LOSS HISTORY section gets custom table renderer
            elif _tc.section == FieldSection.LOSS:
                loss_hist = extracted.get("loss_history", [])
                if loss_hist:
                    _loss_rows = []
                    for yr in loss_hist:
                        if not isinstance(yr, dict):
                            continue
                        _loss_rows.append({
                            "Year":           yr.get("year", ""),
                            "Premium":        yr.get("premium", ""),
                            "Paid":           yr.get("losses_paid", ""),
                            "Outstanding":    yr.get("losses_outstanding", ""),
                            "Incurred":       yr.get("losses_total_incurred", ""),
                            "Claims":         yr.get("claims_count", ""),
                            "Impl. LR %":     yr.get("implied_loss_ratio_pct", ""),
                            "Large Loss":     "⚠️" if yr.get("large_loss_flag") else "",
                            "Dev. Warning":   yr.get("development_warning", "") or "",
                        })
                    st.dataframe(pd.DataFrame(_loss_rows), use_container_width=True, hide_index=True)

                    # Summary metrics row
                    _m1, _m2, _m3, _m4 = st.columns(4)
                    _m1.metric("Years Provided",   extracted.get("loss_history_years_provided", "—"))
                    _m2.metric("Avg LR (all)",      extracted.get("avg_loss_ratio_all_years_pct", "—"))
                    _m3.metric("Avg LR (ex large)", extracted.get("avg_loss_ratio_ex_large_pct", "—"))
                    _m4.metric("Trend",             extracted.get("loss_trend_direction", "—"))

                    large = extracted.get("large_losses", [])
                    if large:
                        st.markdown("**Large Losses Detail**")
                        for ll in large:
                            if not isinstance(ll, dict):
                                continue
                            _sev = ll.get("reserved_adequacy_comment", "")
                            st.markdown(
                                f'<div style="background:#1A0A0A; border-left:3px solid #EF4444; '
                                f'padding:8px 12px; margin:4px 0; border-radius:3px; font-size:0.8rem; color:#E2E8F0;">'
                                f'<b>{ll.get("year","?")}</b> &nbsp;|&nbsp; {ll.get("amount","?")} '
                                f'&nbsp;|&nbsp; {ll.get("status","?")} &nbsp;|&nbsp; {ll.get("description","")}'
                                + (f'<br><span style="color:#94A3B8; font-size:0.75rem;">Reserve note: {_sev}</span>' if _sev else "")
                                + "</div>",
                                unsafe_allow_html=True
                            )
                    else:
                        st.caption("No individual large losses identified.")

                    if extracted.get("ibnr_commentary"):
                        st.info(f"**IBNR / Development:** {extracted['ibnr_commentary']}")
                else:
                    st.warning("No loss history extracted from submission materials.")

            # ── ANALYTICS section gets the UW flags renderer
            elif _tc.section == FieldSection.ANALYTICS:
                uw_flags  = [f for f in (extracted.get("uw_analyst_flags") or []) if isinstance(f, dict)]
                conflicts = [c for c in (extracted.get("data_conflicts") or []) if isinstance(c, dict)]
                questions = [q for q in (extracted.get("questions_for_broker") or []) if q and str(q).strip()]

                red_flags   = [f for f in uw_flags if str(f.get("severity","")).upper() == "RED"]
                amber_flags = [f for f in uw_flags if str(f.get("severity","")).upper() == "AMBER"]
                info_flags  = [f for f in uw_flags if str(f.get("severity","")).upper() == "INFO"]

                _fc1, _fc2, _fc3, _fc4 = st.columns(4)
                _fc1.metric("🔴 RED",    len(red_flags))
                _fc2.metric("🟡 AMBER",  len(amber_flags))
                _fc3.metric("ℹ️ INFO",   len(info_flags))
                _fc4.metric("❓ Questions", len([q for q in questions if q and str(q).strip()]))

                if uw_flags:
                    st.markdown("**Underwriter Analyst Flags**")
                    _sev_order = {"RED": 0, "AMBER": 1, "INFO": 2}
                    for _flag in sorted(uw_flags, key=lambda x: _sev_order.get(str(x.get("severity","INFO")).upper(), 2)):
                        _sev   = str(_flag.get("severity","INFO")).upper()
                        _cat   = _flag.get("category","")
                        _title = _flag.get("flag","")
                        _det   = _flag.get("detail","")
                        _color = "#EF4444" if _sev=="RED" else "#F59E0B" if _sev=="AMBER" else "#6B7B99"
                        _bg    = "#2A1215" if _sev=="RED" else "#2A1F0A" if _sev=="AMBER" else "#111827"
                        st.markdown(
                            f'<div style="background:{_bg}; border-left:3px solid {_color}; padding:10px 14px; margin:6px 0; border-radius:3px;">'
                            f'<div style="font-size:0.7rem; color:{_color}; font-weight:700; letter-spacing:0.08em;">{_sev} &nbsp;·&nbsp; {_cat.upper()}</div>'
                            f'<div style="font-size:0.85rem; color:#E2E8F0; font-weight:600; margin:3px 0;">{_title}</div>'
                            f'<div style="font-size:0.78rem; color:#94A3B8; line-height:1.5;">{_det}</div>'
                            f'</div>', unsafe_allow_html=True)
                else:
                    st.success("No underwriter flags raised.")

                _valid_conflicts = [c for c in conflicts if c.get("field") and c.get("value_a")]
                if _valid_conflicts:
                    st.markdown("")
                    st.markdown("**Data Conflicts**")
                    for c in _valid_conflicts:
                        st.markdown(
                            f'<div style="background:#1A1A2E; border-left:3px solid #8B5CF6; padding:10px 14px; margin:6px 0; border-radius:3px;">'
                            f'<div style="font-size:0.7rem; color:#8B5CF6; font-weight:700;">CONFLICT · {c.get("field","").upper()}</div>'
                            f'<div style="font-size:0.8rem; color:#E2E8F0; margin:3px 0;">'
                            f'<b>A:</b> {c.get("value_a","")} <span style="color:#6B7B99">({c.get("source_a","")})</span><br>'
                            f'<b>B:</b> {c.get("value_b","")} <span style="color:#6B7B99">({c.get("source_b","")})</span></div>'
                            f'<div style="font-size:0.78rem; color:#94A3B8;">Resolution: {c.get("resolution","Manual review required")}</div>'
                            f'</div>', unsafe_allow_html=True)

                _valid_qs = [q for q in questions if q and str(q).strip()]
                if _valid_qs:
                    st.markdown("")
                    st.markdown("**Questions for Broker**")
                    for _qi, _q in enumerate(_valid_qs, 1):
                        st.markdown(
                            f'<div style="background:#111827; border:1px solid #1E2D45; padding:8px 14px; margin:4px 0; border-radius:3px; font-size:0.82rem; color:#E2E8F0;">{_qi}. {_q}</div>',
                            unsafe_allow_html=True)

            # ── COVERAGE section gets Y/N icon renderer
            elif _tc.section == FieldSection.COVERAGE:
                _yesno_fields = [f for f in _section_fields if f.field_type == FieldType.YESNO]
                _other_fields = [f for f in _section_fields if f.field_type != FieldType.YESNO]
                for _f in _yesno_fields:
                    _val  = extracted.get(_f.key, "Unknown")
                    _icon = "✅" if _val == "Y" else "❌" if _val == "N" else "❓"
                    _desc = f" — {_f.description}" if _f.description else ""
                    st.markdown(f"{_icon} **{_f.label}** — {_val}{_desc}")
                for _f in _other_fields:
                    _val = extracted.get(_f.key)
                    if _val:
                        st.markdown(f"• **{_f.label}:** {_val}")

                _features = extracted.get("notable_features", [])
                if _features:
                    st.markdown("")
                    st.markdown("**Notable Features / Endorsements**")
                    for _feat in _features:
                        st.markdown(f"• {_feat}")

            # ── FLAGS section gets colour-coded alerts
            elif _tc.section == FieldSection.FLAGS:
                _c1, _c2 = st.columns(2)
                _left  = [f for f in _section_fields if _section_fields.index(f) % 2 == 0]
                _right = [f for f in _section_fields if _section_fields.index(f) % 2 == 1]
                for _col, _col_fields in [(_c1, _left), (_c2, _right)]:
                    with _col:
                        for _f in _col_fields:
                            _val = extracted.get(_f.key)
                            _display = str(_val).strip() if _val is not None else None
                            if not _display or _display.lower() in ("null","none","unknown","false",""):
                                _col.markdown(
                                    f'<div class="field-row"><span class="field-label">{_f.label}</span>'
                                    f'<span class="field-value" style="color:#6B7B99;">— not disclosed</span></div>',
                                    unsafe_allow_html=True)
                            else:
                                _is_warn = _f.critical and _display.lower() not in ("no","n","none")
                                _col.markdown(
                                    f'<div class="field-row"><span class="field-label">{_f.label}</span>'
                                    f'<span class="field-value" style="color:{"#EF4444" if _is_warn else "#E2E8F0"};">{_display}</span></div>',
                                    unsafe_allow_html=True)

            # ── DEFAULT: render all fields as key-value pairs in two columns
            else:
                _c1, _c2 = st.columns(2)
                _mid = (len(_section_fields) + 1) // 2
                for _ci, (_col, _col_fields) in enumerate([(_c1, _section_fields[:_mid]), (_c2, _section_fields[_mid:])]):
                    with _col:
                        for _f in _col_fields:
                            _val = extracted.get(_f.key)
                            _display = str(_val).strip() if _val is not None else None
                            _missing = not _display or _display.lower() in ("null","none","unknown","false","")
                            _col.markdown(
                                f'<div class="field-row">'
                                f'<span class="field-label">{_f.label}</span>'
                                f'<span class="{"field-missing" if _missing else "field-value"}">{_display if not _missing else "— not found"}</span>'
                                f'</div>',
                                unsafe_allow_html=True)

    # ── Summary tab ──────────────────────────────────────────
    with _tabs[_summary_tab_idx]:
        _summary_text = build_summary_text(
            extracted=extracted,
            gap_analysis=gap,
            source_files=all_files,
            class_label=skill["label"],
            folder_name=folder_name,
        )

        # Render plain-text report as styled markdown
        def _render_summary_as_markdown(text: str):
            for raw_line in text.splitlines():
                line = raw_line.strip()
                # Section divider (===)
                if line.startswith("==="):
                    st.markdown("---")
                # Section divider (---)
                elif line.startswith("---"):
                    pass  # already separated by headers
                # Main title
                elif line == "PRICING — AI SUBMISSION SUMMARY":
                    st.markdown(f"## 🏢 {line}")
                # Section headers (ALL CAPS lines)
                elif line and line.isupper() and len(line) > 3 and not line.startswith("  "):
                    st.markdown(f"### {line.title()}")
                # Source file lines
                elif line.startswith("[OK]") or line.startswith("[!!]"):
                    icon = "✅" if line.startswith("[OK]") else "⚠️"
                    st.markdown(
                        f'<div style="font-size:0.82rem; color:#94A3B8; padding:2px 0;">'
                        f'{icon} {line[4:].strip()}</div>',
                        unsafe_allow_html=True)
                # Key-value lines (two or more spaces between label and value)
                elif "  " in line and not line.startswith("•") and not line.startswith("-"):
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        label, val = parts[0], parts[1].strip()
                        val_color = "#94A3B8" if val in ("NOT PROVIDED", "") else "#E2E8F0"
                        st.markdown(
                            f'<div class="field-row">'
                            f'<span class="field-label">{label}</span>'
                            f'<span class="field-value" style="color:{val_color};">{val}</span>'
                            f'</div>',
                            unsafe_allow_html=True)
                    else:
                        if line:
                            st.markdown(f'<div style="font-size:0.83rem; color:#CBD5E1; padding:2px 0;">{line}</div>', unsafe_allow_html=True)
                # Bullet / flag lines
                elif line.startswith("•") or line.startswith("-") or line.startswith("["):
                    color = "#EF4444" if "[RED]" in line else "#F59E0B" if "[AMBER]" in line else "#94A3B8"
                    st.markdown(
                        f'<div style="font-size:0.82rem; color:{color}; padding:2px 0 2px 8px;">{line}</div>',
                        unsafe_allow_html=True)
                # Metadata lines (Class:, Case Folder: etc.)
                elif ":" in line and line.split(":")[0].strip() in ("Class", "Case Folder", "Generated", "Data Quality"):
                    k, v = line.split(":", 1)
                    st.markdown(
                        f'<div style="font-size:0.82rem; color:#64748B; padding:1px 0;">'
                        f'<span style="color:#475569;">{k}:</span> {v.strip()}</div>',
                        unsafe_allow_html=True)
                # Any other non-empty line
                elif line:
                    st.markdown(
                        f'<div style="font-size:0.83rem; color:#CBD5E1; padding:2px 0;">{line}</div>',
                        unsafe_allow_html=True)

        _render_summary_as_markdown(_summary_text)
        st.caption("Preview only — use **Save** below to write to file.")

    # ── Claims CSV tab ────────────────────────────────────────
    with _tabs[_claims_tab_idx]:
        claims_rows = build_claims_csv_rows(extracted, skill.get("claims_csv_schema", []))
        if claims_rows:
            df_claims = pd.DataFrame(claims_rows)
            st.caption(f"{len(claims_rows)} row(s) ready. Segment_1, Segment_2 and Manual Claim Adjustments left blank for you.")
            st.dataframe(df_claims, use_container_width=True, hide_index=True)
        else:
            st.warning("No loss history found to build claims rows.")

    # ── Raw JSON tab ──────────────────────────────────────────
    with _tabs[_json_tab_idx]:
        st.code(json.dumps(extracted, indent=2), language="json")
        st.caption(f"Extraction confidence: {extracted.get('extraction_confidence','Not stated')}")
        if extracted.get("extraction_notes"):
            st.info(extracted["extraction_notes"])
        st.markdown("---")
        st.caption("**Skill schema:**")
        st.code(skill["skill_class"].schema_doc(), language="text")


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
                summary_path = save_summary_report(
                    extracted=extracted,
                    gap_analysis=gap,
                    source_files=all_files,
                    class_label=skill["label"],
                    output_folder=output_folder,
                    folder_name=folder_name,
                )
                csv_path = save_csv(
                    row=csv_row,
                    csv_schema=skill["csv_schema"],
                    output_folder=output_folder,
                    filename_prefix="submission_data",
                )
                claims_path = ""
                if claims_rows and skill.get("claims_csv_schema"):
                    claims_path = save_claims_csv(
                        rows=claims_rows,
                        claims_csv_schema=skill["claims_csv_schema"],
                        output_folder=output_folder,
                    )
                # Save locations CSV if skill has SOV data (terror/PV)
                locs_path = ""
                if extracted.get("sov_locations") is not None or extracted.get("tiv_total"):
                    try:
                        _loc_rows, _loc_schema = build_locations_csv_rows(extracted)
                        if _loc_rows:
                            locs_path = save_locations_csv(
                                rows=_loc_rows,
                                schema=_loc_schema,
                                output_folder=output_folder,
                            )
                    except Exception:
                        pass  # best-effort

                # Triage skills: save specialised triage CSVs
                triage_path = ""
                triage_locs_path = ""
                direct_triage_path = ""
                if skill.get("code") == "PVQ":
                    try:
                        _tr = build_triage_row(extracted, gap, output_folder, skill["label"])
                        triage_path = save_triage_csv(_tr, output_folder)
                        _tl_rows, _tl_schema = build_triage_locations_rows(extracted)
                        if _tl_rows:
                            triage_locs_path = save_triage_locations_csv(_tl_rows, _tl_schema, output_folder)
                    except Exception as e:
                        st.warning(f"Triage CSV save error: {e}")
                elif skill.get("code") == "PVDT":
                    try:
                        _dtr = build_direct_triage_row(extracted, gap, output_folder, skill["label"])
                        direct_triage_path = save_direct_triage_csv(_dtr, output_folder)
                    except Exception as e:
                        st.warning(f"Direct triage CSV save error: {e}")

                st.success(f"✅ Summary saved:\n`{summary_path}`")
                st.success(f"✅ Submission CSV saved:\n`{csv_path}`")
                if claims_path:
                    st.success(f"✅ Claims CSV saved:\n`{claims_path}`")
                if locs_path:
                    st.success(f"✅ Locations CSV saved:\n`{locs_path}`")
                if triage_path:
                    st.success(f"✅ Triage matrix saved:\n`{triage_path}`")
                if triage_locs_path:
                    st.success(f"✅ Triage locations saved:\n`{triage_locs_path}`")
                if direct_triage_path:
                    st.success(f"✅ Direct triage matrix saved:\n`{direct_triage_path}`")
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


# ─────────────────────────────────────────────────────────────────────
# SINGLE MODE RUNNER
# ─────────────────────────────────────────────────────────────────────

def run_single(folder_path, class_choice, api_key, use_corr, use_data, force_rerun):
    skill       = get_skill(class_choice)
    folder_name = os.path.basename(folder_path.rstrip("\\/"))

    st.markdown("### 1 · Reading Submission Files")
    all_files = {}
    if use_corr:
        all_files.update(extract_folder(folder_path, "01_correspondence"))
    if use_data:
        data_files = extract_folder(folder_path, "02_data")
        data_files = {k: v for k, v in data_files.items()
                      if not k.endswith("AI_Summary.txt") and not k.endswith(".csv")}
        all_files.update(data_files)

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
        extracted   = st.session_state["extracted"]
        all_files   = st.session_state["all_files"]
        skill       = st.session_state["skill"]
        st.success("Using cached extraction — change folder or skill to re-extract.")
    else:
        with st.spinner(f"Sending to Claude ({skill['label']} skill)..."):
            try:
                extracted, _ = call_claude_extraction(combined_text, skill["system_prompt"], api_key)
                st.session_state["extracted"]  = extracted
                st.session_state["all_files"]  = all_files
                st.session_state["folder_path"]= folder_path
                st.session_state["folder_name"]= folder_name
                st.session_state["skill"]      = skill
                st.session_state["_cache_key"] = _cache_key
                st.success("Extraction complete")
            except Exception as e:
                st.error(f"Claude API error: {str(e)}")
                return

    gap = run_gap_analysis(extracted, skill["required_fields"])
    render_results(extracted, gap, all_files, folder_path, folder_name, skill)


# ─────────────────────────────────────────────────────────────────────
# BATCH MODE RUNNER
# ─────────────────────────────────────────────────────────────────────

def run_batch(parent_folder, class_choice, api_key, use_corr, use_data, force_rerun):
    """
    Discover all immediate subfolders of parent_folder,
    process each as a submission, save CSVs to parent/submission_tool_auto_outputs,
    store results in session_state for navigation.
    """
    # Discover subfolders (immediate children only, ignore hidden and output folder)
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

    # ── Progress run ─────────────────────────────────────────
    batch_results = st.session_state.get("batch_results", {})
    _cache_key_batch = f"BATCH|{parent_folder}|{class_choice}"
    already_run = (not force_rerun
                   and st.session_state.get("_cache_key_batch") == _cache_key_batch
                   and batch_results)

    if already_run:
        st.success(f"Using cached batch results ({len(batch_results)} submissions). Change folder or skill to re-run.")
    else:
        batch_results = {}
        progress_bar = st.progress(0, text="Starting batch...")
        status_area  = st.empty()

        for idx, subfolder_name in enumerate(subfolders):
            subfolder_path = os.path.join(parent_folder, subfolder_name)
            progress_pct   = int((idx / len(subfolders)) * 100)
            progress_bar.progress(progress_pct, text=f"Processing {subfolder_name} ({idx+1}/{len(subfolders)})...")
            status_area.info(f"🔄 **{subfolder_name}** — reading files...")

            # Read files
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

            # Claude extraction
            status_area.info(f"🤖 **{subfolder_name}** — sending to Claude...")
            try:
                extracted, _ = call_claude_extraction(combined_text, skill["system_prompt"], api_key)
            except Exception as e:
                status_area.error(f"❌ {subfolder_name} — Claude error: {e}")
                batch_results[subfolder_name] = {"error": str(e), "folder_path": subfolder_path}
                continue

            gap = run_gap_analysis(extracted, skill["required_fields"])

            # Auto-save CSVs to parent folder (consolidated)
            status_area.info(f"💾 **{subfolder_name}** — saving outputs...")
            try:
                save_summary_report(extracted, gap, all_files, skill["label"], subfolder_path, subfolder_name)
                csv_row = build_csv_row(extracted, gap, skill["csv_schema"], subfolder_path, skill["label"])
                # Per-submission: save to subfolder/submission_tool_auto_outputs/
                save_csv(csv_row, skill["csv_schema"], subfolder_path, "submission_data")
                claims_rows = build_claims_csv_rows(extracted, skill.get("claims_csv_schema", []))
                if claims_rows:
                    save_claims_csv(claims_rows, skill["claims_csv_schema"], subfolder_path)
                if extracted.get("sov_locations") is not None or extracted.get("tiv_total"):
                    loc_rows, loc_schema = build_locations_csv_rows(extracted)
                    if loc_rows:
                        save_locations_csv(loc_rows, loc_schema, subfolder_path)
                # Consolidated roll-up: append to parent/submission_tool_auto_outputs/
                save_csv(csv_row, skill["csv_schema"], parent_folder, "submission_data_all")
                if claims_rows:
                    save_claims_csv(claims_rows, skill["claims_csv_schema"], parent_folder)
                # Triage skills: append to triage CSVs at parent folder
                if skill.get("code") == "PVQ":
                    try:
                        _tr = build_triage_row(extracted, gap, subfolder_path, skill["label"])
                        save_triage_csv(_tr, parent_folder)
                        _tl_rows, _tl_schema = build_triage_locations_rows(extracted)
                        if _tl_rows:
                            save_triage_locations_csv(_tl_rows, _tl_schema, parent_folder)
                    except Exception:
                        pass  # best-effort
                elif skill.get("code") == "PVDT":
                    try:
                        _dtr = build_direct_triage_row(extracted, gap, subfolder_path, skill["label"])
                        save_direct_triage_csv(_dtr, parent_folder)
                    except Exception:
                        pass  # best-effort
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

        st.session_state["batch_results"]     = batch_results
        st.session_state["_cache_key_batch"]  = _cache_key_batch

    # ── Results summary table ────────────────────────────────
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
    import pandas as pd
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    # ── Per-submission viewer ────────────────────────────────
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




def _main_page():

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
      <h1>SUBMISSION ANALYSER</h1>
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

        # ── TAB SELECTOR ─────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📑 Display Tabs")
        st.caption("Choose which tabs to show after analysis.")

        _skill_preview = get_skill(class_choice)
        _tab_configs   = _skill_preview["skill_class"].tab_config()

        # Always-present tabs (not toggleable)
        _fixed_tabs = ["📊 Claims CSV", "🔍 Raw JSON"]

        # Build checkbox state — stored in session so they persist across reruns
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

    # ─────────────────────────────────────────────────────────────────────
    # RENDER RESULTS  — shared by single + batch mode
    # ─────────────────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────────────────
    # MAIN DISPATCH
    # ─────────────────────────────────────────────────────────────────────

    if run_button:
        # Validate inputs
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
            run_batch(folder_path, class_choice, api_key, use_corr, use_data, _force)
        else:
            run_single(folder_path, class_choice, api_key, use_corr, use_data, _force)

# ── NAVIGATION ───────────────────────────────────────────────
pg = st.navigation([
    st.Page(_main_page, title="Submission Analyser", icon="📋"),
    st.Page("pages/1_Skill_Editor.py", title="Skill Editor", icon="⚙️"),
])
pg.run()
