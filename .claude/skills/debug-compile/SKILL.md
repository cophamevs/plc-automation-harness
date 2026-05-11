---
name: debug-compile
description: Iterative repair loop for SCL compile errors — max 5 iterations, read-analyze-fix-recompile
---

# Debug Compile Errors

## Prerequisites

- A TIA Portal project is open and a compile error has been returned by `CompileSoftware` or `GenerateBlocksFromSource`.
- You know the `softwarePath` (e.g. `"PLC_1/Program blocks"`) and `sourceName` (e.g. `"Main"`).
- Error message text is available (from the previous compile result).

---

## Overview

This workflow is a **repair loop** with a maximum of 5 iterations.  
Each iteration: read -> analyze -> fix -> recompile -> check.  
If errors remain after 5 iterations, stop and escalate to a human.

```
Iteration counter = 0
WHILE errors remain AND counter < 5:
    Step 1: Read current source
    Step 2: Analyze error message
    Step 3: Apply fix
    Step 4: Recompile
    Step 5: Check result
    counter++
IF still errors: escalate
```

---

## Steps

### Step 1: Read the current source

```
GetExternalSourceContent(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main"
)
```
Expected:
```json
{ "Success": true, "Content": "ORGANIZATION_BLOCK OB1\n..." }
```

Record the full source content. Identify the line number referenced in the error message.

---

### Step 2: Analyze the error

1. Parse the error message for:
   - **Error code** (e.g. `"Type mismatch"`, `"Symbol not found"`)
   - **Location** (block name, line number)
   - **Token** (variable name or expression flagged)

2. Match the pattern against the quick-reference table below.

3. If the pattern matches a case in `case-db/errors/`, read that file for the exact fix.

---

### Step 3: Apply the fix

Edit the source content (in memory) according to the analysis in Step 2, then write it back:

```
SetExternalSourceContent(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main",
  content="<corrected SCL source>"
)
```
Expected: `{ "Success": true }`

> Only modify the specific lines that caused the error. Avoid reformatting unrelated code.

---

### Step 4: Regenerate blocks and recompile

#### 4a. Regenerate blocks from the updated source

```
GenerateBlocksFromSource(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main"
)
```
Expected: `{ "Success": true, "BlocksGenerated": N }`  
If this fails, the SCL syntax is still invalid — return to Step 2.

#### 4b. Recompile

```
CompileSoftware(softwarePath="PLC_1/Program blocks")
```
Expected: `{ "Success": true, "ErrorCount": 0, "WarningCount": 0 }`

---

### Step 5: Check the result

- **`ErrorCount == 0`**: Loop complete. Proceed to the calling workflow (e.g. `/new-project` Step 7).
- **`ErrorCount > 0`**: Increment the iteration counter.
  - If `counter < 5`: return to Step 1 with the new error messages.
  - If `counter == 5`: stop. Report all remaining errors to the user and request human review.

---

## Quick-Reference Fix Table

| Error Pattern | Cause | Fix | Case File |
|---------------|-------|-----|-----------|
| `Type mismatch` / `cannot convert` | Implicit conversion between INT, REAL, DINT, etc. | Add explicit conversion: `INT_TO_REAL(#var)`, `REAL_TO_INT(#var)` | `case-db/errors/001-type-mismatch.md` |
| `Instance DB ... not found` / `FB called without instance` | FB called without an assigned instance DB | Add `DATA_BLOCK DB_Name INSTANCE OF FB_Name ... END_DATA_BLOCK` | `case-db/errors/002-missing-instance-db.md` |
| `Array index out of range` / `Index ... exceeds bounds` | Array subscript outside declared range | Check `ARRAY[lo..hi]` declaration; adjust index or array size | `case-db/errors/003-array-bounds.md` |
| `TIMER ... must be static` / `timer in TEMP` | IEC timer (TON, TOF, TP) declared in VAR_TEMP | Move timer variable to VAR (static) section | `case-db/errors/004-timer-in-temp.md` |
| `Unknown identifier` / `Symbol not found` for local var | Local variable missing `#` prefix | Add `#` prefix: `#myVar` instead of `myVar` | `case-db/errors/005-missing-hash-prefix.md` |
| `STRING without length` / `Invalid type STRING` | STRING used without explicit length | Specify length: `STRING[80]` | `case-db/errors/006-string-no-length.md` |
| `REAL comparison with =` / `equality on REAL` | Direct `=` or `<>` on REAL type | Replace with epsilon check: `ABS(#a - #b) < 1.0e-6` | `case-db/errors/007-real-equality.md` |
| `Block ... referenced before declaration` / dependency order | Blocks out of order in source file | Reorder: UDTs -> FCs -> FBs -> DBs -> OBs | `case-db/errors/008-block-order-dependency.md` |
| `Optimized access` / `address not accessible via S7` | DB has optimized access enabled | Add `{ S7_Optimized_Access := 'FALSE' }` to DB attributes | `case-db/errors/009-optimized-access-conflict.md` |
| `VARIANT ... not supported` / `LREAL not found` on S7-1200 | S7-1200 unsupported data types used | Remove VARIANT, LREAL, LINT, ULINT, LWORD; use REAL/INT alternatives | `case-db/errors/010-s7-1200-unsupported-type.md` |
| `Missing semicolon` / `Unexpected token` | Statement not terminated | Add `;` at end of every statement | -- |
| `CASE without ELSE` | CASE statement missing ELSE branch | Add `ELSE: ;` (no-op) or a meaningful else action | -- |
| `VERSION not declared` | Block header missing VERSION | Add `VERSION : 0.1` to block header | -- |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `GetExternalSourceContent` returns empty | Source file was deleted or renamed | Use `GetSoftwareTree` to confirm the source name, then re-create it with `SetExternalSourceContent` |
| `GenerateBlocksFromSource` fails but error message is vague | Malformed SCL structure (e.g. unmatched `BEGIN`/`END`) | Read the full source and check that every block has matching open/close keywords |
| Same error persists after 5 iterations | Root cause not yet identified; fix is incomplete | Escalate to human: provide full source + all error messages |
| `CompileSoftware` succeeds but wrong block count | Some blocks were silently skipped | Check each block's header for syntax errors individually |
| Error line number does not match current source | Cached compiled state out of sync | Call `GenerateBlocksFromSource` again before `CompileSoftware` |
