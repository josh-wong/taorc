Here’s an updated `starter/config_loader.py` with targeted error handling and unchanged return shape/default behavior:

```python
import json
from pathlib import Path


def load_config(path):
    try:
        with Path(path).open() as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Config file not found at '{path}'. "
                                f"Please provide a valid path.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config file at '{path}' is not valid JSON. "
                         f"Please fix the JSON syntax.") from exc

    missing_keys = [key for key in ("host", "port") if key not in raw]
    if missing_keys:
        missing_list = ", ".join(missing_keys)
        raise KeyError(
            f"Config file at '{path}' is missing required key(s): {missing_list}. "
            f"Please add the missing key(s)."
        )

    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
```