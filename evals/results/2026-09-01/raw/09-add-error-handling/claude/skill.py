```python
# starter/config_loader.py
import json
from pathlib import Path


class ConfigError(Exception):
    """A config file is missing, malformed, or incomplete."""


def load_config(path):
    """Read a JSON config file and return its host, port, and timeout_secs.

    timeout_secs defaults to 30 when the file omits it.

    Raises ConfigError if the file does not exist, is not valid JSON, or is
    missing "host" or "port".
    """
    config_path = Path(path)

    try:
        with config_path.open() as f:
            raw = json.load(f)
    except FileNotFoundError as err:
        raise ConfigError(f"Config file not found: {config_path}") from err
    except json.JSONDecodeError as err:
        # str(err) already carries the line and column of the syntax error.
        raise ConfigError(f"Config file {config_path} is not valid JSON: {err}") from err

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Config file {config_path} must contain a JSON object, "
            f"not {type(raw).__name__}"
        )

    missing = [key for key in ("host", "port") if key not in raw]
    if missing:
        raise ConfigError(
            f"Config file {config_path} is missing required key(s): "
            f"{', '.join(missing)}"
        )

    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
```

## What changed and why

- **One exception type, `ConfigError`.** All three failures are the same thing from a caller's point of view — "this config is unusable" — so a caller can write one `except`. If you'd rather callers catch built-ins (`FileNotFoundError` / `ValueError`), say so and I'll swap it; that's a real alternative, not an oversight.
- **Each message names the file and the specific problem** so the message alone is enough to act on.
- **Missing keys are collected, not short-circuited** — a file missing both reports both, rather than making you fix one and re-run.
- **Docstring added** (`C14`). The function now has failure modes a caller can't see from the signature, and the `timeout_secs` default was previously undocumented.
- **`from err` on both re-raises** so the original exception is still available when debugging.

## One addition beyond the three cases you listed

The `isinstance(raw, dict)` guard. A file containing `[1, 2]` or `"hello"` is valid JSON, so it passes the decode check, and then `raw["host"]` raises `TypeError: list indices must be integers` — exactly the bare traceback you're trying to eliminate. It's four lines and easy to drop if you'd rather keep the change strictly to the three listed cases.

## What I deliberately left alone

- **The return dict and the `30` default** — untouched, as asked.
- **`path` stays untyped and unannotated.** The file has no type hints; matching the local convention beats improving it in an unrelated diff.
- **No `PermissionError` or `IsADirectoryError` handling.** Both are real bare-traceback paths, but they're outside what you asked for and each needs its own message. Worth a follow-up if this loads user-supplied paths.
- **No module-level `REQUIRED_KEYS` constant.** It'd be used exactly once, and the docstring already states the contract — a single-use name here adds indirection without adding information.

## Verification

I don't have access to the repo here, so I couldn't run step 4 of the loop. If `scripts/taorc_lint.py` exists under one of the skill roots, run `python <root>/scripts/taorc_lint.py --changed` against this file before committing.