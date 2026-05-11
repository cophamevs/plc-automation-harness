# Error 004: Timer Declared in VAR_TEMP (Resets Every Scan)

## Frontmatter
- **Tags**: timer, temp, static
- **Error Type**: Runtime

## Error Message
Runtime symptom — no compile error:
```
Timer Q output never becomes TRUE; timer resets on every PLC scan cycle
```

## Bad Code
```scl
FUNCTION_BLOCK FB_Delay
VERSION : 0.1
VAR_INPUT
    enable : BOOL;
END_VAR
VAR_OUTPUT
    delayed : BOOL;
END_VAR
VAR_TEMP
    // ERROR: TON instance in VAR_TEMP is re-initialised every scan
    delayTimer : TON_TIME;
END_VAR
BEGIN
    #delayTimer(IN := #enable, PT := T#5S);
    #delayed := #delayTimer.Q;
END_FUNCTION_BLOCK
```

## Good Code
```scl
FUNCTION_BLOCK FB_Delay
VERSION : 0.1
VAR_INPUT
    enable : BOOL;
END_VAR
VAR_OUTPUT
    delayed : BOOL;
END_VAR
VAR
    // FIX: timer in VAR (static) — persists across scans
    delayTimer : TON_TIME;
END_VAR
BEGIN
    #delayTimer(IN := #enable, PT := T#5S);
    #delayed := #delayTimer.Q;
END_FUNCTION_BLOCK
```

## Why
`VAR_TEMP` variables occupy stack space that is allocated freshly at the start of each block call and discarded at the end. Timer function blocks (TON, TOF, TP, etc.) rely on their internal state (`ET`, accumulated elapsed time, and `Q`) persisting between scan cycles. Placing a timer in `VAR_TEMP` causes it to be zero-initialised on every call, so the elapsed time never accumulates — `Q` can never reach TRUE. The correct location is `VAR` (static), which is backed by the instance DB.

## Detection
- No compile error
- Symptom: timer output (`Q`) never goes TRUE despite `IN` being held TRUE for longer than `PT`
- Check in Watch Table: `#delayTimer.ET` resets to 0 each scan instead of counting up

## Related
- `knowledge/scl-timers.md` — TON/TOF/TP usage and memory requirements
- `knowledge/scl-best-practices.md` — rule: timers/counters always in VAR (static)
- `case-db/errors/002-missing-instance-db.md` — related static-state pattern
