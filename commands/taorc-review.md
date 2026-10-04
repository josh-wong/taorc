---
description: Review the current diff for readability against the taorc catalog.
argument-hint: "[file|directory|PR#]  (default: the current diff)"
---

Use the `readable-code` skill in `review` mode. Load its `references/review-checklist.md` before reading any code, and follow it for scan order, severity, finding format, and what to leave out.

Target: $ARGUMENTS

Resolve the target this way:

- **Empty:** the uncommitted changes in the working tree, staged and unstaged (`git diff HEAD`). If there are none, say so and stop rather than reviewing the whole repository.
- **A number:** that pull request's diff (`gh pr diff <number>`).
- **A file or directory path:** that path as it stands now, not only its changed lines.

Report findings only. Do not edit, stage, or rewrite anything.
