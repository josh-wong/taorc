# Harness verification

CI (placement-matrix, §9 check 9) proves that every generated adapter lands
at the documented path with the right content and version marker. It cannot
prove that a harness actually reads that file and behaves differently — that
needs a human running the product. This document is the M7 record of who ran
that check, on what harness version, and when.

The release gate (§6.6) is four manual smoke tests: one per delivery
mechanism, plus the two highest-traffic products. Each test runs the same two
prompts against a small scratch project with the adapter installed, and
records what happened.

## The two prompts

- **Implicit**: "Add a function that parses a CSV file of user records and
  returns the ones with a valid email." (no mention of readability — checks
  whether the skill or block fires on an ordinary code-writing task)
- **Explicit**: "Review this file for readability." (checks review mode)

## Required smoke tests

Fill in one row per harness before the MS5 gate is considered met. "Fired"
means the implicit prompt visibly changed naming/comment behavior versus a
run with the adapter removed, or the explicit prompt returned findings in the
`references/review-checklist.md` format citing catalog rule IDs.

| Harness                    | Mechanism                             | Harness version | Date tested | Fired? | Notes |
| --------------------------- | -------------------------------------- | ---------------- | ----------- | ------ | ----- |
| Claude Code                 | Agent Skills runtime (`SKILL.md`)      |                   |             |        |       |
| VS Code Copilot              | Agent Skills + `.instructions.md`      |                   |             |        |       |
| Cursor                       | Managed block (`.cursor/rules/*.mdc`)  |                   |             |        |       |
| Codex CLI or opencode        | Managed block (`AGENTS.md`)            |                   |             |        |       |

## Additional harnesses tested (optional)

Not required for the MS5 gate, but recorded here when tested, since a
verification pass costs the same effort regardless of milestone.

| Harness   | Mechanism                            | Harness version | Date tested | Fired? | Notes |
| --------- | ------------------------------------- | ---------------- | ----------- | ------ | ----- |
| Cline     | Managed block (`.clinerules/*.md`)    |                   |             |        |       |
| Windsurf  | Managed block (`.windsurf/rules/*.md`) |                  |             |        |       |
| Gemini CLI | Agent Skills runtime + `GEMINI.md`   |                   |             |        |       |
| claude.ai / Desktop | Skill `.zip` upload           |                   |             |        |       |

## How to run one

1. Build a scratch project (a couple of small source files is enough — no
   need for a real codebase).

2. Install the adapter with `scripts/install.sh --agents=<harness> --dir
   <scratch-project>` (or `install.ps1` on Windows), pointed at this repo
   with `--source`.

3. Open the scratch project in the harness under test and run the implicit
   prompt, then the explicit prompt, in a fresh session each time.

4. Record the result in the table above. A screenshot or transcript excerpt
   is welcome in the notes column but not required.
