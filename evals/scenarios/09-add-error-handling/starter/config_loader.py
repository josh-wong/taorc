import json
from pathlib import Path


def load_config(path):
    with Path(path).open() as f:
        raw = json.load(f)
    return {
        "host": raw["host"],
        "port": raw["port"],
        "timeout_secs": raw.get("timeout_secs", 30),
    }
