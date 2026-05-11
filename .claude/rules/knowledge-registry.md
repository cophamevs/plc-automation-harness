---
description: How to discover and load knowledge from the registry-based knowledge system
globs:
alwaysApply: false
---

# Knowledge Registry System

The knowledge base is registry-based and extensible. NEVER hardcode file paths — always discover through `_index.md` files.

## How to Find Knowledge
1. Read the relevant `_index.md` to see ALL available topics
2. Pick the file(s) that match your current task
3. Read only what you need — don't load everything

## Registries
| Need | Registry File |
|------|--------------|
| SCL syntax, CPU specs, API | `knowledge/_index.md` |
| Design patterns (state machine, timers, comms) | `knowledge/patterns/_index.md` |
| Industry examples (conveyor, motor, PID) | `knowledge/industry/_index.md` |
| Third-party libraries | `knowledge/libraries/_index.md` |
| Annotated examples (success + error cases) | `case-db/_index.md` |

## Quick Lookup
| Need | Read Directly |
|------|--------------|
| SCL syntax reference | `knowledge/scl-language-reference.md` |
| S7-1500 features | `knowledge/s7-1500.md` |
| S7-1200 limitations | `knowledge/s7-1200-limitations.md` |
| TIA Openness API | `knowledge/tia-openness-api.md` |

## Adding New Content
Every directory has a `_template.md`. Copy it, fill in the fields, and add an entry to `_index.md`.
