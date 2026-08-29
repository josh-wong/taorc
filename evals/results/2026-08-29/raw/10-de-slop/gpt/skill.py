Here’s a cleaned-up version of `starter/report.py` with identical behavior and output:

```python
import statistics


def process_data(items):
    if not items:
        raise statistics.StatisticsError("mean requires at least one data point")

    values = [item["value"] for item in items]

    summary = {}
    summary["average"] = statistics.mean(values)
    summary["max"] = max(values)
    summary["min"] = min(values)

    return summary


def generate_report(data):
    summary = process_data(data)
    return f"avg={summary['average']}, max={summary['max']}, min={summary['min']}"
```