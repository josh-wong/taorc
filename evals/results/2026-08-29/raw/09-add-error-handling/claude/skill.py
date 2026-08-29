## The change

```python
# starter/config_loader.py
import json
from pathlib import Path


class ConfigError(Exception):
    """The config file is missing, malformed, or incomplete."""


def load_config(path):
    """Load a config file, raising ConfigError with a fixable message on failure."""
    config_path = Path(path)
    try:
        with config_path.open() as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"No config file at {config_path.resolve()}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"{config_path} is not valid JSON: {e.msg} "
            f"(line {e.lineno}, column {e.colno})"
        ) from None

    if not isinstance(raw, dict):
        raise ConfigError(
            f"{config_path} must hold a JSON object, got {type(raw).__name__}"
        )

    # Report every missing key at once so the file only needs one round of edits.
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

## Decisions worth knowing about

**One exception type, not three.** Callers of a config loader almost always
want a single thing to catch, and "missing, malformed, incomplete" is one
category from the caller's side. Three builtin types would force
`except (FileNotFoundError, ValueError, KeyError)` at every call site.

**`resolve()` in the not-found message only.** When the file *isn't* there, the
useful question is "where did it look?", and a relative path hides the answer.
The other two messages describe a file that was found, so the path as given is
enough.

**`from None` on both re-raises.** Each `ConfigError` message already carries
everything the original exception had — `JSONDecodeError`'s `msg`, `lineno`,
and `colno` are copied into the text. Chaining would add a
"During handling of the above exception" block above the message you actually
want the user to read, which is the bare traceback the task asked to avoid.

**All missing keys at once, not fail-fast.** A user with both keys missing
otherwise edits, re-runs, and fails again. This is the one thing in the
function a reader could reasonably ask "why?" about, so it's the one comment
(`C6`, `C3`).

## What I deliberately did not change

- **`raw.get("timeout_secs", 30)`** — left exactly as-is, including the inline
  `30`. Hoisting it to a `DEFAULT_TIMEOUT_SECS` constant would be restructuring
  a part that already works (`X1`).
- **`raw` as a name** — it's the file's existing vocabulary, and it's honest
  about being unvalidated (`X2`).
- **`OSError` beyond `FileNotFoundError`** — permission denied and
  is-a-directory still surface as tracebacks. You listed three cases; catching
  a fourth is a scope decision for you, not me. Say the word if you want
  `except OSError` broadened.
- **The return shape and the parameter name `path`** — public surface,
  untouched (`X3`).

One addition beyond your three cases, flagged because it widens the diff
slightly: the `isinstance(raw, dict)` guard. A config file containing a valid
JSON array parses fine and then dies on `"host" not in raw` behaving oddly or
`raw["host"]` raising `TypeError` — a bare traceback, which is the thing you
asked to eliminate. It's two lines. Drop it if you'd rather keep the diff to
exactly the three listed cases.

## Verification

I don't have file access in this conversation, so I couldn't run step 4. If
`scripts/taorc_lint.py` exists under one of the skill roots, run:

```
python <root>/scripts/taorc_lint.py --changed
```

I also didn't add tests, since you didn't ask. If you want them, the four
worth having are one per failure mode plus one confirming `timeout_secs`
still defaults to 30.