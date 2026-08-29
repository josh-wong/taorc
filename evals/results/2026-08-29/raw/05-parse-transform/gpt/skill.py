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
    Rows with any other status value are ignored.

    Args:
        csv_text: The full CSV content as a single string.

    Returns:
        A dict mapping each student name to a dict with keys
        "present", "absent", and "late" and integer counts.
    """
    if not csv_text.strip():
        return {}

    # Use defaultdict so we can increment counts without pre-checking keys.
    attendance_by_student: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"present": 0, "absent": 0, "late": 0}
    )

    lines = csv_text.splitlines()
    if not lines:
        return {}

    header = lines[0].strip()
    if not header:
        return {}

    # Basic header validation and column index lookup.
    header_columns = [column.strip() for column in header.split(",")]
    try:
        student_idx = header_columns.index("student")
        date_idx = header_columns.index("date")
        status_idx = header_columns.index("status")
    except ValueError:
        # Required columns missing; cannot summarize.
        return {}

    valid_statuses = {"present", "absent", "late"}

    for line in lines[1:]:
        if not line.strip():
            continue

        columns = [column.strip() for column in line.split(",")]

        # Skip rows that don't have enough columns.
        if max(student_idx, date_idx, status_idx) >= len(columns):
            continue

        student_name = columns[student_idx]
        status = columns[status_idx]

        if status not in valid_statuses:
            # Ignore rows with unrecognized status.
            continue

        attendance_by_student[student_name][status] += 1

    return dict(attendance_by_student)
```