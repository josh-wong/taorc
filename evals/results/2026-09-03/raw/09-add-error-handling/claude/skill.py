```python
# starter/config_loader.py
import json
from pathlib import Path


class ConfigError(Exception):
    """A config file is missing, malformed, or incomplete."""


def load_config(path):
    """Load host/port/timeout_secs from a JSON config file.

    `timeout_secs` defaults to 30 when absent. Raises ConfigError if the file
    is missing, is not valid JSON, or omits `host` or `port`.
    """
    config_path = Path(path)

    try:
        with config_path.open() as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"No config file at {config_path}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"{config_path} is not valid JSON: {e}") from e

    missing_keys = [key for key in ("host", "port") if key not in raw]
    if missing_keys:
        raise ConfigError(
            f"{config_path} is missing required key(s): {', '.join(missing_keys)}"
        )

    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
```

**Choices worth naming**

- **One `ConfigError` for all three cases.** Three raise sites share it, so it isn't a speculative abstraction (`S6`), and it gives callers a single thing to catch around startup. If you'd rather not add a type, `ValueError` everywhere works with no other changes.
- **Every message names the path**, so the error is actionable without a traceback. `JSONDecodeError`'s own text carries line and column, so it's forwarded rather than re-described (`C7`).
- **Missing keys are collected, not short-circuited** — a config missing both `host` and `port` reports both in one run instead of two.
- **Docstring documents the raises**, since this change is exactly what altered the function's contract (`C14`). No inline comments were added; the code says what it does.

**What I deliberately left alone**

- The return dict, the `timeout_secs` default, and the read itself are byte-for-byte unchanged (`X1`, `X4`).
- The `path` parameter name stays as-is despite being slightly vague — it's the public signature (`X3`).
- **One gap you may want to close:** valid JSON that isn't an object (e.g. a top-level list) still escapes as a bare `TypeError`, which is the failure mode you asked to eliminate — but it wasn't in your three cases, so I didn't widen the diff. One line after the parse closes it:
  ```python
  if not isinstance(raw, dict):
      raise ConfigError(f"{config_path} must contain a JSON object, not {type(raw).__name__}")
  ```
  Say the word and I'll add it.

I couldn't run `taorc_lint.py` here — no file access in this session. If the script is present in your repo, `python .claude/skills/readable-code/scripts/taorc_lint.py --changed` should come back clean on this edit.