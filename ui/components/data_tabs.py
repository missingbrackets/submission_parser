# ============================================================
#  ui/components/data_tabs.py
#  Streamlit rendering of extracted data tabs and save section.
# ============================================================

import json
import streamlit as st

from skills.base import FieldSection, FieldType
from core.outputs import build_claims_csv_rows, build_csv_row
from core.report import build_summary_text
from ui.components.geo_viz import render_geo_viz_tab


def render_data_tabs(
    extracted: dict,
    gap: dict,
    all_files: dict,
    folder_name: str,
    skill: dict,
) -> None:
    """Render the '4 · Extracted Data' section with dynamic tabs."""
    import pandas as pd

    st.markdown("### 4 · Extracted Data")

    _tab_states   = st.session_state.get("tab_states", {})
    _tab_configs  = skill["skill_class"].tab_config()
    _active_tabs  = [tc for tc in _tab_configs if _tab_states.get(tc.section.name, tc.default_on)]

    _tab_labels = [f"{tc.icon} {tc.section.value}" for tc in _active_tabs]
    _tab_labels += ["📋 Summary", "📊 Claims CSV", "🔍 Raw JSON"]

    _tabs = st.tabs(_tab_labels)
    _summary_tab_idx = len(_active_tabs)
    _claims_tab_idx  = len(_active_tabs) + 1
    _json_tab_idx    = len(_active_tabs) + 2

    for _i, _tc in enumerate(_active_tabs):
        with _tabs[_i]:
            _section_fields = [
                f for f in skill["output_schema"]
                if f.section == _tc.section and f.in_summary
            ]

            if _tc.section == FieldSection.LOCATIONS:
                _render_locations_tab(extracted, _section_fields)

            elif _tc.section == FieldSection.RATER:
                _render_rater_tab(extracted, _section_fields)

            elif _tc.section == FieldSection.LOSS:
                _render_loss_tab(extracted, pd)

            elif _tc.section == FieldSection.ANALYTICS:
                _render_analytics_tab(extracted)

            elif _tc.section == FieldSection.COVERAGE:
                _render_coverage_tab(extracted, _section_fields)

            elif _tc.section == FieldSection.FLAGS:
                _render_flags_tab(extracted, _section_fields)

            elif _tc.section == FieldSection.GEO_VIZ:
                render_geo_viz_tab(extracted)

            else:
                _render_default_tab(extracted, _section_fields)

    # ── Summary tab ──────────────────────────────────────────
    with _tabs[_summary_tab_idx]:
        _summary_text = build_summary_text(
            extracted=extracted,
            gap_analysis=gap,
            source_files=all_files,
            class_label=skill["label"],
            folder_name=folder_name,
        )
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


def render_save_section(
    extracted: dict,
    gap: dict,
    all_files: dict,
    folder_path: str,
    folder_name: str,
    skill: dict,
    output_folder: str,
) -> None:
    """Render the '5 · Save Outputs' section."""
    from core.outputs import (
        save_csv, build_claims_csv_rows, save_claims_csv,
        build_locations_csv_rows, save_locations_csv,
        build_triage_row, save_triage_csv,
        build_triage_locations_rows, save_triage_locations_csv,
        build_direct_triage_row, save_direct_triage_csv,
    )
    from core.report import save_summary_report

    st.markdown("### 5 · Save Outputs")

    claims_rows = build_claims_csv_rows(extracted, skill.get("claims_csv_schema", []))
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
                locs_path = ""
                if extracted.get("sov_locations") is not None or extracted.get("tiv_total"):
                    try:
                        _loc_rows, _loc_schema = build_locations_csv_rows(extracted)
                        if _loc_rows:
                            locs_path = save_locations_csv(
                                rows=_loc_rows, schema=_loc_schema, output_folder=output_folder
                            )
                    except Exception:
                        pass

                triage_path = triage_locs_path = direct_triage_path = ""
                skill_code = skill.get("code", "")
                if skill_code == "PVQ":
                    try:
                        _tr = build_triage_row(extracted, gap, output_folder, skill["label"])
                        triage_path = save_triage_csv(_tr, output_folder)
                        _tl_rows, _tl_schema = build_triage_locations_rows(extracted)
                        if _tl_rows:
                            triage_locs_path = save_triage_locations_csv(_tl_rows, _tl_schema, output_folder)
                    except Exception as e:
                        st.warning(f"Triage CSV save error: {e}")
                elif skill_code == "PVDT":
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
        with st.expander("Preview CSV row"):
            preview_items = [(k, v) for k, v in csv_row.items() if v]
            for k, v in preview_items:
                st.markdown(f'<div class="field-row"><span class="field-label">{k}</span>'
                            f'<span class="field-value">{v}</span></div>',
                            unsafe_allow_html=True)

    if extracted.get("extraction_notes"):
        st.markdown("---")
        st.info(f"**Extraction Note:** {extracted['extraction_notes']}")


