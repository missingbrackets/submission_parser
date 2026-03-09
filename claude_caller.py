# ============================================================
#  claude_caller.py  — backward-compatibility shim
#
#  All logic has moved to the core/ package.
#  This module re-exports everything so existing imports
#  continue to work without modification.
# ============================================================

from core.extractor import (
    call_claude_extraction,
    _safe,
    _parse_amount,
    _output_root,
    AUTO_OUTPUT_DIR,
)
from core.analysis import run_gap_analysis
from core.outputs import (
    build_csv_row,
    save_csv,
    build_claims_csv_rows,
    save_claims_csv,
    build_locations_csv_rows,
    save_locations_csv,
    TRIAGE_SCHEMA,
    build_triage_row,
    save_triage_csv,
    build_triage_locations_rows,
    save_triage_locations_csv,
    DIRECT_TRIAGE_FLAG_FIELDS,
    DIRECT_TRIAGE_SCHEMA,
    _rag_colour,
    build_direct_triage_row,
    save_direct_triage_csv,
)
from core.report import build_summary_text, save_summary_report

__all__ = [
    "call_claude_extraction",
    "_safe", "_parse_amount", "_output_root", "AUTO_OUTPUT_DIR",
    "run_gap_analysis",
    "build_csv_row", "save_csv",
    "build_claims_csv_rows", "save_claims_csv",
    "build_locations_csv_rows", "save_locations_csv",
    "TRIAGE_SCHEMA", "build_triage_row", "save_triage_csv",
    "build_triage_locations_rows", "save_triage_locations_csv",
    "DIRECT_TRIAGE_FLAG_FIELDS", "DIRECT_TRIAGE_SCHEMA",
    "_rag_colour", "build_direct_triage_row", "save_direct_triage_csv",
    "build_summary_text", "save_summary_report",
]
