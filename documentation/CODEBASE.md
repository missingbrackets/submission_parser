# Submission Analyser — Codebase Reference

> Developer documentation for understanding, maintaining, and extending the Submission Analyser application.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Directory Structure](#2-directory-structure)
3. [Architecture Overview](#3-architecture-overview)
4. [Key Architectural Decisions](#4-key-architectural-decisions)
5. [Module Reference](#5-module-reference)
6. [Data Structures](#6-data-structures)
7. [Data Flow: Single Submission](#7-data-flow-single-submission)
8. [Data Flow: Batch Mode](#8-data-flow-batch-mode)
9. [Skill Resolution Flow](#9-skill-resolution-flow)
10. [CSV Output Pipeline](#10-csv-output-pipeline)
11. [Streamlit Session State](#11-streamlit-session-state)
12. [Adding a New Skill](#12-adding-a-new-skill)
13. [Extension Points](#13-extension-points)
14. [Dependencies](#14-dependencies)

---

## 1. Project Overview

Submission Analyser is a Streamlit application that ingests London Market insurance broker submissions (PDFs, Word documents, Excel spreadsheets, Outlook `.msg` emails), sends the extracted text to the Claude API (Anthropic) for structured data extraction, performs gap analysis against a configurable field checklist, and saves results to CSV files and a plain-text summary report.

The application supports multiple classes of business ("skills"), each defining its own field schema, system prompt, and CSV output structure. Skills are auto-discovered at startup and can be customised non-destructively via JSON sidecar configuration files.

---

## 2. Directory Structure

```
submission_parser/
  main.py                    Entry point (29 lines) — st.navigation() setup
  claude_caller.py           Backward-compatibility shim (re-exports from core/)
  file_parser.py             File text extraction (PDF, Excel, Word, MSG, text)
  requirements.txt           Python dependencies
  Launch_Analyser.bat        Windows launcher script

  core/                      Pure Python — zero Streamlit dependencies
    __init__.py              Re-exports full public API
    extractor.py             Claude API call + low-level value helpers
    analysis.py              Gap analysis logic
    outputs.py               CSV schemas, row builders, file savers
    report.py                Plain-text summary report builder
    processor.py             Orchestration layer with callback pattern

  ui/                        All Streamlit-dependent code
    styles.py                APP_CSS and EDITOR_CSS string constants
    components/
      gap_analysis.py        render_gap_analysis(gap) component
      data_tabs.py           render_data_tabs() + render_save_section()
    pages/
      analyser.py            analyser_page() — main analysis UI
      skill_editor.py        skill_editor_page() — Skill Viewer

  skills/                    Skill definitions and registry
    __init__.py              Auto-discovery registry + public API
    base.py                  FieldType, FieldSource, FieldSection enums;
                             OutputField, TabConfig dataclasses; BaseSkill ABC
    config_loader.py         JSON sidecar config system
    casualty.py              Casualty Liability skill
    terror.py                Political Violence & Terrorism skill
    terror_quick.py          PV Triage (Quick) skill (code: PVQ)
    pv_direct_triage.py      PV Direct Triage skill (code: PVDT)
    template.py              Blank skill template for new skills
    config/                  JSON sidecar files — one per skill code (gitignored)

  pages/
    1_Skill_Editor.py        Thin wrapper — calls skill_editor_page()

  documentation/
    adding_skills.md         Full developer guide for adding new skills
    CODEBASE.md              This file
```

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  main.py  (entry point)                                         │
│  st.set_page_config() — called ONCE here                        │
│  st.navigation([analyser_page, skill_editor_page])              │
└────────────────────┬───────────────────────────────────────────-┘
                     │
         ┌───────────┴────────────┐
         │                        │
┌────────▼────────┐      ┌────────▼──────────┐
│ ui/pages/       │      │ ui/pages/          │
│ analyser.py     │      │ skill_editor.py    │
│ analyser_page() │      │ skill_editor_page()│
└────────┬────────┘      └────────┬──────────┘
         │                        │
         │  uses                  │  reads
         ▼                        ▼
┌────────────────┐      ┌─────────────────────┐
│ ui/components/ │      │ skills/             │
│  gap_analysis  │      │  __init__.py        │
│  data_tabs     │      │  base.py            │
│  (Streamlit)   │      │  *.py skill files   │
└────────┬───────┘      │  config_loader.py   │
         │              │  config/*.json      │
         │  calls       └─────────┬───────────┘
         ▼                        │ get_skill()
┌─────────────────────────────────▼────────────┐
│  core/  (pure Python — no Streamlit imports) │
│                                              │
│  extractor.py   call_claude_extraction()     │
│  analysis.py    run_gap_analysis()           │
│  outputs.py     build_*/save_* functions     │
│  report.py      build_summary_text()         │
│  processor.py   process_submission()         │
│                 process_batch()              │
└─────────────────────────────────┬────────────┘
                                  │  calls
                                  ▼
                        ┌─────────────────┐
                        │  file_parser.py │
                        │  extract_file() │
                        │  extract_folder()│
                        └────────┬────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │  Anthropic Claude API │
                     │  (claude-sonnet-4-...)│
                     └───────────────────────┘
```

The key structural rule: **`core/` never imports from `ui/` or `streamlit`**. The `ui/` layer may import from `core/` and `skills/` freely.

---

## 4. Key Architectural Decisions

### 4.1 core/ separation

All business logic lives in `core/` with zero Streamlit dependencies. This is a deliberate boundary:

- `core/extractor.py` — Claude API call
- `core/analysis.py` — gap analysis
- `core/outputs.py` — CSV row construction and file I/O
- `core/report.py` — summary text assembly
- `core/processor.py` — orchestration

Any of these can be imported and called from a CLI script, FastAPI endpoint, Jupyter notebook, or test suite without a Streamlit installation. The `ui/` layer is a thin rendering skin on top.

### 4.2 Callback pattern in processor.py

`process_submission()` and `process_batch()` accept optional callbacks:

```python
def process_submission(
    folder_path: str,
    class_choice: str,
    api_key: str,
    use_corr: bool = True,
    use_data: bool = True,
    on_progress: Optional[Callable] = None,  # (pct: int, text: str)
    on_status: Optional[Callable] = None,    # (level: str, text: str)
) -> dict:
```

For batch mode:

```python
def process_batch(
    ...
    on_status: Optional[Callable] = None,    # (level: str, subfolder: str, text: str)
) -> dict:  # {subfolder_name: result_dict}
```

If the callbacks are `None`, a `_noop` function is substituted. This means the same orchestration code can be used from Streamlit (passing `st.progress` wrappers), a CLI (printing to stdout), or in tests (passing no callbacks at all).

Note: `ui/pages/analyser.py` currently implements its own inline batch loop rather than calling `process_batch()` directly, because the Streamlit UI needs fine-grained status widget updates. Both paths produce identical output files.

### 4.3 claude_caller.py as backward-compatibility shim

`claude_caller.py` at the package root is a re-export module. It existed as the original monolithic file before the `core/` refactor. It now simply imports and re-exports everything from `core/`:

```python
from core.extractor import call_claude_extraction, ...
from core.analysis import run_gap_analysis
from core.outputs import build_csv_row, save_csv, ...
from core.report import build_summary_text, save_summary_report
```

Any existing code or scripts that did `from claude_caller import run_gap_analysis` continue to work unchanged. New code should import from `core` directly.

### 4.4 Skill auto-discovery

`skills/__init__.py` scans the `skills/` directory at import time. Any `.py` file (excluding `__init__.py`, files starting with `_`, and `base.py`) that contains a class subclassing `BaseSkill` with a non-empty `META["code"]` is automatically registered.

The discovery logic:

```python
for fname in sorted(os.listdir(skills_dir)):
    if not fname.endswith(".py"):
        continue
    if fname.startswith("_") or fname == "base.py":
        continue
    module = importlib.import_module(f"skills.{fname[:-3]}")
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseSkill) and obj is not BaseSkill and obj.META.get("code"):
            _REGISTRY[obj.label()] = obj
```

To add a new skill: drop a `.py` file in `skills/`, subclass `BaseSkill`, set `META["code"]` to a unique short string. It will appear in the dropdown on the next restart with no other changes required.

### 4.5 JSON sidecar config

`skills/config/<CODE>.json` files layer on top of the Python skill definition without modifying it. The config system supports:

| Key | Purpose |
|-----|---------|
| `meta_overrides` | Override `label` or `description` for display |
| `field_overrides` | Per-field property overrides keyed by `OutputField.key` |
| `field_additions` | New `OutputField` entries appended to `OUTPUT_SCHEMA` |
| `csv_consolidation` | Which CSVs are rolled up in batch mode |
| `prompt_override` | Replacement system prompt string (null = use .py default) |

Sidecar files are excluded from git via `.gitignore` (the `skills/config/` directory). This keeps team-specific prompt tuning and field adjustments out of version control.

`apply_config(skill_cls, config)` in `skills/config_loader.py` merges the sidecar onto the base schema and returns a new skill dict. **The original class is never mutated.**

### 4.6 st.navigation() callable pattern

`main.py` uses Streamlit 1.44+ `st.navigation()`:

```python
st.set_page_config(...)   # Called exactly once here

from ui.pages.analyser import analyser_page
from ui.pages.skill_editor import skill_editor_page

pg = st.navigation([
    st.Page(analyser_page,     title="Submission Analyser", icon="📋"),
    st.Page(skill_editor_page, title="Skill Viewer",        icon="📖"),
])
pg.run()
```

Passing callables (not file paths) to `st.Page()` means:

- `set_page_config()` is called once in `main.py`, not inside each page function.
- Page modules are imported at startup, not lazily per-navigation. This ensures the skill registry is populated before the UI renders.
- `pages/1_Skill_Editor.py` exists as a thin wrapper for Streamlit's legacy multi-page file discovery, but the canonical entry point is always `main.py`.

---

## 5. Module Reference

### 5.1 main.py

Ultra-thin entry point. Sets page config, imports the two page callables, and calls `st.navigation()`. No logic of its own. 29 lines.

### 5.2 file_parser.py

Extracts raw text from submission documents. Stateless — no class, no session state.

**Public functions:**

```python
extract_file(filepath: str) -> tuple[str, str]
# Returns (extracted_text, status_message)
# Dispatches on file extension via EXTENSION_MAP

extract_folder(folder_path: str, subfolder: str = None) -> dict
# Returns {filename: {"text": str, "status": str, "path": str, "size_kb": float}}
# Iterates all supported files in target directory (non-recursive)
```

**Supported formats and extraction libraries:**

| Extension | Library | Notes |
|-----------|---------|-------|
| `.pdf` | `pdfplumber` | Extracts text per page + tables; labels `[Page N]` and `[TABLE]` |
| `.xlsx`, `.xlsm` | `openpyxl` | Each sheet labelled `[Sheet: name]`, pipe-delimited rows |
| `.xls` | `openpyxl` then `xlrd` fallback | `xlrd` used if `openpyxl` fails |
| `.docx`, `.doc` | `python-docx` | Body paragraphs + table cells |
| `.msg` | `extract-msg` | Subject, From, Date, body |
| `.txt`, `.csv` | built-in `open()` | UTF-8 with `errors="replace"` |

Files with unsupported extensions are silently skipped by `extract_folder()`. Each library is imported inside the function so a missing library produces a clear status message rather than an import error at startup.

### 5.3 claude_caller.py

Backward-compatibility shim. Imports and re-exports all public symbols from `core/`. See section 4.3.

### 5.4 core/extractor.py

**`call_claude_extraction(combined_text, system_prompt, api_key, max_tokens=4096)`**

Sends the combined submission text to `claude-sonnet-4-20250514`. The user message wraps the text between `=== SUBMISSION CONTENT START ===` and `=== SUBMISSION CONTENT END ===` markers and caps at 60,000 characters. The model is instructed to return pure JSON with no markdown fences.

Response parsing is fault-tolerant: if `json.loads()` fails, a regex fallback attempts to extract the first `{...}` block. If that also fails, an `extraction_error` key is placed in the returned dict.

Returns `(parsed_dict, raw_response_text)`. Callers should check for `"extraction_error"` in the returned dict.

**Helper functions:**

| Function | Purpose |
|----------|---------|
| `_safe(val)` | Returns string or `""`. Converts `bool` to `"Y"`/`"N"`. |
| `_parse_amount(val)` | Strips `£`, `$`, `€`, commas, whitespace. Returns numeric string. |
| `_output_root(case_folder)` | Returns/creates `<case_folder>/submission_tool_auto_outputs/` |

`AUTO_OUTPUT_DIR = "submission_tool_auto_outputs"` — the constant used throughout the codebase for the output subdirectory name.

### 5.5 core/analysis.py

**`run_gap_analysis(extracted: dict, required_fields: list) -> dict`**

Iterates `required_fields` (a list of `(key, label, is_critical)` tuples) and classifies each field as present, critical gap, or advisory gap.

Presence logic by value type:

- **list**: present if non-empty and at least one item has a non-`None` value
- **bool**: always present (both `True` and `False` are meaningful answers)
- **int / float**: always present
- **str / None**: absent if `None` or if the lowercased value is in `EMPTY_VALUES = {"", "null", "none", "unknown", "n/a", "not provided", "not stated"}`

Returns the `gap` dict (see section 6.2).

### 5.6 core/outputs.py

Defines all CSV schemas, row builder functions, and file saver functions. No Streamlit imports.

**Standard submission CSV:**

| Function | Description |
|----------|-------------|
| `build_csv_row(extracted, gap_analysis, csv_schema, source_folder, class_label)` | Assembles one CSV row dict. Handles special arrays (loss history → `loss_yrN_*` columns), derived fields (rate on line, rate on TIV, net premium, raw average loss ratio), and UW flag counts. |
| `save_csv(row, csv_schema, output_folder, filename_prefix)` | Appends row to `<output_folder>/submission_tool_auto_outputs/<prefix>.csv`. Creates file with header on first write. |

**Claims CSV:**

| Function | Description |
|----------|-------------|
| `build_claims_csv_rows(extracted, claims_csv_schema)` | Returns a list of row dicts: one per `loss_history` year entry + one per `large_losses` entry. |
| `save_claims_csv(rows, claims_csv_schema, output_folder, filename)` | Appends rows. |

**Locations CSV:**

| Function | Description |
|----------|-------------|
| `build_locations_csv_rows(extracted)` | If `sov_locations` contains dicts, returns one row per location. Otherwise returns a single aggregate row from top-level TIV fields. Returns `(rows, LOCATION_SCHEMA)`. |
| `save_locations_csv(rows, schema, output_folder, filename)` | **Overwrites** (not appends) — locations are per-submission, not cumulative. |

**PVQ triage CSV (skill code `PVQ` only):**

- `TRIAGE_SCHEMA` — 43-column schema constant
- `build_triage_row(extracted, gap_analysis, source_folder, class_label)` — builds one triage row including computed rate metrics and pipe-delimited flag strings
- `save_triage_csv(row, output_folder, filename)` — appends
- `build_triage_locations_rows(extracted)` / `save_triage_locations_csv(...)` — same location logic as above but for the triage-specific schema

**PVDT direct triage CSV (skill code `PVDT` only):**

- `DIRECT_TRIAGE_FLAG_FIELDS` — list of 8 RAG flag field keys
- `DIRECT_TRIAGE_SCHEMA` — 41-column schema including the 8 flag fields plus `n_red`, `n_amber`, `n_green` counts
- `build_direct_triage_row(extracted, gap_analysis, source_folder, class_label)` — builds row and counts RAG colours via `_rag_colour()`
- `save_direct_triage_csv(row, output_folder, filename)` — appends
- `_rag_colour(value)` — maps a flag string (may contain emoji `🔴`/`🟡`/`🟢` or text `RED`/`AMBER`/`GREEN`) to a canonical colour string

### 5.7 core/report.py

**`build_summary_text(extracted, gap_analysis, source_files, class_label, folder_name) -> str`**

Assembles a multi-section plain-text summary report. Sections: source files processed, risk summary, policy structure, limits, coverage lines, premium analytics, loss history table, large losses, risk flags, underwriter analyst flags, data conflicts, questions for broker, gap analysis.

The returned string is used both for file write (`save_summary_report()`) and for in-app display in the Summary tab of `render_data_tabs()`.

**`save_summary_report(extracted, gap_analysis, source_files, class_label, output_folder, folder_name) -> str`**

Calls `build_summary_text()` and writes to `<output_folder>/submission_tool_auto_outputs/YYYYMMDD_AI_Summary.txt`. Returns the file path.

### 5.8 core/processor.py

Orchestration layer. Imports nothing from Streamlit.

**`process_submission(folder_path, class_choice, api_key, use_corr, use_data, on_progress, on_status) -> dict`**

Reads files from `01_correspondence` and/or `02_data` subfolders, concatenates text, calls Claude, runs gap analysis. Returns:

```python
{
    "extracted":   dict,
    "gap":         dict,
    "all_files":   dict,
    "folder_path": str,
    "folder_name": str,
    "skill":       dict,
}
# or {"error": str} on failure
```

Progress callback fires at: 10% (reading), 30% (sending to Claude), 80% (gap analysis), 100% (complete).

**`save_submission_outputs(extracted, gap, all_files, folder_path, folder_name, skill, output_folder) -> dict`**

Saves all outputs for one submission. `output_folder` defaults to `folder_path`; in batch mode the parent folder is passed to consolidate CSVs. Returns `{output_type: filepath}` for successfully saved files. Skill-specific CSV branching (PVQ → triage, PVDT → direct triage) lives here.

**`process_batch(parent_folder, class_choice, api_key, use_corr, use_data, on_progress, on_status) -> dict`**

Discovers immediate subfolders of `parent_folder` (excluding hidden and `submission_tool_auto_outputs`), processes each as a submission. Writes per-submission outputs to each subfolder and a consolidated roll-up to `parent_folder/submission_tool_auto_outputs/submission_data_all.csv`. Returns `{subfolder_name: result_dict}`.

### 5.9 skills/base.py

Defines all skill abstractions. No runtime dependencies beyond standard library and `dataclasses`.

**Enums:**

| Enum | Values |
|------|--------|
| `FieldType` | `TEXT`, `NUMBER`, `CURRENCY`, `PERCENT`, `DATE`, `YESNO`, `ARRAY`, `BOOLEAN`, `DERIVED` |
| `FieldSource` | `EXTRACTED` (Claude extracts), `DERIVED` (post-processing), `METADATA` (app-set) |
| `FieldSection` | `INSURED`, `POLICY`, `LIMITS`, `COVERAGE`, `PREMIUM`, `LOSS`, `FLAGS`, `ANALYTICS`, `LOCATIONS`, `PERILS`, `BI_EXT`, `GEO`, `RATER`, `META` |

**`OutputField` dataclass:**

```python
@dataclass
class OutputField:
    key:         str            # JSON key returned by Claude / CSV column name
    label:       str            # Human label in UI and reports
    field_type:  FieldType      = FieldType.TEXT
    source:      FieldSource    = FieldSource.EXTRACTED
    section:     FieldSection   = FieldSection.META
    in_csv:      bool           = True   # include as CSV column
    in_summary:  bool           = True   # show in UI tabs and text report
    critical:    bool           = False  # True → red gap; False → amber gap
    gap_check:   bool           = True   # include in gap analysis
    description: str            = ""     # tooltip / developer note
```

**`TabConfig` dataclass:**

```python
@dataclass
class TabConfig:
    section:     FieldSection
    icon:        str   = "📋"
    default_on:  bool  = True
    description: str   = ""
```

**`BaseSkill` class methods (all `@classmethod`):**

| Method | Returns | Description |
|--------|---------|-------------|
| `label()` | `str` | Display name from `META["label"]` |
| `code()` | `str` | Short code from `META["code"]` |
| `version()` | `str` | Version string |
| `description()` | `str` | Description string |
| `required_fields()` | `list[tuple]` | `[(key, label, is_critical)]` for all `gap_check=True` + `EXTRACTED` fields |
| `csv_schema()` | `list[str]` | Ordered column names: metadata cols first, then all `in_csv=True` fields |
| `summary_sections()` | `dict` | `{FieldSection: [OutputField]}` for all `in_summary=True` fields |
| `tab_config()` | `list[TabConfig]` | Uses `TABS` class attribute if defined; otherwise auto-generates one tab per section |
| `fields_by_key()` | `dict` | `{key: OutputField}` lookup |
| `schema_doc()` | `str` | Human-readable schema table for developer reference |

**Subclass must define:**

```python
class MySkill(BaseSkill):
    META = {
        "label":       "My Skill Name",   # shown in dropdown
        "code":        "MYSK",            # unique short code
        "version":     "1.0",
        "description": "...",
    }
    OUTPUT_SCHEMA: list[OutputField] = [...]
    CLAIMS_SCHEMA: list[str]         = [...]   # column names for claims CSV
    SYSTEM_PROMPT: str               = "..."
```

### 5.10 skills/config_loader.py

Manages JSON sidecar config files in `skills/config/`.

**Key functions:**

| Function | Description |
|----------|-------------|
| `load_config(skill_code)` | Loads `skills/config/<CODE>.json`. Returns default skeleton if absent. |
| `save_config(skill_code, config)` | Writes config dict to JSON. |
| `delete_config(skill_code)` | Removes sidecar, reverting to `.py` defaults. |
| `has_config(skill_code)` | Returns `True` if sidecar exists. |
| `apply_config(skill_class, config) -> dict` | Merges overrides and additions onto base schema. Returns enriched skill dict. Does NOT mutate the class. |
| `field_to_dict(f: OutputField) -> dict` | Serialises an `OutputField` to plain dict for JSON round-trip. |

The `apply_config()` return value is the **skill dict** used everywhere in the codebase:

```python
{
    "label":             str,
    "code":              str,
    "version":           str,
    "description":       str,
    "required_fields":   [(key, label, is_critical), ...],
    "csv_schema":        [str, ...],
    "claims_csv_schema": [str, ...],
    "system_prompt":     str,
    "output_schema":     [OutputField, ...],
    "skill_class":       type,   # the BaseSkill subclass
    "config":            dict,   # raw sidecar (for editor use)
    "has_overrides":     bool,
}
```

### 5.11 skills/__init__.py

Public API for the skill system:

```python
available_classes() -> list[str]   # sorted skill labels for UI dropdown
get_skill_class(label) -> type     # the BaseSkill subclass
get_skill(label) -> dict           # full skill dict with sidecar applied
list_skills_doc() -> str           # schema docs for all registered skills
```

### 5.12 ui/styles.py

Two CSS string constants injected with `st.markdown(css, unsafe_allow_html=True)`:

- `APP_CSS` — used in `analyser.py`. Defines `.main-header`, `.gap-critical`, `.gap-advisory`, `.gap-ok`, `.field-row`, `.field-label`, `.field-value`, `.field-missing`, `.score-badge`.
- `EDITOR_CSS` — used in `skill_editor.py`. Defines `.main-header`, `.field-row`, `.badge-override`, `.badge-new`, `.badge-base`.

Both import DM Mono from Google Fonts.

### 5.13 ui/components/gap_analysis.py

**`render_gap_analysis(gap: dict) -> None`**

Renders a four-column row: a custom HTML score badge (green ≥ 75, amber ≥ 50, red below), plus three `st.metric` widgets for critical gaps, advisory gaps, and fields present. Below that, a two-column list of critical and advisory missing fields using `.gap-critical` and `.gap-advisory` CSS classes.

### 5.14 ui/components/data_tabs.py

**`render_data_tabs(extracted, gap, all_files, folder_name, skill) -> None`**

Builds a dynamic tab bar. Active tabs are those whose `FieldSection` is checked on in `st.session_state["tab_states"]`. Three fixed tabs are appended: Summary (calls `build_summary_text()` and renders it), Claims CSV (previews claims rows in a dataframe), Raw JSON (dumps `extracted` dict).

Section-specific renderers are called for special sections:

| Section | Renderer | Notes |
|---------|---------|-------|
| `LOCATIONS` | `_render_locations_tab` | Metrics row + SOV dataframe or aggregate warning |
| `RATER` | `_render_rater_tab` | Populated fields highlighted in blue; missing in expander |
| `LOSS` | `_render_loss_tab` | Loss history dataframe + large losses styled list |
| `ANALYTICS` | `_render_analytics_tab` | UW flags sorted by severity, data conflicts, questions |
| `COVERAGE` | `_render_coverage_tab` | YESNO fields as icon rows; notable features list |
| `FLAGS` | `_render_flags_tab` | Two-column layout; critical fields with non-null values highlighted red |
| All others | `_render_default_tab` | Two-column label/value rows using CSS `.field-row` |

**`render_save_section(extracted, gap, all_files, folder_path, folder_name, skill, output_folder) -> None`**

"Save Summary Report + CSV" button that calls `save_summary_report()`, `save_csv()`, `save_claims_csv()`, `save_locations_csv()`, and (based on `skill["code"]`) either `save_triage_csv()` or `save_direct_triage_csv()`. Each saved file path is displayed in a `st.success()` message. A "Preview CSV row" expander shows non-empty fields from the built CSV row.

### 5.15 ui/pages/analyser.py

Main analysis page. Entry point: `analyser_page()`.

**Sidebar controls:**

- API key (password input)
- Case folder path (text input)
- Class of business selectbox (populated from `available_classes()`)
- Subfolder checkboxes (`01_correspondence`, `02_data`)
- Batch mode toggle
- Tab display checkboxes (one per `TabConfig` from the selected skill)
- Run button

Tab states are written to `st.session_state["tab_states"]` on every render.

**Run flow:** button click sets `st.session_state["run_triggered"] = True`. On the next render, `_run_single()` or `_run_batch()` is called.

**`_run_single()`:** Reads files, builds `combined_text`, checks cache (`st.session_state["_cache_key"]`), calls Claude, runs gap analysis, calls `render_results()`.

**`_run_batch()`:** Iterates subfolders with a `st.progress()` bar, processes each, saves outputs to both the subfolder and parent folder, stores results in `st.session_state["batch_results"]`. After the loop, displays a summary dataframe and a selectbox to drill into individual results.

### 5.16 ui/pages/skill_editor.py

Read-only Skill Viewer page. Entry point: `skill_editor_page()`.

Three tabs:
1. **Output Schema** — filterable dataframe of all `OutputField` entries with section filter selectbox and summary metrics.
2. **CSV Outputs** — dataframes showing column lists for `submission_data.csv`, `claims_data.csv` (if present), and skill-specific triage CSVs.
3. **System Prompt** — displays the active prompt (override if sidecar exists, otherwise `.py` default). If both exist, shows them in sub-tabs.

---

## 6. Data Structures

### 6.1 extracted dict

Returned by `call_claude_extraction()`. Keys match `OutputField.key` values in the skill's `OUTPUT_SCHEMA`.

Scalar fields are strings (or occasionally numbers/booleans). Array fields are lists:

| Key | Type | Description |
|-----|------|-------------|
| `loss_history` | `list[dict]` | One dict per year: `year`, `premium`, `losses_paid`, `losses_outstanding`, `losses_total_incurred`, `claims_count`, `implied_loss_ratio_pct`, `large_loss_flag`, `development_warning`, `notes` |
| `large_losses` | `list[dict]` | One dict per large loss: `year`, `amount`, `description`, `status`, `reserved_adequacy_comment` |
| `sov_locations` | `list[dict]` | One dict per SOV location: `location_name`, `address`, `city`, `country`, `latitude`, `longitude`, `occupancy`, `construction`, `storeys`, `tiv`, `tiv_pd`, `tiv_bi`, `tiv_stock`, `currency`, `fire_protection`, `security_protection`, `peak_tiv_flag`, `notes` |
| `uw_analyst_flags` | `list[dict]` | One dict per flag: `severity` (RED/AMBER/INFO), `category`, `flag`, `detail` |
| `data_conflicts` | `list[dict]` | One dict per conflict: `field`, `value_a`, `source_a`, `value_b`, `source_b`, `resolution` |
| `questions_for_broker` | `list[str]` | Flat list of question strings |

### 6.2 gap dict

Returned by `run_gap_analysis()`:

```python
{
    "critical_gaps":      [(key, label), ...],   # missing critical fields
    "advisory_gaps":      [(key, label), ...],   # missing non-critical fields
    "present":            [(key, label), ...],   # present fields
    "data_quality_score": int,                   # 0–100
    "critical_count":     int,
    "advisory_count":     int,
    "present_count":      int,
    "total_fields":       int,
}
```

Score = `round(present_count / total_fields * 100)`. Display thresholds: ≥ 75 = GOOD (green), ≥ 50 = MODERATE (amber), < 50 = POOR (red).

### 6.3 skill dict

Returned by `get_skill(label)` (via `apply_config()`):

```python
{
    "label":             str,                          # display name
    "code":              str,                          # short code, e.g. "PVQ"
    "version":           str,
    "description":       str,
    "required_fields":   [(key, label, is_critical)],  # gap analysis input
    "csv_schema":        [str, ...],                   # ordered column names
    "claims_csv_schema": [str, ...],                   # claims CSV columns
    "system_prompt":     str,                          # prompt sent to Claude
    "output_schema":     [OutputField, ...],           # full field list
    "skill_class":       type,                         # BaseSkill subclass
    "config":            dict,                         # raw sidecar dict
    "has_overrides":     bool,                         # sidecar exists?
}
```

### 6.4 file_info dict

Values in the `all_files` dict returned by `extract_folder()`:

```python
{
    "text":    str,    # extracted text, may be empty string on failure
    "status":  str,    # human-readable status/error message
    "path":    str,    # absolute file path
    "size_kb": float,  # file size in KB
}
```

---

## 7. Data Flow: Single Submission

```
User: enters folder + API key + class → clicks Run Analysis
                        │
                        ▼
        _run_single() in ui/pages/analyser.py
                        │
          ┌─────────────┴─────────────┐
          │                           │
  extract_folder(path, "01_corr")  extract_folder(path, "02_data")
          │                           │
          └─────────────┬─────────────┘
                        │  all_files dict
                        ▼
     Concatenate texts → combined_text (capped at 60,000 chars)
                        │
                        ▼
     Check cache: st.session_state["extracted"] + "_cache_key"
     Hit → use cached; Miss → call Claude
                        │
                        ▼
     call_claude_extraction(combined_text, system_prompt, api_key)
         → (extracted dict, raw_text)
                        │
                        ▼
     run_gap_analysis(extracted, skill["required_fields"])
         → gap dict
                        │
                        ▼
     render_results(extracted, gap, all_files, ...)
         │
         ├── render_gap_analysis(gap)        — score card
         ├── render_data_tabs(...)           — tabbed extracted data
         └── render_save_section(...)        — save button
                                │
                          Save button click:
                          ├── save_summary_report() → YYYYMMDD_AI_Summary.txt
                          ├── save_csv()             → submission_data.csv
                          ├── save_claims_csv()      → claims_data.csv
                          ├── save_locations_csv()   → locations_data.csv
                          └── save_triage_csv()      → triage_matrix.csv  (PVQ)
                              save_direct_triage_csv()→ triage_direct.csv (PVDT)
```

All output files are written to `<folder_path>/submission_tool_auto_outputs/`.

---

## 8. Data Flow: Batch Mode

```
User: enters parent folder path → enables Multiple Submissions toggle → clicks Run Batch
                        │
                        ▼
         _run_batch() in ui/pages/analyser.py
                        │
                        ▼
     os.listdir(parent_folder) → sorted list of subfolders
     (skips hidden dirs and "submission_tool_auto_outputs")
                        │
                        ▼
     For each subfolder:
       ├── extract_folder(subfolder, "01_corr") + "02_data"
       ├── call_claude_extraction(combined_text, ...)
       ├── run_gap_analysis(extracted, ...)
       ├── save outputs to subfolder/submission_tool_auto_outputs/
       │     submission_data.csv, claims_data.csv, locations_data.csv,
       │     YYYYMMDD_AI_Summary.txt, triage CSVs (skill-dependent)
       └── append consolidated row to parent_folder/submission_tool_auto_outputs/
             submission_data_all.csv  (all submissions in one file)
             claims_data.csv
             triage_matrix.csv or triage_direct.csv (skill-dependent)
                        │
                        ▼
     st.session_state["batch_results"] = {subfolder_name: result_dict}
                        │
                        ▼
     Summary table (dataframe) + selectbox to drill into individual results
     → calls render_results() for selected submission
```

Results are cached in `st.session_state["batch_results"]` keyed by `"BATCH|{parent_folder}|{class_choice}"`. Re-run is forced with the "Re-run all (ignore cache)" checkbox.

---

## 9. Skill Resolution Flow

```
available_classes()        → sorted list of labels from _REGISTRY
         │
         ▼  user selects label
get_skill(label)
         │
         ├── get_skill_class(label)      → BaseSkill subclass from _REGISTRY
         ├── load_config(cls.code())     → sidecar dict (or default skeleton)
         └── apply_config(cls, config)
                  │
                  ├── Copy cls.OUTPUT_SCHEMA to base_fields
                  ├── Apply field_overrides (per-key property patches)
                  ├── Append field_additions (new OutputField entries)
                  ├── Resolve system_prompt (override or cls.SYSTEM_PROMPT)
                  ├── Recompute csv_schema from merged fields
                  ├── Recompute required_fields from merged fields
                  └── Return enriched skill dict
```

The class is never mutated. Every call to `get_skill()` rebuilds the skill dict from scratch, so sidecar changes take effect on the next call without a restart.

---

## 10. CSV Output Pipeline

All CSV files are written to `<output_folder>/submission_tool_auto_outputs/` via `_output_root()`.

### File summary

| File | Write mode | Skill | Description |
|------|-----------|-------|-------------|
| `submission_data.csv` | Append | All | One row per submission. Columns from `skill["csv_schema"]`. |
| `submission_data_all.csv` | Append | All | Batch mode only — consolidated roll-up across all subfolders. |
| `claims_data.csv` | Append | All with `CLAIMS_SCHEMA` | One row per loss year + one per large loss. |
| `locations_data.csv` | **Overwrite** | All | One row per SOV location, or one aggregate row. |
| `triage_matrix.csv` | Append | PVQ only | 43-column triage row including computed rates and flag strings. |
| `triage_locations.csv` | Append | PVQ only | Location rows from SOV for the PV triage skill. |
| `triage_direct.csv` | Append | PVDT only | 41-column direct triage row with RAG flags and n_red/n_amber/n_green counts. |

### CSV column naming conventions

- Metadata columns always first: `extraction_date`, `source_folder`, `class_of_business`
- Loss history columns are flattened: `loss_yr1_year`, `loss_yr1_premium`, `loss_yr1_losses`, `loss_yr1_claims_count` (up to 7 years)
- Derived analytics: `rate_on_line_pct`, `rate_on_tiv_pct`, `raw_avg_loss_ratio`, `premium_net_of_brokerage`, `premium_net`
- Gap metadata: `data_quality_score`, `critical_gaps_count`, `advisory_gaps_count`

### Append-vs-overwrite rationale

The append pattern on `submission_data.csv` and `claims_data.csv` allows multiple single-submission runs (or batch runs) to accumulate into a single file for downstream analysis in Excel or a pricing model. `locations_data.csv` overwrites because each run replaces the set of locations for that case.

---

## 11. Streamlit Session State

Session state keys used by the analyser page:

| Key | Set by | Consumed by | Description |
|-----|--------|-------------|-------------|
| `extracted` | `_run_single()` | `_run_single()` | Cached extraction result dict |
| `all_files` | `_run_single()` | `_run_single()`, `render_results()` | File info dict |
| `folder_path` | `_run_single()` | `render_results()` | Case folder path |
| `folder_name` | `_run_single()` | `render_results()` | Basename of case folder |
| `skill` | `_run_single()` | `render_results()` | Skill dict |
| `_cache_key` | `_run_single()` | `_run_single()` | `"{folder_path}|{class_choice}"` invalidation key |
| `run_triggered` | Run button | `analyser_page()` | `True` when run has been requested |
| `batch_mode_ui` | Run button | `analyser_page()` | `True` if batch toggle was active |
| `force_rerun_ui` | Run button | `_run_single()`, `_run_batch()` | Bypass cache |
| `tab_states` | Sidebar checkboxes | `render_data_tabs()` | `{section_name: bool}` |
| `batch_results` | `_run_batch()` | `_run_batch()` | `{subfolder_name: result_dict}` |
| `_cache_key_batch` | `_run_batch()` | `_run_batch()` | Batch invalidation key |
| `batch_selected_submission` | `st.selectbox()` | `_run_batch()` | Selected subfolder for drill-down |

Session state is not explicitly cleared between runs. The `_cache_key` / `_cache_key_batch` mechanism provides invalidation: if the folder path or class choice changes, the cache miss triggers a fresh Claude call.

---

## 12. Adding a New Skill

The full reference guide is at `/home/user/submission_parser/documentation/adding_skills.md`. Brief summary:

1. **Create the file**: `skills/myskill.py`
2. **Subclass `BaseSkill`**: set `META`, `OUTPUT_SCHEMA`, `CLAIMS_SCHEMA`, `SYSTEM_PROMPT`
3. **Set a unique `META["code"]`** — used for sidecar config filename and CSV routing
4. **That's it**: the skill auto-registers on the next startup

Checklist for the skill definition:

- Every field that Claude should extract needs an `OutputField` entry with `source=FieldSource.EXTRACTED`
- Set `critical=True` on fields whose absence should block underwriting (shown as red gaps)
- Set `gap_check=False` on fields that are nice to have but shouldn't appear in gap analysis at all
- Set `in_csv=False` on array fields (e.g. `loss_history`) — their data gets flattened by `build_csv_row()`
- Include `CLAIMS_SCHEMA` if the skill has per-year loss history rows
- If the skill needs a custom CSV output (like `triage_matrix.csv`), add a schema constant and `build_*/save_*` pair in `core/outputs.py`, then gate the call in `save_submission_outputs()` and `process_batch()` on `skill["code"]`

For custom tab renderers, see section 8 of `adding_skills.md`.

---

## 13. Extension Points

### Using core/ without Streamlit

```python
from skills import get_skill
from file_parser import extract_folder
from core.extractor import call_claude_extraction
from core.analysis import run_gap_analysis
from core.processor import save_submission_outputs

skill = get_skill("Casualty Liability")
files = extract_folder("/path/to/case", "01_correspondence")
combined = "\n".join(v["text"] for v in files.values())
extracted, _ = call_claude_extraction(combined, skill["system_prompt"], api_key)
gap = run_gap_analysis(extracted, skill["required_fields"])
save_submission_outputs(extracted, gap, files, "/path/to/case", "case_name", skill)
```

### Adding a non-Streamlit frontend

Implement `on_progress(pct, text)` and `on_status(level, text)` callbacks and pass them to `process_submission()` or `process_batch()`. The core logic is completely decoupled from the UI.

### Adding a new FieldSection

1. Add a new value to `FieldSection` enum in `skills/base.py`
2. Add a default icon in the `default_icons` dict in `BaseSkill.tab_config()`
3. If the section needs a custom renderer, add a branch in `render_data_tabs()` in `ui/components/data_tabs.py` and implement the renderer function. Otherwise it falls through to `_render_default_tab()`.

### Modifying an existing skill non-destructively

Use a JSON sidecar: `skills/config/<CODE>.json`. The Skill Viewer page (`skill_editor_page()`) displays what overrides and additions are active. Use `save_config()` / `delete_config()` from `skills/config_loader.py` programmatically, or write the JSON file directly.

### Swapping the Claude model

Change the model string in `core/extractor.py`:

```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",   # change here
    ...
)
```

The model is not configurable via skill or sidecar — it is a single constant in `extractor.py`.

---

## 14. Dependencies

From `requirements.txt`:

| Package | Min version | Used for |
|---------|------------|---------|
| `streamlit` | 1.32.0 | UI framework (1.44+ required for `st.navigation()` callable pattern) |
| `anthropic` | 0.25.0 | Claude API client |
| `pdfplumber` | 0.10.0 | PDF text and table extraction |
| `openpyxl` | 3.1.0 | `.xlsx` / `.xlsm` extraction |
| `python-docx` | 1.1.0 | `.docx` extraction |
| `extract-msg` | 0.48.0 | Outlook `.msg` extraction |
| `pandas` | 2.0.0 | Dataframe display in UI (batch results table, Skill Viewer tables) |
| `xlrd` | 2.0.0 | `.xls` fallback extraction |

Standard library modules used: `os`, `json`, `re`, `csv`, `datetime`, `pathlib`, `typing`, `dataclasses`, `enum`, `importlib`, `inspect`, `io`, `traceback`.

All file-format libraries (`pdfplumber`, `openpyxl`, `xlrd`, `python-docx`, `extract-msg`) are imported inside their respective extractor functions rather than at module level. This means a missing library produces a clear status message in the file extraction result rather than an `ImportError` at startup.

---

*End of document. For adding new skills, see `documentation/adding_skills.md`.*
