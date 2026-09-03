Here’s a cleaned-up version that keeps behavior identical (same inputs → same output string):

```python
import statistics


def process_data(items):
    """Return summary statistics for a non-empty sequence of items with 'value' keys.

    Returns a dict with keys: 'average', 'max', 'min'.
    Raises KeyError if an item lacks 'value'.
    Raises statistics.StatisticsError if items is empty.
    """
    values = [item["value"] for item in items]

    return {
        "average": statistics.mean(values),
        "max": max(values),
        "min": min(values),
    }


def generate_report(data):
    summary = process_data(data)
    return f"avg={summary['average']}, max={summary['max']}, min={summary['min']}"
```