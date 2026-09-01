Here’s an updated version of `starter/config_loader.py` with targeted error handling and unchanged return shape/default behavior:

```python
import json
from pathlib import Path


def load_config(path):
    try:
        with Path(path).open() as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config file is not valid JSON: {path}") from exc

    missing_keys = [key for key in ("host", "port") if key not in raw]
    if missing_keys:
        missing_list = ", ".join(missing_keys)
        raise KeyError(
            f"Config file {path} is missing required key(s): {missing_list}"
        )

    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
```