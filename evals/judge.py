#!/usr/bin/env python3
"""LLM-judge scoring track (design doc §10.2, PRD M2).

For every scenario/model pair, asks a judge model to blindly compare the
baseline and skill-enabled completions on one question -- "which would take
a new reader less time to understand" -- with left/right order randomized
so position can't leak which condition is which, plus a 1-5 score for each
version on every catalog category (N/C/F/S/T). Every raw judgment is written
to evals/results/<run>/judgments/ so a published number can be traced back
to the exact prompt and response that produced it (R7.4); the per-category
scores are aggregated into a skill-vs-baseline delta in judge_summary.json.

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
from run_bench import output_extension  # noqa: E402
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
        f'    "{letter}": <1-5 score for {name}>' for letter, name in RUBRIC_CATEGORIES.items()
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

Return exactly this JSON shape. Score each version 1-5 per category on its
own (not relative to the other); omit "T" for a version with no tests:
{{
  "preference": "A" or "B",
  "rubric_a": {{
{rubric_lines}
  }},
  "rubric_b": {{
{rubric_lines}
  }}
}}"""


def clean_rubric(rubric: object) -> dict[str, int]:
    """Keeps only the N/C/F/S/T keys carrying an in-range integer 1-5, so a
    judge that invents a category or answers "N/A" for one can't poison the
    per-category means."""
    if not isinstance(rubric, dict):
        return {}
    scores: dict[str, int] = {}
    for letter in RUBRIC_CATEGORIES:
        score = rubric.get(letter)
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        if 1 <= score <= 5:
            scores[letter] = int(score)
    return scores


def parse_judge_response(text: str) -> dict | None:
    """A greedy `\\{.*\\}` regex would span from a stray brace in the judge's
    own reasoning prose to the response's final `}`, producing invalid JSON
    and silently losing a real verdict. Instead, try decoding a JSON object
    starting at each `{` in turn and keep the first one that actually has
    the "preference" key the answer is supposed to carry."""
    decoder = json.JSONDecoder()
    for opening_brace in re.finditer(r"\{", text):
        try:
            parsed, _ = decoder.raw_decode(text, opening_brace.start())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "preference" in parsed:
            return parsed
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
    rubric_by_condition = None
    if parsed:
        if parsed.get("preference") in ("A", "B"):
            preferred_is_a = parsed["preference"] == "A"
            preferred_condition = "skill" if (preferred_is_a == skill_is_a) else "baseline"
        rubric_a = clean_rubric(parsed.get("rubric_a"))
        rubric_b = clean_rubric(parsed.get("rubric_b"))
        if rubric_a or rubric_b:
            rubric_by_condition = {
                "skill": rubric_a if skill_is_a else rubric_b,
                "baseline": rubric_b if skill_is_a else rubric_a,
            }

    return {
        "judge_model_id": judge_spec.model_id,
        "skill_labeled": "A" if skill_is_a else "B",
        "raw_response": raw_response,
        "parsed": parsed,
        "preferred_condition": preferred_condition,
        "rubric_by_condition": rubric_by_condition,
    }


def accumulate_rubric(
    rubric_samples: dict[str, dict[str, list[int]]], rubric_by_condition: dict | None
) -> None:
    if not rubric_by_condition:
        return
    for condition in ("skill", "baseline"):
        for letter, score in rubric_by_condition.get(condition, {}).items():
            rubric_samples[condition][letter].append(score)


def summarize_rubric(rubric_samples: dict[str, dict[str, list[int]]]) -> dict:
    """Mean 1-5 score per category for each condition and the skill-minus-
    baseline delta -- the per-category signal design doc §10.2 asks for, so
    a run says which axis the skill moves rather than only the overall
    preference. A category is reported only where both conditions have at
    least one score, so the delta always compares like with like."""
    summary = {}
    for letter, name in RUBRIC_CATEGORIES.items():
        skill_scores = rubric_samples["skill"][letter]
        baseline_scores = rubric_samples["baseline"][letter]
        if not skill_scores or not baseline_scores:
            continue
        skill_mean = sum(skill_scores) / len(skill_scores)
        baseline_mean = sum(baseline_scores) / len(baseline_scores)
        summary[letter] = {
            "category": name,
            "skill_mean": round(skill_mean, 2),
            "baseline_mean": round(baseline_mean, 2),
            "delta": round(skill_mean - baseline_mean, 2),
            "pairs_scored": min(len(skill_scores), len(baseline_scores)),
        }
    return summary


def run_judging(run_dir: Path) -> dict:
    scenarios_by_id = {s.id: s for s in load_all_scenarios()}
    judgments_dir = run_dir / "judgments"
    judgments_dir.mkdir(parents=True, exist_ok=True)

    preference_counts = {"skill": 0, "baseline": 0, "no_verdict": 0}
    rubric_samples: dict[str, dict[str, list[int]]] = {
        "skill": {letter: [] for letter in RUBRIC_CATEGORIES},
        "baseline": {letter: [] for letter in RUBRIC_CATEGORIES},
    }
    raw_dir = run_dir / "raw"

    for scenario_dir in sorted(raw_dir.iterdir()):
        scenario = scenarios_by_id.get(scenario_dir.name)
        if scenario is None:
            continue
        for model_dir in sorted(scenario_dir.iterdir()):
            completion_ext = output_extension(scenario)
            baseline_path = model_dir / f"baseline{completion_ext}"
            skill_path = model_dir / f"skill{completion_ext}"
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
            accumulate_rubric(rubric_samples, judgment["rubric_by_condition"])

            out_path = judgments_dir / f"{scenario.id}__{model_dir.name}.json"
            out_path.write_text(json.dumps(judgment, indent=2), encoding="utf-8")
            print(f"  {scenario.id} / {model_dir.name}: judge preferred {verdict}")

    return {
        "preference_counts": preference_counts,
        "rubric_means": summarize_rubric(rubric_samples),
    }


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

    outcome = run_judging(run_dir)
    counts = outcome["preference_counts"]
    rubric_means = outcome["rubric_means"]

    summary_path = run_dir / "judge_summary.json"
    summary_path.write_text(json.dumps(outcome, indent=2), encoding="utf-8")
    print(f"wrote {summary_path}")

    decided = counts["skill"] + counts["baseline"]
    if decided:
        skill_preference_pct = round(counts["skill"] / decided * 100, 1)
        print(f"skill preferred in {skill_preference_pct}% of decided pairs (M2 target >= 70%)")
    print(f"counts: {counts}")
    for letter, means in rubric_means.items():
        print(
            f"  rubric {letter} ({means['category']}): skill {means['skill_mean']} vs "
            f"baseline {means['baseline_mean']} (delta {means['delta']:+g}, "
            f"n={means['pairs_scored']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
