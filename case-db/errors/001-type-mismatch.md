# Error 001: Type Mismatch — INT Assigned to REAL

## Frontmatter
- **Tags**: type, conversion, int, real
- **Error Type**: Compile

## Error Message
```
Cannot convert type 'Int' to type 'Real'
```
TIA Portal compiler rejects the implicit assignment from an INT (or DINT/WORD) variable into a REAL variable without an explicit conversion function.

## Bad Code
```scl
FUNCTION_BLOCK FB_TempScale
VERSION : 0.1
VAR_INPUT
    rawSensor : INT;
END_VAR
VAR_OUTPUT
    scaledTemp : REAL;
END_VAR
BEGIN
    // ERROR: implicit INT → REAL assignment not allowed
    #scaledTemp := #rawSensor;
END_FUNCTION_BLOCK
```

## Good Code
```scl
FUNCTION_BLOCK FB_TempScale
VERSION : 0.1
VAR_INPUT
    rawSensor : INT;
END_VAR
VAR_OUTPUT
    scaledTemp : REAL;
END_VAR
BEGIN
    // FIX: explicit conversion using INT_TO_REAL()
    #scaledTemp := INT_TO_REAL(#rawSensor);
END_FUNCTION_BLOCK
```

## Why
SCL on S7 is a strongly typed language. Unlike C or Python, it does not perform implicit widening conversions between numeric types. Even though INT fits within REAL's value range, the compiler requires an explicit conversion call (`INT_TO_REAL`, `DINT_TO_REAL`, etc.) to make the programmer's intent unambiguous and to prevent accidental data loss.

## Detection
Look for compiler errors containing phrases like:
- `Cannot convert type 'Int' to type 'Real'`
- `Implicit type conversion not allowed`
- `Type mismatch: expected REAL, got INT`

These appear in the TIA Portal compile output panel on the offending assignment line.

## Related
- `knowledge/scl-type-system.md` — full type conversion table
- `knowledge/scl-best-practices.md` — rule: all type conversions must be explicit
