---
name: tag-management
description: Create, configure, and manage PLC tag tables — add tags, export/import, bulk operations
---

# Tag Management

## Prerequisites
- TIA Portal connected (`GetState` -> IsConnected = true)
- Project open with at least one PLC device
- `softwarePath` known (e.g. `PLC_1/PLC_1`)

## Steps

### Step 1: List existing tag tables

```
GetTagTables(softwarePath="<softwarePath>")
```
Expected: `{ "Success": true, "TagTables": ["Default tag table", ...] }`

### Step 2: Create a new tag table (if needed)

```
CreateTagTable(
  softwarePath="<softwarePath>",
  tableName="MyTags"
)
```
Expected: `{ "Success": true }`

Skip if adding tags to an existing table.

### Step 3: Add tags to the table

```
CreateTag(
  softwarePath="<softwarePath>",
  tableName="MyTags",
  tagName="Motor_Start",
  dataType="Bool",
  address="%I0.0",
  comment="Start pushbutton"
)
```
Expected: `{ "Success": true }`

Repeat for each tag. Common data types: `Bool`, `Int`, `Real`, `Word`, `DInt`, `String`.
Common address prefixes: `%I` (input), `%Q` (output), `%M` (memory).

### Step 4: Verify tags were created

```
GetTags(
  softwarePath="<softwarePath>",
  tableName="MyTags"
)
```
Expected: list of all tags with names, types, and addresses.

### Step 5: Export tag table (optional, for backup)

```
ExportTagTable(
  softwarePath="<softwarePath>",
  tableName="MyTags",
  exportPath="D:\\Temp\\MyTags.xml"
)
```
Expected: `{ "Success": true, "ExportPath": "D:\\Temp\\MyTags.xml" }`

### Step 6: Import tag table (optional, from existing file)

```
ImportTagTable(
  softwarePath="<softwarePath>",
  importPath="D:\\Temp\\MyTags.xml"
)
```
Expected: `{ "Success": true }`

## Bulk Operations

To add many tags efficiently, create them in a loop:
1. Prepare a list of tag definitions (name, type, address, comment)
2. Call `CreateTag` for each one sequentially
3. Call `GetTags` to verify all were created

## Common Issues

| Problem | Fix |
|---------|-----|
| "Tag table not found" | Check exact table name with `GetTagTables` |
| "Address already in use" | Another tag uses this address — use `GetTags` to find conflicts |
| "Invalid address format" | Use S7 format: `%I0.0` (bool), `%IW0` (word), `%MD0` (dword) |
| "Tag already exists" | Use `UpdateTag` to modify existing tag, or `DeleteTag` first |
| Import fails with "format error" | Export format must match TIA Portal version |
