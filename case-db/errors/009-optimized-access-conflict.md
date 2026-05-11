# Error 009: Optimized DB Access Conflicts with S7.Net Reads

## Frontmatter
- **Tags**: optimized, access, s7net
- **Error Type**: Runtime

## Error Message
Runtime symptom — no compile error:
```
S7ReadDB / S7ReadDBStruct returns 0 or garbage values for all fields
```
S7.Net (and the MCP tools `S7ReadVariable`, `S7ReadDB`, `S7ReadDBStruct`) use classic byte-offset addressing, which is incompatible with TIA Portal's "optimized" DB layout.

## Bad Code
```scl
// ERROR: DB declared without disabling optimized access
DATA_BLOCK DB_ProcessData
VERSION : 0.1
STRUCT
    setpoint  : REAL;    // expected at byte 0, but optimizer may place anywhere
    actual    : REAL;    // expected at byte 4, but optimizer re-orders freely
    errorCode : INT;     // expected at byte 8
END_STRUCT
BEGIN
    setpoint  := 0.0;
    actual    := 0.0;
    errorCode := 0;
END_DATA_BLOCK
```

## Good Code
```scl
// FIX: disable optimized access so byte offsets are fixed and predictable
DATA_BLOCK DB_ProcessData
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
STRUCT
    setpoint  : REAL;    // byte 0
    actual    : REAL;    // byte 4
    errorCode : INT;     // byte 8
END_STRUCT
BEGIN
    setpoint  := 0.0;
    actual    := 0.0;
    errorCode := 0;
END_DATA_BLOCK
```

## Why
TIA Portal's optimized DB layout packs variables for fastest PLC-internal access, ignoring classic byte offsets. S7.Net (and the underlying S7 communication protocol used by `S7ReadVariable`, `S7ReadDB`, `S7ReadDBStruct`) addresses DB variables using absolute byte offsets. When optimized access is enabled, the byte offsets S7.Net calculates do not match the actual memory positions chosen by the optimizer, resulting in reads returning 0 or data from the wrong fields. Setting `{ S7_Optimized_Access := 'FALSE' }` forces the classic fixed layout.

## Detection
- No compile error; symptom at runtime
- `S7ReadVariable` or `S7ReadDBStruct` returns all zeros or implausible values
- Verify in TIA Portal: right-click DB > Properties > Attributes > "Optimized block access" should be unchecked
- MCP tool `S7ReadDB` will silently return wrong offsets for optimized DBs

## Related
- `knowledge/tia-openness-api.md` — S7 Runtime tools: S7ReadVariable, S7ReadDB, S7ReadDBStruct
- `.claude/rules/s7-1500-features.md` — optimized DB access and S7_Optimized_Access setting
