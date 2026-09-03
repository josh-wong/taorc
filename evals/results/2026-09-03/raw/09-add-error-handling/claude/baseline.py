## `starter/config_loader.py`

```python
import json
from pathlib import Path


class ConfigError(Exception):
    """Raised when a config file is missing, malformed, or incomplete."""


def load_config(path):
    p = Path(path)

    try:
        with p.open() as f:
            raw = json.load(f)
    except FileNotFoundError as e:
        raise ConfigError(
            f"Config file not found: {p}\n"
            f"Create it, or pass the correct path."
        ) from e
    except IsADirectoryError as e:
        raise ConfigError(
            f"Expected a config file but {p} is a directory."
        ) from e
    except PermissionError as e:
        raise ConfigError(
            f"Cannot read config file {p}: permission denied."
        ) from e
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Config file {p} is not valid JSON: {e.msg} "
            f"(line {e.lineno}, column {e.colno})."
        ) from e

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Config file {p} must contain a JSON object, "
            f"got {type(raw).__name__}."
        )

    missing = [key for key in ("host", "port") if key not in raw]
    if missing:
        raise ConfigError(
            f"Config file {p} is missing required key(s): {', '.join(missing)}.\n"
            f'Example: {{"host": "localhost", "port": 8080}}'
        )

    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
```

## Notes on the choices

**One exception type.** Every failure raises `ConfigError`, so a caller can write a single `except ConfigError as e: print(e); sys.exit(1)` and get a readable message instead of a traceback. Every raise uses `from e` so the original exception is still in the chain for debugging.

**Messages say what's wrong *and* what to do.** The JSON case forwards `json.JSONDecodeError`'s `msg`/`lineno`/`colno`, which is the part that actually helps you find the typo. The missing-key case reports *all* missing keys at once rather than failing on `host` and making you re-run to discover `port` is also missing, and includes a minimal valid example.

**Two additions beyond the three listed cases,** both of which would otherwise produce exactly the bare tracebacks you asked me to eliminate:

- `IsADirectoryError` / `PermissionError` — sibling `OSError`s from the same `open()` call. Catching only `FileNotFoundError` would leave these leaking through.
- The `isinstance(raw, dict)` guard — a file containing `[1, 2, 3]` is *valid* JSON, so it passes the decode step, and then `raw["host"]` raises `TypeError: list indices must be integers or slices, not str`. That message doesn't mention the config file at all.

If you'd rather keep the scope strictly to the three listed cases, delete those two blocks; nothing else depends on them.

**Unchanged:** the return dict, the `timeout_secs` default of 30, and the `raw["host"]` / `raw["port"]` lookups. The key check happens before the return rather than by converting those lookups to `.get()`, so the successful path is byte-for-byte the same code as before.

**Not added** (would be scope creep — say the word if you want them): validation that `port` is an integer in range, that `host` is a non-empty string, or that `timeout_secs` is positive. Right now `{"host": null, "port": "banana"}` loads fine and fails later at connect time.