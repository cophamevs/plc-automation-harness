# PLC Automation Harness — Cheat Sheet

## Skills (type in Claude Code)
| Command | What it does |
|---------|-------------|
| `/new-project` | Create project → add device → SCL → compile → simulate → verify |
| `/scl-inject` | Write SCL → generate blocks → compile (primary workflow) |
| `/debug-compile` | Fix compile errors in a loop (max 5 iterations) |
| `/download-test` | Download to PLC/PLCSim → verify via S7.Net read/write |
| `/modify-program` | Open existing project → explore → modify → recompile → save |
| `/tag-management` | Create tag tables, add/update/export/import tags |
| `/project-backup` | Save backup copy, compare with online PLC |

## Agents (type in Claude Code)
| Command | Role | Scope |
|---------|------|-------|
| `@plc-architect` | Design block structure | Architecture only, no code |
| `@scl-developer` | Write new SCL code | New code, 1 fix attempt max |
| `@scl-debugger` | Fix existing SCL errors | Iterative repair, max 5 loops |
| `@scl-reviewer` | Review code quality | 30-item checklist with severity |

### Agent Pipeline
```
@plc-architect → @scl-developer → @scl-reviewer
                      ↓ error?
                  @scl-debugger
```

## Before ANY TIA Portal Operation
```
GetState()        → IsConnected?
Connect()         → if not connected
GetProject()      → confirm project is open
GetProjectTree()  → find softwarePath (e.g. PLC_1/Program blocks)
```

## Device Config (after AddDevice)
| Setting | Value |
|---------|-------|
| PUT/GET communication | Enabled |
| Access level | Full access (no protection) |
| Protection password | Disabled |
| System/clock memory | Enabled (MB0/MB1) |
| DB access | Optimized (default) |

> `configureForSimulation=true` sets all of these automatically.

## SCL Code Injection (4 commands)
```
SetExternalSourceContent(softwarePath, sourceName, content)
GenerateBlocksFromSource(softwarePath, sourceName)
CompileSoftware(softwarePath)
GetBlocks(softwarePath)  → verify
```

## Block Order in Source (MUST follow)
1. TYPE (UDTs)
2. FUNCTION (FCs)
3. FUNCTION_BLOCK (FBs)
4. DATA_BLOCK (instance DBs)
5. ORGANIZATION_BLOCK (OBs)

## Top 12 SCL Rules
1. Always SCL — never LAD/FBD unless requested
2. Every FB needs an instance DB
3. No global variables inside FBs — use IN/OUT/INOUT
4. Explicit types — `INT_TO_REAL()`, no implicit conversion
5. `STRING[80]` — always specify length
6. `ARRAY[1..10]` — S7 is 1-based
7. REAL: `ABS(a - b) < epsilon` — never `=`
8. Check ENO after fallible instructions
9. Every FB: `Error : BOOL` + `ErrorID : INT` outputs
10. Prefixes: `FB_`, `FC_`, `DB_`, `UDT_`, `OB_`
11. NEVER use `%I`/`%Q`/`%M` addresses directly in SCL — create named tags first via `CreateTag`
12. OB VAR_TEMP must be >= 20 bytes — pad with `pad : ARRAY[0..18] OF BYTE`

## Before Download — PLCSim Advanced Check (plcsimadv-mcp)
```
GetInstances()                      → list existing instances
GetInstanceState(instanceName)      → check state (Off/Stop/Run)
SetManagerConfig(networkMode="TCPIPSingleAdapter")  → before CreateInstance
CreateInstance(instanceName, cpuType="1500", ipAddress)
StartInstance(instanceName)
```
- If existing instance has **same IP** → reuse it
- If IP conflict → create new instance with **different IP** + `SetDeviceAddress` to match
- Never create two instances with the same IP

## Safety — Confirm Before Calling
| Tool | Risk |
|------|------|
| `DownloadSoftware` | Overwrites PLC program |
| `S7WriteVariable` | Writes to running PLC memory |
| `S7WriteDB` | Writes raw bytes to data block |
| `StopInstance` (plcsimadv-mcp) | Stops running simulation |
| `DeleteInstance` (plcsimadv-mcp) | Deletes simulation instance |

## S7-1200 Forbidden Features
No VARIANT, LREAL, LINT, ULINT, LWORD, METHOD, PROPERTY, ARRAY[*].
Max 16 KB/DB. Max 6 nesting levels.

## Knowledge Lookup
| Need | Read |
|------|------|
| SCL syntax | `knowledge/scl-language-reference.md` |
| S7-1500 features | `knowledge/s7-1500.md` |
| S7-1200 limits | `knowledge/s7-1200-limitations.md` |
| Design patterns | `knowledge/patterns/_index.md` |
| Industry examples | `knowledge/industry/_index.md` |
| Error fixes | `case-db/_index.md` → errors/ |
| Success examples | `case-db/_index.md` → success/ |
