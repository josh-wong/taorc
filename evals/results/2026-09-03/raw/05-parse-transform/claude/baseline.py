```python
"""Summarize student attendance records from CSV text.

Usage:
    from attendance import summarize_attendance
    summary = summarize_attendance(csv_text)
"""

from __future__ import annotations

import csv
import io

__all__ = ["summarize_attendance", "VALID_STATUSES"]

VALID_STATUSES = ("present", "absent", "late")


def summarize_attendance(csv_text: str) -> dict[str, dict[str, int]]:
    """Count attendance statuses per student.

    Args:
        csv_text: Text of a CSV file with a header row containing the
            columns ``student``, ``date`` and ``status``.  ``status`` is
            expected to be one of ``"present"``, ``"absent"`` or ``"late"``.

    Returns:
        A dict mapping each student name to a dict with the keys
        ``"present"``, ``"absent"`` and ``"late"`` holding the number of
        rows for that student with each status.

    Rows whose ``status`` is not recognized (and rows with a missing or
    empty student name) are skipped rather than raising.  A student that
    has no recognized rows at all does not appear in the result.
    """
    if not csv_text:
        return {}

    summary: dict[str, dict[str, int]] = {}

    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        return {}

    # Tolerate stray whitespace / capitalization in the header row.
    normalized = {
        (name or "").strip().lower(): name for name in reader.fieldnames
    }
    student_key = normalized.get("student")
    status_key = normalized.get("status")
    if student_key is None or status_key is None:
        return {}

    for row in reader:
        student = (row.get(student_key) or "").strip()
        status = (row.get(status_key) or "").strip().lower()

        if not student or status not in VALID_STATUSES:
            continue

        counts = summary.get(student)
        if counts is None:
            counts = {name: 0 for name in VALID_STATUSES}
            summary[student] = counts
        counts[status] += 1

    return summary


if __name__ == "__main__":
    SAMPLE = (
        "student,date,status\n"
        "Amara,2026-01-05,present\n"
        "Amara,2026-01-06,late\n"
        "Devon,2026-01-05,absent\n"
    )
    for name, counts in summarize_attendance(SAMPLE).items():
        print(f"{name}: {counts}")
```

Notes on the choices made where the spec was open-ended:

- **Parsing** uses `csv.DictReader` from the standard library, so quoted fields, embedded commas, and `\r\n` line endings are all handled correctly.
- **Normalization**: student names and statuses are stripped of surrounding whitespace, and statuses are lower-cased before matching, so `"Present "` counts as `present`. Anything else (e.g. `excused`, empty) is skipped silently.
- **Missing/blank student names** are treated like unrecognized rows and skipped.
- A student whose rows are *all* skipped does not get an all-zero entry; only students with at least one recognized row appear in the result.
- Empty input, input with no header, or a header lacking `student`/`status` returns `{}` instead of raising.