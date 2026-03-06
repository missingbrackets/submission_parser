# ============================================================
#  skills/base.py
#  Base class for all Pine Walk pricing skills.
#
#  Every skill inherits from BaseSkill and defines:
#    - META          : display name, class code, version
#    - REQUIRED_FIELDS : gap analysis checklist
#    - OUTPUT_SCHEMA : every field the skill can produce
#    - CLAIMS_SCHEMA : columns for the claims CSV
#    - SYSTEM_PROMPT : sent to Claude API
#
#  The OUTPUT_SCHEMA is the single source of truth for:
#    - What Claude is asked to extract (JSON keys)
#    - What appears in the summary report
#    - What columns land in the submission CSV
#    - What the gap analysis checks
#
#  Adding a new skill = create a new file in skills/,
#  subclass BaseSkill, fill in the four sections.
#  It auto-registers — nothing else needs changing.
# ============================================================

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ── FIELD TYPES ──────────────────────────────────────────────

class FieldType(Enum):
    TEXT        = "text"        # free text string
    NUMBER      = "number"      # numeric value (stored as string in CSV)
    CURRENCY    = "currency"    # monetary amount
    PERCENT     = "percent"     # percentage
    DATE        = "date"        # date string
    YESNO       = "yesno"       # Y / N / Unknown
    ARRAY       = "array"       # list (loss history, flags etc.)
    BOOLEAN     = "boolean"     # true/false
    DERIVED     = "derived"     # calculated by post-processor, not extracted


class FieldSource(Enum):
    EXTRACTED   = "extracted"   # Claude extracts directly from submission
    DERIVED     = "derived"     # calculated from other extracted fields
    METADATA    = "metadata"    # set by the app (date, folder name etc.)


class FieldSection(Enum):
    """Which section of the summary report this field belongs to."""
    INSURED     = "Insured & Exposure"
    POLICY      = "Policy Structure"
    LIMITS      = "Limits & Structure"
    COVERAGE    = "Coverage Lines"
    PREMIUM     = "Premium Analytics"
    LOSS        = "Loss History"
    FLAGS       = "Risk Flags"
    ANALYTICS   = "Underwriter Analytics"
    META        = "Metadata"
    # Terror / Political Violence specific
    LOCATIONS   = "Locations & SOV"
    PERILS      = "Peril Structure"
    BI_EXT      = "BI & Extensions"
    GEO         = "Geopolitical Assessment"
    RATER       = "Rater Inputs"


# ── TAB CONFIGURATION ────────────────────────────────────────

@dataclass
class TabConfig:
    """
    Defines a display tab in the extracted data view.

    section     : FieldSection this tab displays
    icon        : emoji icon for the tab label
    default_on  : whether the tab is ticked by default in the sidebar
    description : tooltip shown next to the checkbox
    """
    section:     FieldSection
    icon:        str   = "📋"
    default_on:  bool  = True
    description: str   = ""


# ── OUTPUT FIELD DEFINITION ───────────────────────────────────

@dataclass
class OutputField:
    """
    Defines a single output field produced by a skill.

    key         : JSON key returned by Claude / used in CSV column header
    label       : human-readable label shown in UI and summary report
    field_type  : FieldType enum
    source      : FieldSource enum
    section     : FieldSection enum (groups field in summary report)
    in_csv      : include in submission CSV output
    in_summary  : include in text summary report
    critical    : if True and missing → RED gap flag; if False → AMBER
    gap_check   : whether to include in gap analysis at all
    description : tooltip / documentation for this field
    """
    key:         str
    label:       str
    field_type:  FieldType       = FieldType.TEXT
    source:      FieldSource     = FieldSource.EXTRACTED
    section:     FieldSection    = FieldSection.META
    in_csv:      bool            = True
    in_summary:  bool            = True
    critical:    bool            = False
    gap_check:   bool            = True
    description: str             = ""


# ── BASE SKILL CLASS ──────────────────────────────────────────

