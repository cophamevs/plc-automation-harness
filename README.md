# PLC Automation Harness

A Claude Code knowledge ecosystem that transforms Claude into a Siemens
S7-1500/S7-1200 PLC automation engineer.

## What Is This?

This repo contains markdown knowledge files, agent definitions, reusable
patterns, annotated case databases, and step-by-step workflows that teach
Claude Code how to program Siemens PLCs using SCL (Structured Control Language).

It works with the [tiaportal-mcp](../tiaportal-mcp) MCP server which provides
102 tools for TIA Portal automation.

## Quick Start

1. Clone this repo alongside tiaportal-mcp:
   ```
   E:\Software_Siemens\
   ├── tiaportal-mcp\           # MCP server (102 tools)
   └── plc-automation-harness\  # This repo (knowledge + agents)
   ```

2. Open this directory in Claude Code:
   ```bash
   cd E:\Software_Siemens\plc-automation-harness
   claude
   ```

3. Claude automatically loads `CLAUDE.md` and has access to:
   - 5 skills (`/new-project`, `/scl-inject`, `/debug-compile`, `/download-test`, `/modify-program`)
   - 4 agents (`@scl-developer`, `@scl-debugger`, `@scl-reviewer`, `@plc-architect`)
   - 5 auto-loaded rules (SCL rules, safety, S7-1500/1200 compat, knowledge registry)
   - SCL language reference and patterns
   - 20 annotated case examples

4. Ensure tiaportal-mcp is configured in `.claude/settings.json`

## Structure

| Directory | Contents |
|-----------|----------|
| `.claude/rules/` | 5 rules auto-loaded by Claude Code (SCL rules, safety, CPU compat) |
| `.claude/skills/` | 5 skills invokable via `/skill-name` (workflows as skills) |
| `.claude/agents/` | 4 specialized agent definitions |
| `knowledge/` | SCL reference, CPU specs, design patterns, industry examples |
| `case-db/` | 10 success cases + 10 error cases for few-shot learning |
| `workflows/` | Step-by-step procedures (reference copies) |
| `prompts/` | Reusable prompt fragments |

## Extensible by Design

Every content directory uses `_index.md` for discovery and `_template.md`
for contribution. Adding new content is zero-friction:

1. Copy the `_template.md` in the target directory
2. Fill in all sections
3. Add one line to the directory's `_index.md`

See `CONTRIBUTING.md` for details.

## Requirements

- Claude Code CLI
- tiaportal-mcp MCP server
- TIA Portal V19 or V20 (running)
- Windows 10/11
