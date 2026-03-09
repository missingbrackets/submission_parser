# ============================================================
#  core/outputs.py
#  CSV schemas, row builders, and file savers.
#  No UI dependencies.
# ============================================================

import csv
import datetime
import os

from core.extractor import _safe, _parse_amount, _output_root


# ── SUBMISSION CSV ROW BUILDER ────────────────────────────────

def build_csv_row(
    extracted: dict,
    gap_analysis: dict,
    csv_schema: list,
    source_folder: str,
    class_label: str,
) -> dict:
    row = {col: "" for col in csv_schema}

    row["extraction_date"]   = datetime.date.today().isoformat()
    row["source_folder"]     = os.path.basename(source_folder.rstrip("\\/"))
    row["class_of_business"] = class_label

    SKIP_KEYS = {
        "extraction_date", "source_folder", "class_of_business",
        "loss_history", "large_losses", "sov_locations",
        "uw_analyst_flags", "data_conflicts", "questions_for_broker",
    }
    for key in csv_schema:
        if key in SKIP_KEYS:
            continue
        if key in extracted and extracted[key] is not None:
            val = extracted[key]
            if not isinstance(val, (list, dict)):
                row[key] = _safe(val)

    if "premium_net_of_brokerage" in row and not row.get("premium_net_of_brokerage"):
        try:
            gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
            brok  = float(_parse_amount(str(extracted.get("brokerage_pct", "0") or "0").replace("%", "")))
            row["premium_net_of_brokerage"] = str(round(gross * (1 - brok / 100), 0))
        except (ValueError, TypeError):
            pass
    if "premium_net" in row and not row.get("premium_net"):
        try:
            gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
            comm  = float(_parse_amount(str(extracted.get("commission_pct", "0") or "0").replace("%", "")))
            row["premium_net"] = str(round(gross * (1 - comm / 100), 0))
        except (ValueError, TypeError):
            pass

    loss_hist = extracted.get("loss_history") or []
    if isinstance(loss_hist, list):
        for i, yr in enumerate(loss_hist[:7]):
            if not isinstance(yr, dict):
                continue
            p = f"loss_yr{i+1}_"
            row[p + "year"]         = _safe(yr.get("year"))
            row[p + "premium"]      = _safe(yr.get("premium"))
            row[p + "losses"]       = _safe(yr.get("losses_total_incurred") or yr.get("losses_paid"))
            row[p + "claims_count"] = _safe(yr.get("claims_count"))

    if "rate_on_line_pct" in row and not row.get("rate_on_line_pct"):
        try:
            gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
            limit = float(_parse_amount(extracted.get("limit_any_one_occurrence") or extracted.get("limit_any_one_claim", "")))
            if limit > 0:
                row["rate_on_line_pct"] = f"{round(gross / limit * 100, 4)}%"
        except (ValueError, TypeError):
            pass
    if "rate_on_tiv_pct" in row and not row.get("rate_on_tiv_pct"):
        try:
            gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
            tiv   = float(_parse_amount(extracted.get("tiv_total", "")))
            if tiv > 0:
                row["rate_on_tiv_pct"] = f"{round(gross / tiv * 100, 4)}%"
        except (ValueError, TypeError):
            pass

    try:
        total_p = total_l = 0
        for yr in (loss_hist or []):
            if not isinstance(yr, dict):
                continue
            p = float(_parse_amount(str(yr.get("premium") or "")))
            l = float(_parse_amount(str(yr.get("losses_total_incurred") or yr.get("losses_paid") or "")))
            if p > 0:
                total_p += p
                total_l += l
        if total_p > 0 and not row.get("raw_avg_loss_ratio"):
            row["raw_avg_loss_ratio"] = f"{round(total_l / total_p * 100, 1)}%"
    except (ValueError, TypeError):
        pass

    large_losses = extracted.get("large_losses") or []
    if isinstance(large_losses, list) and large_losses:
        try:
            total_ll = sum(
                float(_parse_amount(str(ll.get("amount") or "")))
                for ll in large_losses
                if isinstance(ll, dict) and ll.get("amount")
            )
            row["large_losses_total"] = str(round(total_ll, 0))
        except (ValueError, TypeError):
            row["large_losses_total"] = f"{len(large_losses)} identified"

    if isinstance(large_losses, list):
        if "large_losses_flagged" in row:
            row["large_losses_flagged"] = "Y" if len(large_losses) > 0 else "N"

    uw_flags = [f for f in (extracted.get("uw_analyst_flags") or []) if isinstance(f, dict)]
    if isinstance(uw_flags, list):
        red   = [f for f in uw_flags if str(f.get("severity","")).upper() == "RED"]
        amber = [f for f in uw_flags if str(f.get("severity","")).upper() == "AMBER"]
        if "uw_red_flags_count" in row:
            row["uw_red_flags_count"]   = str(len(red))
        if "uw_amber_flags_count" in row:
            row["uw_amber_flags_count"] = str(len(amber))

    row["data_quality_score"]  = str(gap_analysis["data_quality_score"])
    if "critical_gaps_count" in row:
        row["critical_gaps_count"] = str(gap_analysis["critical_count"])
    if "advisory_gaps_count" in row:
        row["advisory_gaps_count"] = str(gap_analysis["advisory_count"])

    return row


