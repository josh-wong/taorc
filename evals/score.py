#!/usr/bin/env python3
"""Automated scoring track (design doc §10.2, PRD M1/M3).

Reads the raw completions written by run_bench.py and computes, per
scenario/model/condition:

  - taorc-lint findings the completion introduced, per 100 LOC   -> M1
    (a finding inherited unchanged from the scenario's starter is
    not charged to the completion that edited around it -- issue #31)
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
from collections import Counter
from io import StringIO
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
LINT_SCRIPT = REPO_ROOT / "skills" / "readable-code" / "scripts" / "taorc_lint.py"

# Bumped whenever a change here alters a published number's meaning, not just
# its value. scores.json records it, and a run scored under an earlier version
# is frozen: score.py will not overwrite it without --rescore, and the CI
# re-score gate skips it, so a metric redefinition never silently rewrites a
# run already published under the old definition.
#   1 -> the MS6 scorer (implicit; pre-versioning runs carry no field)
#   2 -> M1 counts only the findings a completion introduced, not those it
#        inherited unchanged from the scenario's starter (issues #31, #34): a
#        finding is inherited only when the starter line it sits on survived
#        the edit in place, so a fresh violation on a coincidentally identical
#        line still counts
SCORER_VERSION = 2

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
    ".py": {"python", "py", "python3", "py3"},
    ".ts": {"typescript", "ts"},
    ".tsx": {"tsx", "typescript"},
    ".js": {"javascript", "js"},
    ".jsx": {"jsx", "javascript"},
}

# Fence tags that mark a block as prose or a terminal transcript, never the
# answer. When no block matches the scenario's language, the largest block
# that isn't one of these wins -- an untagged answer or an unusual code tag
# (```pycon, ```python-repl) beats a longer ```text findings list.
PROSE_FENCE_LANGS = {
    "text",
    "txt",
    "plaintext",
    "markdown",
    "md",
    "console",
    "output",
    "log",
    "shell",
    "sh",
    "bash",
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
    output file; with no such block, prefer the largest fence that isn't
    tagged as prose (```text and friends) over one that is; fall back to the
    largest block of any language; if the model returned bare code with no
    fence at all, score the whole response."""
    blocks = CODE_FENCE_PATTERN.findall(completion_text)
    if not blocks:
        return completion_text
    wanted_langs = FENCE_LANGS_FOR_SUFFIX.get(output_suffix.lower(), set())
    same_language_blocks = [body for lang, body in blocks if lang.lower() in wanted_langs]
    if same_language_blocks:
        return max(same_language_blocks, key=len)
    non_prose_blocks = [body for lang, body in blocks if lang.lower() not in PROSE_FENCE_LANGS]
    return max(non_prose_blocks or [body for _lang, body in blocks], key=len)


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


def _bound_names(node: ast.stmt) -> frozenset[str]:
    """The module-level names an import or assignment binds, or an empty set for
    a target this merge will not match on -- an attribute or a subscript. Two
    prologue statements that bind exactly the same names are two versions of one
    decision, so the completion's is a replacement rather than an addition."""
    if isinstance(node, ast.Import):
        return frozenset(alias.asname or alias.name.split(".")[0] for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return frozenset(
            alias.asname or alias.name for alias in node.names if alias.name != "*"
        )
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names: set[str] = set()
    for target in targets:
        elements = target.elts if isinstance(target, (ast.Tuple, ast.List)) else [target]
        for element in elements:
            if not isinstance(element, ast.Name):
                return frozenset()
            names.add(element.id)
    return frozenset(names)


def _prologue_spans_by_bound_names(
    tree: ast.Module,
) -> dict[frozenset[str], tuple[int, int]]:
    """bound names -> (first_line, last_line) for each import or assignment in
    the module's prologue, first one wins. The scan stops at the first
    definition, matching the half of the file merge_completion_prologue writes
    into."""
    spans: dict[frozenset[str], tuple[int, int]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)):
            continue
        names = _bound_names(node)
        if names and names not in spans:
            spans[names] = (node.lineno, node.end_lineno)
    return spans


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


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _line_after_comment_header(source_lines: list[str]) -> int:
    """The 0-indexed line just past the comment block a file opens with -- a
    shebang, a license header -- or 0 when it opens with anything else.
    Inserting above a shebang demotes it to an ordinary comment, which leaves
    the file no longer executable as a script and reads as damage to a judge
    grading layout."""
    past_header = 0
    for line in source_lines:
        if not line.lstrip().startswith("#"):
            break
        past_header += 1
    return past_header


