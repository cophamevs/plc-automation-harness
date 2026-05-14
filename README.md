# PLC Automation Harness

A knowledge ecosystem for Claude Code and Codex CLI that supports Siemens
S7-1500/S7-1200 PLC automation workflows.

## What Is This?

This repo contains markdown knowledge files, agent definitions, reusable
patterns, annotated case databases, and step-by-step workflows for programming
Siemens PLCs in SCL (Structured Control Language).

It works with the [tiaportal-mcp](../tiaportal-mcp) MCP server which provides
tools for TIA Portal automation.

## Quick Start

1. Clone this repo alongside tiaportal-mcp:
   ```
   E:\Software_Siemens\
   ├── tiaportal-mcp\           # MCP server (tools)
   └── plc-automation-harness\  # This repo (knowledge + agents)
   ```

2. Configure MCP:
   - For Codex CLI: copy `.mcp.json.example` to `.mcp.json` and update path/version.
   - For Claude Code: update `.claude/settings.json` path/version.

3. Open this directory in your client:
   ```bash
   cd E:\Software_Siemens\plc-automation-harness
   codex   # or: claude
   ```

4. Start with the right root doc:
   - Codex CLI: `AGENTS.md`
   - Claude Code: `CLAUDE.md`

5. Core assets available in this repo:
   - 7 skills (`/new-project`, `/scl-inject`, `/debug-compile`, `/download-test`, `/modify-program`, `/tag-management`, `/project-backup`)
   - 4 agents (`@scl-developer`, `@scl-debugger`, `@scl-reviewer`, `@plc-architect`)
   - 5 auto-loaded rules (SCL rules, safety, S7-1500/1200 compat, knowledge registry)
   - SCL language reference and patterns
   - 25 annotated case examples

## Structure

| Directory | Contents |
|-----------|----------|
| `AGENTS.md` | Codex CLI operating guide and markdown navigation hierarchy |
| `.claude/rules/` | 5 rules auto-loaded by Claude Code (SCL rules, safety, CPU compat) |
| `.claude/skills/` | 5 skills invokable via `/skill-name` (workflows as skills) |
| `.claude/agents/` | 4 specialized agent definitions |
| `knowledge/` | SCL reference, CPU specs, design patterns, industry examples |
| `case-db/` | 10 success cases + 10 error cases for few-shot learning |
| `workflows/` | Quick-reference summaries pointing to skills (source of truth) |
| `prompts/` | Legacy prompt fragments (see rules and agents for authoritative versions) |
| `docs/` | Getting started, architecture, agents guide, cheat sheet |

## Extensible by Design

Every content directory uses `_index.md` for discovery and `_template.md`
for contribution. Adding new content is zero-friction:

1. Copy the `_template.md` in the target directory
2. Fill in all sections
3. Add one line to the directory's `_index.md`

See `CONTRIBUTING.md` for details.

## Requirements

- Codex CLI or Claude Code CLI
- tiaportal-mcp MCP server
- TIA Portal V19 or V20 (running)
- Windows 10/11

## Codex CLI Notes

- Codex setup guide: `docs/codex-quickstart.md`
- MCP template: `.mcp.json.example`
- Local `.mcp.json` is machine-specific and should not be committed
