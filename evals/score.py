#!/usr/bin/env python3
"""Automated scoring track (design doc §10.2, PRD M1/M3).

Reads the raw completions written by run_bench.py and computes, per
scenario/model/condition:

  - taorc-lint findings per 100 LOC                        -> M1
  - comment-to-code ratio, and the share of those comments that explain why
  - mean and max nesting depth
  - empty-word identifier count (N1's own word list)
  - diff size vs. the starter file, on scenarios that measure it -> M3

Nothing here calls a model or costs money; it is pure text analysis over
files run_bench.py already wrote, which is what "deterministic, free"
(§10.2) means for this track.

scores.json also carries a generation_errors list -- the cells run_bench.py
recorded as failed -- so a missing number reads as a known gap, not a zero.

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
import tempfile
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

CODE_FENCE_PATTERN = re.compile(r"```([\w+-]*)\n(.*?)```", re.DOTALL)

# Fence languages that count as "the code" for a given scenario output file.
# A skill-condition completion often wraps the answer in a ```python block and
# then adds longer ```text blocks (a findings list, a behaviour check), so
# "longest fenced block" alone picks the prose. Matching the language first
# keeps scoring on the actual code.
FENCE_LANGS_FOR_SUFFIX = {
    ".py": {"python", "py"},
    ".ts": {"typescript", "ts"},
    ".tsx": {"tsx", "typescript"},
    ".js": {"javascript", "js"},
    ".jsx": {"jsx", "javascript"},
}

# Sourced from the N1 ast-grep rule itself (rather than a second hardcoded
# list here) so this metric can't silently drift from what the linter
# already treats as an empty word.
_LINT_RULES_ROOT = REPO_ROOT / "skills" / "readable-code" / "scripts" / "rules"
_N1_RULE_PATH = _LINT_RULES_ROOT / "python" / "taorc-n1-empty-word-identifier.yml"


def load_empty_word_pattern() -> re.Pattern:
    text = _N1_RULE_PATH.read_text(encoding="utf-8")
    # Greedy `.+` so an alternation that itself contains a parenthesised
    # group is captured whole, not truncated at its first ')'.
    match = re.search(r"regex:\s*'\^\((.+)\)\$'", text)
    if not match:
        raise ValueError(f"could not find N1's word-list regex in {_N1_RULE_PATH}")
    return re.compile(rf"\b({match.group(1)})\b")


EMPTY_WORD_PATTERN = load_empty_word_pattern()


# A same-language block this much shorter than the overall longest block is
# treated as an illustrative snippet, not the answer.
_MIN_SAME_LANGUAGE_LENGTH_RATIO = 0.5


def extract_code(completion_text: str, output_suffix: str = "") -> str:
    """A raw completion is often prose plus one or more fenced code blocks.
    Prefer the largest block whose fence language matches the scenario's
    output file; fall back to the largest block of any language; if the
    model returned bare code with no fence at all, score the whole
    response.

    The language match only wins when its largest block is within
    `_MIN_SAME_LANGUAGE_LENGTH_RATIO` of the overall longest block, so a
    short tagged snippet doesn't beat the real answer sitting in an
    untagged fence."""
    blocks = CODE_FENCE_PATTERN.findall(completion_text)
    if not blocks:
        return completion_text
    all_bodies = [body for _lang, body in blocks]
    longest_body = max(all_bodies, key=len)
    wanted_langs = FENCE_LANGS_FOR_SUFFIX.get(output_suffix.lower(), set())
    same_language_blocks = [body for lang, body in blocks if lang.lower() in wanted_langs]
    if not same_language_blocks:
        return longest_body
    longest_same_language = max(same_language_blocks, key=len)
    is_close_to_longest = (
        len(longest_same_language) >= _MIN_SAME_LANGUAGE_LENGTH_RATIO * len(longest_body)
    )
    return longest_same_language if is_close_to_longest else longest_body


def count_loc(code: str) -> int:
    return sum(1 for line in code.splitlines() if line.strip())


def count_comments(code: str) -> int | None:
    """Number of `#` comments in the file, or None if it doesn't tokenize.
    A line holds at most one comment token, so this doubles as a
    comment-line count for the why-comment share below."""
    try:
        tokens = list(tokenize.generate_tokens(StringIO(code).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return None
    return sum(1 for tok in tokens if tok.type == tokenize.COMMENT)


def comment_ratio(code: str) -> float | None:
    comment_count = count_comments(code)
    if comment_count is None:
        return None
    code_lines = count_loc(code)
    if code_lines == 0:
        return None
    return round(comment_count / code_lines, 3)


# The rules that fire on a comment for saying what the code already says:
# C1 (echoes the next statement), X7 (plan narration), X8 (banner/divider).
WHAT_COMMENT_RULES = frozenset({"C1", "X7", "X8"})


def why_comment_share(code: str, findings: list[dict] | None) -> float | None:
    """Of the file's comments, the fraction that explain intent rather than
    restate the code. comment_ratio is the volume half of the design doc's
    C-category signal; this is the quality half -- a file can carry a
    healthy comment ratio and still be all what-comments. A what-comment is
    one taorc-lint flags under WHAT_COMMENT_RULES. Needs the linter, so
    it's None exactly when `findings` is (ast-grep absent, pathological
    file)."""
    if findings is None:
        return None
    comment_count = count_comments(code)
    if not comment_count:
        return None
    what_comment_lines = {f["line"] for f in findings if f.get("id") in WHAT_COMMENT_RULES}
    why_comments = max(0, comment_count - len(what_comment_lines))
    return round(why_comments / comment_count, 3)


def nesting_depth(code: str) -> tuple[int, float] | tuple[None, None]:
    """Max and mean nesting depth across the compound statements in the
    module (if/for/while/try/with/match/function/class bodies), counted by
    AST structure rather than indentation columns so formatting can't skew
    it.

    A flat `if/elif/elif/else` chain counts as one level, not one more per
    branch: `ast` nests each `elif` as an `If` inside the previous one's
    `orelse`, but a reader sees a flat dispatch, and scoring it as deep
    nesting would penalize the exact F-category restructuring the skill
    asks for. `match` is treated the same way -- one level for the whole
    statement, its case bodies at that same depth."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None, None

    block_depths: list[int] = []
    nesting_types = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncWith,
        ast.Match,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
    )

    def walk(node: ast.AST, depth: int) -> None:
        is_nesting_block = isinstance(node, nesting_types)
        block_depth = depth + 1 if is_nesting_block else depth
        if is_nesting_block:
            block_depths.append(block_depth)
        for child in ast.iter_child_nodes(node):
            child_is_elif = (
                isinstance(node, ast.If)
                and isinstance(child, ast.If)
                and len(node.orelse) == 1
                and child is node.orelse[0]
            )
            walk(child, depth if child_is_elif else block_depth)

    walk(tree, 0)
    if not block_depths:
        return 0, 0.0
    return max(block_depths), round(sum(block_depths) / len(block_depths), 2)


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