def _line_after_prologue(tree: ast.Module, source_lines: list[str]) -> int:
    """The 0-indexed line to insert another prologue statement at: just past
    the module's last leading import or assignment, or just past the opening
    comment header when the file goes straight from that into a definition."""
    insert_at = _line_after_comment_header(source_lines)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        insert_at = node.end_lineno
    return insert_at


def _line_for_future_import(tree: ast.Module, source_lines: list[str]) -> int:
    """The 0-indexed line a `from __future__` import has to go at or before:
    just past the module docstring, or past the opening comment header when the
    file has no docstring. A docstring is the only statement Python lets precede
    a future import, and a comment is not a statement at all."""
    if tree.body and _is_docstring(tree.body[0]):
        return tree.body[0].end_lineno
    return _line_after_comment_header(source_lines)


def _line_after_shebang(source_lines: list[str]) -> int:
    """The 0-indexed line just past a file's shebang, or 0 when it has none.

    Only the shebang, not the whole opening comment block: a comment block a
    completion opens with is as likely to be the `why` for the constant under
    it as a file header, and keeping it is the cheaper mistake. A `#!` line is
    a header either way, and copying one into the middle of a file is damage a
    judge can see.

    The scan starts at the first non-blank line: extract_code keeps whatever
    blank line the fenced body opened with, and reading line 0 alone would let
    one blank ahead of the shebang hide it."""
    for index, line in enumerate(source_lines):
        if not line.strip():
            continue
        return index + 1 if line.startswith("#!") else 0
    return 0


def _first_line_of_leading_comments(
    source_lines: list[str], first_line: int, header_end: int = 0
) -> int:
    """The 1-indexed line the comment block above a statement starts on, or
    `first_line` when code or blank space sits directly above it. A statement's
    ast span starts at the statement itself, so merging by span alone strips the
    `why` comment C5 asks for off the constant it explains.

    Stops at `header_end` -- see _line_after_shebang. A completion whose first
    import sits directly under its own shebang would otherwise carry that line
    into the middle of the spliced file, the same layout damage
    _line_after_comment_header keeps the starter's header safe from, arriving
    from the completion side."""
    while first_line - 1 > header_end and source_lines[first_line - 2].lstrip().startswith("#"):
        first_line -= 1
    return first_line


def _opens_a_definition(line: str) -> bool:
    return line.startswith(("def ", "async def ", "class ", "@"))


def _definition_follows(after: list[str]) -> bool:
    """True when the first thing below the insertion point is a definition,
    looking past the comment block that definition owns. A `def` under its own
    `why` comment is still a `def`, and reading only the comment line would
    leave it the one blank line an ordinary statement gets."""
    for line in after:
        if not line.lstrip().startswith("#"):
            return _opens_a_definition(line)
    return False


