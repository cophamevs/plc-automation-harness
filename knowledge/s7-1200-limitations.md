# S7-1200 Limitations vs S7-1500

## Frontmatter
- **Tags**: 1200, limits, compatibility, restrictions, workaround
- **CPU**: 1200
- **TIA Version**: Any

## Overview
When targeting S7-1200, these features are NOT available. This document lists
each limitation and provides a workaround where possible.

---

## Comparison Table

| Feature | S7-1500 | S7-1200 | Workaround on 1200 |
|---------|---------|---------|---------------------|
| VARIANT | Yes | No | Use separate FBs per type, or ANY pointer |
| LREAL (64-bit float) | Yes | No | Use REAL (32-bit) — less precision |
| LINT (64-bit int) | Yes | No | Use DINT (32-bit) or 2x DINT |
| ULINT | Yes | No | Use UDINT |
| LWORD | Yes | No | Use DWORD |
| LTIME | Yes | No | Use TIME (ms resolution only) |
| LDT | Yes | No | Use DT |
| OOP (METHOD) | Yes | No | Use FCs that take DB as IN_OUT |
| OOP (PROPERTY) | Yes | No | Direct variable access |
| OOP (INTERFACE) | Yes | No | Not available |
| ARRAY[*] | Yes | No | Fixed-size arrays only |
| Max DB size | 64 MB | 16 KB | Split data across multiple DBs |
| Call nesting | 24 levels | 6 levels | Flatten call hierarchy |
| Work memory | Up to 6 MB | Up to 150 KB | Optimize code size |
| Optimized access | Full | Limited | Works but fewer options |
| Web server | Full | Basic | Limited HMI pages |
| OPC UA server | Built-in | FW V4.5+ add-on | Requires firmware update |
| Technology objects | Full (Motion, PID) | PID_Compact only | No motion control |
| System clock memory | Configurable | Must enable manually | Enable in device config |

---

## Detailed Workarounds

### No VARIANT → Type-Specific FBs
```scl
// S7-1500: one generic FB handles any type
FUNCTION_BLOCK "FB_Logger_1500"
VAR_INPUT
  Data : VARIANT;
END_VAR
// ...

// S7-1200: separate FBs per type
FUNCTION_BLOCK "FB_LoggerInt"
VAR_INPUT
  Data : INT;
END_VAR
// ...

FUNCTION_BLOCK "FB_LoggerReal"
VAR_INPUT
  Data : REAL;
END_VAR
// ...
```

### No LREAL → REAL with Precision Notes
```scl
// S7-1500:
VAR
  precise : LREAL := LREAL#3.141592653589793;  // 15-digit precision
END_VAR

// S7-1200:
VAR
  value : REAL := 3.141593;  // Only 7-digit precision
END_VAR
// ⚠️ REAL has ~7 significant digits. For financial calculations,
// consider using DINT with fixed-point (e.g., cents instead of dollars).
```

### No OOP → FCs with DB Parameter
```scl
// S7-1500 with METHOD:
// "DB_Motor1".Start();
// "DB_Motor1".SetSpeed(speed := 1500.0);

// S7-1200 equivalent:
"FC_MotorStart"(MotorDB := "DB_Motor1");
"FC_MotorSetSpeed"(MotorDB := "DB_Motor1", Speed := 1500.0);

FUNCTION "FC_MotorStart" : VOID
VAR_IN_OUT
  MotorDB : "UDT_MotorData";
END_VAR
BEGIN
  #MotorDB.Running := TRUE;
END_FUNCTION
```

### No ARRAY[*] → Fixed-Size Arrays
```scl
// S7-1500: variable-length array
FUNCTION "FC_Sum" : REAL
VAR_INPUT
  Data : ARRAY[*] OF REAL;
END_VAR
// ...

// S7-1200: fixed max size with actual length parameter
FUNCTION "FC_Sum" : REAL
VAR_INPUT
  Data      : ARRAY[1..100] OF REAL;
  DataCount : INT;  // actual number of elements to process
END_VAR
VAR_TEMP
  i   : INT;
  sum : REAL;
END_VAR
BEGIN
  #sum := 0.0;
  FOR #i := 1 TO #DataCount DO
    #sum := #sum + #Data[#i];
  END_FOR;
  #FC_Sum := #sum;
END_FUNCTION
```

### Max 16 KB per DB → Split Strategy
```scl
// If you need 1000 records of 20 bytes each = 20 KB (exceeds 16 KB on 1200)
// Solution: split across multiple DBs

DATA_BLOCK "DB_Records_1"    // Records 1-400 (8 KB)
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    Records : ARRAY[1..400] OF "UDT_Record";
  END_STRUCT;
BEGIN
END_DATA_BLOCK

DATA_BLOCK "DB_Records_2"    // Records 401-800
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    Records : ARRAY[1..400] OF "UDT_Record";
  END_STRUCT;
BEGIN
END_DATA_BLOCK

// In FC, select DB based on record index:
IF #RecordIndex <= 400 THEN
  #Value := "DB_Records_1".Records[#RecordIndex].Value;
ELSE
  #Value := "DB_Records_2".Records[#RecordIndex - 400].Value;
END_IF;
```

### Max 6 Call Nesting → Flatten
```
// Too deep for S7-1200:
OB1 → FB1 → FB2 → FB3 → FB4 → FB5 → FB6 → FC1  (7 levels = ERROR)

// Flattened:
OB1 → FB1   (level 1)
OB1 → FB2   (level 1)  
OB1 → FB3   (level 1)
FB3 → FC1   (level 2 — only 2 deep)
```

### Enable System Clock Memory
S7-1200 does NOT have clock memory bits enabled by default (S7-1500 does).

To enable: Device Configuration → PLC Properties → System and clock memory →
Enable system memory byte (e.g., MB0) and clock memory byte (e.g., MB100).

Then in SCL:
```scl
// M100.0 = 10 Hz clock (50ms on / 50ms off)
// M100.3 = 2 Hz
// M100.4 = 1.25 Hz
// M100.5 = 1 Hz (500ms on / 500ms off)
// M100.6 = 0.625 Hz
// M100.7 = 0.5 Hz (1s on / 1s off)
```

---

## Pre-Flight Checklist for S7-1200 Code

Before compiling code for S7-1200, verify:
1. No VARIANT, LREAL, LINT, ULINT, LWORD, LTIME, LDT used
2. No METHOD, PROPERTY, or INTERFACE declarations
3. No ARRAY[*] — all arrays have fixed bounds
4. No single DB exceeds 16 KB
5. Call nesting depth ≤ 6
6. If using clock memory: enabled in device configuration
7. Total program size fits within work memory (check CPU model)

## Related
- `scl-language-reference.md` — Full language syntax
- `s7-1500.md` — Features available only on S7-1500
