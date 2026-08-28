Write `attendance.py` with a function `summarize_attendance(csv_text)` that
takes the text of a CSV with columns `student,date,status` (`status` is
`"present"`, `"absent"`, or `"late"`) and returns a dict mapping each student
name to a dict `{"present": n, "absent": n, "late": n}` counting their rows.

Example input:

```text
student,date,status
Amara,2026-01-05,present
Amara,2026-01-06,late
Devon,2026-01-05,absent
```

Parse with the standard library only (no third-party CSV parser). Skip rows
with an unrecognized `status` rather than raising.
