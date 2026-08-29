## Cleaned file

```python
# starter/report.py
import statistics


def process_data(data):
    values = [item["value"] for item in data]
    return {
        "average": statistics.mean(values),
        "max": max(values),
        "min": min(values),
    }


def generate_report(data):
    stats = process_data(data)
    return f"avg={stats['average']}, max={stats['max']}, min={stats['min']}"
```

## Findings addressed

```text
[X8] starter/report.py:3-5  Banner comment / section divider
  # ==========================================
  # Report generation module
  # ==========================================
  → deleted; the filename already carries this, and the banner said nothing
    the module contents don't

[X7] starter/report.py:8,11,20,24,27,30  Comments narrating the author's plan
  # Step 1: initialize the result
  → deleted all six "Step N:" comments

[C1] starter/report.py:14,16,34,36,38  Comments restating the code
  # get the value from the item
  # add it to the list
  # return the output
  → deleted

[N9] starter/report.py:25  Role word naming a maximum
  handler = max(values)
  → removed the variable; the value flows straight into the "max" key

[N1] starter/report.py:9  Empty word for a stats dictionary
  result = {}
  → renamed to `stats` in generate_report; removed entirely in process_data,
    where the dict is now built as a literal

[V1] starter/report.py:9,21,25,35,37  Variables carrying a value one line
  avg = statistics.mean(values)
  result["average"] = avg
  → collapsed into the returned dict literal and the returned f-string
```

The `for`/`append` loop became a list comprehension — same iteration, same
single pass over `data`, no rule ID for that one, just fewer lines to read
before reaching the arithmetic.

## Behavior check

Identical:

- Key insertion order is still `average`, `max`, `min`, so any caller relying on
  dict ordering or `repr()` sees no change.
- Evaluation order is still `mean` → `max` → `min`, so an empty `data` still
  raises `statistics.StatisticsError` from `mean` rather than `ValueError` from
  `max`.
- A missing `"value"` key still raises `KeyError` during collection, before any
  statistic is computed.
- The output string format is byte-for-byte unchanged.

## Deliberately not changed

- **`process_data` and `generate_report` names.** Both are module-level and
  exported. `process_data` is vague (`N1`) and would be better as
  `summarize_values`, but renaming it breaks callers (`X3`). Say the word and
  I'll rename it plus update call sites.
- **The `data` parameter name.** Same reason. In Python a parameter name is part
  of the public signature — `process_data(data=rows)` is legal — so renaming it
  to `records` is an API change, not a readability change (`X3`, `X4`). Worth
  doing as its own step if you know nobody calls it by keyword.
- **No docstrings added.** The task was cleanup, not documentation, and two
  three-line functions with accurate names don't need `C8` treatment. Adding
  them would widen the diff (`X1`).
- **No error handling for empty input.** That would change behavior (`X4`).

I did not find `scripts/taorc_lint.py` under any of the searched skill roots, so
the verify step was skipped.