# AI assistant configuration

This file exists so Claude Code loads project instructions automatically. The actual guidelines live in [`AGENTS.md`](AGENTS.md), the shared instruction file also read directly by GitHub Copilot and other AI tools that follow the [AGENTS.md](https://agents.md) convention.

@AGENTS.md
<!-- taorc:begin v0.1.0 -->
## Readable code (taorc)

Write code so the next reader understands it in the least time. Full rules:
first existing path wins—`.claude/skills/readable-code/SKILL.md`,
`.agents/skills/readable-code/SKILL.md`, `.github/skills/readable-code/SKILL.md`,
`skills/readable-code/SKILL.md`. Read it before non-trivial work.

### Always

- Name the thing, not its shape. No `data`, `result`, `handler`, `helper`. (N1, N9)
- Put the unit in the name: `timeoutSecs`, not `timeout`. (N3)
- Comment *why*, never *what*. If a comment restates the line below it, delete it. (C1)
- No plan narration ("Step 1:"), no banner comments, no emoji in code. (X7, X8)
- Handle the trivial or invalid case first and return immediately. (F2, F5)
- Treat one more level of nesting as a signal to restructure. (F6)
- Name a subexpression when a condition runs past three terms. (E1)
- Inline a name used once that says no more than the expression it replaced. (V1)
- For a function you add, say what it returns on empty or boundary input and when it raises. (C14)
- One task per block. If describing it needs "and", split it. (S3)
- Test names say the scenario and the expected result. (T3)

### Never

- Widen the diff to satisfy a readability rule. Mention it instead. (X1)
- Override a project's existing vocabulary or conventions with these. (X2)
- Rename a public or exported symbol, a parameter name included, unless asked. (X3)
- Mix a readability change and a behavior change in one step. (X4)
- Argue with the formatter. It wins. (X5)
<!-- taorc:end -->
