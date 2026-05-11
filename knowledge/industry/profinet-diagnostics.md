# PROFINET Diagnostics

## Frontmatter
- **Tags**: profinet, diagnostics, station-failure, device-status, io-device
- **CPU**: Both
- **Difficulty**: Advanced

## Requirements
Monitor PROFINET I/O device status across a network of distributed I/O stations.
Detect station failure (device goes offline) and recovery (device comes back online),
log events with timestamps, and provide aggregated status for HMI display.

Two complementary detection mechanisms:
1. **OB86 (Rack/Station Failure)** — called immediately by the OS when a PROFINET device
   goes offline or recovers. Provides the hardware identifier of the failing device.
   If OB86 does not exist in the project, the CPU transitions to STOP on station failure.
2. **Cyclic polling in OB1** — FB_ProfinetMonitor maintains the device status array,
   updates aggregated counters, and provides a consistent HMI interface.

### Configuration Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| MAX_DEVICES | CONST INT | 16 | Maximum monitored PROFINET devices |
| DeviceName | STRING[32] | '' | Descriptive name for each device |
| HwId | INT | 0 | Hardware identifier (module address) of each device |
| ExpectedOnline | BOOL | TRUE | Whether device is expected to be present |

### PROFINET Event Classes
| OB86_EV_CLASS Value | Meaning |
|---------------------|---------|
| 16#38 | Incoming event (station failure) |
| 16#39 | Outgoing event (station recovery) |

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| UDT_DeviceStatus | UDT | Per-device PROFINET status record | Online, FailCount, LastFailTime, Name, HwId, ExpectedOnline |
| FB_ProfinetMonitor | FB | Monitors N devices, updates status array, aggregates | IN: device config; OUT: device status array, AllOnline, DevicesOffline, Error, ErrorID |
| DB_PnConfig | DB | Device list with expected addresses and names | Array of config records |
| DB_PnMonitor | DB | Instance DB for FB_ProfinetMonitor | Instance of FB_ProfinetMonitor |
| Main (OB1) | OB | Cyclic call to FB_ProfinetMonitor | Passes config, reads status |
| OB86 | OB | Rack/station failure interrupt handler | Captures HW ID and event class, writes to shared DB |

## SCL Code

