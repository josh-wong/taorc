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
    Empty input or input with no valid data rows returns an empty dict.

    This function never raises for bad status values; it simply skips them.
    It may raise ValueError if the header row is missing or malformed.
    """
    if not csv_text.strip():
        return {}

    lines = csv_text.splitlines()
    if not lines:
        return {}

    header = lines[0].strip()
    expected_header = "student,date,status"
    if header != expected_header:
        raise ValueError(f"Expected header '{expected_header}', got '{header}'")

    attendance_by_student: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"present": 0, "absent": 0, "late": 0}
    )
    valid_statuses = {"present", "absent", "late"}

    for raw_line in lines[1:]:
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(",")
        if len(parts) != 3:
            # Malformed row; skip it rather than guessing.
            continue

        student_name, _date_text, status_text = (part.strip() for part in parts)

        if status_text not in valid_statuses:
            # Unrecognized status is explicitly ignored.
            continue

        attendance_by_student[student_name][status_text] += 1

    return dict(attendance_by_student)
```