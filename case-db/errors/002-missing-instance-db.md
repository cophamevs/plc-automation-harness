# Error 002: Missing Instance Data Block for FB Call

## Frontmatter
- **Tags**: fb, instance, db
- **Error Type**: Compile

## Error Message
```
The block call requires an instance data block
```
Attempting to call a FUNCTION_BLOCK directly from an OB or FC without a named instance DB causes a compile error in TIA Portal.

## Bad Code
```scl
ORGANIZATION_BLOCK OB1
VERSION : 0.1
BEGIN
    // ERROR: FB_Motor called without an instance DB
    FB_Motor(enable := TRUE, speed := 1500);
END_ORGANIZATION_BLOCK
```

## Good Code
```scl
// FIX step 1: declare instance DB in the same source file (before OB1)
DATA_BLOCK DB_Motor
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
FB_Motor
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK OB1
VERSION : 0.1
BEGIN
    // FIX step 2: call the FB through its instance DB
    DB_Motor(enable := TRUE, speed := 1500);
END_ORGANIZATION_BLOCK
```

## Why
Every FUNCTION_BLOCK in S7 requires a dedicated DATA_BLOCK to store its static (VAR) memory between PLC scans. The instance DB is the FB's persistent state. Calling the FB by its type name, rather than through a DB instance, leaves the runtime with nowhere to store inter-scan state, hence the compile-time rejection.

## Detection
Compiler output contains:
- `The block call requires an instance data block`
- `FB call without instance DB`

Also seen when a `DATA_BLOCK` is declared but comes *after* the OB in the source — reorder so DBs appear before OBs (see error 008).

## Related
- `knowledge/scl-block-structure.md` — instance DB rules
- `case-db/errors/008-block-order-dependency.md` — ordering DBs before OBs
- `knowledge/scl-best-practices.md` — mandatory instance DB pattern
