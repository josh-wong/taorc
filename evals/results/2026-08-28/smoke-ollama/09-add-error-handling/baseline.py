```python
# starter/config_loader.py
import json
from pathlib import Path


def load_config(path):
    if not Path(path).exists():
        raise FileNotFoundError(f"Configuration file '{path}' does not exist.")
    
    try:
        with Path(path).open() as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file '{path}': {e}")
    
    if "host" not in raw:
        raise ValueError("Missing required key 'host' in configuration file.")
    
    if "port" not in raw:
        raise ValueError("Missing required key 'port' in configuration file.")
    
    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
```