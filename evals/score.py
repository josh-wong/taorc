#!/usr/bin/env python3
"""Automated scoring track (design doc §10.2, PRD M1/M3).

Reads the raw completions written by run_bench.py and computes, per
scenario/model/condition:

  - taorc-lint findings per 100 LOC                        -> M1
  - comment-to-code ratio
  - mean and max nesting depth
  - empty-word identifier count (N1's own word list)
  - diff size vs. the starter file, on scenarios that measure it -> M3

Nothing here calls a model or costs money; it is pure text analysis over
files run_bench.py already wrote, which is what "deterministic, free"
(§10.2) means for this track.

    python evals/score.py --run evals/results/2026-08-28
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import subprocess
import sys
import tokenize
from io import StringIO
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
LINT_SCRIPT = REPO_ROOT / "skills" / "readable-code" / "scripts" / "taorc_lint.py"

sys.path.insert(0, str(EVALS_ROOT))
from evallib.scenarios import Scenario, load_all_scenarios  # noqa: E402

sys.path.insert(0, str(LINT_SCRIPT.parent))
from taorc_lint import short_python_function_ranges  # noqa: E402

CODE_FENCE_PATTERN = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)

# Sourced from the N1 ast-grep rule itself (rather than a second hardcoded
# list here) so this metric can't silently drift from what the linter
# already treats as an empty word.
_LINT_RULES_ROOT = REPO_ROOT / "skills" / "readable-code" / "scripts" / "rules"
_N1_RULE_PATH = _LINT_RULES_ROOT / "python" / "taorc-n1-empty-word-identifier.yml"


def load_empty_word_pattern() -> re.Pattern:
    text = _N1_RULE_PATH.read_text(encoding="utf-8")
    match = re.search(r"regex:\s*'\^\(([^)]+)\)\$'", text)
    if not match:
        raise ValueError(f"could not find N1's word-list regex in {_N1_RULE_PATH}")
    return re.compile(rf"\b({match.group(1)})\b")


EMPTY_WORD_PATTERN = load_empty_word_pattern()


def extract_code(completion_text: str) -> str:
    """A raw completion is often prose plus one or more fenced code blocks.
    Score the largest fenced block; if the model returned bare code with no
    fence at all, score the whole response."""
    blocks = CODE_FENCE_PATTERN.findall(completion_text)
    if not blocks:
        return completion_text
    return max(blocks, key=len)


def count_loc(code: str) -> int:
    return sum(1 for line in code.splitlines() if line.strip())


def comment_ratio(code: str) -> float | None:
    try:
        tokens = list(tokenize.generate_tokens(StringIO(code).readline))
    except (tokenize.TokenizeError, SyntaxError, IndentationError):
        return None
    comment_lines = sum(1 for tok in tokens if tok.type == tokenize.COMMENT)
    code_lines = count_loc(code)
    if code_lines == 0:
        return None
    return round(comment_lines / code_lines, 3)


def nesting_depth(code: str) -> tuple[int, float] | tuple[None, None]:
    """Max and mean nesting depth across the compound statements in the
    module (if/for/while/try/with/function/class bodies), counted by AST
    depth rather than indentation columns so formatting can't skew it."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None, None

    depths: list[int] = []
    compound_types = (
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.With,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
    )

    def walk(node: ast.AST, depth: int) -> None:
        is_compound = isinstance(node, compound_types)
        next_depth = depth + 1 if is_compound else depth
        if is_compound:
            depths.append(next_depth)
        for child in ast.iter_child_nodes(node):
            walk(child, next_depth)

    walk(tree, 0)
    if not depths:
        return 0, 0.0
    return max(depths), round(sum(depths) / len(depths), 2)


def _assignment_target_names(target: ast.AST) -> list[tuple[str, int]]:
    """Matches the ast-grep rule's "left" field of an assignment exactly as
    ast-grep resolves it: a bare name target only. Verified directly
    against ast-grep that a tuple/list-unpacking target (`first, data =
    f()`) is NOT flagged -- the unpacked names sit inside a pattern node,
    not directly in the assignment's "left" field -- and neither is a
    for-loop target, an except-as name, or an attribute access."""
    if isinstance(target, ast.Name):
        return [(target.id, target.lineno)]
    return []


def _parameter_names(args: ast.arguments) -> list[tuple[str, int]]:
    positional = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    parameters = list(positional)
    if args.vararg:
        parameters.append(args.vararg)
    if args.kwarg:
        parameters.append(args.kwarg)
    return [(param.arg, param.lineno) for param in parameters]


