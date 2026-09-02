Here’s a cleaned-up version that keeps behavior identical (same inputs, same output string), but removes narration, banners, and empty-word names:

```python
import statistics


def process_data(items):
    """Return dict with average, max, and min of item['value'] for non-empty items.

    Raises:
        KeyError: if any item lacks a 'value' key.
        statistics.StatisticsError: if items is empty.
        TypeError: if values are not numeric.
    """
    values = [item["value"] for item in items]

    return {
        "average": statistics.mean(values),
        "max": max(values),
        "min": min(values),
    }


def generate_report(items):
    metrics = process_data(items)
    return (
        f"avg={metrics['average']}, "
        f"max={metrics['max']}, "
        f"min={metrics['min']}"
    )
```