---
name: scl-inject
description: Write SCL code to TIA Portal external source, generate blocks, compile — the primary code injection workflow
---

# SCL Code Injection

The primary workflow for getting SCL code into TIA Portal.

## Prerequisites
- TIA Portal connected (`GetState` -> IsConnected = true)
- Project open with at least one PLC device
- `softwarePath` known (e.g. `PLC_1/Program blocks`)

## Steps

### Step 0: Clean up existing blocks if re-injecting

If you are replacing blocks that already exist (re-injecting updated code), delete the old generated blocks first to avoid "block already exists" errors:

```
GetBlocks(softwarePath="<softwarePath>")
```

For each block that will be regenerated:
```
DeleteBlock(softwarePath="<softwarePath>", blockName="<blockName>")
```

Skip this step if injecting into a fresh project with no existing blocks.

### Step 1: Write SCL to external source

```
SetExternalSourceContent(
  softwarePath="<softwarePath>",
  sourceName="Main",
  content="<full SCL source>"
)
```

The SCL source MUST have blocks in dependency order:
1. TYPE (UDTs) — no dependencies
2. FUNCTION (FCs) — may reference UDTs
3. FUNCTION_BLOCK (FBs) — may reference UDTs and FCs
4. DATA_BLOCK (instance DBs) — reference their parent FB
5. ORGANIZATION_BLOCK (OBs) — call FBs and FCs

### Step 2: Generate blocks from source

```
GenerateBlocksFromSource(
  softwarePath="<softwarePath>",
  sourceName="Main"
)
```

If this fails -> SCL syntax error. Read the error, fix the source, repeat Step 1-2.

### Step 3: Compile

```
CompileSoftware(softwarePath="<softwarePath>")
```

- ErrorCount == 0 -> Success. Proceed to download or save.
- ErrorCount > 0 -> Use `/debug-compile` skill to fix errors.

### Step 4: Verify blocks were created

```
GetBlocks(softwarePath="<softwarePath>")
```

Confirm all expected blocks (OBs, FBs, FCs, DBs) appear in the list.

## Common Issues

| Problem | Fix |
|---------|-----|
| "Source not found" on GenerateBlocksFromSource | Check sourceName matches exactly |
| Block dependency error | Reorder blocks: UDTs -> FCs -> FBs -> DBs -> OBs |
| "Block already exists" | The previous source created blocks that conflict. Delete old blocks first or use a fresh source name |
| Compile errors after successful generation | Use `/debug-compile` skill |