def save_csv(
    row: dict,
    csv_schema: list,
    output_folder: str,
    filename_prefix: str = "submission_data",
) -> str:
    data_folder = _output_root(output_folder)
    filepath    = os.path.join(data_folder, f"{filename_prefix}.csv")
    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_schema)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    return filepath


# ── CLAIMS CSV ────────────────────────────────────────────────

def build_claims_csv_rows(extracted: dict, claims_csv_schema: list) -> list:
    """One row per year of loss history + individual large losses."""
    if not claims_csv_schema:
        return []

    rows    = []
    insured = _safe(extracted.get("insured_name"))

    loss_hist = extracted.get("loss_history") or []
    for i, yr in enumerate(loss_hist or []):
        if not isinstance(yr, dict):
            continue
        year         = _safe(yr.get("year"))
        losses_paid  = _safe(yr.get("losses_paid"))
        losses_os    = _safe(yr.get("losses_outstanding"))
        losses_total = _safe(yr.get("losses_total_incurred") or yr.get("losses_paid"))
        count        = _safe(yr.get("claims_count"))
        notes        = _safe(yr.get("notes"))
        dev_warn     = _safe(yr.get("development_warning"))

        desc = f"Year {year} aggregate"
        if count:
            desc += f" — {count} claim(s)"
        if notes:
            desc += f". {notes}"
        if dev_warn:
            desc += f" [DEV WARNING: {dev_warn}]"

        row = {col: "" for col in claims_csv_schema}
        row["Segment_1"]               = ""
        row["Segment_2"]               = ""
        row["underwriting_year"]       = year
        row["claim_id"]                = f"{year}-{str(i+1).zfill(3)}" if year else f"UNK-{str(i+1).zfill(3)}"
        row["accident_date"]           = ""
        row["reported_date"]           = ""
        row["insured"]                 = insured
        row["claim_description"]       = desc.strip(" —.")
        row["status"]                  = "Historical"
        row["paid"]                    = losses_paid
        row["outstanding"]             = losses_os
        row["incurred"]                = losses_total
        row["Manual Claim Adjustments"] = ""
        rows.append(row)

    large_losses = extracted.get("large_losses") or []
    for j, ll in enumerate(large_losses or []):
        if not isinstance(ll, dict):
            continue
        year   = _safe(ll.get("year"))
        amount = _safe(ll.get("amount"))
        desc   = _safe(ll.get("description"))
        status = _safe(ll.get("status"))
        status_lower = status.lower()

        row = {col: "" for col in claims_csv_schema}
        row["Segment_1"]               = ""
        row["Segment_2"]               = ""
        row["underwriting_year"]       = year
        row["claim_id"]                = f"{year}-LL-{str(j+1).zfill(2)}" if year else f"LL-{str(j+1).zfill(2)}"
        row["accident_date"]           = ""
        row["reported_date"]           = ""
        row["insured"]                 = insured
        row["claim_description"]       = desc or "Large loss — see submission"
        row["status"]                  = status or "Unknown"
        row["paid"]                    = amount if "paid" in status_lower and "out" not in status_lower else ""
        row["outstanding"]             = amount if any(x in status_lower for x in ["open","outstanding","reserve"]) else ""
        row["incurred"]                = amount
        row["Manual Claim Adjustments"] = ""
        rows.append(row)

    return rows


def save_claims_csv(
    rows: list,
    claims_csv_schema: list,
    output_folder: str,
    filename: str = "claims_data.csv",
) -> str:
    data_folder = _output_root(output_folder)
    filepath    = os.path.join(data_folder, filename)
    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=claims_csv_schema)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    return filepath


