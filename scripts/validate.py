#!/usr/bin/env python3
"""The CI validation gate (v1-design-doc.md §9).

Checks whose subject does not exist yet are skipped rather than failed, so
this runs clean against a tree partway through the milestones — lint fixtures
(no taorc-lint until MS4) and the installer/placement-matrix tests (no
installers until MS5) are not implemented here for that reason.

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
import sys

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
        all_errors += check_referential_integrity(catalog)

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
