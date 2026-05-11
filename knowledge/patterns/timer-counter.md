# Timer and Counter Patterns

## Frontmatter
- **Tags**: timer, counter, delay, pulse, ton, tof, tp, ctu, ctd, timeout
- **CPU**: Both
- **Difficulty**: Beginner

## Problem
Timers and counters are the most fundamental building blocks in PLC programming.
Incorrect usage (declaring in TEMP, not resetting, wrong timer type) causes
subtle bugs.

## Solution

### Pattern 1: On-Delay with Timeout Protection
```scl
VAR
  StartDelay : TON_TIME;
  Timeout    : TON_TIME;
END_VAR

// Start delay: wait 3 seconds before enabling output
#StartDelay(IN := #CmdStart, PT := T#3s);
#OutputEnable := #StartDelay.Q;

// Timeout: if operation doesn't complete in 30 seconds, fault
#Timeout(IN := #OperationActive, PT := T#30s);
IF #Timeout.Q THEN
  #Fault := TRUE;
  #FaultCode := 1;  // Operation timeout
END_IF;
```

### Pattern 2: Pulse Generator (Blink)
```scl
VAR
  BlinkTimer : TON_TIME;
  BlinkState : BOOL;
END_VAR

#BlinkTimer(IN := NOT #BlinkState, PT := T#500ms);
IF #BlinkTimer.Q THEN
  #BlinkState := NOT #BlinkState;
  #BlinkTimer(IN := FALSE, PT := T#0ms);  // Reset timer
END_IF;
#BlinkOutput := #BlinkState;
// Result: 500ms on, 500ms off = 1 Hz blink
```

### Pattern 3: One-Shot Pulse (Rising Edge)
```scl
VAR
  PulseTimer : TP_TIME;
END_VAR

#PulseTimer(IN := #TriggerInput, PT := T#100ms);
#PulseOutput := #PulseTimer.Q;
// Output goes TRUE for exactly 100ms on rising edge of TriggerInput
```

### Pattern 4: Cascaded Timers (Sequence)
```scl
VAR
  Timer1 : TON_TIME;
  Timer2 : TON_TIME;
  Timer3 : TON_TIME;
END_VAR

// Phase 1: 5 seconds
#Timer1(IN := #SequenceStart, PT := T#5s);
#Phase1Active := #SequenceStart AND NOT #Timer1.Q;

// Phase 2: starts when Phase 1 completes, lasts 3 seconds
#Timer2(IN := #Timer1.Q, PT := T#3s);
#Phase2Active := #Timer1.Q AND NOT #Timer2.Q;

// Phase 3: starts when Phase 2 completes, lasts 2 seconds
#Timer3(IN := #Timer2.Q, PT := T#2s);
#Phase3Active := #Timer2.Q AND NOT #Timer3.Q;

// Sequence complete
#SequenceDone := #Timer3.Q;
```

### Pattern 5: Parts Counter with Batch
```scl
VAR
  PartsCounter : CTU;
  BatchCount   : INT := 0;
END_VAR

#PartsCounter(CU := #SensorPulse, R := #ResetParts, PV := 100);
#PartsInBatch := #PartsCounter.CV;
#BatchComplete := #PartsCounter.Q;

IF #BatchComplete THEN
  #BatchCount := #BatchCount + 1;
  #PartsCounter(CU := FALSE, R := TRUE, PV := 100);  // Reset for next batch
END_IF;
```

### Pattern 6: Debounce Input
```scl
VAR
  DebounceOn  : TON_TIME;
  DebounceOff : TOF_TIME;
END_VAR

// Input must be TRUE for 50ms to register as ON
#DebounceOn(IN := #RawInput, PT := T#50ms);
// Input must be FALSE for 50ms to register as OFF
#DebounceOff(IN := #DebounceOn.Q, PT := T#50ms);
#DebouncedInput := #DebounceOff.Q;
```

### S7-1200 Variant
Same as S7-1500 version — all timer/counter types are available on both.

## Gotchas
1. **Timer in VAR_TEMP = broken**: Timer loses state every scan. MUST be in VAR (static).
2. **Timer reset**: Call with IN:=FALSE to reset. Just setting IN to FALSE once isn't enough — must call the timer instance.
3. **TON vs TOF vs TP**: TON delays ON, TOF delays OFF, TP gives fixed pulse. Choose the right one.
4. **Timer resolution**: TIME type has 1ms resolution. Minimum reliable timing ≈ scan cycle time.
5. **Counter overflow**: CTU.CV is INT (max 32767). For large counts, use DINT variable with manual counting.

## Related
- `state-machine.md` — State machines use timers for timed transitions
- `../../case-db/success/010-star-delta-starter.md` — Timer sequence for motor starting
