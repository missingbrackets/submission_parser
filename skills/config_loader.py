# ============================================================
#  skills/config_loader.py
#  JSON sidecar config for skill overrides.
#
#  Purpose: allow the UI skill editor to modify field
#  properties, CSV consolidation settings, and the system
#  prompt WITHOUT editing Python source files.
#
#  Each skill gets an optional JSON file at:
#      skills/config/<CODE>.json
#
#  If no sidecar exists, the skill runs from its .py defaults.
#  The sidecar is the single source of UI-driven overrides.
#
#  Schema:
#  {
#    "meta_overrides": {
#      "label": "...",          # optional label override
#      "description": "..."
#    },
#    "field_overrides": {
#      "<key>": {               # must match an existing OutputField key
#        "label":      "...",
#        "section":    "INSURED",   # FieldSection enum name
#        "in_csv":     true,
#        "in_summary": true,
#        "critical":   false,
#        "gap_check":  true,
#        "description":"..."
#      }
#    },
#    "field_additions": [        # new fields not in base OUTPUT_SCHEMA
#      {
#        "key":        "my_new_field",
#        "label":      "My New Field",
#        "field_type": "TEXT",       # FieldType enum name
#        "source":     "EXTRACTED",  # FieldSource enum name
#        "section":    "INSURED",
#        "in_csv":     true,
#        "in_summary": true,
#        "critical":   false,
#        "gap_check":  true,
#        "description":""
#      }
#    ],
#    "csv_consolidation": {
#      "submission_data": true,   # consolidate to parent in batch mode
#      "claims_data":     false,
#      "triage_matrix":   false,
#      "locations_data":  false
#    },
#    "prompt_override": null       # null = use SYSTEM_PROMPT from .py
#  }
# ============================================================

import os
import json
from dataclasses import asdict
from typing import Optional

from skills.base import (
    BaseSkill, OutputField,
    FieldType, FieldSource, FieldSection
)

# ── Path helpers ─────────────────────────────────────────────

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")


def _config_path(skill_code: str) -> str:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return os.path.join(CONFIG_DIR, f"{skill_code}.json")


# ── Default config skeleton ───────────────────────────────────

def _default_config() -> dict:
    return {
        "meta_overrides":   {},
        "field_overrides":  {},
        "field_additions":  [],
        "csv_consolidation": {
            "submission_data": True,
            "claims_data":     True,
            "triage_matrix":   False,
            "locations_data":  False,
        },
        "prompt_override": None,
    }


# ── Load / save ───────────────────────────────────────────────

def load_config(skill_code: str) -> dict:
    """Load sidecar JSON for a skill. Returns default skeleton if absent."""
    path = _config_path(skill_code)
    if not os.path.exists(path):
        return _default_config()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure all top-level keys present (forward-compat with new keys)
        defaults = _default_config()
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
        return data
    except Exception as e:
        print(f"[config_loader] Warning: could not load {path}: {e}")
        return _default_config()


