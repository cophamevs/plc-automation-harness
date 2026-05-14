# AGENTS.md

Operational guide for Codex CLI in this repository.

## 1) Read Order (Markdown Hierarchy)

Use this order for every task:

1. Root orientation:
   - `AGENTS.md` (this file)
   - `CLAUDE.md` (domain/tool rules)
2. Registries:
   - `knowledge/_index.md`
   - `workflows/_index.md`
   - `case-db/_index.md`
3. Targeted docs only:
   - open only files selected from registries that match the task
4. Templates when adding content:
   - `knowledge/_template.md`
   - `workflows/_template.md`
   - `case-db/success/_template.md`
   - `case-db/errors/_template.md`

Do not broad-scan all markdown files when a registry can route you.

## 2) Codex Working Model

This repo is a knowledge harness for Siemens PLC automation using TIA Portal MCP tools.

Before any TIA operation:

1. `GetState`
2. If disconnected: `Connect`
3. Confirm project context: `GetProject`

For SCL code workflow:

1. `SetExternalSourceContent`
2. `GenerateBlocksFromSource`
3. `CompileSoftware`
4. `DownloadSoftware` only after explicit user confirmation

Use `GetProjectTree` to resolve exact `softwarePath` (`DeviceName/CPUName`).

## 3) MCP Configuration for Codex

Use local `.mcp.json` (untracked) created from `.mcp.json.example`.

1. Copy template to `.mcp.json`
2. Set your local `TiaMcpServer.exe` path
3. Set `--tia-major-version` (`19` or `20`)

Keep machine-specific paths out of tracked docs beyond templates/examples.

## 4) Authoring and Contribution Rules

- Preserve registry-first discoverability:
  - Every new knowledge/workflow/case file must be added to the directory `_index.md`.
- Keep content markdown-only unless a utility script is explicitly needed.
- Follow existing style patterns in nearby files.
- For local generated/runtime files, prefer ignore rules over committing machine-local artifacts.

## 5) Hardware Parameter Catalog Note

- Catalog builder: `tools/hw_catalog/build_hw_catalog.py`
- Catalog DB currently tracked: `converted_md/hardware_catalog_v19.sqlite`
- Source markdown for rebuild: `converted_md/TIA_Portal_Openness_Hardware_parameters.md` (local/source artifact)

