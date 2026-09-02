```python
"""Tally per-student attendance from a roll-call CSV export."""

import csv
import io

RECOGNIZED_STATUSES = ("present", "absent", "late")


def summarize_attendance(csv_text: str) -> dict[str, dict[str, int]]:
    r"""Count each student's rows by attendance status.

    `csv_text` is a CSV with a header row and the columns student, date, and
    status. Rows whose status is not in RECOGNIZED_STATUSES are skipped, so a
    student whose every row is unrecognized does not appear in the result at
    all. Empty text and a header-only file both return an empty dict.

    >>> summarize_attendance("student,date,status\nAmara,2026-01-06,late\n")
    {'Amara': {'present': 0, 'absent': 0, 'late': 1}}
    """
    counts_by_student: dict[str, dict[str, int]] = {}
    for row in csv.DictReader(io.StringIO(csv_text)):
        status = row["status"]
        if status not in RECOGNIZED_STATUSES:
            continue
        student = row["student"]
        if student not in counts_by_student:
            counts_by_student[student] = dict.fromkeys(RECOGNIZED_STATUSES, 0)
        counts_by_student[student][status] += 1
    return counts_by_student
```

Notes on a few decisions:

- **`csv.DictReader` over hand-splitting on commas** (`S8`) — it handles quoted fields and embedded commas, which a `line.split(",")` version would corrupt silently.
- **Short rows fall out for free.** `DictReader` fills a missing `status` with `None`, which fails the `RECOGNIZED_STATUSES` check and takes the same skip path as a typo'd status. No separate guard needed.
- **The guard clause comes first** (`F5`, `F6`) so the counting logic stays at one level of nesting.
- **The docstring covers the corner cases a caller cannot see from the signature** (`C14`): what happens to unrecognized rows, that a student can be missing entirely, and the empty-input result. The example row is a worked input/output rather than a description (`C15`), and doubles as a doctest.

Things I deliberately did **not** do:

- No normalization of case or surrounding whitespace on `student` or `status`. `"Present"` and `" late"` are unrecognized and get skipped. You did not specify it, and guessing wrong here silently merges or drops records (`S5`, `S6`) — say the word if the export is dirty.
- No tests file, since you asked for `attendance.py` only (`X1`). The doctest is runnable with `python -m doctest attendance.py -v` if you want a smoke check now.