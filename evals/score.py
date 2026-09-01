#!/usr/bin/env python3
"""Automated scoring track (design doc §10.2, PRD M1/M3).

Reads the raw completions written by run_bench.py and computes, per
scenario/model/condition:

  - taorc-lint findings per 100 LOC                        -> M1
  - comment-to-code ratio, and the share of those comments that explain why
  - mean and max nesting depth
  - empty-word identifier count (N1's own word list)
  - diff size of the edit vs. the starter file, on scenarios that
    measure it -- invariant to whether the completion echoed the whole
    file or returned only the changed function                    -> M3

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


def extract_code(completion_text: str, output_suffix: str = "") -> str:
    """A raw completion is often prose plus one or more fenced code blocks.
    Prefer the largest block whose fence language matches the scenario's
    output file; with no such block, prefer the largest *untagged* fence (a
    real answer the model left untagged) over a tagged prose block like
    ```text; fall back to the largest block of any language; if the model
    returned bare code with no fence at all, score the whole response."""
    blocks = CODE_FENCE_PATTERN.findall(completion_text)
    if not blocks:
        return completion_text
    wanted_langs = FENCE_LANGS_FOR_SUFFIX.get(output_suffix.lower(), set())
    same_language_blocks = [body for lang, body in blocks if lang.lower() in wanted_langs]
    if same_language_blocks:
        return max(same_language_blocks, key=len)
    untagged_blocks = [body for lang, body in blocks if lang == ""]
    return max(untagged_blocks or [body for _lang, body in blocks], key=len)


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


def _top_level_definition_spans(tree: ast.Module) -> dict[str, tuple[int, int]]:
    """name -> (first_line, last_line), 1-indexed and inclusive, for every
    top-level function or class. A decorator line is part of the span so a
    completion that reformats decorators still swaps in cleanly."""
    spans: dict[str, tuple[int, int]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        first_line = min([node.lineno, *(d.lineno for d in node.decorator_list)])
        spans[node.name] = (first_line, node.end_lineno)
    return spans


def _prologue_lines(tree: ast.Module, source_lines: list[str]) -> set[str]:
    """Stripped, non-blank source lines of every top-level statement that is
    not a function or class -- the module docstring, imports, and module-level
    assignments. A full-file completion reproduces these lines; a fragment that
    rewrites one function drops them."""
    prologue: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for raw_line in source_lines[node.lineno - 1 : node.end_lineno]:
            if raw_line.strip():
                prologue.add(raw_line.strip())
    return prologue


def _completion_echoes_an_unchanged_definition(
    starter_spans: dict[str, tuple[int, int]],
    completion_spans: dict[str, tuple[int, int]],
    starter_lines: list[str],
    completion_lines: list[str],
) -> bool:
    """True if the completion reproduces at least one of the starter's
    definitions verbatim. A fragment includes only what it changes, so echoing
    an untouched definition is the signature of a whole-file rewrite -- the
    reading that keeps a full-file completion's own deletions visible to M3."""
    for name, starter_span in starter_spans.items():
        completion_span = completion_spans.get(name)
        if completion_span is None:
            continue
        starter_body = _lines_in_span(starter_lines, starter_span)
        completion_body = _lines_in_span(completion_lines, completion_span)
        if [line.strip() for line in starter_body] == [
            line.strip() for line in completion_body
        ]:
            return True
    return False


def _lines_in_span(source_lines: list[str], span: tuple[int, int]) -> list[str]:
    first_line, last_line = span
    return source_lines[first_line - 1 : last_line]


def _leading_whitespace(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _starter_method_spans(
    tree: ast.Module, source_lines: list[str]
) -> dict[str, list[tuple[str, tuple[int, int], str]]]:
    """method name -> list of (owning class, (first_line, last_line), indent)
    for every method of a top-level class. A completion that returns just the
    one changed method -- dedented to column 0, so it parses as a top-level
    function -- is spliced back into its class instead of appended as a stray
    module-level function (#26). Scenario 02's starter is a single class with
    no top-level function at all."""
    methods: dict[str, list[tuple[str, tuple[int, int], str]]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            first_line = min([child.lineno, *(d.lineno for d in child.decorator_list)])
            indent = _leading_whitespace(source_lines[first_line - 1])
            span = (first_line, child.end_lineno)
            methods.setdefault(child.name, []).append((node.name, span, indent))
    return methods


def _reindent(body_lines: list[str], indent: str) -> list[str]:
    """A completion method returned at column 0, re-indented to sit in a class
    body so only the lines the model actually changed show up in the M3 diff."""
    non_blank = [line for line in body_lines if line.strip()]
    own_indent = min((len(_leading_whitespace(line)) for line in non_blank), default=0)
    return [indent + line[own_indent:] if line.strip() else "" for line in body_lines]


def _rebuild_class_with_method_edits(
    starter_lines: list[str],
    class_span: tuple[int, int],
    completion_lines: list[str],
    method_edits: list[tuple[tuple[int, int], str, tuple[int, int]]],
) -> list[str]:
    """The starter's class span with each edited method swapped in place and
    every other line kept byte-for-byte."""
    class_first, class_last = class_span
    rebuilt: list[str] = []
    next_line = class_first
    for (method_first, method_last), indent, completion_span in sorted(method_edits):
        rebuilt.extend(starter_lines[next_line - 1 : method_first - 1])
        rebuilt.extend(
            _reindent(_lines_in_span(completion_lines, completion_span), indent)
        )
        next_line = method_last + 1
    rebuilt.extend(starter_lines[next_line - 1 : class_last])
    return rebuilt


def _definitions_removed_by_fragment(
    starter_defs_in_order: list[tuple[str, tuple[int, int]]],
    completion_spans: dict[str, tuple[int, int]],
    names_still_referenced: set[str],
) -> set[str]:
    """Top-level names a fragment completion deleted rather than left alone.

    A fragment says nothing about definitions outside the region it rewrites,
    so one it simply omits is kept. But a definition that sits between two the
    fragment does redefine, and that nothing surviving the splice still names,
    was removed on purpose -- re-inserting it would hide the deletion from M3
    (#26). "Nothing still names" is an AST check over both the completion and
    every starter definition the fragment left untouched: a matching substring
    in a string literal or a comment (`# inlined line_total`) does not count as
    a use, but a call from an unchanged sibling function does."""
    redefined_indices = [
        index
        for index, (name, _) in enumerate(starter_defs_in_order)
        if name in completion_spans
    ]
    if len(redefined_indices) < 2:
        return set()

    rewritten_region = range(min(redefined_indices), max(redefined_indices) + 1)
    removed: set[str] = set()
    for index, (name, _span) in enumerate(starter_defs_in_order):
        if name in completion_spans or index not in rewritten_region:
            continue
        if name not in names_still_referenced:
            removed.add(name)
    return removed


def _names_referenced(tree: ast.Module) -> set[str]:
    """Every identifier the code actually reads or writes -- `ast.Name` loads
    and stores plus attribute accesses -- so a name that appears only inside a
    string or comment is not mistaken for a live reference."""
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    return referenced


def _names_referenced_by_kept_code(
    tree: ast.Module, replaced_def_names: set[str]
) -> set[str]:
    """Identifiers read or written by the top-level statements a fragment splice
    keeps byte-for-byte -- the prologue plus every definition the completion did
    not redefine. A name used only by this surviving code is still live, so the
    fragment omitting its definition is not a deletion (#26)."""
    referenced: set[str] = set()
    for node in tree.body:
        is_definition = isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        )
        if is_definition and node.name in replaced_def_names:
            continue
        for descendant in ast.walk(node):
            if isinstance(descendant, ast.Name):
                referenced.add(descendant.id)
            elif isinstance(descendant, ast.Attribute):
                referenced.add(descendant.attr)
    return referenced


