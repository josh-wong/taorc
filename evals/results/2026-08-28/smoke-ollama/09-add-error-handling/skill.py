```python
# starter/config_loader.py
import json
from pathlib import Path


def load_config(path):
    """Load configuration from a JSON file with validation."""
    
    if not Path(path).exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    try:
        with Path(path).open() as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {path} ({e})")
    
    if "host" not in raw:
        raise KeyError("Missing required key 'host' in configuration")
    if "port" not in raw:
        raise KeyError("Missing required key 'port' in configuration")
    
    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
```