def run_lint(code: str, file_extension: str) -> list[dict] | None:
    """Returns None (not scored) rather than raising on any lint-subprocess
    failure -- one pathological completion should drop that one score, not
    crash the whole run and lose every score already computed.

    The completion goes to a private temp dir, not a fixed path under
    evals/: every Python scenario shares one extension, so two score.py
    runs (scoring two run dirs at once) would clobber each other's scratch
    file mid-lint, and a hard kill would strand model-generated code at a
    path the CI lint job scans."""
    if not LINT_SCRIPT.exists():
        return None
    with tempfile.TemporaryDirectory() as scratch_dir:
        scratch = Path(scratch_dir) / f"completion{file_extension}"
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


def _starter_for_output_file(scenario: Scenario) -> str | None:
    """The starter the completion is meant to edit -- the one whose basename
    matches output_file. `next(iter(starter_files))` would compare the model
    output against an unrelated starter on any multi-starter scenario, making
    the M3 diff-inflation number meaningless."""
    output_name = Path(scenario.output_file).name
    for relative_path, content in scenario.starter_files.items():
        if Path(relative_path).name == output_name:
            return content
    return None


def score_completion(scenario: Scenario, completion_path: Path) -> dict:
    completion_text = completion_path.read_text(encoding="utf-8")
    file_extension = Path(scenario.output_file).suffix
    code = extract_code(completion_text, file_extension)
    loc = count_loc(code)
    findings = run_lint(code, file_extension)
    max_depth, mean_depth = nesting_depth(code)

    findings_per_100_loc = None
    if findings is not None and loc:
        findings_per_100_loc = round(len(findings) * 100 / loc, 2)

    metrics = {
        "loc": loc,
        "lint_findings": len(findings) if findings is not None else None,
        "lint_findings_per_100_loc": findings_per_100_loc,
        "comment_to_code_ratio": comment_ratio(code),
        "why_comment_share": why_comment_share(code, findings),
        "max_nesting_depth": max_depth,
        "mean_nesting_depth": mean_depth,
        "empty_word_identifier_count": empty_word_count(code),
    }

    if scenario.measure_diff_size:
        starter_before = _starter_for_output_file(scenario)
        if starter_before is None:
            print(
                f"  WARNING {scenario.id}: measure_diff_size is set but no starter "
                f"file matches output_file {scenario.output_file!r} -- skipping "
                "diff_lines_vs_starter for this completion",
                file=sys.stderr,
            )
        else:
            metrics["diff_lines_vs_starter"] = diff_line_count(starter_before, code)

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


