#!/usr/bin/env python3
"""LLM-judge scoring track (design doc §10.2, PRD M2).

For every scenario/model pair, asks a judge model to blindly compare the
baseline and skill-enabled completions on one question -- "which would take
a new reader less time to understand" -- with left/right order randomized
so position can't leak which condition is which, plus a 1-5 rubric per
catalog category (N/C/F/S/T). Every raw judgment is written to
evals/results/<run>/judgments/ so a published number can be traced back to
the exact prompt and response that produced it (R7.4).

The judge model is never the same model that generated the pair (§10.2), to
reduce self-preference bias -- see judge_model_for() below.

    python evals/judge.py --run evals/results/2026-08-28
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS_ROOT))
from evallib.models import (  # noqa: E402
    DEFAULT_SAMPLER,
    MODEL_MATRIX,
    ModelCallError,
    ModelSpec,
    generate,
)
from evallib.scenarios import load_all_scenarios  # noqa: E402
from score import extract_code  # noqa: E402

JUDGE_SYSTEM_PROMPT = (
    "You are judging two versions of the same piece of code for one thing "
    "only: which would take a new reader less time to understand. Ignore "
    "correctness bugs unless they'd confuse a reader; ignore your own style "
    "preferences. Respond with a single JSON object and nothing else."
)

RUBRIC_CATEGORIES = {
    "N": "naming",
    "C": "comments",
    "F": "control flow and structure",
    "S": "structure and decomposition",
    "T": "test quality (if tests are present, otherwise omit)",
}


def judge_model_for(generation_model_slot: str) -> ModelSpec:
    """Picks uniformly at random among the other matrix slots, so self-
    preference bias doesn't concentrate on whichever model happens to be
    first in MODEL_MATRIX (design doc §10.2)."""
    candidates = [spec for spec in MODEL_MATRIX if spec.slot != generation_model_slot]
    if not candidates:
        raise ValueError("MODEL_MATRIX needs at least two models for judging")
    return random.choice(candidates)


def build_judge_prompt(task_title: str, version_a: str, version_b: str) -> str:
    rubric_lines = "\n".join(
        f'  "{letter}": <1-5 rubric score for {name}>' for letter, name in RUBRIC_CATEGORIES.items()
    )
    return f"""Task the code was written for: {task_title}

Version A:
```
{version_a}
```

Version B:
```
{version_b}
```

Return exactly this JSON shape:
{{
  "preference": "A" or "B",
  "rubric": {{
{rubric_lines}
  }}
}}"""


def parse_judge_response(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def judge_pair(
    scenario_title: str, baseline_code: str, skill_code: str, judge_spec: ModelSpec
) -> dict:
    """Randomizes which condition is labeled A vs. B so the judge can't infer
    the condition from position, then translates the raw A/B answer back to
    baseline/skill before returning it."""
    skill_is_a = random.random() < 0.5
    version_a = skill_code if skill_is_a else baseline_code
    version_b = baseline_code if skill_is_a else skill_code

    prompt = build_judge_prompt(scenario_title, version_a, version_b)
    raw_response = generate(judge_spec, JUDGE_SYSTEM_PROMPT, prompt, DEFAULT_SAMPLER)
    parsed = parse_judge_response(raw_response)

    preferred_condition = None
    if parsed and parsed.get("preference") in ("A", "B"):
        preferred_is_a = parsed["preference"] == "A"
        preferred_condition = "skill" if (preferred_is_a == skill_is_a) else "baseline"

    return {
        "judge_model_id": judge_spec.model_id,
        "skill_labeled": "A" if skill_is_a else "B",
        "raw_response": raw_response,
        "parsed": parsed,
        "preferred_condition": preferred_condition,
    }


def run_judging(run_dir: Path) -> dict:
    scenarios_by_id = {s.id: s for s in load_all_scenarios()}
    judgments_dir = run_dir / "judgments"
    judgments_dir.mkdir(parents=True, exist_ok=True)

    preference_counts = {"skill": 0, "baseline": 0, "no_verdict": 0}
    raw_dir = run_dir / "raw"

    for scenario_dir in sorted(raw_dir.iterdir()):
        scenario = scenarios_by_id.get(scenario_dir.name)
        if scenario is None:
            continue
        for model_dir in sorted(scenario_dir.iterdir()):
            baseline_path = model_dir / f"baseline{Path(scenario.output_file).suffix}"
            skill_path = model_dir / f"skill{Path(scenario.output_file).suffix}"
            if not (baseline_path.exists() and skill_path.exists()):
                continue

            baseline_code = extract_code(baseline_path.read_text(encoding="utf-8"))
            skill_code = extract_code(skill_path.read_text(encoding="utf-8"))
            judge_spec = judge_model_for(model_dir.name)

            try:
                judgment = judge_pair(scenario.title, baseline_code, skill_code, judge_spec)
            except ModelCallError as error:
                print(f"  SKIPPED {scenario.id} / {model_dir.name}: {error}", file=sys.stderr)
                continue

            verdict = judgment["preferred_condition"] or "no_verdict"
            preference_counts[verdict] += 1

            out_path = judgments_dir / f"{scenario.id}__{model_dir.name}.json"
            out_path.write_text(json.dumps(judgment, indent=2), encoding="utf-8")
            print(f"  {scenario.id} / {model_dir.name}: judge preferred {verdict}")

    return preference_counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run", required=True, help="a run directory produced by run_bench.py")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed for A/B order randomization (for a reproducible re-run)",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    run_dir = Path(args.run)
    if not (run_dir / "raw").is_dir():
        parser.error(f"{run_dir} has no raw/ directory -- run run_bench.py first")

    counts = run_judging(run_dir)
    decided = counts["skill"] + counts["baseline"]
    if decided:
        skill_preference_pct = round(counts["skill"] / decided * 100, 1)
        print(f"skill preferred in {skill_preference_pct}% of decided pairs (M2 target >= 70%)")
    print(f"counts: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