```scl
// =============================================================================
// UDT_DeviceStatus — Per-device PROFINET status record
// =============================================================================
TYPE "UDT_DeviceStatus"
VERSION : 0.1
  STRUCT
    Online          : BOOL;       // TRUE = device is currently online
    FailCount       : INT;        // Number of times this device has gone offline
    LastFailTime    : DINT;       // Timestamp of last failure (ms since CPU start)
    LastRecoverTime : DINT;       // Timestamp of last recovery (ms since CPU start)
    Name            : STRING[32]; // Descriptive name of the device
    HwId            : INT;        // Hardware identifier (module address)
    ExpectedOnline  : BOOL;       // TRUE = device should be present in normal operation
    FailActive      : BOOL;       // TRUE = currently in failure state
  END_STRUCT;
END_TYPE

// =============================================================================
// UDT_PnEvent — PROFINET event record from OB86
// =============================================================================
TYPE "UDT_PnEvent"
VERSION : 0.1
  STRUCT
    NewEvent        : BOOL;       // TRUE = unprocessed event pending
    EventClass      : BYTE;       // 16#38 = failure, 16#39 = recovery
    FaultId         : BYTE;       // Fault identifier from OB86
    ModuleAddr      : INT;        // Hardware identifier of failing device
    Timestamp       : DINT;       // ms counter when event occurred
  END_STRUCT;
END_TYPE

// =============================================================================
// FB_ProfinetMonitor — Monitors PROFINET device status for up to 16 devices
// =============================================================================
FUNCTION_BLOCK "FB_ProfinetMonitor"
TITLE = 'PROFINET I/O Device Monitor'
VERSION : 0.1

VAR_INPUT
  Enable          : BOOL;       // Enable monitoring
  ResetCounters   : BOOL;       // Reset all fail counters
  NumDevices      : INT;        // Number of devices to monitor (1..16)
  CpuRunTime      : DINT;       // Current CPU run time in ms (from system clock)
END_VAR

VAR_OUTPUT
  AllOnline       : BOOL;       // TRUE = all expected devices are online
  DevicesOffline  : INT;        // Number of expected devices currently offline
  TotalFailCount  : DINT;       // Sum of all fail counts across all devices
  Error           : BOOL;       // Error flag
  ErrorID         : INT;        // Error code: 0=OK, 1=NumDevices out of range,
                                //   2=event buffer overflow, 3=unknown HwId in event
END_VAR

VAR_IN_OUT
  DeviceStatus    : ARRAY[1..16] OF "UDT_DeviceStatus"; // Device status array
  EventBuffer     : ARRAY[1..8] OF "UDT_PnEvent";       // Event buffer from OB86
END_VAR

VAR
  i               : INT;        // Loop index
  j               : INT;        // Inner loop index
  devCount        : INT;        // Clamped device count
  offlineCount    : INT;        // Temporary offline counter
  totalFails      : DINT;       // Temporary total fail counter
  eventFound      : BOOL;       // Event matched a known device
  prevResetCounters : BOOL;     // Previous scan value for edge detection
END_VAR

VAR CONSTANT
  MAX_DEVICES     : INT := 16;  // Maximum number of monitored devices
  MAX_EVENTS      : INT := 8;   // Maximum events in buffer
  EV_CLASS_FAIL   : BYTE := 16#38; // Incoming event = station failure
  EV_CLASS_RECOVER : BYTE := 16#39; // Outgoing event = station recovery
END_VAR

BEGIN
  // ---- Input validation ----
  #Error := FALSE;
  #ErrorID := 0;

  IF NOT #Enable THEN
    RETURN;
  END_IF;

  // Clamp NumDevices to valid range
  IF #NumDevices < 1 OR #NumDevices > #MAX_DEVICES THEN
    #Error := TRUE;
    #ErrorID := 1;  // NumDevices out of range
    RETURN;
  END_IF;
  #devCount := #NumDevices;

  // ---- Reset counters on rising edge ----
  IF #ResetCounters AND NOT #prevResetCounters THEN
    FOR #i := 1 TO #devCount DO
      #DeviceStatus[#i].FailCount := 0;
      #DeviceStatus[#i].LastFailTime := 0;
      #DeviceStatus[#i].LastRecoverTime := 0;
      #DeviceStatus[#i].FailActive := FALSE;
    END_FOR;
  END_IF;
  #prevResetCounters := #ResetCounters;

  // ---- Process event buffer from OB86 ----
  FOR #j := 1 TO #MAX_EVENTS DO
    IF #EventBuffer[#j].NewEvent THEN
      #eventFound := FALSE;

      // Find the device matching this hardware ID
      FOR #i := 1 TO #devCount DO
        IF #DeviceStatus[#i].HwId = #EventBuffer[#j].ModuleAddr THEN
          #eventFound := TRUE;

          CASE BYTE_TO_INT(#EventBuffer[#j].EventClass) OF
            16#38:  // Station failure
              #DeviceStatus[#i].Online := FALSE;
              #DeviceStatus[#i].FailActive := TRUE;
              #DeviceStatus[#i].FailCount := #DeviceStatus[#i].FailCount + 1;
              #DeviceStatus[#i].LastFailTime := #EventBuffer[#j].Timestamp;

            16#39:  // Station recovery
              #DeviceStatus[#i].Online := TRUE;
              #DeviceStatus[#i].FailActive := FALSE;
              #DeviceStatus[#i].LastRecoverTime := #EventBuffer[#j].Timestamp;

            ELSE
              // Unknown event class — ignore but flag
              #Error := TRUE;
              #ErrorID := 2;
          END_CASE;
        END_IF;
      END_FOR;

      // If no matching device found, flag error
      IF NOT #eventFound THEN
        #Error := TRUE;
        #ErrorID := 3;  // Unknown HwId in event
      END_IF;

      // Mark event as processed
      #EventBuffer[#j].NewEvent := FALSE;
    END_IF;
  END_FOR;

  // ---- Calculate aggregated status ----
  #offlineCount := 0;
  #totalFails := 0;

  FOR #i := 1 TO #devCount DO
    // Count only devices that are expected to be online
    IF #DeviceStatus[#i].ExpectedOnline AND NOT #DeviceStatus[#i].Online THEN
      #offlineCount := #offlineCount + 1;
    END_IF;
    #totalFails := #totalFails + INT_TO_DINT(#DeviceStatus[#i].FailCount);
  END_FOR;

  #DevicesOffline := #offlineCount;
  #TotalFailCount := #totalFails;
  #AllOnline := (#offlineCount = 0);

END_FUNCTION_BLOCK

// =============================================================================
// DB_PnConfig — PROFINET device configuration
//   Pre-populated with example device names and hardware IDs.
//   Adjust HwId values to match your actual TIA Portal HW configuration.
// =============================================================================
DATA_BLOCK "DB_PnConfig"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    NumDevices : INT := 4;
    Device     : ARRAY[1..16] OF STRUCT
      Name           : STRING[32];
      HwId           : INT;
      ExpectedOnline : BOOL;
    END_STRUCT;
  END_STRUCT;
BEGIN
  Device[1].Name := 'ET200SP_Station1';
  Device[1].HwId := 256;
  Device[1].ExpectedOnline := TRUE;

  Device[2].Name := 'ET200SP_Station2';
  Device[2].HwId := 257;
  Device[2].ExpectedOnline := TRUE;

  Device[3].Name := 'ET200SP_Station3';
  Device[3].HwId := 258;
  Device[3].ExpectedOnline := TRUE;

  Device[4].Name := 'ET200SP_Station4';
  Device[4].HwId := 259;
  Device[4].ExpectedOnline := TRUE;
END_DATA_BLOCK

// =============================================================================
// DB_PnEvents — Shared event buffer written by OB86, read by FB_ProfinetMonitor
// =============================================================================
DATA_BLOCK "DB_PnEvents"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    EventWriteIndex : INT := 1;   // Next write position (circular 1..8)
    Events          : ARRAY[1..8] OF "UDT_PnEvent";
  END_STRUCT;
BEGIN
END_DATA_BLOCK

// =============================================================================
// DB_PnMonitor — Instance DB for FB_ProfinetMonitor
// =============================================================================
DATA_BLOCK "DB_PnMonitor"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_ProfinetMonitor"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program: initialize device status and call monitor
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  tempInt   : INT;
  idx       : INT;
  cpuTime   : DINT;
END_VAR
BEGIN
  // ---- Read CPU run time for timestamps (ms since last cold restart) ----
  // Use TIME_TCK() system function to get a DINT ms counter
  #cpuTime := TIME_TO_DINT(TIME_TCK());

  // ---- Copy device config into status array on first scan or config change ----
  // In production, this would be done once at startup (OB100).
  // For simplicity, we refresh names and HwIds every scan.
  FOR #idx := 1 TO "DB_PnConfig".NumDevices DO
    "DB_PnMonitor".DeviceStatus[#idx].Name := "DB_PnConfig".Device[#idx].Name;
    "DB_PnMonitor".DeviceStatus[#idx].HwId := "DB_PnConfig".Device[#idx].HwId;
    "DB_PnMonitor".DeviceStatus[#idx].ExpectedOnline := "DB_PnConfig".Device[#idx].ExpectedOnline;
  END_FOR;

  // ---- Call PROFINET monitor ----
  "DB_PnMonitor"(
    Enable        := TRUE,
    ResetCounters := FALSE,
    NumDevices    := "DB_PnConfig".NumDevices,
    CpuRunTime    := #cpuTime,
    DeviceStatus  := "DB_PnMonitor".DeviceStatus,
    EventBuffer   := "DB_PnEvents".Events
  );
END_ORGANIZATION_BLOCK

// =============================================================================
// OB86 — Rack/Station Failure OB
//   Called by the OS when a PROFINET device fails or recovers.
//   Writes event data into the shared DB_PnEvents buffer for processing
//   by FB_ProfinetMonitor in the next OB1 cycle.
//
//   VAR_TEMP variables are populated automatically by the S7 runtime:
//   - OB86_EV_CLASS:  Event class (16#38 = incoming/fail, 16#39 = outgoing/recover)
//   - OB86_FLT_ID:    Fault identifier
//   - OB86_MDL_ADDR:  Module address = hardware identifier of failing device
// =============================================================================
ORGANIZATION_BLOCK "OB86"
TITLE = 'Rack / Station Failure'
VERSION : 0.1
VAR_TEMP
  OB86_EV_CLASS   : BYTE;    // Event class (16#38=fail, 16#39=recover)
  OB86_FLT_ID     : BYTE;    // Fault identifier
  OB86_PRIORITY   : BYTE;    // OB priority class
  OB86_OB_NUMBR   : BYTE;    // OB number (86)
  OB86_RESERVED_1 : BYTE;    // Reserved by system
  OB86_RESERVED_2 : BYTE;    // Reserved by system
  OB86_MDL_ADDR   : INT;     // Module address (HW identifier of failing device)
  OB86_RESERVED_3 : DWORD;   // Reserved by system
  OB86_RESERVED_4 : DWORD;   // Reserved by system
  writeIdx        : INT;     // Local copy of write index
  cpuTime         : DINT;    // Current timestamp
END_VAR
BEGIN
  // ---- Get current CPU time for event timestamp ----
  #cpuTime := TIME_TO_DINT(TIME_TCK());

  // ---- Write event to circular buffer in DB_PnEvents ----
  #writeIdx := "DB_PnEvents".EventWriteIndex;

  // Bounds check on write index
  IF #writeIdx < 1 OR #writeIdx > 8 THEN
    #writeIdx := 1;
  END_IF;

  // Store event data
  "DB_PnEvents".Events[#writeIdx].NewEvent    := TRUE;
  "DB_PnEvents".Events[#writeIdx].EventClass  := #OB86_EV_CLASS;
  "DB_PnEvents".Events[#writeIdx].FaultId     := #OB86_FLT_ID;
  "DB_PnEvents".Events[#writeIdx].ModuleAddr  := #OB86_MDL_ADDR;
  "DB_PnEvents".Events[#writeIdx].Timestamp   := #cpuTime;

  // Advance circular write index
  #writeIdx := #writeIdx + 1;
  IF #writeIdx > 8 THEN
    #writeIdx := 1;
  END_IF;
  "DB_PnEvents".EventWriteIndex := #writeIdx;

END_ORGANIZATION_BLOCK
```

