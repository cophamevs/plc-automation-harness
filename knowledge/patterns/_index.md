# SCL Patterns

> Reusable design patterns for S7-1500/S7-1200 PLC programming in SCL.

| File | Description | Tags | CPU |
|------|-------------|------|-----|
| state-machine.md | Enum-based FSM with entry/exit actions, timer transitions | fsm, sequence, step, case | Both |
| alarm-management.md | Program Alarm, diagnostic buffer, alarm classes | alarm, diagnostic, fault | Both |
| timer-counter.md | TON/TOF/TP patterns, cascaded timers, pulse generators, R_TRIG placement | timer, counter, delay, pulse, rtrig | Both |
| data-logging.md | Ring buffer, recipe DB, FIFO shift register with cascading fix | logging, recipe, buffer, data, fifo | Both |
| communication.md | PUT/GET, OUC TCP/UDP, MODBUS TCP, S7 communication | comm, tcp, modbus, putget | Both |
| error-handling.md | ENO chain, status word pattern, error aggregation, non-empty ELSE | error, eno, status, fault, failsafe | Both |
| multi-instance.md | Multi-instance FB architecture — eliminate DB explosion, hierarchical symbolic access | multi-instance, fb, memory, db-explosion, hierarchy | Both |
