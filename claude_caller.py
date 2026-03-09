# ============================================================
#  CLAUDE CALLER + POST-PROCESSING  v4
#  Sends extracted text to Claude, parses response,
#  runs gap analysis, builds CSV rows, saves outputs.
# ============================================================

import json
import os
import re
import csv
import datetime
from typing import Tuple

import anthropic

# ── CLAUDE EXTRACTION ────────────────────────────────────────
def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,
    max_tokens: int = 4096,
) -> Tuple[dict, str]:
    """
    Send combined submission text to Claude.
    Returns (parsed_dict, raw_response_text)
    """
    client = anthropic.Anthropic(api_key=api_key)

    user_msg = (
        "You are processing a broker submission. The content below has been extracted "
        "from multiple source files (emails, PDFs, Excel spreadsheets, Word documents). "
        "Read ALL of it carefully before extracting — later sections may correct or "
        "supplement earlier ones. Reconcile any conflicts as instructed.\n\n"
        "=== SUBMISSION CONTENT START ===\n\n"
        + combined_text[:60000]
        + "\n\n=== SUBMISSION CONTENT END ===\n\n"
        "Now extract all structured data and return the JSON as specified. "
        "Return ONLY the JSON object — no markdown fences, no explanation."
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = message.content[0].text

    # Strip markdown fences if present
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    clean = clean.strip()

    parsed = {}
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        # Try to find first complete {...} block
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = {"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
        else:
            parsed = {"extraction_error": "No JSON found in response", "raw_snippet": clean[:500]}

    return parsed, raw


# ── HELPERS ──────────────────────────────────────────────────
def _safe(val) -> str:
    """Return string value or empty string."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Y" if val else "N"
    return str(val).strip()

def _parse_amount(val) -> str:
    """Strip currency symbols/commas, return numeric string."""
    if val is None:
        return ""
    s = re.sub(r"[£$€,\s]", "", str(val))
    return s


# ── OUTPUT PATH HELPER ───────────────────────────────────────
AUTO_OUTPUT_DIR = "submission_tool_auto_outputs"

def _output_root(case_folder: str) -> str:
    """
    All tool outputs go to:
      <case_folder>/submission_tool_auto_outputs/
    rather than directly into the case folder subfolders.
    """
    root = os.path.join(case_folder, AUTO_OUTPUT_DIR)
    os.makedirs(root, exist_ok=True)
    return root


# ── GAP ANALYSIS ─────────────────────────────────────────────
def run_gap_analysis(extracted: dict, required_fields: list) -> dict:
    """
    Compare extracted data against required_fields checklist.
    Handles scalar fields, array fields, and boolean fields.
    """
    critical_gaps = []
    advisory_gaps = []
    present       = []

    EMPTY_VALUES = {"", "null", "none", "unknown", "n/a", "not provided", "not stated"}

    for field_key, label, is_critical in required_fields:
        val = extracted.get(field_key)

        if isinstance(val, list):
            # Array field: present if non-empty and has at least one populated item
            is_present = (
                len(val) > 0 and
                any(
                    any(v for v in (item.values() if isinstance(item, dict) else [item]) if v is not None)
                    for item in val
                )
            )
        elif isinstance(val, bool):
            is_present = True  # booleans are always "provided"
        elif isinstance(val, (int, float)):
            is_present = True
        else:
            is_present = (
                val is not None and
                str(val).strip().lower() not in EMPTY_VALUES
            )

        if is_present:
            present.append((field_key, label))
        elif is_critical:
            critical_gaps.append((field_key, label))
        else:
            advisory_gaps.append((field_key, label))

    total_fields  = len(required_fields)
    present_count = len(present)
    score = round((present_count / total_fields) * 100) if total_fields > 0 else 0

    return {
        "critical_gaps":      critical_gaps,
        "advisory_gaps":      advisory_gaps,
        "present":            present,
        "data_quality_score": score,
        "critical_count":     len(critical_gaps),
        "advisory_count":     len(advisory_gaps),
        "present_count":      present_count,
        "total_fields":       total_fields,
    }


# ── SUBMISSION CSV ROW BUILDER ────────────────────────────────
def build_csv_row(
    extracted: dict,
    gap_analysis: dict,
    csv_schema: list,
    source_folder: str,
    class_label: str,
) -> dict:
    """
    Map extracted data onto the fixed CSV schema.
    Field names match the JSON structure returned by the casualty skill.
    """
    row = {col: "" for col in csv_schema}

    # ── Metadata
    row["extraction_date"]   = datetime.date.today().isoformat()
    row["source_folder"]     = os.path.basename(source_folder.rstrip("\\/"))
    row["class_of_business"] = class_label

    # ── Direct scalar mappings — write any extracted field that exists in schema
    # (generic: works for all skills without hardcoded field lists)
    SKIP_KEYS = {
        "extraction_date", "source_folder", "class_of_business",  # metadata set above
        "loss_history", "large_losses", "sov_locations",          # arrays — handled separately
        "uw_analyst_flags", "data_conflicts", "questions_for_broker",
    }
    for key in csv_schema:
        if key in SKIP_KEYS:
            continue
        if key in extracted and extracted[key] is not None:
            val = extracted[key]
            # Skip arrays — they have dedicated handlers below
            if not isinstance(val, (list, dict)):
                row[key] = _safe(val)

    # ── Net premium — only write if column exists in this skill's schema
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

    # ── Loss history — up to 7 years, most recent first
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

    # ── Rate on line / rate on TIV (only if columns in schema)
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

    # ── Derived avg loss ratio (recalculate as sense check)
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

    # ── Large losses total
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

    # ── UW flags summary
    uw_flags = [f for f in (extracted.get("uw_analyst_flags") or []) if isinstance(f, dict)]
    if isinstance(uw_flags, list):
        red   = [f for f in uw_flags if str(f.get("severity","")).upper() == "RED"]
        amber = [f for f in uw_flags if str(f.get("severity","")).upper() == "AMBER"]
        if "uw_red_flags_count" in row:
            row["uw_red_flags_count"]   = str(len(red))
        if "uw_amber_flags_count" in row:
            row["uw_amber_flags_count"] = str(len(amber))

    # ── Gap analysis scores
    row["data_quality_score"]  = str(gap_analysis["data_quality_score"])
    if "critical_gaps_count" in row:
        row["critical_gaps_count"] = str(gap_analysis["critical_count"])
    if "advisory_gaps_count" in row:
        row["advisory_gaps_count"] = str(gap_analysis["advisory_count"])

    return row


# ── SAVE SUBMISSION CSV ───────────────────────────────────────
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


# ── CLAIMS CSV BUILDER ────────────────────────────────────────
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


# ── LOCATIONS CSV BUILDER ────────────────────────────────────
def build_locations_csv_rows(extracted: dict) -> list:
    """
    Build one row per SOV location from extracted sov_locations array.
    Falls back to synthesising from aggregate data if no SOV provided.
    Returns list of dicts.
    """
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

    locations = extracted.get("sov_locations") or []
    valid_locs = [l for l in locations if isinstance(l, dict)]

    if valid_locs:
        for i, loc in enumerate(valid_locs):
            row = {col: "" for col in LOCATION_SCHEMA}
            row["insured_name"]      = insured
            row["policy_period_start"] = policy_start
            row["location_id"]       = f"LOC-{str(i+1).zfill(3)}"
            row["location_name"]     = _safe(loc.get("location_name") or loc.get("name"))
            row["address"]           = _safe(loc.get("address"))
            row["city"]              = _safe(loc.get("city"))
            row["country"]           = _safe(loc.get("country"))
            row["latitude"]          = _safe(loc.get("latitude") or loc.get("lat"))
            row["longitude"]         = _safe(loc.get("longitude") or loc.get("lon") or loc.get("lng"))
            row["occupancy"]         = _safe(loc.get("occupancy") or loc.get("use") or loc.get("type"))
            row["construction"]      = _safe(loc.get("construction"))
            row["storeys"]           = _safe(loc.get("storeys") or loc.get("floors"))
            row["tiv_total"]         = _safe(loc.get("tiv") or loc.get("tiv_total"))
            row["tiv_pd"]            = _safe(loc.get("tiv_pd") or loc.get("pd_value"))
            row["tiv_bi"]            = _safe(loc.get("tiv_bi") or loc.get("bi_value"))
            row["tiv_stock"]         = _safe(loc.get("tiv_stock") or loc.get("stock_value"))
            row["tiv_currency"]      = _safe(loc.get("currency") or currency)
            row["fire_protection"]   = _safe(loc.get("fire_protection") or loc.get("fire"))
            row["security_protection"] = _safe(loc.get("security_protection") or loc.get("security"))
            row["peak_tiv_flag"]     = _safe(loc.get("peak_tiv_flag") or loc.get("is_largest") or "")
            row["notes"]             = _safe(loc.get("notes") or loc.get("comments"))
            rows.append(row)
    else:
        # No SOV — synthesise a single summary row from aggregate data
        row = {col: "" for col in LOCATION_SCHEMA}
        row["insured_name"]       = insured
        row["policy_period_start"] = policy_start
        row["location_id"]        = "AGG-001"
        row["location_name"]      = "Aggregate (no SOV provided)"
        row["country"]            = _safe(extracted.get("insured_country") or extracted.get("territorial_scope"))
        row["tiv_total"]          = _safe(extracted.get("tiv_total"))
        row["tiv_pd"]             = _safe(extracted.get("tiv_pd"))
        row["tiv_bi"]             = _safe(extracted.get("tiv_bi"))
        row["tiv_stock"]          = _safe(extracted.get("tiv_stock"))
        row["tiv_currency"]       = currency
        row["notes"]              = "No SOV provided — aggregate TIV only"
        rows.append(row)

    return rows, LOCATION_SCHEMA


def save_locations_csv(
    rows: list,
    schema: list,
    output_folder: str,
    filename: str = "locations_data.csv",
) -> str:
    """
    Write locations rows to output_folder/02_data/locations_data.csv.
    Overwrites each run (locations are per-submission, not cumulative).
    Returns full file path.
    """
    data_folder = _output_root(output_folder)
    filepath = os.path.join(data_folder, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema)
        writer.writeheader()
        writer.writerows(rows)

    return filepath



# ── TRIAGE MATRIX CSV ────────────────────────────────────────

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
    """Append triage row. Grows across runs — one file per portfolio."""
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
    """Append location rows across runs — full portfolio location history."""
    data_folder = _output_root(output_folder)
    filepath    = os.path.join(data_folder, filename)
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    return filepath


# ── SAVE SUMMARY REPORT ───────────────────────────────────────
def build_summary_text(
    extracted: dict,
    gap_analysis: dict,
    source_files: dict,
    class_label: str,
    folder_name: str,
) -> str:
    """
    Build the full AI summary report as a string.
    Called by both save_summary_report (file write) and the in-app Summary tab.
    """
    def line(key, label, width=35):
        val = extracted.get(key)
        display = _safe(val) if val is not None else "NOT PROVIDED"
        if not display or display.lower() in {"null","none","unknown",""}:
            display = "NOT PROVIDED"
        lines.append(f"  {label:<{width}} {display}")

    lines = []
    lines.append("=" * 70)
    lines.append("  AI SUBMISSION SUMMARY")
    lines.append("=" * 70)
    lines.append(f"  Class:        {class_label}")
    lines.append(f"  Case Folder:  {folder_name}")
    lines.append(f"  Generated:    {datetime.datetime.now().strftime('%d %b %Y %H:%M')}")
    lines.append(f"  Data Quality: {gap_analysis['data_quality_score']}/100  "
                 f"({gap_analysis['present_count']}/{gap_analysis['total_fields']} fields found)")
    lines.append("=" * 70)

    lines.append("")
    lines.append("SOURCE FILES PROCESSED")
    lines.append("-" * 40)
    for fname, info in source_files.items():
        ok = "OK" if info.get("text") else "!!"
        lines.append(f"  [{ok}] {fname} ({info.get('size_kb','?')} KB) — {info.get('status','')}")

    lines.append("")
    lines.append("RISK SUMMARY")
    lines.append("-" * 40)
    line("insured_name",        "Insured:")
    line("broker_name",         "Broker:")
    line("industry_sector",     "Industry / SIC:")
    line("industry_sic_code",   "SIC Code:")
    line("annual_revenue",      "Annual Revenue:")
    line("annual_payroll",      "Annual Payroll:")
    line("number_of_employees", "Employees:")
    line("revenue_growth_flag", "Revenue Growth Flag:")

    lines.append("")
    lines.append("POLICY STRUCTURE")
    lines.append("-" * 40)
    line("policy_period_start", "Policy From:")
    line("policy_period_end",   "Policy To:")
    line("coverage_trigger",    "Trigger:")
    line("retroactive_date",    "Retro Date:")
    line("retro_date_adequacy", "Retro Adequacy:")
    line("jurisdiction",        "Jurisdiction:")
    line("territorial_scope",   "Territory:")
    line("us_canada_exposure",  "US/Canada Exposure:")

    lines.append("")
    lines.append("LIMITS & STRUCTURE")
    lines.append("-" * 40)
    line("limit_any_one_claim", "Limit Any One Claim:")
    line("limit_aggregate",     "Annual Aggregate:")
    line("excess_point",        "Excess / Attachment:")
    line("deductible",          "Deductible / SIR:")
    line("sir_as_pct_of_limit", "SIR as % of Limit:")
    line("sublimits",           "Sub-limits:")

    lines.append("")
    lines.append("COVERAGE LINES")
    lines.append("-" * 40)
    for key, label in [
        ("coverage_gl", "General / Public Liability"),
        ("coverage_pl", "Products Liability"),
        ("coverage_el", "Employers Liability"),
        ("coverage_pi", "Professional Indemnity"),
        ("coverage_do", "Directors & Officers"),
    ]:
        val = extracted.get(key, "Unknown")
        lines.append(f"  {label:<35} {val}")

    lines.append("")
    lines.append("PREMIUM ANALYTICS")
    lines.append("-" * 40)
    line("premium_sought_gross",     "Premium Sought (Gross):")
    line("brokerage_pct",            "Brokerage %:")
    line("premium_net_of_brokerage", "Net Premium:")
    line("premium_basis",            "Premium Basis:")
    line("prior_premium",            "Prior Year Premium:")
    line("implied_rate_change_pct",  "Implied Rate Change:")
    line("rate_on_line_pct",         "Rate on Line %:")

    lines.append("")
    lines.append("LOSS HISTORY")
    lines.append("-" * 40)
    line("loss_history_years_provided", "Years Provided:")
    line("loss_history_completeness",   "Completeness:")
    line("avg_loss_ratio_all_years_pct","Avg LR (all years):")
    line("avg_loss_ratio_ex_large_pct", "Avg LR (ex large):")
    line("loss_trend_direction",        "Loss Trend:")

    loss_hist = extracted.get("loss_history") or []
    if loss_hist:
        lines.append("")
        lines.append(f"  {'Year':<8} {'Premium':>14} {'Incurred':>14} {'Claims':>8}  {'LR%':>6}  Note")
        lines.append(f"  {'-'*7} {'-'*14} {'-'*14} {'-'*8}  {'-'*6}  {'-'*20}")
        for yr in loss_hist:
            if not isinstance(yr, dict):
                continue
            year   = str(yr.get("year") or "")
            prem   = str(yr.get("premium") or "—")
            loss   = str(yr.get("losses_total_incurred") or yr.get("losses_paid") or "—")
            cnt    = str(yr.get("claims_count") or "—")
            lr     = str(yr.get("implied_loss_ratio_pct") or "—")
            ll     = " *** LARGE LOSS ***" if yr.get("large_loss_flag") else ""
            dw     = f" [DEV: {yr['development_warning']}]" if yr.get("development_warning") else ""
            lines.append(f"  {year:<8} {prem:>14} {loss:>14} {cnt:>8}  {lr:>6}  {ll}{dw}")
    else:
        lines.append("  No loss history extracted.")

    large = extracted.get("large_losses") or []
    if large:
        lines.append("")
        lines.append("LARGE LOSSES DETAIL")
        lines.append("-" * 40)
        for ll in large:
            if not isinstance(ll, dict):
                continue
            lines.append(f"  {ll.get('year','?')} | {ll.get('amount','?')} | {ll.get('status','?')}")
            if ll.get("description"):
                lines.append(f"    {ll['description']}")
            if ll.get("reserved_adequacy_comment"):
                lines.append(f"    Reserve note: {ll['reserved_adequacy_comment']}")

    lines.append("")
    lines.append("RISK FLAGS")
    lines.append("-" * 40)
    line("pending_litigation",         "Pending Litigation:")
    line("pending_litigation_detail",  "  Detail:")
    line("prior_declinatures",         "Prior Declinatures:")
    line("prior_declinatures_detail",  "  Detail:")
    line("insurer_switch_flag",        "Insurer Switch:")
    line("insurer_switch_reason",      "  Reason:")
    line("ibnr_commentary",            "IBNR Note:")

    features = extracted.get("notable_features") or []
    if features:
        lines.append("")
        lines.append("NOTABLE FEATURES")
        lines.append("-" * 40)
        for feat in features:
            lines.append(f"  • {feat}")

    # UW Analyst Flags
    uw_flags = [f for f in (extracted.get("uw_analyst_flags") or []) if isinstance(f, dict)]
    lines.append("")
    lines.append("=" * 70)
    lines.append("  UNDERWRITER ANALYST FLAGS")
    lines.append("=" * 70)
    if uw_flags:
        sev_order = {"RED": 0, "AMBER": 1, "INFO": 2}
        for flag in sorted(uw_flags, key=lambda x: sev_order.get(str(x.get("severity","INFO")).upper(), 2)):
            sev    = str(flag.get("severity","INFO")).upper()
            cat    = flag.get("category","")
            title  = flag.get("flag","")
            detail = flag.get("detail","")
            prefix = "!!" if sev == "RED" else "! " if sev == "AMBER" else "  "
            lines.append(f"\n  {prefix} [{sev}] {cat.upper()} — {title}")
            if detail:
                for chunk in [detail[i:i+65] for i in range(0, len(detail), 65)]:
                    lines.append(f"       {chunk}")
    else:
        lines.append("  No flags raised.")

    # Data conflicts
    conflicts = [c for c in (extracted.get("data_conflicts") or []) if isinstance(c, dict) and c.get("field") and c.get("value_a")]
    if conflicts:
        lines.append("")
        lines.append("=" * 70)
        lines.append("  DATA CONFLICTS")
        lines.append("=" * 70)
        for c in conflicts:
            lines.append(f"\n  Field:      {c.get('field','')}")
            lines.append(f"  Value A:    {c.get('value_a','')}  ({c.get('source_a','')})")
            lines.append(f"  Value B:    {c.get('value_b','')}  ({c.get('source_b','')})")
            lines.append(f"  Resolution: {c.get('resolution','Manual review required')}")

    # Questions for broker
    questions = [q for q in (extracted.get("questions_for_broker") or []) if q and not isinstance(q, dict) and str(q).strip()]
    if questions:
        lines.append("")
        lines.append("=" * 70)
        lines.append("  QUESTIONS FOR BROKER")
        lines.append("=" * 70)
        for i, q in enumerate(questions, 1):
            lines.append(f"  {i}. {q}")

    # Gap analysis
    lines.append("")
    lines.append("=" * 70)
    lines.append("  GAP ANALYSIS")
    lines.append("=" * 70)
    if gap_analysis["critical_gaps"]:
        lines.append(f"\n  CRITICAL [{gap_analysis['critical_count']}] — blocking:")
        for _, label in gap_analysis["critical_gaps"]:
            lines.append(f"    [MISSING] {label}")
    else:
        lines.append("\n  CRITICAL GAPS: None.")
    if gap_analysis["advisory_gaps"]:
        lines.append(f"\n  ADVISORY [{gap_analysis['advisory_count']}] — useful but not blocking:")
        for _, label in gap_analysis["advisory_gaps"]:
            lines.append(f"    [MISSING] {label}")

    if extracted.get("extraction_notes"):
        lines.append("")
        lines.append("EXTRACTION NOTES")
        lines.append("-" * 40)
        lines.append(f"  {extracted['extraction_notes']}")
        lines.append(f"  Confidence: {extracted.get('extraction_confidence','Not stated')}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("  END OF AI SUMMARY — verify all figures against source documents")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_summary_report(
    extracted: dict,
    gap_analysis: dict,
    source_files: dict,
    class_label: str,
    output_folder: str,
    folder_name: str,
) -> str:
    """Build summary text and write to file. Returns filepath."""
    text        = build_summary_text(extracted, gap_analysis, source_files, class_label, folder_name)
    corr_folder = _output_root(output_folder)
    date_str    = datetime.date.today().strftime("%Y%m%d")
    filepath    = os.path.join(corr_folder, f"{date_str}_AI_Summary.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    return filepath