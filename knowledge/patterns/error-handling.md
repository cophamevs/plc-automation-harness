# Error Handling Pattern

## Frontmatter
- **Tags**: error, eno, status, fault, handler, aggregation
- **CPU**: Both
- **Difficulty**: Intermediate

## Problem
PLC programs need to handle errors gracefully: invalid inputs, communication
failures, sensor faults, timeout conditions. SCL uses ENO (Enable Output) for
propagating errors through function call chains.

## Solution

### Pattern 1: Standard FB Error Interface
Every FB should have consistent error outputs:

```scl
FUNCTION_BLOCK "FB_Template"
VERSION : 0.1

VAR_INPUT
  Execute : BOOL;
END_VAR

VAR_OUTPUT
  Done    : BOOL;   // Operation completed successfully
  Busy    : BOOL;   // Operation in progress
  Error   : BOOL;   // Fault occurred
  ErrorID : INT;    // Error code (0 = no error)
END_VAR

VAR
  State : INT;
END_VAR

BEGIN
  #Done := FALSE;
  #Busy := FALSE;

  CASE #State OF
    0: // Idle
      #Error := FALSE;
      #ErrorID := 0;
      IF #Execute THEN
        #State := 1;
        #Busy := TRUE;
      END_IF;

    1: // Working
      #Busy := TRUE;
      // ... do work ...
      IF (* work complete *) TRUE THEN
        #State := 2;
      END_IF;
      // Check for errors
      IF (* error condition *) FALSE THEN
        #Error := TRUE;
        #ErrorID := 1;
        #State := 0;
      END_IF;

    2: // Done
      #Done := TRUE;
      IF NOT #Execute THEN
        #State := 0;  // Reset when Execute drops
      END_IF;
  END_CASE;
END_FUNCTION_BLOCK
```

### Pattern 2: ENO Chain
```scl
// ENO = Enable Output — FALSE if instruction failed
// Check ENO after critical operations

#result := REAL_TO_INT(#inputValue);
IF NOT ENO THEN
  #Error := TRUE;
  #ErrorID := 10;  // Conversion overflow
  RETURN;
END_IF;
```

### Pattern 3: Error Aggregation
```scl
FUNCTION_BLOCK "FB_ErrorAggregator"
TITLE = 'Collect errors from multiple sub-systems'
VERSION : 0.1

VAR_INPUT
  SubSystem1Error   : BOOL;
  SubSystem1ErrorID : INT;
  SubSystem2Error   : BOOL;
  SubSystem2ErrorID : INT;
  SubSystem3Error   : BOOL;
  SubSystem3ErrorID : INT;
  AckAll            : BOOL;
END_VAR

VAR_OUTPUT
  AnyError          : BOOL;
  FirstErrorID      : INT;
  ErrorCount        : INT;
END_VAR

VAR
  ErrorLatched      : ARRAY[1..3] OF BOOL;
  ErrorIDs          : ARRAY[1..3] OF INT;
END_VAR

BEGIN
  // Update current errors
  #ErrorLatched[1] := #ErrorLatched[1] OR #SubSystem1Error;
  #ErrorLatched[2] := #ErrorLatched[2] OR #SubSystem2Error;
  #ErrorLatched[3] := #ErrorLatched[3] OR #SubSystem3Error;
  #ErrorIDs[1] := #SubSystem1ErrorID;
  #ErrorIDs[2] := #SubSystem2ErrorID;
  #ErrorIDs[3] := #SubSystem3ErrorID;

  // Acknowledge
  IF #AckAll THEN
    IF NOT #SubSystem1Error THEN #ErrorLatched[1] := FALSE; END_IF;
    IF NOT #SubSystem2Error THEN #ErrorLatched[2] := FALSE; END_IF;
    IF NOT #SubSystem3Error THEN #ErrorLatched[3] := FALSE; END_IF;
  END_IF;

  // Aggregate
  #AnyError := #ErrorLatched[1] OR #ErrorLatched[2] OR #ErrorLatched[3];
  #ErrorCount := BOOL_TO_INT(#ErrorLatched[1])
               + BOOL_TO_INT(#ErrorLatched[2])
               + BOOL_TO_INT(#ErrorLatched[3]);

  // First error (lowest index)
  #FirstErrorID := 0;
  IF #ErrorLatched[1] THEN #FirstErrorID := #ErrorIDs[1];
  ELSIF #ErrorLatched[2] THEN #FirstErrorID := #ErrorIDs[2];
  ELSIF #ErrorLatched[3] THEN #FirstErrorID := #ErrorIDs[3];
  END_IF;
END_FUNCTION_BLOCK
```

### Pattern 4: Safe Division
```scl
FUNCTION "FC_SafeDiv" : REAL
VERSION : 0.1
VAR_INPUT
  Numerator   : REAL;
  Denominator : REAL;
  DefaultVal  : REAL := 0.0;
END_VAR
BEGIN
  IF ABS(#Denominator) < 1.0E-10 THEN
    #FC_SafeDiv := #DefaultVal;
    ENO := FALSE;
  ELSE
    #FC_SafeDiv := #Numerator / #Denominator;
  END_IF;
END_FUNCTION
```

### S7-1200 Variant
Same as S7-1500 — ENO and error patterns work identically on both.

## Gotchas
1. **ENO is per-instruction** — it resets on the next instruction. Check it immediately.
2. **Error latching**: Always latch errors (don't just reflect current state) — transient errors can be missed.
3. **Consistent interface**: Use the same Done/Busy/Error/ErrorID pattern on ALL FBs.
4. **Error codes**: Define a table of error codes per FB. Document them.
5. **BOOL_TO_INT**: Returns 0 or 1 — useful for counting errors.
6. **ELSE clause must never be empty**: An empty ELSE is a silent failure. Every CASE and IF-ELSIF must handle the undefined case by activating a fail-safe action:
```scl
// ❌ WRONG — undefined state ignored silently
CASE #LightState OF
  10: #VehicleContinue := TRUE;
  20: #VehicleSlowDown := TRUE;
  30: #VehicleStop := TRUE;
  ELSE
    ;  // do nothing — dangerous!
END_CASE;

// ✅ CORRECT — ELSE triggers fail-safe
CASE #LightState OF
  10: #VehicleContinue := TRUE;
  20: #VehicleSlowDown := TRUE;
  30: #VehicleStop := TRUE;
  ELSE
    // Unknown/corrupted state → safe fallback
    #VehicleContinue := FALSE;
    #VehicleSlowDown := FALSE;
    #VehicleStop := TRUE;    // default to stop (safe)
    #Error := TRUE;
    #ErrorID := 99;          // undefined state
    #Alarm_Active := TRUE;
END_CASE;
```
**ELSE fail-safe checklist:**
- [ ] All outputs driven to a known safe state
- [ ] Error flag set and ErrorID assigned
- [ ] Alarm surfaced to HMI or diagnostic buffer

## Related
- `alarm-management.md` — Alarms triggered by error conditions
- `state-machine.md` — Fault state in state machines
