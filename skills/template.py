# ============================================================
#  skills/_template.py
#  TEMPLATE FOR NEW SKILLS — copy this file, rename it,
#  fill in the four sections below.
#
#  File naming: use the class code in lowercase e.g.
#    property.py, contingency.py, space.py, marine.py
#
#  Once saved in the skills/ folder it auto-registers.
#  Nothing else needs changing.
# ============================================================

from skills.base import BaseSkill, OutputField, FieldType, FieldSource, FieldSection

O = OutputField   # shorthand


class TemplateSkill(BaseSkill):

    # ── 1. META ───────────────────────────────────────────────
    # label    : shown in the app dropdown
    # code     : short unique identifier e.g. "PROP", "CONT", "MAR"
    # version  : increment when you change the schema
    # description : shown in the Schema Viewer tab

    META = {
        "label":       "My New Class",          # << CHANGE
        "code":        "NEW",                   # << CHANGE — must be unique
        "version":     "1.0",
        "description": "Describe what this skill covers.",
    }

    # ── 2. CLAIMS CSV SCHEMA ──────────────────────────────────
    # Flat list of column names for the claims CSV.
    # Keep the standard Pine Walk columns, add class-specific ones.

    CLAIMS_SCHEMA = [
        "Segment_1",
        "Segment_2",
        "underwriting_year",
        "claim_id",
        "accident_date",
        "reported_date",
        "insured",
        "claim_description",
        "status",
        "paid",
        "outstanding",
        "incurred",
        "Manual Claim Adjustments",
        # Add class-specific columns below:
        # "peril",
        # "cat_event",
    ]

    # ── 3. OUTPUT SCHEMA ──────────────────────────────────────
    # One OutputField per field this skill produces.
    # This is the single source of truth for:
    #   - CSV columns  (in_csv=True)
    #   - Summary report sections  (in_summary=True)
    #   - Gap analysis  (gap_check=True, critical=True/False)
    #
    # OutputField(
    #   key         = JSON key / CSV column name
    #   label       = human-readable label
    #   field_type  = FieldType.TEXT / CURRENCY / PERCENT / DATE / YESNO / ARRAY / BOOLEAN / DERIVED
    #   source      = FieldSource.EXTRACTED / DERIVED / METADATA
    #   section     = FieldSection.INSURED / POLICY / LIMITS / COVERAGE / PREMIUM / LOSS / FLAGS / ANALYTICS
    #   in_csv      = True/False
    #   in_summary  = True/False
    #   critical    = True → RED gap if missing | False → AMBER gap
    #   gap_check   = False to exclude from gap analysis entirely
    #   description = tooltip / documentation
    # )

    OUTPUT_SCHEMA = [

        # ── INSURED ───────────────────────────────────────────
        O("insured_name",        "Insured Name",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("industry_sector",     "Industry / Sector",  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("annual_revenue",      "Annual Revenue",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),

        # ── POLICY ────────────────────────────────────────────
        O("policy_period_start", "Policy Start",       FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.POLICY,   critical=True),
        O("policy_period_end",   "Policy End",         FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.POLICY,   critical=True),

        # ── LIMITS ────────────────────────────────────────────
        O("limit_any_one_claim", "Limit Any One Claim",FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True),
        O("excess_point",        "Excess Point",       FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True),

        # ── PREMIUM ───────────────────────────────────────────
        O("premium_sought_gross","Premium Sought",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=True),
        O("brokerage_pct",       "Brokerage %",        FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=False),

        # ── LOSS HISTORY ──────────────────────────────────────
        O("loss_history",        "Loss History",       FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOSS,     critical=True, in_csv=False),
        O("large_losses",        "Large Losses",       FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOSS,     critical=False,in_csv=False),

        # ── FLAGS ─────────────────────────────────────────────
        O("pending_litigation",  "Pending Litigation", FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True),
        O("prior_declinatures",  "Prior Declinatures", FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True),

        # ── ANALYTICS ─────────────────────────────────────────
        O("uw_analyst_flags",    "UW Analyst Flags",   FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS,critical=False, in_csv=False, gap_check=False),
        O("questions_for_broker","Questions for Broker",FieldType.ARRAY,   FieldSource.EXTRACTED, FieldSection.ANALYTICS,critical=False, in_csv=False, gap_check=False),
        O("data_quality_score",  "Data Quality Score", FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.ANALYTICS,critical=False, gap_check=False),

        # << ADD YOUR CLASS-SPECIFIC FIELDS HERE >>
    ]

    # ── 4. SYSTEM PROMPT ──────────────────────────────────────
    # This is sent to Claude with every extraction call.
    # Include:
    #   - Role / expertise framing
    #   - Class-specific extraction rules and judgement guidance
    #   - The exact JSON structure to return (must match OUTPUT_SCHEMA keys)

    SYSTEM_PROMPT = """You are a senior London Market underwriting analyst specialising in [CLASS].

You will receive text extracted from a broker submission. Extract all available information
and return structured JSON. Apply underwriting judgement — reconcile conflicts, flag issues.

CRITICAL RULES:
- Return ONLY valid JSON — no markdown, no preamble
- Use null for absent fields — never invent values
- Record data conflicts in data_conflicts array
- Raise specific flags in uw_analyst_flags (RED / AMBER / INFO)

Return this exact JSON structure:
{
  "insured_name": null,
  "industry_sector": null,
  "annual_revenue": null,
  "policy_period_start": null,
  "policy_period_end": null,
  "limit_any_one_claim": null,
  "excess_point": null,
  "premium_sought_gross": null,
  "brokerage_pct": null,
  "loss_history": [],
  "large_losses": [],
  "pending_litigation": null,
  "prior_declinatures": null,
  "data_conflicts": [],
  "uw_analyst_flags": [],
  "questions_for_broker": [],
  "extraction_confidence": "High / Medium / Low",
  "extraction_notes": null
}"""