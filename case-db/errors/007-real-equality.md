# Error 007: REAL Equality Comparison Fails Due to Float Precision

## Frontmatter
- **Tags**: real, float, comparison
- **Error Type**: Logic

## Error Message
Logic symptom — no compile error:
```
IF branch never executes even though #temp appears to equal 25.0
```

## Bad Code
```scl
FUNCTION_BLOCK FB_TempCheck
VERSION : 0.1
VAR_INPUT
    temp : REAL;
END_VAR
VAR_OUTPUT
    atSetpoint : BOOL;
END_VAR
BEGIN
    // ERROR: exact REAL equality unreliable due to floating-point representation
    IF #temp = 25.0 THEN
        #atSetpoint := TRUE;
    ELSE
        #atSetpoint := FALSE;
    END_IF;
END_FUNCTION_BLOCK
```

## Good Code
```scl
FUNCTION_BLOCK FB_TempCheck
VERSION : 0.1
VAR_INPUT
    temp : REAL;
END_VAR
VAR_OUTPUT
    atSetpoint : BOOL;
END_VAR
VAR_CONSTANT
    EPSILON : REAL := 0.01;
    SETPOINT : REAL := 25.0;
END_VAR
BEGIN
    // FIX: use epsilon (tolerance) comparison for REAL values
    IF ABS(#temp - SETPOINT) < EPSILON THEN
        #atSetpoint := TRUE;
    ELSE
        #atSetpoint := FALSE;
    END_IF;
END_FUNCTION_BLOCK
```

## Why
IEEE 754 single-precision floating-point (REAL in S7) cannot represent all decimal values exactly. A value that displays as `25.0` in a Watch Table may be stored as `24.99999237` or `25.00000381` internally, depending on how it was computed (sensor scaling, arithmetic rounding, etc.). An exact equality test `= 25.0` compares every bit of the mantissa, so it silently fails. The correct idiom is to test whether the absolute difference is within an acceptable epsilon tolerance.

## Detection
- No compile error; logic symptom only
- In Watch Table: `#temp` shows `25.0` but `#atSetpoint` stays FALSE
- Inspect the raw hex value — it will differ from the exact 32-bit encoding of 25.0 (`0x41C80000`)
- Search SCL source for `= <float literal>` or `<> <float literal>` patterns

## Related
- `knowledge/scl-language-reference.md` — REAL type and IEEE 754 representation
- `.claude/rules/scl-rules.md` — rule 7: never use = for REAL, use epsilon
