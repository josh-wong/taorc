#!/usr/bin/env python3
"""The CI validation gate (v1-design-doc.md §9).

Checks whose subject does not exist yet are skipped rather than failed, so
this runs clean against a tree partway through the milestones — the
installer/placement-matrix tests (no installers until MS5) are not
implemented here for that reason.

check_lint_fixtures (MS4) follows the same skip-don't-fail rule for a
different reason: taorc_lint.py itself degrades gracefully when ast-grep
isn't on PATH (§8.1), so a CI environment without it should see this gate
skip the same checks taorc-lint would, not fail on a tool it never had.

Skill-spec validation is partial rather than absent. §9 specifies
`skills-ref validate`, an external tool this gate does not shell out to;
check_skill_spec covers the stdlib-checkable half instead. See its docstring
for what that leaves to the external tool.

The catalog itself is not among them. It has been required to be schema-valid
since MS2 gave it a mandatory 'precedence' block, so the empty catalog that
MS0's gate ran against no longer passes -- which is the intended outcome, as
a catalog with no tiebreakers cannot resolve a conflict between two rules.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import yaml
from build import AGENT_BLOCK_TOKEN_BUDGET, BLOCK_BEGIN, render_managed_block
from lib import (
    CATEGORY_PREFIXES,
    REPO_ROOT,
    RULE_ID_PREFIX_CLASS,
    count_tokens,
    find_rule_ids,
    load_catalog,
    read_manifest_version,
    read_version,
)

# templates/agent-block.md's budget is imported from build.py rather than
# duplicated here, so the two scripts can't drift onto different limits.
BUDGETS = {
    "skills/readable-code/SKILL.md": 5000,
    "templates/agent-block.md": AGENT_BLOCK_TOKEN_BUDGET,
    "prompts/system-prompt.md": 800,
    "prompts/system-prompt-mini.md": 150,
}

SKILL_MD_LINE_LIMIT = 500

# The Agent Skills spec caps a skill description at 1024 characters. It is the
# field that decides whether the skill fires at all (PRD M4), so an overrun
# that a harness silently truncates would cost triggers, not just tidiness.
SKILL_DESCRIPTION_LIMIT = 1024

# Files that legitimately cite rule IDs; everything else under these roots is
# scanned for referential integrity against catalog/rules.yaml.
CITATION_ROOTS = ["skills/readable-code", "prompts", "templates", "evals"]


def check_schema(catalog: dict) -> list[str]:
    schema = json.loads((REPO_ROOT / "catalog" / "schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"catalog/rules.yaml: {e.message} (at {list(e.path)})"
        for e in validator.iter_errors(catalog)
    ]


def check_schema_prefix_sync() -> list[str]:
    """catalog/schema.json hardcodes its own copy of the rule-ID prefix class
    (it can't import RULE_ID_PREFIX_CLASS, being plain JSON); catch drift
    between the two here instead of letting them silently diverge."""
    schema = json.loads((REPO_ROOT / "catalog" / "schema.json").read_text(encoding="utf-8"))
    id_pattern = schema["$defs"]["rule"]["properties"]["id"]["pattern"]
    match = re.match(r"\^\[([A-Z]+)\]", id_pattern)
    if not match:
        return [
            f"catalog/schema.json: id pattern {id_pattern!r} is not in the expected ^[...] form"
        ]
    schema_prefixes = "".join(sorted(match.group(1)))
    lib_prefixes = "".join(sorted(RULE_ID_PREFIX_CLASS))
    if schema_prefixes != lib_prefixes:
        return [
            (
                f"catalog/schema.json: id pattern prefixes {schema_prefixes!r} do not match "
                f"lib.CATEGORY_PREFIXES {lib_prefixes!r}"
            )
        ]
    return []


def check_id_consistency(catalog: dict) -> list[str]:
    errors = []
    all_ids = {rule["id"] for rule in catalog["rules"]}
    seen_ids: set[str] = set()

    for rule in catalog["rules"]:
        rule_id = rule["id"]
        if rule_id in seen_ids:
            errors.append(f"catalog/rules.yaml: duplicate rule id {rule_id}")
        seen_ids.add(rule_id)

        prefix = re.match(r"[A-Z]+", rule_id).group()
        expected_prefix = CATEGORY_PREFIXES.get(rule["category"])
        if expected_prefix and prefix != expected_prefix:
            errors.append(
                f"catalog/rules.yaml: {rule_id} has category {rule['category']!r} "
                f"(expects prefix {expected_prefix!r}, got {prefix!r})"
            )

        if rule.get("deprecated") and rule.get("superseded_by") not in all_ids:
            errors.append(
                f"catalog/rules.yaml: {rule_id} superseded_by "
                f"{rule.get('superseded_by')!r} is not a known rule id"
            )
    return errors


def check_lint_rule_files(catalog: dict) -> list[str]:
    errors = []
    rules_dir = REPO_ROOT / "skills" / "readable-code" / "scripts" / "rules"
    for rule in catalog["rules"]:
        if not rule.get("lintable"):
            continue
        lint_rule = rule["lint_rule"]
        matches = list(rules_dir.glob(f"*/{lint_rule}.yml")) if rules_dir.exists() else []
        if not matches:
            errors.append(
                f"catalog/rules.yaml: {rule['id']} names lint_rule {lint_rule!r}, "
                f"no matching file under skills/readable-code/scripts/rules/*/"
            )
    return errors


LINT_SCRIPT = REPO_ROOT / "skills" / "readable-code" / "scripts" / "taorc_lint.py"
FIXTURE_EXTENSION_BY_LANGUAGE = {"python": ".py", "typescript": ".ts"}


def check_lint_fixtures(catalog: dict) -> list[str]:
    """§9 item 7: every lintable rule's fixtures must produce the finding set
    PRD R6.4 requires -- the positive fixture fires, the negative one (the
    false-positive suite M5 is measured against) does not.

    Every existing fixture is checked in a single taorc_lint.py invocation
    (findings are grouped back to their fixture by the "file" field in the
    JSON output) rather than one subprocess per rule/kind/language -- with 9
    lintable rules x 2 kinds x 2 languages, a separate spawn per combination
    would mean 36 sequential process starts (each paying interpreter
    startup and an ast-grep PATH lookup) that only grow as more rules become
    lintable.

    Skipped, not failed, when ast-grep isn't on PATH; see this module's
    docstring for why that differs from every other check here.
    """
    if shutil.which("ast-grep") is None and shutil.which("sg") is None:
        return []

    errors = []
    fixtures_root = REPO_ROOT / "lint" / "fixtures"

    expected: list[tuple[Path, str, str]] = []
    for rule in catalog["rules"]:
        if not rule.get("lintable"):
            continue
        rule_id = rule["id"]
        fixture_name = rule_id.lower()

        for kind in ("positive", "negative"):
            for language, extension in FIXTURE_EXTENSION_BY_LANGUAGE.items():
                fixture = fixtures_root / kind / language / f"{fixture_name}{extension}"
                if not fixture.exists():
                    errors.append(
                        f"lint/fixtures/{kind}/{language}/{fixture_name}{extension}: "
                        f"missing fixture for {rule_id}"
                    )
                    continue
                expected.append((fixture, rule_id, kind))

    if not expected:
        return errors

    completed = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--format", "json", *(str(f) for f, _, _ in expected)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        errors.append(
            f"lint/fixtures: taorc_lint.py exited with status "
            f"{completed.returncode} ({completed.stderr.strip()})"
        )
        return errors
    try:
        findings = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        errors.append(
            f"lint/fixtures: taorc_lint.py did not produce valid JSON "
            f"({completed.stderr.strip()})"
        )
        return errors

    fired_ids_by_file: dict[str, set[str]] = {}
    for finding in findings:
        fired_ids_by_file.setdefault(finding["file"], set()).add(finding["id"])

    for fixture, rule_id, kind in expected:
        rel = fixture.relative_to(REPO_ROOT)
        fired = rule_id in fired_ids_by_file.get(str(fixture), set())
        if kind == "positive" and not fired:
            errors.append(f"{rel}: expected {rule_id} to fire here, but it did not")
        if kind == "negative" and fired:
            errors.append(f"{rel}: {rule_id} fired on a fixture that must not trigger it")

    return errors


SUPPRESSION_FIXTURES_ROOT = REPO_ROOT / "lint" / "fixtures" / "suppression"


def check_suppression_fixtures() -> list[str]:
    """taorc-ignore/-next suppression parsing (taorc_lint.py's
    collect_suppressions/apply_suppressions) has no coverage under
    check_lint_fixtures, since that loop only ever generates fixtures named
    after a catalog rule id and none of them contain a suppression comment.
    Runs a handful of dedicated fixtures under lint/fixtures/suppression/ and
    asserts each behaves as its filename promises, so a regression in the
    -next line-offset math or malformed-reason detection fails CI instead of
    shipping silently.

    Skipped, not failed, when ast-grep isn't on PATH -- see check_lint_fixtures.
    """
    if shutil.which("ast-grep") is None and shutil.which("sg") is None:
        return []

    errors = []
    suppressed_cases = [
        "same_line.py",
        "next_line.py",
        "next_line_blank_gap.py",
        "next_line_comment_gap.py",
    ]
    for filename in suppressed_cases:
        fixture = SUPPRESSION_FIXTURES_ROOT / filename
        if not fixture.exists():
            errors.append(f"lint/fixtures/suppression/{filename}: missing fixture")
            continue

        completed = subprocess.run(
            [sys.executable, str(LINT_SCRIPT), "--rules", "N1", "--format", "json", str(fixture)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            errors.append(
                f"lint/fixtures/suppression/{filename}: taorc_lint.py exited "
                f"with status {completed.returncode} ({completed.stderr.strip()})"
            )
            continue
        try:
            findings = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError:
            errors.append(
                f"lint/fixtures/suppression/{filename}: taorc_lint.py did not "
                f"produce valid JSON ({completed.stderr.strip()})"
            )
            continue

        if findings:
            errors.append(
                f"lint/fixtures/suppression/{filename}: expected N1 to be "
                f"suppressed here, but it fired"
            )

    fixture = SUPPRESSION_FIXTURES_ROOT / "missing_reason.py"
    if not fixture.exists():
        errors.append("lint/fixtures/suppression/missing_reason.py: missing fixture")
        return errors

    completed = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--format", "json", str(fixture)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        errors.append(
            f"lint/fixtures/suppression/missing_reason.py: taorc_lint.py "
            f"exited with status {completed.returncode} ({completed.stderr.strip()})"
        )
        return errors
    try:
        findings = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        errors.append(
            f"lint/fixtures/suppression/missing_reason.py: taorc_lint.py did "
            f"not produce valid JSON ({completed.stderr.strip()})"
        )
        return errors

    ids = {f["id"] for f in findings}
    if "N1" not in ids:
        errors.append(
            "lint/fixtures/suppression/missing_reason.py: expected N1 to "
            "still fire, since its suppression comment has no reason"
        )
    if "taorc-lint" not in ids:
        errors.append(
            "lint/fixtures/suppression/missing_reason.py: expected a "
            "taorc-lint finding flagging the missing reason"
        )

    return errors


def check_referential_integrity(catalog: dict) -> list[str]:
    errors = []
    known_ids = {rule["id"] for rule in catalog["rules"]}

    for root_name in CITATION_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for md_file in root.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            cited = find_rule_ids(text)
            unknown = cited - known_ids
            if unknown:
                rel = md_file.relative_to(REPO_ROOT)
                errors.append(f"{rel}: cites unknown rule id(s) {sorted(unknown)}")

    skill_md = REPO_ROOT / "skills" / "readable-code" / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8")
        cited = find_rule_ids(text)
        missing = {r["id"] for r in catalog["rules"] if not r.get("deprecated")} - cited
        if missing:
            errors.append(
                f"skills/readable-code/SKILL.md: missing catalog rule id(s) {sorted(missing)}"
            )

    return errors


def check_linter_referential_integrity(catalog: dict) -> list[str]:
    """AGENTS.md: any ID cited in "SKILL.md, a reference file, the linter, or
    an eval scorer" must already exist in the catalog. check_referential_integrity
    only walks *.md files, so a stale or typo'd id inside taorc_lint.py's
    CATALOG_SEVERITY/CATALOG_SLUG dicts, or inside an ast-grep rule .yml's
    message, would otherwise pass CI silently.
    """
    errors = []
    known_ids = {rule["id"] for rule in catalog["rules"]}

    if LINT_SCRIPT.exists():
        text = LINT_SCRIPT.read_text(encoding="utf-8")
        cited = set(re.findall(rf'"([{RULE_ID_PREFIX_CLASS}][0-9]+)"\s*:', text))
        unknown = cited - known_ids
        if unknown:
            rel = LINT_SCRIPT.relative_to(REPO_ROOT)
            errors.append(f"{rel}: cites unknown rule id(s) {sorted(unknown)}")

    rules_dir = REPO_ROOT / "skills" / "readable-code" / "scripts" / "rules"
    if rules_dir.exists():
        for yml_file in sorted(rules_dir.rglob("*.yml")):
            text = yml_file.read_text(encoding="utf-8")
            cited = set(re.findall(rf'\[([{RULE_ID_PREFIX_CLASS}][0-9]+)\]', text))
            unknown = cited - known_ids
            if unknown:
                rel = yml_file.relative_to(REPO_ROOT)
                errors.append(f"{rel}: cites unknown rule id(s) {sorted(unknown)}")

    return errors


def extract_dict_literal(text: str, name: str) -> dict[str, str]:
    """Reads a top-level `NAME = {"key": "value", ...}` string->string dict
    literal out of source text via regex, without importing or executing the
    module it came from -- so a sync check that reads taorc_lint.py can't be
    taken down (or made to silently run unrelated code) by an unrelated
    change to that script's imports or top-level statements.
    """
    match = re.search(rf"^{name} = \{{(.*?)\n\}}", text, re.DOTALL | re.MULTILINE)
    if not match:
        return {}
    return dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', match.group(1)))


def check_lint_severity_sync(catalog: dict) -> list[str]:
    """v1-design-doc.md §8.2 claims "§3.1 requires the two to agree and CI
    asserts it" for catalog vs. linter severity. Rule .yml files hardcode
    severity: warning (ast-grep has no "suggestion" level -- see
    taorc_lint.py's CATALOG_SEVERITY comment), so the only place severity can
    actually drift from the catalog is that table; this reads it and diffs it
    against catalog/rules.yaml.
    """
    errors = []
    if not LINT_SCRIPT.exists():
        return errors

    text = LINT_SCRIPT.read_text(encoding="utf-8")
    linter_severity_by_id = extract_dict_literal(text, "CATALOG_SEVERITY")

    for rule in catalog["rules"]:
        if not rule.get("lintable"):
            continue
        rule_id = rule["id"]
        linter_severity = linter_severity_by_id.get(rule_id)
        if linter_severity is None:
            errors.append(
                f"skills/readable-code/scripts/taorc_lint.py: CATALOG_SEVERITY "
                f"is missing lintable rule {rule_id}"
            )
        elif linter_severity != rule["severity"]:
            errors.append(
                f"skills/readable-code/scripts/taorc_lint.py: CATALOG_SEVERITY[{rule_id!r}] "
                f"is {linter_severity!r}, catalog/rules.yaml says {rule['severity']!r}"
            )
    return errors


def check_lint_slug_sync(catalog: dict) -> list[str]:
    """taorc_lint.py's CATALOG_SLUG hand-duplicates each lintable rule's slug
    from catalog/rules.yaml (it's shipped in every --format json finding),
    but unlike CATALOG_SEVERITY it had no sync check -- a slug renamed in the
    catalog could drift out of the linter's JSON output with CI staying
    green. Mirrors check_lint_severity_sync.
    """
    errors = []
    if not LINT_SCRIPT.exists():
        return errors

    text = LINT_SCRIPT.read_text(encoding="utf-8")
    linter_slug_by_id = extract_dict_literal(text, "CATALOG_SLUG")

    for rule in catalog["rules"]:
        if not rule.get("lintable"):
            continue
        rule_id = rule["id"]
        linter_slug = linter_slug_by_id.get(rule_id)
        if linter_slug is None:
            errors.append(
                f"skills/readable-code/scripts/taorc_lint.py: CATALOG_SLUG "
                f"is missing lintable rule {rule_id}"
            )
        elif linter_slug != rule["slug"]:
            errors.append(
                f"skills/readable-code/scripts/taorc_lint.py: CATALOG_SLUG[{rule_id!r}] "
                f"is {linter_slug!r}, catalog/rules.yaml says {rule['slug']!r}"
            )
    return errors


def check_lint_language_extension_sync() -> list[str]:
    """LANGUAGE_BY_SUFFIX (taorc_lint.py) and FIXTURE_EXTENSION_BY_LANGUAGE
    (this module, above) independently hand-encode the same language<->
    extension mapping with no shared source, so adding a lintable language or
    extension to one and not the other would silently point check_lint_fixtures
    at files taorc-lint never scans, or vice versa. Diffs them here.
    """
    errors = []
    if not LINT_SCRIPT.exists():
        return errors

    text = LINT_SCRIPT.read_text(encoding="utf-8")
    linter_language_by_suffix = extract_dict_literal(text, "LANGUAGE_BY_SUFFIX")

    for language, extension in FIXTURE_EXTENSION_BY_LANGUAGE.items():
        linter_language = linter_language_by_suffix.get(extension)
        if linter_language != language:
            errors.append(
                f"scripts/validate.py: FIXTURE_EXTENSION_BY_LANGUAGE[{language!r}] is "
                f"{extension!r}, but taorc_lint.py's LANGUAGE_BY_SUFFIX[{extension!r}] "
                f"is {linter_language!r}"
            )
    return errors


def check_budgets(version: str) -> list[str]:
    errors = []
    for relative_path, budget in BUDGETS.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        # The agent-block template is measured as build.py renders it (with
        # its begin/end markers) so the two scripts check the same content.
        is_agent_block = relative_path == "templates/agent-block.md"
        measured_text = render_managed_block(version, text) if is_agent_block else text
        tokens = count_tokens(measured_text)
        if tokens > budget:
            errors.append(f"{relative_path}: {tokens} tokens exceeds budget of {budget}")
        if relative_path.endswith("SKILL.md"):
            line_count = len(text.splitlines())
            if line_count > SKILL_MD_LINE_LIMIT:
                errors.append(
                    f"{relative_path}: {line_count} lines exceeds limit of {SKILL_MD_LINE_LIMIT}"
                )
    return errors


def check_version_sync(version: str) -> list[str]:
    errors = []

    for manifest_path in [
        REPO_ROOT / ".claude-plugin" / "plugin.json",
        REPO_ROOT / ".claude-plugin" / "marketplace.json",
        REPO_ROOT / ".codex-plugin" / "plugin.json",
        REPO_ROOT / "gemini-extension.json",
    ]:
        if not manifest_path.exists():
            continue
        current_version = read_manifest_version(manifest_path)
        if current_version != version:
            rel = manifest_path.relative_to(REPO_ROOT)
            errors.append(
                f"{rel}: version {current_version!r} does not match VERSION ({version!r})"
            )

    # Derived from build.BLOCK_BEGIN so the two never drift apart.
    marker_pattern = re.compile(re.escape(BLOCK_BEGIN).replace(r"\{version\}", r"([\d.]+)"))
    for relative_path in [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".github/instructions/readable-code.instructions.md",
        ".cursor/rules/readable-code.mdc",
        ".clinerules/readable-code.md",
        ".windsurf/rules/readable-code.md",
    ]:
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in marker_pattern.finditer(text):
            if match.group(1) != version:
                errors.append(
                    f"{relative_path}: managed block marker version {match.group(1)!r} "
                    f"does not match VERSION ({version!r})"
                )

    return errors


def _parse_frontmatter(text: str) -> dict | None:
    """The YAML frontmatter block, or None if the file has no well-formed one.

    Malformed YAML returns None rather than propagating: this gate's job is to
    report what is wrong with the file, and a traceback out of here would take
    down the checks that run after it as well.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end == -1:
        return None
    try:
        parsed = yaml.safe_load(text[4 : end + 1])
    except yaml.YAMLError:
        return None
    return parsed if isinstance(parsed, dict) else None


def check_skill_spec(version: str) -> list[str]:
    """The parts of §9's skill-spec check that need no external tool.

    `skills-ref validate` covers the full Agent Skills spec and is not run
    here; what this adds is the half that is cheap and that CI would otherwise
    never see -- that the frontmatter parses, that 'name' matches the directory
    (the spec requires it, and an installer that resolves a skill by directory
    would silently install one named something else), that the description is a
    string within the spec's length limit, that metadata.version tracks VERSION,
    and that every reference SKILL.md points at actually exists. A dangling
    pointer costs an agent a failed read at the exact moment it decided it
    needed the file.
    """
    errors = []
    skill_dir = REPO_ROOT / "skills" / "readable-code"
    skill_md = skill_dir / "SKILL.md"
    # A hard error, not a milestone skip. The file has existed since MS3, and
    # check_budgets also skips a missing path -- so treating its absence as
    # "nothing to check" would let a deleted or renamed skill directory take
    # the token and line budgets down with it, silently, on a green run.
    if not skill_md.exists():
        return ["skills/readable-code/SKILL.md: missing"]

    text = skill_md.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    if frontmatter is None:
        return ["skills/readable-code/SKILL.md: no parseable YAML frontmatter"]

    name = frontmatter.get("name")
    if name != skill_dir.name:
        errors.append(
            f"skills/readable-code/SKILL.md: name {name!r} does not match "
            f"directory name {skill_dir.name!r}"
        )

    description = frontmatter.get("description")
    if not description:
        errors.append("skills/readable-code/SKILL.md: frontmatter has no description")
    elif not isinstance(description, str):
        # An unquoted description that parses as a number or a list is still a
        # broken description; say so rather than raising on len().
        errors.append(
            f"skills/readable-code/SKILL.md: description parsed as "
            f"{type(description).__name__}, not a string"
        )
    elif len(description) > SKILL_DESCRIPTION_LIMIT:
        errors.append(
            f"skills/readable-code/SKILL.md: description is {len(description)} characters, "
            f"over the {SKILL_DESCRIPTION_LIMIT}-character spec limit"
        )

    # Nothing else covers this. check_version_sync reads the four manifests and
    # the managed-block markers, and build.py never writes SKILL.md, so without
    # this a VERSION bump leaves the shipped skill advertising the old one.
    metadata = frontmatter.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append(
            f"skills/readable-code/SKILL.md: metadata parsed as "
            f"{type(metadata).__name__}, not a mapping"
        )
    else:
        skill_version = (metadata or {}).get("version")
        if skill_version != version:
            errors.append(
                f"skills/readable-code/SKILL.md: metadata.version {skill_version!r} "
                f"does not match VERSION ({version!r})"
            )

    for reference in sorted(set(re.findall(r"references/([\w-]+\.md)", text))):
        if not (skill_dir / "references" / reference).exists():
            errors.append(
                f"skills/readable-code/SKILL.md: points at references/{reference}, "
                f"which does not exist"
            )

    return errors


def main() -> int:
    catalog = load_catalog()
    version = read_version()

    all_errors: list[str] = []
    all_errors += check_schema(catalog)
    all_errors += check_schema_prefix_sync()

    # Downstream checks assume schema-valid rules (e.g. every rule has an
    # 'id'); skip them on a broken catalog rather than crashing.
    if not all_errors:
        all_errors += check_id_consistency(catalog)
        all_errors += check_lint_rule_files(catalog)
        all_errors += check_lint_fixtures(catalog)
        all_errors += check_suppression_fixtures()
        all_errors += check_referential_integrity(catalog)
        all_errors += check_linter_referential_integrity(catalog)
        all_errors += check_lint_severity_sync(catalog)
        all_errors += check_lint_slug_sync(catalog)
        all_errors += check_lint_language_extension_sync()

    all_errors += check_skill_spec(version)
    all_errors += check_budgets(version)
    all_errors += check_version_sync(version)

    if all_errors:
        print(f"validate.py: {len(all_errors)} error(s):", file=sys.stderr)
        for error in all_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    rule_count = len(catalog["rules"])
    print(f"validate.py: all checks passed ({rule_count} rule(s) in catalog, v{version}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
