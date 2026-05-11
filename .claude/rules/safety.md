---
description: Safety warnings for operations that write to physical/simulated PLCs
globs:
alwaysApply: true
---

# Safety-Critical Operations

These MCP tools write to physical or simulated PLCs. ALWAYS confirm with the user before executing:

| Tool | Risk | Confirmation Required |
|------|------|----------------------|
| `DownloadSoftware` | Overwrites the PLC program — may stop running machinery | YES — always |
| `S7WriteVariable` | Writes to running PLC memory — can affect process | YES — always |
| `S7WriteDB` | Writes raw bytes to data block — can corrupt data | YES — always |

## Rules
1. NEVER call these tools without explicit user confirmation
2. State what will happen BEFORE calling: "This will overwrite the PLC program at 192.168.0.1"
3. For real hardware: verify the correct device is targeted (IP, CPU type)
4. For simulation: still confirm, but lower risk
5. After download: verify PLC state before declaring success
