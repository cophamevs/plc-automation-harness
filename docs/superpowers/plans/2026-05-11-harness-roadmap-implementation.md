# Harness Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the content gaps identified in the harness evaluation — 4 industry examples, 5 case studies, 2 library references, 2 new skills.

**Architecture:** Pure markdown content following existing templates (`_template.md` in each directory). Each file follows the established structure: Frontmatter, Requirements/Overview, SCL Code (complete and compilable), Test Procedure/Usage Examples. All SCL code must follow rules in `.claude/rules/scl-rules.md`: block ordering, Error/ErrorID outputs, explicit types, STRING[n], 1-based arrays, VERSION on every block, `S7_Optimized_Access := 'FALSE'` on instance DBs.

**Tech Stack:** Markdown, SCL (IEC 61131-3), tiaportal-mcp MCP tools

---

## File Map

### Industry Examples (P1.1)
- Create: `knowledge/industry/valve-control.md`
- Create: `knowledge/industry/multi-plc-comm.md`
- Create: `knowledge/industry/hmi-interface.md`
- Create: `knowledge/industry/profinet-diagnostics.md`
- Modify: `knowledge/industry/_index.md` (move planned items to actual entries)

### Case Studies (P1.2)
- Create: `case-db/success/011-multi-plc-comm.md`
- Create: `case-db/success/012-multi-fb-system.md`
- Create: `case-db/success/013-valve-sequence.md`
- Create: `case-db/errors/011-comm-timeout.md`
- Create: `case-db/errors/012-db-size-exceeded.md`
- Modify: `case-db/_index.md` (move planned items to actual entries)

### Library References (P1.3)
- Create: `knowledge/libraries/lgf.md`
- Create: `knowledge/libraries/oscat.md`
- Modify: `knowledge/libraries/_index.md` (add entries)

### Skills (P2.1, P2.2)
- Create: `.claude/skills/tag-management/SKILL.md`
- Create: `.claude/skills/project-backup/SKILL.md`
- Modify: `CLAUDE.md` (add 2 skills to skills list)
- Modify: `docs/cheat-sheet.md` (add 2 skills to skills table)

---

## Task 1: Industry Example — Valve Control

**Files:**
- Create: `knowledge/industry/valve-control.md`

- [ ] **Step 1: Create valve-control.md with full content**

Use the template structure from `knowledge/industry/_template.md`. Reference `knowledge/industry/conveyor-control.md` for the expected depth (Frontmatter, Requirements with I/O table, Block Structure table, complete compilable SCL, Test Procedure with MCP commands + S7ReadVariable addresses, Variations).