## Test Procedure

### 1. Deploy
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="profinet_diag", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="profinet_diag")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

Before deploying, ensure the TIA Portal project has PROFINET I/O devices configured
with hardware identifiers matching the values in DB_PnConfig. Adjust `HwId` values
to match your actual HW configuration (viewable in Device & Networks view).

### 2. Verify via S7 Runtime
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Read aggregated status from DB_PnMonitor
// NOTE: Offsets depend on the actual instance DB layout.
// Use S7ReadDBStruct to discover offsets, or consult the cross-reference.

// AllOnline (BOOL) — TRUE when all expected devices are online
S7ReadVariable(address="DB_PnMonitor.AllOnline")

// DevicesOffline (INT) — count of expected devices currently offline
S7ReadVariable(address="DB_PnMonitor.DevicesOffline")

// TotalFailCount (DINT) — cumulative failure count across all devices
S7ReadVariable(address="DB_PnMonitor.TotalFailCount")

// Error (BOOL) — monitor error flag
S7ReadVariable(address="DB_PnMonitor.Error")

// ErrorID (INT) — monitor error code
S7ReadVariable(address="DB_PnMonitor.ErrorID")

// Read individual device status (example: device 1)
// DeviceStatus[1].Online
S7ReadVariable(address="DB_PnMonitor.DeviceStatus[1].Online")

