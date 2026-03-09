# ============================================================
#  core/processor.py
#  Orchestrates submission processing: file reading → Claude
#  extraction → gap analysis → CSV output.
#
#  Pure Python — no Streamlit or UI dependencies.
#  Uses callback functions for progress/status reporting so
#  any frontend (Streamlit, CLI, FastAPI, etc.) can hook in.
# ============================================================

import os
from typing import Callable, Optional

from core.extractor import call_claude_extraction
from core.analysis import run_gap_analysis
from core.outputs import (
    build_csv_row, save_csv,
    build_claims_csv_rows, save_claims_csv,
    build_locations_csv_rows, save_locations_csv,
    build_triage_row, save_triage_csv,
    build_triage_locations_rows, save_triage_locations_csv,
    build_direct_triage_row, save_direct_triage_csv,
)
from core.report import save_summary_report


def _noop(*args, **kwargs):
    pass


def process_submission(
    folder_path: str,
    class_choice: str,
    api_key: str,
    use_corr: bool = True,
    use_data: bool = True,
    on_progress: Optional[Callable] = None,
    on_status: Optional[Callable] = None,
) -> dict:
    """
    Process a single submission folder.

    Callbacks:
      on_progress(pct: int, text: str)  — progress percentage + label
      on_status(level: str, text: str)  — level is 'info' / 'warning' / 'error'

    Returns dict with keys:
      extracted, gap, all_files, folder_path, folder_name, skill
      or {'error': str} on failure.
    """
    from skills import get_skill
    from file_parser import extract_folder

    progress = on_progress or _noop
    status   = on_status   or _noop

    skill       = get_skill(class_choice)
    folder_name = os.path.basename(folder_path.rstrip("\\/"))

    progress(10, "Reading files...")
    all_files = {}
    if use_corr:
        all_files.update(extract_folder(folder_path, "01_correspondence"))
    if use_data:
        df = extract_folder(folder_path, "02_data")
        df = {k: v for k, v in df.items()
              if not k.endswith("AI_Summary.txt") and not k.endswith(".csv")}
        all_files.update(df)

    if not all_files:
        return {"error": "No supported files found in the selected subfolders."}

    combined_parts = [
        f"\n\n{'='*50}\nFILE: {fname}\n{'='*50}\n{info['text']}"
        for fname, info in all_files.items() if info["text"]
    ]
    combined_text = "\n".join(combined_parts)

    if not combined_text.strip():
        return {"error": "No text could be extracted from any files."}

    status("info", f"Extracted {len(combined_text):,} characters from {len(all_files)} file(s)")
    progress(30, f"Sending to Claude ({skill['label']} skill)...")

    try:
        extracted, _ = call_claude_extraction(combined_text, skill["system_prompt"], api_key)
    except Exception as e:
        return {"error": f"Claude API error: {e}"}

    progress(80, "Running gap analysis...")
    gap = run_gap_analysis(extracted, skill["required_fields"])
    progress(100, "Complete")

    return {
        "extracted":   extracted,
        "gap":         gap,
        "all_files":   all_files,
        "folder_path": folder_path,
        "folder_name": folder_name,
        "skill":       skill,
    }


def save_submission_outputs(
    extracted: dict,
    gap: dict,
    all_files: dict,
    folder_path: str,
    folder_name: str,
    skill: dict,
    output_folder: Optional[str] = None,
) -> dict:
    """
    Save all output files for one submission.
    output_folder defaults to folder_path (for single mode).
    In batch mode, pass the parent folder to consolidate CSVs.

    Returns dict of {output_type: filepath} for successfully saved files.
    """
    if output_folder is None:
        output_folder = folder_path

    saved = {}

    saved["summary"] = save_summary_report(
        extracted, gap, all_files, skill["label"], output_folder, folder_name
    )

    csv_row = build_csv_row(extracted, gap, skill["csv_schema"], folder_path, skill["label"])
    saved["csv"] = save_csv(csv_row, skill["csv_schema"], output_folder, "submission_data")

    claims_rows = build_claims_csv_rows(extracted, skill.get("claims_csv_schema", []))
    if claims_rows and skill.get("claims_csv_schema"):
        saved["claims"] = save_claims_csv(claims_rows, skill["claims_csv_schema"], output_folder)

    if extracted.get("sov_locations") is not None or extracted.get("tiv_total"):
        try:
            loc_rows, loc_schema = build_locations_csv_rows(extracted)
            if loc_rows:
                saved["locations"] = save_locations_csv(loc_rows, loc_schema, output_folder)
        except Exception:
            pass

    skill_code = skill.get("code", "")
    if skill_code == "PVQ":
        try:
            tr = build_triage_row(extracted, gap, folder_path, skill["label"])
            saved["triage"] = save_triage_csv(tr, output_folder)
            tl_rows, tl_schema = build_triage_locations_rows(extracted)
            if tl_rows:
                saved["triage_locations"] = save_triage_locations_csv(tl_rows, tl_schema, output_folder)
        except Exception:
            pass
    elif skill_code == "PVDT":
        try:
            dtr = build_direct_triage_row(extracted, gap, folder_path, skill["label"])
            saved["direct_triage"] = save_direct_triage_csv(dtr, output_folder)
        except Exception:
            pass

    return saved


