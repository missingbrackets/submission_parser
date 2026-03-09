# ============================================================
#  core/analysis.py
#  Gap analysis — compare extracted data against required fields.
#  No UI dependencies.
# ============================================================


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
            is_present = (
                len(val) > 0 and
                any(
                    any(v for v in (item.values() if isinstance(item, dict) else [item]) if v is not None)
                    for item in val
                )
            )
        elif isinstance(val, bool):
            is_present = True
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