def _inserted_with_blank_lines(lines: list[str], insert_at: int, block: list[str]) -> list[str]:
    """`lines` with `block` inserted at 0-indexed `insert_at`, held apart from
    its new neighbours by a blank line -- two where a definition follows, which
    is what a formatter would leave. Adds no blank line at the start or end of
    the file, or where the neighbour is already blank."""
    before, after = lines[:insert_at], lines[insert_at:]
    spaced = list(block)
    if before and before[-1].strip():
        spaced.insert(0, "")
    if after and after[0].strip():
        spaced.extend(["", ""] if _definition_follows(after) else [""])
    return before + spaced + after


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
    anything else the completion never mentions stays byte-for-byte.

    Three limits worth knowing before reusing this for anything but M3:

    A new definition goes at the end of the file, whatever placement the
    completion asked for -- a fragment that adds one function alone carries no
    structural anchor, and only its surrounding prose says where it belongs.
    Harmless for M3, which counts diff lines. Not harmless for judging, where
    the F and S rubric categories grade reading order, so a judge scores the
    layout this function chose rather than the model's.

    The rebuilt file carries the starter's prologue, not the completion's, so
    an import or module-level constant the fragment added is dropped -- one
    uncounted diff line for M3, but code that no longer resolves its own names
    for anyone else. merge_completion_prologue puts those lines back.

    Deletion cannot be expressed at all except inside a region the completion
    rewrote wholesale. Splicing a completion whose task was removal restores
    what it removed; judge.py's starter_to_splice_onto exists to keep that
    off the removal-shaped scenarios."""
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


def merge_completion_prologue(spliced_source: str, completion_code: str) -> str:
    """`spliced_source` with every import and module-level assignment the
    completion added but the splice dropped, inserted below the prologue the
    file already has -- above it for a `from __future__` import, the one
    statement Python accepts nowhere else.

    reconstruct_edited_file rebuilds a fragment from the starter's lines plus
    the completion's definitions, which loses the completion's own prologue.
    M3 only undercounts a line for that. A judge is handed code that cannot
    resolve its own names: a completion that adds `import logging` and a
    module-level `logger`, then follows X1 by printing only the function it
    changed, is graded on a file where `logger` is undefined -- the output-format
    confound that splicing exists to remove, in a worse form.

    Imports and assignments are the only statements merged. Anything else a
    completion leaves at module level runs rather than defines -- an
    `if __name__ == "__main__"` guard, a demo call -- and the merge inserts
    above the file's definitions, so merging one would hand the judge a file
    that raises NameError on the function it sits above. A module docstring is
    left out for its own reason: the starter's already stands, and a second one
    lands mid-file as a stray expression.

    Only the completion's own prologue is read: the scan stops at its first
    definition, because the same insert-above-the-definitions rule makes an
    assignment the completion wrote below its functions -- a dispatch table
    naming them, say -- raise NameError once hoisted above them.

    A comment block sitting directly above a merged statement travels with it.
    The statement's ast span begins at the statement, so merging by span alone
    would drop the rationale off a hoisted constant and penalize the completion
    on C for a comment it did write.

    A `from __future__` import goes above the prologue rather than below it,
    since Python compiles it nowhere else. ast.parse accepts the misplaced
    version -- it defers that check to compile() -- so nothing downstream
    would have reported the file it produced.

    A statement whose every line the spliced file's own prologue already has
    is skipped, so merging into a whole-file completion changes nothing. The
    comparison is against that prologue rather than every line in the file,
    which would let a constant coincide with an indented line inside some
    function body and be dropped as already present.

    A statement that binds exactly the names one of the spliced file's own
    prologue statements binds replaces it in place. Adding it instead would
    define the name twice: a completion that retunes `MAX_LINES = 50` to 100
    would be graded on a file carrying both, so the completion that did the
    right thing reads as the broken one. The completion's leading comments
    replace the starter's only when it wrote some, leaving a starter `why`
    comment standing over a constant whose value alone changed.

    Returns spliced_source unchanged when either side fails to parse or the
    completion's prologue neither adds nor replaces anything.
    """
    try:
        spliced_tree = ast.parse(spliced_source)
        completion_tree = ast.parse(completion_code)
    except SyntaxError:
        return spliced_source

    spliced_lines = spliced_source.splitlines()
    completion_lines = completion_code.splitlines()
    prologue_already_spliced = _prologue_lines(spliced_tree, spliced_lines)
    spliced_spans_by_name = _prologue_spans_by_bound_names(spliced_tree)
    spliced_header_end = _line_after_shebang(spliced_lines)
    completion_header_end = _line_after_shebang(completion_lines)

    future_import_lines: list[str] = []
    added_lines: list[str] = []
    replacements: list[tuple[tuple[int, int], list[str]]] = []
    line_after_last_added = 0
    for node in completion_tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)):
            continue
        statement_lines = _lines_in_span(completion_lines, (node.lineno, node.end_lineno))
        # Judged on the statement's own lines: the spliced file's prologue is
        # read off its ast too, so a comment above a duplicate import is in
        # neither set and would make the import look new.
        if all(
            line.strip() in prologue_already_spliced
            for line in statement_lines
            if line.strip()
        ):
            line_after_last_added = node.end_lineno + 1
            continue
        first_line = _first_line_of_leading_comments(
            completion_lines, node.lineno, completion_header_end
        )
        with_its_comment = _lines_in_span(completion_lines, (first_line, node.end_lineno))
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            future_import_lines.extend(with_its_comment)
            line_after_last_added = node.end_lineno + 1
            continue
        replaced_span = spliced_spans_by_name.get(_bound_names(node))
        if replaced_span is not None:
            replaced_first_line = replaced_span[0]
            if first_line < node.lineno:
                replaced_first_line = _first_line_of_leading_comments(
                    spliced_lines, replaced_first_line, spliced_header_end
                )
            replacements.append(((replaced_first_line, replaced_span[1]), with_its_comment))
            line_after_last_added = node.end_lineno + 1
            continue
        # A blank line the completion left between two of these statements is
        # the grouping its author chose, and the spans alone would run them
        # together. M2 grades layout, so the merge must not invent its own.
        if added_lines and first_line > line_after_last_added:
            added_lines.append("")
        added_lines.extend(with_its_comment)
        line_after_last_added = node.end_lineno + 1

    if not added_lines and not future_import_lines and not replacements:
        return spliced_source

    # Bottom-up, so a replacement that changes a statement's line count has not
    # moved the span of the one above it.
    merged_lines = spliced_lines
    for (first_line, last_line), block in sorted(replacements, reverse=True):
        merged_lines = merged_lines[: first_line - 1] + block + merged_lines[last_line:]

    if not added_lines and not future_import_lines:
        return "\n".join(merged_lines) + "\n"

    # Re-parsed rather than measured off spliced_tree: the replacements above
    # moved every line below the first of them.
    try:
        merged_tree = ast.parse("\n".join(merged_lines))
    except SyntaxError:
        return "\n".join(merged_lines) + "\n"

    if added_lines:
        merged_lines = _inserted_with_blank_lines(
            merged_lines, _line_after_prologue(merged_tree, merged_lines), added_lines
        )
    # Inserted second, and at a line at or above the one the prologue merge
    # used, so the earlier insertion has not moved the index out from under it.
    if future_import_lines:
        merged_lines = _inserted_with_blank_lines(
            merged_lines,
            _line_for_future_import(merged_tree, merged_lines),
            future_import_lines,
        )
    return "\n".join(merged_lines) + "\n"


def starter_for_output_file(scenario: Scenario) -> str | None:
    """The starter the completion is meant to edit -- the one whose basename
    matches output_file. `next(iter(starter_files))` would compare the model
    output against an unrelated starter on any multi-starter scenario, making
    the M3 diff-inflation number meaningless.

    judge.py imports this alongside reconstruct_edited_file so both scoring
    tracks splice a fragment onto the same starter."""
    output_name = Path(scenario.output_file).name
    for relative_path, content in scenario.starter_files.items():
        if Path(relative_path).name == output_name:
            return content
    return None


def _finding_signature(finding: dict) -> tuple[str, str]:
    """A finding's rule id paired with the exact source text that tripped it.
    Two findings share a signature when the same rule fired on the same line,
    which is how an inherited finding is recognised across an edit that has
    already shifted every line number."""
    return finding.get("id", ""), (finding.get("matched") or "").strip()


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip())


def _enclosing_definition_index(lines: list[str], index: int) -> int | None:
    """0-based index of the nearest `def`/`class` line above `index` indented
    less than it -- the definition the line at `index` sits inside -- or None
    when no definition encloses it."""
    ceiling_indent = _indent_width(lines[index])
    for above in range(index - 1, -1, -1):
        candidate = lines[above]
        if not candidate.strip() or _indent_width(candidate) >= ceiling_indent:
            continue
        if candidate.lstrip().startswith(("def ", "class ", "async def ")):
            return above
        ceiling_indent = _indent_width(candidate)
    return None


def _is_top_level_definition(line: str) -> bool:
    return _indent_width(line) == 0 and line.lstrip().startswith(
        ("def ", "class ", "async def ")
    )


def _retained_line_map(starter_source: str, completion_source: str) -> dict[int, int]:
    """Maps a 1-based starter line number to the completion line number holding
    the same content, for every line the edit carried through unchanged and in
    place. Lines the completion deleted, replaced, or added are absent.

    A multi-line `equal` block from difflib is retained wholesale. A lone
    `equal` line is ambiguous: difflib aligns a stray `data = []` between a
    starter function the completion deleted and a brand-new one just as
    readily as it aligns a line an edit stepped around. So a lone line is
    kept only when the definition around it survived -- a lone top-level
    `def`/`class` line stands on its own (difflib matched the whole
    signature), and a lone line deeper in is kept once the `def`/`class`
    above it is known retained. A completion that rewrites a function's body
    around one untouched line keeps that line's inherited finding (issue
    #31); a completion that deletes a function keeps none of it even when a
    common line resurfaces in a replacement (issue #34)."""
    starter_lines = starter_source.splitlines()
    completion_lines = completion_source.splitlines()
    matcher = difflib.SequenceMatcher(a=starter_lines, b=completion_lines, autojunk=False)

    retained: dict[int, int] = {}
    lone_equal_lines: list[tuple[int, int]] = []
    for tag, starter_start, starter_end, completion_start, _ in matcher.get_opcodes():
        if tag != "equal":
            continue
        if starter_end - starter_start >= 2:
            for offset in range(starter_end - starter_start):
                retained[starter_start + offset + 1] = completion_start + offset + 1
        else:
            lone_equal_lines.append((starter_start, completion_start))

    # A lone line inside a lone `def` line is retained only once that `def`
    # itself is, which an earlier pass may not have reached -- hence the fixpoint.
    a_pass_added_a_line = True
    while a_pass_added_a_line:
        a_pass_added_a_line = False
        for starter_index, completion_index in lone_equal_lines:
            starter_line_number = starter_index + 1
            if starter_line_number in retained:
                continue
            enclosing_index = _enclosing_definition_index(starter_lines, starter_index)
            inside_a_retained_definition = (
                enclosing_index is not None and enclosing_index + 1 in retained
            )
            if inside_a_retained_definition or _is_top_level_definition(
                starter_lines[starter_index]
            ):
                retained[starter_line_number] = completion_index + 1
                a_pass_added_a_line = True
    return retained


def findings_introduced(
    completion_findings: list[dict],
    starter_findings: list[dict] | None,
    starter_source: str | None = None,
    completion_source: str | None = None,
) -> list[dict]:
    """`completion_findings` minus the ones the completion inherited unchanged
    from the scenario's starter -- a finding on a line the completion never
    touched sits outside the edit, so M1 must not charge it (issue #31). On an
    edit task the old behaviour rewarded breaching X2/X3: renaming a starter's
    public symbol cleared the finding, leaving it alone kept it.

    With both sources given, a starter finding is inherited only when its line
    survived the edit in place (difflib `equal` block) and the completion has a
    finding with the same rule id and text on the mapped line. A starter
    function the completion deleted takes its findings with it, so a fresh
    violation the completion wrote on a coincidentally identical line still
    counts (issue #34). Without the sources, falls back to matching by
    (rule id, text) as a multiset.

    Returns `completion_findings` unchanged when `starter_findings` is None or
    empty -- a scenario with no starter matching output_file (01, 04, 05, 06,
    08) is unaffected."""
    if not starter_findings:
        return list(completion_findings)

    if starter_source is None or completion_source is None:
        inherited = Counter(_finding_signature(f) for f in starter_findings)
        introduced: list[dict] = []
        for finding in completion_findings:
            signature = _finding_signature(finding)
            if inherited[signature] > 0:
                inherited[signature] -= 1
                continue
            introduced.append(finding)
        return introduced

    retained_line = _retained_line_map(starter_source, completion_source)
    inherited_on_mapped_line: Counter[tuple[str, str, int]] = Counter()
    for finding in starter_findings:
        mapped_line = retained_line.get(finding.get("line"))
        if mapped_line is None:
            continue
        rule_id, matched_text = _finding_signature(finding)
        inherited_on_mapped_line[(rule_id, matched_text, mapped_line)] += 1

    introduced = []
    for finding in completion_findings:
        rule_id, matched_text = _finding_signature(finding)
        key = (rule_id, matched_text, finding.get("line"))
        if inherited_on_mapped_line[key] > 0:
            inherited_on_mapped_line[key] -= 1
            continue
        introduced.append(finding)
    return introduced


_starter_findings_by_scenario: dict[str, list[dict] | None] = {}


def starter_findings_for(scenario: Scenario) -> list[dict] | None:
    """taorc-lint's findings on the starter this completion edits, or None when
    the scenario has no starter matching output_file or the lint subprocess
    failed on it. Cached per scenario -- every completion in a scenario is
    measured against the same starter."""
    if scenario.id in _starter_findings_by_scenario:
        return _starter_findings_by_scenario[scenario.id]
    starter_source = starter_for_output_file(scenario)
    findings = None
    if starter_source is not None:
        findings = run_lint(starter_source, Path(scenario.output_file).suffix)
        if findings is None:
            print(
                f"  WARNING {scenario.id}: taorc-lint failed on the starter file -- "
                "M1 for this scenario will count every finding in each completion, "
                "including any inherited unchanged from the starter",
                file=sys.stderr,
            )
    _starter_findings_by_scenario[scenario.id] = findings
    return findings


def score_completion(scenario: Scenario, completion_path: Path) -> dict:
    completion_text = completion_path.read_text(encoding="utf-8")
    file_extension = Path(scenario.output_file).suffix
    code = extract_code(completion_text, file_extension)
    loc = count_loc(code)
    findings = run_lint(code, file_extension)
    max_depth, mean_depth = nesting_depth(code)

    introduced = None
    if findings is not None:
        introduced = findings_introduced(
            findings,
            starter_findings_for(scenario),
            starter_for_output_file(scenario),
            code,
        )

    findings_per_100_loc = None
    if introduced is not None and loc:
        findings_per_100_loc = round(len(introduced) * 100 / loc, 2)

    metrics = {
        "loc": loc,
        "lint_findings": len(introduced) if introduced is not None else None,
        "lint_findings_total": len(findings) if findings is not None else None,
        "lint_findings_per_100_loc": findings_per_100_loc,
        "comment_to_code_ratio": comment_ratio(code),
        "why_comment_share": why_comment_share(code, findings),
        "max_nesting_depth": max_depth,
        "mean_nesting_depth": mean_depth,
        "empty_word_identifier_count": empty_word_count(code),
    }

    if scenario.measure_diff_size:
        starter_before = starter_for_output_file(scenario)
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


def committed_scorer_version(scores_path: Path) -> int | None:
    """The SCORER_VERSION a run's existing scores.json was written under, 1 for
    one that predates the field, or None when there is no scores.json yet."""
    if not scores_path.is_file():
        return None
    try:
        document = json.loads(scores_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return document.get("scorer_version", 1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run", required=True, help="a run directory produced by run_bench.py")
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="overwrite a scores.json written under an earlier SCORER_VERSION "
        "(its published numbers were scored under a different metric definition)",
    )
    args = parser.parse_args()

    run_dir = Path(args.run)
    if not (run_dir / "raw").is_dir():
        parser.error(f"{run_dir} has no raw/ directory -- run run_bench.py first")

    scores_path = run_dir / "scores.json"
    prior_version = committed_scorer_version(scores_path)
    if prior_version is not None and prior_version < SCORER_VERSION and not args.rescore:
        print(
            f"{scores_path} was scored under scorer_version {prior_version}; this "
            f"scorer is version {SCORER_VERSION}, which redefined a published "
            "metric (see SCORER_VERSION in score.py). Its numbers stand as run -- "
            "pass --rescore to overwrite anyway.",
            file=sys.stderr,
        )
        return 0

    scores = score_run(run_dir)
    guardrail = summarize_guardrail(scores)
    generation_errors = collect_generation_errors(run_dir)

    scores_document = {
        "scorer_version": SCORER_VERSION,
        "scores": scores,
        "guardrail_diff_inflation_pct": guardrail,
        "generation_errors": generation_errors,
    }
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
