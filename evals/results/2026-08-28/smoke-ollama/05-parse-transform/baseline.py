```python
import csv
from io import StringIO


def summarize_attendance(csv_text):
    """
    Summarize attendance data from CSV text.

    Args:
        csv_text: String containing CSV data with columns student,date,status

    Returns:
        Dict mapping student names to dicts with counts for 'present', 'absent', 'late'
    """
    result = {}

    reader = csv.DictReader(StringIO(csv_text))

    for row in reader:
        try:
            student = row['student']
            status = row['status']
        except KeyError:
            continue  # Skip rows with missing fields

        if status not in ('present', 'absent', 'late'):
            continue  # Skip rows with unrecognized status

        if student not in result:
            result[student] = {'present': 0, 'absent': 0, 'late': 0}

        if status == 'present':
            result[student]['present'] += 1
        elif status == 'absent':
            result[student]['absent'] += 1
        elif status == 'late':
            result[student]['late'] += 1

    return result
```