# ── LOCATIONS CSV ─────────────────────────────────────────────

def build_locations_csv_rows(extracted: dict) -> tuple:
    LOCATION_SCHEMA = [
        "insured_name", "policy_period_start", "location_id",
        "location_name", "address", "city", "country",
        "latitude", "longitude",
        "occupancy", "construction", "storeys",
        "tiv_total", "tiv_pd", "tiv_bi", "tiv_stock", "tiv_currency",
        "fire_protection", "security_protection",
        "peak_tiv_flag", "notes",
    ]

    rows = []
    insured      = _safe(extracted.get("insured_name"))
    policy_start = _safe(extracted.get("policy_period_start"))
    currency     = _safe(extracted.get("tiv_currency") or extracted.get("limit_currency") or "")

    locations  = extracted.get("sov_locations") or []
    valid_locs = [l for l in locations if isinstance(l, dict)]

    if valid_locs:
        for i, loc in enumerate(valid_locs):
            row = {col: "" for col in LOCATION_SCHEMA}
            row["insured_name"]        = insured
            row["policy_period_start"] = policy_start
            row["location_id"]         = f"LOC-{str(i+1).zfill(3)}"
            row["location_name"]       = _safe(loc.get("location_name") or loc.get("name"))
            row["address"]             = _safe(loc.get("address"))
            row["city"]                = _safe(loc.get("city"))
            row["country"]             = _safe(loc.get("country"))
            row["latitude"]            = _safe(loc.get("latitude") or loc.get("lat"))
            row["longitude"]           = _safe(loc.get("longitude") or loc.get("lon") or loc.get("lng"))
            row["occupancy"]           = _safe(loc.get("occupancy") or loc.get("use") or loc.get("type"))
            row["construction"]        = _safe(loc.get("construction"))
            row["storeys"]             = _safe(loc.get("storeys") or loc.get("floors"))
            row["tiv_total"]           = _safe(loc.get("tiv") or loc.get("tiv_total"))
            row["tiv_pd"]              = _safe(loc.get("tiv_pd") or loc.get("pd_value"))
            row["tiv_bi"]              = _safe(loc.get("tiv_bi") or loc.get("bi_value"))
            row["tiv_stock"]           = _safe(loc.get("tiv_stock") or loc.get("stock_value"))
            row["tiv_currency"]        = _safe(loc.get("currency") or currency)
            row["fire_protection"]     = _safe(loc.get("fire_protection") or loc.get("fire"))
            row["security_protection"] = _safe(loc.get("security_protection") or loc.get("security"))
            row["peak_tiv_flag"]       = _safe(loc.get("peak_tiv_flag") or loc.get("is_largest") or "")
            row["notes"]               = _safe(loc.get("notes") or loc.get("comments"))
            rows.append(row)
    else:
        row = {col: "" for col in LOCATION_SCHEMA}
        row["insured_name"]        = insured
        row["policy_period_start"] = policy_start
        row["location_id"]         = "AGG-001"
        row["location_name"]       = "Aggregate (no SOV provided)"
        row["country"]             = _safe(extracted.get("insured_country") or extracted.get("territorial_scope"))
        row["tiv_total"]           = _safe(extracted.get("tiv_total"))
        row["tiv_pd"]              = _safe(extracted.get("tiv_pd"))
        row["tiv_bi"]              = _safe(extracted.get("tiv_bi"))
        row["tiv_stock"]           = _safe(extracted.get("tiv_stock"))
        row["tiv_currency"]        = currency
        row["notes"]               = "No SOV provided — aggregate TIV only"
        rows.append(row)

    return rows, LOCATION_SCHEMA


