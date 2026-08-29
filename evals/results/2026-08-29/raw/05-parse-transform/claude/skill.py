```python
"""Count attendance rows per student from CSV text."""

import csv
import io

ATTENDANCE_STATUSES = ("present", "absent", "late")


def summarize_attendance(csv_text):
    r"""Count each student's rows by attendance status.

    `csv_text` is CSV with a header row and the columns student, date, and
    status. A row is skipped if its status is not one of ATTENDANCE_STATUSES
    or if it has no student name; a skipped row never creates an entry.

    Returns a dict mapping each student with at least one counted row to
    {"present": n, "absent": n, "late": n}. Every returned inner dict has all
    three keys. Text with only a header, or no text at all, returns {}.

    >>> summarize_attendance("student,date,status\nAmara,2026-01-05,late\n")
    {'Amara': {'present': 0, 'absent': 0, 'late': 1}}
    """
    counts_by_student = {}
    for row in csv.DictReader(io.StringIO(csv_text)):
        student = row.get("student")
        status = row.get("status")
        if not student or status not in ATTENDANCE_STATUSES:
            continue
        if student not in counts_by_student:
            counts_by_student[student] = dict.fromkeys(ATTENDANCE_STATUSES, 0)
        counts_by_student[student][status] += 1
    return counts_by_student
```

A few decisions worth naming:

- `csv.DictReader` over hand-splitting on commas (`S8`) — it handles quoted fields and embedded newlines for free.
- `ATTENDANCE_STATUSES` is both the validity check and the key set for each inner dict, so the two can't drift apart.
- The skip is a single guard clause at the top of the loop body (`F5`), which keeps the counting path unnested.
- The docstring states the corner cases — skipped rows, guaranteed keys, empty input — rather than describing the mechanics of the loop (`C14`), and the example is a runnable doctest (`C15`).

What I deliberately did **not** do:

- No stripping of whitespace around names or statuses, and no case-folding of `status`. You specified exact status values, and silently normalizing input is a behavior change disguised as robustness (`S5`).
- No `collections.defaultdict`. It would remove two lines but return a `defaultdict` to callers, where an unexpected lookup silently creates an entry instead of raising `KeyError`.
- No handling for a missing or misspelled header row; `DictReader` will simply yield rows whose `student` is `None`, which the existing guard skips. Say the word if you'd rather that raise.
- No file I/O or CLI wrapper — the function takes text, as asked.