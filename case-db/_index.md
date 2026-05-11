# Case Database

> Annotated input→output examples for few-shot learning. Agents should search
> this index by tags to find similar cases before writing new code.

## Success Cases
| File | Description | Tags | CPU | Complexity |
|------|-------------|------|-----|------------|
| success/001-blink-led.md | Toggle output every 1 second | timer, output, basic | Both | Beginner |
| success/002-motor-start-stop.md | FB with Start/Stop/Running/Fault | motor, fb, state | Both | Beginner |
| success/003-traffic-light.md | State machine with timer transitions | fsm, timer, case | Both | Intermediate |
| success/004-conveyor-sequence.md | Multi-FB conveyor with jam detection | conveyor, sequence, multi-fb | Both | Intermediate |
| success/005-pid-temperature.md | PID_Compact temperature control | pid, temperature, tech-object | 1500 | Intermediate |
| success/006-recipe-management.md | Recipe storage and loading from global DB | recipe, db, data | Both | Intermediate |
| success/007-alarm-handler.md | Centralized alarm collection and reporting | alarm, diagnostic, handler | Both | Intermediate |
| success/008-modbus-tcp-client.md | MODBUS TCP read/write to external device | modbus, tcp, communication | Both | Advanced |
| success/009-data-logger.md | Ring buffer data logging to DB | logging, buffer, timestamp | Both | Intermediate |
| success/010-star-delta-starter.md | Star-delta motor start sequence with timers | motor, star-delta, timer | Both | Intermediate |

## Error Cases
| File | Description | Tags | Error Type |
|------|-------------|------|------------|
| errors/001-type-mismatch.md | INT assigned to REAL without conversion | type, conversion, int, real | Compile |
| errors/002-missing-instance-db.md | FB called without DATA_BLOCK | fb, instance, db | Compile |
| errors/003-array-bounds.md | Array index 0 on 1-based array | array, index, bounds | Runtime |
| errors/004-timer-in-temp.md | Timer declared in VAR_TEMP loses state | timer, temp, static | Runtime |
| errors/005-missing-hash-prefix.md | Local variable without # prefix | variable, hash, prefix | Compile |
| errors/006-string-no-length.md | STRING without [n] length specifier | string, length, declaration | Compile |
| errors/007-real-equality.md | REAL compared with = instead of epsilon | real, float, comparison | Logic |
| errors/008-block-order-dependency.md | FB referenced before declaration in source | order, dependency, generate | Compile |
| errors/009-optimized-access-conflict.md | S7_Optimized_Access blocks S7.Net read | optimized, access, s7net | Runtime |
| errors/010-s7-1200-unsupported-type.md | VARIANT/LREAL used on S7-1200 target | 1200, variant, lreal, compat | Compile |

## Planned Cases (not yet created)
**Success — Advanced:**
- 011 — Multi-PLC S7 communication with handshake
- 012 — Complex multi-FB system with error propagation
- 013 — Valve sequencing with interlock logic

**Error — Advanced:**
- 011 — Communication timeout not handled (PUT/GET)
- 012 — DB size exceeds S7-1200 16KB limit
