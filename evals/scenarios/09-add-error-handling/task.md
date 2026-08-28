`starter/config_loader.py` has no error handling. Add it so `load_config`
fails with a clear, actionable message (not a bare traceback) for these
cases:

- The file doesn't exist.
- The file isn't valid JSON.
- A required key (`host` or `port`) is missing.

Keep the function's return shape and default `timeout_secs` behavior
unchanged. Don't restructure the parts of the function that already work.
