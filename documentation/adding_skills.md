# Pine Walk Submission Analyser — Adding Skills

> AI-powered submission analysis that extracts, structures and triages London Market risks in seconds — turning broker slips into pricing-ready data.

This document is the complete reference for adding a new class of business skill. It covers the skill file itself, any new tab types, custom CSV outputs, and the hooks needed in `claude_caller.py` and `main.py` for both single and batch mode.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Skills in the Current Codebase](#2-skills-in-the-current-codebase)
3. [Quick Start](#3-quick-start)
4. [The Five Required Sections](#4-the-five-required-sections)
5. [OutputField Reference](#5-outputfield-reference)
6. [FieldSection — Sections and Tabs](#6-fieldsection--sections-and-tabs)
7. [Adding a New FieldSection](#7-adding-a-new-fieldsection)
8. [Adding a Custom Tab Renderer](#8-adding-a-custom-tab-renderer)
9. [Output Folder Structure](#9-output-folder-structure)
10. [Standard CSV Outputs](#10-standard-csv-outputs)
11. [Adding a Skill-Specific CSV Output](#11-adding-a-skill-specific-csv-output)
12. [Skill-Specific CSV Gating](#12-skill-specific-csv-gating)
13. [Hooking into the Batch Runner](#13-hooking-into-the-batch-runner)
14. [The Triage Skill Pattern](#14-the-triage-skill-pattern)
15. [The System Prompt](#15-the-system-prompt)
16. [build_csv_row — Safety Rules](#16-build_csv_row--safety-rules)
17. [Full Checklist](#17-full-checklist)

---

## 1. Architecture Overview

```
submission_analyser/
  main.py               Streamlit UI — render_results(), run_single(), run_batch()
  file_parser.py        PDF/Word/Excel/.msg text extraction
  claude_caller.py      Claude API call, gap analysis, all CSV builders and savers
  requirements.txt
  Launch_Analyser.bat

  skills/
    __init__.py         Auto-discovery registry — never needs editing
    base.py             FieldType, FieldSource, FieldSection enums
                        OutputField dataclass, TabConfig dataclass
                        BaseSkill base class
    casualty.py         Casualty Liability (CAS)
    terror.py           Political Violence & Terrorism — full (PVT)
    terror_quick.py     PV Triage / Quick (PVQ)
    _template.py        Copy this to start a new skill
    your_new.py         Drop here — auto-registers on next app start
```

### The key principle

`OUTPUT_SCHEMA` is the single source of truth. When you define a field there, the framework automatically:

- Adds it as a column in `submission_data.csv` (if `in_csv=True`)
- Shows it in the summary report and UI tab (if `in_summary=True`)
- Includes it in gap analysis (if `gap_check=True`)
- Flags it RED or AMBER if missing (if `critical=True/False`)

You write code in at most four places:

| File | When |
|------|------|
| `skills/your_skill.py` | Always — defines extraction logic |
| `skills/base.py` | Only if you need a new tab type (`FieldSection`) |
| `claude_caller.py` | Only if you need a new skill-specific CSV output |
| `main.py` | Only if you need a custom tab renderer or batch runner hook |

---

## 2. Skills in the Current Codebase

| File | Label (dropdown) | Code | Purpose |
|------|-----------------|------|---------|
| `casualty.py` | Casualty Liability | `CAS` | Full casualty extraction — 95 fields |
| `terror.py` | Political Violence & Terrorism | `PVT` | Full PV extraction — 152 fields |
| `terror_quick.py` | PV Triage (Quick) | `PVQ` | Fast triage — 42 fields + triage recommendation |

The `code` value in `META` is used to gate skill-specific CSV outputs (see section 12). Keep codes short, unique, and uppercase.

---

## 3. Quick Start

**Step 1 — Copy the template**
```
skills/_template.py  →  skills/marine.py   (or property.py, space.py etc.)
```

**Step 2 — Fill in the five sections** (see section 4)

**Step 3 — Restart the app.** Your skill appears in the dropdown automatically.

No other files need editing for a standard skill that uses only `submission_data.csv` and `claims_data.csv`.

---

## 4. The Five Required Sections

Every skill file defines a class inheriting `BaseSkill` with five class-level attributes.

```python
from skills.base import BaseSkill, OutputField, TabConfig, FieldType, FieldSource, FieldSection

O = OutputField   # shorthand keeps OUTPUT_SCHEMA readable

class MarineSkill(BaseSkill):

    # ── 1. META ──────────────────────────────────────────────────
    META = {
        "label":       "Marine Cargo",      # shown in dropdown
        "code":        "MAR",               # unique 2-5 char ID — used for CSV gating
        "version":     "1.0",
        "description": "London Market marine cargo and stock throughput.",
    }

    # ── 2. TABS ──────────────────────────────────────────────────
    # Controls which tabs appear and their sidebar checkbox default.
    # Omit TABS entirely to auto-generate tabs from OUTPUT_SCHEMA sections.
    TABS = [
        TabConfig(FieldSection.INSURED,   icon="🏢", default_on=True,  description="Insured details"),
        TabConfig(FieldSection.POLICY,    icon="📄", default_on=True,  description="Policy structure"),
        TabConfig(FieldSection.LIMITS,    icon="🔢", default_on=True,  description="Limits and deductibles"),
        TabConfig(FieldSection.PREMIUM,   icon="💷", default_on=True,  description="Premium and rating"),
        TabConfig(FieldSection.LOSS,      icon="📉", default_on=True,  description="Loss history"),
        TabConfig(FieldSection.FLAGS,     icon="⚠️", default_on=True,  description="Risk flags"),
        TabConfig(FieldSection.ANALYTICS, icon="🚩", default_on=True,  description="UW analyst flags"),
    ]

    # ── 3. CLAIMS_SCHEMA ─────────────────────────────────────────
    # Flat list of column names for claims_data.csv.
    # Set to [] if this class has no loss history CSV.
    CLAIMS_SCHEMA = [
        "Segment_1", "Segment_2", "underwriting_year", "claim_id",
        "accident_date", "reported_date", "insured",
        "peril", "claim_description", "status",
        "paid", "outstanding", "incurred", "Manual Claim Adjustments",
    ]

    # ── 4. OUTPUT_SCHEMA ─────────────────────────────────────────
    # One OutputField per extracted or derived field.
    # This drives: submission CSV columns, gap analysis, tab display, summary report.
    OUTPUT_SCHEMA = [
        O("insured_name",         "Insured Name",    FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True),
        O("premium_sought_gross", "Premium Sought",  FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=True),
        O("rate_on_line_pct",     "Rate on Line %",  FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,   gap_check=False),
        O("uw_analyst_flags",     "UW Flags",        FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, in_csv=False, gap_check=False),
        O("data_conflicts",       "Data Conflicts",  FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, in_csv=False, gap_check=False),
        O("questions_for_broker", "Broker Questions",FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, in_csv=False, gap_check=False),
        # ... etc
    ]

    # ── 5. SYSTEM_PROMPT ─────────────────────────────────────────
    SYSTEM_PROMPT = """You are a senior London Market marine underwriter..."""
```

---

## 5. OutputField Reference

```python
OutputField(
    key         = "field_json_key",       # must match the JSON key Claude returns
    label       = "Human Label",          # shown in UI, reports, gap analysis
    field_type  = FieldType.TEXT,         # see FieldType table below
    source      = FieldSource.EXTRACTED,  # EXTRACTED / DERIVED / METADATA
    section     = FieldSection.INSURED,   # which tab this field belongs to
    in_csv      = True,                   # include as submission_data.csv column
    in_summary  = True,                   # show in summary report and UI tab
    critical    = False,                  # True = RED gap flag if missing
    gap_check   = True,                   # False = skip gap analysis entirely
    description = "Tooltip / doc text",   # shown in schema_doc() and tooltips
)
```

### FieldType values

| Value | Use for |
|-------|---------|
| `TEXT` | Free text strings |
| `NUMBER` | Numeric values (stored as string in CSV) |
| `CURRENCY` | Monetary amounts |
| `PERCENT` | Percentages |
| `DATE` | Date strings |
| `YESNO` | Fields that return Y / N / Unknown |
| `BOOLEAN` | True / false flags |
| `ARRAY` | Lists — loss history, SOV locations, UW flags etc. |
| `DERIVED` | Calculated post-extraction — pair with `source=FieldSource.DERIVED` |

### FieldSource values

| Value | Use for |
|-------|---------|
| `EXTRACTED` | Claude extracts directly from submission text |
| `DERIVED` | Calculated by `build_csv_row()` in `claude_caller.py` |
| `METADATA` | Set by the app — extraction date, folder name etc. |

### Common field patterns

```python
# Standard extracted text field
O("insured_name", "Insured Name", FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.INSURED, critical=True)

# Currency with companion currency field (gap_check=False on currency — it's secondary)
O("premium_sought_gross", "Premium Sought", FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM, critical=True)
O("premium_currency",     "Currency",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM, gap_check=False)

# Y/N flag
O("bi_covered", "BI Covered", FieldType.YESNO, FieldSource.EXTRACTED, FieldSection.LIMITS, critical=True)

# Array — shown in tab but NOT a CSV column
O("loss_history", "Loss History", FieldType.ARRAY, FieldSource.EXTRACTED, FieldSection.LOSS, critical=True, in_csv=False)

# Derived field — calculated, not extracted, not gap-checked
O("rate_on_line_pct", "Rate on Line %", FieldType.PERCENT, FieldSource.DERIVED, FieldSection.PREMIUM, gap_check=False)

# CSV-only flattened field — in CSV but not shown in UI tab
O("loss_yr1_year", "Loss Yr1 Year", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False)

# Standard analytics arrays — include all three in every skill
O("uw_analyst_flags",     "UW Flags",         FieldType.ARRAY, FieldSource.EXTRACTED, FieldSection.ANALYTICS, in_csv=False, gap_check=False)
O("data_conflicts",       "Data Conflicts",   FieldType.ARRAY, FieldSource.EXTRACTED, FieldSection.ANALYTICS, in_csv=False, gap_check=False)
O("questions_for_broker", "Broker Questions", FieldType.ARRAY, FieldSource.EXTRACTED, FieldSection.ANALYTICS, in_csv=False, gap_check=False)
```

---

## 6. FieldSection — Sections and Tabs

Each `FieldSection` value becomes a potential tab. Sections without any `in_summary=True` fields are never shown. Sections with dedicated renderers display automatically — no extra code needed.

| Enum value | Display name | Icon | Renderer | Notes |
|------------|-------------|------|----------|-------|
| `INSURED` | Insured & Exposure | 🏢 | Default grid | Identity, revenue, employees |
| `POLICY` | Policy Structure | 📄 | Default grid | Period, trigger, jurisdiction |
| `LIMITS` | Limits & Structure | 🔢 | Default grid | Limits, excess, deductible |
| `COVERAGE` | Coverage Lines | 🏷 | Y/N icons | Y/N flags — automatic icon renderer |
| `PREMIUM` | Premium Analytics | 💷 | Default grid | Premium, brokerage, rate metrics |
| `LOSS` | Loss History | 📉 | Loss table | Loss years + large losses, implied LRs |
| `FLAGS` | Risk Flags | ⚠️ | Colour grid | Litigation, declinatures |
| `ANALYTICS` | Underwriter Analytics | 🚩 | Flag cards | UW flags, conflicts, broker questions |
| `LOCATIONS` | Locations & SOV | 📍 | SOV table | Per-location schedule (PV skills) |
| `PERILS` | Peril Structure | 💥 | Y/N icons | Peril Y/N flags (PV skills) |
| `BI_EXT` | BI & Extensions | 🔄 | Default grid | BI, ICOW, extensions (PV skills) |
| `GEO` | Geopolitical Assessment | 🌍 | Default grid | Country risk, sanctions (PV skills) |
| `RATER` | Rater Inputs | 🧮 | Rater card | Structured rater input (PV skills) |
| `META` | Metadata | ℹ️ | Default grid | Extraction date, folder etc. |

---

## 7. Adding a New FieldSection

Only needed if none of the existing sections fit. Two steps, both in `base.py`:

**Step 1 — Add the enum value:**
```python
class FieldSection(Enum):
    # ... existing values ...
    VESSEL = "Vessel Schedule"    # ← add here
```

**Step 2 — Add the default icon in `tab_config()`:**
```python
default_icons = {
    # ... existing entries ...
    FieldSection.VESSEL: "⚓",    # ← add here
}
```

This gives the section a default icon and the standard two-column key-value grid renderer. For a custom table renderer see section 8.

---

## 8. Adding a Custom Tab Renderer

The tab rendering loop lives inside `render_results()` in `main.py`. It has a chain of `if / elif` checks per section — anything not matched falls through to the default two-column key-value grid.

Find the loop (search for `for _i, _tc in enumerate(_active_tabs):`) and add your `elif` block before the final `else:`:

```python
elif _tc.section == FieldSection.VESSEL:
    import pandas as pd
    vessels = [v for v in (extracted.get("vessel_schedule") or [])
               if isinstance(v, dict)]   # always filter with isinstance
    if vessels:
        _rows = [{
            "Vessel":  v.get("vessel_name", ""),
            "Flag":    v.get("flag", ""),
            "Type":    v.get("vessel_type", ""),
            "TIV":     v.get("insured_value", ""),
        } for v in vessels]
        _df = pd.DataFrame(_rows)
        _df = _df.loc[:, (_df != "").any(axis=0)]  # drop fully-empty columns
        st.dataframe(_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No vessel schedule extracted.")
```

**Rules:**
- Always filter arrays: `[v for v in (extracted.get("key") or []) if isinstance(v, dict)]`
- Always drop empty columns: `.loc[:, (df != "").any(axis=0)]`
- Place your `elif` before the final `else:` default renderer
- `_section_fields` is available — it's all `OutputField` objects for this section with `in_summary=True`, useful for rendering remaining scalar fields below the table

---

## 9. Output Folder Structure

All outputs write to a `submission_tool_auto_outputs/` subfolder. The `_output_root()` helper in `claude_caller.py` constructs this path — always pass it the case folder, never the outputs folder directly.

**Single submission mode** — outputs go into the submission folder:
```
case_folder/
  submission_tool_auto_outputs/
    YYYYMMDD_AI_Summary.txt
    submission_data.csv
    claims_data.csv
    locations_data.csv          (PVT skill only)
    triage_matrix.csv           (PVQ skill only)
    triage_locations.csv        (PVQ skill only)
```

**Batch mode** — per-submission outputs plus a consolidated roll-up at parent level:
```
parent_folder/
  submission_tool_auto_outputs/
    submission_data_all.csv     ← consolidated, one row per submission (all skills)
    claims_data.csv             ← consolidated claims roll-up (all skills)
    triage_matrix.csv           ← consolidated triage rows (PVQ only)
    triage_locations.csv        ← consolidated locations (PVQ only)

  subfolder_A/
    submission_tool_auto_outputs/
      YYYYMMDD_AI_Summary.txt
      submission_data.csv
      claims_data.csv
      locations_data.csv

  subfolder_B/
    submission_tool_auto_outputs/
      ...
```

**Append vs overwrite:**

| File | Mode | Reason |
|------|------|--------|
| `submission_data.csv` | Append `"a"` | Grows across submissions |
| `submission_data_all.csv` | Append `"a"` | Batch consolidated roll-up |
| `claims_data.csv` | Append `"a"` | Grows across submissions |
| `triage_matrix.csv` | Append `"a"` | Portfolio-level accumulation across all runs |
| `triage_locations.csv` | Append `"a"` | Portfolio-level accumulation across all runs |
| `locations_data.csv` | Overwrite `"w"` | Per-submission, replaced each run |
| `YYYYMMDD_AI_Summary.txt` | Overwrite `"w"` | Per-submission, replaced each run |

---

## 10. Standard CSV Outputs

These are produced automatically for every skill — no skill-specific code needed.

| File | Builder | Saver | Driven by |
|------|---------|-------|-----------|
| `submission_data.csv` | `build_csv_row()` | `save_csv()` | `OUTPUT_SCHEMA` (`in_csv=True` fields) |
| `claims_data.csv` | `build_claims_csv_rows()` | `save_claims_csv()` | `CLAIMS_SCHEMA` |

`build_csv_row()` is fully generic — it iterates the active skill's `csv_schema` and writes any matching key from `extracted`. You do not need to touch it when adding a new skill.

**Critical:** Any key written into `row` inside `build_csv_row()` must exist in `csv_schema`. Writing a key not in the schema raises `dict contains fields not in fieldnames`. See section 16 for the safety pattern.

---

## 11. Adding a Skill-Specific CSV Output

For CSVs beyond the standard two — e.g. SOV locations, vessel schedules, treaty layers. Requires changes to three files.

### Step 1 — Add schema constant and builder in `claude_caller.py`

Add the schema constant near the top of the file alongside `TRIAGE_SCHEMA` and `LOCATION_SCHEMA`:

```python
VESSEL_SCHEMA = [
    "extraction_date", "insured_name",
    "vessel_id", "vessel_name", "flag", "imo_number",
    "vessel_type", "year_built", "gross_tonnage",
    "insured_value", "currency", "notes",
]
```

Then add the builder function:

```python
def build_vessels_csv_rows(extracted: dict) -> tuple:
    """Returns (rows, schema). One row per vessel in vessel_schedule array."""
    rows    = []
    insured = _safe(extracted.get("insured_name"))
    today   = datetime.date.today().isoformat()

    vessels = [v for v in (extracted.get("vessel_schedule") or [])
               if isinstance(v, dict)]

    for i, v in enumerate(vessels):
        row = {col: "" for col in VESSEL_SCHEMA}
        row["extraction_date"] = today
        row["insured_name"]    = insured
        row["vessel_id"]       = f"VES-{str(i+1).zfill(3)}"
        row["vessel_name"]     = _safe(v.get("vessel_name"))
        row["flag"]            = _safe(v.get("flag"))
        row["imo_number"]      = _safe(v.get("imo_number"))
        row["insured_value"]   = _safe(v.get("insured_value"))
        row["currency"]        = _safe(v.get("currency"))
        row["notes"]           = _safe(v.get("notes"))
        rows.append(row)

    return rows, VESSEL_SCHEMA
```

### Step 2 — Add a saver function in `claude_caller.py`

```python
def save_vessels_csv(rows: list, schema: list,
                     output_folder: str,
                     filename: str = "vessels_data.csv") -> str:
    data_folder = _output_root(output_folder)   # always use _output_root()
    filepath    = os.path.join(data_folder, filename)
    file_exists = os.path.exists(filepath)

    with open(filepath, "w", newline="", encoding="utf-8") as f:  # "w" = per-submission
        writer = csv.DictWriter(f, fieldnames=schema)
        writer.writeheader()
        writer.writerows(rows)

    return filepath
```

> Always use `_output_root(output_folder)` — never construct the path manually. This guarantees outputs land in `submission_tool_auto_outputs/`.

### Step 3 — Import both functions in `main.py`

```python
from claude_caller import (
    ...
    build_vessels_csv_rows,
    save_vessels_csv,
)
```

### Step 4 — Call in the save button block inside `render_results()`

```python
# Save vessels CSV — gated on skill code (see section 12)
vessels_path = ""
if skill.get("code") == "MAR":
    try:
        _v_rows, _v_schema = build_vessels_csv_rows(extracted)
        if _v_rows:
            vessels_path = save_vessels_csv(_v_rows, _v_schema, output_folder)
    except Exception as e:
        st.warning(f"Vessels CSV save error: {e}")

if vessels_path:
    st.success(f"✅ Vessels CSV saved:\n`{vessels_path}`")
```

### Step 5 — Hook into the batch runner (see section 13)

---

## 12. Skill-Specific CSV Gating

When a CSV output only applies to one skill, gate it on `skill.get("code")`. This stops the builder running against extracted data from a different skill that won't have the required fields.

```python
# Correct — only runs for marine skill
if skill.get("code") == "MAR":
    build_vessels_csv_rows(extracted)

# Wrong — will run for every skill, producing empty or wrong output
build_vessels_csv_rows(extracted)
```

Current gating in the codebase:

| Trigger | What it saves |
|---------|--------------|
| `skill.get("code") == "PVQ"` | `triage_matrix.csv`, `triage_locations.csv` |
| `extracted.get("sov_locations") is not None` | `locations_data.csv` (PVT skill) |

The field-existence check used by PVT is an acceptable alternative to a code check — either pattern works. The code check is slightly cleaner when the CSV is truly unique to one skill.

---

## 13. Hooking into the Batch Runner

In batch mode, `run_batch()` auto-saves each submission without user interaction. Add your skill's CSV saves to the auto-save block inside `run_batch()`.

Find this section (search for `# Consolidated roll-up`):

```python
# Consolidated roll-up: append to parent/submission_tool_auto_outputs/
save_csv(csv_row, skill["csv_schema"], parent_folder, "submission_data_all")
if claims_rows:
    save_claims_csv(claims_rows, skill["claims_csv_schema"], parent_folder)

# Triage skill: append to triage_matrix.csv + triage_locations.csv at parent
if skill.get("code") == "PVQ":
    try:
        _tr = build_triage_row(extracted, gap, subfolder_path, skill["label"])
        save_triage_csv(_tr, parent_folder)
        _tl_rows, _tl_schema = build_triage_locations_rows(extracted)
        if _tl_rows:
            save_triage_locations_csv(_tl_rows, _tl_schema, parent_folder)
    except Exception:
        pass
```

Add your saves in the same pattern:

```python
# Marine skill: save vessel schedule per-submission and consolidated at parent
if skill.get("code") == "MAR":
    try:
        _v_rows, _v_schema = build_vessels_csv_rows(extracted)
        if _v_rows:
            save_vessels_csv(_v_rows, _v_schema, subfolder_path)          # per-submission
            save_vessels_csv(_v_rows, _v_schema, parent_folder,           # consolidated
                             filename="vessels_data_all.csv")
    except Exception:
        pass  # always best-effort in batch
```

**Important:** Batch saves must always be wrapped in `try/except pass`. A save failure on one submission must never stop the rest of the batch.

---

## 14. The Triage Skill Pattern

`terror_quick.py` (code `PVQ`) is the reference implementation for a lightweight fast-triage variant. Key differences from a full skill:

| Aspect | Full skill | Triage skill |
|--------|-----------|-------------|
| Field count | 100–152 | ~25–42 |
| `CLAIMS_SCHEMA` | Defined | `[]` — not needed |
| Extra fields | None | `triage_recommendation`, `triage_rationale` |
| Custom CSVs | None | `triage_matrix.csv`, `triage_locations.csv` |
| CSV mode | Append | Append — accumulates across all runs |
| System prompt | Exhaustive | "Do NOT attempt exhaustive extraction" |
| Max tokens | 4096 | 1200–1500 |

The triage CSV functions in `claude_caller.py` are:

| Function | Purpose |
|----------|---------|
| `TRIAGE_SCHEMA` | Schema constant for `triage_matrix.csv` columns |
| `build_triage_row()` | One row per submission — includes derived rate metrics and flag summary |
| `save_triage_csv()` | Appends to `triage_matrix.csv` |
| `build_triage_locations_rows()` | Lightweight per-location rows (simpler than full SOV schema) |
| `save_triage_locations_csv()` | Appends to `triage_locations.csv` |

To create a triage variant for another class (e.g. Property Quick):
1. Copy `terror_quick.py`, rename, set unique `META["code"]` (e.g. `PRQ`)
2. Reduce `OUTPUT_SCHEMA` to ~25 critical triage fields
3. Keep `triage_recommendation` and `triage_rationale` fields
4. Set `CLAIMS_SCHEMA = []`
5. Add a new schema constant and builder/saver functions in `claude_caller.py`
6. Gate saves on the new code in `render_results()` and `run_batch()`
7. Import the new functions in `main.py`

---

## 15. The System Prompt

The system prompt has three jobs:

1. **Frame the role** — who Claude is, what class of business, what expertise to apply
2. **Explain the thinking** — reconciliation rules, red flag criteria, sense checks
3. **Define the JSON structure** — the exact JSON template Claude must return

### Critical rules

**JSON keys must exactly match `OUTPUT_SCHEMA` keys.** Keys present in the JSON but absent from `OUTPUT_SCHEMA` are extracted but silently ignored. Keys in `OUTPUT_SCHEMA` but absent from the JSON will be null.

**Array fields need their sub-structure defined in the prompt:**

```python
# In OUTPUT_SCHEMA:
O("loss_history", "Loss History", FieldType.ARRAY, FieldSource.EXTRACTED,
  FieldSection.LOSS, in_csv=False)

# In SYSTEM_PROMPT JSON template — sub-keys are NOT in OUTPUT_SCHEMA:
"loss_history": [
  {
    "year": null,
    "premium": null,
    "losses_paid": null,
    "losses_total_incurred": null,
    "claims_count": null,
    "notes": null
  }
]
```

**Always end with the full JSON template:**
```
Return this exact JSON structure:

{
  "field_one": null,
  "field_two": null,
  ...
}
```

**Standard analytics fields — include in every skill:**
```json
"uw_analyst_flags":      [],
"data_conflicts":        [],
"questions_for_broker":  [],
"extraction_confidence": "High / Medium / Low",
"extraction_notes":      null
```

**For triage skills — add speed instructions:**
```
Do NOT attempt exhaustive extraction. Focus only on the fields below.
Keep flags brief — maximum 5. Return ONLY valid JSON, no preamble.
```

---

## 16. build_csv_row — Safety Rules

`build_csv_row()` in `claude_caller.py` is fully generic — it iterates the active skill's `csv_schema` and writes any matching key from `extracted`. You do not need to edit it when adding a new skill.

However, there are a small number of hardcoded derived calculations (rate metrics, gap counts, flag counts) that write named keys directly. These are **all guarded** with `if "field_name" in row:` to prevent `dict contains fields not in fieldnames` errors when a skill doesn't have that column.

If you add a new derived calculation that writes a named key, always use this pattern:

```python
# Correct — safe for all skills
if "rate_on_line_pct" in row and not row.get("rate_on_line_pct"):
    try:
        gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
        limit = float(_parse_amount(extracted.get("limit_aoo", "")))
        if limit > 0:
            row["rate_on_line_pct"] = f"{round(gross / limit * 100, 4)}%"
    except (ValueError, TypeError):
        pass

# Wrong — will raise 'dict contains fields not in fieldnames' for any skill
# that doesn't include rate_on_line_pct in OUTPUT_SCHEMA
row["rate_on_line_pct"] = f"{round(gross / limit * 100, 4)}%"
```

The same `if "key" in row:` guard applies to:
- Gap counts (`critical_gaps_count`, `advisory_gaps_count`)
- Flag counts (`large_losses_flagged`)
- Any other hardcoded post-extraction write

**The rule:** if you're writing a key that is not guaranteed to exist in every skill's schema, guard it.

---

## 17. Full Checklist

### Skill file (`skills/your_skill.py`)
- [ ] Class name is unique (e.g. `MarineSkill`)
- [ ] `META["code"]` is unique (2–5 uppercase letters)
- [ ] `META["label"]` is the dropdown string
- [ ] Every field in `OUTPUT_SCHEMA` has a unique `key`
- [ ] Array fields not needed as CSV columns have `in_csv=False`
- [ ] Derived fields have `source=FieldSource.DERIVED` and `gap_check=False`
- [ ] Standard analytics fields included: `uw_analyst_flags`, `data_conflicts`, `questions_for_broker`
- [ ] `SYSTEM_PROMPT` JSON template keys match `OUTPUT_SCHEMA` keys exactly
- [ ] `CLAIMS_SCHEMA` defined (or `[]` if no claims CSV needed)
- [ ] File saved in `skills/` folder

### New FieldSection (only if needed)
- [ ] Enum value added to `FieldSection` in `base.py`
- [ ] Default icon added to `default_icons` in `tab_config()` in `base.py`

### Custom tab renderer (only if needed)
- [ ] `elif _tc.section == FieldSection.YOUR_SECTION:` block added inside `render_results()` in `main.py`
- [ ] Placed before the final `else:` default renderer
- [ ] Arrays filtered: `[x for x in (extracted.get("key") or []) if isinstance(x, dict)]`
- [ ] Empty columns dropped: `.loc[:, (df != "").any(axis=0)]`

### New skill-specific CSV output (only if needed)
- [ ] Schema constant (`YOUR_SCHEMA = [...]`) added near top of `claude_caller.py`
- [ ] Builder function `build_X_rows()` added to `claude_caller.py` — starts with `{col: "" for col in SCHEMA}` row initialisation
- [ ] Saver function `save_X_csv()` added to `claude_caller.py` — uses `_output_root(output_folder)`
- [ ] Correct open mode: `"w"` for per-submission files, `"a"` for cumulative/portfolio files
- [ ] Both functions imported in `main.py`
- [ ] Save call added in `render_results()` save button block, gated on `skill.get("code") == "XXX"`, wrapped in `try/except`
- [ ] Save call also added in `run_batch()` auto-save block, gated on code, wrapped in `try/except pass`

### Verification
- [ ] `python3 -c "import ast; ast.parse(open('skills/your_skill.py').read()); print('OK')"` — no syntax errors
- [ ] Restart app — new skill appears in dropdown
- [ ] Run a test submission — Raw JSON tab shows expected structure
- [ ] `schema_doc()` in Raw JSON tab shows correct field count and CSV column list
- [ ] Save outputs — no `dict contains fields not in fieldnames` errors
- [ ] Run in batch mode — all submissions complete, no save errors in progress log