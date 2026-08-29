```python
"""Attendance summarizer for CSV text input."""


def summarize_attendance(csv_text: str) -> dict:
    """Summarize attendance counts by student and status.

    Args:
        csv_text: CSV-formatted string with columns student, date, status.

    Returns:
        Dict mapping each student name to a dict of status counts.
        Only 'present', 'absent', and 'late' are counted; other statuses skipped.

    Raises:
        ValueError: If input is empty or lacks required header row.
    """
    if not csv_text.strip():
        return {}

    lines = csv_text.splitlines()
    if not lines or not lines[0].strip():
        return {}

    header = [h.strip() for h in lines[0].split(',')]
    if 'student' not in header or 'date' not in header or 'status' not in header:
        raise ValueError("Missing required columns: student, date, status")

    row_idx = 1
    students = {}
    valid_statuses = {'present', 'absent', 'late'}

    for line in lines[1:]:
        if not line.strip():
            continue

        fields = [f.strip() for f in line.split(',')]
        if len(fields) != 3:
            continue

        student, date, status = fields

        if not student or not date or not status:
            continue

        if status not in valid_statuses:
            continue

        if student not in students:
            students[student] = {'present': 0, 'absent': 0, 'late': 0}

        students[student][status] += 1

    return students
```