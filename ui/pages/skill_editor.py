# ============================================================
#  ui/pages/skill_editor.py
#  Skill Viewer page — read-only view of each skill's schema,
#  CSV outputs, and system prompt.
# ============================================================

import streamlit as st

from skills import available_classes, get_skill, get_skill_class
from skills.config_loader import load_config, apply_config, has_config
from ui.styles import EDITOR_CSS


def skill_editor_page():
    """Skill Viewer — read-only schema, CSV, and prompt browser."""
    st.markdown(EDITOR_CSS, unsafe_allow_html=True)

    st.markdown("""
<div class="main-header">
  <h1>SKILL VIEWER</h1>
  <p>Browse field schemas, CSV output columns, and Claude prompts for each skill</p>
</div>
""", unsafe_allow_html=True)

    # ── SIDEBAR — skill selector ──────────────────────────────
    with st.sidebar:
        st.markdown("### 📚 Select Skill")

        skill_label = st.selectbox(
            "Skill",
            options=available_classes(),
            key="viewer_skill_select",
            label_visibility="collapsed",
        )

        skill_cls  = get_skill_class(skill_label)
        skill_code = skill_cls.code()
        config     = load_config(skill_code)
        merged     = apply_config(skill_cls, config)

        st.markdown("---")
        st.markdown(f"**Code:** `{skill_code}`")
        st.markdown(f"**Version:** {skill_cls.version()}")
        st.markdown(f"**Fields:** {len(merged['output_schema'])}")
        st.markdown(f"**CSV columns:** {len(merged['csv_schema'])}")
        st.markdown(f"**Gap-checked:** {len(merged['required_fields'])}")
        if has_config(skill_code):
            n_ov  = len(config.get("field_overrides", {}))
            n_add = len(config.get("field_additions", []))
            st.markdown(f"**Config sidecar:** {n_ov} override(s), {n_add} addition(s)")
        else:
            st.markdown("_No config sidecar_")

    # ── MAIN TABS ─────────────────────────────────────────────
    tab_fields, tab_csv, tab_prompt = st.tabs([
        "📋 Output Schema",
        "📊 CSV Outputs",
        "🤖 System Prompt",
    ])

    fields  = merged["output_schema"]
    csv_sch = merged["csv_schema"]
    req     = merged["required_fields"]

    # ── TAB 1: Output Schema ──────────────────────────────────
    with tab_fields:
        import pandas as pd

        st.markdown(f"### {skill_label} — Output Fields")

        # Section filter
        sections = sorted({f.section.value for f in fields})
        chosen_section = st.selectbox(
            "Filter by section",
            options=["All sections"] + sections,
            key="viewer_section_filter",
        )

        visible = fields if chosen_section == "All sections" else [
            f for f in fields if f.section.value == chosen_section
        ]

        rows = []
        req_keys = {k: c for k, _, c in req}
        for f in visible:
            rows.append({
                "Key":       f.key,
                "Label":     f.label,
                "Section":   f.section.value,
                "Type":      f.field_type.value,
                "Critical":  "🔴" if f.critical else "",
                "Gap Check": "✅" if f.gap_check else "",
                "In CSV":    "✅" if f.in_csv else "",
                "In Tab":    "✅" if f.in_summary else "",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "Key":       st.column_config.TextColumn(width="medium"),
                         "Label":     st.column_config.TextColumn(width="large"),
                         "Section":   st.column_config.TextColumn(width="medium"),
                         "Type":      st.column_config.TextColumn(width="small"),
                         "Critical":  st.column_config.TextColumn(width="small"),
                         "Gap Check": st.column_config.TextColumn(width="small"),
                         "In CSV":    st.column_config.TextColumn(width="small"),
                         "In Tab":    st.column_config.TextColumn(width="small"),
                     })
        st.caption(f"Showing {len(visible)} of {len(fields)} fields")

        # Summary metrics
        n_crit = sum(1 for f in fields if f.critical)
        n_gap  = sum(1 for f in fields if f.gap_check)
        n_csv  = sum(1 for f in fields if f.in_csv)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total fields", len(fields))
        m2.metric("Critical 🔴",  n_crit)
        m3.metric("Gap-checked",  n_gap)
        m4.metric("In CSV",       n_csv)

    # ── TAB 2: CSV Outputs ────────────────────────────────────
    with tab_csv:
        import pandas as pd

        st.markdown(f"### {skill_label} — CSV Output Files")

        # ── Submission CSV
        st.markdown("#### submission_data.csv")
        st.caption("One row per processed submission — appended across runs.")
        csv_rows = []
        fbk = {f.key: f for f in fields}
        for i, col in enumerate(csv_sch):
            f = fbk.get(col)
            csv_rows.append({
                "#":         i + 1,
                "Column":    col,
                "Label":     f.label       if f else "(metadata)",
                "Type":      f.field_type.value if f else "—",
                "Critical":  "🔴"          if (f and f.critical) else "",
                "Gap Check": "✅"          if (f and f.gap_check) else "",
            })
        df_csv = pd.DataFrame(csv_rows)
        st.dataframe(df_csv, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(csv_sch)} columns")

        # ── Claims CSV (if skill has one)
        claims_schema = merged.get("claims_csv_schema") or []
        if claims_schema:
            st.markdown("---")
            st.markdown("#### claims_data.csv")
            st.caption("One row per year of loss history + individual large losses.")
            st.dataframe(
                pd.DataFrame([{"#": i+1, "Column": c} for i, c in enumerate(claims_schema)]),
                use_container_width=True, hide_index=True,
            )
            st.caption(f"Total: {len(claims_schema)} columns")

        # ── Triage / Direct Triage CSVs (skill-specific)
        from core.outputs import TRIAGE_SCHEMA, DIRECT_TRIAGE_SCHEMA
        if skill_code == "PVQ":
            st.markdown("---")
            st.markdown("#### triage_matrix.csv")
            st.caption("One triage row per submission — consolidated across runs.")
            st.dataframe(
                pd.DataFrame([{"#": i+1, "Column": c} for i, c in enumerate(TRIAGE_SCHEMA)]),
                use_container_width=True, hide_index=True,
            )
            st.markdown("---")
            st.markdown("#### triage_locations.csv")
            st.caption("One row per location — consolidated across runs.")
        elif skill_code == "PVDT":
            st.markdown("---")
            st.markdown("#### triage_direct.csv")
            st.caption("One RAG-rated triage row per submission — consolidated across runs.")
            st.dataframe(
                pd.DataFrame([{"#": i+1, "Column": c} for i, c in enumerate(DIRECT_TRIAGE_SCHEMA)]),
                use_container_width=True, hide_index=True,
            )

    # ── TAB 3: System Prompt ──────────────────────────────────
    with tab_prompt:
        st.markdown(f"### {skill_label} — System Prompt")

        prompt_override = config.get("prompt_override") if has_config(skill_code) else None

        if prompt_override:
            st.info("**Config override active** — the prompt below replaces the .py default.")
            col_a, col_b = st.tabs(["Override (active)", "Original .py"])
            with col_a:
                st.code(prompt_override, language="text")
            with col_b:
                st.code(skill_cls.SYSTEM_PROMPT, language="text")
        else:
            st.info("**Using .py default prompt** — no config override.")
            st.code(skill_cls.SYSTEM_PROMPT, language="text")

        st.caption(f"Prompt length: {len(skill_cls.SYSTEM_PROMPT):,} characters")
