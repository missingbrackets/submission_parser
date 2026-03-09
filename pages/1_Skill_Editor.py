# ============================================================
#  pages/1_Skill_Editor.py
#  Pine Walk — Skill Editor
#
#  Streamlit multi-page app page.
#  Allows non-developers to:
#    - Browse and edit skill field properties
#    - Add new fields to a skill
#    - Configure which CSVs consolidate in batch mode
#    - Override the Claude system prompt
#    - Save / reset changes
#
#  All changes are stored in skills/config/<CODE>.json
#  The Python skill files are never modified.
# ============================================================

import os
import sys
import json
import copy

import streamlit as st

# ── Path setup (works whether run via main.py or directly) ───
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from skills import available_classes, get_skill_class, get_skill
from skills.base import FieldType, FieldSource, FieldSection, OutputField
from skills.config_loader import (
    load_config, save_config, delete_config, has_config, apply_config,
    field_to_dict,
    FIELD_TYPE_OPTIONS, FIELD_SOURCE_OPTIONS, SECTION_OPTIONS, SECTION_LABELS,
    CSV_FILES,
)

# ── CSS — reuse main app palette ─────────────────────────────
st.markdown("""
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
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
  <h1>PINE WALK &nbsp;|&nbsp; SKILL EDITOR</h1>
  <p>Configure field schemas, CSV outputs, and Claude prompts · Changes saved to skills/config/</p>
</div>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────

def _section_display(name: str) -> str:
    return SECTION_LABELS.get(name, name)

def _badge(is_new: bool, is_override: bool) -> str:
    if is_new:
        return '<span class="badge-new">NEW</span>'
    if is_override:
        return '<span class="badge-override">EDITED</span>'
    return '<span class="badge-base">BASE</span>'

def _reset_editor_state():
    for k in list(st.session_state.keys()):
        if k.startswith("editor_") and k != "editor_skill_select":
            del st.session_state[k]


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Skill Editor")

    skill_label = st.selectbox(
        "Select skill to edit",
        options=available_classes(),
        key="editor_skill_select",
        on_change=_reset_editor_state,
    )

    skill_cls = get_skill_class(skill_label)
    skill_code = skill_cls.code()
    config = load_config(skill_code)

    st.markdown("---")
    st.markdown(f"**Code:** `{skill_code}`")
    st.markdown(f"**Version:** {skill_cls.version()}")
    st.markdown(f"**Base fields:** {len(skill_cls.OUTPUT_SCHEMA)}")

    _additions = len(config.get("field_additions", []))
    _overrides = len(config.get("field_overrides", {}))
    if has_config(skill_code):
        st.markdown(f"**Overrides:** {_overrides} field(s) edited")
        st.markdown(f"**Additions:** {_additions} new field(s)")
        st.info("This skill has a config sidecar.")
    else:
        st.markdown("_No config sidecar — using .py defaults_")

    st.markdown("---")
    if st.button("💾 Save All Changes", type="primary", use_container_width=True,
                 key="sidebar_save"):
        st.session_state["editor_save_triggered"] = True

    if has_config(skill_code):
        if st.button("🔄 Reset to Defaults", use_container_width=True, key="sidebar_reset"):
            st.session_state["editor_reset_triggered"] = True


# ── Load working config into session state ────────────────────
_sk = f"editor_working_config_{skill_code}"
if _sk not in st.session_state:
    st.session_state[_sk] = copy.deepcopy(config)

working = st.session_state[_sk]


# ── Handle save / reset ───────────────────────────────────────
if st.session_state.pop("editor_save_triggered", False):
    saved_path = save_config(skill_code, working)
    st.success(f"✅ Saved to `{saved_path}`")
    # Reload to reflect saved state
    st.session_state[_sk] = copy.deepcopy(working)
    st.rerun()

if st.session_state.pop("editor_reset_triggered", False):
    deleted = delete_config(skill_code)
    if deleted:
        st.success("✅ Config reset — skill now uses .py defaults.")
    del st.session_state[_sk]
    st.rerun()


# ── Build the merged view for display ────────────────────────
merged_skill = apply_config(skill_cls, working)
merged_fields: list[OutputField] = merged_skill["output_schema"]

# Track which keys came from additions vs base
base_keys     = {f.key for f in skill_cls.OUTPUT_SCHEMA}
addition_keys = {d["key"] for d in working.get("field_additions", []) if d.get("key")}
override_keys = set(working.get("field_overrides", {}).keys())


# ── TABS ─────────────────────────────────────────────────────
tab_fields, tab_csv, tab_prompt, tab_preview = st.tabs([
    "📋 Fields",
    "📊 CSV & Batch Config",
    "🤖 System Prompt",
    "👁 Preview",
])


# ══════════════════════════════════════════════════════════════
# TAB 1 — FIELDS
# ══════════════════════════════════════════════════════════════
with tab_fields:

    st.markdown("### Field Schema")
    st.caption(
        "Edit properties of existing fields or add new ones. "
        "BASE fields come from the skill .py file. "
        "EDITED fields have UI overrides. NEW fields were added here."
    )

    # ── Filter / search bar ──────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        search = st.text_input("🔍 Search fields", placeholder="key or label...", key="editor_search")
    with fc2:
        filter_section = st.selectbox(
            "Filter by section",
            options=["All"] + [_section_display(s) for s in SECTION_OPTIONS],
            key="editor_filter_section",
        )
    with fc3:
        filter_status = st.selectbox(
            "Filter by status",
            options=["All", "BASE", "EDITED", "NEW"],
            key="editor_filter_status",
        )

    # ── Apply filters ────────────────────────────────────────
    def _status(key):
        if key in addition_keys: return "NEW"
        if key in override_keys: return "EDITED"
        return "BASE"

    visible_fields = merged_fields
    if search:
        s = search.lower()
        visible_fields = [f for f in visible_fields if s in f.key.lower() or s in f.label.lower()]
    if filter_section != "All":
        visible_fields = [f for f in visible_fields if f.section.value == filter_section]
    if filter_status != "All":
        visible_fields = [f for f in visible_fields if _status(f.key) == filter_status]

    st.caption(f"Showing {len(visible_fields)} of {len(merged_fields)} fields")
    st.markdown("---")

    # ── Field rows ───────────────────────────────────────────
    for f in visible_fields:
        status = _status(f.key)
        is_new = (status == "NEW")
        is_ov  = (status == "EDITED")

        with st.expander(
            f"{f.key}  ·  {f.label}  ·  {f.section.value}",
            expanded=False,
        ):
            st.markdown(
                f'**{f.key}** {_badge(is_new, is_ov)}',
                unsafe_allow_html=True,
            )

            col_a, col_b, col_c = st.columns(3)
            col_d, col_e, col_f = st.columns(3)
            col_g, _            = st.columns([4, 2])

            with col_a:
                new_label = st.text_input("Label", value=f.label,
                                          key=f"editor_label_{f.key}")
            with col_b:
                new_section = st.selectbox(
                    "Section / Tab",
                    options=SECTION_OPTIONS,
                    index=SECTION_OPTIONS.index(f.section.name),
                    format_func=_section_display,
                    key=f"editor_section_{f.key}",
                )
            with col_c:
                new_type = st.selectbox(
                    "Field Type",
                    options=FIELD_TYPE_OPTIONS,
                    index=FIELD_TYPE_OPTIONS.index(f.field_type.name),
                    key=f"editor_type_{f.key}",
                )

            with col_d:
                new_in_csv = st.checkbox("In Submission CSV",  value=f.in_csv,
                                         key=f"editor_csv_{f.key}")
            with col_e:
                new_in_summary = st.checkbox("Show in Tab",    value=f.in_summary,
                                             key=f"editor_sum_{f.key}")
            with col_f:
                new_gap = st.checkbox("Gap Check",             value=f.gap_check,
                                      key=f"editor_gap_{f.key}")

            new_critical = st.checkbox(
                "🔴 Critical (missing = RED flag)",
                value=f.critical,
                key=f"editor_crit_{f.key}",
            )

            with col_g:
                new_desc = st.text_input("Description / tooltip", value=f.description,
                                         key=f"editor_desc_{f.key}")

            # ── Apply button for this field ──────────────────
            apply_col, remove_col = st.columns([3, 1])
            with apply_col:
                if st.button(f"✅ Apply changes to '{f.key}'",
                             key=f"editor_apply_{f.key}",
                             use_container_width=True):
                    # Collect new values from widget state
                    ov = {
                        "label":      st.session_state[f"editor_label_{f.key}"],
                        "section":    st.session_state[f"editor_section_{f.key}"],
                        "field_type": st.session_state[f"editor_type_{f.key}"],
                        "in_csv":     st.session_state[f"editor_csv_{f.key}"],
                        "in_summary": st.session_state[f"editor_sum_{f.key}"],
                        "gap_check":  st.session_state[f"editor_gap_{f.key}"],
                        "critical":   st.session_state[f"editor_crit_{f.key}"],
                        "description":st.session_state[f"editor_desc_{f.key}"],
                    }

                    if is_new:
                        # Update in field_additions list
                        for add in working["field_additions"]:
                            if add.get("key") == f.key:
                                add.update(ov)
                                add["source"] = f.source.name
                                break
                    else:
                        # Write to field_overrides
                        if "field_overrides" not in working:
                            working["field_overrides"] = {}
                        existing_ov = working["field_overrides"].get(f.key, {})
                        existing_ov.update(ov)
                        working["field_overrides"][f.key] = existing_ov

                    st.session_state[_sk] = working
                    st.success(f"✅ '{f.key}' updated — click **Save All Changes** to persist.")
                    st.rerun()

            with remove_col:
                if is_new:
                    if st.button(f"🗑 Remove", key=f"editor_remove_{f.key}",
                                 use_container_width=True):
                        working["field_additions"] = [
                            a for a in working.get("field_additions", [])
                            if a.get("key") != f.key
                        ]
                        st.session_state[_sk] = working
                        st.rerun()
                elif is_ov:
                    if st.button(f"↩ Revert", key=f"editor_revert_{f.key}",
                                 use_container_width=True):
                        working.get("field_overrides", {}).pop(f.key, None)
                        st.session_state[_sk] = working
                        st.rerun()

    # ── ADD NEW FIELD ────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ➕ Add New Field")
    st.caption(
        "Add a field that doesn't exist in the base skill. "
        "This field will be added to the extraction prompt, CSV, and UI tabs. "
        "You must also add it to the Claude prompt manually (System Prompt tab)."
    )

    # Suggest keys from other skills that aren't in this one
    all_keys_across_skills = set()
    for lbl in available_classes():
        try:
            other_cls = get_skill_class(lbl)
            for f in other_cls.OUTPUT_SCHEMA:
                all_keys_across_skills.add(f.key)
        except Exception:
            pass
    suggestion_keys = sorted(all_keys_across_skills - {f.key for f in merged_fields})

    na1, na2 = st.columns(2)
    with na1:
        new_key_mode = st.radio(
            "Field key source",
            options=["Pick from existing skills", "Define new key"],
            key="editor_new_key_mode",
            horizontal=True,
        )
    with na2:
        if new_key_mode == "Pick from existing skills":
            chosen_key = st.selectbox(
                "Existing field key",
                options=["(select)"] + suggestion_keys,
                key="editor_pick_existing_key",
            )
            # Pre-populate label/type from whichever skill has this field
            _prefill = None
            if chosen_key != "(select)":
                for lbl in available_classes():
                    try:
                        other_cls = get_skill_class(lbl)
                        fbk = other_cls.fields_by_key()
                        if chosen_key in fbk:
                            _prefill = fbk[chosen_key]
                            break
                    except Exception:
                        pass
            new_field_key = chosen_key if chosen_key != "(select)" else ""
        else:
            new_field_key = st.text_input(
                "New field key (snake_case)",
                placeholder="e.g. vessel_flag",
                key="editor_new_field_key_text",
            ).strip().lower().replace(" ", "_")
            _prefill = None

    nb1, nb2, nb3 = st.columns(3)
    with nb1:
        nf_label = st.text_input(
            "Label",
            value=_prefill.label if _prefill else "",
            key="editor_nf_label",
        )
    with nb2:
        nf_section = st.selectbox(
            "Section / Tab",
            options=SECTION_OPTIONS,
            index=SECTION_OPTIONS.index(_prefill.section.name) if _prefill else 0,
            format_func=_section_display,
            key="editor_nf_section",
        )
    with nb3:
        nf_type = st.selectbox(
            "Field Type",
            options=FIELD_TYPE_OPTIONS,
            index=FIELD_TYPE_OPTIONS.index(_prefill.field_type.name) if _prefill else 0,
            key="editor_nf_type",
        )

    nc1, nc2, nc3, nc4 = st.columns(4)
    with nc1:
        nf_csv     = st.checkbox("In Submission CSV", value=True,  key="editor_nf_csv")
    with nc2:
        nf_summary = st.checkbox("Show in Tab",       value=True,  key="editor_nf_summary")
    with nc3:
        nf_gap     = st.checkbox("Gap Check",         value=True,  key="editor_nf_gap")
    with nc4:
        nf_crit    = st.checkbox("Critical",          value=False, key="editor_nf_crit")

    nf_desc = st.text_input("Description", key="editor_nf_desc")

    if st.button("➕ Add Field", type="primary", key="editor_add_field_btn"):
        if not new_field_key:
            st.error("Field key is required.")
        elif new_field_key in {f.key for f in merged_fields}:
            st.error(f"Key '{new_field_key}' already exists in this skill.")
        else:
            new_entry = {
                "key":         new_field_key,
                "label":       nf_label or new_field_key,
                "field_type":  st.session_state["editor_nf_type"],
                "source":      "EXTRACTED",
                "section":     st.session_state["editor_nf_section"],
                "in_csv":      st.session_state["editor_nf_csv"],
                "in_summary":  st.session_state["editor_nf_summary"],
                "gap_check":   st.session_state["editor_nf_gap"],
                "critical":    st.session_state["editor_nf_crit"],
                "description": st.session_state["editor_nf_desc"],
            }
            if "field_additions" not in working:
                working["field_additions"] = []
            working["field_additions"].append(new_entry)
            st.session_state[_sk] = working
            st.success(f"✅ Field '{new_field_key}' added — click **Save All Changes** to persist.")
            st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 2 — CSV & BATCH CONFIG
# ══════════════════════════════════════════════════════════════
with tab_csv:

    st.markdown("### CSV Output Configuration")
    st.caption(
        "Control which CSV files this skill produces and which are "
        "consolidated into the parent folder when running in batch mode."
    )

    consol = working.get("csv_consolidation", {})
    if not isinstance(consol, dict):
        consol = {}

    st.markdown("#### Batch Mode Consolidation")
    st.markdown(
        "When running in **Multiple Submissions** mode, ticking a file here "
        "means all rows from every submission in the batch are also appended "
        "to a consolidated copy in the parent folder's `submission_tool_auto_outputs/`."
    )
    st.markdown("")

    new_consol = {}
    for csv_key, csv_display in CSV_FILES.items():
        default_val = consol.get(csv_key, csv_key in ("submission_data", "claims_data"))
        new_consol[csv_key] = st.checkbox(
            f"Consolidate **{csv_display}** to parent folder",
            value=default_val,
            key=f"editor_consol_{csv_key}",
        )

    working["csv_consolidation"] = new_consol
    st.session_state[_sk] = working

    st.markdown("---")
    st.markdown("#### Submission CSV Column Preview")
    st.caption("Columns that will appear in submission_data.csv for this skill, in order.")

    csv_cols = merged_skill["csv_schema"]
    col_data = []
    fbk = {f.key: f for f in merged_fields}
    for i, col in enumerate(csv_cols):
        f = fbk.get(col)
        col_data.append({
            "Position": i + 1,
            "Column":   col,
            "Label":    f.label if f else "(metadata)",
            "Type":     f.field_type.value if f else "metadata",
            "Critical": "🔴" if (f and f.critical) else "",
            "Gap Check":"✅" if (f and f.gap_check) else "",
        })

    import pandas as pd
    df_cols = pd.DataFrame(col_data)
    st.dataframe(df_cols, use_container_width=True, hide_index=True)
    st.caption(f"Total: {len(csv_cols)} columns")

    st.markdown("---")
    st.markdown("#### Gap Analysis Summary")
    req = merged_skill["required_fields"]
    crit_count = sum(1 for _, _, c in req if c)
    adv_count  = len(req) - crit_count
    gc1, gc2, gc3 = st.columns(3)
    gc1.metric("Gap-checked fields", len(req))
    gc2.metric("Critical (RED)",     crit_count)
    gc3.metric("Advisory (AMBER)",   adv_count)


# ══════════════════════════════════════════════════════════════
# TAB 3 — SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════
with tab_prompt:

    st.markdown("### Claude System Prompt")

    has_prompt_override = bool(working.get("prompt_override"))
    if has_prompt_override:
        st.info("**Override active** — this prompt replaces the .py default.")
    else:
        st.info(
            "**Using .py default.** Edit below and click Apply to create an override. "
            "The original .py file is never modified."
        )

    # Show base prompt for reference if override is active
    if has_prompt_override:
        with st.expander("View original .py prompt"):
            st.code(skill_cls.SYSTEM_PROMPT, language="text")

    current_prompt = working.get("prompt_override") or skill_cls.SYSTEM_PROMPT

    edited_prompt = st.text_area(
        "System prompt",
        value=current_prompt,
        height=500,
        key="editor_prompt_text",
        label_visibility="collapsed",
    )

    pa1, pa2 = st.columns(2)
    with pa1:
        if st.button("✅ Apply Prompt Override", type="primary",
                     key="editor_apply_prompt", use_container_width=True):
            working["prompt_override"] = st.session_state["editor_prompt_text"]
            st.session_state[_sk] = working
            st.success("Prompt override applied — click **Save All Changes** to persist.")
            st.rerun()

    with pa2:
        if has_prompt_override:
            if st.button("↩ Revert to .py Default",
                         key="editor_revert_prompt", use_container_width=True):
                working["prompt_override"] = None
                st.session_state[_sk] = working
                st.success("Prompt override cleared.")
                st.rerun()

    st.markdown("---")
    st.markdown("#### JSON Template Helper")
    st.caption(
        "The JSON block at the end of your prompt must include all fields "
        "marked 'In Submission CSV' or 'Show in Tab'. "
        "The block below is auto-generated from the current field schema — "
        "copy it into your prompt as a starting point."
    )

    json_template = {}
    for f in merged_fields:
        if f.in_summary or f.in_csv:
            if f.field_type == FieldType.ARRAY:
                json_template[f.key] = []
            elif f.field_type == FieldType.YESNO:
                json_template[f.key] = "Unknown"
            elif f.field_type in (FieldType.NUMBER, FieldType.CURRENCY, FieldType.PERCENT):
                json_template[f.key] = None
            else:
                json_template[f.key] = None

    st.code(json.dumps(json_template, indent=2), language="json")

    if st.button("📋 Copy JSON template to clipboard", key="editor_copy_json"):
        st.info("Use the copy icon in the code block above — browser clipboard access is not available.")


# ══════════════════════════════════════════════════════════════
# TAB 4 — PREVIEW
# ══════════════════════════════════════════════════════════════
with tab_preview:

    st.markdown("### Merged Skill Preview")
    st.caption(
        "This shows exactly what the skill will look like after your changes "
        "are saved — field count, CSV columns, gap analysis settings."
    )

    pv1, pv2, pv3, pv4 = st.columns(4)
    pv1.metric("Total fields",     len(merged_fields))
    pv2.metric("CSV columns",      len(merged_skill["csv_schema"]))
    pv3.metric("Gap-checked",      len(merged_skill["required_fields"]))
    pv4.metric("Critical fields",  sum(1 for f in merged_fields if f.critical))

    if has_config(skill_code):
        delta_fields = len(merged_fields) - len(skill_cls.OUTPUT_SCHEMA)
        if delta_fields != 0:
            st.info(
                f"{'➕' if delta_fields > 0 else '➖'} "
                f"{abs(delta_fields)} field(s) {'added' if delta_fields > 0 else 'removed'} "
                f"vs .py base  ·  {len(override_keys)} field(s) have property overrides"
            )

    st.markdown("---")
    st.markdown("#### Full Field List")

    preview_rows = []
    for f in merged_fields:
        status = _status(f.key)
        preview_rows.append({
            "Key":       f.key,
            "Label":     f.label,
            "Section":   f.section.value,
            "Type":      f.field_type.value,
            "CSV":       "✅" if f.in_csv else "",
            "Tab":       "✅" if f.in_summary else "",
            "Gap":       "✅" if f.gap_check else "",
            "Critical":  "🔴" if f.critical else "",
            "Status":    status,
        })

    import pandas as pd
    df_preview = pd.DataFrame(preview_rows)
    # Highlight new/edited rows
    def _highlight_status(row):
        if row["Status"] == "NEW":
            return ["background-color: #0A2A14"] * len(row)
        if row["Status"] == "EDITED":
            return ["background-color: #1A2744"] * len(row)
        return [""] * len(row)

    styled = df_preview.style.apply(_highlight_status, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Raw Config JSON")
    st.caption("The exact JSON that will be written to the sidecar file.")
    st.code(json.dumps(working, indent=2), language="json")

    if st.button("💾 Save All Changes", type="primary",
                 key="preview_save_btn", use_container_width=False):
        saved_path = save_config(skill_code, working)
        st.success(f"✅ Saved to `{saved_path}`")
        st.session_state[_sk] = copy.deepcopy(working)
        st.rerun()