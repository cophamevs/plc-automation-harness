---
description: S7-1200 restrictions - MUST check when target CPU is S7-1200
globs:
alwaysApply: false
---

# S7-1200 Compatibility Rules

When the target PLC is S7-1200, these features are FORBIDDEN:

| Feature | S7-1500 | S7-1200 | Workaround |
|---------|---------|---------|------------|
| VARIANT | Yes | NO | Use ANY or overloaded FBs |
| LREAL (64-bit float) | Yes | NO | Use REAL (32-bit) |
| LINT (64-bit int) | Yes | NO | Use DINT (32-bit) |
| ULINT, LWORD | Yes | NO | Use UDINT, DWORD |
| METHOD/PROPERTY | Yes | NO | Use separate FCs |
| ARRAY[*] | Yes | NO | Fixed-length arrays only |
| Max DB size | 64 MB | 16 KB | Split into multiple DBs |
| Nesting depth | 24 | 6 | Flatten call hierarchy |
| System clock memory | Always available | Must enable in device config | Enable in HW config first |

Always ask the user which CPU they're targeting BEFORE writing SCL code.

For detailed workarounds with code examples, read `knowledge/s7-1200-limitations.md`.
