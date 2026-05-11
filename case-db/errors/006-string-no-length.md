# Error 006: STRING Declared Without Explicit Length

## Frontmatter
- **Tags**: string, length, declaration
- **Error Type**: Compile

## Error Message
```
STRING declaration requires an explicit length specifier [n]
```
TIA Portal V18+ may accept a bare `STRING` and default to 254 characters, but this behavior is version-dependent. Best practice requires explicit length to avoid compiler warnings, memory waste, and cross-version inconsistency.

## Bad Code
```scl
FUNCTION_BLOCK FB_Logger
VERSION : 0.1
VAR
    // WARNING/ERROR: STRING without length is ambiguous
    message : STRING;
    errorText : STRING;
END_VAR
BEGIN
    #message := 'Pump started';
    #errorText := 'No error';
END_FUNCTION_BLOCK
```

## Good Code
```scl
FUNCTION_BLOCK FB_Logger
VERSION : 0.1
VAR
    // FIX: explicit STRING length avoids ambiguity and memory waste
    message   : STRING[80];
    errorText : STRING[40];
END_VAR
BEGIN
    #message   := 'Pump started';
    #errorText := 'No error';
END_FUNCTION_BLOCK
```

## Why
On S7-1500/1200, `STRING` without `[n]` allocates the maximum 254-character buffer (2 + 254 = 256 bytes) for each variable. In data-intensive programs this wastes significant DB memory. More critically, the actual maximum length stored in the string header is 254, which may differ from what downstream string-processing FBs expect. Specifying `STRING[n]` makes the memory footprint explicit, prevents accidental truncation, and ensures consistent behavior across TIA Portal versions.

## Detection
- Compiler warning: `STRING without length specifier; defaulting to STRING[254]`
- Or compile error in strict mode / newer TIA Portal versions
- Review all `STRING` declarations for missing `[n]` using a search for `: STRING` (without a following `[`)

## Related
- `knowledge/scl-language-reference.md` — STRING type and length declaration
- `.claude/rules/scl-rules.md` — rule 5: always specify STRING[n]
