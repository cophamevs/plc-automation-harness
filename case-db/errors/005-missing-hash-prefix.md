# Error 005: Missing # Prefix for Local FB Variables

## Frontmatter
- **Tags**: variable, hash, prefix
- **Error Type**: Compile

## Error Message
```
Identifier 'myVar' is not declared
```
Or, if a symbol with the same name exists at a higher scope (e.g., a global DB tag), the compiler silently resolves to the wrong variable — producing a logic error rather than a compile error.

## Bad Code
```scl
FUNCTION_BLOCK FB_Calc
VERSION : 0.1
VAR
    result : REAL;
END_VAR
VAR_INPUT
    operand : REAL;
END_VAR
BEGIN
    // ERROR: local variable must be prefixed with #
    result := operand * 2.0;
END_FUNCTION_BLOCK
```

## Good Code
```scl
FUNCTION_BLOCK FB_Calc
VERSION : 0.1
VAR
    result : REAL;
END_VAR
VAR_INPUT
    operand : REAL;
END_VAR
BEGIN
    // FIX: use # prefix for all local/instance variables
    #result := #operand * 2.0;
END_FUNCTION_BLOCK
```

## Why
In TIA Portal SCL, the `#` prefix is mandatory for all local block variables (VAR, VAR_INPUT, VAR_OUTPUT, VAR_IN_OUT, VAR_TEMP, VAR_CONSTANT) inside FUNCTION_BLOCK, FUNCTION, and ORGANIZATION_BLOCK bodies. This prefix distinguishes local scope from global scope (tag tables, shared DBs). Without `#`, the compiler looks in global scope first; if found there the wrong variable is used silently; if not found a compile error is raised. Always prefix local references with `#`.

## Detection
- Compile error: `Identifier 'xxx' is not declared` on the offending line
- Or: unexpected values at runtime because a global tag is being written instead of the local variable
- Search the generated SCL for unqualified identifiers (no `#`, no DB-dot notation, no system namespace)

## Related
- `knowledge/scl-language-reference.md` — variable scoping and # prefix rules
- `.claude/rules/scl-rules.md` — SCL syntax quick reference
