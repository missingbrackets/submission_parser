# ============================================================
#  SKILLS REGISTRY
#  Add new class skills here as they are created.
#  Key = display label shown in the app dropdown
# ============================================================

from skills.casualty import (
    CLASS_LABEL as CASUALTY_LABEL,
    REQUIRED_FIELDS as CASUALTY_FIELDS,
    CSV_SCHEMA as CASUALTY_SCHEMA,
    CLAIMS_CSV_SCHEMA as CASUALTY_CLAIMS_SCHEMA,
    SYSTEM_PROMPT as CASUALTY_PROMPT,
)

SKILLS = {
    "Casualty Liability": {
        "label":            CASUALTY_LABEL,
        "required_fields":  CASUALTY_FIELDS,
        "csv_schema":       CASUALTY_SCHEMA,
        "claims_csv_schema": CASUALTY_CLAIMS_SCHEMA,
        "system_prompt":    CASUALTY_PROMPT,
    },
    # Future classes — add imports above and entries here:
    # "Industrial All Risks": { ... },
    # "Contingency":          { ... },
    # "Space":                { ... },
}

def get_skill(class_name: str) -> dict:
    """Return skill config for a class, or raise KeyError."""
    if class_name not in SKILLS:
        raise KeyError(f"No skill found for class: {class_name}")
    return SKILLS[class_name]

def available_classes() -> list:
    return list(SKILLS.keys())
