#!/usr/bin/env python3
"""Local Ollama smoke test for system-prompt-mini.md (design doc §14.3).

This is deliberately NOT part of the published cross-model matrix in
run_bench.py. Its only job is an informal check that the ~150-token mini
prompt still nudges a small local model's output, on a machine anyone can
run it on -- "useful signal, not a metric." Never fold its numbers into
RESULTS.md or the M1-M3 tables; a local build's quantization isn't
reproducible the way the hosted matrix's pinned model IDs are (§14.3).

    ollama pull qwen3.5:4b-mlx    # or whatever local model you have
    python evals/run_smoke_ollama.py --model qwen3.5:4b-mlx \\
        --out evals/results/2026-08-28/smoke-ollama
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS_ROOT))
from evallib.models import DEFAULT_SAMPLER, ModelCallError, call_ollama  # noqa: E402
from evallib.scenarios import build_user_prompt, load_all_scenarios  # noqa: E402
from evallib.skill_artifacts import BASELINE_SYSTEM_PROMPT  # noqa: E402

MINI_PROMPT_PATH = EVALS_ROOT.parent / "prompts" / "system-prompt-mini.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--model", required=True, help="local Ollama model tag, e.g. qwen3.5:4b-mlx"
    )
    parser.add_argument("--out", required=True, help="output directory for raw completions")
    parser.add_argument(
        "--scenarios", default="all", help="comma-separated scenario ids to run (default: all)"
    )
    args = parser.parse_args()

    mini_prompt = MINI_PROMPT_PATH.read_text(encoding="utf-8")
    scenarios = load_all_scenarios()
    if args.scenarios != "all":
        wanted_ids = set(args.scenarios.split(","))
        scenarios = [s for s in scenarios if s.id in wanted_ids]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README.md").write_text(
        "Unpublished smoke test of prompts/system-prompt-mini.md against a "
        f"local Ollama model ({args.model}). Informal signal only, per "
        "design doc §14.3 -- do not cite these numbers in RESULTS.md.\n",
        encoding="utf-8",
    )

    for scenario in scenarios:
        user_prompt = build_user_prompt(scenario)
        suffix = Path(scenario.output_file).suffix
        scenario_dir = out_dir / scenario.id
        scenario_dir.mkdir(exist_ok=True)
        conditions = [("baseline", BASELINE_SYSTEM_PROMPT), ("skill", mini_prompt)]
        for condition, system_prompt in conditions:
            try:
                completion = call_ollama(args.model, system_prompt, user_prompt, DEFAULT_SAMPLER)
            except ModelCallError as error:
                print(f"  SKIPPED {scenario.id} / {condition}: {error}", file=sys.stderr)
                continue
            completion_path = scenario_dir / f"{condition}{suffix}"
            completion_path.write_text(completion, encoding="utf-8")
            print(f"  wrote {completion_path.relative_to(out_dir)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
