# Data Logging Pattern

## Frontmatter
- **Tags**: logging, recipe, buffer, ring, data, timestamp, db
- **CPU**: Both
- **Difficulty**: Intermediate

## Problem
PLC programs often need to store historical data (temperatures, events, production
counts) in a ring buffer, or load/save recipe parameters from a configuration DB.

## Solution

### Pattern 1: Ring Buffer Logger

#### Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| UDT_LogEntry | UDT | Single log record |
| FB_RingLogger | FB | Ring buffer manager |
| DB_Logger | DB | Instance with log data |

#### SCL Code
```scl
TYPE "UDT_LogEntry"
VERSION : 0.1
  STRUCT
    Timestamp  : DINT;     // Milliseconds since startup (TIME_TO_DINT)
    Value      : REAL;     // Logged value
    EventCode  : INT;      // Event type (0=sample, 1=alarm, 2=change)
    Valid      : BOOL;     // Entry has been written
  END_STRUCT;
END_TYPE

FUNCTION_BLOCK "FB_RingLogger"
TITLE = 'Ring buffer data logger'
VERSION : 0.1

VAR_INPUT
  LogValue    : REAL;      // Value to log
  EventCode   : INT;       // Event type
  Trigger     : BOOL;      // Rising edge triggers log entry
  ClearAll    : BOOL;      // Clear entire buffer
END_VAR

VAR_OUTPUT
  EntryCount  : INT;       // Total entries written (wraps at BufferSize)
  BufferFull  : BOOL;      // Buffer has wrapped at least once
  Error       : BOOL;
  ErrorID     : INT;
END_VAR

VAR
  Buffer      : ARRAY[0..99] OF "UDT_LogEntry";
  WriteIndex  : INT := 0;
  TotalWrites : DINT := 0;
  PrevTrigger : BOOL;
END_VAR

VAR CONSTANT
  BUFFER_SIZE : INT := 100;
END_VAR

BEGIN
  // Clear
  IF #ClearAll THEN
    FOR #WriteIndex := 0 TO #BUFFER_SIZE - 1 DO
      #Buffer[#WriteIndex].Valid := FALSE;
    END_FOR;
    #WriteIndex := 0;
    #TotalWrites := 0;
    #BufferFull := FALSE;
    RETURN;
  END_IF;

  // Rising edge detection
  IF #Trigger AND NOT #PrevTrigger THEN
    #Buffer[#WriteIndex].Value := #LogValue;
    #Buffer[#WriteIndex].EventCode := #EventCode;
    #Buffer[#WriteIndex].Timestamp := TIME_TO_DINT("Clock_1ms");
    #Buffer[#WriteIndex].Valid := TRUE;

    #WriteIndex := #WriteIndex + 1;
    #TotalWrites := #TotalWrites + 1;

    IF #WriteIndex >= #BUFFER_SIZE THEN
      #WriteIndex := 0;
      #BufferFull := TRUE;
    END_IF;
  END_IF;

  #PrevTrigger := #Trigger;
  #EntryCount := DINT_TO_INT(#TotalWrites);
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Logger"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_RingLogger"
BEGIN
END_DATA_BLOCK
```

### Pattern 2: Recipe Manager
```scl
TYPE "UDT_Recipe"
VERSION : 0.1
  STRUCT
    Name       : STRING[32];
    Speed      : REAL;
    Temperature: REAL;
    Pressure   : REAL;
    CycleTime  : TIME;
    BatchSize  : INT;
  END_STRUCT;
END_TYPE

DATA_BLOCK "DB_Recipes"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    ActiveIndex : INT := 0;
    Recipes     : ARRAY[0..9] OF "UDT_Recipe";
  END_STRUCT;
BEGIN
  Recipes[0].Name := 'Default';
  Recipes[0].Speed := 100.0;
  Recipes[0].Temperature := 25.0;
  Recipes[0].Pressure := 1.0;
  Recipes[0].CycleTime := T#10s;
  Recipes[0].BatchSize := 100;
END_DATA_BLOCK

FUNCTION "FC_LoadRecipe" : BOOL
VERSION : 0.1
VAR_INPUT
  RecipeIndex : INT;
END_VAR
VAR_OUTPUT
  Speed       : REAL;
  Temperature : REAL;
  Pressure    : REAL;
  CycleTime   : TIME;
  BatchSize   : INT;
END_VAR
BEGIN
  IF #RecipeIndex < 0 OR #RecipeIndex > 9 THEN
    #FC_LoadRecipe := FALSE;
    RETURN;
  END_IF;

  #Speed := "DB_Recipes".Recipes[#RecipeIndex].Speed;
  #Temperature := "DB_Recipes".Recipes[#RecipeIndex].Temperature;
  #Pressure := "DB_Recipes".Recipes[#RecipeIndex].Pressure;
  #CycleTime := "DB_Recipes".Recipes[#RecipeIndex].CycleTime;
  #BatchSize := "DB_Recipes".Recipes[#RecipeIndex].BatchSize;
  "DB_Recipes".ActiveIndex := #RecipeIndex;
  #FC_LoadRecipe := TRUE;
END_FUNCTION
```

### S7-1200 Variant
Ring buffer: reduce ARRAY size if DB exceeds 16 KB. 100 entries × ~12 bytes = ~1.2 KB → fits.
Recipe DB: 10 recipes × ~50 bytes = ~500 bytes → fits easily.

## Gotchas
1. **Ring buffer overflow**: WriteIndex wraps around — old data is overwritten
2. **S7-1200 DB size**: Calculate array size × entry size. Stay under 16 KB.
3. **NON_RETAIN**: Log data is lost on PLC restart. Use RETAIN if persistence needed.
4. **Timestamp**: Use TIME system variable or real-time clock for meaningful timestamps

## Related
- `../industry/batch-process.md` — Recipes used in batch operations
- `error-handling.md` — Log error events
