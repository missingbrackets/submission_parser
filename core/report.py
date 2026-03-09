# ============================================================
#  core/report.py
#  Build and save the AI summary report text file.
#  No UI dependencies.
# ============================================================

import datetime
import os

from core.extractor import _safe, _output_root


def build_summary_text(
    extracted: dict,
    gap_analysis: dict,
    source_files: dict,
    class_label: str,
    folder_name: str,
) -> str:
    """
    Build the full AI summary report as a plain-text string.
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

    questions = [q for q in (extracted.get("questions_for_broker") or []) if q and not isinstance(q, dict) and str(q).strip()]
    if questions:
        lines.append("")
        lines.append("=" * 70)
        lines.append("  QUESTIONS FOR BROKER")
        lines.append("=" * 70)
        for i, q in enumerate(questions, 1):
            lines.append(f"  {i}. {q}")

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
