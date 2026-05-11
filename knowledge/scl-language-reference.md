# SCL Language Reference

## Frontmatter
- **Tags**: scl, syntax, types, operators, control-flow, blocks, timer, string, conversion
- **CPU**: Both
- **TIA Version**: Any

## Overview
Complete reference for Structured Control Language (SCL) — the high-level
programming language for Siemens S7-1500 and S7-1200 PLCs. SCL is based on
IEC 61131-3 Structured Text (ST) with Siemens extensions.

---

## 1. Data Types

### Elementary Types
| Type | Size | Range | S7-1200 | S7-1500 |
|------|------|-------|---------|---------|
| BOOL | 1 bit | TRUE / FALSE | Yes | Yes |
| BYTE | 1 byte | 16#00..16#FF | Yes | Yes |
| WORD | 2 bytes | 16#0000..16#FFFF | Yes | Yes |
| DWORD | 4 bytes | 16#0000_0000..16#FFFF_FFFF | Yes | Yes |
| LWORD | 8 bytes | 16#0..16#FFFF_FFFF_FFFF_FFFF | No | Yes |
| SINT | 1 byte | -128..127 | Yes | Yes |
| INT | 2 bytes | -32768..32767 | Yes | Yes |
| DINT | 4 bytes | -2147483648..2147483647 | Yes | Yes |
| LINT | 8 bytes | -2^63..2^63-1 | No | Yes |
| USINT | 1 byte | 0..255 | Yes | Yes |
| UINT | 2 bytes | 0..65535 | Yes | Yes |
| UDINT | 4 bytes | 0..4294967295 | Yes | Yes |
| ULINT | 8 bytes | 0..2^64-1 | No | Yes |
| REAL | 4 bytes | ±1.18e-38..±3.40e+38 | Yes | Yes |
| LREAL | 8 bytes | ±2.23e-308..±1.80e+308 | No | Yes |
| CHAR | 1 byte | single character | Yes | Yes |
| WCHAR | 2 bytes | Unicode character | Yes | Yes |
| STRING[n] | n+2 bytes | max n=254 | Yes | Yes |
| WSTRING[n] | n*2+4 bytes | Unicode string | Yes | Yes |

### Time Types
| Type | Size | Format | S7-1200 | S7-1500 |
|------|------|--------|---------|---------|
| TIME | 4 bytes | T#1d2h3m4s5ms | Yes | Yes |
| LTIME | 8 bytes | LT#1d2h3m4s5ms6us7ns | No | Yes |
| DATE | 2 bytes | D#2026-05-11 | Yes | Yes |
| TOD | 4 bytes | TOD#14:30:00.000 | Yes | Yes |
| DT | 8 bytes | DT#2026-05-11-14:30:00 | Yes | Yes |
| LDT | 8 bytes | LDT#2026-05-11-14:30:00.000000000 | No | Yes |
| S5TIME | 2 bytes | S5T#2h46m30s (BCD coded) | Yes | Yes |

### Complex Types
| Type | Description | S7-1200 | S7-1500 |
|------|-------------|---------|---------|
| ARRAY[lo..hi] OF type | Fixed-size array (1-based default) | Yes | Yes |
| ARRAY[*] OF type | Variable-length array (IN/OUT only) | No | Yes |
| STRUCT | Inline structure | Yes | Yes |
| UDT (TYPE...END_TYPE) | Named reusable structure | Yes | Yes |
| VARIANT | Generic pointer to any type | No | Yes |
| ANY | S7 ANY pointer (legacy) | Yes | Yes |

### Literal Formats
```scl
// Integer literals
myInt := 42;                // decimal
myInt := 16#2A;             // hex
myInt := 2#0010_1010;       // binary
myInt := 8#52;              // octal

// Real literals
myReal := 3.14;
myReal := 1.0E+3;          // scientific: 1000.0

// Time literals
myTime := T#5s;             // 5 seconds
myTime := T#1h30m;          // 1 hour 30 minutes
myTime := T#100ms;          // 100 milliseconds

// Date/time literals
myDate := D#2026-05-11;
myTod := TOD#14:30:00;
myDt := DT#2026-05-11-14:30:00;

// String literals
myStr := 'Hello World';
myWStr := WSTRING#"Unicode text";
myChar := 'A';
```

---

## 2. Operators

### Arithmetic
| Operator | Description | Operand Types |
|----------|-------------|---------------|
| + | Addition | INT, DINT, REAL, LREAL, TIME |
| - | Subtraction / Negation | INT, DINT, REAL, LREAL, TIME |
| * | Multiplication | INT, DINT, REAL, LREAL |
| / | Division | INT, DINT, REAL, LREAL |
| MOD | Modulo (remainder) | INT, DINT, UDINT |
| ** | Exponentiation | REAL, LREAL |

