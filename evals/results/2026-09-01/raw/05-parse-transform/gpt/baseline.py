```python
# attendance.py

from __future__ import annotations

from typing import Dict


def summarize_attendance(csv_text: str) -> Dict[str, Dict[str, int]]:
    """
    Summarize attendance from CSV text.

    The CSV is expected to have a header with columns:
        student,date,status

    `status` is one of: "present", "absent", "late".
    Rows with any other status are ignored.

    Args:
        csv_text: The full CSV content as a string.

    Returns:
        A dict mapping each student name (str) to a dict:
            {
                "present": int,
                "absent": int,
                "late": int,
            }
        counting how many rows of each status that student has.
    """
    # Normalize line endings and split into lines
    lines = csv_text.splitlines()
    if not lines:
        return {}

    # Find header and its column indices
    header = lines[0].strip()
    if not header:
        # No usable header
        return {}

    columns = [col.strip() for col in header.split(",")]
    try:
        student_idx = columns.index("student")
        status_idx = columns.index("status")
    except ValueError:
        # Required columns not found
        return {}

    valid_statuses = {"present", "absent", "late"}
    summary: Dict[str, Dict[str, int]] = {}

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue  # skip empty lines

        parts = [part.strip() for part in line.split(",")]

        # Skip malformed rows that don't have enough columns
        if len(parts) <= max(student_idx, status_idx):
            continue

        student = parts[student_idx]
        status = parts[status_idx]

        if status not in valid_statuses:
            # Skip unrecognized status
            continue

        if student not in summary:
            summary[student] = {"present": 0, "absent": 0, "late": 0}

        summary[student][status] += 1

    return summary
```