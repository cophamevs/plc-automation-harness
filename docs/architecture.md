# PLC Automation Harness -- Architecture

## 1. Overview

The PLC Automation Harness is a markdown-only knowledge ecosystem for Claude Code.
It contains no executable code. Instead, it provides structured reference documents,
annotated case examples, reusable prompt fragments, agent definitions, and
step-by-step workflows that teach Claude Code how to program Siemens S7-1500 and
S7-1200 PLCs using SCL (Structured Control Language).

It is designed to work alongside the
[tiaportal-mcp](https://github.com/copham/tiaportal-mcp) MCP server, which
exposes tools for automating TIA Portal. The harness supplies domain
knowledge; the MCP server supplies tool execution.

```
E:\Software_Siemens\
+-- tiaportal-mcp\           # MCP server (tools)
+-- plc-automation-harness\  # This repo (knowledge + agents)
```

When Claude Code opens the harness directory, it loads `CLAUDE.md` automatically.
That file serves as the root system prompt: it defines programming rules, tool
categories, safety protocols, and pointers into the registry-based knowledge
system described below.

---

## 2. Design Principles

### Claude Code Native

The system is activated by Claude Code loading three layers at session start:
1. `CLAUDE.md` — lean root prompt (~74 lines) with tool categories and pointers
2. `.claude/rules/` — auto-loaded rules (SCL rules, safety are `alwaysApply: true`)
3. `.claude/settings.json` — MCP server connection

No build step, no plugin installation, no runtime dependency beyond the Claude
CLI itself and the tiaportal-mcp MCP server.

### Registry-Based Extensibility

Every content directory contains an `_index.md` registry file and a
`_template.md` scaffold. The `_index.md` lists all files in that directory with
metadata (description, tags, CPU compatibility). Claude discovers content by
reading registry files -- never by hardcoding paths. The `_template.md` enables
zero-friction contribution: copy it, fill in the sections, add one line to the
index.

### No Code, Only Markdown

There are no source files, scripts, configuration generators, or compiled
artifacts. Every piece of knowledge is a Markdown document that Claude reads
on demand. This makes the system version-controllable, diff-friendly, and
trivially extensible by non-programmers.

### Hierarchical: General to Specific

Knowledge is organized from broad to narrow:

```
CLAUDE.md                        # Root: tool categories, pointers
  .claude/rules/ (alwaysApply)   # SCL rules, safety — auto-loaded
  .claude/rules/ (on-demand)     # S7-1500, S7-1200, knowledge registry
  .claude/skills/                # Guided workflows via /skill-name
  .claude/agents/                # Specialized personas via @agent-name
  knowledge/_index.md            # Core references (SCL syntax, CPU specs)
    knowledge/patterns/          # Reusable SCL design patterns
    knowledge/industry/          # Domain-specific application examples
    knowledge/libraries/         # Third-party function block libraries
  case-db/_index.md              # Annotated input/output examples
```

Claude loads `CLAUDE.md` + alwaysApply rules first, then activates skills
or agents on demand, drilling into knowledge registries when the task requires.

---

## 3. Directory Structure

```
plc-automation-harness/
|
|-- CLAUDE.md                         # Root system prompt (loaded every session)
|-- CONTRIBUTING.md                   # How to add new content
|-- README.md                         # Project overview and quick start
|
|-- .claude/
|   |-- rules/
|   |   |-- scl-rules.md              # Mandatory SCL rules (alwaysApply)
|   |   |-- safety.md                 # Safety-critical warnings (alwaysApply)
|   |   |-- s7-1500-features.md       # S7-1500 features (on-demand)
|   |   |-- s7-1200-compat.md         # S7-1200 restrictions (on-demand)
|   |   +-- knowledge-registry.md     # How to discover knowledge (on-demand)
|   |-- skills/
|   |   |-- new-project/SKILL.md      # /new-project — full E2E workflow
|   |   |-- scl-inject/SKILL.md       # /scl-inject — code injection
|   |   |-- debug-compile/SKILL.md    # /debug-compile — error repair loop
|   |   |-- download-test/SKILL.md    # /download-test — download + verify
|   |   +-- modify-program/SKILL.md   # /modify-program — modify existing
|   |-- agents/
|   |   |-- scl-developer.md          # @scl-developer agent
|   |   |-- scl-debugger.md           # @scl-debugger agent
|   |   |-- scl-reviewer.md           # @scl-reviewer agent
|   |   +-- plc-architect.md          # @plc-architect agent
|   +-- settings.json                 # MCP server configuration
|
|-- knowledge/
|   |-- _index.md                     # Registry: core reference files
|   |-- scl-language-reference.md     # SCL syntax, data types, operators
|   |-- s7-1500.md                    # S7-1500 features (VARIANT, OOP, 64-bit)
|   |-- s7-1200-limitations.md        # S7-1200 restrictions + workarounds
|   |-- tia-openness-api.md           # TIA Openness API reference
|   |
|   |-- patterns/
|   |   |-- _index.md                 # Registry: design patterns
|   |   |-- _template.md              # Scaffold for new patterns
|   |   |-- state-machine.md          # Enum-based FSM with timer transitions
|   |   |-- alarm-management.md       # Program Alarm, diagnostic buffer
|   |   |-- timer-counter.md          # TON/TOF/TP, cascaded timers, pulses
|   |   |-- data-logging.md           # Ring buffer, recipe DB, serialization
|   |   |-- communication.md          # PUT/GET, TCP/UDP, MODBUS TCP
|   |   +-- error-handling.md         # ENO chain, status word, error aggregation
|   |
|   |-- industry/
|   |   |-- _index.md                 # Registry: industry examples
|   |   |-- _template.md              # Scaffold for new examples
|   |   |-- conveyor-control.md       # Belt conveyor with jam detection
|   |   |-- motor-starter.md          # DOL, star-delta, VFD patterns
|   |   |-- pid-loop.md              # PID_Compact, manual/auto, tuning
|   |   +-- batch-process.md          # ISA-88 phases: fill, heat, drain
|   |
|   +-- libraries/
|       |-- _index.md                 # Registry: third-party libraries
|       +-- _template.md              # Scaffold for new library entries
|
|-- case-db/
|   |-- _index.md                     # Registry: success + error cases
|   |-- success/
|   |   |-- _template.md              # Scaffold for new success cases
|   |   |-- 001-blink-led.md          # ... through 010-star-delta-starter.md
|   |   +-- (10 annotated success cases)
|   +-- errors/
|       |-- _template.md              # Scaffold for new error cases
|       |-- 001-type-mismatch.md      # ... through 010-s7-1200-unsupported-type.md
|       +-- (10 annotated error cases)
|
|-- workflows/
|   |-- _index.md                     # Registry: procedures
|   |-- _template.md                  # Scaffold for new workflows
|   |-- new-project-from-scratch.md   # Create -> AddDevice -> SCL -> Compile -> Download
|   |-- debug-compile-errors.md       # Error -> Fix -> Recompile loop (max 5 iter)
|   |-- download-and-test.md          # Validate -> Download -> S7Connect -> Verify
|   +-- modify-existing-program.md    # Open -> Export -> Modify -> Reimport -> Save
|
|-- prompts/
|   |-- scl-system-prompt.md          # Reusable SCL code generation context
|   |-- review-checklist.md           # Quick self-review after generating SCL
|   +-- debug-template.md             # Error report template for agent handoff
|
+-- docs/
    +-- architecture.md               # This document
```

---

## 4. Registry System

### Discovery Mechanism

Claude never hardcodes paths to knowledge files. Instead, `CLAUDE.md` points
to registry files, and each registry lists available content with metadata.

```
CLAUDE.md
  "Read knowledge/patterns/_index.md to see ALL available topics"
    --> knowledge/patterns/_index.md
          | File                  | Tags                        | CPU  |
          | state-machine.md      | fsm, sequence, step, case   | Both |
          | alarm-management.md   | alarm, diagnostic, fault    | Both |
          | ...                   | ...                         | ...  |
```

This indirection means newly added files are immediately discoverable without
modifying `CLAUDE.md` -- only the relevant `_index.md` needs a new row.

### Index File Format

Every `_index.md` follows the same structure:

1. **Title and description** -- one-line purpose of the directory.
2. **Table** with columns: File, Description, Tags, and optionally CPU
   compatibility and Complexity.
3. **Subdirectory pointers** (if applicable) linking to child `_index.md` files.

Tags enable Claude to search for relevant content by topic (e.g., "timer",
"modbus", "1200") without reading every file.

### Template File Format

Every `_template.md` provides the expected section structure for new entries.
Contributors copy the template, fill in all sections, and add a row to the
corresponding `_index.md`. This guarantees structural consistency across all
knowledge files.

### Registry Hierarchy

```
knowledge/_index.md
  |-- knowledge/patterns/_index.md
  |-- knowledge/industry/_index.md
  +-- knowledge/libraries/_index.md

case-db/_index.md
  |-- case-db/success/ (files listed inline)
  +-- case-db/errors/  (files listed inline)

workflows/_index.md
```

---

## 5. Rules Layer

The `.claude/rules/` directory contains context rules that Claude Code loads
based on their frontmatter metadata.

### alwaysApply Rules (loaded every session)

| File | Purpose |
|------|---------|
| `scl-rules.md` | 8 mandatory SCL rules, block ordering, naming conventions, syntax reference |
| `safety.md` | Safety warnings for DownloadSoftware, S7WriteVariable, S7WriteDB |

### On-Demand Rules (loaded when relevant)

| File | Purpose |
|------|---------|
| `s7-1500-features.md` | S7-1500 specific features (VARIANT, OOP, 64-bit types) |
| `s7-1200-compat.md` | S7-1200 restrictions and workarounds table |
| `knowledge-registry.md` | How to discover knowledge via _index.md registries |

Rules use YAML frontmatter with `alwaysApply: true/false` and a `description`
field that Claude Code matches against the current conversation context.

---

## 6. Skills Layer

The `.claude/skills/` directory contains guided workflows invokable via
`/skill-name` in Claude Code. Each skill is a subdirectory with a `SKILL.md`
file containing YAML frontmatter (`name`, `description`) and the full
step-by-step procedure.

| Skill | Command | Steps | Purpose |
|-------|---------|-------|---------|
| New Project | `/new-project` | 9 | Full E2E: create project, add device, SCL, compile, simulate, download, verify |
| SCL Inject | `/scl-inject` | 4 | Write SCL to external source, generate blocks, compile, verify |
| Debug Compile | `/debug-compile` | 5 | Iterative repair loop (max 5 iterations) with error reference table |
| Download Test | `/download-test` | 6 | Validate, download, S7Connect, read/write verify |
| Modify Program | `/modify-program` | 5 | Open, explore, export/modify, recompile, save |

Skills differ from agents: skills are procedural (follow these steps), agents
are behavioral (adopt this persona). Skills load the full workflow into context
when invoked; agents carry specialized knowledge and decision-making rules.

---

## 7. Knowledge Layer

The `knowledge/` directory contains reference material organized into four
tiers: core references, design patterns, industry examples, and library
documentation.

### 7.1 Core References

Four files at the top level of `knowledge/` provide foundational information.

**SCL Language Reference** (`scl-language-reference.md`)
Complete syntax reference for Structured Control Language: data types (BOOL
through STRING), arithmetic and logical operators, control flow (IF, CASE, FOR,
WHILE, REPEAT), timer and counter system FBs, and block declaration syntax for
OB, FB, FC, DB, and UDT.

**S7-1500 Features** (`s7-1500.md`)
Capabilities unique to the S7-1500 platform: VARIANT type for generic FB
interfaces, 64-bit numeric types (LREAL, LINT, ULINT, LWORD), OOP constructs
(METHOD, PROPERTY in FBs), named constructors for UDTs, variable-length arrays
(ARRAY[*]), 64 MB per DB, and 24 nesting levels for FC/FB calls.

**S7-1200 Limitations** (`s7-1200-limitations.md`)
Restrictions of the S7-1200 relative to S7-1500, with documented workarounds:
no VARIANT (use ANY or overloaded FBs), no 64-bit types (max 32-bit: REAL,
DINT, UDINT), no OOP (no METHOD/PROPERTY), no variable-length arrays, 16 KB
per DB limit, 6 nesting levels, and no system clock memory bits by default.

**TIA Openness API** (`tia-openness-api.md`)
Reference for the TIA Portal Openness API as exposed through tiaportal-mcp.
Covers the API concepts that map to MCP tool categories: project management,
hardware configuration, software compilation, block import/export, and online
operations.

### 7.2 Patterns

Six reusable SCL design patterns in `knowledge/patterns/`, each containing
a problem description, SCL implementation, usage example, and notes on CPU
compatibility.

| Pattern | Purpose |
|---------|---------|
| State Machine | Enum-based finite state machine with entry/exit actions and timer-driven transitions |
| Alarm Management | Program Alarm integration, diagnostic buffer access, alarm class hierarchy |
| Timer / Counter | TON, TOF, TP usage patterns; cascaded timers; pulse generators |
| Data Logging | Ring buffer implementation, recipe DB management, data serialization |
| Communication | PUT/GET, Open User Communication (TCP/UDP), MODBUS TCP, S7 communication |
| Error Handling | ENO chain propagation, status word pattern, error aggregation across FB hierarchies |

### 7.3 Industry Modules

Four domain-specific application examples in `knowledge/industry/`, each
containing requirements, block structure, complete SCL implementation, and
test procedures.

| Module | Scope | CPU |
|--------|-------|-----|
| Conveyor Control | Belt conveyor with sensors, jam detection, start/stop sequences | Both |
| Motor Starter | Direct-on-line, star-delta, and VFD control patterns | Both |
| PID Loop | PID_Compact configuration, manual/auto mode switching, tuning guidance | 1500 only |
| Batch Process | ISA-88 batch concepts: fill, heat, drain phases with recipe management | Both |

### 7.4 Libraries

The `knowledge/libraries/` directory is reserved for third-party function block
library references (e.g., OSCAT, Siemens LGF). The registry and template are
in place; no library entries have been contributed yet.

---

## 8. Case Database

The `case-db/` directory contains 20 annotated examples organized into success
cases and error cases. These serve as few-shot learning material: agents search
the index by tags to find cases similar to the current task before generating
new code.

### 8.1 Success Cases (10)

Each success case contains: requirements, complete SCL source code, MCP tool
commands used, and a test procedure with expected results.

| # | Case | Complexity | CPU |
|---|------|------------|-----|
| 001 | Blink LED (toggle output every 1 s) | Beginner | Both |
| 002 | Motor Start/Stop (FB with Start/Stop/Running/Fault) | Beginner | Both |
| 003 | Traffic Light (state machine with timer transitions) | Intermediate | Both |
| 004 | Conveyor Sequence (multi-FB with jam detection) | Intermediate | Both |
| 005 | PID Temperature (PID_Compact control) | Intermediate | 1500 |
| 006 | Recipe Management (storage and loading from global DB) | Intermediate | Both |
| 007 | Alarm Handler (centralized collection and reporting) | Intermediate | Both |
| 008 | MODBUS TCP Client (read/write to external device) | Advanced | Both |
| 009 | Data Logger (ring buffer to DB) | Intermediate | Both |
| 010 | Star-Delta Starter (motor start sequence with timers) | Intermediate | Both |

### 8.2 Error Cases (10)

Each error case contains: the exact error message, the problematic code, the
corrected code, and an explanation of why the error occurs.

| # | Error | Type |
|---|-------|------|
| 001 | Type Mismatch (INT assigned to REAL without conversion) | Compile |
| 002 | Missing Instance DB (FB called without DATA_BLOCK) | Compile |
| 003 | Array Bounds (index 0 on 1-based array) | Runtime |
| 004 | Timer in TEMP (timer declared in VAR_TEMP loses state) | Runtime |
| 005 | Missing Hash Prefix (local variable without # prefix) | Compile |
| 006 | String No Length (STRING without [n] specifier) | Compile |
| 007 | REAL Equality (compared with = instead of epsilon) | Logic |
| 008 | Block Order Dependency (FB referenced before declaration) | Compile |
| 009 | Optimized Access Conflict (S7_Optimized_Access blocks S7.Net read) | Runtime |
| 010 | S7-1200 Unsupported Type (VARIANT/LREAL on S7-1200) | Compile |

### 8.3 Case Format

Cases follow a consistent structure enforced by `_template.md` files in each
subdirectory. The `_index.md` at the case-db root lists all cases in two tables
(success and errors) with searchable tags. Claude matches tags from the current
task against the index to find relevant examples before writing new code.

---

## 9. Workflows

The `workflows/` directory contains quick-reference summaries that point to the
authoritative source in `.claude/skills/`. Skills are the single source of truth
for all step-by-step procedures.

| Skill | Command | Purpose |
|-------|---------|---------|
| New Project | `/new-project` | End-to-end: empty project to verified running PLC |
| SCL Inject | `/scl-inject` | Primary code injection workflow |
| Debug Compile | `/debug-compile` | Iterative fix loop for compile-time failures (max 5 iterations) |
| Download Test | `/download-test` | Transfer program to PLC and verify via runtime reads |
| Modify Program | `/modify-program` | Safely modify blocks in an existing project |

Skills reference MCP tool names directly and include safety gates (user
confirmation before `DownloadSoftware`, `S7WriteVariable`, `S7WriteDB`).

---

## 10. Agents

Four specialized agents defined in `.claude/agents/`. Each is a Markdown file
containing a system prompt, behavioral rules, and references to knowledge files.
Users invoke them via slash commands in Claude Code.

### @scl-developer

Primary code generation agent. Before writing code, it confirms the target CPU,
checks the case database for similar programs, and plans the block structure.
It follows a strict process: plan blocks, write SCL in correct dependency order
(UDTs, FCs, FBs, instance DBs, OBs), inject via external source, compile, and
verify. Falls back to `/plc-architect` for complex programs and `/scl-debugger`
on compile failure.

### @scl-debugger

Error resolution agent. Operates in a read-error, locate, fix, recompile loop
with a maximum of 5 iterations. Contains an error code reference table mapping
common TIA Portal error patterns (syntax errors, semantic errors, runtime
faults) to their causes and fixes. Reads the current source via MCP tools,
applies corrections, and recompiles until zero errors remain.

### @scl-reviewer

Code quality agent. Reviews SCL against a structured checklist covering four
categories: structure (single responsibility, no global access, instance DBs),
safety (division by zero, array bounds, timer overflow, REAL comparison),
type safety (explicit conversions, STRING lengths, VARIANT validation), and
S7-1200 compatibility. Produces a pass/fail report with specific remediation
for each finding.

### @plc-architect

Program design agent. Given machine or process requirements, it decomposes
functionality into FBs, defines interfaces (IN/OUT parameters), plans OB
structure (main cycle, startup, diagnostics), and lays out DB allocation
(instance, config, recipe). Outputs a block diagram table. Enforces rules:
max 1 level of FB nesting, separate control logic from calculations, and
mandatory Error/ErrorID outputs on every FB.

---

## 11. Prompts

Three reusable prompt fragments in `prompts/`, designed to be embedded in
custom prompts or agent instructions.

| File | Purpose |
|------|---------|
| `scl-system-prompt.md` | Reusable SCL code generation context: block ordering rules, mandatory rules, and output format expectations. Embed this when building custom prompts that need SCL output. |
| `review-checklist.md` | Quick self-review checklist (structure, safety, type safety, timing) for post-generation validation. Used by `/scl-reviewer` and available for ad-hoc review. |
| `debug-template.md` | Error report template with fields for error source, error message, relevant code, and attempted fixes. Used for structured handoff between `/scl-developer` and `/scl-debugger`. |

---

## 12. Extension Points

The harness is designed for growth. Each content type has a defined extension
path.

### Add a New Pattern

1. Copy `knowledge/patterns/_template.md` to `knowledge/patterns/<name>.md`.
2. Fill in all sections (Problem, Solution, SCL Code, Usage, CPU Compatibility).
3. Add a row to `knowledge/patterns/_index.md` with file name, description,
   tags, and CPU.

### Add a New Industry Example

1. Copy `knowledge/industry/_template.md` to `knowledge/industry/<name>.md`.
2. Fill in Requirements, Block Structure, SCL Code, and Test Procedure.
3. Add a row to `knowledge/industry/_index.md`.

### Add a New Library Reference

1. Copy `knowledge/libraries/_template.md` to `knowledge/libraries/<name>.md`.
2. Document the library's blocks, usage, and integration notes.
3. Add a row to `knowledge/libraries/_index.md`.

### Add a New Success Case

1. Copy `case-db/success/_template.md` to `case-db/success/NNN-<name>.md`
   (sequential numbering).
2. Fill in Requirements, SCL Code, MCP Commands, and Test Procedure.
3. Add a row to the Success Cases table in `case-db/_index.md`.

### Add a New Error Case

1. Copy `case-db/errors/_template.md` to `case-db/errors/NNN-<name>.md`.
2. Fill in Error Message, Bad Code, Good Code, and explanation.
3. Add a row to the Error Cases table in `case-db/_index.md`.

### Add a New Workflow

1. Copy `workflows/_template.md` to `workflows/<name>.md`.
2. Fill in Prerequisites, Steps (with exact MCP tool calls), and
   Troubleshooting.
3. Add a row to `workflows/_index.md`.

### Add a New Agent

1. Create `.claude/agents/<name>.md` with the agent system prompt.
2. Add the `/name` slash command reference to the Agents section in `CLAUDE.md`.

### Add a New Prompt Fragment

1. Create `prompts/<name>.md` with the reusable prompt content.
2. Reference it from agent definitions or `CLAUDE.md` as needed.

---

## 13. Data Flow Summary

The following describes how information flows during a typical session.

```
User opens Claude Code in plc-automation-harness/
  |
  v
Claude loads CLAUDE.md + alwaysApply rules
  |-- CLAUDE.md: tool categories, pointers (~74 lines)
  |-- .claude/rules/scl-rules.md: 8 mandatory SCL rules (auto)
  |-- .claude/rules/safety.md: safety-critical warnings (auto)
  +-- .claude/settings.json: MCP server connection
  |
  v
User invokes /new-project skill or @scl-developer agent
  |
  v
Agent reads relevant _index.md registries
  |-- Searches case-db by tags for similar examples
  |-- Loads patterns if design pattern applies
  |-- Checks CPU-specific docs if target is S7-1200
  |
  v
Agent generates SCL code
  |
  v
Injects via tiaportal-mcp MCP tools
  |-- SetExternalSourceContent (write SCL)
  |-- GenerateBlocksFromSource (compile to blocks)
  |-- CompileSoftware (full project compile)
  |
  v
On error: handoff to /scl-debugger (max 5 fix iterations)
On success: /scl-reviewer validates quality
  |
  v
Optional: DownloadSoftware + S7Connect + verify via S7ReadVariable
```

---

## 14. Relationship to tiaportal-mcp

The harness and the MCP server are complementary but independent repositories.

| Concern | Harness (this repo) | tiaportal-mcp |
|---------|-------------------|---------------|
| Type | Markdown knowledge files | C# .NET MCP server |
| Contains | References, patterns, cases, agents | 102 executable MCP tools |
| Role | Teaches Claude *what* to do | Gives Claude the ability *to do it* |
| Runtime | Loaded by Claude Code at session start | Runs as MCP server process |
| Extension | Add .md files, update _index.md | Add C# tool implementations |

Both repos live under the same parent directory and are connected via the
`.claude/settings.json` MCP server configuration in the harness.