def save_locations_csv(
    rows: list,
    schema: list,
    output_folder: str,
    filename: str = "locations_data.csv",
) -> str:
    data_folder = _output_root(output_folder)
    filepath = os.path.join(data_folder, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


# ── TRIAGE MATRIX CSV (PVQ skill) ─────────────────────────────

TRIAGE_SCHEMA = [
    "extraction_date", "source_folder", "class_of_business",
    "triage_recommendation", "triage_rationale",
    "insured_name", "broker_name", "insured_country", "risk_type",
    "territorial_scope", "location_count", "sov_provided",
    "tiv_total", "tiv_currency",
    "cover_type", "peril_war", "peril_pv_liability",
    "limit_aoo", "limit_currency", "excess_point", "deductible",
    "bi_covered", "bi_indemnity_period",
    "premium_sought_gross", "premium_currency", "commission_pct",
    "prior_premium", "rate_on_line_pct", "rate_on_tiv_pct", "implied_rate_change",
    "policy_period_start", "policy_period_end", "renewal_or_new",
    "country_risk", "sanctions_exposure",
    "prior_declinatures", "known_circumstances", "large_losses_flag",
    "loss_years_provided", "occurrence_hrs",
    "data_quality_score", "extraction_confidence",
    "red_flags", "amber_flags",
]


def build_triage_row(extracted: dict, gap_analysis: dict,
                     source_folder: str, class_label: str) -> dict:
    row = {col: "" for col in TRIAGE_SCHEMA}
    row["extraction_date"]    = datetime.date.today().isoformat()
    row["source_folder"]      = os.path.basename(source_folder.rstrip("\\/"))
    row["class_of_business"]  = class_label
    row["data_quality_score"] = str(gap_analysis.get("data_quality_score", ""))
    for key in TRIAGE_SCHEMA:
        if key in extracted and extracted[key] is not None:
            val = extracted[key]
            if not isinstance(val, (list, dict)):
                row[key] = _safe(val)
    try:
        gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
        limit = float(_parse_amount(extracted.get("limit_aoo", "")))
        tiv   = float(_parse_amount(extracted.get("tiv_total", "")))
        if limit > 0:
            row["rate_on_line_pct"] = f"{round(gross / limit * 100, 4)}%"
        if tiv > 0:
            row["rate_on_tiv_pct"] = f"{round(gross / tiv * 100, 4)}%"
    except (ValueError, TypeError):
        pass
    try:
        gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
        prior = float(_parse_amount(extracted.get("prior_premium", "")))
        if prior > 0:
            row["implied_rate_change"] = f"{round((gross - prior) / prior * 100, 1)}%"
    except (ValueError, TypeError):
        pass
    uw_flags    = [f for f in (extracted.get("uw_analyst_flags") or []) if isinstance(f, dict)]
    red_flags   = [f.get("flag", "") for f in uw_flags if str(f.get("severity","")).upper() == "RED"]
    amber_flags = [f.get("flag", "") for f in uw_flags if str(f.get("severity","")).upper() == "AMBER"]
    row["red_flags"]   = " | ".join(red_flags)
    row["amber_flags"] = " | ".join(amber_flags)
    return row


def save_triage_csv(row: dict, output_folder: str,
                    filename: str = "triage_matrix.csv") -> str:
    data_folder = _output_root(output_folder)
    filepath    = os.path.join(data_folder, filename)
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAGE_SCHEMA)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    return filepath


def build_triage_locations_rows(extracted: dict) -> tuple:
    TRIAGE_LOC_SCHEMA = [
        "extraction_date", "insured_name", "insured_country",
        "location_id", "location_name", "city", "country",
        "latitude", "longitude",
        "occupancy", "tiv_total", "currency", "notes",
    ]
    rows     = []
    insured  = _safe(extracted.get("insured_name"))
    country  = _safe(extracted.get("insured_country"))
    currency = _safe(extracted.get("tiv_currency") or "")
    today    = datetime.date.today().isoformat()
    locations = [l for l in (extracted.get("sov_locations") or []) if isinstance(l, dict)]
    if locations:
        for i, loc in enumerate(locations):
            row = {col: "" for col in TRIAGE_LOC_SCHEMA}
            row["extraction_date"] = today
            row["insured_name"]    = insured
            row["insured_country"] = country
            row["location_id"]     = f"LOC-{str(i+1).zfill(3)}"
            row["location_name"]   = _safe(loc.get("location_name") or loc.get("name"))
            row["city"]            = _safe(loc.get("city"))
            row["country"]         = _safe(loc.get("country"))
            row["latitude"]        = _safe(loc.get("latitude") or loc.get("lat"))
            row["longitude"]       = _safe(loc.get("longitude") or loc.get("lon") or loc.get("lng"))
            row["occupancy"]       = _safe(loc.get("occupancy") or loc.get("use"))
            row["tiv_total"]       = _safe(loc.get("tiv_total") or loc.get("tiv"))
            row["currency"]        = _safe(loc.get("currency") or currency)
            row["notes"]           = _safe(loc.get("notes"))
            rows.append(row)
    else:
        row = {col: "" for col in TRIAGE_LOC_SCHEMA}
        row["extraction_date"] = today
        row["insured_name"]    = insured
        row["insured_country"] = country
        row["location_id"]     = "AGG-001"
        row["location_name"]   = "Aggregate (no SOV)"
        row["country"]         = country
        row["tiv_total"]       = _safe(extracted.get("tiv_total"))
        row["currency"]        = currency
        row["notes"]           = "No SOV - aggregate TIV only"
        rows.append(row)
    return rows, TRIAGE_LOC_SCHEMA


