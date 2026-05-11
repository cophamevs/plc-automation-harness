# Getting Started with PLC Automation Harness

This guide walks you through setting up the PLC Automation Harness and using it
to program Siemens S7-1500/S7-1200 PLCs with Claude Code.

The harness is a markdown-only knowledge ecosystem. It contains no executable
code -- just structured knowledge files, agent definitions, design patterns,
annotated case databases, and step-by-step workflows that teach Claude Code
how to act as a PLC automation engineer. All actual TIA Portal automation
happens through the tiaportal-mcp MCP server, which provides 102 tools.

---

## 1. Prerequisites

Before you begin, make sure you have the following installed and available:

| Requirement | Notes |
|-------------|-------|
| **TIA Portal V19 or V20** | Must be installed on the same Windows machine. V19 is the default; V20 is also supported. |
| **tiaportal-mcp server** | The MCP server that bridges Claude Code to TIA Portal. Must be built from source. See [tiaportal-mcp](https://github.com/copham/tiaportal-mcp). |
| **Windows 10 or 11** | TIA Portal only runs on Windows. |
| **Claude Code CLI** | Install from [claude.ai/claude-code](https://claude.ai/claude-code). |
| **PLCSim Advanced** (optional) | Required only if you want to simulate instead of downloading to real hardware. |

---

## 2. Installation

### 2a. Clone the repositories

Place both repositories side by side under the same parent directory:

```
E:\Software_Siemens\
├── tiaportal-mcp\           # MCP server (102 tools)
└── plc-automation-harness\  # This repo (knowledge + agents)
```

Clone the harness:

```bash
cd E:\Software_Siemens
git clone <harness-repo-url> plc-automation-harness
```

### 2b. Build the tiaportal-mcp server

Follow the build instructions in the tiaportal-mcp repository. The default
build produces an executable at:

```
E:\Software_Siemens\tiaportal-mcp\src\TiaMcpServer\bin\Release\net48\TiaMcpServer.exe
```

### 2c. Verify the MCP configuration

Open `.claude/settings.json` in the harness directory:

```json
{
  "mcpServers": {
    "tiaportal-mcp": {
      "command": "E:\\Software_Siemens\\tiaportal-mcp\\src\\TiaMcpServer\\bin\\Release\\net48\\TiaMcpServer.exe",
      "args": ["--tia-major-version", "19"],
      "env": {}
    }
  }
}
```

Verify that:

1. The `command` path points to your actual built executable.
2. The `--tia-major-version` argument matches your TIA Portal version (`19` or `20`).

If your paths differ, edit the file to match your setup. For example, if you
built tiaportal-mcp elsewhere or use TIA Portal V20:

```json
{
  "mcpServers": {
    "tiaportal-mcp": {
      "command": "C:\\Your\\Path\\To\\TiaMcpServer.exe",
      "args": ["--tia-major-version", "20"],
      "env": {}
    }
  }
}
```

---

## 3. First Session

### 3a. Open Claude Code in the harness directory

```bash
cd E:\Software_Siemens\plc-automation-harness
claude
```

When Claude Code starts, it automatically loads:
- `CLAUDE.md` — lean root prompt with tool categories and pointers
- `.claude/rules/scl-rules.md` — mandatory SCL programming rules (alwaysApply)
- `.claude/rules/safety.md` — safety-critical operation warnings (alwaysApply)
- `.claude/settings.json` — MCP server connection to tiaportal-mcp

### 3b. Verify the MCP connection

Inside Claude Code, type:

```
/mcp
```

You should see `tiaportal-mcp` listed as a connected MCP server with its
102 tools available. If the server is not listed or shows as disconnected,
see the Troubleshooting section below.

### 3c. Test basic connectivity

Ask Claude to check the TIA Portal connection:

```
Check if TIA Portal is connected. If not, connect to it.
```

Claude will call `GetState` to check the connection status. If TIA Portal is
running, it will connect automatically via `Connect`. You should see a
response confirming `IsConnected: true` and the TIA Portal version.

---

## 4. Your First Project

This section walks through the end-to-end workflow for creating a PLC project
from scratch. You can also invoke this as a skill: type `/new-project` in
Claude Code to get the full guided workflow.

Make sure TIA Portal is running before you start.

### Step 1: Create the project

Ask Claude:

```
Create a new TIA Portal project called "MyFirstProject" at D:\TIA-Projects\MyFirstProject
```

Claude will call `CreateProject` with your project name and path. The parent
directory (`D:\TIA-Projects\`) must already exist on disk.

### Step 2: Add a PLC device

Ask Claude:

```
Add an S7-1500 PLC (CPU 1515-2 PN) named PLC_1 to the project. Configure it for simulation.
```

Claude will:
1. Search the hardware catalog with `GetHardwareCatalog` to find the correct type identifier.
2. Call `AddDevice` with the type identifier, device name, and `configureForSimulation=true`.

If you are targeting real hardware instead of simulation, say so and provide
the PLC's IP address.

### Step 3: Write SCL code

Ask Claude to write a simple program:

```
Write an SCL program for PLC_1 that blinks an output Q0.0 every 1 second using a TON timer.
```

Claude will:
1. Plan the block structure (OB1 for the main cycle, possibly an FB for the blink logic).
2. Write the SCL source using `SetExternalSourceContent`.
3. Generate blocks from the source using `GenerateBlocksFromSource`.

### Step 4: Compile

Ask Claude:

```
Compile the software for PLC_1.
```

Claude calls `CompileSoftware`. If there are errors, Claude will read the error
messages, fix the source, and recompile automatically (up to 5 iterations),
following the debug-compile-errors workflow.

### Step 5: Download and test (simulation)

If you have PLCSim Advanced installed:

```
Start a PLCSim simulation for PLC_1 and download the program.
```

Claude will:
1. Create a PLCSim instance with `PlcSimCreateInstance`.
2. Start it with `PlcSimStart`.
3. Configure online access with `ConfigOnlineAccess`.
4. Download the software with `DownloadSoftware`.

### Step 6: Verify via S7 runtime connection

```
Connect to the PLC via S7 and read Q0.0 to verify the blink program is running.
```

Claude will use `S7Connect`, then `S7ReadVariable` to read runtime values
directly from the PLC memory.

---

## 5. Using Skills and Agents

The harness provides two types of specialized capabilities:

### Skills (invoke with `/skill-name`)

Skills are guided workflows that load full step-by-step procedures:

| Skill | Command | Purpose |
|-------|---------|---------|
| **New Project** | `/new-project` | Create project, add device, SCL, compile, simulate, download, verify (9 steps) |
| **SCL Inject** | `/scl-inject` | Write SCL → generate blocks → compile (4 steps, primary code workflow) |
| **Debug Compile** | `/debug-compile` | Iterative compile error repair loop (max 5 iterations) |
| **Download Test** | `/download-test` | Download to PLC/PLCSim, verify via S7.Net read/write (6 steps) |
| **Modify Program** | `/modify-program` | Open existing project, explore, modify, recompile, save (5 steps) |

### Agents (invoke with `@agent-name`)

Agents are specialized personas with domain-specific knowledge:

| Agent | Command | Purpose |
|-------|---------|---------|
| **SCL Developer** | `@scl-developer` | Generate production-ready SCL code with block planning and injection |
| **SCL Debugger** | `@scl-debugger` | Diagnose and fix compile/runtime errors (7-step debug loop) |
| **SCL Reviewer** | `@scl-reviewer` | Review code quality, safety, IEC 61131-3 compliance (30-item checklist) |
| **PLC Architect** | `@plc-architect` | Design program architecture and block decomposition |

### When to use which

- Full project from scratch: `/new-project` skill
- Just inject SCL code: `/scl-inject` skill
- Complex program design: `@plc-architect` first, then `@scl-developer`
- Code won't compile: `/debug-compile` skill or `@scl-debugger` agent
- Code review before deployment: `@scl-reviewer`
- Quick single-block task: `@scl-developer` directly

---

## 6. Exploring Knowledge

The `knowledge/` directory is the harness's reference library. Every
subdirectory has an `_index.md` file that lists all documents with descriptions
and tags, making it easy for Claude to discover relevant material.

### Core reference files

| File | What it covers |
|------|---------------|
| `knowledge/scl-language-reference.md` | Complete SCL syntax, data types, operators, control flow |
| `knowledge/s7-1500.md` | S7-1500 specific features: VARIANT, OOP, 64-bit types |
| `knowledge/s7-1200-limitations.md` | S7-1200 restrictions vs S7-1500 with workarounds |
| `knowledge/tia-openness-api.md` | TIA Portal Openness API guide for MCP tool workflows |

### Design patterns (`knowledge/patterns/`)

Reusable SCL patterns with complete, compilable code:

- **state-machine.md** -- Enum-based finite state machine with entry/exit actions and timer transitions
- **alarm-management.md** -- Program Alarm, diagnostic buffer, alarm classes
- **timer-counter.md** -- TON/TOF/TP patterns, cascaded timers, pulse generators
- **data-logging.md** -- Ring buffer, recipe DB, data serialization
- **communication.md** -- PUT/GET, TCP/UDP, MODBUS TCP, S7 communication
- **error-handling.md** -- ENO chain, status word pattern, error aggregation

### Industry examples (`knowledge/industry/`)

Domain-specific application examples with full SCL implementations:

- **conveyor-control.md** -- Belt conveyor with sensors, jam detection, sequences
- **motor-starter.md** -- DOL, star-delta, VFD control patterns
- **pid-loop.md** -- PID_Compact usage, manual/auto mode, tuning (S7-1500 only)
- **batch-process.md** -- ISA-88 batch concepts: fill/heat/drain phases

### Case database (`case-db/`)

20 annotated cases that Claude uses for few-shot learning:

- `case-db/success/` -- 10 success cases (LED blink, motor control, traffic light, conveyor, PID, recipes, alarms, Modbus, data logging, star-delta starter)
- `case-db/errors/` -- 10 error cases (type mismatch, missing instance DB, array bounds, timer in temp, missing hash prefix, string without length, REAL equality, block order, optimized access conflict, S7-1200 unsupported type)

### Workflows (`workflows/`)

Step-by-step procedures with exact MCP tool calls:

- **new-project-from-scratch.md** -- Full end-to-end: create project, add device, write SCL, compile, download, verify
- **debug-compile-errors.md** -- Read error, fix source, recompile loop (max 5 iterations)
- **download-and-test.md** -- Validate, download, S7Connect, read/write verify
- **modify-existing-program.md** -- Open project, export/read, modify, reimport, save

### How Claude discovers content

Claude reads `_index.md` files to find relevant documents. You can also
point Claude to specific files:

```
Read the state-machine pattern and implement a 4-state washing machine cycle.
```

```
Check the error cases for common type mismatch issues.
```

---

## 7. Adding Your Own Content

The harness is designed to be extended. Every content directory contains a
`_template.md` file you can copy to create new entries.

### Add a new pattern

1. Copy the template:
   ```
   copy knowledge\patterns\_template.md knowledge\patterns\my-pattern.md
   ```
2. Edit `my-pattern.md` with complete content: Problem, Solution (with
   compilable SCL code), Usage Example, Gotchas, and Related links.
3. Add an entry to `knowledge\patterns\_index.md` with file name, description,
   tags, and CPU compatibility.

### Add a new industry example

1. Copy the template:
   ```
   copy knowledge\industry\_template.md knowledge\industry\my-example.md
   ```
2. Fill in Requirements, Block Structure, SCL Code, and Test Procedure.
3. Add an entry to `knowledge\industry\_index.md`.

### Add a new success case

1. Copy the template:
   ```
   copy case-db\success\_template.md case-db\success\011-my-case.md
   ```
2. Include Requirements, complete SCL Code, MCP tool commands used, and
   Test Procedure.
3. Add an entry to `case-db\_index.md`.

### Add a new error case

1. Copy the template:
   ```
   copy case-db\errors\_template.md case-db\errors\011-my-error.md
   ```
2. Include the Error Message, Bad Code (what went wrong), Good Code (the fix),
   and a Why section explaining the root cause.
3. Add an entry to `case-db\_index.md`.

### Add a new workflow

1. Copy the template:
   ```
   copy workflows\_template.md workflows\my-workflow.md
   ```
2. Write Prerequisites, Steps with exact MCP tool calls, and a
   Troubleshooting table.
3. Add an entry to `workflows\_index.md`.

### Add a new agent

1. Create a new file at `.claude\agents\my-agent.md` with agent instructions.
2. Add the `/my-agent` command reference to the Agents section in `CLAUDE.md`.

### The registry rule

Every `_index.md` is a registry. If a file is not listed in its directory's
`_index.md`, Claude will not discover it automatically. Always update the
index after adding new content.

---

## 8. Troubleshooting

### MCP server not connected

**Symptom:** `/mcp` in Claude Code does not show `tiaportal-mcp`, or it shows
as disconnected.

**Fixes:**
1. Verify the executable path in `.claude/settings.json` points to a valid
   `TiaMcpServer.exe` file.
2. Confirm you built the server in Release mode (`bin\Release\net48\`).
3. Check that `--tia-major-version` matches your TIA Portal installation
   (19 or 20).
4. Restart Claude Code after editing `settings.json`.

### TIA Portal not running

**Symptom:** `GetState` returns `IsConnected: false` and `Connect` fails.

**Fixes:**
1. Open TIA Portal manually before starting Claude Code.
2. Make sure TIA Portal has fully loaded (splash screen dismissed, start page visible).
3. Run `Connect` again after TIA Portal is ready.

### Wrong TIA Portal version

**Symptom:** `Connect` fails with a version mismatch error or COM registration error.

**Fixes:**
1. Check which TIA Portal version is installed: V19 or V20.
2. Update `--tia-major-version` in `.claude/settings.json` to match.
3. If you have multiple versions installed, make sure the correct one is running.

### CreateProject fails with "path already exists"

**Symptom:** Cannot create a new project because the target folder exists.

**Fixes:**
1. Delete or rename the existing project folder on disk.
2. Or choose a different `projectPath` for the new project.

### AddDevice fails with "typeIdentifier not found"

**Symptom:** The device cannot be added because the catalog entry is wrong.

**Fixes:**
1. Use `GetHardwareCatalog` with a broad filter (e.g., `"S7-1500"`) to list
   available entries.
2. Copy the exact `TypeIdentifier` string from the catalog results, including
   the firmware version suffix (e.g., `/V2.0`).

### GenerateBlocksFromSource fails

**Symptom:** Block generation fails due to SCL syntax errors.

**Fixes:**
1. Review the error message for the line number and error description.
2. Fix the SCL source and call `SetExternalSourceContent` again.
3. Retry `GenerateBlocksFromSource`.
4. Use `/scl-debugger` for automated diagnosis and repair.

### CompileSoftware returns errors

**Symptom:** Compilation succeeds but reports `ErrorCount > 0`.

**Fixes:**
1. Read the error messages in the compile output.
2. Use `/debug-compile` skill or invoke `@scl-debugger` agent.
3. Common causes: missing instance DBs, type mismatches, global variable
   access inside FBs.

### Download fails with "PLC not reachable"

**Symptom:** `DownloadSoftware` cannot reach the PLC.

**Fixes:**
1. For simulation: make sure PLCSim Advanced is running and the instance is
   started (`PlcSimStart`).
2. For real hardware: verify the PLC IP address matches the device configuration
   in the project. Check that the PLC is in STOP mode. Check Windows Firewall
   rules.
3. Run `ConfigOnlineAccess` with the correct adapter before downloading.

### S7Connect fails

**Symptom:** Cannot establish an S7 runtime connection.

**Fixes:**
1. Verify the IP address matches the PLC (simulated or real).
2. Confirm the `cpuType` parameter matches the target (`S7-1500` or `S7-1200`).
3. Check that the PLC is in RUN mode after download.
4. Check Windows Firewall: port 102 (ISO-on-TCP) must be open.

---

## Next Steps

- Read through `CLAUDE.md` to understand all the rules Claude follows when
  writing SCL code.
- Browse the case database (`case-db/success/`) to see complete working
  examples.
- Try modifying an existing project using the `/modify-program` skill.
- Add your own patterns and industry examples to grow the knowledge base.
- See `CONTRIBUTING.md` for detailed contribution guidelines.
