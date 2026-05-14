---
name: download-test
description: Download compiled program to PLC/PLCSim and verify via S7.Net read/write
---

# Download and Test

## Prerequisites

- A TIA Portal project is open with a successfully compiled program (`ErrorCount == 0`).
- `softwarePath` is known (e.g. `"PLC_1/Program blocks"`).
- Target PLC (or PLCSim instance) is reachable at the known `ipAddress`.
- For real hardware: PLC is in **STOP** mode and **you have confirmed with the user** that overwriting the program is acceptable.
- S7.Net-accessible DB variables exist in the program (DBs must have `{ S7_Optimized_Access := 'FALSE' }`).

---

## Steps

### Step 0: Check PLCSim instances (simulation only)

Before downloading, always check existing PLCSim Advanced instances to avoid IP conflicts.
These tools are from the **`plcsimadv-mcp`** server.

```
GetInstances()
```

**If instances exist**, check their state:
```
GetInstanceState(instanceName="<name>")
```

| Situation | Action |
|-----------|--------|
| Instance with **matching IP** and state **Run** | Use it — proceed to Step 1 |
| Instance with **same IP** but wrong CPU | Create new instance with **different IP**, update TIA Portal device via `SetDeviceAddress`, recompile |
| No instances | Call `SetManagerConfig(networkMode="TCPIPSingleAdapter")`, then `CreateInstance`, then `StartInstance` |

> **Never create a PLCSim instance with an IP that's already in use by another instance.** Either reuse the existing one or pick a different IP and update the device configuration in TIA Portal to match.

---

### Step 1: Validate end-to-end readiness

```
ValidateEndToEndReady(softwarePath="PLC_1/Program blocks")
```
Expected:
```json
{
  "Success": true,
  "Compiled": true,
  "ErrorCount": 0,
  "WarningCount": 0,
  "HardwareConfigured": true
}
```

If `Success` is `false` or `Compiled` is `false`, resolve the listed issues before continuing:
- Compile errors -> follow `/debug-compile` skill
- Hardware not configured -> run `/new-project` skill Step 3-4

---

### Step 2: Download the software

> **Confirm with the user before this step.** Downloading overwrites the PLC program and will interrupt any running process.

```
DownloadSoftware(softwarePath="PLC_1/Program blocks")
```
Expected:
```json
{ "Success": true, "Message": "Download completed successfully" }
```

If the download fails, consult the Troubleshooting table below before retrying.

---

### Step 3: Connect via S7.Net

```
S7Connect(
  ipAddress="192.168.0.1",
  cpuType="S7-1500"
)
```
Expected:
```json
{ "Success": true, "Connected": true, "CpuType": "S7-1500" }
```

Common `cpuType` values: `"S7-1500"`, `"S7-1200"`, `"S7-300"`, `"S7-400"`.

---

### Step 4: Read test-point variables

#### Single variable read

```
S7ReadVariable(
  address="DB1.DBX0.0",
  dataType="Bool"
)
```
Expected: `{ "Success": true, "Value": false }`

#### Multiple variables in one call (preferred for efficiency)

```
S7ReadVariables(
  variables=[
    { "address": "DB1.DBX0.0", "dataType": "Bool" },
    { "address": "DB1.DBW2",   "dataType": "Int"  },
    { "address": "DB1.DBD4",   "dataType": "Real" }
  ]
)
```
Expected:
```json
{
  "Success": true,
  "Results": [
    { "address": "DB1.DBX0.0", "value": false,  "success": true },
    { "address": "DB1.DBW2",   "value": 0,      "success": true },
    { "address": "DB1.DBD4",   "value": 0.0,    "success": true }
  ]
}
```

Record baseline values before writing.

---

### Step 5: Write a test value and verify by reading back

> **Confirm with the user before writing to a live PLC.** Writing can affect running machinery and processes.

#### 5a. Write the test value

```
S7WriteVariable(
  address="DB1.DBX0.0",
  dataType="Bool",
  value=true
)
```
Expected: `{ "Success": true }`

#### 5b. Read back to confirm

```
S7ReadVariable(
  address="DB1.DBX0.0",
  dataType="Bool"
)
```
Expected: `{ "Success": true, "Value": true }`  
The read-back value must match what was written.  
If it does not match, the PLC program may be overwriting the variable each scan cycle — this is expected for output variables driven by logic.

#### 5c. Restore original value (if needed)

```
S7WriteVariable(
  address="DB1.DBX0.0",
  dataType="Bool",
  value=false
)
```

---

### Step 6: Disconnect

```
S7Disconnect()
```
Expected: `{ "Success": true }`

Always disconnect cleanly. Leaving a persistent S7 connection may block other clients from accessing the PLC.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `ValidateEndToEndReady` returns `Compiled: false` | Project not compiled or compile failed | Run `CompileSoftware` and fix all errors first |
| `DownloadSoftware` fails: "PLC not reachable" | IP mismatch, PLC powered off, or firewall blocking | Verify IP in TIA Portal device properties; check network connectivity with ping; disable Windows Firewall for testing |
| `DownloadSoftware` fails: "PLC not in STOP" | PLC is in RUN mode and download requires STOP | Put PLC in STOP via TIA Portal Online menu, or use `SetPlcState(state="Stop")` |
| `DownloadSoftware` fails: "Consistency check error" | Hardware config or firmware mismatch | Ensure CPU typeIdentifier matches physical/simulated CPU; recheck `AddDevice` parameters |
| `S7Connect` fails: "Connection refused" | Wrong IP or CPU type | Confirm IP in TIA Portal; for PLCSim use `"192.168.0.1"` (default) |
| `S7Connect` fails after PLCSim download | PLCSim still in STOP after download | `StartInstance(instanceName="PLC_1_Sim")` (plcsimadv-mcp), then retry `S7Connect` |
| `S7ReadVariable` returns wrong type | `dataType` parameter does not match DB field | Check DB declaration for correct data type; map SCL types to S7 addresses (BOOL->DBX, INT->DBW, DINT/REAL->DBD) |
| `S7ReadVariable` value always 0 after write | PLC logic overwrites variable each cycle | This is correct behavior for output variables; test with a non-driven memory variable instead |
| `S7WriteVariable` succeeds but no observable effect | Variable is an input (read-only from S7 perspective) or logic resets it | Use a dedicated test/debug DB or put PLC in STOP before writing |
| `S7Disconnect` returns error | Connection already closed or timed out | Ignore — connection is no longer active |
