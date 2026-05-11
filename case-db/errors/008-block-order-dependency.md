# Error 008: Block Order Dependency in External Source File

## Frontmatter
- **Tags**: order, dependency, generate
- **Error Type**: Compile

## Error Message
```
Block 'FB_Motor' referenced before declaration
```
Or from `GenerateBlocksFromSource`:
```
Error generating blocks: undefined symbol 'FB_Motor'
```
TIA Portal's SCL compiler processes a single external source file top-to-bottom. A block that references another block defined later in the same file triggers an undefined-symbol error.

## Bad Code
```scl
// ERROR: OB1 references FB_Motor, but FB_Motor is declared AFTER OB1

ORGANIZATION_BLOCK OB1
VERSION : 0.1
BEGIN
    DB_Motor(enable := TRUE);   // FB_Motor not yet seen by compiler
END_ORGANIZATION_BLOCK

DATA_BLOCK DB_Motor
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
FB_Motor
BEGIN
END_DATA_BLOCK

FUNCTION_BLOCK FB_Motor
VERSION : 0.1
VAR_INPUT
    enable : BOOL;
END_VAR
BEGIN
    // motor logic
END_FUNCTION_BLOCK
```

## Good Code
```scl
// FIX: correct order — UDTs → FCs → FBs → DBs → OBs

FUNCTION_BLOCK FB_Motor
VERSION : 0.1
VAR_INPUT
    enable : BOOL;
END_VAR
BEGIN
    // motor logic
END_FUNCTION_BLOCK

DATA_BLOCK DB_Motor
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
FB_Motor
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK OB1
VERSION : 0.1
BEGIN
    DB_Motor(enable := TRUE);   // FB_Motor and DB_Motor both declared above
END_ORGANIZATION_BLOCK
```

## Why
TIA Portal's `GenerateBlocksFromSource` compiles the external source file as a single translation unit, processing declarations sequentially. When OB1 calls `DB_Motor(...)`, the compiler must already know that `DB_Motor` is an instance of `FB_Motor` and that `FB_Motor` has the inputs being passed. If either block appears later in the file, the forward-reference resolution fails. The required declaration order is: TYPE (UDTs) → FUNCTION (FCs) → FUNCTION_BLOCK (FBs) → DATA_BLOCK (instance DBs) → ORGANIZATION_BLOCK (OBs).

## Detection
- `GenerateBlocksFromSource` returns an error referencing an undefined symbol
- Error line number points to the call site, not the definition
- Check source file ordering: search for OB/DB before their referenced FB definitions

## Related
- `.claude/rules/scl-rules.md` — block ordering: TYPE → FC → FB → DB → OB
- `case-db/errors/002-missing-instance-db.md` — instance DB requirements
