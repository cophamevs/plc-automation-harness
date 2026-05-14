# Codex Quickstart

This guide configures this repository for Codex CLI with `tiaportal-mcp`.

## Prerequisites

- Windows 10/11
- TIA Portal V19 or V20
- Built `TiaMcpServer.exe` from `tiaportal-mcp`
- Codex CLI

## 1) Clone Repos Side-by-Side

```text
E:\Software_Siemens\
├── tiaportal-mcp\
└── plc-automation-harness\
```

## 2) Configure MCP for Codex

Create local `.mcp.json` from template:

```powershell
Copy-Item .mcp.json.example .mcp.json
```

Then edit `.mcp.json`:

- `command`: full path to your `TiaMcpServer.exe`
- `args`: set `--tia-major-version` to `19` or `20`

## 3) Start Codex in Repo

```powershell
cd E:\Software_Siemens\plc-automation-harness
codex
```

## 4) First Prompts

Use these in order:

1. "Read AGENTS.md and follow its markdown hierarchy for this repo."
2. "Check TIA connectivity: GetState, Connect if needed, then GetProject."
3. "Show project tree and identify softwarePath for PLC_1."

## 5) Default Code Workflow

For SCL updates, use:

1. `SetExternalSourceContent`
2. `GenerateBlocksFromSource`
3. `CompileSoftware`
4. `DownloadSoftware` only after explicit confirmation

## 6) Where to Read Knowledge

Start at registries:

- `knowledge/_index.md`
- `workflows/_index.md`
- `case-db/_index.md`

Then open only task-relevant files.

