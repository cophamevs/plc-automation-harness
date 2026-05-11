# Error 003: Array Index Out of Bounds

## Frontmatter
- **Tags**: array, index, bounds
- **Error Type**: Runtime

## Error Message
Runtime symptom: access violation / unexpected values read, or TIA Portal diagnostics buffer shows:
```
Access error: array index out of range
```
No compile-time error is generated; SCL bounds checking occurs at runtime.

## Bad Code
```scl
FUNCTION_BLOCK FB_Buffer
VERSION : 0.1
VAR
    data : ARRAY[1..10] OF INT;
END_VAR
VAR_INPUT
    idx : INT;
END_VAR
VAR_OUTPUT
    value : INT;
END_VAR
BEGIN
    // ERROR: S7 arrays are 1-based; index 0 is out of bounds for ARRAY[1..10]
    #value := #data[0];
END_FUNCTION_BLOCK
```

## Good Code
```scl
FUNCTION_BLOCK FB_Buffer
VERSION : 0.1
VAR
    data : ARRAY[1..10] OF INT;
END_VAR
VAR_INPUT
    idx : INT;
END_VAR
VAR_OUTPUT
    value : INT;
END_VAR
BEGIN
    // FIX: use 1-based index; clamp if necessary
    IF #idx >= 1 AND #idx <= 10 THEN
        #value := #data[#idx];
    END_IF;
END_FUNCTION_BLOCK
```

## Why
TIA Portal SCL arrays can be declared with any lower bound, but the convention for S7 is `ARRAY[1..n]`. Accessing index 0 on a `[1..10]` array reads memory outside the declared range. The compiler does not catch this because the index can be a runtime variable. At runtime the CPU either returns garbage from adjacent memory or raises a diagnostic event (depending on CPU mode and settings).

## Detection
- No compile error; symptom appears at runtime
- Check the CPU diagnostic buffer in TIA Portal Online > Diagnostics
- Look for `OB121` (synchronous error OB) triggers if configured
- S7ReadVariable or S7ReadDB may return 0 or stale data for the out-of-range element

## Related
- `knowledge/scl-language-reference.md` — ARRAY declaration and 1-based indexing
- `.claude/rules/scl-rules.md` — rule 6: S7 uses 1-based arrays
