```python
import statistics

def process_data(data):
    """Process data and compute statistics."""
    
    values = [item["value"] for item in data]
    
    result = {
        "average": statistics.mean(values),
        "max": max(values),
        "min": min(values)
    }
    
    return result


def generate_report(data):
    """Generate a report string from processed data."""
    
    result = process_data(data)
    output = f"avg={result['average']}, max={result['max']}, min={result['min']}"
    
    return output
```