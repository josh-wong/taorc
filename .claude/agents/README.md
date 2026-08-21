# Custom agents for taorc

This directory contains project-specific Claude Code subagents, adapted for taorc's toolchain: Python-based generation and validation scripts, a YAML rule catalog, a multi-harness distribution mechanism, and token-budgeted skill content.

## Available agents

The following specialized agents help automate development workflows for this project.

### Build and quality assurance

These agents handle compilation, code quality checks, and automated testing workflows.

**builder:** Build specialist that regenerates every adapter and manifest from `catalog/rules.yaml` and `templates/agent-block.md`, and checks the result for drift. Example usage: "Use builder to regenerate the adapters and check for drift"

**lint-checker:** Code quality specialist that analyzes code for style violations and enforces coding standards. Example usage: "Use lint-checker to lint modified files"

**test-runner:** Testing specialist that runs the CI validation gate, lint fixture suites, and the eval harness. Example usage: "Use test-runner to run scripts/validate.py and report failures"

### Debugging and performance

These agents specialize in diagnosing failures and optimizing performance.

**debugger:** Debugging specialist that diagnoses crashes, runtime errors, and integration failures using logs and stack traces. Example usage: "Use debugger to analyze this crash log"

**performance-profiler:** Performance specialist that checks token budgets on `SKILL.md`, the managed block, and the fallback prompts against their targets. Example usage: "Use performance-profiler to check SKILL.md's token count against budget"

### Legal and compliance

**legal-copyright-auditor:** Copyright compliance specialist that checks the repo for text or examples too closely derived from *The Art of Readable Code*, and verifies required disclaimers and attribution are present. Example usage: "Use legal-copyright-auditor to audit this PR before merge"

### GitHub workflow

These agents automate GitHub interactions while following project conventions and templates.

**github-issue-creator:** GitHub workflow specialist that creates well-formed issues following the project template at `.github/ISSUE_TEMPLATE/standard-issue-template.md`. Example usage: "Use github-issue-creator to file a bug for the login timeout"

**pr-creator:** Pull request specialist that creates well-structured PRs with clear descriptions and testing notes, following the PR template. Example usage: "Use pr-creator to open a PR for the new comments.md reference file"

## How to use agents

Agents are invoked by referencing them in natural language requests to Claude Code. When you ask Claude to perform a task that matches an agent's specialty, you can explicitly request that agent or Claude may automatically delegate to the appropriate agent.

### Invoking agents explicitly

To explicitly use a specific agent, include the agent name in your request using the pattern "Use the [agent-name] to [task description]". Here are practical examples:

**Building and testing:**

- "Use the builder to regenerate the adapters and check for drift"
- "Use the test-runner to run scripts/validate.py and report failures"
- "Use the lint-checker to check the new reference file for style issues"

**Debugging and performance:**

- "Use the debugger to find out why the C1 lint rule is misfiring on this file"
- "Use the performance-profiler to check SKILL.md's token count against budget"

**GitHub workflows:**

- "Use the github-issue-creator to file a bug for the false-positive N7 finding"
- "Use the pr-creator to open a pull request for the new comments.md reference file"

### Automatic agent selection

Claude Code can automatically select the appropriate agent based on your request context. For example, asking "Can you run the tests?" may automatically invoke the test-runner agent. You can override this by explicitly naming a different agent if needed.

### Viewing available agents

To see all available agents in your session, use the `/agents` command. This displays project-specific agents from this directory, user-level agents from your home directory, and built-in system agents. Each agent listing shows its name, description, and configured tools.

## Agent design philosophy

These agents are meant to encode this project's specific, non-obvious constraints — the things a generic assistant would get wrong by default, not general good practice it already knows. Fill in each agent's placeholders with the project's real build/test/lint commands and its load-bearing architectural rules, and delete any optional agent that doesn't apply.

## Customization

Each agent is defined in a Markdown file with YAML frontmatter followed by a system prompt. To customize an agent, edit the corresponding `.md` file to modify the system prompt or tool permissions. Changes take effect automatically without requiring a restart. For detailed information about agent configuration options, see the [Claude Code documentation](https://github.com/anthropics/claude-code) for the agent system.

## Contributing

When adding new agents to this directory, follow the existing naming convention using lowercase with hyphens. Use clear, descriptive names that indicate the agent's purpose. Document the agent's capabilities and provide example usage in this README. Specify appropriate tools and model in the YAML frontmatter based on the agent's complexity. Test thoroughly before committing to ensure the agent behaves as expected across different scenarios.