def empty_word_count(code: str) -> int:
    """Counts identifiers only where the N1 ast-grep rule actually looks --
    a bare-name assignment target, or a function parameter -- and drops the
    ones taorc-lint's own short-function exclusion would drop, so this
    metric can't silently drift from the linter it approximates."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return len(EMPTY_WORD_PATTERN.findall(code))

    names: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                names.extend(_assignment_target_names(target))
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            names.extend(_assignment_target_names(node.target))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            names.extend(_parameter_names(node.args))

    short_function_lines = {
        line for start, end in short_python_function_ranges(code) for line in range(start, end + 1)
    }
    return sum(
        1
        for name, lineno in names
        if EMPTY_WORD_PATTERN.fullmatch(name) and lineno not in short_function_lines
    )


def run_lint(code: str, suffix: str) -> list[dict] | None:
    """Returns None (not scored) rather than raising on any lint-subprocess
    failure -- one pathological completion should drop that one score, not
    crash the whole run and lose every score already computed."""
    if not LINT_SCRIPT.exists():
        return None
    scratch = EVALS_ROOT / f"_score_scratch{suffix}"
    scratch.write_text(code, encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(LINT_SCRIPT), str(scratch), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return None
    finally:
        scratch.unlink(missing_ok=True)
    if not completed.stdout.strip():
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def diff_line_count(before: str, after: str) -> int:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="")
    return sum(
        1
        for line in diff
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )


def score_completion(scenario: Scenario, completion_path: Path) -> dict:
    completion_text = completion_path.read_text(encoding="utf-8")
    code = extract_code(completion_text)
    suffix = Path(scenario.output_file).suffix
    loc = count_loc(code)
    findings = run_lint(code, suffix)
    max_depth, mean_depth = nesting_depth(code)

    findings_per_100_loc = None
    if findings is not None and loc:
        findings_per_100_loc = round(len(findings) * 100 / loc, 2)

    metrics = {
        "loc": loc,
        "lint_findings": len(findings) if findings is not None else None,
        "lint_findings_per_100_loc": findings_per_100_loc,
        "comment_to_code_ratio": comment_ratio(code),
        "max_nesting_depth": max_depth,
        "mean_nesting_depth": mean_depth,
        "empty_word_identifier_count": empty_word_count(code),
    }

    if scenario.measure_diff_size and scenario.starter_files:
        starter_path = next(iter(scenario.starter_files))
        before = scenario.starter_files[starter_path]
        metrics["diff_lines_vs_starter"] = diff_line_count(before, code)
    elif scenario.measure_diff_size:
        print(
            f"  WARNING {scenario.id}: measure_diff_size is set but starter_files is "
            "empty -- skipping diff_lines_vs_starter for this completion",
            file=sys.stderr,
        )

    return metrics


def score_run(run_dir: Path) -> dict:
    scenarios_by_id = {s.id: s for s in load_all_scenarios()}
    scores: dict[str, dict] = {}

    raw_dir = run_dir / "raw"
    for scenario_dir in sorted(raw_dir.iterdir()):
        scenario = scenarios_by_id.get(scenario_dir.name)
        if scenario is None:
            continue
        scores[scenario.id] = {}
        for model_dir in sorted(scenario_dir.iterdir()):
            scores[scenario.id][model_dir.name] = {}
            for completion_path in sorted(model_dir.glob("*")):
                if completion_path.suffix == ".json":
                    continue
                condition = completion_path.stem
                scores[scenario.id][model_dir.name][condition] = score_completion(
                    scenario, completion_path
                )

    return scores


def summarize_guardrail(scores: dict) -> dict:
    """Diff-size inflation on the three measure_diff_size scenarios, skill
    vs. baseline, averaged per model -- PRD M3. A baseline diff of zero
    lines is legitimate data (the baseline condition left the starter file
    untouched), not a missing score, so it's kept rather than treated like
    a missing diff_lines_vs_starter value."""
    scenarios_by_id = {s.id: s for s in load_all_scenarios()}
    inflation_by_model: dict[str, list[float]] = {}

    for scenario_id, by_model in scores.items():
        scenario = scenarios_by_id.get(scenario_id)
        if scenario is None or not scenario.measure_diff_size:
            continue
        for model_slot, by_condition in by_model.items():
            baseline = by_condition.get("baseline", {}).get("diff_lines_vs_starter")
            skill = by_condition.get("skill", {}).get("diff_lines_vs_starter")
            if baseline is None or skill is None:
                continue
            if baseline == 0:
                if skill > 0:
                    # Skill edited a file the baseline left untouched -- exactly
                    # the over-editing case M3 exists to catch, but the ratio is
                    # unbounded (division by zero) and can't join the averaged
                    # percentage below, so flag it instead of silently dropping it.
                    print(
                        f"  WARNING {scenario_id}/{model_slot}: baseline made a "
                        f"zero-line diff but skill made a {skill}-line diff -- "
                        "unbounded inflation, not included in the percentage below",
                        file=sys.stderr,
                    )
                    continue
                inflation_by_model.setdefault(model_slot, []).append(0.0)
                continue
            inflation_by_model.setdefault(model_slot, []).append((skill - baseline) / baseline)

    return {
        model_slot: round(sum(ratios) / len(ratios) * 100, 1)
        for model_slot, ratios in inflation_by_model.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run", required=True, help="a run directory produced by run_bench.py")
    args = parser.parse_args()

    run_dir = Path(args.run)
    if not (run_dir / "raw").is_dir():
        parser.error(f"{run_dir} has no raw/ directory -- run run_bench.py first")

    scores = score_run(run_dir)
    guardrail = summarize_guardrail(scores)

    scores_document = {"scores": scores, "guardrail_diff_inflation_pct": guardrail}
    scores_path = run_dir / "scores.json"
    scores_path.write_text(json.dumps(scores_document, indent=2), encoding="utf-8")
    print(f"wrote {scores_path}")
    for model_slot, inflation_pct in guardrail.items():
        print(f"  {model_slot}: diff-size inflation {inflation_pct:+.1f}% (M3 target <= 10%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
