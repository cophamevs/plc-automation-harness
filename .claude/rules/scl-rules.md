---
description: Mandatory SCL programming rules for Siemens S7 PLC development
globs: 
alwaysApply: true
---

# SCL Programming Rules

## Mandatory Rules
1. ALWAYS use SCL — never LAD/FBD/STL unless user explicitly requests
2. Every FB MUST have a corresponding Instance DB — calling FB without instance = compile error
3. NEVER use global variables inside FBs — pass through IN/OUT/INOUT parameters
4. ALWAYS declare variable types explicitly — no implicit type conversions
5. STRING type: always specify length `STRING[80]`, default max is 254 chars
6. ARRAY indexes: S7 uses 1-based by default `ARRAY[1..10] OF INT`
7. REAL comparison: never use `=`, use `ABS(a - b) < epsilon`
8. ENO (Enable Output): check after every instruction that can fail
9. Every FB MUST have `Error : BOOL` and `ErrorID : INT` outputs for diagnostics
10. Block names MUST use standard prefixes: `OB_`, `FB_`, `FC_`, `DB_`, `UDT_`

## Block Ordering in External Sources
When writing SCL for external source injection, blocks MUST appear in dependency order:
1. TYPE (UDTs)
2. FUNCTION (FCs)
3. FUNCTION_BLOCK (FBs)
4. DATA_BLOCK (instance DBs)
5. ORGANIZATION_BLOCK (OBs)

## Block Naming Convention (Mandatory)
| Type | Prefix (MUST use) | Example | Numbering |
|------|-------------------|---------|-----------|
| OB | OB_ | OB_Main, OB_Startup | OB1, OB100 |
| FB | FB_ | FB_MotorControl | FB1-FB999 |
| FC | FC_ | FC_CalcPressure | FC1-FC999 |
| DB | DB_ | DB_Config, DB_Recipe | DB1-DB999 |
| UDT | UDT_ | UDT_MotorData | - |

## Device Configuration (Mandatory for ALL PLCs)
After adding a device, configure these settings before compiling or downloading:

| Setting | Value | Why |
|---------|-------|-----|
| PUT/GET communication | **Enabled** | Required for S7.Net runtime access and inter-PLC communication |
| Protection & Security → Access level | **Full access (no protection)** | Allows S7.Net read/write without authentication |
| Protection & Security → Password | **Disabled (empty)** | Prevents download/access blocks |
| System and clock memory bytes | **Enabled** (assign to free MB, e.g. MB0/MB1) | Required for system diagnostics, clock pulses |
| DB block access | **Optimized** (default) | Better performance; set `S7_Optimized_Access := 'FALSE'` only on FBs that need S7.Net direct access |

> When using `AddDevice` with `configureForSimulation=true`, these are set automatically.
> For real hardware, configure manually in TIA Portal Device & Networks or via the MCP tools.

## Tag Management Rules
11. NEVER use absolute addresses (`%I0.0`, `%Q0.0`, `%M10.0`) directly in SCL source
12. ALWAYS create named PLC tags FIRST via `CreateTag`, then reference by tag name in SCL
13. Using absolute addresses causes TIA Portal to auto-generate ugly tag names like `Tag__639141118790971718`

**Correct workflow:**
```
// Step 1: Create tags via MCP
CreateTag(tableName="ValveTags", tagName="CmdOpen", dataType="Bool", address="%M10.0")
CreateTag(tableName="ValveTags", tagName="FbkOpen", dataType="Bool", address="%M11.0")

// Step 2: Use tag NAMES in SCL (not addresses)
"DB_Valve1"(
    CmdOpen := "CmdOpen",    // ← tag name, NOT %M10.0
    FbkOpen := "FbkOpen",    // ← tag name, NOT %M11.0
    ...
);
```

## External Source Compilation Rules
When generating blocks from external source files:

| Rule | Detail |
|------|--------|
| OB VAR_TEMP >= 20 bytes | Pad with `pad : ARRAY[0..18] OF BYTE` if needed |
| `S7_Optimized_Access` pragma on FB | Instance DBs inherit from FB, not from the DB pragma |
| No TITLE with pragma | Remove TITLE line when using `{ S7_Optimized_Access := 'FALSE' }` |
| M0/M1 reserved | System/clock memory — use M10+ for user data |
| No %I/%Q without HW modules | Use M bits for PLCSim-only testing |

## SCL Syntax Quick Reference
```
// Data types
BOOL, BYTE, WORD, DWORD, SINT, INT, DINT, USINT, UINT, UDINT
REAL, LREAL(1500), TIME, DATE, TOD, STRING[n], CHAR
ARRAY[lo..hi] OF type, STRUCT, UDT

// Control flow
IF cond THEN ... ELSIF cond THEN ... ELSE ... END_IF;
CASE selector OF val1: ...; val2: ...; ELSE ...; END_CASE;
FOR i := 1 TO 10 BY 1 DO ... END_FOR;
WHILE cond DO ... END_WHILE;
REPEAT ... UNTIL cond END_REPEAT;

// Timer/Counter (system FBs)
"IEC_Timer_0_DB".TON(IN:=start, PT:=T#5s);
elapsed := "IEC_Timer_0_DB".ET;
done := "IEC_Timer_0_DB".Q;
```