Content requirements:
- Frontmatter: Tags `valve, control, feedback, solenoid, modulating`, CPU `Both`, Difficulty `Intermediate`
- Requirements: On/off valve with open/close feedback sensors, timeout detection, manual override. Include I/O table.
- Block Structure: `UDT_ValveData` (status structure), `FB_Valve` (control with state machine: Idle/Opening/Open/Closing/Closed/Fault), instance DB, OB1
- SCL Code must include:
  - State machine with timer-based timeout (valve doesn't reach position within configurable time)
  - Open/close feedback monitoring
  - Error/ErrorID outputs (0=none, 1=OpenTimeout, 2=CloseTimeout, 3=BothFeedbacks)
  - Manual override input that bypasses state machine
  - All blocks in dependency order: UDT → FB → DB → OB
  - VERSION on every block, `S7_Optimized_Access := 'FALSE'` on DB
- Test Procedure: exact MCP deploy commands + S7ReadVariable addresses for state, position, error
- Variations: Modulating valve with analog setpoint (REAL 0.0-100.0%), S7-1200 notes

- [ ] **Step 2: Verify SCL code quality**

Self-review against `.claude/rules/scl-rules.md`:
- Block order correct (UDT → FB → DB → OB)
- Every FB has `Error : BOOL` and `ErrorID : INT`
- `#` prefix on all local variables
- STRING[n] with explicit length
- REAL comparison uses epsilon
- CASE has ELSE branch
- Timers in VAR (static)
- VERSION on every block

- [ ] **Step 3: Commit**

```bash
git add knowledge/industry/valve-control.md
git commit -m "feat: add valve control industry example"
```

---

## Task 2: Industry Example — Multi-PLC Communication

**Files:**
- Create: `knowledge/industry/multi-plc-comm.md`

- [ ] **Step 1: Create multi-plc-comm.md with full content**

Content requirements:
- Frontmatter: Tags `communication, putget, s7comm, multi-plc, handshake`, CPU `Both`, Difficulty `Advanced`
- Requirements: Two S7 PLCs exchanging data via PUT/GET. PLC_A sends setpoints, PLC_B sends status back. Include handshake mechanism (sequence counter) to detect stale data.
- Block Structure: `UDT_CommData` (shared data structure), `FB_S7Sender` (PUT with handshake), `FB_S7Receiver` (GET with stale detection), instance DBs, OB1
- SCL Code must include:
  - PUT block call with REQ/DONE/BUSY/ERROR handling
  - GET block call with NDR/BUSY/ERROR handling
  - Sequence counter that increments on each successful send
  - Stale data detection: if sequence counter hasn't changed for > configurable timeout, set CommFault
  - Retry logic: up to 3 retries before flagging permanent error
  - Error/ErrorID outputs on both FBs
- Test Procedure: deploy commands, S7ReadVariable addresses for comm status, sequence counter, error flags
- Variations: Using Open User Communication (OUC) TCP instead of PUT/GET, S7-1200 notes (PUT/GET must be enabled in device config)

- [ ] **Step 2: Verify SCL code quality**

Same checklist as Task 1 Step 2.

- [ ] **Step 3: Commit**

```bash
git add knowledge/industry/multi-plc-comm.md
git commit -m "feat: add multi-PLC communication industry example"
```

---

## Task 3: Industry Example — HMI Interface

**Files:**
- Create: `knowledge/industry/hmi-interface.md`

- [ ] **Step 1: Create hmi-interface.md with full content**

Content requirements:
- Frontmatter: Tags `hmi, interface, screen, alarm, data-exchange, visualization`, CPU `Both`, Difficulty `Intermediate`
- Requirements: Standard HMI data exchange pattern. PLC provides a "HMI interface DB" containing all data the HMI reads/writes. Includes screen navigation, operating mode (Auto/Manual/Service), command handshake (HMI writes command → PLC acknowledges → HMI clears).
- Block Structure: `UDT_HmiCommand` (command handshake structure), `UDT_HmiStatus` (status structure), `DB_HmiInterface` (global DB, non-optimized), `FB_HmiHandler` (processes commands, updates status), instance DB, OB1
- SCL Code must include:
  - Global DB with clear sections: Status (PLC→HMI), Commands (HMI→PLC), Parameters (bidirectional)
  - Command handshake: HMI sets `CmdRequest := TRUE` + `CmdID`, PLC processes, sets `CmdAck := TRUE`, HMI clears `CmdRequest`, PLC clears `CmdAck`
  - Operating mode enum (0=Auto, 1=Manual, 2=Service) with transition validation
  - `S7_Optimized_Access := 'FALSE'` on the HMI DB (mandatory for HMI tag binding)
  - Error/ErrorID on FB_HmiHandler
- Test Procedure: deploy, S7ReadVariable for mode, command status; S7WriteVariable to simulate HMI command
- Variations: Multiple HMI panels (separate DBs per panel), alarm text integration

- [ ] **Step 2: Verify SCL code quality**

Same checklist as Task 1 Step 2.

- [ ] **Step 3: Commit**

```bash
git add knowledge/industry/hmi-interface.md
git commit -m "feat: add HMI interface industry example"
```

---

## Task 4: Industry Example — PROFINET Diagnostics

**Files:**
- Create: `knowledge/industry/profinet-diagnostics.md`

- [ ] **Step 1: Create profinet-diagnostics.md with full content**

Content requirements:
- Frontmatter: Tags `profinet, diagnostics, station-failure, device-status, io-device`, CPU `Both`, Difficulty `Advanced`
- Requirements: Monitor PROFINET I/O device status. Detect station failure (device goes offline), log events, provide aggregated status for HMI. Use OB86 (rack failure) for immediate detection and cyclic polling via `DeviceStates` SFB for status overview.
- Block Structure: `UDT_DeviceStatus` (per-device status), `FB_ProfinetMonitor` (monitors N devices), `DB_PnConfig` (device list with expected addresses), instance DB, OB1, OB86
- SCL Code must include:
  - OB86 handler that captures the failing station info from OB86 start info
  - FB that maintains an array of device statuses with fields: Online (BOOL), FailCount (INT), LastFailTime (TIME), Name (STRING[32])
  - Aggregated status: AllOnline (BOOL), DevicesOffline (INT)
  - Error/ErrorID on FB_ProfinetMonitor
  - Note: OB86 receives `OB86_FLT_ID` containing the hardware identifier of the failing device
- Test Procedure: deploy, simulate station failure via PLCSim, read device status array via S7ReadDB
- Variations: S7-1200 limitations (max array size, no LREAL for timestamps — use DINT ms counter)

- [ ] **Step 2: Verify SCL code quality**

Same checklist as Task 1 Step 2. Extra check: OB86 requires specific VAR_TEMP variables from the start info.

- [ ] **Step 3: Commit**

```bash
git add knowledge/industry/profinet-diagnostics.md
git commit -m "feat: add PROFINET diagnostics industry example"
```

---

## Task 5: Update Industry Index

**Files:**
- Modify: `knowledge/industry/_index.md`

- [ ] **Step 1: Move planned entries to actual entries in _index.md**

Replace the "Planned (not yet created)" section. Move the 4 entries into the main table:

```markdown
| File | Description | Tags | CPU |
|------|-------------|------|-----|
| conveyor-control.md | Belt conveyor with sensors, jam detection, sequences | conveyor, belt, sensor, jam | Both |
| motor-starter.md | DOL, star-delta, VFD control patterns | motor, dol, star-delta, vfd | Both |
| pid-loop.md | PID_Compact usage, manual/auto mode, tuning | pid, temperature, control, tuning | 1500 |
| batch-process.md | ISA-88 batch concepts: fill/heat/drain phases | batch, isa88, phase, recipe | Both |
| valve-control.md | On/off and modulating valve control with feedback monitoring | valve, control, feedback, solenoid | Both |
| multi-plc-comm.md | S7 communication between PLCs via PUT/GET with handshake | communication, putget, s7comm, multi-plc | Both |
| hmi-interface.md | HMI data exchange patterns, command handshake, operating modes | hmi, interface, screen, data-exchange | Both |
| profinet-diagnostics.md | PROFINET device diagnostics, station failure handling via OB86 | profinet, diagnostics, station-failure, io-device | Both |
```

Remove the "Planned" section entirely.

- [ ] **Step 2: Commit**

```bash
git add knowledge/industry/_index.md
git commit -m "docs: update industry index with 4 new examples"
```

---

## Task 6: Success Case — Multi-PLC Communication

**Files:**
- Create: `case-db/success/011-multi-plc-comm.md`

- [ ] **Step 1: Create 011-multi-plc-comm.md**

Follow the template from `case-db/success/_template.md`. Reference `case-db/success/008-modbus-tcp-client.md` for Advanced-level depth.

Content requirements:
- Frontmatter: Tags `communication, putget, s7, handshake, multi-plc`, CPU `Both`, Complexity `Advanced`
- Requirements: PLC_A sends a setpoint (REAL) and mode (INT) to PLC_B. PLC_B returns actual value (REAL) and status (INT). Handshake via sequence counter.
- Block Structure: FB_S7Writer (PUT), FB_S7Reader (GET), UDT for shared data, instance DBs, OB1
- SCL Code: Complete, compilable. Simpler than the industry example (focused on one direction). Include PUT call with REQ/DONE/ERROR, sequence counter increment, Error/ErrorID.
- MCP Commands: SetExternalSourceContent → GenerateBlocksFromSource → CompileSoftware → DownloadSoftware
- Key Decisions: Why PUT/GET over OUC (simpler, no socket management), why handshake (detect stale data), why non-optimized DB (cross-PLC access)
- Test Procedure: S7ReadVariable addresses for sequence counter, data values, error status

- [ ] **Step 2: Verify SCL code quality**

Same checklist as Task 1 Step 2.

- [ ] **Step 3: Commit**

```bash
git add case-db/success/011-multi-plc-comm.md
git commit -m "feat: add success case 011 — multi-PLC communication"
```

---

## Task 7: Success Case — Multi-FB System with Error Propagation

**Files:**
- Create: `case-db/success/012-multi-fb-system.md`

- [ ] **Step 1: Create 012-multi-fb-system.md**

Content requirements:
- Frontmatter: Tags `multi-fb, error-propagation, aggregation, hierarchy, advanced`, CPU `Both`, Complexity `Advanced`
- Requirements: System with 3 FBs (FB_Pump, FB_Valve, FB_Tank) where FB_Tank orchestrates FB_Pump and FB_Valve. Errors from child FBs propagate up to FB_Tank's Error/ErrorID outputs. Demonstrates the harness's recommended error handling pattern.
- Block Structure: FB_Pump (start/stop with overload detection), FB_Valve (open/close with timeout), FB_Tank (orchestrates fill/drain cycle using pump + valve), instance DBs for all, OB1
- SCL Code: Complete. FB_Tank calls FB_Pump and FB_Valve via their instance DBs. After each call, checks child Error outputs. If any child has Error=TRUE, FB_Tank sets its own Error=TRUE and ErrorID = 100 + child's ErrorID (offset per child).
- Key Decisions: Why error offset pattern (disambiguate source), why 1-level nesting only (readability), why separate FBs vs one big FB (reusability)
- Test Procedure: S7ReadVariable for tank state, pump status, valve status, aggregated error

- [ ] **Step 2: Verify SCL code quality**

Same checklist. Extra check: FB nesting is exactly 1 level (OB1 → FB_Tank → FB_Pump/FB_Valve).

- [ ] **Step 3: Commit**

```bash
git add case-db/success/012-multi-fb-system.md
git commit -m "feat: add success case 012 — multi-FB system with error propagation"
```

---

## Task 8: Success Case — Valve Sequencing with Interlocks

**Files:**
- Create: `case-db/success/013-valve-sequence.md`

- [ ] **Step 1: Create 013-valve-sequence.md**

Content requirements:
- Frontmatter: Tags `valve, sequence, interlock, safety, state-machine`, CPU `Both`, Complexity `Advanced`
- Requirements: 3 valves (V1 inlet, V2 outlet, V3 drain) with interlock rules: V2 cannot open unless V1 is open, V3 cannot open unless V2 is closed. Sequence: Open V1 → wait fill level → Open V2 → wait drain → Close V2 → Close V1.
- Block Structure: FB_InterlockValve (valve with interlock input), FB_ValveSequencer (state machine orchestrating 3 valves), instance DBs, OB1
- SCL Code: Complete. FB_InterlockValve extends the valve control pattern with an `InterlockOK` input — if FALSE, valve cannot open and immediately closes. FB_ValveSequencer uses CASE states: Idle/FillStart/Filling/DrainStart/Draining/Complete/Fault.
- Key Decisions: Why interlock at FB level (reusable), why sequence as state machine (clear, debuggable)
- Test Procedure: S7ReadVariable for sequence state, each valve's position, interlock status

- [ ] **Step 2: Verify SCL code quality**

Same checklist.

- [ ] **Step 3: Commit**

```bash
git add case-db/success/013-valve-sequence.md
git commit -m "feat: add success case 013 — valve sequence with interlocks"
```

---

## Task 9: Error Case — Communication Timeout Not Handled

**Files:**
- Create: `case-db/errors/011-comm-timeout.md`

- [ ] **Step 1: Create 011-comm-timeout.md**

Follow the template from `case-db/errors/_template.md`.

Content requirements:
- Frontmatter: Tags `communication, timeout, putget, error-handling`, Error Type `Runtime`
- Error Message: No compile error. Runtime symptom: PLC hangs or data goes stale when remote PLC disconnects.
- Bad Code: FB calling PUT with `REQ := TRUE` every scan but never checking `ERROR` or `STATUS` outputs. No timeout timer. No retry count.
- Good Code: FB with state machine: Idle → Requesting → WaitDone → Success/Error. Checks BUSY/DONE/ERROR. Has timeout timer (if BUSY for > 5s, abort). Retry counter (max 3). Sets Error/ErrorID on permanent failure.
- Why: PUT/GET are asynchronous — they take multiple scan cycles. If ERROR is never checked, the FB stays in a requesting state forever when the remote PLC is unreachable. The PLC continues running but the data exchange silently stops.
- Detection: Watch Table shows `BUSY` stuck at TRUE for the PUT/GET call. Data values never update. No error logged because ERROR output is ignored.
- Related: `knowledge/patterns/communication.md`, `knowledge/patterns/error-handling.md`

- [ ] **Step 2: Commit**

```bash
git add case-db/errors/011-comm-timeout.md
git commit -m "feat: add error case 011 — communication timeout not handled"
```

---

## Task 10: Error Case — DB Size Exceeds S7-1200 Limit

**Files:**
- Create: `case-db/errors/012-db-size-exceeded.md`

- [ ] **Step 1: Create 012-db-size-exceeded.md**

Content requirements:
- Frontmatter: Tags `1200, db-size, limit, memory, data-block`, Error Type `Compile`
- Error Message: `Data block size exceeds maximum (16384 bytes)` or `Memory area exceeded`
- Bad Code: A DB with `ARRAY[1..500] OF REAL` (500 * 4 = 2000 bytes, OK) PLUS a large struct with multiple arrays totaling > 16 KB. Show a concrete example: `ARRAY[1..1000] OF UDT_DataPoint` where UDT_DataPoint is ~20 bytes = 20,000 bytes > 16 KB.
- Good Code: Split into two DBs: `DB_DataLog_Part1` (first 400 entries) and `DB_DataLog_Part2` (remaining 600 entries). Each under 16 KB. Show the split with index calculation: `IF #idx <= 400 THEN ... DB_Part1 ... ELSE ... DB_Part2 ...`.
- Why: S7-1200 CPUs have a hardware-enforced 16 KB (16,384 bytes) maximum per data block. S7-1500 allows up to 64 MB. Code targeting S7-1200 must split large data structures across multiple DBs.
- Detection: Compile error referencing the DB name and maximum size. Also visible in TIA Portal DB properties → Size field exceeding 16384.
- Related: `knowledge/s7-1200-limitations.md`, `.claude/rules/s7-1200-compat.md`

- [ ] **Step 2: Commit**

```bash
git add case-db/errors/012-db-size-exceeded.md
git commit -m "feat: add error case 012 — DB size exceeds S7-1200 limit"
```

---

## Task 11: Update Case-DB Index

**Files:**
- Modify: `case-db/_index.md`

- [ ] **Step 1: Move planned entries to actual entries**

In the Success Cases table, add after entry 010:

```markdown
| success/011-multi-plc-comm.md | S7 communication between PLCs with handshake | putget, s7, handshake, comm | Both | Advanced |
| success/012-multi-fb-system.md | Multi-FB system with error propagation | multi-fb, error, hierarchy | Both | Advanced |
| success/013-valve-sequence.md | Valve sequencing with interlock logic | valve, sequence, interlock | Both | Advanced |
```

In the Error Cases table, add after entry 010:

```markdown
| errors/011-comm-timeout.md | PUT/GET timeout not handled | communication, timeout, putget | Runtime |
| errors/012-db-size-exceeded.md | DB size exceeds S7-1200 16KB limit | 1200, db-size, limit, memory | Compile |
```

Remove the "Planned Cases" section entirely.

- [ ] **Step 2: Commit**

```bash
git add case-db/_index.md
git commit -m "docs: update case-db index with 5 new cases"
```

---

## Task 12: Library Reference — LGF (Siemens Library of General Functions)

**Files:**
- Create: `knowledge/libraries/lgf.md`

- [ ] **Step 1: Create lgf.md with full content**

Follow the template from `knowledge/libraries/_template.md`.

Content requirements:
- Frontmatter: Tags `lgf, siemens, utility, general, library`, CPU `Both`, Source `Shipped with TIA Portal V16+`, Version `V6.0+`
- Overview: Siemens Library of General Functions. Ships with TIA Portal. Provides ~100 standardized FBs/FCs for common automation tasks. Categories: pulse generators, edge detection, multiplexers, comparators, data manipulation, signal conditioning, arithmetic, conversion.
- Installation: Already available in TIA Portal under Global Libraries → Library of General Functions. To use: drag blocks into project or add library reference via Project → Libraries.
- Key Function Blocks table (8-10 most useful):
  - `LGF_PulseGenerator` — configurable pulse generator with duty cycle
  - `LGF_RampFunction` — linear ramp with configurable rate
  - `LGF_Limiter` — value clamping with min/max
  - `LGF_ScaleLinear` — linear scaling (raw sensor value → engineering unit)
  - `LGF_EdgeDetection` — rising/falling edge with pulse output
  - `LGF_MultiplexerInt` — select one of N integer inputs
  - `LGF_Debounce` — signal debouncing with configurable time
  - `LGF_Hysteresis` — hysteresis comparator
- Usage Examples: 2-3 SCL examples showing how to call LGF blocks:
  1. Scaling a 0-27648 analog input to 0.0-100.0% using LGF_ScaleLinear
  2. Debouncing a pushbutton input using LGF_Debounce
  3. Ramping a speed setpoint using LGF_RampFunction
- Compatibility Notes: Available from TIA Portal V16+. Most blocks work on both S7-1500 and S7-1200. Some advanced blocks (using VARIANT) are S7-1500 only — check individual block documentation.

- [ ] **Step 2: Commit**

```bash
git add knowledge/libraries/lgf.md
git commit -m "feat: add LGF library reference"
```

---

## Task 13: Library Reference — OSCAT Basic

**Files:**
- Create: `knowledge/libraries/oscat.md`

- [ ] **Step 1: Create oscat.md with full content**

Content requirements:
- Frontmatter: Tags `oscat, open-source, math, string, datetime, building`, CPU `Both`, Source `https://store.siemens.com (search OSCAT) or oscat.de`, Version `V3.33`
- Overview: Open-source IEC 61131-3 function block library. 500+ blocks covering: mathematical functions, string manipulation, date/time operations, building automation, signal processing, astronomy, network utilities. Community-maintained, free to use.
- Installation: Download from Siemens Industry Online Support or oscat.de. Import via TIA Portal: Project → Libraries → Open Global Library → navigate to OSCAT .zal file. Copy needed blocks into project library.
- Key Function Blocks table (8-10 most useful for PLC automation):
  - `OSCAT_SCALE` — generic scaling with offset and gain
  - `OSCAT_PID` — alternative PID controller (simpler than PID_Compact)
  - `OSCAT_FILTER_I` — integer signal filter (moving average)
  - `OSCAT_DT_TO_STRING` — date/time to formatted string conversion
  - `OSCAT_HOUR_METER` — operating hours counter
  - `OSCAT_BLINK` — blink generator with configurable on/off times
  - `OSCAT_SEQUENCE` — step sequencer with configurable timing
  - `OSCAT_SUN_POS` — sun position calculator (azimuth/elevation from GPS coordinates)
- Usage Examples: 2-3 SCL examples
- Compatibility Notes: Designed for IEC 61131-3 compliance, works on both S7 families. Some blocks use features not available on S7-1200 — check individual block VAR types. OSCAT is not officially supported by Siemens — use at own risk in production.

- [ ] **Step 2: Commit**

```bash
git add knowledge/libraries/oscat.md
git commit -m "feat: add OSCAT Basic library reference"
```

---

## Task 14: Update Libraries Index

**Files:**
- Modify: `knowledge/libraries/_index.md`

- [ ] **Step 1: Add entries to the table and remove candidate list**

Replace the entire file content with:

```markdown
# Third-Party Libraries

> Reference guides for third-party function block libraries usable in S7 PLCs.

| File | Description | Tags | CPU |
|------|-------------|------|-----|
| lgf.md | Siemens Library of General Functions — scaling, ramp, debounce, pulse | lgf, siemens, utility, general | Both |
| oscat.md | OSCAT Basic — 500+ open-source IEC 61131-3 blocks (math, string, datetime) | oscat, open-source, math, string | Both |

To add a library: copy `_template.md`, fill in content, add an entry to this table.
```

- [ ] **Step 2: Commit**

```bash
git add knowledge/libraries/_index.md
git commit -m "docs: update libraries index with LGF and OSCAT entries"
```

---

## Task 15: Skill — Tag Management

**Files:**
- Create: `.claude/skills/tag-management/SKILL.md`

- [ ] **Step 1: Create SKILL.md**

Use the structure from existing skills (e.g., `.claude/skills/scl-inject/SKILL.md`): frontmatter, prerequisites, numbered steps with exact MCP tool calls, expected responses, troubleshooting table.

```markdown
---
name: tag-management
description: Create, configure, and manage PLC tag tables — add tags, export/import, bulk operations
---

# Tag Management

## Prerequisites
- TIA Portal connected (`GetState` -> IsConnected = true)
- Project open with at least one PLC device
- `softwarePath` known (e.g. `PLC_1/Program blocks`)

## Steps

### Step 1: List existing tag tables

```
GetTagTables(softwarePath="<softwarePath>")
```
Expected: `{ "Success": true, "TagTables": ["Default tag table", ...] }`

### Step 2: Create a new tag table (if needed)

```
CreateTagTable(
  softwarePath="<softwarePath>",
  tableName="MyTags"
)
```
Expected: `{ "Success": true }`

Skip if adding tags to an existing table.

### Step 3: Add tags to the table

```
CreateTag(
  softwarePath="<softwarePath>",
  tableName="MyTags",
  tagName="Motor_Start",
  dataType="Bool",
  address="%I0.0",
  comment="Start pushbutton"
)
```
Expected: `{ "Success": true }`

Repeat for each tag. Common data types: `Bool`, `Int`, `Real`, `Word`, `DInt`, `String`.
Common address prefixes: `%I` (input), `%Q` (output), `%M` (memory).

### Step 4: Verify tags were created

```
GetTags(
  softwarePath="<softwarePath>",
  tableName="MyTags"
)
```
Expected: list of all tags with names, types, and addresses.

### Step 5: Export tag table (optional, for backup)

```
ExportTagTable(
  softwarePath="<softwarePath>",
  tableName="MyTags",
  exportPath="D:\\Temp\\MyTags.xml"
)
```
Expected: `{ "Success": true, "ExportPath": "D:\\Temp\\MyTags.xml" }`

### Step 6: Import tag table (optional, from existing file)

```
ImportTagTable(
  softwarePath="<softwarePath>",
  importPath="D:\\Temp\\MyTags.xml"
)
```
Expected: `{ "Success": true }`

## Bulk Operations

To add many tags efficiently, create them in a loop:
1. Prepare a list of tag definitions (name, type, address, comment)
2. Call `CreateTag` for each one sequentially
3. Call `GetTags` to verify all were created

## Common Issues

| Problem | Fix |
|---------|-----|
| "Tag table not found" | Check exact table name with `GetTagTables` |
| "Address already in use" | Another tag uses this address — use `GetTags` to find conflicts |
| "Invalid address format" | Use S7 format: `%I0.0` (bool), `%IW0` (word), `%MD0` (dword) |
| "Tag already exists" | Use `UpdateTag` to modify existing tag, or `DeleteTag` first |
| Import fails with "format error" | Export format must match TIA Portal version |
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/tag-management/SKILL.md
git commit -m "feat: add tag management skill"
```

---

## Task 16: Skill — Project Backup

**Files:**
- Create: `.claude/skills/project-backup/SKILL.md`

- [ ] **Step 1: Create SKILL.md**

```markdown
---
name: project-backup
description: Save a backup copy of the current TIA Portal project and optionally compare with online PLC
---

# Project Backup

## Prerequisites
- TIA Portal connected (`GetState` -> IsConnected = true)
- Project open (`GetProject` returns project info)

## Steps

### Step 1: Verify current project

```
GetProject()
```
Expected: `{ "Success": true, "ProjectName": "MyProject", "ProjectPath": "D:\\TIA-Projects\\..." }`

Record the project name and path.

### Step 2: Save current state

```
SaveProject()
```
Expected: `{ "Success": true }`

Always save before creating a backup to ensure the latest changes are on disk.

### Step 3: Create backup copy

```
SaveAsProject(path="<original_path>_backup_YYYYMMDD")
```
Expected: `{ "Success": true, "ProjectPath": "D:\\TIA-Projects\\MyProject_backup_20260511\\..." }`

Use today's date in the backup name. This creates a full independent copy of the project.

> Note: After `SaveAsProject`, TIA Portal switches to the backup copy as the active project. If you want to continue working on the original, reopen it:

```
OpenProject(path="<original_path>\\<original_name>.ap19")
```

### Step 4: Compare with online PLC (optional)

If a PLC is connected, compare the project state with what's running:

```
CompareToOnline(softwarePath="<softwarePath>")
```
Expected:
```json
{
  "Success": true,
  "Differences": [],
  "InSync": true
}
```

If `InSync` is `false`, review the `Differences` list to see which blocks differ between project and PLC.

## Common Issues

| Problem | Fix |
|---------|-----|
| "Path already exists" on SaveAsProject | A backup with this name already exists — add a sequence number or time |
| SaveProject fails with "read-only" | Remove read-only attribute from project folder |
| CompareToOnline fails "not connected" | Run `GoOnline` first, then compare |
| After SaveAsProject, wrong project active | Reopen the original project with `OpenProject` |
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/project-backup/SKILL.md
git commit -m "feat: add project backup skill"
```

---

## Task 17: Update CLAUDE.md and Cheat Sheet with New Skills

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/cheat-sheet.md`

- [ ] **Step 1: Add 2 new skills to CLAUDE.md**

In the `## Skills (invoke with /skill-name)` section, add after the last entry:

```markdown
- `/tag-management` — Create, configure, and manage PLC tag tables
- `/project-backup` — Save backup copy, optionally compare with online PLC
```

- [ ] **Step 2: Add 2 new skills to cheat-sheet.md**

In the Skills table, add:

```markdown
| `/tag-management` | Create tag tables, add/update/export/import tags |
| `/project-backup` | Save backup copy, compare with online PLC |
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/cheat-sheet.md
git commit -m "docs: add tag-management and project-backup skills to CLAUDE.md and cheat sheet"
```

---

## Task 18: Final Verification

- [ ] **Step 1: Verify all new files exist**

Run:
```bash
git log --oneline -17
```
Expected: 17 commits covering all tasks.

- [ ] **Step 2: Verify no broken cross-references in new files**

Search all new files for references to other files and confirm targets exist:
```bash
grep -r "knowledge/" knowledge/industry/valve-control.md knowledge/industry/multi-plc-comm.md knowledge/industry/hmi-interface.md knowledge/industry/profinet-diagnostics.md
grep -r "case-db/" case-db/success/011-multi-plc-comm.md case-db/success/012-multi-fb-system.md case-db/success/013-valve-sequence.md case-db/errors/011-comm-timeout.md case-db/errors/012-db-size-exceeded.md
```

For each reference found, verify the target file exists on disk.

- [ ] **Step 3: Verify indexes are complete**

Check that every new file appears in its directory's `_index.md`:
- `knowledge/industry/_index.md` — should list 8 entries (4 old + 4 new)
- `case-db/_index.md` — should list 15 success + 12 error entries
- `knowledge/libraries/_index.md` — should list 2 entries

- [ ] **Step 4: Update evaluation spec status**

In `docs/superpowers/specs/2026-05-11-harness-evaluation-design.md`, update the scores:
- Layer 2 Knowledge: 4.0 → 4.5 (content gaps filled)
- Layer 3 Workflows: 4.5 → 5.0 (2 new skills added)
- Overall: 4.4 → 4.7

Commit:
```bash
git add docs/superpowers/specs/2026-05-11-harness-evaluation-design.md
git commit -m "docs: update evaluation scores after roadmap implementation"
```