class BaseSkill:
    """
    All pricing skills inherit from this class.

    Subclasses must define:
        META            = { "label": str, "code": str, "version": str, "description": str }
        OUTPUT_SCHEMA   = [ OutputField(...), ... ]
        CLAIMS_SCHEMA   = [ "col1", "col2", ... ]   (flat list of CSV column names)
        SYSTEM_PROMPT   = "..."

    Everything else is derived automatically.
    """

    META: dict = {
        "label":       "Base Skill",
        "code":        "BASE",
        "version":     "1.0",
        "description": "Base skill — do not use directly",
    }

    OUTPUT_SCHEMA: list = []   # list of OutputField
    CLAIMS_SCHEMA: list = []   # flat list of column name strings
    SYSTEM_PROMPT: str  = ""

    # ── Derived properties ────────────────────────────────────

    @classmethod
    def label(cls) -> str:
        return cls.META.get("label", cls.__name__)

    @classmethod
    def code(cls) -> str:
        return cls.META.get("code", "")

    @classmethod
    def version(cls) -> str:
        return cls.META.get("version", "1.0")

    @classmethod
    def description(cls) -> str:
        return cls.META.get("description", "")

    @classmethod
    def required_fields(cls) -> list:
        """
        Return list of (key, label, is_critical) tuples for gap analysis.
        Only fields with gap_check=True are included.
        Matches the format expected by run_gap_analysis().
        """
        return [
            (f.key, f.label, f.critical)
            for f in cls.OUTPUT_SCHEMA
            if f.gap_check and f.source == FieldSource.EXTRACTED
        ]

    @classmethod
    def csv_schema(cls) -> list:
        """
        Return ordered list of CSV column names.
        Metadata columns first, then all in_csv fields in schema order.
        """
        # Always-present metadata columns
        meta_cols = ["extraction_date", "source_folder", "class_of_business"]
        extracted_cols = [f.key for f in cls.OUTPUT_SCHEMA if f.in_csv]
        # Deduplicate while preserving order
        seen = set(meta_cols)
        result = meta_cols[:]
        for col in extracted_cols:
            if col not in seen:
                result.append(col)
                seen.add(col)
        return result

    @classmethod
    def summary_sections(cls) -> dict:
        """
        Return fields grouped by section for summary report rendering.
        Returns { FieldSection: [OutputField, ...], ... }
        """
        sections = {}
        for f in cls.OUTPUT_SCHEMA:
            if f.in_summary:
                sections.setdefault(f.section, []).append(f)
        return sections

    @classmethod
    def tab_config(cls) -> list:
        """
        Return list of TabConfig for this skill.
        Override in subclass to customise tab order, icons, defaults.
        Default behaviour: one tab per FieldSection that has in_summary fields,
        in enum order.
        """
        # Use skill-defined tabs if present
        if hasattr(cls, "TABS") and cls.TABS:
            return cls.TABS

        # Auto-generate from sections that have displayable fields
        sections_with_fields = {
            f.section for f in cls.OUTPUT_SCHEMA
            if f.in_summary and f.source.value != "metadata"
        }

        default_icons = {
            FieldSection.INSURED:   "🏢",
            FieldSection.POLICY:    "📄",
            FieldSection.LIMITS:    "🔢",
            FieldSection.COVERAGE:  "🏷",
            FieldSection.PREMIUM:   "💷",
            FieldSection.LOSS:      "📉",
            FieldSection.FLAGS:     "⚠️",
            FieldSection.ANALYTICS: "🚩",
            FieldSection.META:      "ℹ️",
            FieldSection.LOCATIONS: "📍",
            FieldSection.PERILS:    "💥",
            FieldSection.BI_EXT:    "🔄",
            FieldSection.GEO:       "🌍",
            FieldSection.RATER:     "🧮",
        }

        return [
            TabConfig(
                section    = s,
                icon       = default_icons.get(s, "📋"),
                default_on = True,
            )
            for s in FieldSection
            if s in sections_with_fields
        ]

    @classmethod
    def fields_by_key(cls) -> dict:
        """Return { key: OutputField } lookup dict."""
        return {f.key: f for f in cls.OUTPUT_SCHEMA}

    @classmethod
    def schema_doc(cls) -> str:
        """
        Return a human-readable schema documentation string.
        Useful for understanding what a skill produces at a glance.
        """
        lines = []
        lines.append(f"SKILL: {cls.label()} (v{cls.version()})")
        lines.append(f"Code:  {cls.code()}")
        lines.append(f"Desc:  {cls.description()}")
        lines.append("")
        lines.append(f"{'KEY':<40} {'LABEL':<40} {'TYPE':<12} {'SOURCE':<12} {'CSV':<5} {'CRITICAL'}")
        lines.append("-" * 120)

        current_section = None
        for f in cls.OUTPUT_SCHEMA:
            if f.section != current_section:
                current_section = f.section
                lines.append(f"\n  [{f.section.value.upper()}]")
            csv_flag      = "Y" if f.in_csv else "-"
            critical_flag = "Y" if f.critical else "-"
            lines.append(
                f"  {f.key:<38} {f.label:<40} {f.field_type.value:<12} "
                f"{f.source.value:<12} {csv_flag:<5} {critical_flag}"
            )

        lines.append("")
        lines.append(f"Total output fields: {len(cls.OUTPUT_SCHEMA)}")
        lines.append(f"CSV columns:         {len(cls.csv_schema())}")
        lines.append(f"Gap-checked fields:  {len(cls.required_fields())}")
        lines.append(f"Critical fields:     {sum(1 for f in cls.OUTPUT_SCHEMA if f.critical)}")

        if cls.CLAIMS_SCHEMA:
            lines.append(f"\nCLAIMS CSV COLUMNS ({len(cls.CLAIMS_SCHEMA)}):")
            lines.append("  " + ", ".join(cls.CLAIMS_SCHEMA))

        return "\n".join(lines)