// DeviceStatus[1].FailCount
S7ReadVariable(address="DB_PnMonitor.DeviceStatus[1].FailCount")

// DeviceStatus[1].LastFailTime
S7ReadVariable(address="DB_PnMonitor.DeviceStatus[1].LastFailTime")

// DeviceStatus[1].Name
S7ReadVariable(address="DB_PnMonitor.DeviceStatus[1].Name")

// Alternative: read the entire device status array as raw bytes
S7ReadDB(dbNumber=<DB_PnMonitor number>, startByte=0, length=1024)

S7Disconnect()
```

### 3. Functional Tests

1. **Baseline — all devices online**: After download with all PROFINET devices connected,
   verify `AllOnline = TRUE`, `DevicesOffline = 0`, all `DeviceStatus[n].Online = TRUE`.

2. **Station failure**: In PLCSim, simulate a station failure by disconnecting a
   PROFINET device (or use PLCSim Advanced to remove a device from the simulated network).
   Verify:
   - OB86 fires and writes event to DB_PnEvents
   - `DeviceStatus[n].Online = FALSE` for the affected device
   - `DeviceStatus[n].FailCount` increments by 1
   - `DeviceStatus[n].LastFailTime` is updated with the current CPU time
   - `AllOnline = FALSE`, `DevicesOffline = 1`

3. **Station recovery**: Reconnect the disconnected device. Verify:
   - OB86 fires with event class 16#39 (recovery)
   - `DeviceStatus[n].Online = TRUE`
   - `DeviceStatus[n].FailActive = FALSE`
   - `AllOnline = TRUE`, `DevicesOffline = 0`
   - `FailCount` remains at the previous value (does not decrement)

4. **Multiple simultaneous failures**: Disconnect two or more devices. Verify:
   - Each device is tracked independently
   - `DevicesOffline` reflects the correct count
   - `AllOnline = FALSE`

5. **Event buffer overflow**: Rapidly trigger more than 8 events before OB1 can process them.
   Verify that the circular buffer wraps without crashing. Oldest unprocessed events
   may be overwritten — this is acceptable behavior for diagnostics.

6. **Counter reset**: Set `ResetCounters = TRUE` via S7WriteVariable. Verify all
   `FailCount` values return to 0 and timestamps are cleared.

7. **Unknown device event**: If OB86 fires for a device not in the config table,
   verify `Error = TRUE`, `ErrorID = 3`.

## Variations

### S7-1200 Variant
The S7-1200 supports OB86 but has the following limitations:

- **Array size**: Maximum DB size is 16 KB. With 16 devices, the status array fits
  comfortably (~50 bytes per device = ~800 bytes total). For larger installations,
  reduce `MAX_DEVICES` or split across multiple DBs.
- **No LREAL**: Timestamps use `DINT` (ms counter) throughout — no changes needed.
  The DINT ms counter wraps after ~24.8 days. For longer uptime tracking, use a
  `DATE_AND_TIME` variable or a pair of DINTs (days + ms within day).
- **No VARIANT**: The code does not use VARIANT, so no changes needed.
- **Nesting depth**: OB86 -> FB call is only 2 levels deep — well within the
  S7-1200 limit of 6.
- **Timer behavior**: No timers are used in this example, so no compatibility issues.
- **STRING**: S7-1200 supports STRING[32] — no changes needed.
- **CPU type for S7Connect**: Change `cpuType` to `"S71200"` when connecting via S7.Net.

```scl
// S7-1200 specific: If using firmware < V4.2, replace TIME_TCK() with a
// free-running DINT counter incremented in OB1:
//
//   VAR_GLOBAL
//     MsCycleCounter : DINT := 0;
//   END_VAR
//
// Increment in OB1:
//   MsCycleCounter := MsCycleCounter + 1;
//
// This gives a rough cycle-count-based timestamp rather than ms.
// For precise timing on S7-1200 V4.2+, TIME_TCK() is available.
```

### Extended Diagnostics with Device Names on HMI
For HMI integration, create a separate FC that builds a summary string listing
all offline devices by name:

```scl
FUNCTION "FC_BuildOfflineSummary" : VOID
VERSION : 0.1
VAR_INPUT
  NumDevices : INT;
