"""Loads and structurally checks the M4 trigger suite (design doc §10.4).

The suite in ``evals/triggers.json`` is the measurement instrument for M4
(PRD R2.3): 100 prompts, 60 the readable-code skill should activate on and
40 it must not. The design doc fixes the shape -- 60 positive / 40 negative,
with the 40 negatives split 10 prose-readability / 5 code-explanation / 25
other -- because that split is what lets n=100 resolve the ≥90% positive and
≤10% negative targets to roughly ±7pp and 2.5pp. A suite that has drifted
off those counts can no longer resolve either target, so ``load_suite``
refuses one that has rather than letting ``run_triggers.py`` score M4 from a
sample that cannot support the claim -- which would silently invalidate the
description tuning that depends on it (issue #9).

This module also resolves the skill's ``name`` and ``description`` from
``SKILL.md``'s frontmatter (``skill_identity``), so the classifier is always
handed exactly what ships, not a copy that can go stale.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

EVALS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EVALS_ROOT.parent
TRIGGERS_PATH = EVALS_ROOT / "triggers.json"
SKILL_MD_PATH = REPO_ROOT / "skills" / "readable-code" / "SKILL.md"

TOTAL_PROMPTS = 100
POSITIVE_COUNT = 60
NEGATIVE_COUNT = 40

# The negative split the design doc commits to in §10.4. Enforced exactly:
# the prose-readability slots in particular are the ones that decide whether
# M4's ≤10% target means anything, so "close enough" is not close enough.
NEGATIVE_CATEGORY_COUNTS = {
    "prose-readability": 10,
    "code-explanation": 5,
    "other": 25,
}

# The code-writing shapes SKILL.md claims (issue #20 / R2.3). Exact per-shape
# counts are left free so the suite can be rebalanced during tuning, but
# every shape must keep enough prompts to be a real probe rather than a
# token gesture.
POSITIVE_CATEGORIES = frozenset(
    {
        "implement",
        "refactor",
        "comment",
        "review-readability",
        "de-slop",
        "naming",
        "restructure-nesting",
    }
)
MIN_PROMPTS_PER_POSITIVE_CATEGORY = 3


class TriggerSuiteError(ValueError):
    """The trigger suite on disk is not a valid M4 instrument."""


@dataclass(frozen=True)
class TriggerPrompt:
    id: str
    label: str  # "positive" | "negative"
    category: str
    prompt: str

    @property
    def should_activate(self) -> bool:
        return self.label == "positive"


@dataclass(frozen=True)
class SkillIdentity:
    name: str
    description: str


def _fail(problems: list[str]) -> None:
    if problems:
        raise TriggerSuiteError(
            "evals/triggers.json is not a valid M4 suite:\n  - "
            + "\n  - ".join(problems)
        )


def _parse_prompts(suite_json: object) -> list[TriggerPrompt]:
    if not isinstance(suite_json, dict) or not isinstance(suite_json.get("prompts"), list):
        raise TriggerSuiteError("evals/triggers.json: top level needs a 'prompts' array")

    prompts: list[TriggerPrompt] = []
    problems: list[str] = []
    for index, entry in enumerate(suite_json["prompts"]):
        where = f"prompt #{index + 1}"
        if not isinstance(entry, dict):
            problems.append(f"{where}: not an object")
            continue
        prompt_id = entry.get("id")
        label = entry.get("label")
        category = entry.get("category")
        text = entry.get("prompt")
        if not isinstance(prompt_id, str) or not prompt_id:
            problems.append(f"{where}: missing 'id'")
            continue
        if label not in ("positive", "negative"):
            problems.append(f"{prompt_id}: label must be 'positive' or 'negative'")
        if not isinstance(category, str) or not category:
            problems.append(f"{prompt_id}: missing 'category'")
        if not isinstance(text, str) or not text.strip():
            problems.append(f"{prompt_id}: empty prompt text")
        prompts.append(
            TriggerPrompt(
                id=prompt_id,
                label=label if isinstance(label, str) else "",
                category=category if isinstance(category, str) else "",
                prompt=text.strip() if isinstance(text, str) else "",
            )
        )
    _fail(problems)
    return prompts


def _check_distribution(prompts: list[TriggerPrompt]) -> None:
    problems: list[str] = []

    ids = [p.id for p in prompts]
    duplicate_ids = sorted({i for i in ids if ids.count(i) > 1})
    if duplicate_ids:
        problems.append(f"duplicate ids: {', '.join(duplicate_ids)}")

    seen_text: dict[str, str] = {}
    for prompt in prompts:
        key = prompt.prompt.casefold()
        if key in seen_text:
            problems.append(f"{prompt.id}: prompt text duplicates {seen_text[key]}")
        else:
            seen_text[key] = prompt.id

    if len(prompts) != TOTAL_PROMPTS:
        problems.append(f"has {len(prompts)} prompts, needs {TOTAL_PROMPTS}")

    positives = [p for p in prompts if p.label == "positive"]
    negatives = [p for p in prompts if p.label == "negative"]
    if len(positives) != POSITIVE_COUNT:
        problems.append(f"has {len(positives)} positives, needs {POSITIVE_COUNT}")
    if len(negatives) != NEGATIVE_COUNT:
        problems.append(f"has {len(negatives)} negatives, needs {NEGATIVE_COUNT}")

    for category, required in NEGATIVE_CATEGORY_COUNTS.items():
        actual = sum(1 for p in negatives if p.category == category)
        if actual != required:
            problems.append(
                f"negative category '{category}': has {actual}, needs exactly {required} (§10.4)"
            )
    unknown_negative = sorted(
        {p.category for p in negatives} - set(NEGATIVE_CATEGORY_COUNTS)
    )
    if unknown_negative:
        problems.append(f"unknown negative categories: {', '.join(unknown_negative)}")

    unknown_positive = sorted({p.category for p in positives} - POSITIVE_CATEGORIES)
    if unknown_positive:
        problems.append(f"unknown positive categories: {', '.join(unknown_positive)}")
    for category in sorted(POSITIVE_CATEGORIES):
        actual = sum(1 for p in positives if p.category == category)
        if actual < MIN_PROMPTS_PER_POSITIVE_CATEGORY:
            problems.append(
                f"positive shape '{category}': has {actual}, needs at least "
                f"{MIN_PROMPTS_PER_POSITIVE_CATEGORY} to be a real probe"
            )

    _fail(problems)


def load_suite(path: Path = TRIGGERS_PATH) -> list[TriggerPrompt]:
    """The 100 trigger prompts, or ``TriggerSuiteError`` if the file on disk
    has drifted from the shape §10.4 requires."""
    if not path.exists():
        raise TriggerSuiteError(f"{path} does not exist")
    try:
        suite_json = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise TriggerSuiteError(f"{path}: not valid JSON ({error})") from error
    prompts = _parse_prompts(suite_json)
    _check_distribution(prompts)
    return prompts


def frontmatter_block(text: str) -> str | None:
    """The raw YAML inside a leading ``---\\n`` ... ``\\n---\\n`` fence, or None
    if the text has no well-formed one. scripts/validate.py slices SKILL.md's
    frontmatter the same way for its own checks and imports this so the fence
    offsets live in one place; each caller parses and reports on the result in
    its own style (that one returns None where this raises)."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end == -1:
        return None
    return text[4 : end + 1]