### Comparison
| Operator | Description |
|----------|-------------|
| = | Equal |
| <> | Not equal |
| < | Less than |
| > | Greater than |
| <= | Less than or equal |
| >= | Greater than or equal |

### Logical (Boolean)
| Operator | Description |
|----------|-------------|
| AND / & | Logical AND |
| OR | Logical OR |
| XOR | Exclusive OR |
| NOT | Logical NOT |

### Bitwise
| Function | Description | Example |
|----------|-------------|---------|
| SHL(IN, N) | Shift left N bits | SHL(IN:=val, N:=3) |
| SHR(IN, N) | Shift right N bits | SHR(IN:=val, N:=2) |
| ROL(IN, N) | Rotate left N bits | ROL(IN:=val, N:=1) |
| ROR(IN, N) | Rotate right N bits | ROR(IN:=val, N:=1) |

### Operator Precedence (highest to lowest)
1. `NOT`, `-` (unary negation)
2. `**` (exponentiation)
3. `*`, `/`, `MOD`
4. `+`, `-`
5. `<`, `>`, `<=`, `>=`
6. `=`, `<>`
7. `AND`, `&`
8. `XOR`
9. `OR`

---

## 3. Control Structures

### IF / ELSIF / ELSE
```scl
IF #Temperature > 100.0 THEN
  #HeaterOn := FALSE;
  #AlarmHigh := TRUE;
ELSIF #Temperature < 20.0 THEN
  #HeaterOn := TRUE;
  #AlarmLow := TRUE;
ELSE
  #HeaterOn := FALSE;
  #AlarmHigh := FALSE;
  #AlarmLow := FALSE;
END_IF;
```

### CASE
```scl
CASE #State OF
  0:
    // Idle state
    #Output := 0;
  1, 2:
    // States 1 and 2 share behavior
    #Output := 1;
  3..10:
    // Range: states 3 through 10
    #Output := 2;
  ELSE
    // Default — always include ELSE
    #Output := -1;
END_CASE;
```

### FOR
```scl
FOR #i := 1 TO 10 BY 1 DO
  #Sum := #Sum + #DataArray[#i];
END_FOR;

// BY is optional (default = 1)
// Loop variable must be declared in VAR_TEMP or VAR
```

### WHILE
```scl
#i := 1;
WHILE #i <= 10 AND NOT #Error DO
  #Result := #Result + #Data[#i];
  #i := #i + 1;
END_WHILE;
```

### REPEAT...UNTIL
```scl
#i := 0;
REPEAT
  #i := #i + 1;
  #Sum := #Sum + #Data[#i];
UNTIL #i >= 10 OR #Sum > 1000
END_REPEAT;
```

### EXIT, CONTINUE, RETURN
```scl
// EXIT — break out of innermost loop
FOR #i := 1 TO 100 DO
  IF #Data[#i] = 0 THEN EXIT; END_IF;
END_FOR;

// CONTINUE — skip to next iteration
FOR #i := 1 TO 100 DO
  IF #Data[#i] < 0 THEN CONTINUE; END_IF;
  #Sum := #Sum + #Data[#i];
END_FOR;

// RETURN — exit function/block immediately
IF NOT #Valid THEN RETURN; END_IF;
```

---

## 4. Block Declarations

### ORGANIZATION_BLOCK (OB)
```scl
ORGANIZATION_BLOCK "Main"
TITLE = 'Main Program Sweep (Cycle)'
VERSION : 0.1

VAR_TEMP
  tempInfo : INT;
END_VAR

BEGIN
  // Called every scan cycle
  "DB_Motor1"(Start := "Tag_Start", Stop := "Tag_Stop");
END_ORGANIZATION_BLOCK
```

Common OBs:
| OB | Name | Trigger |
|----|------|---------|
| OB1 | Main | Every scan cycle |
| OB100 | Startup | Once after CPU restart to RUN |
| OB35 | Cyclic Interrupt | Fixed interval (default 100ms) |
| OB40 | Hardware Interrupt | Digital input edge |
| OB82 | Diagnostic Error | Module fault |
| OB121 | Programming Error | Division by zero, etc. |
| OB122 | I/O Access Error | Module not responding |

### FUNCTION_BLOCK (FB)
```scl
FUNCTION_BLOCK "FB_Pump"
TITLE = 'Pump Control'
VERSION : 0.1

VAR_INPUT
  CmdStart   : BOOL;   // Start command
  CmdStop    : BOOL;   // Stop command
  MaxRunTime : TIME := T#8h;  // Max continuous run time
END_VAR

VAR_OUTPUT
  Running    : BOOL;   // Pump is running
  Error      : BOOL;   // Fault active
  ErrorID    : INT;    // Error code (0 = no error)
END_VAR

VAR_IN_OUT
  RunHours   : REAL;   // Accumulated run hours (persistent)
END_VAR

VAR
  // Static — retains value between calls
  State      : INT := 0;
  RunTimer   : TON_TIME;
  StartTime  : TIME;
END_VAR

VAR_TEMP
  // Temporary — reset every call
  elapsed    : TIME;
END_VAR

VAR CONSTANT
  ST_IDLE    : INT := 0;
  ST_RUNNING : INT := 1;
  ST_FAULT   : INT := 10;
END_VAR

BEGIN
  // Implementation here
END_FUNCTION_BLOCK
```

