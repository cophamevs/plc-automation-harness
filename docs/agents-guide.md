# PLC Automation Harness -- Agents Guide

## Overview

Claude Code agents are specialized personas that you invoke within a Claude Code session using the `@agent-name` syntax. Each agent carries its own system prompt with domain-specific knowledge, checklists, tool preferences, and behavioral rules. This makes them fundamentally different from a base Claude session:

- **Base session**: General-purpose. Handles open-ended questions, file editing, shell commands, and ad-hoc tasks across any domain.
- **Agent session**: Scoped to a role. The agent follows a defined process, uses a curated set of MCP tools, and applies domain constraints (e.g., IEC 61131-3 compliance, S7-1200 memory limits) automatically.

Agents do not share state with each other. Each invocation starts fresh. You can chain agents by passing the output of one as context to the next.

This harness ships four agents purpose-built for Siemens S7 PLC development
via TIA Portal MCP tools. Agents are complemented by five skills (invokable
via `/skill-name`) that provide guided step-by-step workflows. See the
Skills section at the end for how they interact.

---

## SCL Developer (@scl-developer)

### Purpose

Generate production-ready SCL (Structured Control Language) code for S7-1500 and S7-1200 PLCs and inject it into TIA Portal via MCP tools.

### When to Use

- Creating new PLC blocks (FBs, FCs, OBs, DBs, UDTs) from scratch
- Generating complete SCL external source files for TIA Portal import
- Writing code that follows Siemens SCL best practices and block ordering rules
- Any task where the end result is SCL code compiled inside TIA Portal

### Process (4 Steps)

1. **Plan Blocks** -- Determine which blocks are needed: OBs for execution entry points, FBs for stateful logic (motors, valves, sequences), FCs for stateless calculations, DBs for data storage, and UDTs for reusable structures. The agent confirms the target CPU (S7-1500 vs S7-1200) and consults `knowledge/s7-1200-limitations.md` when targeting a 1200. It also searches `case-db/success/` for similar prior programs to use as reference.

2. **Write SCL External Source** -- Produces all blocks in a single source file with strict ordering: UDTs first, then FCs, then FBs, then instance DBs, then OBs. This ordering satisfies TIA Portal's dependency resolution during generation.

3. **Inject into TIA Portal** -- Calls three MCP tools in sequence:
   - `SetExternalSourceContent` to write the SCL source
   - `GenerateBlocksFromSource` to parse and create blocks
   - `CompileSoftware` to compile everything

4. **Verify** -- Checks the compile result for errors. On success, calls `GetBlocks` to confirm all expected blocks exist. On failure, attempts one fix; if still failing, hands off to `@scl-debugger` for iterative repair.

### Scope Boundary

This agent **writes new code**. It does not enter multi-iteration debug loops — that is `@scl-debugger`'s job. If a compile error persists after one fix attempt, hand off.

### Key MCP Tools

- `SetExternalSourceContent` -- write SCL source into the TIA Portal project
- `GenerateBlocksFromSource` -- generate PLC blocks from the source
- `CompileSoftware` -- compile the PLC software
- `GetBlocks` -- verify block inventory after compilation

### SCL Pitfalls the Agent Guards Against

- Missing `#` prefix on local variables
- Omitted semicolons
- Implicit type conversions (enforces explicit `INT_TO_REAL()`, etc.)
- STRING declared without length specifier
- Incorrect block ordering in source files
- Missing VERSION declarations
- Instance DB `S7_Optimized_Access` not set to FALSE for S7 runtime access

### Example Invocation

```
@scl-developer Create a motor control program for an S7-1500. 
I need an FB for motor start/stop with a 2-second start delay, 
a speed calculation FC, and the Main OB to tie it together.
```

---

## SCL Debugger (@scl-debugger)

### Purpose

Diagnose and fix compile errors and runtime issues in Siemens S7 PLC programs. This agent operates as an automated fix loop -- it reads errors, applies corrections, recompiles, and repeats until the program compiles cleanly or an iteration limit is reached.

