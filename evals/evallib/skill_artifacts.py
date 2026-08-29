"""Resolves the system prompt for each eval condition.

A raw completion call has no file access and no tool runtime, so it can't
reproduce the operating loop's "read local context" or "run taorc-lint"
steps (SKILL.md §Operating loop) -- those need an actual agent session.
What this harness measures instead is the narrower, cheaper question the
design doc's cost estimate implies (§10.1): does injecting the catalog as a
system prompt change what the model writes, in the direction the catalog
intends? A full agentic-session comparison is a reasonable follow-up if this
signal and the real skill runtime ever turn out to diverge.
"""

from __future__ import annotations

import sys
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EVALS_ROOT.parent

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from build import render_managed_block  # noqa: E402
from lib import read_version  # noqa: E402

BASELINE_SYSTEM_PROMPT = (
    "You are a careful software engineer. Complete the task exactly as "
    "described, using your own best judgment for anything it doesn't "
    "specify."
)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def skill_system_prompt(skill_artifact: str) -> str:
    if skill_artifact == "skill_md":
        return _read("skills/readable-code/SKILL.md")
    if skill_artifact == "agent_block":
        template = _read("templates/agent-block.md")
        return render_managed_block(read_version(), template)
    if skill_artifact == "system_prompt":
        return _read("prompts/system-prompt.md")
    raise ValueError(f"unknown skill_artifact: {skill_artifact!r}")


def system_prompt_for(condition: str, skill_artifact: str) -> str:
    if condition == "baseline":
        return BASELINE_SYSTEM_PROMPT
    if condition == "skill":
        return skill_system_prompt(skill_artifact)
    raise ValueError(f"unknown condition: {condition!r}")
