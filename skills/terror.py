# ============================================================
#  skills/terror.py
#  Political Violence & Terrorism — London Market
#  Pricing | Submission Analyser
#
#  Covers: T&S only, Full PV, War/Civil War extensions,
#          PV Liability, BI/ICOW, all standard risk types:
#          Warehouse Stock, National Infrastructure,
#          Industrial Services, Global Office/Financial
# ============================================================

from skills.base import (
    BaseSkill, OutputField, TabConfig,
    FieldType, FieldSource, FieldSection
)

O = OutputField


class TerrorSkill(BaseSkill):

    META = {
        "label":       "Political Violence & Terrorism",
        "code":        "PVT",
        "version":     "1.0",
        "description": "London Market political violence and terrorism. "
                       "T&S only through full PV including War/Civil War. "
                       "Covers Warehouse Stock, National Infrastructure, "
                       "Industrial Services, and Global Office/Financial risk types.",
    }

    # ── TAB CONFIGURATION ─────────────────────────────────────

    TABS = [
        TabConfig(FieldSection.INSURED,   icon="🏢", default_on=True,  description="Insured identity, business activity, group structure"),
        TabConfig(FieldSection.POLICY,    icon="📄", default_on=True,  description="Policy period, wording form, law & jurisdiction"),
        TabConfig(FieldSection.LOCATIONS, icon="📍", default_on=True,  description="Schedule of values, location detail, TIV breakdown"),
        TabConfig(FieldSection.PERILS,    icon="💥", default_on=True,  description="Cover type, peril structure, occurrence definition, exclusions"),
        TabConfig(FieldSection.LIMITS,    icon="🔢", default_on=True,  description="Limits of indemnity, deductibles, AOO vs aggregate"),
        TabConfig(FieldSection.BI_EXT,    icon="🔄", default_on=True,  description="BI cover, indemnity period, ICOW, denial of access, extensions"),
        TabConfig(FieldSection.PREMIUM,   icon="💷", default_on=True,  description="Premium, commission, NCB, rate on line, rate on TIV"),
        TabConfig(FieldSection.LOSS,      icon="📉", default_on=True,  description="Loss history, declarations, prior claims"),
        TabConfig(FieldSection.GEO,       icon="🌍", default_on=True,  description="Country risk assessment, accumulation, sanctions, geopolitical flags"),
        TabConfig(FieldSection.FLAGS,     icon="⚠️", default_on=True,  description="Compliance, sanctions, prior declinatures, known circumstances"),
        TabConfig(FieldSection.RATER,     icon="🧮", default_on=True,  description="Structured rater inputs — exposure, layer, TIV, currency"),
        TabConfig(FieldSection.ANALYTICS, icon="🚩", default_on=True,  description="UW analyst flags, data conflicts, broker questions"),
        TabConfig(FieldSection.GEO_VIZ,   icon="🗺️", default_on=True,  description="Interactive location map, Street View and satellite imagery"),
    ]

    # ── CLAIMS CSV SCHEMA ─────────────────────────────────────

    CLAIMS_SCHEMA = [
        "Segment_1",
        "Segment_2",
        "underwriting_year",
        "claim_id",
        "loss_date",
        "reported_date",
        "insured",
        "location",
        "country",
        "peril",
        "claim_description",
        "status",
        "paid",
        "outstanding",
        "incurred",
        "Manual Claim Adjustments",
    ]

    # ── OUTPUT SCHEMA ─────────────────────────────────────────

    OUTPUT_SCHEMA = [

        # ── INSURED & EXPOSURE ────────────────────────────────
        O("insured_name",           "Insured Name",                  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Full legal name of primary insured"),
        O("insured_group",          "Insured Group / Affiliates",    FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, description="Parent, subsidiaries, JVs, managed entities within scope"),
        O("insured_country",        "Country of Domicile",           FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Primary country where insured is domiciled"),
        O("business_activity",      "Business Activity / Operations",FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Narrative of operations — warehousing, infrastructure, industrial, financial services etc."),
        O("risk_type",              "Risk Type",                     FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=True,  description="Warehouse Stock / National Infrastructure / Industrial Services / Global Office/Financial"),
        O("broker_name",            "Broker",                        FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False),
        O("coverholder",            "Coverholder / MGA",             FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.INSURED,   critical=False, description="Coverholder if delegated authority risk"),

        # ── POLICY STRUCTURE ──────────────────────────────────
        O("policy_period_start",    "Policy Period Start",           FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True),
        O("policy_period_end",      "Policy Period End",             FieldType.DATE,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True),
        O("wording_form",           "Wording / Form Reference",      FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Policy form family — market standard (e.g. LSW1135, NMA2918) or bespoke"),
        O("wording_type",           "Wording Type",                  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=False, description="Market standard / Bespoke / Manuscript"),
        O("claims_basis",           "Claims Basis",                  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True,  description="Occurrence (standard for PV property) or Claims-Made"),
        O("jurisdiction",           "Governing Law / Jurisdiction",  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=True),
        O("prior_insurer",          "Prior Insurer(s)",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=False),
        O("prior_premium",          "Prior Year Premium",            FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.POLICY,    critical=False),
        O("renewal_or_new",         "Renewal or New Business",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=False, description="Renewal / New Business / Transfer"),
        O("payment_terms",          "Premium Payment Terms",         FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.POLICY,    critical=False, description="Payment warranty period — failure may trigger cancellation"),

        # ── LOCATIONS & SOV ───────────────────────────────────
        O("territorial_scope",      "Territorial Scope",             FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=True,  description="Countries / regions covered — finite schedule or broad territorial wording"),
        O("location_count",         "Number of Locations",           FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=True,  description="Total number of insured locations"),
        O("tiv_total",              "Total Insured Value (TIV)",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=True,  description="Aggregate TIV across all locations — primary rating exposure base"),
        O("tiv_currency",           "TIV Currency",                  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=True,  gap_check=False),
        O("tiv_pd",                 "TIV — Property Damage",         FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, description="PD component of TIV"),
        O("tiv_bi",                 "TIV — Business Interruption",   FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, description="BI / revenue / gross profit declared value"),
        O("tiv_stock",              "TIV — Stock / Contents",        FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, description="Stock, machinery, contents values"),
        O("sov_provided",           "SOV / Location Schedule Provided", FieldType.YESNO, FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=True,  description="Whether a Schedule of Values with per-location detail was provided"),
        O("largest_location_tiv",   "Largest Single Location TIV",   FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, description="TIV of the largest individual location — MPL indicator"),
        O("largest_location_name",  "Largest Location Name / City",  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False),
        O("highest_risk_country",   "Highest Risk Country",          FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, description="Country with highest TIV concentration or highest geopolitical risk"),
        O("accumulation_comment",   "Accumulation / Concentration",  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, description="AI assessment of geographic concentration risk — multiple locations in same city/zone"),
        O("sov_locations",          "Location Detail (SOV)",         FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, in_csv=False,
          description="Array of per-location detail extracted from SOV"),
        O("automatic_additions_pct","Automatic Additions Cap (%)",   FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.LOCATIONS, critical=False, description="% of declared values for automatic new acquisitions"),

        # ── PERIL STRUCTURE ───────────────────────────────────
        O("cover_type",             "Cover Type",                    FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PERILS,    critical=True,  description="T&S Only / Full PV / Full PV + War / Full PV + War + Liability"),
        O("peril_terrorism",        "Terrorism & Sabotage",          FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=True),
        O("peril_rscc",             "Riots / Strikes / Civil Commotion", FieldType.YESNO,FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False),
        O("peril_malicious_damage", "Malicious Damage",              FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False),
        O("peril_insurrection",     "Insurrection / Revolution",     FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False),
        O("peril_war",              "War / Civil War",               FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False, description="War / Civil War extension — significantly increases exposure"),
        O("peril_pv_liability",     "PV Liability Extension",        FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False, description="Third party liability arising from PV perils — common on infrastructure"),
        O("occurrence_definition",  "Occurrence Time Window",        FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PERILS,    critical=True,  description="Hours clause for aggregating PV losses — typically 72hrs; War/CW may differ"),
        O("war_time_window",        "War / Civil War Time Window",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False, description="Extended time window for War/CW occurrences — often 168hrs or longer"),
        O("exclusions_nuclear",     "Nuclear / CBRN Exclusion",      FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=True,  description="Nuclear, chemical, biological, radiological exclusion"),
        O("exclusions_cyber",       "Cyber Exclusion",               FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=True,  description="Cyber / electronic attack exclusion"),
        O("exclusions_td_pipelines","T&D / Pipeline Exclusion",      FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False, description="Transmission & distribution lines / pipelines exclusion — common on infrastructure"),
        O("exclusions_pollution",   "Pollution / Contamination Excl",FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False),
        O("exclusions_other",       "Other Notable Exclusions",      FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False),
        O("sanctions_clause",       "Sanctions Clause",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PERILS,    critical=True,  description="Sanctions limitation or suspension clause reference"),
        O("territorial_carveouts",  "Territorial Carve-Outs",        FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PERILS,    critical=False, description="Specific country/region exclusions — sanctions-linked or heightened geopolitical risk"),

        # ── LIMITS & STRUCTURE ────────────────────────────────
        O("limit_any_one_occurrence","Limit Any One Occurrence",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  description="Maximum indemnity any one occurrence"),
        O("limit_currency",         "Limit Currency",                FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  gap_check=False),
        O("limit_aggregate",        "Annual Aggregate Limit",        FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  description="Annual aggregate — if equal to AOO, effectively no aggregate protection"),
        O("limit_pv_liability",     "PV Liability Limit",            FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="Separate limit for PV Liability extension if applicable"),
        O("excess_point",           "Excess / Attachment Point",     FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  description="Point above which this layer responds — 0 if primary"),
        O("layer_structure",        "Layer Structure",               FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="Primary / Excess / Quota share — layer position in programme"),
        O("deductible_pd",          "PD Deductible",                 FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=True,  description="Monetary deductible for property damage"),
        O("deductible_bi",          "BI Time Deductible",            FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="Time deductible for BI — e.g. 30 days / 168 hours"),
        O("deductible_notes",       "Deductible Notes",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="Peril-specific deductible variations or structure notes"),
        O("limit_options",          "Limit Options Offered",         FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LIMITS,    critical=False, description="If broker has requested quotes at multiple limit options"),

        # ── BI & EXTENSIONS ───────────────────────────────────
        O("bi_covered",             "Business Interruption Covered", FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=True,  description="Whether BI is included — Warehouse Stock sometimes PD only"),
        O("bi_sum_insured",         "BI Sum Insured",                FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="BI declared value / revenue / gross profit"),
        O("bi_indemnity_period",    "BI Indemnity Period",           FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="Maximum indemnity period — e.g. 12 months / 24 months"),
        O("icow_covered",           "ICOW Covered",                  FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="Increased Cost of Working"),
        O("icow_limit",             "ICOW Limit",                    FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False),
        O("denial_of_access",       "Denial of Access",              FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="BI when access restricted due to insured perils — often radius based"),
        O("denial_of_access_detail","Denial of Access Detail",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="Radius, sub-limit, indemnity period for DoA cover"),
        O("suppliers_customers",    "Suppliers / Customers Ext.",    FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="BI losses from damage at critical suppliers/customers"),
        O("suppliers_customers_limit","Suppliers / Customers Limit", FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False),
        O("utilities_extension",    "Utilities Extension",           FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False),
        O("data_reinstatement",     "Data / Electronic Assets",      FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="Reinstatement of data, computer equipment, portable devices"),
        O("data_limit",             "Data / Electronic Assets Limit",FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False),
        O("debris_removal",         "Debris Removal / Prof Fees",    FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="Debris removal, professional fees, expediting expenses — within SI or sub-limited"),
        O("public_authorities",     "Public Authorities / ICOC",     FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False, description="Increased cost of construction to comply with regulations"),
        O("waiver_subrogation",     "Waiver of Subrogation",         FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False),
        O("non_invalidation",       "Non-Invalidation Clause",       FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.BI_EXT,    critical=False),

        # ── PREMIUM ANALYTICS ─────────────────────────────────
        O("premium_sought_gross",   "Premium Sought (Gross)",        FieldType.CURRENCY, FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=True),
        O("premium_currency",       "Premium Currency",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, gap_check=False),
        O("commission_pct",         "Commission / Brokerage %",      FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False),
        O("ncb_requested",          "NCB Requested",                 FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, description="No claims bonus requested — amount or %"),
        O("premium_net",            "Net Premium",                   FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.PREMIUM,   critical=False, gap_check=False),
        O("rate_on_line_pct",       "Rate on Line % (gross)",        FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,   critical=False, gap_check=False, description="Gross premium / limit — key adequacy metric"),
        O("rate_on_tiv_pct",        "Rate on TIV % (gross)",         FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,   critical=False, gap_check=False, description="Gross premium / TIV — exposure rate check"),
        O("implied_rate_change_pct","Implied Rate Change %",         FieldType.PERCENT,  FieldSource.EXTRACTED, FieldSection.PREMIUM,   critical=False, description="AI calculated from current vs prior premium"),
        O("prior_rate_on_line_pct", "Prior Year RoL %",              FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.PREMIUM,   critical=False, gap_check=False),

        # ── LOSS HISTORY ──────────────────────────────────────
        O("loss_history_declaration","Loss Declaration Statement",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOSS,      critical=True,  description="'No known or reported losses' statement or equivalent declaration to inception"),
        O("loss_history_years_provided","Years of History Provided", FieldType.NUMBER,   FieldSource.EXTRACTED, FieldSection.LOSS,      critical=True),
        O("loss_history",           "Year-by-Year Loss Detail",      FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False, in_csv=False),
        O("large_losses",           "Large / Significant Losses",    FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False, in_csv=False),
        O("large_losses_flagged",   "Large Losses Identified",       FieldType.YESNO,    FieldSource.DERIVED,   FieldSection.LOSS,      critical=False, gap_check=False),
        O("large_losses_total",     "Large Losses Total",            FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.LOSS,      critical=False, gap_check=False),
        O("loss_history_completeness","Loss History Completeness",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.LOSS,      critical=False),

        # Loss history CSV columns (derived, flattened)
        O("loss_yr1_year",     "Loss Yr1 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr1_premium",  "Loss Yr1 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr1_losses",   "Loss Yr1 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr1_claims_count", "Loss Yr1 Claims",FieldType.DERIVED,FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_year",     "Loss Yr2 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_premium",  "Loss Yr2 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_losses",   "Loss Yr2 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr2_claims_count", "Loss Yr2 Claims",FieldType.DERIVED,FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_year",     "Loss Yr3 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_premium",  "Loss Yr3 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_losses",   "Loss Yr3 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr3_claims_count", "Loss Yr3 Claims",FieldType.DERIVED,FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_year",     "Loss Yr4 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_premium",  "Loss Yr4 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_losses",   "Loss Yr4 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr4_claims_count", "Loss Yr4 Claims",FieldType.DERIVED,FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_year",     "Loss Yr5 Year",     FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_premium",  "Loss Yr5 Premium",  FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_losses",   "Loss Yr5 Losses",   FieldType.DERIVED, FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),
        O("loss_yr5_claims_count", "Loss Yr5 Claims",FieldType.DERIVED,FieldSource.DERIVED, FieldSection.LOSS, in_summary=False, gap_check=False),

        # ── GEOPOLITICAL ASSESSMENT ───────────────────────────
        O("primary_country_risk",   "Primary Country Risk Rating",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.GEO,       critical=True,  description="AI assessment of primary territory geopolitical risk: Low/Moderate/Elevated/High/Extreme"),
        O("country_risk_rationale", "Country Risk Rationale",        FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.GEO,       critical=False, description="Brief rationale for country risk assessment based on known context"),
        O("sanctions_exposure",     "Sanctions Exposure",            FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.GEO,       critical=True,  description="Whether any territorial scope or named insured touches sanctioned jurisdictions"),
        O("accumulation_risk",      "Accumulation Risk",             FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.GEO,       critical=False, description="AI assessment: Low/Moderate/High — based on location clustering"),
        O("conflict_proximity",     "Proximity to Active Conflict",  FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.GEO,       critical=False, description="Whether any insured territories are proximate to or within active conflict zones"),
        O("political_stability",    "Political Stability Comment",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.GEO,       critical=False, description="AI comment on political stability in primary operating territory"),
        O("nat_pool_interaction",   "National Pool / TRIA Interaction", FieldType.TEXT,  FieldSource.EXTRACTED, FieldSection.GEO,       critical=False, description="Whether national terrorism pool (Pool Re, GAREAT, TRIA etc.) interacts with this risk"),

        # ── RISK FLAGS ────────────────────────────────────────
        O("pending_litigation",     "Pending Litigation / Known Circumstances", FieldType.YESNO, FieldSource.EXTRACTED, FieldSection.FLAGS, critical=True, description="Any known circumstances, incidents, or claims in progress"),
        O("pending_detail",         "Pending / Known Circumstances Detail", FieldType.TEXT, FieldSource.EXTRACTED, FieldSection.FLAGS,   critical=False),
        O("prior_declinatures",     "Prior Declinatures",            FieldType.YESNO,    FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=True),
        O("prior_declinatures_detail","Prior Declinatures Detail",   FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False),
        O("insurer_switch_flag",    "Insurer Switch",                FieldType.BOOLEAN,  FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False),
        O("insurer_switch_reason",  "Insurer Switch Reason",         FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False),
        O("claims_handling_notes",  "Claims Handling / Control",     FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False, description="Claims control language, nominated adjuster, payment on account"),
        O("non_cancellation",       "Non-Cancellation Clause",       FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.FLAGS,    critical=False, description="Non-cancellation except non-payment terms"),

        # ── RATER INPUTS ──────────────────────────────────────
        # Structured data ready to feed directly into pricing model
        O("rater_risk_type",        "Rater: Risk Type Code",         FieldType.TEXT,     FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False, description="Standardised: WHSE / INFRA / INDUS / OFFICE"),
        O("rater_cover_code",       "Rater: Cover Code",             FieldType.TEXT,     FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False, description="Standardised: TS / PV / PVW / PVWL"),
        O("rater_tiv",              "Rater: TIV",                    FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False, description="TIV in rating currency"),
        O("rater_currency",         "Rater: Currency",               FieldType.TEXT,     FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_limit",            "Rater: Limit",                  FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_excess",           "Rater: Excess / Attachment",    FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_deductible",       "Rater: PD Deductible",          FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_bi_flag",          "Rater: BI Included",            FieldType.YESNO,    FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_bi_tiv",           "Rater: BI TIV",                 FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_bi_period_months", "Rater: BI Period (months)",     FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_war_flag",         "Rater: War Extension",          FieldType.YESNO,    FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_liability_flag",   "Rater: Liability Extension",    FieldType.YESNO,    FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_liability_limit",  "Rater: Liability Limit",        FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_occurrence_hrs",   "Rater: Occurrence Window (hrs)",FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_primary_country",  "Rater: Primary Country",        FieldType.TEXT,     FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False, description="ISO 3166-1 alpha-2 country code for primary location"),
        O("rater_location_count",   "Rater: Location Count",         FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_premium_sought",   "Rater: Premium Sought",         FieldType.CURRENCY, FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_commission_pct",   "Rater: Commission %",           FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_rol_pct",          "Rater: Rate on Line %",         FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),
        O("rater_rot_pct",          "Rater: Rate on TIV %",          FieldType.PERCENT,  FieldSource.DERIVED,   FieldSection.RATER,    critical=False, gap_check=False),

        # ── UNDERWRITER ANALYTICS ─────────────────────────────
        O("uw_analyst_flags",       "UW Analyst Flags",              FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False),
        O("data_conflicts",         "Data Conflicts",                FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False),
        O("questions_for_broker",   "Questions for Broker",          FieldType.ARRAY,    FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, in_csv=False, gap_check=False),
        O("data_quality_score",     "Data Quality Score",            FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.ANALYTICS, critical=False, gap_check=False),
        O("critical_gaps_count",    "Critical Gaps Count",           FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.ANALYTICS, critical=False, gap_check=False),
        O("advisory_gaps_count",    "Advisory Gaps Count",           FieldType.NUMBER,   FieldSource.DERIVED,   FieldSection.ANALYTICS, critical=False, gap_check=False),
        O("extraction_confidence",  "Extraction Confidence",         FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, gap_check=False, in_summary=False),
        O("extraction_notes",       "Extraction Notes",              FieldType.TEXT,     FieldSource.EXTRACTED, FieldSection.ANALYTICS, critical=False, gap_check=False, in_summary=False),
    ]

    # ── SYSTEM PROMPT ─────────────────────────────────────────
    SYSTEM_PROMPT = """You are a senior London Market Political Violence and Terrorism \
underwriting analyst at Pine Walk, a specialty MGA. You have deep expertise in PV/T pricing \
across all standard risk types: Warehouse Stock, National Infrastructure, Industrial Services, \
and Global Office/Financial.

You will receive text extracted from a broker submission (email, PDF slip, Excel SOV, Word). \
Your job is to extract, reconcile, critically assess, and structure ALL available information, \
then return JSON with embedded underwriting judgement.

════════════════════════════════════════════
RISK TYPE RECOGNITION
════════════════════════════════════════════

Identify the risk type early — it shapes everything else:
- WAREHOUSE STOCK: consumer goods distribution, regional warehouses, storage hubs.
  Often PD only (no BI), high stock turnover, key question is peak stock values.
- NATIONAL INFRASTRUCTURE: transport networks, utilities, multi-asset programmes,
  large public-facing operations. PV Liability more common. T&D exclusions important.
  Accumulation across network is primary u/w concern.
- INDUSTRIAL SERVICES: manufacturing/depot/plant + mobile/rig operations.
  BI critical — production stoppage can be severe. Machinery values prominent.
- GLOBAL OFFICE / FINANCIAL: multi-city office portfolios, contents/ICOW/IT/data.
  BI and ICOW often the largest exposure. Data reinstatement extensions relevant.

════════════════════════════════════════════
PERIL STRUCTURE — THINK CAREFULLY
════════════════════════════════════════════

Cover type drives the rate and the key questions:
- T&S ONLY: narrow cover, lowest exposure, clearest exclusion of broader PV perils.
  Verify RSCC / Malicious Damage are clearly excluded.
- FULL PV (no War): standard market offering. Verify RSCC, MD, Insurrection are
  all included. War / Civil War should be explicitly excluded.
- FULL PV + WAR: significant exposure uplift. War / Civil War extension requires
  careful country risk assessment. Check time window — typically >72hrs for War.
  Aggregation across civil war scenarios can be severe.
- PV LIABILITY: third party bodily injury / property damage from PV perils.
  More common on infrastructure. Check limit is separate from PD limit.

Occurrence time window matters for aggregation:
- Standard PV: 72 hours is market norm
- War / Civil War: often 168 hours or longer
- Extended windows increase potential for large single events — flag if unusually wide

════════════════════════════════════════════
TIV AND SOV ASSESSMENT
════════════════════════════════════════════

TIV is the primary exposure base — treat it like premium income for casualty:
- If TIV is not provided, the risk cannot be priced — this is a critical gap
- SOV (Schedule of Values) is the gold standard — per location addresses, occupancy,
  construction, declared values. Flag if only aggregate TIV provided without SOV
- For each location in sov_locations, populate latitude and longitude if the address
  or city/country is clear enough to infer approximate coordinates from your knowledge.
  Use city-centre coordinates if no street address — better than blank.
  Leave null only if the location is too vague to geocode (e.g. "various locations")
- Largest single location TIV is the MPL (Maximum Probable Loss) indicator for
  a targeted attack scenario
- Geographic concentration: multiple high-value locations in the same city or zone
  creates accumulation risk in a single occurrence. Flag clustering
- TIV split between PD / BI / Stock is important — BI-heavy risks behave differently
  to PD-heavy risks under a PV event
- For infrastructure: "within country" wording with annexure schedules — check
  whether the annexure was actually provided
- Revenue/TIV ratio sense check: for BI, declared BI sum insured should be
  proportionate to the business's annual revenue — flag material mismatches

════════════════════════════════════════════
PREMIUM AND RATE ADEQUACY
════════════════════════════════════════════

Calculate both rate metrics:
- Rate on Line (RoL) = Gross Premium / Limit × 100
- Rate on TIV (RoT) = Gross Premium / TIV × 100

Both matter for different reasons:
- RoL tells you the cost of the limit relative to the cover provided
- RoT tells you the rate relative to the underlying exposure

Prior year premium: if available, calculate implied rate change. Flag if:
- Rate change is negative (rate reduction) when geopolitical risk has increased
- Large rate reductions without explanation — adverse selection concern
- NCB requested alongside no loss history — reasonable; NCB without evidence of
  clean record requires challenge

════════════════════════════════════════════
GEOPOLITICAL CONTEXT — APPLY JUDGEMENT
════════════════════════════════════════════

This is where PV u/w differs most from other classes. Apply your knowledge:
- Assess primary country/territory risk based on known geopolitical context
  (do NOT invent specific events, but apply general knowledge of risk levels)
- Risk levels: Low / Moderate / Elevated / High / Extreme
- Flag if territorial scope includes active conflict zones or regions with
  significantly elevated terrorism/political violence risk
- Sanctions: flag any territorial overlap with OFAC, UK, EU sanctioned jurisdictions
- National terrorism pools: flag if Pool Re (UK), GAREAT (France), TRIA (US),
  or other national schemes may interact — affects cedant's retention and market share
- Proximity to conflict: for War/CW cover, proximity of insured territory to
  active conflict zones is a key u/w consideration

════════════════════════════════════════════
RATER INPUTS — STANDARDISE CAREFULLY
════════════════════════════════════════════

The rater_* fields are structured inputs for the pricing model. Standardise:
- rater_risk_type: WHSE / INFRA / INDUS / OFFICE
- rater_cover_code: TS (T&S only) / PV (Full PV, no War) / PVW (PV + War) / PVWL (PV + War + Liability)
- Convert all monetary values to the rater_currency (which should be the limit currency)
- rater_bi_period_months: convert indemnity period to integer months
- rater_occurrence_hrs: integer hours for occurrence window
- rater_primary_country: ISO 3166-1 alpha-2 code (e.g. GB, FR, NG, PH)

════════════════════════════════════════════
UW FLAGS — WHAT TO FLAG IN PV
════════════════════════════════════════════

Raise RED flags for:
- TIV not provided — cannot price
- Territorial scope includes active War / high-severity conflict zone without
  War extension being present (or vice versa — War extension requested in stable territory)
- SOV not provided for multi-location risk — no per-location visibility
- Known circumstances or prior losses not declared
- Sanctions exposure identified
- Occurrence window wider than 168 hours — unusual and requires explanation
- Prior declinatures

Raise AMBER flags for:
- No SOV provided — only aggregate TIV (advisory: request full SOV)
- Rate on TIV appears materially below market for the territory and cover type
- Large aggregate TIV without corresponding per-location detail
- BI indemnity period >24 months without explanation
- Automatic additions clause without post-inception declaration requirement
- T&D exclusion absent on infrastructure risk
- Cyber exclusion absent or unclear
- Insurer switch without explanation

Raise INFO for:
- National pool interaction possible — note for cedant discussion
- NCB requested — note, verify loss record
- Short policy period or TBC inception — flag for monitoring

════════════════════════════════════════════
OUTPUT RULES
════════════════════════════════════════════

- Return ONLY valid JSON — no markdown, no preamble
- null for absent fields — never invent or estimate
- Monetary amounts: numeric string without currency symbols e.g. "5000000"
- Currency in companion _currency field
- Y/N fields: exactly "Y", "N", or "Unknown"
- Boolean fields: true or false
- rater_* fields: populate from extracted data — these are your structured output
- uw_analyst_flags: specific, actionable, ranked RED → AMBER → INFO

Return this exact JSON structure:

{
  "insured_name": null,
  "insured_group": null,
  "insured_country": null,
  "business_activity": null,
  "risk_type": null,
  "broker_name": null,
  "coverholder": null,

  "policy_period_start": null,
  "policy_period_end": null,
  "wording_form": null,
  "wording_type": null,
  "claims_basis": null,
  "jurisdiction": null,
  "prior_insurer": null,
  "prior_premium": null,
  "renewal_or_new": null,
  "payment_terms": null,

  "territorial_scope": null,
  "location_count": null,
  "tiv_total": null,
  "tiv_currency": null,
  "tiv_pd": null,
  "tiv_bi": null,
  "tiv_stock": null,
  "sov_provided": "Unknown",
  "largest_location_tiv": null,
  "largest_location_name": null,
  "highest_risk_country": null,
  "accumulation_comment": null,
  "sov_locations": [
    {
      "location_name": null,
      "address": null,
      "city": null,
      "country": null,
      "latitude": null,
      "longitude": null,
      "occupancy": null,
      "construction": null,
      "storeys": null,
      "tiv_total": null,
      "tiv_pd": null,
      "tiv_bi": null,
      "tiv_stock": null,
      "currency": null,
      "fire_protection": null,
      "security_protection": null,
      "peak_tiv_flag": false,
      "notes": null
    }
  ],
  "automatic_additions_pct": null,

  "cover_type": null,
  "peril_terrorism": "Unknown",
  "peril_rscc": "Unknown",
  "peril_malicious_damage": "Unknown",
  "peril_insurrection": "Unknown",
  "peril_war": "Unknown",
  "peril_pv_liability": "Unknown",
  "occurrence_definition": null,
  "war_time_window": null,
  "exclusions_nuclear": "Unknown",
  "exclusions_cyber": "Unknown",
  "exclusions_td_pipelines": "Unknown",
  "exclusions_pollution": "Unknown",
  "exclusions_other": null,
  "sanctions_clause": null,
  "territorial_carveouts": null,

  "limit_any_one_occurrence": null,
  "limit_currency": null,
  "limit_aggregate": null,
  "limit_pv_liability": null,
  "excess_point": null,
  "layer_structure": null,
  "deductible_pd": null,
  "deductible_bi": null,
  "deductible_notes": null,
  "limit_options": null,

  "bi_covered": "Unknown",
  "bi_sum_insured": null,
  "bi_indemnity_period": null,
  "icow_covered": "Unknown",
  "icow_limit": null,
  "denial_of_access": "Unknown",
  "denial_of_access_detail": null,
  "suppliers_customers": "Unknown",
  "suppliers_customers_limit": null,
  "utilities_extension": "Unknown",
  "data_reinstatement": "Unknown",
  "data_limit": null,
  "debris_removal": null,
  "public_authorities": null,
  "waiver_subrogation": "Unknown",
  "non_invalidation": "Unknown",

  "premium_sought_gross": null,
  "premium_currency": null,
  "commission_pct": null,
  "ncb_requested": null,
  "implied_rate_change_pct": null,

  "loss_history_declaration": null,
  "loss_history_years_provided": null,
  "loss_history": [],
  "large_losses": [],
  "loss_history_completeness": null,

  "primary_country_risk": null,
  "country_risk_rationale": null,
  "sanctions_exposure": null,
  "accumulation_risk": null,
  "conflict_proximity": null,
  "political_stability": null,
  "nat_pool_interaction": null,

  "pending_litigation": "Unknown",
  "pending_detail": null,
  "prior_declinatures": "Unknown",
  "prior_declinatures_detail": null,
  "insurer_switch_flag": false,
  "insurer_switch_reason": null,
  "claims_handling_notes": null,
  "non_cancellation": null,

  "rater_risk_type": null,
  "rater_cover_code": null,
  "rater_tiv": null,
  "rater_currency": null,
  "rater_limit": null,
  "rater_excess": null,
  "rater_deductible": null,
  "rater_bi_flag": "Unknown",
  "rater_bi_tiv": null,
  "rater_bi_period_months": null,
  "rater_war_flag": "Unknown",
  "rater_liability_flag": "Unknown",
  "rater_liability_limit": null,
  "rater_occurrence_hrs": null,
  "rater_primary_country": null,
  "rater_location_count": null,
  "rater_premium_sought": null,
  "rater_commission_pct": null,
  "rater_rol_pct": null,
  "rater_rot_pct": null,

  "data_conflicts": [],
  "uw_analyst_flags": [],
  "questions_for_broker": [],

  "extraction_confidence": "High / Medium / Low",
  "extraction_notes": null
}"""