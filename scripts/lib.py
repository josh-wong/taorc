"""Shared helpers for build.py and validate.py."""

from __future__ import annotations

import json
import re
import sys
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

# Rule IDs are only recognized inside backtick code spans (the citation
# convention used throughout this repo, e.g. `N7`, `C4`, `X2` -- see
# AGENTS.md's "Controlled vocabularies" section). A bare, un-quoted pattern
# would also match ordinary prose tokens that happen to look like an ID
# (X11, F1, V8, S3, ...), producing false "unknown rule id" citations.
RULE_ID_PATTERN = re.compile(rf"`([{RULE_ID_PREFIX_CLASS}][0-9]+)`")


def read_version() -> str:
    return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    path = path or REPO_ROOT / "catalog" / "rules.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {"version": 1}
    # 'rules' is defaulted so callers can iterate it without guarding; the
    # placeholder catalog shipped before MS1 legitimately had none. 'precedence'
    # is deliberately NOT defaulted: injecting an empty list here would satisfy
    # the schema's required-key check and leave a catalog with no tiebreakers
    # reported only as a minItems failure -- and would hand any other caller a
    # silently empty tiebreaker list instead of a KeyError.
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
    except Exception as exc:
        # Printed rather than swallowed: a budget check that passes/fails near
        # the boundary should be traceable to "tiktoken was unavailable here"
        # rather than looking like a silent, unexplained verdict change.
        print(f"count_tokens: tiktoken unavailable ({exc!r}), using char-based estimate", file=sys.stderr)
        return max(1, int(len(text) // 2.5))


def find_rule_ids(text: str) -> set[str]:
    return set(RULE_ID_PATTERN.findall(text))


def read_manifest_version(path: Path) -> str | None:
    return json.loads(path.read_text(encoding="utf-8")).get("version")


def write_manifest_version(path: Path, version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