# ── Private section renderers ─────────────────────────────────

def _render_locations_tab(extracted, section_fields):
    import pandas as pd
    _lm1, _lm2, _lm3, _lm4 = st.columns(4)
    _lm1.metric("Locations",      extracted.get("location_count", "—"))
    _lm2.metric("Total TIV",      f"{extracted.get('tiv_total','—')} {extracted.get('tiv_currency','')}")
    _lm3.metric("Largest Loc TIV",extracted.get("largest_location_tiv", "—"))
    _lm4.metric("SOV Provided",   extracted.get("sov_provided", "—"))

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
        _df_sov = _df_sov.loc[:, (_df_sov != "").any(axis=0)]
        st.dataframe(_df_sov, use_container_width=True, hide_index=True)
        st.caption(f"{len(sov_locs)} location(s) extracted.")
    else:
        st.warning("No per-location SOV data extracted — only aggregate TIV available.")
        st.caption("Request full Schedule of Values from broker for per-location pricing.")

    if extracted.get("accumulation_comment"):
        st.info(f"**Accumulation / Concentration:** {extracted['accumulation_comment']}")
    if extracted.get("highest_risk_country"):
        st.warning(f"**Highest Risk Country:** {extracted['highest_risk_country']}")

    _scalar_loc_fields = [
        f for f in section_fields
        if f.field_type not in (FieldType.ARRAY,)
        and f.key not in ("tiv_total","tiv_currency","tiv_pd","tiv_bi","tiv_stock",
                          "location_count","sov_provided","largest_location_tiv",
                          "largest_location_name","accumulation_comment","highest_risk_country")
    ]
    if _scalar_loc_fields:
        with st.expander("All location fields"):
            _c1, _c2 = st.columns(2)
            _mid = (len(_scalar_loc_fields) + 1) // 2
            for _col, _col_fields in [(_c1, _scalar_loc_fields[:_mid]), (_c2, _scalar_loc_fields[_mid:])]:
                with _col:
                    for _f in _col_fields:
                        _val = extracted.get(_f.key)
                        _display = str(_val).strip() if _val is not None else None
                        _missing = not _display or _display.lower() in ("null","none","unknown","false","")
                        _col.markdown(
                            f'<div class="field-row"><span class="field-label">{_f.label}</span>'
                            f'<span class="{"field-missing" if _missing else "field-value"}">'
                            f'{_display if not _missing else "— not found"}</span></div>',
                            unsafe_allow_html=True)


def _render_rater_tab(extracted, section_fields):
    _populated = [(f, extracted.get(f.key)) for f in section_fields if extracted.get(f.key)]
    _missing_r = [f for f in section_fields if not extracted.get(f.key)]

    if _populated:
        st.markdown("**Structured Rater Inputs**")
        st.caption("These fields are ready to copy into your pricing model.")
        _rc1, _rc2 = st.columns(2)
        _mid = (len(_populated) + 1) // 2
        for _col, _items in [(_rc1, _populated[:_mid]), (_rc2, _populated[_mid:])]:
            with _col:
                for _f, _val in _items:
                    _col.markdown(
                        f'<div class="field-row">'
                        f'<span class="field-label">{_f.label}</span>'
                        f'<span class="field-value" style="color:#00C2FF;">{_val}</span>'
                        f'</div>', unsafe_allow_html=True)
        if _missing_r:
            with st.expander(f"{len(_missing_r)} rater field(s) not populated"):
                for _f in _missing_r:
                    st.caption(f"— {_f.label}: {_f.description or 'not extracted'}")
    else:
        st.warning("No rater inputs populated — check extraction quality.")