END_VAR
VAR_IN_OUT
  DeviceStatus : ARRAY[1..16] OF "UDT_DeviceStatus";
  SummaryText  : STRING[254];
END_VAR
VAR_TEMP
  idx : INT;
END_VAR
BEGIN
  #SummaryText := '';
  FOR #idx := 1 TO #NumDevices DO
    IF #DeviceStatus[#idx].ExpectedOnline AND NOT #DeviceStatus[#idx].Online THEN
      IF LEN(#SummaryText) > 0 THEN
        #SummaryText := CONCAT(IN1 := #SummaryText, IN2 := ', ');
      END_IF;
      #SummaryText := CONCAT(IN1 := #SummaryText, IN2 := #DeviceStatus[#idx].Name);
    END_IF;
  END_FOR;
  IF LEN(#SummaryText) = 0 THEN
    #SummaryText := 'All devices online';
  END_IF;
END_FUNCTION
```

### Multi-PLC PROFINET Monitoring
For plants with multiple PLCs each managing their own PROFINET network, create a
supervisory PLC that collects aggregated status from each subordinate PLC via
PUT/GET or I-Device communication. Each subordinate runs its own `FB_ProfinetMonitor`
and exposes `AllOnline` and `DevicesOffline` in a communication DB. The supervisor
aggregates these into a plant-wide PROFINET health dashboard.

### Alarm Integration
Extend `FB_ProfinetMonitor` to generate alarms using `Program_Alarm` or
`ProDiag` (S7-1500 only) when a device goes offline:

```scl
// Inside FB_ProfinetMonitor, after detecting a failure event:
// (S7-1500 only — ProDiag / Program_Alarm)
//
// IF #DeviceStatus[#i].FailActive AND #DeviceStatus[#i].ExpectedOnline THEN
//   // Trigger alarm with device name and HwId in alarm text
//   // Configure alarm class and priority in TIA Portal alarm settings
// END_IF;
```

For S7-1200, use a simple alarm bit array mapped to HMI alarm tags instead.
