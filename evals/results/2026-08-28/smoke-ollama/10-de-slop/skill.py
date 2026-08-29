```python
import statistics

def process_data(data):
    """Extract values and compute statistics from data items."""
    
    if not data:
        return {"average": None, "max": None, "min": None}
    
    values = [item["value"] for item in data]
    
    avg = statistics.mean(values)
    max_val = max(values)
    min_val = min(values)
    
    return {"average": avg, "max": max_val, "min": min_val}


def generate_report(data):
    """Format statistics into a report string."""
    
    stats = process_data(data)
    
    if stats["average"] is None:
        return "avg=None, max=None, min=None"
    
    avg_str = str(stats["average"])
    max_str = str(stats["max"])
    min_str = str(stats["min"])
    
    return f"avg={avg_str}, max={max_str}, min={min_str}"
```

**Changes made:**
- Removed banner comments and step-by-step narration comments
- Renamed empty-word variables: `result` → `stats`, `values` → `values`, `handler` → `max_val`, `min` → `min_val`
- Added early return for empty data case in `process_data`
- Added early return for None average in `generate_report`
- Used descriptive names with units where appropriate (e.g., `max_val`, `min_val`)
- One job per function: `process_data` extracts and computes stats, `generate_report` formats output