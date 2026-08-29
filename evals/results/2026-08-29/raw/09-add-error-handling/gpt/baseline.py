Here’s an updated version of `starter/config_loader.py` with targeted error handling added, while keeping the working structure and return shape unchanged:

```python
import json
from pathlib import Path


def load_config(path):
    try:
        with Path(path).open() as f:
            raw = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Config file not found at '{path}'. Please provide a valid path to a JSON config file."
        ) from e
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Config file at '{path}' is not valid JSON: {e.msg} (line {e.lineno}, column {e.colno})."
        ) from e

    try:
        return {
            "host": raw["host"],
            "port": raw["port"],
            "timeout_secs": raw.get("timeout_secs", 30),
        }
    except KeyError as e:
        missing_key = e.args[0]
        raise KeyError(
            f"Missing required config key '{missing_key}' in '{path}'. "
            "Expected keys: 'host', 'port'."
        ) from e
```