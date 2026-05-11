---
name: project-backup
description: Save a backup copy of the current TIA Portal project and optionally compare with online PLC
---

# Project Backup

## Prerequisites
- TIA Portal connected (`GetState` -> IsConnected = true)
- Project open (`GetProject` returns project info)

## Steps

### Step 1: Verify current project

```
GetProject()
```
Expected: `{ "Success": true, "ProjectName": "MyProject", "ProjectPath": "D:\\TIA-Projects\\..." }`

Record the project name and path.

### Step 2: Save current state

```
SaveProject()
```
Expected: `{ "Success": true }`

Always save before creating a backup to ensure the latest changes are on disk.

### Step 3: Create backup copy

```
SaveAsProject(path="<original_path>_backup_YYYYMMDD")
```
Expected: `{ "Success": true, "ProjectPath": "D:\\TIA-Projects\\MyProject_backup_20260511\\..." }`

Use today's date in the backup name. This creates a full independent copy of the project.

> Note: After `SaveAsProject`, TIA Portal switches to the backup copy as the active project. If you want to continue working on the original, reopen it:

```
OpenProject(path="<original_path>\\<original_name>.ap19")
```

### Step 4: Compare with online PLC (optional)

If a PLC is connected, compare the project state with what's running:

```
CompareToOnline(softwarePath="<softwarePath>")
```
Expected:
```json
{
  "Success": true,
  "Differences": [],
  "InSync": true
}
```

If `InSync` is `false`, review the `Differences` list to see which blocks differ between project and PLC.

## Common Issues

| Problem | Fix |
|---------|-----|
| "Path already exists" on SaveAsProject | A backup with this name already exists — add a sequence number or time |
| SaveProject fails with "read-only" | Remove read-only attribute from project folder |
| CompareToOnline fails "not connected" | Run `GoOnline` first, then compare |
| After SaveAsProject, wrong project active | Reopen the original project with `OpenProject` |