def _render_loss_tab(extracted, pd):
    loss_hist = extracted.get("loss_history", [])
    if loss_hist:
        _loss_rows = []
        for yr in loss_hist:
            if not isinstance(yr, dict):
                continue
            _loss_rows.append({
                "Year":         yr.get("year", ""),
                "Premium":      yr.get("premium", ""),
                "Paid":         yr.get("losses_paid", ""),
                "Outstanding":  yr.get("losses_outstanding", ""),
                "Incurred":     yr.get("losses_total_incurred", ""),
                "Claims":       yr.get("claims_count", ""),
                "Impl. LR %":   yr.get("implied_loss_ratio_pct", ""),
                "Large Loss":   "⚠️" if yr.get("large_loss_flag") else "",
                "Dev. Warning": yr.get("development_warning", "") or "",
            })
        st.dataframe(pd.DataFrame(_loss_rows), use_container_width=True, hide_index=True)

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
                    + "</div>", unsafe_allow_html=True)
        else:
            st.caption("No individual large losses identified.")

        if extracted.get("ibnr_commentary"):
            st.info(f"**IBNR / Development:** {extracted['ibnr_commentary']}")
    else:
        st.warning("No loss history extracted from submission materials.")


def _render_analytics_tab(extracted):
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


def _render_coverage_tab(extracted, section_fields):
    _yesno_fields = [f for f in section_fields if f.field_type == FieldType.YESNO]
    _other_fields = [f for f in section_fields if f.field_type != FieldType.YESNO]
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


def _render_flags_tab(extracted, section_fields):
    _c1, _c2 = st.columns(2)
    _left  = [f for f in section_fields if section_fields.index(f) % 2 == 0]
    _right = [f for f in section_fields if section_fields.index(f) % 2 == 1]
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


def _render_default_tab(extracted, section_fields):
    _c1, _c2 = st.columns(2)
    _mid = (len(section_fields) + 1) // 2
    for _col, _col_fields in [(_c1, section_fields[:_mid]), (_c2, section_fields[_mid:])]:
        with _col:
            for _f in _col_fields:
                _val = extracted.get(_f.key)
                _display = str(_val).strip() if _val is not None else None
                _missing = not _display or _display.lower() in ("null","none","unknown","false","")
                _col.markdown(
                    f'<div class="field-row">'
                    f'<span class="field-label">{_f.label}</span>'
                    f'<span class="{"field-missing" if _missing else "field-value"}">'
                    f'{_display if not _missing else "— not found"}</span>'
                    f'</div>', unsafe_allow_html=True)


def _render_summary_as_markdown(text: str):
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("==="):
            st.markdown("---")
        elif line.startswith("---"):
            pass
        elif line == "PRICING — AI SUBMISSION SUMMARY":
            st.markdown(f"## 🏢 {line}")
        elif line and line.isupper() and len(line) > 3 and not line.startswith("  "):
            st.markdown(f"### {line.title()}")
        elif line.startswith("[OK]") or line.startswith("[!!]"):
            icon = "✅" if line.startswith("[OK]") else "⚠️"
            st.markdown(
                f'<div style="font-size:0.82rem; color:#94A3B8; padding:2px 0;">'
                f'{icon} {line[4:].strip()}</div>', unsafe_allow_html=True)
        elif "  " in line and not line.startswith("•") and not line.startswith("-"):
            parts = line.split(None, 1)
            if len(parts) == 2:
                label, val = parts[0], parts[1].strip()
                val_color = "#94A3B8" if val in ("NOT PROVIDED", "") else "#E2E8F0"
                st.markdown(
                    f'<div class="field-row">'
                    f'<span class="field-label">{label}</span>'
                    f'<span class="field-value" style="color:{val_color};">{val}</span>'
                    f'</div>', unsafe_allow_html=True)
            else:
                if line:
                    st.markdown(f'<div style="font-size:0.83rem; color:#CBD5E1; padding:2px 0;">{line}</div>', unsafe_allow_html=True)
        elif line.startswith("•") or line.startswith("-") or line.startswith("["):
            color = "#EF4444" if "[RED]" in line else "#F59E0B" if "[AMBER]" in line else "#94A3B8"
            st.markdown(
                f'<div style="font-size:0.82rem; color:{color}; padding:2px 0 2px 8px;">{line}</div>',
                unsafe_allow_html=True)
        elif ":" in line and line.split(":")[0].strip() in ("Class", "Case Folder", "Generated", "Data Quality"):
            k, v = line.split(":", 1)
            st.markdown(
                f'<div style="font-size:0.82rem; color:#64748B; padding:1px 0;">'
                f'<span style="color:#475569;">{k}:</span> {v.strip()}</div>',
                unsafe_allow_html=True)
        elif line:
            st.markdown(
                f'<div style="font-size:0.83rem; color:#CBD5E1; padding:2px 0;">{line}</div>',
                unsafe_allow_html=True)
