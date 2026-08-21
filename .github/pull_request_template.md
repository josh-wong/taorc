## Summary

<!-- Brief description of what this PR accomplishes, starting with "This PR ..." -->

## Related issues or PRs

<!-- Use format: Resolves issue #123, Relates to PR #456. If a related issue or PR doesn't exist, write "N/A" -->
-

## Changes made

<!-- List specific changes with bullet points -->
-
-
-

## Technical implementation

<!-- Describe architectural decisions, patterns used, etc. -->
- **Approach:**
- **Key files modified:**
- **Dependencies added/removed:**
- **Design patterns used:**

## Testing performed

<!-- Mark completed testing with [x]. Add or remove items to match this project's actual testing surface (platforms, locales, accessibility modes, etc.) -->
- [ ] Code compiles without errors or warnings
- [ ] Tested core functionality works as expected
- [ ] Tested edge cases and error handling
- [ ] Unit tests added or updated (if applicable)
- [ ] `taorc-lint` fixtures pass, positive and negative (if a lintable rule changed)
- [ ] Token budgets verified for any changed budgeted file (`SKILL.md`, `templates/agent-block.md`, `prompts/system-prompt.md`, `prompts/system-prompt-mini.md`)
- [ ] Adapter placement matrix passes for affected harnesses (if `catalog/rules.yaml` or `templates/agent-block.md` changed)
- [ ] Manual harness smoke test performed and recorded in `docs/harness-verification.md` (if skill content or the managed block changed)

## Legal and copyright considerations

<!-- Mark applicable items with [x]. Add PR-specific notes below any relevant item. -->
- [ ] No text from *The Art of Readable Code* was added to any file — rule statements, rationale, and examples are original
- [ ] Any new or changed catalog rule ID follows the stable-ID policy (never renumbered or reused; withdrawn rules get `deprecated: true` and `superseded_by`)
- [ ] Chapter citations (`chapter:` fields, `chapter-map.md`) point to a chapter number only, not book text or a detailed summary

## Code quality

<!-- Verify these items -->
- [ ] Code follows project conventions and patterns
- [ ] Added appropriate comments for non-obvious logic only
- [ ] No hardcoded strings that should be localized (if the project supports multiple locales)
- [ ] Proper error handling implemented
- [ ] No debugging code or print statements left in
- [ ] Removed unused imports and variables

## Breaking changes

<!-- Does this PR renumber or remove a rule ID, or change a generated adapter's format? -->
- [ ] No breaking changes
- [ ] Rule catalog change: added, deprecated, or superseded a rule ID (describe below; IDs are never renumbered or reused)
- [ ] Adapter or manifest format change affecting existing installs (describe migration or backward-compatibility handling below)

## Additional context

<!-- Any extra information for reviewers, screenshots, performance notes, etc. -->
