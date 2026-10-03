---
name: Readable Code Review
description: Reports readability findings as taorc rule citations with concrete fixes.
keep-coding-instructions: true
---

# Readable code review

This style changes how you report a readability review, not how you write or change code. When a response is not a readability review — writing code, answering a question, running a command — respond as you normally would.

When a response is a readability review, from `/taorc-review` or from a request such as "review this for readability", lay it out as follows.

## Findings come first

Open with the first finding. No preamble before it: no restating the request, no summary of what you are about to check, no verdict on the code as a whole.

Write every finding in this shape, one blank line between findings, ordered by severity (`error`, then `warning`, then `suggestion`) and by file and line within a severity:

```text
[ID] path/to/file.ext:LINE  One-line statement of the problem
  the matched source line, verbatim
  → the concrete fix, in the imperative
```

For a finding that covers the whole diff rather than one line, replace the location with `this diff` and replace the source line with one sentence on what the finding covers.

## Every ID is real

Cite only rule IDs from the `readable-code` skill's catalog table. When an observation is worth raising but no rule covers it, write it as a plain sentence with no bracketed ID, after the findings. A plausible-looking invented ID is worse than none.

## The fix is a change, not a suggestion

Write `→ rename to retryDelayMs`, not "consider a clearer name". When you cannot state the change, leave the finding out.

## Close briefly

After the findings, add at most two short paragraphs:

- **Left alone:** what you deliberately did not flag and why, such as pre-existing code outside the diff or a convention the file has already settled.
- **Unruled observations:** anything worth saying that no catalog rule covers.

Omit either paragraph when it has nothing to say. When there are no findings at all, say so in one sentence and stop.
