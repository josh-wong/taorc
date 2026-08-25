#!/usr/bin/env python3
"""taorc-lint: the deterministic checker for taorc's high-precision rules.

Single-file, stdlib-only CLI (v1-design-doc.md §8). It shells out to
ast-grep for eight of the nine v1 rules and implements the ninth, C1
(comment echoes the code below it), in Python over ast-grep's comment-node
JSON, since C1 is a scored comparison rather than a pattern match.

If ast-grep is not on PATH, this prints an install hint and exits 0 -- it
never blocks a build over a missing optional tool.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple

SCRIPT_DIR = Path(__file__).resolve().parent
SGCONFIG_PATH = SCRIPT_DIR / "sgconfig.yml"

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
}

# The severity a catalog rule actually carries (catalog/rules.yaml). ast-grep
# has no "suggestion" level of its own, so its rule files all declare
# "warning" and this table is what corrects C4 and N11 back to the severity
# the catalog -- and the review checklist -- agree on.
CATALOG_SEVERITY = {
    "C1": "warning",
    "C4": "suggestion",
    "N1": "warning",
    "N3": "warning",
    "N11": "suggestion",
    "S7": "warning",
    "T3": "warning",
    "X7": "warning",
    "X8": "warning",
}

CATALOG_SLUG = {
    "C1": "dont-restate-the-code",
    "C4": "flag-known-flaws-with-markers",
    "N1": "specific-over-vague-words",
    "N3": "encode-units-and-formats-in-names",
    "N11": "avoid-negated-boolean-names",
    "S7": "delete-code-that-cannot-change-the-outcome",
    "T3": "name-tests-for-situation-and-outcome",
    "X7": "do-not-narrate-your-plan-in-comments",
    "X8": "no-banners-dividers-or-emoji",
}

SEVERITY_RANK = {"suggestion": 0, "warning": 1, "error": 2}

# taorc-c1-comment-echoes-code-python -> C1
LINT_RULE_ID_FROM_MESSAGE = re.compile(r"^\[([A-Z]+\d+)\]")

COMMENT_PREFIX = re.compile(r"^\s*(#|//)")

SUPPRESSION = re.compile(
    r"(?:#|//)\s*taorc-ignore(?P<next>-next)?\s*:?\s*"
    r"(?P<ids>[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*)?"
    r"(?:\s*(?:—|--)\s*(?P<reason>.+))?\s*$"
)

C1_STOPWORDS = {
    "the",
    "a",
    "an",
    "this",
    "that",
    "to",
    "of",
    "and",
    "or",
    "then",
    "we",
    "it",
    "is",
    "are",
    "in",
    "on",
    "for",
    "with",
    "through",
    "each",
    "all",
}
C1_NARRATION_VERBS = {
    "loop",
    "iterate",
    "increment",
    "decrement",
    "set",
    "get",
    "create",
    "initialize",
    "return",
    "call",
    "check",
    "add",
    "remove",
    "update",
    "build",
    "make",
    "do",
}
C1_MATCH_THRESHOLD = 0.8
WORD_PATTERN = re.compile(r"[A-Za-z]+")
STEM_SUFFIXES = ("ing", "es", "ed", "er", "s")


class Finding(NamedTuple):
    id: str
    severity: str
    file: str
    line: int
    col: int
    title: str
    matched: str
    fix: str


def find_ast_grep() -> str | None:
    return shutil.which("ast-grep") or shutil.which("sg")


@lru_cache(maxsize=None)
def _read_source(file: str) -> str:
    """Reads a target file once and shares the result across every check
    that needs it (C1 scoring, N1's short-function exclusion, suppression
    collection), instead of each one re-reading the same file from disk."""
    try:
        return Path(file).read_text(encoding="utf-8")
    except OSError:
        return ""


@lru_cache(maxsize=None)
def _read_lines(file: str) -> list[str]:
    return _read_source(file).splitlines()


def stem(word: str) -> str:
    for suffix in STEM_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            word = word[: -len(suffix)]
            break
    if word.endswith("e") and len(word) >= 3:
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    tokens = []
    for word in WORD_PATTERN.findall(text):
        # Split camelCase (snake_case already breaks apart at the regex
        # above, since underscores aren't word characters).
        for part in re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+", word):
            tokens.append(part.lower())
    return tokens


def c1_fires(comment_text: str, statement_text: str) -> bool:
    """The algorithm specified in v1-design-doc.md §8.2.1."""
    content = [t for t in tokenize(comment_text) if t not in C1_STOPWORDS]
    if len(content) < 2:
        return False
    content = [t for t in content if t not in C1_NARRATION_VERBS]
    if not content:
        return False
    stemmed_comment = [stem(t) for t in content]
    statement_tokens = {stem(t) for t in tokenize(statement_text)}
    matched = sum(1 for t in stemmed_comment if t in statement_tokens)
    return (matched / len(stemmed_comment)) >= C1_MATCH_THRESHOLD


def next_statement_line_index(lines: list[str], comment_line_index: int) -> int | None:
    """0-based index of the next non-blank, non-comment line after comment_line_index."""
    for offset, line in enumerate(lines[comment_line_index + 1 :], start=1):
        stripped = line.strip()
        if not stripped or COMMENT_PREFIX.match(line):
            continue
        return comment_line_index + offset
    return None


def next_statement_line(lines: list[str], comment_line_index: int) -> str | None:
    index = next_statement_line_index(lines, comment_line_index)
    return lines[index].strip() if index is not None else None


N1_SHORT_FUNCTION_LINES = 5


def short_python_function_ranges(source: str) -> list[tuple[int, int]]:
    """Line ranges of Python functions under N1_SHORT_FUNCTION_LINES lines.

    N1 excludes them (v1-design-doc.md §8.2's word-list note): a vague name
    in a function this short is visible in its entirety at the call site,
    so it doesn't cost a reader the lookup the rule exists to save. There
    is no equivalent stdlib parser for TypeScript, so this exclusion only
    narrows the Python side of N1.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    ranges = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            span = node.end_lineno - node.lineno + 1
            if span < N1_SHORT_FUNCTION_LINES:
                ranges.append((node.lineno, node.end_lineno))
    return ranges


def drop_n1_in_short_python_functions(findings: list[Finding]) -> list[Finding]:
    ranges_by_file: dict[str, list[tuple[int, int]]] = {}
    kept = []
    for f in findings:
        if f.id != "N1" or not f.file.endswith(".py"):
            kept.append(f)
            continue
        if f.file not in ranges_by_file:
            ranges_by_file[f.file] = short_python_function_ranges(_read_source(f.file))
        if any(start <= f.line <= end for start, end in ranges_by_file[f.file]):
            continue
        kept.append(f)
    return kept


def run_ast_grep(ast_grep_bin: str, paths: list[Path]) -> list[dict[str, Any]]:
    if not paths:
        return []
    completed = subprocess.run(
        [ast_grep_bin, "scan", "--config", str(SGCONFIG_PATH), "--json", *[str(p) for p in paths]],
        capture_output=True,
        text=True,
        check=False,
    )
    if not completed.stdout.strip():
        return []
    return json.loads(completed.stdout)


def catalog_id_from_match(match: dict[str, Any]) -> str | None:
    found = LINT_RULE_ID_FROM_MESSAGE.match(match.get("message", ""))
    return found.group(1) if found else None


def title_from_match(match: dict[str, Any]) -> str:
    return LINT_RULE_ID_FROM_MESSAGE.sub("", match.get("message", "")).strip()


def build_findings(matches: list[dict[str, Any]]) -> tuple[list[Finding], list[dict[str, Any]]]:
    """Split raw ast-grep matches into ordinary findings and C1 candidates.

    C1's extraction rule matches every comment (it has to -- deciding fire
    or no-fire needs the scoring algorithm, not a pattern), so its matches
    are returned separately for c1 scoring rather than turned into findings
    directly.
    """
    findings: list[Finding] = []
    c1_candidates: list[dict[str, Any]] = []

    for match in matches:
        catalog_id = catalog_id_from_match(match)
        if catalog_id is None:
            continue
        if catalog_id == "C1":
            c1_candidates.append(match)
            continue
        if catalog_id not in CATALOG_SEVERITY:
            raise KeyError(
                f"{catalog_id} has an ast-grep rule but no entry in CATALOG_SEVERITY"
            )

        start = match["range"]["start"]
        findings.append(
            Finding(
                id=catalog_id,
                severity=CATALOG_SEVERITY[catalog_id],
                file=match["file"],
                line=start["line"] + 1,
                col=start["column"] + 1,
                title=title_from_match(match),
                matched=match["lines"].strip(),
                fix=(match.get("note") or "").strip(),
            )
        )

    return findings, c1_candidates


def score_c1_candidates(c1_candidates: list[dict[str, Any]]) -> list[Finding]:
    findings = []

    for match in c1_candidates:
        file = match["file"]
        if not COMMENT_PREFIX.match(match["lines"]):
            continue  # a trailing comment on a code line, not a standalone one
        if SUPPRESSION.search(match["lines"]):
            continue  # a suppression directive, not code narration

        lines = _read_lines(file)
        if not lines:
            continue

        start = match["range"]["start"]
        statement = next_statement_line(lines, start["line"])
        if statement is None:
            continue
        if not c1_fires(match["lines"], statement):
            continue

        findings.append(
            Finding(
                id="C1",
                severity=CATALOG_SEVERITY["C1"],
                file=file,
                line=start["line"] + 1,
                col=start["column"] + 1,
                title="Comment echoes the code below it",
                matched=match["lines"].strip(),
                fix="delete the comment; the code already says this",
            )
        )

    return findings


def collect_suppressions(paths: set[str]) -> tuple[dict[tuple[str, int, str], str], list[Finding]]:
    """Maps (file, line, rule_id) -> reason for every valid suppression, and
    returns a finding for every suppression comment missing a reason."""
    resolved: dict[tuple[str, int, str], str] = {}
    malformed: list[Finding] = []

    for file in paths:
        lines = _read_lines(file)
        if not lines:
            continue
        for index, line in enumerate(lines):
            match = SUPPRESSION.search(line)
            if not match:
                continue
            ids = match.group("ids")
            if not ids:
                continue  # a bare taorc-ignore suppresses nothing
            reason = (match.group("reason") or "").strip()
            if match.group("next"):
                statement_index = next_statement_line_index(lines, index)
                target_line = statement_index + 1 if statement_index is not None else index + 2
            else:
                target_line = index + 1
            if not reason:
                malformed.append(
                    Finding(
                        id="taorc-lint",
                        severity="warning",
                        file=file,
                        line=index + 1,
                        col=1,
                        title="Suppression missing a reason",
                        matched=line.strip(),
                        fix="add a reason after the rule id, e.g. "
                        "`taorc-ignore: N1 — why this is fine`",
                    )
                )
                continue
            for rule_id in (i.strip() for i in ids.split(",")):
                resolved[(file, target_line, rule_id)] = reason

    return resolved, malformed


def apply_suppressions(
    findings: list[Finding], suppressions: dict[tuple[str, int, str], str]
) -> tuple[list[Finding], list[tuple[Finding, str]]]:
    kept = []
    suppressed = []
    for finding in findings:
        reason = suppressions.get((finding.file, finding.line, finding.id))
        if reason is not None:
            suppressed.append((finding, reason))
        else:
            kept.append(finding)
    return kept, suppressed


def changed_files() -> list[Path]:
    for base in ("origin/main", "main", "origin/master", "master"):
        merge_base = subprocess.run(
            ["git", "merge-base", "HEAD", base], capture_output=True, text=True, check=False
        )
        if merge_base.returncode == 0:
            break
    else:
        print("taorc-lint: could not find a merge base against main/master", file=sys.stderr)
        return []

    diff = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=d", merge_base.stdout.strip()],
        capture_output=True,
        text=True,
        check=False,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=False,
    )
    names = set(diff.stdout.splitlines()) | set(untracked.stdout.splitlines())
    return [
        Path(name)
        for name in names
        if Path(name).suffix in LANGUAGE_BY_SUFFIX and Path(name).exists()
    ]