def save_config(skill_code: str, config: dict) -> str:
    """Persist config to JSON sidecar. Returns file path."""
    path = _config_path(skill_code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return path


def delete_config(skill_code: str) -> bool:
    """Delete sidecar, reverting skill to .py defaults. Returns True if deleted."""
    path = _config_path(skill_code)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def has_config(skill_code: str) -> bool:
    """True if a sidecar exists for this skill."""
    return os.path.exists(_config_path(skill_code))


# ── Merge helpers ─────────────────────────────────────────────

def _parse_field_type(value: str) -> FieldType:
    try:
        return FieldType[value.upper()]
    except KeyError:
        return FieldType.TEXT


def _parse_field_source(value: str) -> FieldSource:
    try:
        return FieldSource[value.upper()]
    except KeyError:
        return FieldSource.EXTRACTED


def _parse_field_section(value: str) -> FieldSection:
    try:
        return FieldSection[value.upper()]
    except KeyError:
        return FieldSection.META


def apply_config(skill_class: type, config: dict) -> dict:
    """
    Merge a JSON config over the skill's base OUTPUT_SCHEMA and SYSTEM_PROMPT.

    Returns an enriched skill dict (same shape as get_skill() output) with
    config-driven overrides applied. The original skill class is NOT mutated.
    """
    # ── Start from base schema ────────────────────────────────
    base_fields: list[OutputField] = list(skill_class.OUTPUT_SCHEMA)

    # ── Apply field overrides ─────────────────────────────────
    overrides = config.get("field_overrides", {})
    merged_fields = []
    for f in base_fields:
        if f.key in overrides:
            ov = overrides[f.key]
            # Build a new OutputField with overridden values, preserving
            # any property not explicitly overridden
            merged_fields.append(OutputField(
                key         = f.key,
                label       = ov.get("label",       f.label),
                field_type  = _parse_field_type(ov["field_type"]) if "field_type" in ov else f.field_type,
                source      = _parse_field_source(ov["source"])   if "source"     in ov else f.source,
                section     = _parse_field_section(ov["section"]) if "section"    in ov else f.section,
                in_csv      = ov.get("in_csv",      f.in_csv),
                in_summary  = ov.get("in_summary",  f.in_summary),
                critical    = ov.get("critical",    f.critical),
                gap_check   = ov.get("gap_check",   f.gap_check),
                description = ov.get("description", f.description),
            ))
        else:
            merged_fields.append(f)

    # ── Append field additions ────────────────────────────────
    existing_keys = {f.key for f in merged_fields}
    for add in config.get("field_additions", []):
        if add.get("key") and add["key"] not in existing_keys:
            merged_fields.append(OutputField(
                key         = add["key"],
                label       = add.get("label",       add["key"]),
                field_type  = _parse_field_type(add.get("field_type",  "TEXT")),
                source      = _parse_field_source(add.get("source",    "EXTRACTED")),
                section     = _parse_field_section(add.get("section",  "META")),
                in_csv      = add.get("in_csv",      True),
                in_summary  = add.get("in_summary",  True),
                critical    = add.get("critical",    False),
                gap_check   = add.get("gap_check",   True),
                description = add.get("description", ""),
            ))

    # ── Resolved system prompt ────────────────────────────────
    prompt = config.get("prompt_override") or skill_class.SYSTEM_PROMPT

    # ── Build enriched skill dict ─────────────────────────────
    # Reconstruct csv_schema and required_fields from merged_fields

    meta_cols = ["extraction_date", "source_folder", "class_of_business"]
    seen = set(meta_cols)
    csv_cols = meta_cols[:]
    for f in merged_fields:
        if f.in_csv and f.key not in seen:
            csv_cols.append(f.key)
            seen.add(f.key)

    required = [
        (f.key, f.label, f.critical)
        for f in merged_fields
        if f.gap_check and f.source == FieldSource.EXTRACTED
    ]

    label = config.get("meta_overrides", {}).get("label") or skill_class.label()
    desc  = config.get("meta_overrides", {}).get("description") or skill_class.description()

    return {
        "label":             label,
        "code":              skill_class.code(),
        "version":           skill_class.version(),
        "description":       desc,
        "required_fields":   required,
        "csv_schema":        csv_cols,
        "claims_csv_schema": skill_class.CLAIMS_SCHEMA,
        "system_prompt":     prompt,
        "output_schema":     merged_fields,
        "skill_class":       skill_class,
        "config":            config,             # pass through for editor use
        "has_overrides":     has_config(skill_class.code()),
    }


# ── Field serialisation (for editor → JSON round-trip) ────────

def field_to_dict(f: OutputField) -> dict:
    """Serialise an OutputField to a plain dict for JSON storage."""
    return {
        "key":         f.key,
        "label":       f.label,
        "field_type":  f.field_type.name,
        "source":      f.source.name,
        "section":     f.section.name,
        "in_csv":      f.in_csv,
        "in_summary":  f.in_summary,
        "critical":    f.critical,
        "gap_check":   f.gap_check,
        "description": f.description,
    }


# ── Helpers for the editor UI ─────────────────────────────────

FIELD_TYPE_OPTIONS  = [e.name for e in FieldType]
FIELD_SOURCE_OPTIONS = [e.name for e in FieldSource]
SECTION_OPTIONS     = [e.name for e in FieldSection]
SECTION_LABELS      = {e.name: e.value for e in FieldSection}

CSV_FILES = {
    "submission_data": "Submission Data (submission_data.csv)",
    "claims_data":     "Claims Data (claims_data.csv)",
    "triage_matrix":   "Triage Matrix (triage_matrix.csv)",
    "locations_data":  "Locations / SOV (locations_data.csv)",
}