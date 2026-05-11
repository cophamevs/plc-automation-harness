---
description: S7-1500 specific features that are OK to use when targeting S7-1500
globs:
alwaysApply: false
---

# S7-1500 Features

These features are available ONLY on S7-1500 (not S7-1200):

- **VARIANT** type for generic FB interfaces — use with `TypeOf()` + `MOVE_BLK_VARIANT`
- **LREAL** (64-bit float), **LINT** (64-bit int), **ULINT**, **LWORD**
- **OOP**: METHOD, PROPERTY in FBs (use sparingly — most PLC programmers don't expect it)
- **Named constructors** for UDTs
- **ARRAY[*]** (variable-length arrays in IN/OUT parameters)
- **64 MB** max per DB (vs 16 KB on S7-1200)
- **24 nesting levels** for FC/FB calls (vs 6 on S7-1200)
- **Optimized DB access** by default (better performance, but blocks S7.Net direct access)

For S7.Net runtime access, set `{ S7_Optimized_Access := 'FALSE' }` on DBs.

For detailed reference, read `knowledge/s7-1500.md`.
