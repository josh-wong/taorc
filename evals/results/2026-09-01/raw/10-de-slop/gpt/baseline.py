```python
import statistics


def process_data(data):
    values = [item["value"] for item in data]

    return {
        "average": statistics.mean(values),
        "max": max(values),
        "min": min(values),
    }


def generate_report(data):
    result = process_data(data)
    return f"avg={result['average']}, max={result['max']}, min={result['min']}"
```