def save_triage_locations_csv(rows: list, schema: list,
                               output_folder: str,
                               filename: str = "triage_locations.csv") -> str:
    data_folder = _output_root(output_folder)
    filepath    = os.path.join(data_folder, filename)
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    return filepath


# ── DIRECT TRIAGE MATRIX CSV (PVDT skill) ─────────────────────

DIRECT_TRIAGE_FLAG_FIELDS = [
    "flag_direct_to_market",
    "flag_country_risk",
    "flag_sanctions",
    "flag_rate_adequacy",
    "flag_data_completeness",
    "flag_known_circumstances",
    "flag_prior_declinatures",
    "flag_structure_complexity",
]

DIRECT_TRIAGE_SCHEMA = [
    "extraction_date", "source_folder", "class_of_business",
    "triage_recommendation",
    "n_red", "n_amber", "n_green",
    "insured_name", "broker_name", "direct_to_market",
    "insured_country", "risk_type", "territorial_scope",
    "tiv_total", "tiv_currency", "location_count", "sov_provided",
    "cover_type", "peril_war", "limit_aoo", "limit_currency", "excess_point",
    "premium_sought_gross", "premium_currency", "commission_pct", "prior_premium",
    "rate_on_line_pct", "rate_on_tiv_pct",
    "policy_period_start", "policy_period_end", "renewal_or_new",
    "flag_direct_to_market",
    "flag_country_risk",
    "flag_sanctions",
    "flag_rate_adequacy",
    "flag_data_completeness",
    "flag_known_circumstances",
    "flag_prior_declinatures",
    "flag_structure_complexity",
    "triage_rationale",
]


def _rag_colour(value: str) -> str:
    """Return 'RED', 'AMBER', 'GREEN', or '' from a flag value string."""
    v = str(value).upper()
    if "🔴" in v or v.startswith("RED"):
        return "RED"
    if "🟡" in v or "AMBER" in v:
        return "AMBER"
    if "🟢" in v or "GREEN" in v:
        return "GREEN"
    return ""


def build_direct_triage_row(extracted: dict, gap_analysis: dict,
                             source_folder: str, class_label: str) -> dict:
    row = {col: "" for col in DIRECT_TRIAGE_SCHEMA}
    row["extraction_date"]   = datetime.date.today().isoformat()
    row["source_folder"]     = os.path.basename(source_folder.rstrip("\\/"))
    row["class_of_business"] = class_label

    for key in DIRECT_TRIAGE_SCHEMA:
        if key in extracted and extracted[key] is not None:
            val = extracted[key]
            if not isinstance(val, (list, dict)):
                row[key] = _safe(val)

    try:
        gross = float(_parse_amount(extracted.get("premium_sought_gross", "")))
        limit = float(_parse_amount(extracted.get("limit_aoo", "")))
        tiv   = float(_parse_amount(extracted.get("tiv_total", "")))
        if limit > 0:
            row["rate_on_line_pct"] = f"{round(gross / limit * 100, 4)}%"
        if tiv > 0:
            row["rate_on_tiv_pct"]  = f"{round(gross / tiv   * 100, 4)}%"
    except (ValueError, TypeError):
        pass

    n_red = n_amber = n_green = 0
    for flag_key in DIRECT_TRIAGE_FLAG_FIELDS:
        colour = _rag_colour(str(extracted.get(flag_key, "")))
        if colour == "RED":
            n_red   += 1
        elif colour == "AMBER":
            n_amber += 1
        elif colour == "GREEN":
            n_green += 1
    row["n_red"]   = str(n_red)
    row["n_amber"] = str(n_amber)
    row["n_green"] = str(n_green)

    return row


def save_direct_triage_csv(row: dict, output_folder: str,
                            filename: str = "triage_direct.csv") -> str:
    data_folder = _output_root(output_folder)
    filepath    = os.path.join(data_folder, filename)
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DIRECT_TRIAGE_SCHEMA)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    return filepath
