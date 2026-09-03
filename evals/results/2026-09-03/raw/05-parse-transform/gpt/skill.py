```python
# attendance.py

from __future__ import annotations

from collections import defaultdict
from typing import Dict


def summarize_attendance(csv_text: str) -> Dict[str, Dict[str, int]]:
    """
    Summarize attendance counts per student from CSV text.

    The CSV must have a header row with columns: student,date,status.
    Status values counted are: "present", "absent", "late".
    Rows with any other status are ignored.

    Returns a dict mapping each student name to a dict:
    {"present": n, "absent": n, "late": n}.

    Empty input or input with no valid data rows returns an empty dict.
    """
    if not csv_text.strip():
        return {}

    # Using defaultdict to avoid repeated existence checks per student.
    attendance_by_student: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"present": 0, "absent": 0, "late": 0}
    )

    lines = csv_text.splitlines()
    if not lines:
        return {}

    header = lines[0].strip()
    if not header:
        return {}

    # Basic header validation by position; we do not support re-ordered columns.
    expected_header = ["student", "date", "status"]
    header_columns = [column.strip() for column in header.split(",")]
    if header_columns != expected_header:
        # Header is not in the expected format; no rows are processed.
        return {}

    for line in lines[1:]:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        columns = [column.strip() for column in stripped_line.split(",")]
        if len(columns) != 3:
            # Malformed row; skip it rather than raising.
            continue

        student_name, _date_text, status_text = columns

        if status_text not in ("present", "absent", "late"):
            # Unrecognized status is explicitly ignored.
            continue

        attendance_by_student[student_name][status_text] += 1

    # Convert defaultdict to a regular dict for a stable, predictable return type.
    return dict(attendance_by_student)
```