def process_batch(
    parent_folder: str,
    class_choice: str,
    api_key: str,
    use_corr: bool = True,
    use_data: bool = True,
    on_progress: Optional[Callable] = None,
    on_status: Optional[Callable] = None,
) -> dict:
    """
    Discover all immediate subfolders of parent_folder and process each.

    Callbacks:
      on_progress(pct: int, text: str)
      on_status(level: str, subfolder: str, text: str)

    Returns {subfolder_name: result_dict}
    where result_dict is either a process_submission() result or {'error': str}.
    """
    from skills import get_skill
    from file_parser import extract_folder

    progress = on_progress or _noop
    status   = on_status   or _noop

    try:
        subfolders = sorted([
            d for d in os.listdir(parent_folder)
            if os.path.isdir(os.path.join(parent_folder, d))
            and not d.startswith(".")
            and d != "submission_tool_auto_outputs"
        ])
    except Exception as e:
        return {"__error__": str(e)}

    if not subfolders:
        return {"__error__": "No subfolders found in the selected parent folder."}

    skill = get_skill(class_choice)
    results = {}

    for idx, subfolder_name in enumerate(subfolders):
        subfolder_path = os.path.join(parent_folder, subfolder_name)
        pct = int((idx / len(subfolders)) * 100)
        progress(pct, f"Processing {subfolder_name} ({idx+1}/{len(subfolders)})...")
        status("info", subfolder_name, "reading files...")

        # Read files
        all_files = {}
        if use_corr:
            all_files.update(extract_folder(subfolder_path, "01_correspondence"))
        if use_data:
            df = extract_folder(subfolder_path, "02_data")
            df = {k: v for k, v in df.items()
                  if not k.endswith("AI_Summary.txt") and not k.endswith(".csv")}
            all_files.update(df)

        if not all_files:
            status("warning", subfolder_name, "no files found, skipping.")
            results[subfolder_name] = {"error": "No files found", "folder_path": subfolder_path}
            continue

        combined_parts = [
            f"\n\n{'='*50}\nFILE: {fname}\n{'='*50}\n{info['text']}"
            for fname, info in all_files.items() if info["text"]
        ]
        combined_text = "\n".join(combined_parts)

        if not combined_text.strip():
            status("warning", subfolder_name, "no text extractable, skipping.")
            results[subfolder_name] = {"error": "No text extracted", "folder_path": subfolder_path}
            continue

        status("info", subfolder_name, "sending to Claude...")
        try:
            extracted, _ = call_claude_extraction(combined_text, skill["system_prompt"], api_key)
        except Exception as e:
            status("error", subfolder_name, f"Claude error: {e}")
            results[subfolder_name] = {"error": str(e), "folder_path": subfolder_path}
            continue

        gap = run_gap_analysis(extracted, skill["required_fields"])

        status("info", subfolder_name, "saving outputs...")
        try:
            # Per-submission outputs saved to subfolder
            save_submission_outputs(
                extracted, gap, all_files, subfolder_path, subfolder_name, skill,
                output_folder=subfolder_path,
            )
            # Consolidated roll-up: also save to parent folder (appends)
            csv_row = build_csv_row(extracted, gap, skill["csv_schema"], subfolder_path, skill["label"])
            save_csv(csv_row, skill["csv_schema"], parent_folder, "submission_data_all")

            claims_rows = build_claims_csv_rows(extracted, skill.get("claims_csv_schema", []))
            if claims_rows and skill.get("claims_csv_schema"):
                save_claims_csv(claims_rows, skill["claims_csv_schema"], parent_folder)

            skill_code = skill.get("code", "")
            if skill_code == "PVQ":
                try:
                    tr = build_triage_row(extracted, gap, subfolder_path, skill["label"])
                    save_triage_csv(tr, parent_folder)
                    tl_rows, tl_schema = build_triage_locations_rows(extracted)
                    if tl_rows:
                        save_triage_locations_csv(tl_rows, tl_schema, parent_folder)
                except Exception:
                    pass
            elif skill_code == "PVDT":
                try:
                    dtr = build_direct_triage_row(extracted, gap, subfolder_path, skill["label"])
                    save_direct_triage_csv(dtr, parent_folder)
                except Exception:
                    pass
        except Exception as e:
            status("warning", subfolder_name, f"save error: {e}")

        results[subfolder_name] = {
            "extracted":   extracted,
            "gap":         gap,
            "all_files":   all_files,
            "folder_path": subfolder_path,
            "folder_name": subfolder_name,
            "skill":       skill,
        }

    progress(100, "Batch complete")
    return results
