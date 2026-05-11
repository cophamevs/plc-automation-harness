# TIA Portal Openness API — Agent Guide

## Frontmatter
- **Tags**: openness, api, mcp, tools, workflow, tia-portal
- **CPU**: Both
- **TIA Version**: V19+

## Overview
The tiaportal-mcp MCP server exposes tools that wrap the Siemens TIA Portal
Openness .NET API. This guide covers the tools most relevant to SCL development
workflows.

---

## Connection Lifecycle

```
Connect → [GetProject / OpenProject / CreateProject] → ... work ... → SaveProject → CloseProject → Disconnect
```

| Tool | When to Use |
|------|-------------|
| Connect | First — attaches to running TIA Portal instance |
| GetState | Check if already connected (avoid redundant Connect) |
| GetProject | List open projects/sessions |
| OpenProject | Open .ap19/.als19 file |
| CreateProject | Start new project from scratch |
| SaveProject | Save changes |
| CloseProject | Close project (auto-saves if needed) |
| Disconnect | Release TIA Portal connection |

---

## SCL Code Injection (Primary Workflow)

The fastest way to create PLC programs:

### Step 1: Write SCL to External Source
```
SetExternalSourceContent(
  softwarePath="PLC_1/PLC_1",
  sourceName="main",
  content="<complete SCL with all blocks>"
)
```
- Creates source if it doesn't exist, replaces content if it does
- Source name is arbitrary — "main" is conventional

### Step 2: Generate Blocks from Source
```
GenerateBlocksFromSource(
  softwarePath="PLC_1/PLC_1",
  sourceName="main"
)
```
- Compiles SCL source into PLC blocks (OBs, FBs, FCs, DBs, UDTs)
- Blocks appear in PLC software tree
- Returns error if SCL has syntax/semantic errors

### Step 3: Full Compilation
```
CompileSoftware(softwarePath="PLC_1/PLC_1")
```
- Compiles entire PLC software (not just external sources)
- Required before download

### Step 4: Download (⚠️ SAFETY — Confirm with user)
```
DownloadSoftware(
  softwarePath="PLC_1/PLC_1",
  downloadOptions="Software"
)
```
- Sends compiled program to PLC
- Options: None, Hardware, Software, SoftwareOnlyChanges

---

## Project Tree Navigation

```
GetProjectTree() → device paths
GetSoftwareTree(softwarePath) → block groups, external sources
GetBlocks(softwarePath) → list all blocks
GetBlockInfo(softwarePath, blockPath) → single block details
```

**softwarePath format:** `DeviceName/CPUName` — discover via GetProjectTree.

**blockPath format:** `GroupName/BlockName` or just `BlockName` if in root group.

---

## Block CRUD

| Operation | Tool |
|-----------|------|
| List blocks | GetBlocks(softwarePath, regexName?) |
| Block details | GetBlockInfo(softwarePath, blockPath) |
| Export to XML | ExportBlock(softwarePath, blockPath, exportPath) |
| Import from XML | ImportBlock(softwarePath, groupPath, importPath) |
| Delete | DeleteBlock(softwarePath, blockPath) |
| Move to group | MoveBlock(softwarePath, blockPath, targetGroupPath) |
| Create group | CreateBlockGroup(softwarePath, parentGroupPath, groupName) |

---

## S7 Runtime Access (Live PLC Data)

Connect to running PLC via S7 protocol for read/write:

```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")
S7ReadVariable(address="DB1.DBW0")      → {Value, DataType}
S7WriteVariable(address="DB1.DBW0", value="42", dataType="Int")  ⚠️ SAFETY
S7ReadDBStruct(dbNumber=1, variables='[{"offset":0,"type":"Int","name":"Speed"}]')
S7Disconnect()
```

**Important:** S7 runtime access requires `S7_Optimized_Access := 'FALSE'` on the DB.

---

## PLCSim Advance (Virtual PLC)

For testing without physical hardware:

```
PlcSimCreateInstance(instanceName="PLC_1", cpuType="1500", ipAddress="192.168.0.1")
PlcSimStart(instanceName="PLC_1")
ConfigOnlineAccess(softwarePath="PLC_1/PLC_1")  → auto-detects PLCSim adapter
DownloadSoftware(softwarePath="PLC_1/PLC_1")
// ... test with S7Connect/S7ReadVariable ...
PlcSimStop(instanceName="PLC_1")
PlcSimDeleteInstance(instanceName="PLC_1")
```

---

## Key Points
- Always call GetState before starting — avoid redundant connections
- External source workflow (Set→Generate→Compile) is faster than XML import
- softwarePath is required for most tools — discover via GetProjectTree
- Set `S7_Optimized_Access := 'FALSE'` on any DB you want to read via S7.Net
- Download and S7Write are safety-critical — always confirm with user

## Related
- Full API reference: `tiaportal-mcp/docs/tia-openness-api.md`
- `../workflows/new-project-from-scratch.md` — Complete E2E workflow
