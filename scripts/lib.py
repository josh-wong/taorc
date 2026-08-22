"""Shared helpers for build.py and validate.py."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

CATEGORY_PREFIXES = {
    "principles": "P",
    "names": "N",
    "aesthetics": "A",
    "comments": "C",
    "control-flow": "F",
    "expressions": "E",
    "variables": "V",
    "structure": "S",
    "tests": "T",
    "guardrails": "X",
}

# Derived from CATEGORY_PREFIXES so the two never drift apart. Kept in sync
# with catalog/schema.json's `id` pattern by validate.py's
# check_schema_prefix_sync(), since a JSON schema can't import this constant.
RULE_ID_PREFIX_CLASS = "".join(sorted(CATEGORY_PREFIXES.values()))
RULE_ID_PATTERN = re.compile(rf"\b[{RULE_ID_PREFIX_CLASS}][0-9]+\b")


def read_version() -> str:
    return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    path = path or REPO_ROOT / "catalog" / "rules.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {"version": 1, "rules": []}
    data.setdefault("rules", [])
    return data


def count_tokens(text: str) -> int:
    """Approximate token count.

    Falls back to a character-based estimate when tiktoken is unavailable or
    unusable (not installed, or its encoding can't be fetched, e.g. no network
    on first use). The estimate uses ~2.5 characters/token, which runs high
    for typical English/code text and so is unlikely to under-count enough
    to mask an over-budget file, though it is not a strict upper bound.
    """
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, int(len(text) // 2.5))


def find_rule_ids(text: str) -> set[str]:
    return set(RULE_ID_PATTERN.findall(text))
