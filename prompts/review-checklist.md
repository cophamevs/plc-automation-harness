# SCL Code Review Checklist

Quick self-review after generating SCL code. Check each item.

## Structure
- [ ] Each FB has single responsibility
- [ ] No global variable access inside FBs
- [ ] Instance DBs created for every FB call
- [ ] Block order correct: UDTs → FCs → FBs → DBs → OBs

## Safety
- [ ] No division by zero possible
- [ ] Array access within declared bounds
- [ ] REAL comparison uses epsilon (not =)
- [ ] No infinite loops

## Type Safety
- [ ] All type conversions explicit
- [ ] STRING length specified: STRING[n]
- [ ] Timers in VAR (static), not VAR_TEMP

## Completeness
- [ ] VERSION declared on every block
- [ ] Every FB has Error/ErrorID outputs
- [ ] CASE has ELSE branch
- [ ] OB1 calls all FB instances

## S7-1200 (if applicable)
- [ ] No VARIANT, LREAL, LINT, ULINT, LWORD
- [ ] No METHOD/PROPERTY
- [ ] No ARRAY[*]
- [ ] DB size ≤ 16 KB
- [ ] Call nesting ≤ 6 levels
