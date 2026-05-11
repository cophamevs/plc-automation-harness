# Error 010: VARIANT Data Type Not Supported on S7-1200

## Frontmatter
- **Tags**: 1200, variant, lreal, compat
- **Error Type**: Compile

## Error Message
```
The data type 'VARIANT' is not supported for this CPU
```
S7-1200 CPUs do not support the VARIANT, LREAL, LINT, ULINT, or LWORD data types. Code that uses these types compiles on S7-1500 targets but fails when the target is changed to an S7-1200.

## Bad Code
```scl
// ERROR: VARIANT is an S7-1500-only feature; will not compile for S7-1200

FUNCTION FC_ProcessAny
VERSION : 0.1
VAR_INPUT
    // VARIANT can hold any data type — not available on S7-1200
    inputData : VARIANT;
END_VAR
VAR_OUTPUT
    result : REAL;
END_VAR
BEGIN
    // process inputData generically
    #result := 0.0;
END_FUNCTION
```

## Good Code
```scl
// FIX option A: replace VARIANT with a specific type for the known use case

FUNCTION FC_ProcessReal
VERSION : 0.1
VAR_INPUT
    inputData : REAL;   // concrete type — works on S7-1200
END_VAR
VAR_OUTPUT
    result : REAL;
END_VAR
BEGIN
    #result := #inputData * 1.0;
END_FUNCTION

// FIX option B: if polymorphism is truly needed, use ANY pointer
// (ANY is supported on S7-1200 in specific contexts — verify CPU firmware version)
FUNCTION FC_ProcessAny
VERSION : 0.1
VAR_INPUT
    inputData : ANY;
END_VAR
VAR_OUTPUT
    result : REAL;
END_VAR
BEGIN
    #result := 0.0;
END_FUNCTION
```

## Why
The VARIANT data type (introduced for S7-1500 and SCL structured programming) allows a variable to hold a reference to any data type at runtime. The S7-1200 CPU firmware and instruction set do not implement VARIANT. The same restriction applies to LREAL (64-bit float), LINT/ULINT (64-bit integers), LWORD (64-bit bitstring), METHOD, PROPERTY, and ARRAY[*] (open arrays). When targeting S7-1200, use concrete types or the older ANY pointer mechanism where generic handling is required.

## Detection
- Compile error: `The data type 'VARIANT' is not supported for this CPU`
- Check the project's target CPU type in TIA Portal Device view before writing SCL
- Additional S7-1200 unsupported features: LREAL, LINT, ULINT, LWORD, METHOD, PROPERTY, ARRAY[*]
- Review checklist item: "S7-1200: No VARIANT, LREAL, LINT, ULINT, LWORD"

## Related
- `knowledge/s7-1200-constraints.md` — full list of S7-1200 type and feature restrictions
- `knowledge/scl-best-practices.md` — CPU compatibility checklist
- `prompts/review-checklist.md` — S7-1200 section