def _parse_frontmatter(text: str) -> dict:
    block = frontmatter_block(text)
    if block is None:
        raise TriggerSuiteError(f"{SKILL_MD_PATH}: no well-formed YAML frontmatter")
    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError as error:
        raise TriggerSuiteError(
            f"{SKILL_MD_PATH}: frontmatter is not valid YAML ({error})"
        ) from error
    if not isinstance(parsed, dict):
        raise TriggerSuiteError(f"{SKILL_MD_PATH}: frontmatter is not a mapping")
    return parsed


def skill_identity(path: Path = SKILL_MD_PATH) -> SkillIdentity:
    """The skill ``name`` and ``description`` exactly as they ship in
    ``SKILL.md`` -- the only two fields the tier-1 classifier is allowed to
    see (§10.4). A folded (``>``) description arrives with its newlines
    already collapsed to spaces by the YAML parser; this only trims the
    trailing one."""
    frontmatter = _parse_frontmatter(path.read_text(encoding="utf-8"))
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not isinstance(name, str) or not name.strip():
        raise TriggerSuiteError(f"{path}: frontmatter has no 'name'")
    if not isinstance(description, str) or not description.strip():
        raise TriggerSuiteError(f"{path}: frontmatter has no 'description'")
    return SkillIdentity(name=name.strip(), description=description.strip())
