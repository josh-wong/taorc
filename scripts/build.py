#!/usr/bin/env python3
"""Generate managed adapter blocks and manifests from the catalog and templates.

Reads VERSION, catalog/rules.yaml, and templates/agent-block.md, and writes
every generated artifact listed in v1-design-doc.md §6.1. ADAPTER_TARGETS is
empty until the adapter files exist to receive a managed block (MS5) — until
then this script renders and budget-checks the block without writing it
anywhere, so the generation path is exercised well before it has a target.
"""

from __future__ import annotations

import sys
from pathlib import Path

from lib import REPO_ROOT, count_tokens, read_version, write_manifest_version

BLOCK_BEGIN = "<!-- taorc:begin v{version} -->"
BLOCK_END = "<!-- taorc:end -->"
AGENT_BLOCK_TOKEN_BUDGET = 700

# (target path relative to repo root, frontmatter template or None)
# Populated in MS5 once the adapter files exist to receive a managed block.
ADAPTER_TARGETS: list[tuple[str, str | None]] = []

# Manifest files whose "version" field must track VERSION.
# Populated once the manifests exist (.claude-plugin/, .codex-plugin/, gemini-extension.json).
MANIFEST_TARGETS: list[str] = []


def render_managed_block(version: str, template_text: str) -> str:
    body = template_text.strip("\n")
    return f"{BLOCK_BEGIN.format(version=version)}\n{body}\n{BLOCK_END}\n"


def apply_managed_block(path: Path, block: str, frontmatter: str | None = None) -> None:
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    else:
        existing = frontmatter or ""

    begin_prefix = BLOCK_BEGIN.split(" v")[0]
    has_begin = begin_prefix in existing
    has_end = BLOCK_END in existing

    if has_begin != has_end:
        raise ValueError(
            f"{path}: has a taorc managed-block begin marker without a matching end "
            "marker (or vice versa) -- fix the file by hand before running build.py"
        )

    if has_begin and has_end:
        start = existing.index(begin_prefix)
        end = existing.index(BLOCK_END) + len(BLOCK_END)
        # existing[end:] still carries the single newline that originally
        # separated the old end marker from whatever follows; strip it before
        # re-adding block's own trailing newline, or repeated runs accumulate
        # one extra blank line each time.
        remainder = existing[end:].removeprefix("\n")
        updated = existing[:start] + block.rstrip("\n") + "\n" + remainder
    else:
        separator = "\n" if existing and not existing.endswith("\n") else ""
        updated = existing + separator + block

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")


def main() -> int:
    version = read_version()
    template_path = REPO_ROOT / "templates" / "agent-block.md"
    template_text = template_path.read_text(encoding="utf-8")

    block = render_managed_block(version, template_text)
    tokens = count_tokens(block)
    if tokens > AGENT_BLOCK_TOKEN_BUDGET:
        print(
            f"error: rendered managed block is {tokens} tokens, "
            f"over the {AGENT_BLOCK_TOKEN_BUDGET}-token budget (§6.2)",
            file=sys.stderr,
        )
        return 1

    print(f"Rendered managed block for v{version} ({tokens} tokens, within budget).")

    if not ADAPTER_TARGETS:
        print("No adapter targets registered yet — nothing to write (see MS5).")
    for relative_path, frontmatter in ADAPTER_TARGETS:
        apply_managed_block(REPO_ROOT / relative_path, block, frontmatter)
        print(f"Updated {relative_path}")

    for relative_path in MANIFEST_TARGETS:
        write_manifest_version(REPO_ROOT / relative_path, version)
        print(f"Synced version in {relative_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
