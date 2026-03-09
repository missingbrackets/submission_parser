# Submission Analyser — Adding Skills

This document explains how to add a new class of business skill, add custom tabs, and add new table/CSV outputs.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Quick Start — Adding a New Skill](#2-quick-start)
3. [The Four Required Sections](#3-the-four-required-sections)
4. [OutputField Reference](#4-outputfield-reference)
5. [FieldSection — Sections and Tabs](#5-fieldsection--sections-and-tabs)
6. [Adding a New FieldSection (New Tab Type)](#6-adding-a-new-fieldsection)
7. [Adding a Custom Tab Renderer](#7-adding-a-custom-tab-renderer)
8. [Adding a New CSV Output](#8-adding-a-new-csv-output)
9. [The System Prompt](#9-the-system-prompt)
10. [Checklist](#10-checklist)

---

## 1. Architecture Overview

```
skills/
  base.py          ← FieldType, FieldSource, FieldSection enums
                     OutputField dataclass
                     TabConfig dataclass
                     BaseSkill base class (all logic lives here)
  __init__.py      ← Auto-discovery registry (never needs editing)
  casualty.py      ← Casualty Liability skill
  terror.py        ← Political Violence & Terrorism skill
  _template.py     ← Copy this to start a new skill
  your_new.py      ← Drop here — auto-registers immediately

main.py            ← Streamlit UI — reads skill config at runtime
claude_caller.py   ← Claude API call, gap analysis, CSV builders
```

**The key principle:** `OUTPUT_SCHEMA` is the single source of truth.

When you define a field in `OUTPUT_SCHEMA`, the framework automatically:
- Adds it to the submission CSV columns (`in_csv=True`)
- Shows it in the summary report (`in_summary=True`)
- Includes it in gap analysis (`gap_check=True`)
- Flags it as RED or AMBER if missing (`critical=True/False`)

You only write code in three places:
1. The skill file — defines what to extract and how to think
2. `base.py` — only if you need a new `FieldSection` (new tab type)
3. `main.py` — only if you need a custom tab renderer or new CSV output

---

## 2. Quick Start

**Step 1 — Copy the template**
```
skills/_template.py  →  skills/property.py   (or marine.py, space.py etc.)
```

**Step 2 — Fill in the four sections** (see section 3 below)

**Step 3 — Done.** Restart the app. Your skill appears in the dropdown.

No other files need editing for a standard skill.

---

## 3. The Four Required Sections

Every skill file defines a class that inherits `BaseSkill` and sets four class-level attributes.

```python
from skills.base import BaseSkill, OutputField, TabConfig, FieldType, FieldSource, FieldSection

O = OutputField   # shorthand

class PropertySkill(BaseSkill):

    # ── 1. META ───────────────────────────────────────
    META = {
        "label":       "Property All Risks",   # shown in dropdown
        "code":        "PAR",                  # short unique ID
        "version":     "1.0",
        "description": "London Market property all risks.",
    }

    # ── 2. TABS ───────────────────────────────────────
    # Controls which tabs appear and their default state.
    # Omit TABS entirely to auto-generate from OUTPUT_SCHEMA sections.
    TABS = [
        TabConfig(FieldSection.INSURED,   icon="🏢", default_on=True,  description="Insured details"),
        TabConfig(FieldSection.POLICY,    icon="📄", default_on=True,  description="Policy structure"),
        TabConfig(FieldSection.LIMITS,    icon="🔢", default_on=True,  description="Limits and deductibles"),
        TabConfig(FieldSection.PREMIUM,   icon="💷", default_on=True,  description="Premium and rating"),
        TabConfig(FieldSection.LOSS,      icon="📉", default_on=True,  description="Loss history"),
        TabConfig(FieldSection.FLAGS,     icon="⚠️", default_on=True,  description="Risk flags"),
        TabConfig(FieldSection.ANALYTICS, icon="🚩", default_on=True,  description="UW analyst flags"),
    ]

    # ── 3. CLAIMS_SCHEMA ──────────────────────────────
    # Flat list of column names for the claims CSV.
    CLAIMS_SCHEMA = [
        "Segment_1", "Segment_2", "underwriting_year", "claim_id",
        "accident_date", "reported_date", "insured", "location",
        "peril", "claim_description", "status",
        "paid", "outstanding", "incurred", "Manual Claim Adjustments",
    ]

    # ── 4. OUTPUT_SCHEMA ──────────────────────────────
    # One OutputField per field this skill produces.
    OUTPUT_SCHEMA = [
        O("insured_name",        "Insured Name",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("annual_revenue",      "Annual Revenue",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("premium_sought_gross","Premium Sought",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=True),
        # ... etc
    ]

    # ── 5. SYSTEM_PROMPT ──────────────────────────────
    SYSTEM_PROMPT = """..."""
```

---

## 4. OutputField Reference

```python
OutputField(
    key         = "field_json_key",     # must match JSON key Claude returns
    label       = "Human Label",        # shown in UI, reports, gap analysis
    field_type  = FieldType.TEXT,       # see types below
    source      = FieldSource.EXTRACTED,# EXTRACTED / DERIVED / METADATA
    section     = FieldSection.INSURED, # which tab this field belongs to
    in_csv      = True,                 # include as CSV column
    in_summary  = True,                 # include in summary report and tab display
    critical    = False,                # True = RED gap flag if missing
    gap_check   = True,                 # False = exclude from gap analysis entirely
    description = "Tooltip text",       # shown in schema doc and tooltips
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
| `YESNO` | Fields that should be Y / N / Unknown |
| `BOOLEAN` | True/false flags |
| `ARRAY` | Lists — loss history, SOV locations, UW flags etc. |
| `DERIVED` | Calculated fields — set `source=FieldSource.DERIVED` too |

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

# Currency with companion currency field
O("premium_sought_gross", "Premium Sought", FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM, critical=True)
O("premium_currency",     "Currency",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM, critical=False, gap_check=False)

# Y/N flag
O("coverage_gl", "General Liability", FieldType.YESNO, FieldSource.EXTRACTED, FieldSection.COVERAGE, critical=False)

# Array — appears in summary tab only, not as a CSV column
O("loss_history", "Loss History", FieldType.ARRAY, FieldSource.EXTRACTED, FieldSection.LOSS, critical=True, in_csv=False)

# Derived field — calculated post-extraction, not gap-checked
O("rate_on_line_pct", "Rate on Line %", FieldType.PERCENT, FieldSource.DERIVED, FieldSection.PREMIUM, critical=False, gap_check=False)

# CSV-only field (flattened from array) — not shown in summary tab
O("loss_yr1_year", "Loss Yr1 Year", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False)

# Analytics arrays — never in CSV, never gap-checked
O("uw_analyst_flags", "UW Analyst Flags", FieldType.ARRAY, FieldSource.EXTRACTED, FieldSection.ANALYTICS, in_csv=False, gap_check=False)
```

---

## 5. FieldSection — Sections and Tabs

Each `FieldSection` value becomes a potential tab. Sections are defined in `base.py`.

### Existing sections

| Enum value | Display name | Default icon | Notes |
|------------|-------------|--------------|-------|
| `INSURED` | Insured & Exposure | 🏢 | Identity, revenue, employees |
| `POLICY` | Policy Structure | 📄 | Period, trigger, jurisdiction |
| `LIMITS` | Limits & Structure | 🔢 | Limits, excess, deductible |
| `COVERAGE` | Coverage Lines | 🏷 | Y/N coverage flags — gets icon renderer |
| `PREMIUM` | Premium Analytics | 💷 | Premium, brokerage, rate metrics |
| `LOSS` | Loss History | 📉 | Gets custom table renderer |
| `FLAGS` | Risk Flags | ⚠️ | Litigation, declinatures |
| `ANALYTICS` | Underwriter Analytics | 🚩 | UW flags, conflicts, questions — gets custom renderer |
| `LOCATIONS` | Locations & SOV | 📍 | SOV table renderer (terror/PV) |
| `PERILS` | Peril Structure | 💥 | Y/N peril flags |
| `BI_EXT` | BI & Extensions | 🔄 | BI, ICOW, extensions |
| `GEO` | Geopolitical Assessment | 🌍 | Country risk, sanctions |
| `RATER` | Rater Inputs | 🧮 | Structured rater input card renderer |
| `META` | Metadata | ℹ️ | Extraction date, folder etc. |

Sections without any `in_summary=True` fields are never shown as tabs.

---

## 6. Adding a New FieldSection

If none of the existing sections fit your new class, add a new one to `base.py`.

**Step 1 — Add the enum value in `base.py`:**

```python
class FieldSection(Enum):
    # ... existing values ...
    MARINE      = "Marine & Cargo"       # ← add here
```

**Step 2 — Add the default icon in `tab_config()` in `base.py`:**

```python
default_icons = {
    # ... existing entries ...
    FieldSection.MARINE:    "⚓",        # ← add here
}
```

**Step 3 — Use it in your skill's `OUTPUT_SCHEMA`:**

```python
O("vessel_name", "Vessel Name", FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.MARINE, critical=True)
```

That's all that's needed for the **default key-value renderer**. The app will automatically show your new section as a two-column field grid.

If you want a **custom renderer** for the new section (e.g. a table, a map, a card layout), see section 7.

---

## 7. Adding a Custom Tab Renderer

The app (`main.py`) has a chain of `if / elif` checks in the tab rendering loop. Sections not matched by any `elif` fall through to the **default renderer** — a two-column key-value grid.

**The rendering loop lives here in `main.py`:**

```python
for _i, _tc in enumerate(_active_tabs):
    with _tabs[_i]:
        _section_fields = [
            f for f in skill["output_schema"]
            if f.section == _tc.section and f.in_summary
        ]

        if _tc.section == FieldSection.LOSS:
            # custom loss history table renderer
            ...

        elif _tc.section == FieldSection.ANALYTICS:
            # custom UW flags renderer
            ...

        elif _tc.section == FieldSection.LOCATIONS:
            # custom SOV table renderer
            ...

        elif _tc.section == FieldSection.RATER:
            # custom rater input card renderer
            ...

        # ← ADD YOUR NEW RENDERER HERE as elif

        else:
            # default: two-column key-value grid (works for most sections)
            ...
```

### Example — adding a custom renderer for a new MARINE section

Add this `elif` block before the final `else:`:

```python
elif _tc.section == FieldSection.MARINE:
    import pandas as pd

    vessels = extracted.get("vessel_schedule") or []
    valid_vessels = [v for v in vessels if isinstance(v, dict)]

    if valid_vessels:
        _vessel_rows = []
        for v in valid_vessels:
            _vessel_rows.append({
                "Vessel":       v.get("vessel_name", ""),
                "Flag":         v.get("flag", ""),
                "IMO":          v.get("imo_number", ""),
                "Type":         v.get("vessel_type", ""),
                "Year Built":   v.get("year_built", ""),
                "Gross Tons":   v.get("gross_tonnage", ""),
                "Value":        v.get("insured_value", ""),
            })
        st.dataframe(pd.DataFrame(_vessel_rows), use_container_width=True, hide_index=True)
    else:
        st.warning("No vessel schedule extracted.")

    # Render remaining scalar fields normally
    _scalar = [f for f in _section_fields if f.field_type != FieldType.ARRAY]
    # ... render as key-value pairs
```

### When do you need a custom renderer?

| Situation | What to do |
|-----------|-----------|
| Section contains only scalar fields | Use default renderer — no custom code needed |
| Section contains an `ARRAY` field you want to show as a table | Add custom renderer |
| Section needs summary metrics (metric cards) | Add custom renderer |
| Section has Y/N flags that should show icons | Use `FieldSection.COVERAGE` (already has icon renderer) or add custom |
| Section needs conditional colouring (e.g. RED if value present) | Add custom renderer |

---

## 8. Adding a New CSV Output

The app currently produces up to four CSV files:

| File | Description | Behaviour |
|------|-------------|-----------|
| `submission_data.csv` | One row per submission | Appends each run |
| `claims_data.csv` | One row per loss year / large loss | Appends each run |
| `locations_data.csv` | One row per SOV location | Overwrites each run |
| `YYYYMMDD_AI_Summary.txt` | Full text summary report | Overwrites each run |

To add a new CSV type (e.g. a vessel schedule for Marine), you need three things:

### Step 1 — Add a builder function in `claude_caller.py`

Follow this pattern:

```python
def build_vessels_csv_rows(extracted: dict) -> tuple:
    """
    Returns (rows, schema) where rows is a list of dicts
    and schema is the list of column names.
    """
    VESSEL_SCHEMA = [
        "insured_name", "policy_period_start",
        "vessel_id", "vessel_name", "flag", "imo_number",
        "vessel_type", "year_built", "gross_tonnage",
        "insured_value", "currency", "notes",
    ]

    rows    = []
    insured = _safe(extracted.get("insured_name"))
    policy  = _safe(extracted.get("policy_period_start"))

    vessels = extracted.get("vessel_schedule") or []
    for i, v in enumerate(vessels):
        if not isinstance(v, dict):
            continue
        row = {col: "" for col in VESSEL_SCHEMA}
        row["insured_name"]      = insured
        row["policy_period_start"] = policy
        row["vessel_id"]         = f"VES-{str(i+1).zfill(3)}"
        row["vessel_name"]       = _safe(v.get("vessel_name"))
        row["flag"]              = _safe(v.get("flag"))
        row["imo_number"]        = _safe(v.get("imo_number"))
        row["vessel_type"]       = _safe(v.get("vessel_type"))
        row["year_built"]        = _safe(v.get("year_built"))
        row["gross_tonnage"]     = _safe(v.get("gross_tonnage"))
        row["insured_value"]     = _safe(v.get("insured_value"))
        row["currency"]          = _safe(v.get("currency"))
        row["notes"]             = _safe(v.get("notes"))
        rows.append(row)

    return rows, VESSEL_SCHEMA


def save_vessels_csv(rows, schema, output_folder, filename="vessels_data.csv"):
    data_folder = os.path.join(output_folder, "02_data")
    os.makedirs(data_folder, exist_ok=True)
    filepath = os.path.join(data_folder, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:  # "w" = overwrite
        writer = csv.DictWriter(f, fieldnames=schema)
        writer.writeheader()
        writer.writerows(rows)

    return filepath
```

> **Append vs overwrite:** Use `"a"` (append) for cumulative files like claims that grow across submissions. Use `"w"` (overwrite) for per-submission files like locations or vessel schedules.

### Step 2 — Import the functions in `main.py`

```python
from claude_caller import (
    ...
    build_vessels_csv_rows,   # ← add
    save_vessels_csv,          # ← add
)
```

### Step 3 — Call them in the save button block in `main.py`

Find the save button section and add:

```python
# Save vessels CSV (marine skill)
vessels_path = ""
if extracted.get("vessel_schedule"):
    try:
        _ves_rows, _ves_schema = build_vessels_csv_rows(extracted)
        if _ves_rows:
            vessels_path = save_vessels_csv(
                rows=_ves_rows,
                schema=_ves_schema,
                output_folder=folder_path,
            )
    except Exception:
        pass  # best-effort

if vessels_path:
    st.success(f"✅ Vessels CSV saved:\n`{vessels_path}`")
```

The `try/except` with `pass` is intentional — additional CSV outputs are best-effort and should never prevent the main summary and submission CSV from saving.

---

## 9. The System Prompt

The system prompt is the most important part of the skill. It has three jobs:

1. **Frame the role** — tell Claude what class of business it's working on and what expertise to apply
2. **Explain the thinking** — reconciliation rules, red flags to raise, sense checks to apply
3. **Define the JSON structure** — the exact JSON Claude must return, matching `OUTPUT_SCHEMA` keys

### Key rules for the system prompt

**The JSON structure must exactly match `OUTPUT_SCHEMA`**

Every key in the JSON template must have a corresponding `OutputField` in `OUTPUT_SCHEMA` with the same `key` value. Keys present in the JSON but absent from `OUTPUT_SCHEMA` will be extracted but silently ignored by the CSV builder.

**Array fields need their own sub-structure**

```python
# In OUTPUT_SCHEMA:
O("loss_history", "Loss History", FieldType.ARRAY, FieldSource.EXTRACTED, FieldSection.LOSS, in_csv=False)

# In SYSTEM_PROMPT JSON template:
"loss_history": [
  {
    "year": null,
    "premium": null,
    "losses_paid": null,
    "losses_outstanding": null,
    "losses_total_incurred": null,
    "claims_count": null,
    "notes": null
  }
]
```

The sub-keys of array items are not in `OUTPUT_SCHEMA` — they are handled by custom renderers and CSV builders.

**Always end the prompt with the exact JSON structure**

```
Return this exact JSON structure:

{
  "field_one": null,
  "field_two": null,
  ...
}
```

Claude will reliably follow a concrete template. Vague instructions produce inconsistent structures.

**Standard analytics fields to always include**

Every skill should include these at the end of the JSON template — they are used by the standard UW flags renderer:

```json
"data_conflicts": [],
"uw_analyst_flags": [],
"questions_for_broker": [],
"extraction_confidence": "High / Medium / Low",
"extraction_notes": null
```

---

## 10. Checklist

Use this when adding a new skill:

### Skill file (`skills/your_skill.py`)
- [ ] Class name is unique (e.g. `PropertySkill`)
- [ ] `META["code"]` is unique (2–5 uppercase letters)
- [ ] `META["label"]` is the string that appears in the dropdown
- [ ] Every field in `OUTPUT_SCHEMA` has a unique `key`
- [ ] Array fields that shouldn't appear as CSV columns have `in_csv=False`
- [ ] Derived / calculated fields have `source=FieldSource.DERIVED` and `gap_check=False`
- [ ] Standard analytics fields are in `OUTPUT_SCHEMA` (`uw_analyst_flags`, `data_conflicts`, `questions_for_broker`)
- [ ] `SYSTEM_PROMPT` JSON template keys match `OUTPUT_SCHEMA` keys
- [ ] `CLAIMS_SCHEMA` columns are defined if the class has loss history
- [ ] File saved in `skills/` folder

### New FieldSection (only if needed)
- [ ] Enum value added to `FieldSection` in `base.py`
- [ ] Default icon added to `default_icons` dict in `tab_config()` in `base.py`

### Custom tab renderer (only if needed)
- [ ] `elif _tc.section == FieldSection.YOUR_SECTION:` block added in `main.py`
- [ ] Block placed before the final `else:` default renderer
- [ ] Empty columns dropped from dataframes (`.loc[:, (df != "").any(axis=0)]`)
- [ ] Array fields filtered with `isinstance(item, dict)` before `.get()` calls

### New CSV output (only if needed)
- [ ] Builder function `build_X_csv_rows()` added to `claude_caller.py`
- [ ] Saver function `save_X_csv()` added to `claude_caller.py`
- [ ] Both functions imported in `main.py`
- [ ] Save call added inside the save button block in `main.py` wrapped in `try/except`
- [ ] Correct open mode: `"w"` for per-submission files, `"a"` for cumulative files

### Verification
- [ ] Run `python3 -c "import ast; ast.parse(open('skills/your_skill.py').read()); print('OK')"` — no syntax errors
- [ ] Restart app — new skill appears in dropdown
- [ ] Run a test submission — check Raw JSON tab shows expected structure
- [ ] Check `schema_doc()` output in Raw JSON tab matches expectations