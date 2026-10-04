#!/usr/bin/env python3
"""Generate managed adapter blocks and manifests from the catalog and templates.

Reads VERSION, catalog/rules.yaml, and templates/agent-block.md, and writes
every generated artifact listed in v1-design-doc.md §6.1.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from lib import REPO_ROOT, count_tokens, read_version, write_manifest_version

BLOCK_BEGIN = "<!-- taorc:begin v{version} -->"
BLOCK_END = "<!-- taorc:end -->"
AGENT_BLOCK_TOKEN_BUDGET = 700

CURSOR_FRONTMATTER = """---
description: Write, comment, and review code so the next reader understands it in the least time.
alwaysApply: true
---

"""

COPILOT_INSTRUCTIONS_FRONTMATTER = """---
applyTo: "**/*"
---

"""

# (target path relative to repo root, frontmatter to seed a new file with, or
# None for a plain managed block). See v1-design-doc.md §6.1's output table.
ADAPTER_TARGETS: list[tuple[str, str | None]] = [
    ("AGENTS.md", None),
    ("CLAUDE.md", None),
    ("GEMINI.md", None),
    (".cursor/rules/readable-code.mdc", CURSOR_FRONTMATTER),
    (".github/copilot-instructions.md", None),
    (".github/instructions/readable-code.instructions.md", COPILOT_INSTRUCTIONS_FRONTMATTER),
    (".clinerules/readable-code.md", None),
    (".windsurf/rules/readable-code.md", None),
]

# Manifest files whose "version" field must track VERSION.
MANIFEST_TARGETS: list[str] = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    "gemini-extension.json",
]

# A line in each installer that records the version it was built for, so an
# installer can refuse a default download of a different version (#42). Each
# must appear exactly once in its file.
INSTALLER_VERSION_LINES: list[tuple[str, str]] = [
    ("scripts/install.sh", 'INSTALLER_VERSION="{version}"'),
    ("scripts/install.ps1", '$InstallerVersion = "{version}"'),
]

# The repo's own dogfooding copy of the skill for harnesses that only look
# under .github/skills/ (Copilot). A copy, never a symlink — see
# v1-design-doc.md §14.2 for why a Windows checkout without symlink support
# would silently turn this into a text file containing a path.
GITHUB_SKILLS_COPY = ("skills/readable-code", ".github/skills/readable-code")


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


def installer_version_pattern(line_template: str) -> re.Pattern[str]:
    """A pattern matching line_template as a whole line, with the version as
    group 1. The version may be empty."""
    escaped = re.escape(line_template).replace(r"\{version\}", r'([^"]*)')
    return re.compile(rf"^{escaped}$", re.MULTILINE)


def write_installer_version(path: Path, line_template: str, version: str) -> None:
    """Rewrite the version line in the installer at path.

    Raises ValueError, leaving the file unchanged, unless the line appears
    exactly once.
    """
    text = path.read_text(encoding="utf-8")
    pattern = installer_version_pattern(line_template)
    updated, line_count = pattern.subn(lambda _: line_template.format(version=version), text)
    if line_count != 1:
        raise ValueError(
            f"{path}: expected exactly one line matching {line_template!r}, found {line_count}"
        )
    path.write_text(updated, encoding="utf-8")


def sync_github_skills_copy() -> None:
    source_dir = REPO_ROOT / GITHUB_SKILLS_COPY[0]
    dest_dir = REPO_ROOT / GITHUB_SKILLS_COPY[1]
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(
        source_dir,
        dest_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


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

    for relative_path, frontmatter in ADAPTER_TARGETS:
        try:
            apply_managed_block(REPO_ROOT / relative_path, block, frontmatter)
        except (ValueError, OSError) as err:
            print(f"error: {err}", file=sys.stderr)
            return 1
        print(f"Updated {relative_path}")

    for relative_path in MANIFEST_TARGETS:
        try:
            write_manifest_version(REPO_ROOT / relative_path, version)
        except (json.JSONDecodeError, OSError) as err:
            print(f"error: {relative_path}: {err}", file=sys.stderr)
            return 1
        print(f"Synced version in {relative_path}")

    for relative_path, line_template in INSTALLER_VERSION_LINES:
        try:
            write_installer_version(REPO_ROOT / relative_path, line_template, version)
        except (ValueError, OSError) as err:
            print(f"error: {err}", file=sys.stderr)
            return 1
        print(f"Synced version in {relative_path}")

    try:
        sync_github_skills_copy()
    except OSError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(f"Synced {GITHUB_SKILLS_COPY[1]} from {GITHUB_SKILLS_COPY[0]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