def reconstruct_edited_file(starter_source: str, completion_code: str) -> str:
    """The starter file as this completion would leave it, so M3 measures the
    edit rather than how much unchanged code the model chose to echo.

    A completion that returns the whole file is scored as-is. One that returns
    only the changed or added function is applied onto the starter: a top-level
    definition with a matching name replaces the original, a new one is
    appended, one dropped from inside the rewritten region is deleted, and
    anything else the completion never mentions stays byte-for-byte."""
    try:
        starter_tree = ast.parse(starter_source)
        completion_tree = ast.parse(completion_code)
    except SyntaxError:
        return completion_code

    starter_spans = _top_level_definition_spans(starter_tree)
    completion_spans = _top_level_definition_spans(completion_tree)

    starter_lines = starter_source.splitlines()
    completion_lines = completion_code.splitlines()

    # A bare fragment redefines every name in a small starter too (scenarios 02
    # and 09 define just one), so name coverage alone misreads it as a rewrite
    # (#26). A whole-file completion also either carries the starter's prologue
    # or echoes at least one untouched definition; a fragment that adds its own
    # import satisfies neither and is still spliced (its new prologue line is
    # not merged in, so M3 undercounts that one line rather than counting every
    # un-echoed starter line as a deletion).
    completion_redefines_every_name = starter_spans.keys() <= completion_spans.keys()
    starter_prologue = _prologue_lines(starter_tree, starter_lines)
    completion_keeps_starter_prologue = bool(starter_prologue) and starter_prologue <= (
        _prologue_lines(completion_tree, completion_lines)
    )
    completion_echoes_unchanged_definition = _completion_echoes_an_unchanged_definition(
        starter_spans, completion_spans, starter_lines, completion_lines
    )
    # A whole-file completion that renamed or dropped a top-level definition on
    # purpose no longer redefines every starter name, so the name-coverage test
    # alone misreads it as a fragment and splices the stale definition back
    # (#26). Reproducing the starter's entire prologue -- its docstring and
    # imports -- is the signal that the model returned the whole file anyway; a
    # bare fragment carries none of it. Redefining every one of two or more
    # starter definitions is the same signal even when the prologue was
    # deliberately dropped: a fragment does not rewrite the whole file.
    completion_rewrites_every_definition = (
        len(starter_spans) >= 2 and completion_redefines_every_name
    )
    completion_is_full_file = (
        completion_keeps_starter_prologue
        or completion_rewrites_every_definition
        or (
            completion_redefines_every_name
            and (not starter_prologue or completion_echoes_unchanged_definition)
        )
    )
    if not completion_spans or completion_is_full_file:
        return completion_code

    starter_defs_in_order = sorted(starter_spans.items(), key=lambda item: item[1][0])
    names_still_referenced = _names_referenced(completion_tree) | (
        _names_referenced_by_kept_code(starter_tree, set(completion_spans))
    )
    removed_names = _definitions_removed_by_fragment(
        starter_defs_in_order, completion_spans, names_still_referenced
    )

    # A completion def that names no top-level starter definition but exactly
    # one method of a top-level starter class is that method's rewrite, not a
    # new module-level function (#26).
    starter_method_spans = _starter_method_spans(starter_tree, starter_lines)
    method_edits_by_class: dict[str, list[tuple[tuple[int, int], str, tuple[int, int]]]] = {}
    spliced_method_names: set[str] = set()
    for name, completion_span in completion_spans.items():
        if name in starter_spans:
            continue
        owners = starter_method_spans.get(name, [])
        if len(owners) != 1:
            continue
        owning_class, method_span, indent = owners[0]
        method_edits_by_class.setdefault(owning_class, []).append(
            (method_span, indent, completion_span)
        )
        spliced_method_names.add(name)

    rebuilt: list[str] = []
    next_starter_line = 1
    for name, (first_line, last_line) in starter_defs_in_order:
        if name in removed_names:
            next_starter_line = last_line + 1
            continue
        rebuilt.extend(starter_lines[next_starter_line - 1 : first_line - 1])
        if name in completion_spans:
            rebuilt.extend(_lines_in_span(completion_lines, completion_spans[name]))
        elif name in method_edits_by_class:
            rebuilt.extend(
                _rebuild_class_with_method_edits(
                    starter_lines,
                    (first_line, last_line),
                    completion_lines,
                    method_edits_by_class[name],
                )
            )
        else:
            rebuilt.extend(starter_lines[first_line - 1 : last_line])
        next_starter_line = last_line + 1
    rebuilt.extend(starter_lines[next_starter_line - 1 :])

    for name, span in completion_spans.items():
        if name not in starter_spans and name not in spliced_method_names:
            rebuilt.extend(["", "", *_lines_in_span(completion_lines, span)])

    return "\n".join(rebuilt) + "\n"


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
            code_after_edit = reconstruct_edited_file(starter_before, code)
            metrics["diff_lines_vs_starter"] = diff_line_count(starter_before, code_after_edit)

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
