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
