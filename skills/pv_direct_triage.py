# ============================================================
#  skills/pv_direct_triage.py
#  Political Violence & Terrorism — Direct Market Triage
#  Pricing | Submission Analyser
#
#  Purpose: rapid go/no-go triage for PV/T risks going direct
#  to the Lloyd's or company market.
#
#  Extracts ~20 core submission fields plus 8 RAG-rated triage
#  flags (🟢 GREEN / 🟡 AMBER / 🔴 RED) covering:
#    1. Direct market placement type
#    2. Country risk
#    3. Sanctions exposure
#    4. Rate adequacy
#    5. Data completeness
#    6. Known circumstances / prior losses
#    7. Prior declinatures
#    8. Structural complexity / appetite fit
#
#  Outputs:
#    - Standard summary report + submission_data.csv (core fields)
#    - triage_direct.csv (RAG flags matrix, appends per run)
# ============================================================

from skills.base import (
    BaseSkill, OutputField, TabConfig,
    FieldType, FieldSource, FieldSection
)

O = OutputField


class PVDirectTriageSkill(BaseSkill):

    META = {
        "label":       "PV Direct Triage",
        "code":        "PVDT",
        "version":     "1.0",
        "description": (
            "Political Violence & Terrorism direct-to-market triage. "
            "Extracts ~20 core fields plus 8 RAG-rated flags "
            "(🟢 GREEN / 🟡 AMBER / 🔴 RED) across placement type, "
            "country risk, sanctions, rate, data quality, known "
            "circumstances, prior declinatures, and structure. "
            "Produces triage_direct.csv for portfolio tracking."
        ),
    }

    TABS = [
        TabConfig(FieldSection.INSURED,   icon="🏢", default_on=True,  description="Identity, placement type and territorial exposure"),
        TabConfig(FieldSection.LIMITS,    icon="🔢", default_on=True,  description="Cover type, limit, excess and BI"),
        TabConfig(FieldSection.PREMIUM,   icon="💷", default_on=True,  description="Premium sought, commission and rate metrics"),
        TabConfig(FieldSection.FLAGS,     icon="🚦", default_on=True,  description="Eight RAG triage flags and overall recommendation"),
        TabConfig(FieldSection.ANALYTICS, icon="🚩", default_on=True,  description="UW flags and questions for broker"),
    ]

    CLAIMS_SCHEMA = []   # no claims CSV for triage

    OUTPUT_SCHEMA = [

        # ── INSURED & EXPOSURE ────────────────────────────────
        O("insured_name",         "Insured Name",               FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,
          description="Full legal name of primary insured"),
        O("broker_name",          "Broker",                     FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=False),
        O("direct_to_market",     "Direct to Market",           FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,
          description="Y if placed direct to Lloyd's / company market; N if coverholder, DUA or delegated authority"),
        O("insured_country",      "Country of Domicile",        FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,
          description="Primary country where the insured is domiciled"),
        O("risk_type",            "Risk Type",                  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,
          description="Warehouse Stock / National Infrastructure / Industrial Services / Global Office/Financial / Other"),
        O("tiv_total",            "Total TIV",                  FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,
          description="Aggregate Total Insured Value across all locations"),
        O("tiv_currency",         "TIV Currency",               FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=False, gap_check=False),
        O("location_count",       "No. of Locations",           FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("territorial_scope",    "Territorial Scope",          FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True,
          description="Countries / regions covered — finite schedule or broad territorial wording"),
        O("policy_period_start",  "Policy Start",               FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("policy_period_end",    "Policy End",                 FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),
        O("renewal_or_new",       "Renewal / New",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,  critical=False,
          description="Renewal / New Business / Transfer"),
        O("sov_provided",         "SOV Provided",               FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.INSURED,  critical=True),

        # ── LIMITS & STRUCTURE ────────────────────────────────
        O("cover_type",           "Cover Type",                 FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True,
          description="T&S Only / Full PV / Full PV + War / Full PV + War + Liability"),
        O("peril_war",            "War Extension",              FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True),
        O("limit_aoo",            "Limit (Any One Occurrence)", FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True),
        O("limit_currency",       "Limit Currency",             FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=False, gap_check=False),
        O("excess_point",         "Excess / Attachment",        FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=True,
          description="0 if primary layer"),
        O("deductible",           "PD Deductible",              FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=False),
        O("bi_covered",           "BI Covered",                 FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.LIMITS,   critical=False),

        # ── PREMIUM & RATES ───────────────────────────────────
        O("premium_sought_gross", "Premium Sought (Gross)",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=True),
        O("premium_currency",     "Premium Currency",           FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=False, gap_check=False),
        O("commission_pct",       "Commission %",               FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=False),
        O("prior_premium",        "Prior Year Premium",         FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,  critical=False),
        O("rate_on_line_pct",     "Rate on Line %",             FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,  critical=False, gap_check=False,
          description="Gross premium ÷ Limit × 100 — calculated by the app"),
        O("rate_on_tiv_pct",      "Rate on TIV %",              FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,  critical=False, gap_check=False,
          description="Gross premium ÷ TIV × 100 — calculated by the app"),

        # ── RAG TRIAGE FLAGS ──────────────────────────────────
        #  Values must begin with one of:
        #    🟢 GREEN — <one-line reason>
        #    🟡 AMBER — <one-line reason>
        #    🔴 RED   — <one-line reason>
        O("flag_direct_to_market",     "🚦 Direct Market Placement", FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,
          description="GREEN: direct Lloyd's/company market placement  |  AMBER: coverholder or DUA  |  RED: unclear or unapproved route to market"),
        O("flag_country_risk",         "🚦 Country Risk",            FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,
          description="GREEN: low/stable political environment  |  AMBER: moderate or elevated risk  |  RED: high/extreme or active conflict zone"),
        O("flag_sanctions",            "🚦 Sanctions Exposure",      FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,
          description="GREEN: no exposure identified  |  AMBER: indirect or possible nexus  |  RED: confirmed OFAC / UK / EU sanctions link"),
        O("flag_rate_adequacy",        "🚦 Rate Adequacy",           FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,
          description="GREEN: rate appears adequate for territory and cover type  |  AMBER: potentially low  |  RED: materially below market benchmark"),
        O("flag_data_completeness",    "🚦 Data Completeness",       FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,
          description="GREEN: SOV and full loss history provided  |  AMBER: partial data, key items outstanding  |  RED: critical data absent (no TIV or no SOV)"),
        O("flag_known_circumstances",  "🚦 Known Circumstances",     FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,
          description="GREEN: none declared  |  AMBER: under query or unclear  |  RED: known losses or circumstances confirmed"),
        O("flag_prior_declinatures",   "🚦 Prior Declinatures",      FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True,
          description="GREEN: none declared  |  AMBER: queried by prior markets  |  RED: formally declined by other markets"),
        O("flag_structure_complexity", "🚦 Structure / Appetite",    FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False,
          description="GREEN: standard structure, within appetite  |  AMBER: some complexity (e.g. War ext, high BI)  |  RED: highly complex or outside appetite"),

        # Overall recommendation (also in FLAGS tab)
        O("triage_recommendation",     "Triage Recommendation",     FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False,
          description="FAST-TRACK / REFER TO FULL ANALYSIS / QUERY BROKER / DECLINE"),
        O("triage_rationale",          "Triage Rationale",          FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=False,
          description="One concise sentence summarising the triage decision"),

        # ── ANALYTICS ─────────────────────────────────────────
        O("uw_analyst_flags",     "UW Flags",                   FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False,
          description='List of {"severity": "RED|AMBER|INFO", "flag": "title", "detail": "one line"}'),
        O("questions_for_broker", "Questions for Broker",       FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False),
        O("extraction_confidence","Extraction Confidence",      FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, gap_check=False, in_summary=False),
    ]

    # ── SYSTEM PROMPT ─────────────────────────────────────────
    SYSTEM_PROMPT = """You are a senior London Market Political Violence and Terrorism underwriter \
at Pine Walk performing a DIRECT-TO-MARKET TRIAGE assessment. Your task is to extract core \
submission data and apply a structured RAG (Red / Amber / Green) rating to 8 key triage dimensions.

Speed and accuracy matter equally. Focus on the fields below. Do not pad the response.

════════════════════════════════════════════
STEP 1 — EXTRACT CORE FIELDS
════════════════════════════════════════════

Extract these fields from the submission documents:

  insured_name          Full legal name of primary insured
  broker_name           Placing broker
  direct_to_market      Y if direct Lloyd's or company-market placement; N if coverholder / DUA / binder
  insured_country       Primary country of domicile
  risk_type             One of: Warehouse Stock / National Infrastructure / Industrial Services / Global Office/Financial / Other
  tiv_total             Aggregate Total Insured Value (numeric string, no symbols)
  tiv_currency          Currency of TIV
  location_count        Number of insured locations
  territorial_scope     Countries or regions covered
  policy_period_start   YYYY-MM-DD
  policy_period_end     YYYY-MM-DD
  renewal_or_new        Renewal / New Business / Transfer
  sov_provided          Y / N / Unknown — whether a Schedule of Values was submitted
  cover_type            T&S Only / Full PV / Full PV + War / Full PV + War + Liability
  peril_war             Y / N / Unknown — War extension in scope
  limit_aoo             Limit any one occurrence (numeric string)
  limit_currency        Currency of limit
  excess_point          Excess / attachment point (0 if primary layer)
  deductible            PD deductible amount (numeric string)
  bi_covered            Y / N / Unknown — Business Interruption included
  premium_sought_gross  Gross premium sought (numeric string)
  premium_currency      Currency of premium
  commission_pct        Commission percentage (numeric string)
  prior_premium         Prior year premium (numeric string), null if new business


════════════════════════════════════════════
STEP 2 — ASSIGN 8 RAG TRIAGE FLAGS
════════════════════════════════════════════

For each flag, return a string starting with exactly one of:
  🟢 GREEN — <concise reason, max 15 words>
  🟡 AMBER — <concise reason, max 15 words>
  🔴 RED   — <concise reason, max 15 words>

Apply these criteria:

FLAG 1 — flag_direct_to_market  (Direct Market Placement)
  🟢 GREEN  Confirmed direct placement to Lloyd's syndicate(s) or company market
  🟡 AMBER  Coverholder, DUA, or delegated authority arrangement
  🔴 RED    Route to market unclear, unapproved intermediary, or not stated

FLAG 2 — flag_country_risk  (Country Risk)
  Assess the primary country and all countries in territorial scope.
  🟢 GREEN  All locations in low / stable political-risk territories (e.g. Western Europe, North America, Japan, Australia)
  🟡 AMBER  Some locations in moderate or elevated risk territory (e.g. parts of LatAm, SE Asia, Eastern Europe, MENA stable states)
  🔴 RED    Any location in high / extreme risk or active conflict zone (e.g. Ukraine, Sudan, Myanmar, Haiti, Yemen, Libya)
            Also RED if territorial scope is very broad (e.g. "Worldwide") with no further detail

FLAG 3 — flag_sanctions  (Sanctions Exposure)
  Consider OFAC (US), UK HMT, and EU sanctions lists.
  🟢 GREEN  No sanctioned territories, entities, or persons identified in submission
  🟡 AMBER  Indirect exposure possible (e.g. parent company with global ops, ambiguous territorial scope)
  🔴 RED    Any confirmed or highly probable link to sanctioned jurisdiction, entity, or person
            Automatically RED for: Cuba, Iran, North Korea, Russia (post-2022), Syria, Venezuela (Maduro regime), Belarus (post-2021)

FLAG 4 — flag_rate_adequacy  (Rate Adequacy)
  Assess Rate on Line (gross premium / limit × 100) against territory and cover benchmarks.
  Very approximate benchmarks — use your market knowledge, not these numbers:
    T&S only, stable territory:        RoL 0.05–0.15%
    Full PV, moderate territory:       RoL 0.15–0.40%
    Full PV + War, elevated territory: RoL 0.40–1.00%+
    War-adjacent / high risk:          RoL 1.00%+
  🟢 GREEN  Rate appears adequate or above market for the territory and cover type
  🟡 AMBER  Rate appears potentially low — within 50% of expected
  🔴 RED    Rate appears materially below market — less than 50% of expected benchmark

FLAG 5 — flag_data_completeness  (Data Completeness)
  🟢 GREEN  TIV confirmed, full SOV provided, 3+ years loss history present
  🟡 AMBER  TIV confirmed but SOV absent, or loss history incomplete (1–2 years), or minor gaps
  🔴 RED    TIV absent or not confirmed, no SOV at all, or no loss history on a risk that requires it

FLAG 6 — flag_known_circumstances  (Known Circumstances)
  🟢 GREEN  No known circumstances, open claims, or prior losses declared
  🟡 AMBER  Prior losses declared but paid/closed; or situation under query / requires clarification
  🔴 RED    Active or open claim; known circumstances not yet resolved; or suspicion of non-disclosure

FLAG 7 — flag_prior_declinatures  (Prior Declinatures)
  🟢 GREEN  No prior declinatures declared or evidenced
  🟡 AMBER  Risk previously queried or placed with difficulty but not formally declined
  🔴 RED    Formally declined by one or more markets; or indication of market withdrawal

FLAG 8 — flag_structure_complexity  (Structure / Appetite Fit)
  Consider cover type, BI inclusion, War extension, deductible structure, and territorial breadth.
  🟢 GREEN  Standard PV structure (T&S or Full PV primary layer), finite territories, within normal appetite
  🟡 AMBER  Added complexity: BI coverage, War extension, broad territorial scope, or unusual wording
  🔴 RED    Highly complex, layered, or manuscript structure; or outside standard appetite
            (e.g. primary War cover in conflict zone, full Worldwide War, large aggregate BI)


════════════════════════════════════════════
STEP 3 — OVERALL TRIAGE RECOMMENDATION
════════════════════════════════════════════

Set triage_recommendation to exactly one of:
  FAST-TRACK              No RED flags, ≤2 AMBER flags, adequate data → proceed directly to pricing
  REFER TO FULL ANALYSIS  Risk is within appetite but needs detailed PV skill (complex structure, high TIV, War ext)
  QUERY BROKER            Missing critical data or ambiguity that must be resolved before pricing
  DECLINE                 One or more hard show-stoppers (confirmed sanctions, known circumstances, out-of-appetite structure)

Set triage_rationale to a single sentence (max 25 words) summarising the key driver of the recommendation.


════════════════════════════════════════════
STEP 4 — UW FLAGS (optional, max 5)
════════════════════════════════════════════

List up to 5 concise underwriting flags. Prioritise RED show-stoppers, then key AMBERs.
Format each as: {"severity": "RED|AMBER|INFO", "flag": "short title", "detail": "one line"}

Also list up to 5 questions_for_broker as plain strings.


════════════════════════════════════════════
OUTPUT RULES
════════════════════════════════════════════

- Return ONLY valid JSON — no markdown, no preamble, no trailing text
- null for absent fields — never invent data
- Monetary amounts: numeric string without currency symbols e.g. "5000000"
- Y / N fields: exactly "Y", "N", or "Unknown"
- RAG flag fields: must start with 🟢 GREEN, 🟡 AMBER, or 🔴 RED followed by " — " and a reason

Return this exact JSON structure:

{
  "insured_name": null,
  "broker_name": null,
  "direct_to_market": "Unknown",
  "insured_country": null,
  "risk_type": null,
  "tiv_total": null,
  "tiv_currency": null,
  "location_count": null,
  "territorial_scope": null,
  "policy_period_start": null,
  "policy_period_end": null,
  "renewal_or_new": null,
  "sov_provided": "Unknown",

  "cover_type": null,
  "peril_war": "Unknown",
  "limit_aoo": null,
  "limit_currency": null,
  "excess_point": null,
  "deductible": null,
  "bi_covered": "Unknown",

  "premium_sought_gross": null,
  "premium_currency": null,
  "commission_pct": null,
  "prior_premium": null,

  "flag_direct_to_market":     "🟢 GREEN — <reason>",
  "flag_country_risk":         "🟢 GREEN — <reason>",
  "flag_sanctions":            "🟢 GREEN — <reason>",
  "flag_rate_adequacy":        "🟢 GREEN — <reason>",
  "flag_data_completeness":    "🟢 GREEN — <reason>",
  "flag_known_circumstances":  "🟢 GREEN — <reason>",
  "flag_prior_declinatures":   "🟢 GREEN — <reason>",
  "flag_structure_complexity": "🟢 GREEN — <reason>",

  "triage_recommendation": null,
  "triage_rationale": null,

  "uw_analyst_flags": [],
  "questions_for_broker": [],

  "extraction_confidence": "High / Medium / Low"
}"""
