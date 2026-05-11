# Workflows

> Step-by-step procedures using tiaportal-mcp MCP tools.
>
> These workflows are maintained as Claude Code skills in `.claude/skills/`.
> The files below are quick-reference summaries that point to the authoritative skill.

| Workflow | Skill (source of truth) | Tags |
|----------|------------------------|------|
| new-project-from-scratch.md | `.claude/skills/new-project/SKILL.md` | create, new, e2e |
| debug-compile-errors.md | `.claude/skills/debug-compile/SKILL.md` | debug, compile, error, fix |
| download-and-test.md | `.claude/skills/download-test/SKILL.md` | download, test, s7, verify |
| modify-existing-program.md | `.claude/skills/modify-program/SKILL.md` | modify, edit, existing |

To invoke a workflow, use the corresponding skill command in Claude Code:
- `/new-project` — Create project from scratch
- `/scl-inject` — Primary SCL code injection
- `/debug-compile` — Iterative compile error repair
- `/download-test` — Download and verify via S7.Net
- `/modify-program` — Open, modify, recompile existing project
