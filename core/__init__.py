# ============================================================
#  core/__init__.py
#  Public API — import from core directly.
# ============================================================

from core.extractor import call_claude_extraction, _safe, _parse_amount, _output_root, AUTO_OUTPUT_DIR
from core.analysis import run_gap_analysis
from core.outputs import (
    build_csv_row, save_csv,
    build_claims_csv_rows, save_claims_csv,
    build_locations_csv_rows, save_locations_csv,
    TRIAGE_SCHEMA, build_triage_row, save_triage_csv,
    build_triage_locations_rows, save_triage_locations_csv,
    DIRECT_TRIAGE_FLAG_FIELDS, DIRECT_TRIAGE_SCHEMA,
    build_direct_triage_row, save_direct_triage_csv,
)
from core.report import build_summary_text, save_summary_report
from core.processor import process_submission, process_batch, save_submission_outputs

__all__ = [
    "call_claude_extraction", "_safe", "_parse_amount", "_output_root", "AUTO_OUTPUT_DIR",
    "run_gap_analysis",
    "build_csv_row", "save_csv",
    "build_claims_csv_rows", "save_claims_csv",
    "build_locations_csv_rows", "save_locations_csv",
    "TRIAGE_SCHEMA", "build_triage_row", "save_triage_csv",
    "build_triage_locations_rows", "save_triage_locations_csv",
    "DIRECT_TRIAGE_FLAG_FIELDS", "DIRECT_TRIAGE_SCHEMA",
    "build_direct_triage_row", "save_direct_triage_csv",
    "build_summary_text", "save_summary_report",
    "process_submission", "process_batch", "save_submission_outputs",
]
