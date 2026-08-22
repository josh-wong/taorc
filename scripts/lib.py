"""Shared helpers for build.py and validate.py."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

RULE_ID_PATTERN = re.compile(r"\b[PNACFEVSTX][0-9]+\b")

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

    Falls back to a character-based estimate when tiktoken is unavailable,
    which is close enough for a budget guardrail (real tokenizer counts are
    always <= this estimate for English prose).
    """
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        return max(1, len(text) // 4)


def find_rule_ids(text: str) -> set[str]:
    return set(RULE_ID_PATTERN.findall(text))
