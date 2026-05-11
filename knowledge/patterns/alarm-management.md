# Alarm Management Pattern

## Frontmatter
- **Tags**: alarm, diagnostic, fault, warning, program-alarm
- **CPU**: Both
- **Difficulty**: Intermediate

## Problem
Industrial machines have many alarm conditions (overtemperature, overpressure,
jam detection, communication loss). You need a centralized way to collect,
prioritize, acknowledge, and clear alarms.

## Solution

### Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| UDT_Alarm | UDT | Alarm data structure |
| FB_AlarmHandler | FB | Collects and manages up to 32 alarms |
| DB_Alarms | DB | Instance for alarm handler |

### SCL Code

```scl
TYPE "UDT_Alarm"
VERSION : 0.1
  STRUCT
    Active     : BOOL;       // Alarm condition currently present
    Latched    : BOOL;       // Alarm was active (needs acknowledge)
    Acknowledged : BOOL;     // Operator acknowledged
    Priority   : INT;        // 1=Critical, 2=Warning, 3=Info
    ActivationCount : DINT;  // How many times this alarm triggered
    LastActiveTime  : TIME;  // When last activated
  END_STRUCT;
END_TYPE

FUNCTION_BLOCK "FB_AlarmHandler"
TITLE = 'Centralized Alarm Handler for up to 32 alarms'
VERSION : 0.1

VAR_INPUT
  AlarmBits     : DWORD;    // 32 alarm inputs packed as bits
  AckAll        : BOOL;     // Acknowledge all alarms
  ResetAll      : BOOL;     // Reset all latched alarms (if condition cleared)
END_VAR

VAR_OUTPUT
  AnyActive     : BOOL;     // At least one alarm active
  AnyUnacked    : BOOL;     // At least one alarm latched but not acknowledged
  ActiveCount   : INT;      // Number of currently active alarms
  HighestPriority : INT;    // Highest priority among active alarms (1=worst)
  Error         : BOOL;
  ErrorID       : INT;
END_VAR

VAR
  Alarms        : ARRAY[0..31] OF "UDT_Alarm";
  CycleTimer    : TON_TIME;
END_VAR

VAR_TEMP
  i             : INT;
  bitVal        : BOOL;
  activeCount   : INT;
  anyActive     : BOOL;
  anyUnacked    : BOOL;
  highPri       : INT;
END_VAR

BEGIN
  #activeCount := 0;
  #anyActive := FALSE;
  #anyUnacked := FALSE;
  #highPri := 999;

  FOR #i := 0 TO 31 DO
    // Extract bit from DWORD
    #bitVal := DWORD_TO_BOOL(SHR(IN := #AlarmBits, N := #i) AND DWORD#1);

    // Rising edge — alarm just became active
    IF #bitVal AND NOT #Alarms[#i].Active THEN
      #Alarms[#i].ActivationCount := #Alarms[#i].ActivationCount + 1;
      #Alarms[#i].Latched := TRUE;
      #Alarms[#i].Acknowledged := FALSE;
    END_IF;

    #Alarms[#i].Active := #bitVal;

    // Acknowledge
    IF #AckAll AND #Alarms[#i].Latched THEN
      #Alarms[#i].Acknowledged := TRUE;
    END_IF;

    // Reset latched alarm if condition cleared AND acknowledged
    IF #ResetAll AND NOT #Alarms[#i].Active AND #Alarms[#i].Acknowledged THEN
      #Alarms[#i].Latched := FALSE;
      #Alarms[#i].Acknowledged := FALSE;
    END_IF;

    // Aggregate
    IF #Alarms[#i].Active THEN
      #activeCount := #activeCount + 1;
      #anyActive := TRUE;
      IF #Alarms[#i].Priority < #highPri THEN
        #highPri := #Alarms[#i].Priority;
      END_IF;
    END_IF;

    IF #Alarms[#i].Latched AND NOT #Alarms[#i].Acknowledged THEN
      #anyUnacked := TRUE;
    END_IF;
  END_FOR;

  #ActiveCount := #activeCount;
  #AnyActive := #anyActive;
  #AnyUnacked := #anyUnacked;
  #HighestPriority := #highPri;
  IF #highPri = 999 THEN #HighestPriority := 0; END_IF;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Alarms"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_AlarmHandler"
BEGIN
END_DATA_BLOCK
```

### S7-1200 Variant
Same as S7-1500 version — no S7-1500-only features used.
Note: `DWORD_TO_BOOL(SHR(...))` works on both platforms.

## Usage Example
```scl
// In OB1 — pack alarm conditions into DWORD
VAR_TEMP
  alarmWord : DWORD;
END_VAR

#alarmWord := DWORD#0;
IF "Tag_OverTemp" THEN #alarmWord := #alarmWord OR SHL(IN:=DWORD#1, N:=0); END_IF;
IF "Tag_OverPress" THEN #alarmWord := #alarmWord OR SHL(IN:=DWORD#1, N:=1); END_IF;
IF "Tag_JamDetect" THEN #alarmWord := #alarmWord OR SHL(IN:=DWORD#1, N:=2); END_IF;

"DB_Alarms"(
  AlarmBits := #alarmWord,
  AckAll    := "Tag_AckButton",
  ResetAll  := "Tag_ResetButton"
);
```

## Gotchas
1. Set alarm priorities during initialization or via config DB — don't hardcode
2. Latch behavior: alarm stays visible even after condition clears, until acknowledged
3. DWORD limits to 32 alarms — for more, use ARRAY of DWORD or multiple handlers
4. Bit extraction from DWORD: shift right then AND with 1, convert to BOOL

## Related
- `state-machine.md` — State machines often trigger alarms on fault states
- `error-handling.md` — ENO-based error propagation
- `../industry/conveyor-control.md` — Practical alarm usage
