---
name: modify-program
description: Open existing TIA Portal project, explore structure, modify SCL blocks, recompile, save
---

# Modify Existing Program

## Prerequisites

- TIA Portal V19 or V20 is running (or will be connected in Step 1).
- Full path to the existing project file (`.ap19` or `.ap20`) is known.
- `softwarePath` is known or will be discovered via `GetProjectTree` (Step 2).
- Sufficient disk space for project save and export files.

---

## Steps

### Step 1: Connect to TIA Portal and open the project

#### 1a. Verify connection

```
GetState()
```
Expected: `{ "IsConnected": true }`.  
If not connected, call:

```
Connect()
```
Expected: `{ "Success": true }`

#### 1b. Open the existing project

```
OpenProject(path="D:\\TIA-Projects\\MyPlcProject\\MyPlcProject.ap19")
```
Expected:
```json
{ "Success": true, "ProjectName": "MyPlcProject", "ProjectPath": "D:\\TIA-Projects\\..." }
```

> If a project is already open in TIA Portal, `OpenProject` will close it first. Ensure any unsaved changes in the currently open project are saved beforehand.

---

### Step 2: Explore the project structure

#### 2a. Get the project-level tree (PLCs, HMIs, drives)

```
GetProjectTree()
```
Expected: nested JSON listing all devices. Identify your PLC node and note its `SoftwarePath` (e.g. `"PLC_1/Program blocks"`).

#### 2b. Get the software tree (folders and block lists)

```
GetSoftwareTree(softwarePath="PLC_1/Program blocks")
```
Expected: directory listing of program-block folders and source files inside the PLC software.

#### 2c. List all blocks in a folder

```
GetBlocks(softwarePath="PLC_1/Program blocks")
```
Expected:
```json
{
  "Success": true,
  "Blocks": [
    { "Name": "OB1",   "Type": "OB",  "Number": 1  },
    { "Name": "FB_Ctrl", "Type": "FB", "Number": 10 },
    { "Name": "DB_Ctrl", "Type": "DB", "Number": 10 }
  ]
}
```

Use this list to identify which block(s) you need to modify.

---

### Step 3: Export / read the existing block content

Choose the export method appropriate to your goal:

#### Option A — Read the SCL external source (preferred for SCL blocks)

```
GetExternalSourceContent(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main"
)
```
Expected: `{ "Success": true, "Content": "<full SCL source text>" }`

Use this when blocks were generated from an external source file and you want to edit the SCL directly.

#### Option B — Export a single block to XML

```
ExportBlock(
  softwarePath="PLC_1/Program blocks",
  blockName="FB_Ctrl",
  exportPath="D:\\Temp\\FB_Ctrl.xml"
)
```
Expected: `{ "Success": true, "ExportPath": "D:\\Temp\\FB_Ctrl.xml" }`

Use this when you need the compiled block in XML (e.g. for structured diff or re-import into another project).

#### Option C — Export all blocks as documents (LAD/FBD/SCL/STL)

```
ExportAsDocuments(
  softwarePath="PLC_1/Program blocks",
  exportPath="D:\\Temp\\Export",
  format="SCL"
)
```
Expected: `{ "Success": true, "ExportedCount": 5, "ExportPath": "D:\\Temp\\Export" }`

Use this when you need to review all blocks before deciding which to modify.

---

### Step 4: Apply the modification and recompile

#### 4a. Write the updated source

Incorporate your changes into the source content retrieved in Step 3, then write it back:

```
SetExternalSourceContent(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main",
  content="<modified SCL source>"
)
```
Expected: `{ "Success": true }`

#### 4b. Regenerate blocks from the updated source

```
GenerateBlocksFromSource(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main"
)
```
Expected: `{ "Success": true, "BlocksGenerated": N }`  
If this fails (syntax error), fix the SCL and repeat Step 4a-4b.

#### 4c. Compile the software

```
CompileSoftware(softwarePath="PLC_1/Program blocks")
```
Expected: `{ "Success": true, "ErrorCount": 0, "WarningCount": 0 }`

If `ErrorCount > 0`, follow the `/debug-compile` skill, then return here.

---

### Step 5: Save the project

```
SaveProject()
```
Expected: `{ "Success": true }`

> Always save after a successful compile. TIA Portal does not auto-save.  
> To save to a different location use `SaveProjectAs(path="D:\\Backup\\MyPlcProject_v2")`.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `OpenProject` fails: "file not found" | Incorrect path or project moved | Verify full path including filename and extension (`.ap19` / `.ap20`) |
| `OpenProject` fails: "project already open" | A different project is loaded and locked | Save and close the current project in TIA Portal, then retry |
| `GetProjectTree` shows no devices | Project empty or wrong version | Confirm the project contains PLC devices; check TIA Portal version compatibility |
| `GetExternalSourceContent` returns `Success: false` | Source file does not exist (blocks were compiled without external source) | Use `ExportBlock` (Option B) or `ExportAsDocuments` (Option C) instead |
| `GenerateBlocksFromSource` fails with "source not found" | `sourceName` does not match the file stored in TIA Portal | Use `GetSoftwareTree` to list exact source names, then correct the `sourceName` parameter |
| `CompileSoftware` returns errors after modification | Change introduced a type mismatch, missing symbol, or structural error | Follow `/debug-compile` skill; the quick-reference table covers the most common patterns |
| `SaveProject` fails: "read-only" | Project file is marked read-only on disk | Remove the read-only attribute from the project folder in Windows Explorer |
| Block count decreased after `GenerateBlocksFromSource` | A block was accidentally deleted from source | Compare with the export from Step 3; restore missing block definitions |
| Modifications are lost after reopening TIA Portal | `SaveProject` was not called before closing | Always call `SaveProject` as the final step; consider adding it to your automation script |
