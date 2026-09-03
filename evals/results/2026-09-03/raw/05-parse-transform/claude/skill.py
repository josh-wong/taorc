```python
"""Tally per-student attendance from CSV text."""

import csv
import io

TRACKED_STATUSES = ("present", "absent", "late")


def summarize_attendance(csv_text):
    r"""Count each student's attendance rows by status.

    csv_text is a CSV with a header row and the columns student, date, and
    status. Returns {student: {"present": n, "absent": n, "late": n}}, with a
    zero-filled entry for every student who has at least one row with a
    recognized status.

    Rows whose status is not one of TRACKED_STATUSES are skipped, so a student
    whose every row is unrecognized does not appear at all. Empty or
    header-only text gives {}.

    >>> summarize_attendance("student,date,status\nAmara,2026-01-05,late\n")
    {'Amara': {'present': 0, 'absent': 0, 'late': 1}}
    """
    counts_by_student = {}
    for row in csv.DictReader(io.StringIO(csv_text)):
        # A truncated row gives status None rather than raising, which falls
        # through to the same skip as any other unrecognized value.
        status = row.get("status")
        if status not in TRACKED_STATUSES:
            continue

        counts = counts_by_student.setdefault(
            row["student"], dict.fromkeys(TRACKED_STATUSES, 0)
        )
        counts[status] += 1

    return counts_by_student
```

**Notes on the choices**

- `csv.DictReader` over hand-splitting on commas (`S8`) — it handles quoted names like `"Vega, Amara"` for free.
- `counts_by_student` rather than `result` or `data` (`N1`, `N9`); `TRACKED_STATUSES` is the single source of both the validity check and the zero-filled keys, so the two can't drift apart.
- The docstring pins the corner cases a caller can't read off the signature: what happens to unrecognized rows, whether a fully-unrecognized student appears, and what empty input returns (`C14`), plus one worked example (`C15`).
- The only comment explains why `.get("status")` is safe against short rows while `row["student"]` is a plain subscript — the asymmetry is the thing a reader would stop on (`C6`).

**What I deliberately left alone**

- No `strip()` or case-folding on `status`. The spec says skip unrecognized values, and silently accepting `" Present"` is a behavior decision, not a readability one (`S5`, `X4`). Say the word if you want it and I'll add it as a separate change.
- `row["student"]` raises if the CSV has a `status` column but no `student` column. That's a malformed-header case the spec didn't cover, and swallowing it would hide a real problem.
- No tests written, since you asked only for the module. The distinct outcomes worth pinning down if you want them: normal tally, unknown status skipped, student with only unknown statuses absent from the result, header-only input, empty string.

I didn't run the `taorc-lint` verify step — no `scripts/taorc_lint.py` was available in this session.