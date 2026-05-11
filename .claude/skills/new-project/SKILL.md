---
name: new-project
description: Create a TIA Portal project from scratch — device setup, SCL injection, compile, simulate, download, verify
---

# New Project from Scratch

Follow these steps in order. Each step includes the exact MCP tool call and expected response.

## Prerequisites

- TIA Portal V19 or V20 is running (or will be opened by the MCP server).
- tiaportal-mcp server is connected (or `Connect` will be called in Step 1).
- A project path on disk that does not yet exist (parent directory must exist).
- SCL source code ready (or to be written in Step 5).
- For simulation: PLCSim Advanced is installed.
- For real hardware download: PLC is reachable on the network.

---

## Steps

### Step 1: Check connection and connect if needed

```
GetState()
```
Expected: `{ "IsConnected": true, "TiaVersion": "V19" }` or similar.  
If `IsConnected` is `false`, call:

```
Connect()
```
Expected: `{ "Success": true, "Message": "Connected to TIA Portal" }`

---

### Step 2: Create a new project

```
CreateProject(
  projectName="MyPlcProject",
  projectPath="D:\\TIA-Projects\\MyPlcProject"
)
```
Expected:
```json
{ "Success": true, "ProjectPath": "D:\\TIA-Projects\\MyPlcProject\\MyPlcProject.ap19" }
```

> The parent directory `D:\TIA-Projects\` must already exist. TIA Portal creates the project sub-folder automatically.

---

### Step 3: Add a PLC device

#### 3a. Find the typeIdentifier using the hardware catalog (optional but recommended)

```
GetHardwareCatalog(filter="6ES7 515")
```
Expected: list of catalog entries with `TypeIdentifier` fields, e.g. `"OrderNumber:6ES7 515-2AM01-0AB0/V2.0"`.

Choose the entry matching your CPU model and firmware.

#### 3b. Add the device

```
AddDevice(
  typeIdentifier="OrderNumber:6ES7 515-2AM01-0AB0/V2.0",
  deviceName="PLC_1",
  configureForSimulation=true,
  ipAddress="192.168.0.1"
)
```
Expected:
```json
{
  "Success": true,
  "DeviceName": "PLC_1",
  "SoftwarePath": "PLC_1/Program blocks"
}
```

> `configureForSimulation=true` auto-configures: PUT/GET communication, full access (no protection), system/clock memory bytes, optimized DB access, and PLCSim adapter.  
> For real hardware: set `configureForSimulation=false`, adjust `ipAddress`, and manually configure these device settings:
> - **PUT/GET communication**: Enabled (Properties → Protection & Security)
> - **Access level**: Full access, no protection
> - **Protection password**: Disabled (empty)
> - **System/clock memory bytes**: Enabled (assign to free MB addresses)
> - **DB access**: Optimized (default); use `S7_Optimized_Access := 'FALSE'` pragma on FBs that need S7.Net direct access

---

### Step 4: Discover the softwarePath from the project tree

```
GetProjectTree()
```
Expected: nested tree where each PLC node has a `SoftwarePath` (e.g. `"PLC_1/Program blocks"`).  
Record this value — it is required for all subsequent tool calls.

---

### Step 5: Create PLC tags BEFORE writing SCL

> **IMPORTANT:** Never use absolute addresses (`%I0.0`, `%M10.0`) directly in SCL.
> Always create named tags first, then reference them by name in the SCL source.
> Using absolute addresses causes TIA Portal to auto-generate ugly tag names like `Tag__639141118790971718`.

#### 5a. Create a tag table

```
CreateTagTable(softwarePath="PLC_1/PLC_1", tableName="ProcessTags")
```

#### 5b. Create tags for all I/O points used in the program

```
CreateTag(softwarePath="PLC_1/PLC_1", tableName="ProcessTags",
  tagName="CmdOpen", dataType="Bool", address="%M10.0", comment="Open command")
CreateTag(softwarePath="PLC_1/PLC_1", tableName="ProcessTags",
  tagName="FbkOpen", dataType="Bool", address="%M11.0", comment="Open feedback")
