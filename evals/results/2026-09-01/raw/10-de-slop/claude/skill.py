## `starter/report.py`

```python
import statistics


def process_data(data):
    """Return the average, max, and min of each record's "value" field.

    Raises statistics.StatisticsError if `data` is empty.
    """
    values = [item["value"] for item in data]
    return {
        "average": statistics.mean(values),
        "max": max(values),
        "min": min(values),
    }


def generate_report(data):
    """Format the summary statistics of `data` as a single line."""
    stats = process_data(data)
    return f"avg={stats['average']}, max={stats['max']}, min={stats['min']}"
```

## What changed

```text
[X8] starter/report.py:4-6  Banner comment / section divider
  # ==========================================
  # Report generation module
  # ==========================================
  → deleted; the module name already says this

[X7] starter/report.py:9,12,20,24,28,31  Comments narrate the author's plan
  # Step 1: initialize the result
  → deleted all six "Step N:" markers

[C1] starter/report.py:15,17,36,38,40  Comments restate the line below
  # add it to the list
  values.append(value)
  → deleted

[N9] starter/report.py:25  Role word used for a number
  handler = max(values)
  → variable removed; value now assigned directly to the "max" key

[N1] starter/report.py:37  Empty-word name for summary statistics
  result = process_data(data)
  → renamed to `stats`

[V1] starter/report.py:10,21,25,39  Variables that only carry a value one line
  result = {} ... return result;  avg = ...;  output = f"..."; return output
  → inlined; the accumulator dict is now a single literal and both functions
    return their expression directly

[C7] starter/report.py:8,35  Empty-input behavior undocumented
  → added a docstring to each function; `process_data` now states that empty
    input raises statistics.StatisticsError
```

**Behavior is identical.** The returned dict has the same three keys in the same
insertion order (`average`, `max`, `min`), the dict literal evaluates `mean`
first so an empty list raises `StatisticsError` at exactly the same point as
before, and the comprehension materializes the full list before any reduction —
so a missing `"value"` key raises the same `KeyError` at the same time.

## What I deliberately left alone

- **`process_data` is a vague name** (`N1`, `N9`) — `summarize_values` would read
  better. Both functions are module-level and may have callers outside this file,
  so `X3` says don't rename exported symbols unless asked.
- **The `data` parameter is an empty word** (`N1`). In Python a parameter name is
  part of the callable signature, so renaming it would break any
  `generate_report(data=...)` keyword call — that's a behavior change, which
  `X4` keeps out of a readability pass. `records` is the rename I'd make if you
  confirm there are no keyword callers.
- **`process_data` as a separate function.** Only one caller, so `S6` argues
  against the split, but the abstraction already exists and may be imported
  elsewhere. Not mine to collapse.

I found no `scripts/taorc_lint.py` available to run against these changes, so
the verify step is the self-check above rather than linter output.