def collect_generation_errors(run_dir: Path) -> list[dict]:
    """Every cell run_bench.py recorded as failed instead of scored, so a
    reader of scores.json can tell a genuinely-absent number from a low
    one. run_bench.py writes <condition>.error.json on failure and deletes
    it once that cell later succeeds, so this is the live list of gaps."""
    errors: list[dict] = []
    for error_path in sorted((run_dir / "raw").glob("*/*/*.error.json")):
        try:
            errors.append(json.loads(error_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            errors.append(
                {"error_file": str(error_path.relative_to(run_dir)), "error": "unreadable"}
            )
    return errors


def summarize_guardrail(scores: dict) -> dict:
    """Diff-size inflation on the three measure_diff_size scenarios, skill
    vs. baseline, averaged per model -- PRD M3. A baseline diff of zero
    lines is legitimate data (the baseline condition left the starter file
    untouched), not a missing score, so it's kept rather than treated like
    a missing diff_lines_vs_starter value. When the baseline made no edit
    but the skill did, the ratio would divide by zero; the denominator is
    floored at one line so that case still lands in the average -- dropping
    it let the worst over-editor (skill touches a file baseline left alone)
    report a better M3 number than a milder one whose baseline edited a
    line or two."""
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
            if baseline == 0 and skill > 0:
                print(
                    f"  WARNING {scenario_id}/{model_slot}: baseline made a "
                    f"zero-line diff but skill made a {skill}-line diff -- "
                    "scoring it against a one-line baseline floor",
                    file=sys.stderr,
                )
            baseline_floor = max(baseline, 1)
            inflation_by_model.setdefault(model_slot, []).append(
                (skill - baseline) / baseline_floor
            )

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
    generation_errors = collect_generation_errors(run_dir)

    scores_document = {
        "scores": scores,
        "guardrail_diff_inflation_pct": guardrail,
        "generation_errors": generation_errors,
    }
    scores_path = run_dir / "scores.json"
    scores_path.write_text(json.dumps(scores_document, indent=2), encoding="utf-8")
    print(f"wrote {scores_path}")
    for model_slot, inflation_pct in guardrail.items():
        print(f"  {model_slot}: diff-size inflation {inflation_pct:+.1f}% (M3 target <= 10%)")
    if generation_errors:
        print(
            f"  WARNING: {len(generation_errors)} cell(s) failed generation and are absent "
            "from the scores above, not scored as zero:",
            file=sys.stderr,
        )
        for entry in generation_errors:
            print(
                f"    {entry.get('scenario_id', '?')} / {entry.get('model_slot', '?')} / "
                f"{entry.get('condition', '?')}: {entry.get('error', '?')}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
