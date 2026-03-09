# ============================================================
#  skills/terror_quick.py
#  Political Violence & Terrorism — Quick Triage
#  Pricing | Submission Analyser
#
#  ~25 fields vs 152 in full skill.
#  Purpose: fast first-pass triage across a batch of submissions.
#  Outputs: triage matrix CSV (one row per submission, appends
#           across runs) + per-location CSV.
#  Use the full TerrorSkill for detailed pricing.
# ============================================================

from skills.base import (
    BaseSkill, OutputField, TabConfig,
    FieldType, FieldSource, FieldSection
)

O = OutputField


class TerrorQuickSkill(BaseSkill):

    META = {
        "label":       "PV Triage (Quick)",
        "code":        "PVQ",
        "version":     "1.0",
        "description": "Fast triage extraction for Political Violence & Terrorism. "
                       "~25 key fields only. Use for batch first-pass; switch to "
                       "full PV skill for detailed pricing.",
    }

    TABS = [
        TabConfig(FieldSection.INSURED,   icon="🏢", default_on=True,  description="Identity and exposure"),
        TabConfig(FieldSection.PERILS,    icon="💥", default_on=True,  description="Cover type and peril scope"),
        TabConfig(FieldSection.LIMITS,    icon="🔢", default_on=True,  description="Limit, excess, deductible"),
        TabConfig(FieldSection.PREMIUM,   icon="💷", default_on=True,  description="Premium and rate metrics"),
        TabConfig(FieldSection.LOCATIONS, icon="📍", default_on=True,  description="Location schedule"),
        TabConfig(FieldSection.FLAGS,     icon="⚠️", default_on=True,  description="Triage flags"),
        TabConfig(FieldSection.ANALYTICS, icon="🚩", default_on=True,  description="UW flags and questions"),
    ]

    # ── LOCATIONS CSV — per-location rows ────────────────────
    # Separate from CLAIMS_SCHEMA; handled by build_locations_csv_rows()
    CLAIMS_SCHEMA = []   # no claims CSV for triage skill

    # ── OUTPUT SCHEMA — triage fields only ───────────────────

    OUTPUT_SCHEMA = [

        # ── IDENTITY & EXPOSURE ───────────────────────────────
        O("insured_name",         "Insured Name",            FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,  description="Full legal name of primary insured"),
        O("broker_name",          "Broker",                  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=False),
        O("insured_country",      "Country of Domicile",     FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("risk_type",            "Risk Type",               FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,  description="WHSE / INFRA / INDUS / OFFICE"),
        O("tiv_total",            "Total TIV",               FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,  description="Total Insured Value across all locations"),
        O("tiv_currency",         "TIV Currency",            FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,  gap_check=False),
        O("location_count",       "No. of Locations",        FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("territorial_scope",    "Territorial Scope",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("policy_period_start",  "Policy Start",            FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("policy_period_end",    "Policy End",              FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("renewal_or_new",       "Renewal / New",           FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=False, description="Renewal / New Business / Transfer"),

        # ── PERIL STRUCTURE ───────────────────────────────────
        O("cover_type",           "Cover Type",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PERILS,   critical=True,  description="T&S Only / Full PV / Full PV + War / Full PV + War + Liability"),
        O("peril_war",            "War Extension",           FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,   critical=True),
        O("peril_pv_liability",   "Liability Extension",     FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,   critical=False),
        O("occurrence_hrs",       "Occurrence Window (hrs)", FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.PERILS,   critical=False, description="Hours clause — typically 72hrs"),

        # ── LIMITS & STRUCTURE ────────────────────────────────
        O("limit_aoo",            "Limit (AOO)",             FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True,  description="Limit any one occurrence"),
        O("limit_currency",       "Limit Currency",          FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True,  gap_check=False),
        O("excess_point",         "Excess / Attachment",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True,  description="0 if primary layer"),
        O("deductible",           "PD Deductible",           FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=False),
        O("bi_covered",           "BI Covered",              FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True),
        O("bi_indemnity_period",  "BI Indemnity Period",     FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=False),

        # ── PREMIUM & RATE ────────────────────────────────────
        O("premium_sought_gross", "Premium Sought (Gross)",  FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=True),
        O("premium_currency",     "Premium Currency",        FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=False, gap_check=False),
        O("commission_pct",       "Commission %",            FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=False),
        O("prior_premium",        "Prior Year Premium",      FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=False),
        O("rate_on_line_pct",     "Rate on Line %",          FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,  critical=False, gap_check=False, description="Gross premium / limit"),
        O("rate_on_tiv_pct",      "Rate on TIV %",           FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,  critical=False, gap_check=False, description="Gross premium / TIV"),
        O("implied_rate_change",  "Implied Rate Change %",   FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,  critical=False, gap_check=False),

        # ── TRIAGE FLAGS ──────────────────────────────────────
        O("country_risk",         "Country Risk",            FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True,  description="AI assessment: Low / Moderate / Elevated / High / Extreme"),
        O("sanctions_exposure",   "Sanctions Exposure",      FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True,  description="None identified / Possible / Confirmed"),
        O("sov_provided",         "SOV Provided",            FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True),
        O("prior_declinatures",   "Prior Declinatures",      FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True),
        O("known_circumstances",  "Known Circumstances",     FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True,  description="Any known losses or claims in progress"),
        O("large_losses_flag",    "Large Losses on Record",  FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False),
        O("loss_years_provided",  "Loss History (years)",    FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False),
        O("triage_recommendation","Triage Recommendation",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False,
          description="AI recommendation: REFER TO FULL ANALYSIS / DECLINE / QUERY BROKER / FAST-TRACK"),
        O("triage_rationale",     "Triage Rationale",        FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False,
          description="One-line summary of key triage considerations"),

        # ── ANALYTICS ─────────────────────────────────────────
        O("uw_analyst_flags",     "UW Flags",                FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False),
        O("questions_for_broker", "Questions for Broker",    FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False),
        O("data_quality_score",   "Data Quality Score",      FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.ANALYTICS, critical=False, gap_check=False),
        O("extraction_confidence","Extraction Confidence",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, gap_check=False, in_summary=False),

        # ── LOCATIONS (array — drives per-location CSV) ───────
        O("sov_locations",        "Location Detail (SOV)",   FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, in_csv=False,
          description="Per-location schedule — feeds locations_triage.csv"),
    ]

    # ── SYSTEM PROMPT ─────────────────────────────────────────
    SYSTEM_PROMPT = """You are a senior London Market Political Violence and Terrorism \
underwriter at Pine Walk performing a FAST TRIAGE assessment. Your goal is speed and \
accuracy on the ~30 fields that matter most for a go/no-go decision.

Do NOT attempt exhaustive extraction. Focus only on the fields below.

════════════════════════════════════════════
TRIAGE PRIORITY ORDER
════════════════════════════════════════════

Work through these in order — stop when you have enough for a triage decision:

1. SHOW-STOPPERS first:
   - Sanctions exposure (any territorial overlap with OFAC/UK/EU sanctioned jurisdictions)
   - Known circumstances or prior losses not declared
   - Prior declinatures
   If any confirmed → triage_recommendation = "DECLINE" or "QUERY BROKER"

2. EXPOSURE SIZE:
   - TIV: is it in scope for your book?
   - Cover type: T&S only / Full PV / War extension
   - Primary country risk level

3. RATE ADEQUACY:
   - Calculate Rate on Line (premium / limit × 100) and Rate on TIV (premium / TIV × 100)
   - Flag if either looks materially off for the territory and cover type

4. DATA QUALITY:
   - SOV provided? (critical for pricing)
   - Loss history years available?

════════════════════════════════════════════
TRIAGE RECOMMENDATION
════════════════════════════════════════════

Set triage_recommendation to one of:
- FAST-TRACK: clean risk, adequate data, sensible rate, no flags → proceed to pricing
- REFER TO FULL ANALYSIS: needs detailed skill — complex structure, high TIV, War extension
- QUERY BROKER: missing critical data (no TIV, no SOV, unclear cover type) → ask first
- DECLINE: show-stopper identified (sanctions, known circumstances, prior declinatures)

Set triage_rationale to a single concise sentence explaining the recommendation.

════════════════════════════════════════════
LOCATION EXTRACTION (SOV)
════════════════════════════════════════════

Extract per-location data into sov_locations array. For each location:
- location_name, city, country (required if available)
- tiv_total (the declared value for that location)
- occupancy (warehouse / office / industrial / infrastructure)
- latitude, longitude: infer from city/country if not stated — use city-centre coords
  Leave null only if location is too vague to geocode

════════════════════════════════════════════
RATE SENSE CHECK (apply your knowledge)
════════════════════════════════════════════

Very approximate benchmarks (do not embed in output — use only to calibrate flags):
- T&S only, stable territory: very low RoL
- Full PV, moderate territory: low-to-mid RoL
- Full PV + War, elevated territory: mid RoL
- War extension on conflict-adjacent territory: materially higher

If rate looks <50% of expected → flag AMBER "Rate appears below market"
If rate looks >200% of expected → flag INFO "Rate appears above market — verify"

════════════════════════════════════════════
UW FLAGS — TRIAGE ONLY
════════════════════════════════════════════

Keep flags brief — maximum 5. Prioritise RED show-stoppers, then key AMBERs.
Format: {"severity": "RED|AMBER|INFO", "flag": "short title", "detail": "one line"}

════════════════════════════════════════════
OUTPUT RULES
════════════════════════════════════════════

- Return ONLY valid JSON — no markdown, no preamble
- null for absent fields — never invent
- Monetary amounts: numeric string without symbols e.g. "5000000"
- Y/N fields: exactly "Y", "N", or "Unknown"
- occurrence_hrs: integer e.g. 72
- Keep the response SHORT — only the fields below

Return this exact JSON structure:

{
  "insured_name": null,
  "broker_name": null,
  "insured_country": null,
  "risk_type": null,
  "tiv_total": null,
  "tiv_currency": null,
  "location_count": null,
  "territorial_scope": null,
  "policy_period_start": null,
  "policy_period_end": null,
  "renewal_or_new": null,

  "cover_type": null,
  "peril_war": "Unknown",
  "peril_pv_liability": "Unknown",
  "occurrence_hrs": null,

  "limit_aoo": null,
  "limit_currency": null,
  "excess_point": null,
  "deductible": null,
  "bi_covered": "Unknown",
  "bi_indemnity_period": null,

  "premium_sought_gross": null,
  "premium_currency": null,
  "commission_pct": null,
  "prior_premium": null,

  "country_risk": null,
  "sanctions_exposure": null,
  "sov_provided": "Unknown",
  "prior_declinatures": "Unknown",
  "known_circumstances": "Unknown",
  "large_losses_flag": "Unknown",
  "loss_years_provided": null,
  "triage_recommendation": null,
  "triage_rationale": null,

  "uw_analyst_flags": [],
  "questions_for_broker": [],

  "sov_locations": [
    {
      "location_name": null,
      "city": null,
      "country": null,
      "latitude": null,
      "longitude": null,
      "occupancy": null,
      "tiv_total": null,
      "currency": null,
      "notes": null
    }
  ],

  "extraction_confidence": "High / Medium / Low"
}"""