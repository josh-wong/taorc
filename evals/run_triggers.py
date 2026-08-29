#!/usr/bin/env python3
"""Tier-1 trigger classifier for M4 (v1-design-doc.md §10.4, PRD R2.3).

For each of the 100 prompts in ``evals/triggers.json``, makes one cheap
classification call: given only the skill's ``name`` and ``description``
(resolved live from ``skills/readable-code/SKILL.md`` so it tracks what
ships), would the readable-code skill activate for this request? No agent
run, no tools -- that is what makes a full pass cost cents and finish in
under a minute, so the ``description`` can be iterated dozens of times
against it (§10.4). Tier 2, the 10-prompt end-to-end check in real Claude
Code, is a manual step recorded elsewhere, not this script.

    python evals/run_triggers.py --out evals/results/2026-08-29
    python evals/run_triggers.py --out evals/results/2026-08-29 --dry-run
    python evals/run_triggers.py --out evals/results/2026-08-29 --limit 5

Results land under ``<out>/triggers/`` following run_bench.py's layout: one
``raw/<id>.json`` per classified prompt, ``raw/<id>.error.json`` for a call
that failed, and ``triggers_summary.json`` with the activation rate on the
60 positives and the false-fire rate on the 40 negatives, scored against M4
(≥90% activation, ≤10% false fire).

``meets_m4`` is ``true`` only when the whole suite classified: a run with
any failed cell, or one narrowed by ``--limit``, reports ``meets_m4: false``
whatever the partial rates say and exits non-zero, so a shrunken sample
can't be mistaken for a passing verdict.

Like run_bench.py, this resumes: a prompt already classified on disk is
kept, not re-billed, so an interrupted pass finishes by being re-invoked
with the same ``--out`` (pass ``--force`` to re-classify). It needs one API
key -- the classifier model's (``--model``, default the ``claude`` slot). A
docs-only commit must not spend one: nothing runs this on every PR, only
changes to ``SKILL.md`` frontmatter or ``catalog/rules.yaml`` and on-demand
runs (see ``evals/README.md``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evallib.models import MODEL_MATRIX, ModelCallError, SamplerSettings, generate
from evallib.triggers import SkillIdentity, TriggerPrompt, load_suite, skill_identity

# A yes/no classification wants no sampling variance; temperature 0 gives a
# stable verdict across the reruns that iterating a description depends on.
# The token cap is deliberately generous, not tight: the verdict is one
# short JSON object, but a model that emits a sentence of reasoning before
# it would trip models._reject_if_truncated at a small cap, and a truncated
# call is a hard failure that re-fails identically on every rerun -- so the
# prompt would be permanently absent from the rates that gate M4. 1000
# tokens clears any reasonable preamble while still bounding a runaway reply.
CLASSIFIER_SAMPLER = SamplerSettings(temperature=0.0, top_p=1.0, max_tokens=1000)

CLASSIFIER_SYSTEM_PROMPT = (
    "You route user requests to agent skills. You are given one skill's "
    "name and description, then a user request. Decide only whether that "
    "skill should activate for that request. Judge against the description "
    "exactly as written -- do not give the skill the benefit of the doubt, "
    "and do not invent capabilities it does not claim. Reply with a single "
    'JSON object and nothing else: {"activate": true} or {"activate": false}.'
)

_JSON_OBJECT = re.compile(r"\{[^{}]*\}", re.DOTALL)

# Some model slots answer the boolean field with a stringified verdict
# ({"activate": "false"}) or a word ({"activate": "no"}). bool() on any
# non-empty string is True, so a bare bool() cast would score those as
# activations. Map the known spellings explicitly; anything else is an
# unparseable verdict, not a guess.
_ACTIVATION_WORDS = {
    "true": True,
    "yes": True,
    "activate": True,
    "false": False,
    "no": False,
    "skip": False,
}


def build_classifier_prompt(skill: SkillIdentity, request: str) -> str:
    return (
        f"Skill name: {skill.name}\n\n"
        f"Skill description:\n{skill.description}\n\n"
        f"User request:\n{request}\n\n"
        'Should this skill activate? Reply with {"activate": true} or {"activate": false}.'
    )


def parse_activation(response_text: str) -> bool:
    """The classifier's verdict as a bool. Raises ModelCallError on a
    response with no usable ``activate`` verdict rather than guessing -- an
    unparseable verdict is a failed cell, recorded and retried, not a silent
    false that would skew the false-fire rate."""
    for candidate in _JSON_OBJECT.findall(response_text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict) or "activate" not in parsed:
            continue
        verdict = _as_activation_bool(parsed["activate"])
        if verdict is not None:
            return verdict
    raise ModelCallError(
        f"classifier response has no usable 'activate' verdict: {response_text!r}"
    )


def _as_activation_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):  # {"activate": 1} / {"activate": 0}
        return value != 0
    if isinstance(value, str):
        return _ACTIVATION_WORDS.get(value.strip().lower())
    return None


def classify_one(
    prompt: TriggerPrompt,
    skill: SkillIdentity,
    model_slot: str,
    triggers_dir: Path,
    force: bool,
) -> dict | None:
    """Classifies one prompt and writes ``raw/<id>.json``, or returns the
    already-saved result on a resume. Returns None when the call failed (an
    ``raw/<id>.error.json`` is left behind, mirroring run_bench.py)."""
    spec = next((m for m in MODEL_MATRIX if m.slot == model_slot), None)
    if spec is None:
        raise ValueError(f"no model in MODEL_MATRIX with slot {model_slot!r}")

    raw_dir = triggers_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    result_path = raw_dir / f"{prompt.id}.json"
    error_path = raw_dir / f"{prompt.id}.error.json"

    if result_path.exists() and not force:
        saved = _load_saved_result(result_path)
        if saved is not None and _resumable(saved, skill, model_slot):
            print(f"  KEPT {prompt.id} -- already classified (pass --force to redo)")
            return saved
        if saved is not None:
            print(
                f"  STALE {prompt.id} -- re-classifying (skill description or "
                "--model changed since it was saved)"
            )

    system_prompt = CLASSIFIER_SYSTEM_PROMPT
    user_prompt = build_classifier_prompt(skill, prompt.prompt)
    try:
        response_text = generate(spec, system_prompt, user_prompt, CLASSIFIER_SAMPLER)
        activated = parse_activation(response_text)
    except ModelCallError as error:
        result_path.unlink(missing_ok=True)
        error_path.write_text(
            json.dumps(
                {
                    "prompt_id": prompt.id,
                    "model_slot": model_slot,
                    "error": str(error),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  FAILED {prompt.id}: {error}", file=sys.stderr)
        return None

    result = {
        "prompt_id": prompt.id,
        "label": prompt.label,
        "category": prompt.category,
        "prompt": prompt.prompt,
        "should_activate": prompt.should_activate,
        "activated": activated,
        "correct": activated == prompt.should_activate,
        "model_slot": model_slot,
        "model_id": spec.model_id,
        "skill_name": skill.name,
        "skill_description": skill.description,
        "raw_response": response_text,
        "classified_at": datetime.now(timezone.utc).isoformat(),
    }
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    error_path.unlink(missing_ok=True)
    verdict = "activate" if activated else "skip"
    mark = "ok" if result["correct"] else "MISS"
    print(f"  {prompt.id} [{prompt.label}] -> {verdict} ({mark})")
    return result


def _load_saved_result(path: Path) -> dict | None:
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return saved if isinstance(saved, dict) and "activated" in saved else None


def _resumable(saved: dict, skill: SkillIdentity, model_slot: str) -> bool:
    """A saved cell can be kept only if it was classified against the same
    skill description and the same model. evals/README.md says to rerun
    "whenever SKILL.md frontmatter changes" -- resuming across that edit
    would keep verdicts from the old description while the summary header
    reports the new one. A cell saved before this field existed has no
    recorded description and is re-classified."""
    return (
        saved.get("skill_description") == skill.description
        and saved.get("model_slot") == model_slot
    )


def summarize(
    results: list[dict],
    skill: SkillIdentity,
    model_slot: str,
    *,
    suite_fully_scored: bool,
) -> dict:
    positives = [r for r in results if r["should_activate"]]
    negatives = [r for r in results if not r["should_activate"]]
    activated_positives = [r for r in positives if r["activated"]]
    activated_negatives = [r for r in negatives if r["activated"]]

    activation_rate = _pct(len(activated_positives), len(positives))
    false_fire_rate = _pct(len(activated_negatives), len(negatives))

    false_fire_by_category: dict[str, dict] = {}
    for result in negatives:
        bucket = false_fire_by_category.setdefault(
            result["category"], {"total": 0, "false_fires": 0}
        )
        bucket["total"] += 1
        bucket["false_fires"] += 1 if result["activated"] else 0

    meets_activation = activation_rate is not None and activation_rate >= 90.0
    meets_false_fire = false_fire_rate is not None and false_fire_rate <= 10.0
    # A rate computed over a subset of the suite -- because cells failed to
    # classify, or --limit ran only the first N -- is not an M4 verdict. The
    # missing prompts could all be misses; reporting "meets M4" off what
    # happened to succeed is how a tuning decision gets made against an
    # instrument that measured half the suite.
    meets_m4 = suite_fully_scored and meets_activation and meets_false_fire

    return {
        "suite_fully_scored": suite_fully_scored,
        "classifier_model_slot": model_slot,
        "skill_name": skill.name,
        "skill_description": skill.description,
        "classifier_sampler": {
            "temperature": CLASSIFIER_SAMPLER.temperature,
            "top_p": CLASSIFIER_SAMPLER.top_p,
            "max_tokens": CLASSIFIER_SAMPLER.max_tokens,
        },
        "counts": {
            "positives_classified": len(positives),
            "negatives_classified": len(negatives),
        },
        "activation_rate_pct": activation_rate,
        "false_fire_rate_pct": false_fire_rate,
        "m4_targets": {"activation_rate_pct": ">=90", "false_fire_rate_pct": "<=10"},
        "meets_m4": bool(meets_m4),
        "false_fire_by_negative_category": false_fire_by_category,
        "positives_not_activated": sorted(
            r["prompt_id"] for r in positives if not r["activated"]
        ),
        "negatives_activated": sorted(
            r["prompt_id"] for r in negatives if r["activated"]
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _pct(part: int, whole: int) -> float | None:
    if whole == 0:
        return None
    return round(part * 100 / whole, 1)


def _require_api_key(model_slot: str) -> None:
    spec = next((m for m in MODEL_MATRIX if m.slot == model_slot), None)
    if spec is None:
        known = ", ".join(sorted(m.slot for m in MODEL_MATRIX))
        raise SystemExit(f"unknown --model {model_slot!r}. Known slots: {known}")
    if not os.environ.get(spec.api_key_env):
        raise SystemExit(
            f"--model {model_slot} needs {spec.api_key_env} set to classify "
            f"({spec.provider} model {spec.model_id!r}). Use --dry-run to check "
            "the suite and prompts without a key."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out", required=True, help="run directory, e.g. evals/results/2026-08-29"
    )
    parser.add_argument(
        "--model",
        default="claude",
        help="matrix slot to classify with (default: claude -- the skill's primary harness)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="classify only the first N prompts -- a cheap smoke test of the runner",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print what would be sent, call nothing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-classify prompts already on disk (default: keep them, so an "
        "interrupted pass resumes without re-billing)",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be a positive integer")

    suite = load_suite()
    skill = skill_identity()
    prompts = suite[: args.limit] if args.limit is not None else suite

    if args.dry_run:
        print(f"skill name: {skill.name}")
        print(f"skill description: {len(skill.description)} chars")
        print(f"classifier: {args.model} slot, sampler {CLASSIFIER_SAMPLER}")
        print(f"would classify {len(prompts)} of {len(suite)} prompts")
        example = build_classifier_prompt(skill, prompts[0].prompt)
        print(f"\n--- example call for {prompts[0].id} ---")
        print(f"system: {CLASSIFIER_SYSTEM_PROMPT}")
        print(f"user:\n{example}")
        return 0

    _require_api_key(args.model)

    triggers_dir = Path(args.out) / "triggers"
    results: list[dict] = []
    failed_prompt_ids: list[str] = []
    for prompt in prompts:
        result = classify_one(prompt, skill, args.model, triggers_dir, args.force)
        if result is None:
            failed_prompt_ids.append(prompt.id)
        else:
            results.append(result)

    ran_whole_suite = args.limit is None
    suite_fully_scored = ran_whole_suite and not failed_prompt_ids
    summary = summarize(
        results, skill, args.model, suite_fully_scored=suite_fully_scored
    )
    summary["classification_failures"] = len(failed_prompt_ids)
    summary["failed_prompt_ids"] = sorted(failed_prompt_ids)
    summary["limited_to_first_n"] = args.limit

    summary_path = triggers_dir / "triggers_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwrote {summary_path}")
    print(
        f"  activation rate (positives): {_fmt_pct(summary['activation_rate_pct'])} "
        "(M4 target >= 90%)"
    )
    print(
        f"  false-fire rate (negatives): {_fmt_pct(summary['false_fire_rate_pct'])} "
        "(M4 target <= 10%)"
    )
    print(f"  meets M4: {'yes' if summary['meets_m4'] else 'no'}")
    if not ran_whole_suite:
        print(
            f"  NOTE: --limit {args.limit} scored only the first {len(prompts)} "
            "prompts; this is a runner smoke test, not an M4 verdict."
        )
    if failed_prompt_ids:
        print(
            f"  WARNING: {len(failed_prompt_ids)} prompt(s) failed classification and "
            f"are absent from the rates above: {', '.join(sorted(failed_prompt_ids))} "
            "-- see raw/*.error.json, then rerun with the same --out to retry them.",
            file=sys.stderr,
        )
    # A partial pass is a non-zero exit, not a green run with a stderr line:
    # meets_m4 is already false, and an on-demand or CI caller should see the
    # failure rather than trust a summary written over a shrunken sample.
    return 1 if failed_prompt_ids else 0


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
