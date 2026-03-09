# ============================================================
#  skills/casualty.py
#  Casualty Liability — London Market
#  Submission Analyser
#
#  OUTPUT_SCHEMA is the single source of truth:
#    - Defines every field Claude is asked to extract
#    - Controls CSV columns, summary report, gap analysis
#    - Read the schema_doc() for full field listing
# ============================================================

from skills.base import BaseSkill, OutputField, TabConfig, FieldType, FieldSource, FieldSection

O = OutputField   # shorthand


class CasualtySkill(BaseSkill):

    META = {
        "label":       "Casualty Liability",
        "code":        "CAS",
        "version":     "2.0",
        "description": "London Market casualty liability — GL, PL, EL, PI, D&O. "
                       "Claims-made and occurrence triggers. UK and international.",
    }

    # ── TAB CONFIGURATION ────────────────────────────────────
    # Controls which tabs appear in the extracted data view.
    # Set default_on=False for tabs you want available but not shown by default.

    TABS = [
        TabConfig(FieldSection.INSURED,   icon="🏢", default_on=True,  description="Insured identity, revenue, employees"),
        TabConfig(FieldSection.POLICY,    icon="📄", default_on=True,  description="Policy period, trigger, retro date, territory"),
        TabConfig(FieldSection.LIMITS,    icon="🔢", default_on=True,  description="Limits, excess, deductible, SIR"),
        TabConfig(FieldSection.COVERAGE,  icon="🏷", default_on=True,  description="GL, PL, EL, PI, D&O coverage flags"),
        TabConfig(FieldSection.PREMIUM,   icon="💷", default_on=True,  description="Premium, brokerage, rate change, RoL"),
        TabConfig(FieldSection.LOSS,      icon="📉", default_on=True,  description="Loss history table and large losses"),
        TabConfig(FieldSection.FLAGS,     icon="⚠️", default_on=True,  description="Litigation, declinatures, insurer switch"),
        TabConfig(FieldSection.ANALYTICS, icon="🚩", default_on=True,  description="UW flags, data conflicts, broker questions"),
    ]

    # ── CLAIMS CSV SCHEMA ─────────────────────────────────────
    # One row per claim / loss year. Fixed layout for rating model.

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
    ]

    # ── OUTPUT SCHEMA ─────────────────────────────────────────
    # Every field the skill can produce, in report order.
    # This drives: CSV columns | summary report | gap analysis

    OUTPUT_SCHEMA = [

        # ── INSURED & EXPOSURE ────────────────────────────────
        O("insured_name",           "Insured Name",                  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Full legal name of the insured entity"),
        O("insured_country",        "Country of Domicile",           FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Country where insured is domiciled"),
        O("industry_sector",        "Industry / Sector",             FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Industry description"),
        O("industry_sic_code",      "SIC Code",                      FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, description="Standard Industry Classification code if provided"),
        O("annual_revenue",         "Annual Revenue / Turnover",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Most recent annual revenue — primary exposure base for GL/PL"),
        O("annual_revenue_currency","Revenue Currency",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, gap_check=False),
        O("annual_payroll",         "Annual Payroll",                FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, description="Annual payroll — exposure base for EL"),
        O("annual_payroll_currency","Payroll Currency",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, gap_check=False),
        O("number_of_employees",    "Number of Employees",           FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, description="Headcount — sense check against payroll and EL premium"),
        O("revenue_growth_flag",    "Revenue Growth Flag",           FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, description="AI flag if revenue has grown >15% YoY — on-levelling needed"),

        # ── POLICY STRUCTURE ──────────────────────────────────
        O("policy_period_start",    "Policy Period Start",           FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Inception date"),
        O("policy_period_end",      "Policy Period End",             FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Expiry date"),
        O("coverage_trigger",       "Coverage Trigger",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Claims-Made or Occurrence"),
        O("retroactive_date",       "Retroactive Date",              FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Retro date for claims-made policies — full prior acts if blank"),
        O("retro_date_adequacy",    "Retro Date Adequacy",           FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=False, description="AI assessment of whether retro date is adequate"),
        O("jurisdiction",           "Jurisdiction / Governing Law",  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Governing law and jurisdiction for claims"),
        O("territorial_scope",      "Territorial Scope",             FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Territories covered"),
        O("us_canada_exposure",     "US / Canada Exposure",          FieldType.BOOLEAN,  FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="TRUE if territorial scope includes US or Canada — significant rating uplift"),

        # ── LIMITS & STRUCTURE ────────────────────────────────
        O("limit_any_one_claim",    "Limit Any One Claim",           FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  description="Maximum indemnity any one claim"),
        O("limit_any_one_claim_currency", "Limit Currency",          FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, gap_check=False),
        O("limit_aggregate",        "Annual Aggregate Limit",        FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  description="Annual aggregate limit — if equal to AOC limit, no true aggregate protection"),
        O("excess_point",           "Excess / Attachment Point",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  description="Point above which this policy responds"),
        O("deductible",             "Deductible / SIR",              FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="Deductible or self-insured retention"),
        O("sir_as_pct_of_limit",    "SIR as % of Limit",             FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="AI calculated — SIR >10% of limit is a moral hazard flag"),
        O("sublimits",              "Sub-limits",                    FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="Any coverage sub-limits"),

        # ── COVERAGE LINES ────────────────────────────────────
        O("coverage_gl",            "General / Public Liability",    FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.COVERAGE,  critical=False, description="Y/N/Unknown"),
        O("coverage_pl",            "Products Liability",            FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.COVERAGE,  critical=False, description="Y/N/Unknown"),
        O("coverage_el",            "Employers Liability",           FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.COVERAGE,  critical=False, description="Y/N/Unknown — statutory min £5m for UK"),
        O("coverage_pi",            "Professional Indemnity",        FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.COVERAGE,  critical=False, description="Y/N/Unknown"),
        O("coverage_do",            "Directors & Officers",          FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.COVERAGE,  critical=False, description="Y/N/Unknown"),

        # ── PREMIUM ANALYTICS ─────────────────────────────────
        O("premium_sought_gross",       "Premium Sought (Gross)",    FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=True,  description="Gross premium including brokerage"),
        O("premium_sought_currency",    "Premium Currency",          FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, gap_check=False),
        O("brokerage_pct",              "Brokerage %",               FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, description="Brokerage percentage"),
        O("premium_net_of_brokerage",   "Net Premium",               FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.PREMIUM,   critical=False, gap_check=False, description="Gross premium minus brokerage — derived"),
        O("premium_basis",              "Premium Basis",             FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, description="Flat / adjustable / deposit"),
        O("prior_premium",              "Prior Year Premium",        FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, description="Prior year gross premium for rate change calculation"),
        O("implied_rate_change_pct",    "Implied Rate Change %",     FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, description="AI calculated from current vs prior premium"),
        O("rate_on_line_pct",           "Rate on Line %",            FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, description="Premium / Limit — AI calculated sense check"),

        # ── LOSS HISTORY ──────────────────────────────────────
        O("loss_history_years_provided","Years of History Provided", FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.LOSS,      critical=True,  description="Number of years of loss data provided"),
        O("loss_history_completeness",  "Loss History Completeness", FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False, description="AI assessment of completeness and reliability"),
        O("avg_loss_ratio_all_years_pct","Avg Loss Ratio (all yrs)", FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False, gap_check=False, description="Simple average LR across all years"),
        O("avg_loss_ratio_ex_large_pct","Avg LR (ex large losses)",  FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False, gap_check=False, description="Average LR excluding large losses"),
        O("loss_trend_direction",       "Loss Trend Direction",      FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False, description="AI assessment: Improving / Deteriorating / Stable / Volatile"),
        O("loss_history",               "Year-by-Year Loss Detail",  FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOSS,      critical=True,  in_csv=False, description="Array of annual loss data — see loss_yr1..7 CSV columns"),
        O("large_losses",               "Large Losses Detail",       FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOSS,      critical=True,  in_csv=False, description="Array of individually identified large losses"),
        O("large_losses_total",         "Large Losses Total",        FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.LOSS,      critical=False, gap_check=False, description="Sum of all identified large losses — derived"),
        O("large_losses_flagged",       "Large Losses Flagged",      FieldType.YESNO,    FieldSource.DERIVED,   FieldSection.LOSS,      critical=False, gap_check=False, description="Y if any large losses identified"),
        O("ibnr_commentary",            "IBNR / Development Note",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False, description="Any broker commentary on IBNR or claims development"),

        # Loss history flattened columns (derived, in CSV only)
        O("loss_yr1_year",     "Loss Yr1 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr1_premium",  "Loss Yr1 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr1_losses",   "Loss Yr1 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr1_claims_count", "Loss Yr1 Claims", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_year",     "Loss Yr2 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_premium",  "Loss Yr2 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_losses",   "Loss Yr2 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_claims_count", "Loss Yr2 Claims", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_year",     "Loss Yr3 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_premium",  "Loss Yr3 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_losses",   "Loss Yr3 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_claims_count", "Loss Yr3 Claims", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_year",     "Loss Yr4 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_premium",  "Loss Yr4 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_losses",   "Loss Yr4 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_claims_count", "Loss Yr4 Claims", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_year",     "Loss Yr5 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_premium",  "Loss Yr5 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_losses",   "Loss Yr5 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_claims_count", "Loss Yr5 Claims", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr6_year",     "Loss Yr6 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr6_premium",  "Loss Yr6 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr6_losses",   "Loss Yr6 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr6_claims_count", "Loss Yr6 Claims", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr7_year",     "Loss Yr7 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr7_premium",  "Loss Yr7 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr7_losses",   "Loss Yr7 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr7_claims_count", "Loss Yr7 Claims", FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),

        # ── RISK FLAGS ────────────────────────────────────────
        O("pending_litigation",         "Pending Litigation",            FieldType.YESNO,  FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,  description="Any pending litigation or known circumstances"),
        O("pending_litigation_detail",  "Pending Litigation Detail",     FieldType.TEXT,   FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False, description="Details of any pending litigation"),
        O("prior_declinatures",         "Prior Declinatures",            FieldType.YESNO,  FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,  description="Any prior declinatures or special terms imposed"),
        O("prior_declinatures_detail",  "Prior Declinatures Detail",     FieldType.TEXT,   FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False, description="Details of any prior declinatures"),
        O("insurer_switch_flag",        "Insurer Switch",                FieldType.BOOLEAN,FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False, description="TRUE if insurer changed in last 2 years"),
        O("insurer_switch_reason",      "Insurer Switch Reason",         FieldType.TEXT,   FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False, description="Reason given for insurer change"),
        O("prior_insurer",              "Prior Insurer",                 FieldType.TEXT,   FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False, description="Name of prior insurer"),
        O("risk_improvements",          "Risk Improvements",             FieldType.TEXT,   FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False, description="Any risk improvements cited by broker"),
        O("risk_improvements_verified", "Risk Improvements Verified",    FieldType.BOOLEAN,FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False, description="Whether risk improvements have been independently verified"),
        O("broker_name",                "Broker",                        FieldType.TEXT,   FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False),

        # ── UNDERWRITER ANALYTICS ─────────────────────────────
        # These are arrays — in summary report only, not flattened to CSV
        O("uw_analyst_flags",           "UW Analyst Flags",              FieldType.ARRAY,  FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False, description="RED/AMBER/INFO flags raised by AI analyst"),
        O("data_conflicts",             "Data Conflicts",                FieldType.ARRAY,  FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False, description="Conflicting data points identified and reconciled"),
        O("questions_for_broker",       "Questions for Broker",          FieldType.ARRAY,  FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False, description="Specific questions generated from gaps and flags"),

        # Scalar analytics summaries (in CSV)
        O("raw_avg_loss_ratio",         "Raw Avg Loss Ratio",            FieldType.PERCENT, FieldSource.DERIVED,  FieldSection.ANALYTICS, critical=False, gap_check=False, description="Derived from loss history array"),
        O("data_quality_score",         "Data Quality Score",            FieldType.NUMBER,  FieldSource.DERIVED,  FieldSection.ANALYTICS, critical=False, gap_check=False, description="0-100 score from gap analysis"),
        O("critical_gaps_count",        "Critical Gaps Count",           FieldType.NUMBER,  FieldSource.DERIVED,  FieldSection.ANALYTICS, critical=False, gap_check=False),
        O("advisory_gaps_count",        "Advisory Gaps Count",           FieldType.NUMBER,  FieldSource.DERIVED,  FieldSection.ANALYTICS, critical=False, gap_check=False),
        O("extraction_confidence",      "Extraction Confidence",         FieldType.TEXT,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, gap_check=False, in_summary=False),
        O("extraction_notes",           "Extraction Notes",              FieldType.TEXT,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, gap_check=False, in_summary=False),
    ]

    # ── SYSTEM PROMPT ─────────────────────────────────────────
    SYSTEM_PROMPT = """You are a senior London Market casualty underwriting analyst at Pine Walk, \
a specialty MGA. You have 15+ years experience pricing casualty liability risks across GL, PL, EL, \
PI and D&O. You think and act like an experienced underwriter assistant — not a data entry clerk.

You will receive text extracted from a broker submission (email, PDF slip, Excel, Word). \
Your job is to extract, reconcile, and critically assess all available information, \
then return structured JSON with embedded underwriting judgement.

════════════════════════════════════════════
HOW TO THINK ABOUT THE DATA
════════════════════════════════════════════

RECONCILIATION — when the same field appears multiple times with different values:
- Prefer the most recent document over older ones
- Prefer structured data (slip, schedule) over email narrative
- Prefer specific figures over rounded ones (£1,234,567 over "approx £1.2m")
- Where values conflict materially, use the more conservative figure and flag the conflict
- Never silently drop a conflicting figure — record it in data_conflicts

LOSS HISTORY JUDGEMENT:
- Most recent policy year losses are almost always UNDERDEVELOPED — paid figures will be \
below ultimate. Flag this explicitly if the current year shows low paid with open reserves
- If a broker presents only paid losses with no outstanding reserves, treat as incomplete \
and flag — incurred = paid + outstanding, not just paid
- Calculate implied loss ratios for each year. A year with 0% LR in an active business \
is suspicious — flag it
- If the loss history shows a sudden improvement in the most recent 1-2 years after \
adverse prior years, flag potential favourable selection of data window
- Large losses should be cross-referenced: if a year shows high aggregate losses, \
there should be a corresponding large loss entry — flag if missing
- If claims count is provided, sense-check against loss quantum

EXPOSURE SENSE CHECKS:
- Revenue/payroll should be broadly consistent with employee count and industry sector
- If revenue has grown significantly year-on-year, prior year loss ratios need \
on-levelling — flag material exposure growth (>15% year on year)
- For UK EL: statutory minimum £5m limit — flag if limit is below this
- For US-exposed risks: flag if territorial scope includes US/Canada but limits look light

PREMIUM SENSE CHECK:
- Rate-on-line (premium / limit) should be in a credible range for the class
- Standard UK casualty: 0.1%-2% RoL depending on excess point and class
- Check if prior year premium is available — calculate implied rate change

POLICY STRUCTURE RED FLAGS:
- Retro date gap: claims-made policy where retro date is less than 5 years back without explanation
- Mid-term insurer switch in last 2 years — ask why
- SIR/deductible >10% of limit — moral hazard consideration
- US/Canada territory on a UK-domiciled insured — jurisdictional exposure uplift needed
- Aggregate limit equal to any-one-claim limit — no true aggregate protection
- Prior declinatures — always a red flag, record verbatim
- Pending litigation / known circumstances — must be explicitly excluded or priced

BROKER FRAMING AWARENESS:
- "Clean loss record" with no supporting data — require evidence
- Loss history starting from a convenient recent date — ask for full 5-year minimum
- Revenue described as "stable" but no year-on-year figures — request schedule
- Risk improvements listed without dates or verification — treat as unconfirmed

════════════════════════════════════════════
OUTPUT RULES
════════════════════════════════════════════

- Return ONLY valid JSON — no markdown, no preamble, no explanation outside the JSON
- Use null for genuinely absent fields — never invent or estimate values
- Monetary amounts: store as numeric string e.g. "1250000", currency in companion field
- Loss history: most recent year first, one object per year
- Large loss threshold: any single loss >£100,000 OR >10% of that year's annual premium
- coverage_trigger: exactly "Claims-Made", "Occurrence", or "Unknown"
- Coverage Y/N flags: exactly "Y", "N", or "Unknown"
- uw_analyst_flags: be specific and direct — think like a senior u/w reviewing this risk

Return this exact JSON structure:

{
  "insured_name": null,
  "insured_country": null,
  "industry_sector": null,
  "industry_sic_code": null,
  "annual_revenue": null,
  "annual_revenue_currency": null,
  "annual_payroll": null,
  "annual_payroll_currency": null,
  "number_of_employees": null,
  "revenue_growth_flag": null,

  "policy_period_start": null,
  "policy_period_end": null,
  "coverage_trigger": null,
  "retroactive_date": null,
  "retro_date_adequacy": null,
  "jurisdiction": null,
  "territorial_scope": null,
  "us_canada_exposure": false,

  "limit_any_one_claim": null,
  "limit_any_one_claim_currency": null,
  "limit_aggregate": null,
  "excess_point": null,
  "deductible": null,
  "sir_as_pct_of_limit": null,
  "sublimits": null,

  "coverage_gl": "Unknown",
  "coverage_pl": "Unknown",
  "coverage_el": "Unknown",
  "coverage_pi": "Unknown",
  "coverage_do": "Unknown",

  "premium_sought_gross": null,
  "premium_sought_currency": null,
  "brokerage_pct": null,
  "premium_net_of_brokerage": null,
  "premium_basis": null,
  "prior_premium": null,
  "implied_rate_change_pct": null,
  "rate_on_line_pct": null,

  "loss_history": [
    {
      "year": null,
      "premium": null,
      "losses_paid": null,
      "losses_outstanding": null,
      "losses_total_incurred": null,
      "claims_count": null,
      "implied_loss_ratio_pct": null,
      "large_loss_flag": false,
      "development_warning": null,
      "notes": null
    }
  ],

  "loss_history_completeness": null,
  "loss_history_years_provided": null,
  "avg_loss_ratio_all_years_pct": null,
  "avg_loss_ratio_ex_large_pct": null,
  "loss_trend_direction": null,

  "large_losses": [
    {
      "year": null,
      "amount": null,
      "description": null,
      "status": null,
      "reserved_adequacy_comment": null
    }
  ],

  "ibnr_commentary": null,
  "pending_litigation": null,
  "pending_litigation_detail": null,
  "prior_declinatures": null,
  "prior_declinatures_detail": null,
  "prior_insurer": null,
  "insurer_switch_flag": false,
  "insurer_switch_reason": null,
  "risk_improvements": null,
  "risk_improvements_verified": false,
  "broker_name": null,

  "data_conflicts": [
    {
      "field": null,
      "value_a": null,
      "value_b": null,
      "source_a": null,
      "source_b": null,
      "resolution": null
    }
  ],

  "uw_analyst_flags": [
    {
      "severity": "RED / AMBER / INFO",
      "category": "Loss History / Exposure / Structure / Coverage / Broker Framing / Compliance",
      "flag": "concise flag title",
      "detail": "specific detail explaining why this is flagged and what action is needed"
    }
  ],

  "questions_for_broker": [],

  "notable_features": [],
  "extraction_confidence": "High / Medium / Low",
  "extraction_notes": null
}"""