```

Repeat for every I/O tag. Use meaningful names that match the FB interface.

---

### Step 6: Write SCL source and generate blocks

#### 6a. Write (or replace) the external source file

```
SetExternalSourceContent(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main",
  content="ORGANIZATION_BLOCK OB1\nVAR_TEMP\nEND_VAR\nBEGIN\nEND_ORGANIZATION_BLOCK"
)
```
Expected: `{ "Success": true }`

Replace `content` with the full SCL source. The source should contain all required blocks in dependency order:
1. TYPE (UDTs) — dependencies first
2. FUNCTION (FCs)
3. FUNCTION_BLOCK (FBs)
4. DATA_BLOCK (instance DBs)
5. ORGANIZATION_BLOCK (OBs)

#### 6b. Generate blocks from the source

```
GenerateBlocksFromSource(
  softwarePath="PLC_1/Program blocks",
  sourceName="Main"
)
```
Expected: `{ "Success": true, "BlocksGenerated": 3 }` (count varies).  
If this fails, fix the SCL syntax before proceeding.

---

### Step 7: Compile the software

```
CompileSoftware(softwarePath="PLC_1/Program blocks")
```
Expected:
```json
{ "Success": true, "ErrorCount": 0, "WarningCount": 0 }
```

- If `ErrorCount > 0`, read the error messages and follow the `/debug-compile` skill.
- Warnings may be acceptable; review them before proceeding.

---

### Step 8: PLCSim setup (simulation path only)

Skip this step if downloading to real hardware (go to Step 9).

#### 8a. Check for existing PLCSim instances FIRST

```
PlcSimGetInstances()
```

**If instances exist:** check their IPs and states.
```
PlcSimGetState(instanceName="<existing_name>")
```

| Situation | Action |
|-----------|--------|
| Existing instance has **same IP** as your device and is **Running** | Use it — skip to Step 9 |
| Existing instance has **same IP** but **wrong CPU type** | Create new instance with **different IP** (e.g. 192.168.0.11), then update device IP in TIA Portal via `SetDeviceAddress` to match |
| No existing instances | Create a new one (Step 8b) |

> **IMPORTANT:** If a PLCSim instance already occupies your target IP, do NOT create another instance with the same IP. Either reuse it or pick a different IP and update the TIA Portal device configuration to match.

#### 8b. Create a new PLCSim instance (if needed)

```
PlcSimCreateInstance(
  instanceName="PLC_1_Sim",
  cpuType="1500",
  ipAddress="192.168.0.10"
)
```
Expected: `{ "Success": true, "InstanceName": "PLC_1_Sim" }`

#### 8c. Start the PLCSim instance

```
PlcSimStart(instanceName="PLC_1_Sim")
```
Expected: `{ "Success": true, "State": "Run" }`

#### 8d. Verify PLCSim is reachable

```
PlcSimGetState(instanceName="PLC_1_Sim")
```
Expected: `operatingState: "Run"`. If state is "Stop", the instance is ready for download (CPU will go to RUN after download).

> **If the instance IP doesn't match the TIA Portal device IP**, update the device:
> ```
> SetDeviceAddress(softwarePath="PLC_1/PLC_1", ipAddress="<plcsim_ip>")
> ```
> Then recompile before downloading.

---

### Step 9: Configure online access

```
ConfigOnlineAccess(
  softwarePath="PLC_1/Program blocks",
  ipAddress="192.168.0.1",
  autoDetect=true
)
```
Expected: `{ "Success": true, "AdapterName": "PLCSIM Virtual Eth. Adapter" }` (for simulation)  
or an actual network adapter name for real hardware.

> `autoDetect=true` scans for the PLCSim virtual adapter automatically. For real hardware set `autoDetect=false` and supply the correct `interfaceName`.

---

### Step 10: Download, connect via S7, verify, and disconnect

> **Confirm with the user before downloading to real hardware.** Downloading overwrites the PLC program and may affect running machinery.

#### 9a. Download the software

```
DownloadSoftware(softwarePath="PLC_1/Program blocks")
```
Expected: `{ "Success": true, "Message": "Download completed successfully" }`

#### 9b. Connect via S7.Net

```
S7Connect(ipAddress="192.168.0.1", cpuType="S7-1500")
```
Expected: `{ "Success": true, "Connected": true }`

#### 9c. Read a variable to verify operation

```
S7ReadVariable(
  address="DB1.DBX0.0",
  dataType="Bool"
)
```
Expected: `{ "Success": true, "Value": false }` (or the actual runtime value).  
Adjust `address` and `dataType` to match an actual DB variable in your program.

#### 9d. Disconnect

```
S7Disconnect()
```
Expected: `{ "Success": true }`

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `GetState` returns `IsConnected: false` after `Connect` | TIA Portal not running, or COM registration missing | Launch TIA Portal manually; re-run `Connect()` |
| `CreateProject` fails with "path already exists" | Target folder exists on disk | Delete or rename the existing folder, or choose a new `projectPath` |
| `GetHardwareCatalog` returns empty list | Filter string too specific or catalog not installed | Broaden the filter (e.g. `"S7-1500"`) |
| `AddDevice` fails with "typeIdentifier not found" | Incorrect order number or firmware suffix | Use exact string from `GetHardwareCatalog` result |
| `GenerateBlocksFromSource` fails | SCL syntax error in source content | Fix the SCL and call `SetExternalSourceContent` again before retrying |
| `CompileSoftware` returns errors | Logic or type errors in generated blocks | Follow `/debug-compile` skill |
| `PlcSimCreateInstance` fails | PLCSim Advanced not installed or already running | Check PLCSim installation; stop any existing instance first |
| `ConfigOnlineAccess` cannot find adapter | PLCSim not started, or real NIC name wrong | Start PLCSim first (Step 7), or check NIC name in Windows Device Manager |
| `DownloadSoftware` fails with "PLC not reachable" | IP mismatch or PLC not in STOP mode | Verify `ipAddress` matches PLC configuration; put PLC in STOP mode via TIA Portal |
| `S7Connect` fails | Wrong IP or CPU type | Confirm IP address and CPU model string; check firewall rules |
| `S7ReadVariable` returns unexpected type error | Address or dataType mismatch | Verify the DB structure and use the correct `dataType` parameter |
