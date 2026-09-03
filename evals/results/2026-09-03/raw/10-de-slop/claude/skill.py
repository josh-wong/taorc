## Cleaned file

```python
# starter/report.py
import statistics


def process_data(data):
    """Return the average, max, and min of the "value" field across `data` records.

    Raises statistics.StatisticsError if `data` is empty.
    """
    values = [item["value"] for item in data]
    return {
        "average": statistics.mean(values),
        "max": max(values),
        "min": min(values),
    }


def generate_report(data):
    """Format the summary stats of `data` as one "avg=..., max=..., min=..." line."""
    stats = process_data(data)
    return f"avg={stats['average']}, max={stats['max']}, min={stats['min']}"
```

## What changed

```text
[X8] starter/report.py:3-5  Banner comment carries no information
  # ==========================================
  # Report generation module
  # ==========================================
  → deleted

[X7] starter/report.py:8,11,20,24,28,31  Comments narrate the author's plan
  # Step 1: initialize the result
  → deleted all six "Step N:" markers

[C1] starter/report.py:15,17,36,38,40  Comments restate the line below them
  # add it to the list
  values.append(value)
  → deleted

[N9] starter/report.py:25  Role word naming a plain number
  handler = max(values)
  → inlined into the returned dict; the key "max" already names it

[V1] starter/report.py:9,22,25  Variables that only carry a value one line
  result = {} ... avg = statistics.mean(values) ... result["average"] = avg
  → build and return the dict directly

[V1] starter/report.py:14  Loop variable used once
  value = item["value"]; values.append(value)
  → list comprehension

[C14] starter/report.py:7,35  Callers can't see the expected input shape or the
      empty-input behavior
  → added a one-line docstring to each function

[N1] starter/report.py:36  Empty word for the stats dict
  result = process_data(data)
  → stats
```

Evaluation order is unchanged: `mean` still runs before `max` before `min`, so
empty input raises the same `StatisticsError` from the same call, and a record
missing `"value"` raises the same `KeyError`. Dict insertion order is preserved,
so the f-string output is byte-identical.

## What I left alone

- **`process_data` and `generate_report` names.** `process_data` is vague — `process` says nothing and `data` says nothing (`N1`, `N9`); `summarize_values` would be honest. Both are module-level and may be imported elsewhere, so renaming is out of scope (`X3`). Say the word and I'll rename plus update call sites.
- **The `data` parameter on both functions.** Same reason: in Python a parameter name is part of the callable interface, and you asked for identical inputs. `records` would be the fix if you want it.
- **The two-function split.** `generate_report` calls `process_data` exactly once and nothing else calls it, which is the shape `S6` warns about. But collapsing them changes the module's surface, and this is a readability pass (`X1`, `X4`).
- **Whitespace and line length** — left to your formatter (`X5`); the output above is Black-compatible.

I couldn't run step 4: I have no file access this turn, so I couldn't check whether `scripts/taorc_lint.py` exists under any of the skill roots. If it's installed, run `python <root>/scripts/taorc_lint.py --changed` against this file.