### FUNCTION (FC)
```scl
FUNCTION "FC_CelsiusToFahrenheit" : REAL
TITLE = 'Temperature Conversion'
VERSION : 0.1

VAR_INPUT
  Celsius : REAL;
END_VAR

VAR_TEMP
  result : REAL;
END_VAR

BEGIN
  #result := #Celsius * 1.8 + 32.0;
  #FC_CelsiusToFahrenheit := #result;
  // FC return value: assign to function name
END_FUNCTION
```

### DATA_BLOCK (DB) — Global
```scl
DATA_BLOCK "DB_Config"
{ S7_Optimized_Access := 'FALSE' }
TITLE = 'System Configuration'
VERSION : 0.1

NON_RETAIN
  STRUCT
    MaxSpeed     : REAL := 1500.0;
    MinSpeed     : REAL := 100.0;
    AlarmDelay   : TIME := T#5s;
    SystemName   : STRING[32] := 'Pump Station 1';
    MotorCount   : INT := 4;
    MotorSpeeds  : ARRAY[1..4] OF REAL := [750.0, 750.0, 1000.0, 1000.0];
  END_STRUCT;

BEGIN
END_DATA_BLOCK
```

### DATA_BLOCK (DB) — Instance
```scl
DATA_BLOCK "DB_Pump1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Pump"
BEGIN
  // Initial values can be set here
  MaxRunTime := T#12h;
END_DATA_BLOCK
```

### TYPE (UDT)
```scl
TYPE "UDT_SensorData"
VERSION : 0.1
  STRUCT
    Value      : REAL;
    RawValue   : INT;
    Status     : WORD;
    Timestamp  : DT;
    Valid      : BOOL;
    HighAlarm  : BOOL;
    LowAlarm   : BOOL;
  END_STRUCT;
END_TYPE
```

---

## 5. Timers and Counters

### TON (On-Delay Timer)
```scl
// Declaration in VAR (static):
VAR
  StartDelay : TON_TIME;
END_VAR

// Usage:
#StartDelay(IN := #CmdStart, PT := T#5s);
IF #StartDelay.Q THEN
  // 5 seconds elapsed since CmdStart went TRUE
  #MotorOn := TRUE;
END_IF;
// .ET gives elapsed time: #StartDelay.ET
```

### TOF (Off-Delay Timer)
```scl
VAR
  StopDelay : TOF_TIME;
END_VAR

#StopDelay(IN := #CmdRun, PT := T#3s);
#MotorContactor := #StopDelay.Q;
// Output stays TRUE for 3s after CmdRun goes FALSE
```

### TP (Pulse Timer)
```scl
VAR
  Pulse : TP_TIME;
END_VAR

#Pulse(IN := #Trigger, PT := T#500ms);
#PulseOutput := #Pulse.Q;
// Output TRUE for exactly 500ms on rising edge of Trigger
```

### CTU (Count Up)
```scl
VAR
  PartsCounter : CTU;
END_VAR

#PartsCounter(CU := #SensorPulse, R := #ResetCount, PV := 100);
#CurrentCount := #PartsCounter.CV;  // Current value
#BatchComplete := #PartsCounter.Q;   // TRUE when CV >= PV
```

### CTD (Count Down)
```scl
VAR
  Countdown : CTD;
END_VAR

#Countdown(CD := #Pulse, LOAD := #LoadCmd, PV := 50);
#Remaining := #Countdown.CV;
#Done := #Countdown.Q;  // TRUE when CV <= 0
```

---

## 6. String Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| LEN | LEN(s) → INT | String length |
| CONCAT | CONCAT(s1, s2) → STRING | Concatenate |
| LEFT | LEFT(IN:=s, L:=n) → STRING | Left n chars |
| RIGHT | RIGHT(IN:=s, L:=n) → STRING | Right n chars |
| MID | MID(IN:=s, L:=n, P:=pos) → STRING | Substring |
| FIND | FIND(IN1:=s, IN2:=sub) → INT | Find substring (0=not found) |
| DELETE | DELETE(IN:=s, L:=n, P:=pos) → STRING | Delete chars |
| INSERT | INSERT(IN1:=s, IN2:=ins, P:=pos) → STRING | Insert at position |
| REPLACE | REPLACE(IN1:=s, IN2:=rep, L:=n, P:=pos) → STRING | Replace chars |