def collect_target_files(paths: list[str], use_changed: bool) -> list[Path]:
    if use_changed:
        return changed_files()

    targets: list[Path] = []
    for raw in paths or ["."]:
        path = Path(raw)
        if path.is_dir():
            for suffix in LANGUAGE_BY_SUFFIX:
                targets.extend(path.rglob(f"*{suffix}"))
        elif path.suffix in LANGUAGE_BY_SUFFIX:
            targets.append(path)
    return targets


def format_text(findings: list[Finding]) -> str:
    lines = []
    for f in findings:
        lines.append(f"[{f.id}] {f.file}:{f.line}  {f.title}")
        lines.append(f"  {f.matched}")
        lines.append(f"  → {f.fix}")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    return json.dumps(
        [
            {
                "id": f.id,
                "slug": CATALOG_SLUG.get(f.id, ""),
                "severity": f.severity,
                "file": f.file,
                "line": f.line,
                "col": f.col,
                "title": f.title,
                "matched": f.matched,
                "fix": f.fix,
            }
            for f in findings
        ],
        indent=2,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint code against taorc's lintable rules.")
    parser.add_argument("paths", nargs="*", help="files or directories to scan")
    parser.add_argument(
        "--changed", action="store_true", help="lint files changed vs. the merge base"
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument(
        "--severity", choices=["suggestion", "warning", "error"], default="suggestion"
    )
    parser.add_argument("--rules", help="comma-separated subset of rule ids, e.g. C1,N3")
    parser.add_argument("--show-suppressed", action="store_true")
    parser.add_argument("--fail-on", choices=["suggestion", "warning", "error"], default=None)
    args = parser.parse_args()

    ast_grep_bin = find_ast_grep()
    if ast_grep_bin is None:
        print(
            "taorc-lint: ast-grep is not on PATH. Install it (e.g. `brew install "
            "ast-grep` or `pip install ast-grep-cli`) to run taorc-lint. Skipping.",
            file=sys.stderr,
        )
        return 0

    target_files = collect_target_files(args.paths, args.changed)
    if not target_files:
        return 0

    matches = run_ast_grep(ast_grep_bin, target_files)
    findings, c1_candidates = build_findings(matches)
    findings += score_c1_candidates(c1_candidates)
    findings = drop_n1_in_short_python_functions(findings)

    suppressions, malformed = collect_suppressions({str(p) for p in target_files})
    findings, suppressed = apply_suppressions(findings, suppressions)
    findings += malformed

    if args.rules:
        wanted = {r.strip() for r in args.rules.split(",")}
        findings = [f for f in findings if f.id in wanted]

    min_rank = SEVERITY_RANK[args.severity]
    findings = [f for f in findings if SEVERITY_RANK[f.severity] >= min_rank]
    findings.sort(key=lambda f: (f.file, f.line))

    if args.format == "json":
        print(format_json(findings))
    else:
        rendered = format_text(findings)
        if rendered:
            print(rendered)
        if args.show_suppressed:
            for finding, reason in suppressed:
                print(f"[{finding.id}] {finding.file}:{finding.line}  suppressed — {reason}")

    if args.fail_on is not None:
        fail_rank = SEVERITY_RANK[args.fail_on]
        if any(SEVERITY_RANK[f.severity] >= fail_rank for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
