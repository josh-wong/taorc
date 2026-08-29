#!/usr/bin/env python3
"""Generation runner for the eval matrix (design doc §10.1, PRD R7.1/R7.3).

Runs every scenario under evals/scenarios/ in both conditions (baseline,
skill) against every model in the matrix, and writes each raw completion to
evals/results/<run>/raw/<scenario>/<model>/<condition>.{code_ext,txt}
alongside a metadata.json recording the model, sampler settings, and
timestamp -- so a published RESULTS.md can point at exactly what produced
each number (R7.4).

    python evals/run_bench.py --out evals/results/2026-08-28
    python evals/run_bench.py --out evals/results/2026-08-28 --models claude
    python evals/run_bench.py --out evals/results/2026-08-28 --dry-run

Each model slot needs its own API key set (see evals/evallib/models.py's
MODEL_MATRIX for which env var). A model with no key set is skipped with a
warning rather than failing the whole run, so a partial matrix is still
usable while keys are being gathered.

Re-running against a directory that already holds completions is safe: a
cell with a non-empty completion file is kept, not regenerated, so an
interrupted paid run resumes by just being re-invoked (pass --force to
regenerate). A cell whose generation failed leaves a <condition>.error.json
behind -- a durable record that score.py surfaces -- and is retried on the
next run; a --force regen that fails drops the previous completion first,
so a cell is never both scored and reported as failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evallib.models import (
    DEFAULT_SAMPLER,
    MODEL_MATRIX,
    ModelCallError,
    applied_sampler,
    generate,
)
from evallib.scenarios import Scenario, build_user_prompt, load_all_scenarios
from evallib.skill_artifacts import system_prompt_for

CONDITIONS = ["baseline", "skill"]


def output_extension(scenario: Scenario) -> str:
    return Path(scenario.output_file).suffix or ".txt"


def run_one(
    scenario: Scenario,
    model_slot: str,
    condition: str,
    out_dir: Path,
    dry_run: bool,
    force: bool,
) -> None:
    spec = next((m for m in MODEL_MATRIX if m.slot == model_slot), None)
    if spec is None:
        raise ValueError(f"no model in MODEL_MATRIX with slot {model_slot!r}")

    system_prompt = system_prompt_for(condition, spec.skill_artifact)
    user_prompt = build_user_prompt(scenario)

    if dry_run:
        artifact_label = spec.skill_artifact if condition == "skill" else "baseline"
        print(f"[dry-run] {scenario.id} / {model_slot} / {condition}")
        print(f"  system prompt: {len(system_prompt)} chars ({artifact_label})")
        print(f"  user prompt: {len(user_prompt)} chars")
        return

    target_dir = out_dir / "raw" / scenario.id / model_slot
    target_dir.mkdir(parents=True, exist_ok=True)
    completion_path = target_dir / f"{condition}{output_extension(scenario)}"
    metadata_path = target_dir / f"{condition}.meta.json"
    error_path = target_dir / f"{condition}.error.json"

    already_done = completion_path.exists() and completion_path.stat().st_size > 0
    if already_done and not force:
        print(
            f"  KEPT {scenario.id} / {model_slot} / {condition} -- already generated "
            "(pass --force to regenerate)"
        )
        return

    try:
        completion = generate(spec, system_prompt, user_prompt, DEFAULT_SAMPLER)
    except ModelCallError as error:
        # A forced regen that fails must not leave the old completion on
        # disk: the next non-force run would score that stale file while
        # score.py also lists this cell as a generation failure, so the
        # same cell reads as both scored and failed. Drop it and let the
        # error.json be the whole record until a retry succeeds.
        completion_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        error_path.write_text(
            json.dumps(
                {
                    "scenario_id": scenario.id,
                    "model_slot": model_slot,
                    "condition": condition,
                    "error": str(error),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  SKIPPED {scenario.id} / {model_slot} / {condition}: {error}", file=sys.stderr)
        return

    completion_path.write_text(completion, encoding="utf-8")
    error_path.unlink(missing_ok=True)  # a prior failure that has since succeeded
    metadata_path.write_text(
        json.dumps(
            {
                "scenario_id": scenario.id,
                "model_slot": model_slot,
                "model_id": spec.model_id,
                "provider": spec.provider,
                "condition": condition,
                "skill_artifact": spec.skill_artifact if condition == "skill" else None,
                "sampler": applied_sampler(spec, DEFAULT_SAMPLER),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  wrote {completion_path.relative_to(out_dir)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out", required=True, help="output directory, e.g. evals/results/2026-08-28"
    )
    parser.add_argument(
        "--models",
        default=",".join(m.slot for m in MODEL_MATRIX),
        help="comma-separated model slots to run (default: all)",
    )
    parser.add_argument(
        "--scenarios",
        default="all",
        help="comma-separated scenario ids to run (default: all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print what would run, call nothing")
    parser.add_argument(
        "--force",
        action="store_true",
        help="regenerate cells that already have a completion (default: keep them, so an "
        "interrupted run resumes without re-billing finished work)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    model_slots = args.models.split(",")
    known_slots = {m.slot for m in MODEL_MATRIX}
    unknown = set(model_slots) - known_slots
    if unknown:
        parser.error(
            f"unknown model slot(s): {', '.join(sorted(unknown))}. "
            f"Known: {', '.join(sorted(known_slots))}"
        )

    all_scenarios = load_all_scenarios()
    if args.scenarios != "all":
        wanted_ids = set(args.scenarios.split(","))
        all_scenarios = [s for s in all_scenarios if s.id in wanted_ids]
        missing = wanted_ids - {s.id for s in all_scenarios}
        if missing:
            parser.error(f"unknown scenario id(s): {', '.join(sorted(missing))}")

    for scenario in all_scenarios:
        print(f"{scenario.id} ({scenario.title})")
        for model_slot in model_slots:
            for condition in CONDITIONS:
                run_one(scenario, model_slot, condition, out_dir, args.dry_run, args.force)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