```scl
VAR_TEMP
  msg : STRING[80];
  pos : INT;
END_VAR

#msg := CONCAT(IN1 := 'Speed: ', IN2 := REAL_TO_STRING(#Speed));
#pos := FIND(IN1 := #msg, IN2 := ':');
// pos = 6 (position of ':')
```

---

## 7. Type Conversions

Explicit conversion functions — SCL requires these, no implicit conversion.

### Integer Conversions
| From → To | Function |
|-----------|----------|
| INT → DINT | INT_TO_DINT(x) |
| INT → REAL | INT_TO_REAL(x) |
| DINT → INT | DINT_TO_INT(x) — truncates if overflow |
| DINT → REAL | DINT_TO_REAL(x) |
| REAL → INT | REAL_TO_INT(x) — rounds |
| REAL → DINT | REAL_TO_DINT(x) — rounds |
| BYTE → INT | BYTE_TO_INT(x) |
| INT → BYTE | INT_TO_BYTE(x) — truncates |
| WORD → INT | WORD_TO_INT(x) — reinterprets bits |
| INT → WORD | INT_TO_WORD(x) — reinterprets bits |
| DWORD → DINT | DWORD_TO_DINT(x) |
| DINT → DWORD | DINT_TO_DWORD(x) |

### String Conversions
| Function | Description |
|----------|-------------|
| INT_TO_STRING(x) | "42" |
| REAL_TO_STRING(x) | "3.140000e+000" |
| STRING_TO_INT(s) | Parse integer from string |
| STRING_TO_REAL(s) | Parse float from string |
| DINT_TO_STRING(x) | Long integer to string |

### Time Conversions
| Function | Description |
|----------|-------------|
| TIME_TO_DINT(t) | Time in milliseconds |
| DINT_TO_TIME(d) | Milliseconds to TIME |
| S5TIME_TO_TIME(s) | Convert legacy S5TIME |

---

## 8. Addressing

### Absolute Addresses
| Prefix | Memory Area | Examples |
|--------|-------------|---------|
| I | Input image | I0.0, IB0, IW0, ID0 |
| Q | Output image | Q0.0, QB0, QW0, QD0 |
| M | Bit memory (flags) | M0.0, MB0, MW0, MD0 |
| DB | Data block | DB1.DBX0.0, DB1.DBB0, DB1.DBW0, DB1.DBD0 |

Size suffixes: X=bit, B=byte, W=word(2), D=dword(4)

### Symbolic Addresses
```scl
// Preferred — use symbolic names from tag tables or block interfaces
"Tag_MotorStart"    // PLC tag from tag table
"DB_Config".MaxSpeed  // DB member by name
#LocalVar           // Block-local variable (# prefix required)
```

### AT Overlay
```scl
VAR
  RawWord : WORD;
  Bits AT RawWord : ARRAY[0..15] OF BOOL;
END_VAR
// Access individual bits of RawWord via Bits[0]..Bits[15]
```

---

## 9. System Functions

### MOVE / MOVE_BLK
```scl
// Copy single value
#Dest := #Source;  // simple assignment

// Copy array slice
MOVE_BLK(IN := #SourceArray[1],
         COUNT := 5,
         OUT => #DestArray[1]);
```

### FILL_BLK
```scl
// Fill array with a value
FILL_BLK(IN := 0,
         COUNT := 10,
         OUT => #MyArray[1]);
```

### PEEK / POKE
```scl
// Low-level byte access (S7-1500)
#val := PEEK(area := 16#84, dbNumber := 1, byteOffset := 0);
POKE(area := 16#84, dbNumber := 1, byteOffset := 0, value := #newVal);
// area: 16#81=I, 16#82=Q, 16#83=M, 16#84=DB
```

### Serialize / Deserialize (S7-1500)
```scl
// Convert structured data to byte array and back
Serialize(SRC_VARIABLE := #MyStruct,
          DEST_ARRAY := #ByteArray,
          POS := #Position);
          
Deserialize(SRC_ARRAY := #ByteArray,
            DEST_VARIABLE := #MyStruct,
            POS := #Position);
```

---

## Key Points
- SCL is case-insensitive for keywords but preserve case for readability
- Every statement ends with semicolon `;`
- Local variables MUST use `#` prefix: `#myVar`
- String DB member access: `"DB_Name".MemberName`
- Block calls: `"DB_Instance"(Param1 := val, Param2 := val)`
- No implicit type conversion — always use explicit conversion functions
- Arrays are 1-based by default: `ARRAY[1..10]`
- VERSION declaration required on every block

## Related
- `s7-1500.md` — S7-1500 specific features (VARIANT, OOP, 64-bit)
- `s7-1200-limitations.md` — What to avoid on S7-1200
- `patterns/` — Reusable design patterns using these language features
