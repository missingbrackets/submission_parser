# ============================================================
#  core/extractor.py
#  Claude API call + shared low-level helpers.
#  No UI dependencies — safe to import in any frontend.
# ============================================================

import json
import os
import re
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
    Returns (parsed_dict, raw_response_text).
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
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = {"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
        else:
            parsed = {"extraction_error": "No JSON found in response", "raw_snippet": clean[:500]}

    return parsed, raw


# ── VALUE HELPERS ────────────────────────────────────────────

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
    """
    root = os.path.join(case_folder, AUTO_OUTPUT_DIR)
    os.makedirs(root, exist_ok=True)
    return root