### Scope Boundary

This agent **fixes existing code**. It does not write new programs from scratch — that is `@scl-developer`'s job. Entry points: compile failure, generation failure, or runtime misbehavior.

### When to Use

- `CompileSoftware` or `GenerateBlocksFromSource` returned errors (especially after `@scl-developer`'s one-attempt fix failed)
- Runtime values read via `S7ReadVariable` are unexpected (stuck at zero, wrong values)
- Timers or counters are not behaving as expected
- Block inconsistency errors after modifying dependencies

### Process (7-Step Debug Loop)

1. **Read the error** from CompileSoftware or GenerateBlocksFromSource output
2. **Locate the error** by block name and line number (when available)
3. **Read the current source** via `GetExternalSourceContent`
4. **Match the error** to known patterns from its built-in error code reference
5. **Fix the source** via `SetExternalSourceContent` with corrected code
6. **Recompile** via `GenerateBlocksFromSource` then `CompileSoftware`
7. **Repeat** until zero errors remain, up to a maximum of 5 iterations

The agent follows escalation rules: after 3 failed attempts on the same error, it reports to the user with the exact error message, the offending SCL code, what was tried, and a hypothesis about root cause. After 5 total iterations it stops and summarizes all remaining errors.

### Error Code Reference

The agent carries a built-in reference covering three error categories:

**Syntax Errors** -- "unexpected token" (missing terminators), "identifier not declared" (undeclared variables), "type mismatch" (wrong data type assignments), "duplicate identifier" (name collisions).

**Semantic Errors** -- "block is inconsistent" (dependency ordering), "instance DB required" (FB called without DB), "access not possible" (S7_Optimized_Access conflicts), "address out of range" (memory limits exceeded).

**Runtime Errors** -- values stuck at zero (block not called in OB1), unexpected values (byte order or offset issues), timers not running (declared in TEMP instead of static VAR).

### Key MCP Tools

- `GetExternalSourceContent` -- read current SCL source
- `SetExternalSourceContent` -- write corrected source
- `GenerateBlocksFromSource` -- recompile from source
- `CompileSoftware` -- full compilation check
- `GetBlocks` / `GetBlockInfo` -- verify blocks and consistency
- `S7ReadVariable` / `S7ReadDBStruct` -- read runtime values for diagnosis

### Example Invocation

```
@scl-debugger CompileSoftware returned 3 errors on softwarePath 
"PLC_1/PLC Program". Here is the output:
[paste compile errors here]
```

---

## SCL Reviewer (@scl-reviewer)

### Purpose

Review SCL code for quality, safety, IEC 61131-3 compliance, and S7-1200 compatibility. The agent applies a structured 30-item checklist and reports findings in a standardized format.

### When to Use

- Before deploying code to a physical PLC
- Code quality audit on existing programs
- Verifying S7-1200 compatibility before porting from S7-1500
- Checking that safety-critical code handles edge cases (division by zero, array bounds, overflow)

### Review Checklist (6 Categories, 30 Items)

1. **Structure (6 items)** -- Single responsibility per FB, no global variable access inside FBs, max 1 level of FB nesting, FCs for pure calculations only, UDTs for repeated structures, instance DBs for every FB call.

2. **Safety (6 items)** -- No division by zero possible, array access within bounds, timer/counter overflow handled, REAL comparison uses epsilon tolerance (not equality), STRING operations check length limits, no infinite loops.

3. **Type Safety (4 items)** -- All conversions explicit, no implicit widening (INT to DINT), VARIANT parameters validated before use (S7-1500), STRING length always specified.

4. **S7-1200 Compatibility (5 items)** -- No VARIANT/LREAL/LINT/ULINT/LWORD, no OOP constructs (METHOD/PROPERTY), no ARRAY[*], DB size at most 16 KB, call nesting at most 6 levels. This category is evaluated only when the target is S7-1200.

5. **Naming and Style (5 items)** -- Block name prefixes (FB_, FC_, DB_, UDT_, OB_), CamelCase variables, UPPER_CASE constants, REGION/END_REGION for logical sections, VERSION declared on every block.

6. **Error Handling (4 items)** -- ENO checked after critical operations, status outputs on every FB (minimum: Error BOOL + ErrorID INT), timeout on communication operations, graceful degradation on sensor failure.

### Output Format

Each checklist item has a severity weight: **CRITICAL** (must fix before download), **MAJOR** (should fix), **MINOR** (recommended). Findings are reported per item:

- **PASS** -- requirement met, no action needed
- **WARN** -- potential issue, recommendation provided (typically MINOR/MAJOR items)
- **FAIL** -- must fix before deployment (typically CRITICAL items)

The review summary groups all CRITICAL failures first, then MAJOR, then MINOR.

### Key MCP Tools

- `GetExternalSourceContent` -- read source code under review
- `GetBlocks` -- check block inventory
- `GetBlockInfo` -- check block consistency and protection status
- `GetTypes` -- verify UDT definitions

### Example Invocation

```
@scl-reviewer Review the SCL code in external source "main" on 
softwarePath "PLC_1/PLC Program". Target CPU is S7-1200.
Focus on safety and S7-1200 compatibility.
```

---

## PLC Architect (@plc-architect)

### Purpose

Design the block structure and program architecture for Siemens S7 PLC programs. The architect produces a high-level plan that the `@scl-developer` agent can then implement.

### When to Use

- Starting a new PLC project from scratch
- Decomposing a complex machine or process into PLC blocks
- Planning interfaces between functional units
- Deciding OB strategy (main cycle, startup, diagnostics, cyclic interrupts)
- Evaluating whether a design fits within S7-1200 or S7-1500 constraints

### Process (5 Steps)

1. **Understand requirements** -- Gather machine/process requirements from the user: what does the system control, what are the inputs and outputs, what are the operating modes.

2. **Decompose into functional units** -- Each functional unit (motor, conveyor, valve station, HMI interface) maps to one FB. The decomposition follows single-responsibility principles.

3. **Define interfaces** -- Specify IN, OUT, and INOUT parameters for each FB. Define how blocks communicate: which FB outputs feed into which FB inputs, what data is shared via global DBs.

4. **Plan OB structure** -- Assign execution contexts: OB1 for the main cycle, OB100 for startup initialization, OB82 for diagnostics, OB35 for cyclic interrupt (heavy computation offloading).

5. **Plan DB structure** -- Categorize data blocks: instance DBs (one per FB call), global config DBs (read by multiple blocks), recipe DBs (operator-changeable parameters).

### Output Format

The architect delivers a block diagram as a structured table:

| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| OB1   | OB   | Main cycle | calls FB_Motor, FB_Conveyor |
| FB_Motor | FB | Motor control | IN: cmd, OUT: status, error |
| FB_Conveyor | FB | Conveyor control | IN: speed, OUT: position |
| DB_Config | DB | Configuration | global read |

Along with interface definitions (parameter names, types, and data flow descriptions) and design rationale.

### Handoff to Implementation

After design approval, hand off to `@scl-developer` with:
1. The block diagram table
2. Target CPU (S7-1500 or S7-1200)
3. Any special requirements (S7_Optimized_Access, communication, safety)

For complex systems, have the developer implement one FB at a time and use `@scl-reviewer` after each.

### Design Rules

- Max 1 level of FB nesting for readability
- Separate control logic (FBs) from calculations (FCs)
- Config data in global DBs, runtime data in instance DBs
- Every FB must expose Error (BOOL) and ErrorID (INT) outputs
- Heavy computation belongs in cyclic interrupt OBs (OB35), not the main scan cycle
- S7-1500: group related blocks in folders; max 64 MB per DB (split above 10 MB)
- S7-1200: max 6 nesting levels, max 16 KB per DB, no VARIANT (fixed interfaces per data type)

### Example Invocation

```
@plc-architect Design the block structure for a bottling line with 
3 conveyor sections, 2 filling stations, and a capping station. 
Target is S7-1500. Include startup and diagnostics OBs.
```

---

## Agent Workflow

The four agents form a natural pipeline for PLC development:

```
@plc-architect  -->  @scl-developer  -->  @scl-reviewer  -->  @scl-debugger
   (design)          (implement)          (review)            (fix if needed)
```

### Typical Sequence

1. **Architect first.** Invoke `@plc-architect` with your system requirements. It produces a block diagram and interface definitions.

2. **Develop second.** Pass the architect's block plan to `@scl-developer`. It generates the full SCL source, injects it into TIA Portal, and compiles.

3. **Review third.** Invoke `@scl-reviewer` on the compiled code. It evaluates all 30 checklist items and flags issues. Address FAIL items before proceeding.

4. **Debug as needed.** If compilation fails at any stage, or if runtime testing reveals unexpected behavior, invoke `@scl-debugger` with the error output. It runs the fix loop automatically.

### Iteration

The workflow is not always linear. Common loops include:

- **Developer-Debugger loop**: Compile fails, debugger fixes, developer reviews the fix.
- **Developer-Reviewer loop**: Reviewer flags issues, developer reworks the code, reviewer re-checks.
- **Architect revision**: Reviewer finds structural issues (e.g., FB doing too much), architect redesigns that portion.

---

## Skills vs Agents

The harness provides both skills and agents. They serve different purposes:

| Type | Invocation | Purpose | Example |
|------|-----------|---------|---------|
| **Skill** | `/skill-name` | Step-by-step procedure with exact tool calls | `/new-project`, `/debug-compile` |
| **Agent** | `@agent-name` | Specialized persona with domain knowledge | `@scl-developer`, `@scl-reviewer` |

**When to use skills:** You want a guided workflow — follow steps 1, 2, 3...
**When to use agents:** You want an expert persona — describe what you need, it decides how.

### Available Skills

| Skill | Steps | Purpose |
|-------|-------|---------|
| `/new-project` | 9 | Full E2E: create project → download → verify |
| `/scl-inject` | 4 | Write SCL → generate → compile → verify |
| `/debug-compile` | 5 | Error repair loop (max 5 iterations) |
| `/download-test` | 6 | Download + S7.Net verification |
| `/modify-program` | 5 | Open → modify → recompile → save |

---

## Tips

### When to Use Agents vs Skills vs Base Session

| Situation | Use |
|-----------|-----|
| Full project from scratch | `/new-project` skill |
| Just inject SCL code | `/scl-inject` skill |
| Complex program design | `@plc-architect` agent |
| Writing new SCL code | `@scl-developer` agent |
| Fixing compile errors | `/debug-compile` skill or `@scl-debugger` agent |
| Code quality audit | `@scl-reviewer` agent |
| Download and test | `/download-test` skill |
| Quick one-off TIA Portal operations | Base session |
| General file editing, non-PLC tasks | Base session |

### Combining Agents Effectively

- **Provide context when switching agents.** Agents do not share state. When moving from architect to developer, paste or reference the architect's block table so the developer has the full picture.

- **Let the debugger work autonomously.** The debugger is designed to iterate up to 5 times on its own. Give it the error output and let it run its loop before intervening.

- **Use the reviewer before deployment, not just after development.** Catching issues before downloading to hardware saves significant time, especially for S7-1200 compatibility problems that may require architectural changes.

- **Start with the architect for non-trivial programs.** Any program with more than 2-3 blocks benefits from upfront design. The time spent in the architect phase pays off in fewer debugger iterations later.

- **Specify the target CPU early.** All four agents adjust their behavior based on whether the target is S7-1500 or S7-1200. State this in your first message to the agent.
