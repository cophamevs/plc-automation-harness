# Case 009: Ring Buffer Data Logger

## Frontmatter
- **Tags**: logging, ring-buffer, data, temperature, event, timestamp, intermediate
- **CPU**: Both
- **Complexity**: Intermediate

## Requirements
Log temperature readings every 10 seconds into a ring buffer of 100 entries. Also log
alarm events immediately (event-triggered, not periodic). Each log entry stores a
timestamp, value, event code, and validity flag. FB_RingLogger manages the ring buffer
with write index wrapping. FC_GetLogEntry retrieves entries by index with newest-first
ordering. Test by writing data and reading back via S7ReadDBStruct to verify ring buffer
operation.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| UDT_LogEntry | UDT | Single log record (timestamp, value, event code) |
| FC_GetLogEntry | FC | Read a log entry by index (0=newest) |
| FB_RingLogger | FB | Ring buffer manager with periodic and event triggers |
| DB_Logger1 | DB | Instance for FB_RingLogger |
| Main (OB1) | OB | Feeds temperature and alarm events to logger |

## SCL Code
```scl
TYPE "UDT_LogEntry"
VERSION : 0.1
  STRUCT
    Timestamp  : DINT;       // Milliseconds since startup (TIME_TO_DINT)
    Value      : REAL;       // Logged value
    EventCode  : INT;        // 0=periodic sample, 1=alarm, 2=change
    Valid      : BOOL;       // Entry has been written
  END_STRUCT;
END_TYPE

FUNCTION "FC_GetLogEntry" : BOOL
TITLE = 'Read log entry by index (0=newest, 1=second newest, ...)'
VERSION : 0.1
VAR_INPUT
  EntryIndex   : INT;        // 0 = most recent entry
  WriteIndex   : INT;        // Current write index from FB_RingLogger
  BufferFull   : BOOL;       // Buffer has wrapped at least once
  Buffer       : ARRAY[0..99] OF "UDT_LogEntry";
END_VAR
VAR_OUTPUT
  Timestamp    : DINT;
  Value        : REAL;
  EventCode    : INT;
  Valid        : BOOL;
END_VAR
VAR_TEMP
  actualIndex  : INT;
  maxEntries   : INT;
END_VAR
BEGIN
  // Determine how many valid entries exist
  IF #BufferFull THEN
    #maxEntries := 100;
  ELSE
    #maxEntries := #WriteIndex;
  END_IF;

  // Bounds check
  IF #EntryIndex < 0 OR #EntryIndex >= #maxEntries THEN
    #Timestamp := 0;
    #Value := 0.0;
    #EventCode := 0;
    #Valid := FALSE;
    #FC_GetLogEntry := FALSE;
    RETURN;
  END_IF;

  // Calculate actual buffer position (newest first)
  // WriteIndex points to the NEXT write position, so newest = WriteIndex - 1
  #actualIndex := #WriteIndex - 1 - #EntryIndex;
  IF #actualIndex < 0 THEN
    #actualIndex := #actualIndex + 100;
  END_IF;

  #Timestamp := #Buffer[#actualIndex].Timestamp;
  #Value := #Buffer[#actualIndex].Value;
  #EventCode := #Buffer[#actualIndex].EventCode;
  #Valid := #Buffer[#actualIndex].Valid;
  #FC_GetLogEntry := TRUE;
END_FUNCTION

FUNCTION_BLOCK "FB_RingLogger"
TITLE = 'Ring buffer data logger with periodic and event triggers'
VERSION : 0.1

VAR_INPUT
  LogValue     : REAL;        // Value to log
  EventCode    : INT;         // Event type (0=sample, 1=alarm, 2=change)
  EventTrigger : BOOL;        // Rising edge logs immediately (event-driven)
  SampleTime   : TIME := T#10s;  // Periodic logging interval
  ClearAll     : BOOL;        // Clear entire buffer
END_VAR

VAR_OUTPUT
  EntryCount   : INT;         // Total entries written (saturates at 32767)
  BufferFull   : BOOL;        // Buffer has wrapped at least once
  WriteIndex   : INT;         // Current write position (for FC_GetLogEntry)
  Error        : BOOL;
  ErrorID      : INT;
END_VAR

VAR
  Buffer       : ARRAY[0..99] OF "UDT_LogEntry";
  WrIdx        : INT := 0;
  TotalWrites  : DINT := 0;
  PrevTrigger  : BOOL;
  SampleTimer  : TON_TIME;
END_VAR

VAR CONSTANT
  BUFFER_SIZE  : INT := 100;
END_VAR

VAR_TEMP
  i            : INT;
  doLog        : BOOL;
  logCode      : INT;
END_VAR

BEGIN
  #Error := FALSE;
  #ErrorID := 0;
  #doLog := FALSE;
  #logCode := 0;

  // Clear buffer
  IF #ClearAll THEN
    FOR #i := 0 TO #BUFFER_SIZE - 1 DO
      #Buffer[#i].Valid := FALSE;
      #Buffer[#i].Timestamp := 0;
      #Buffer[#i].Value := 0.0;
      #Buffer[#i].EventCode := 0;
    END_FOR;
    #WrIdx := 0;
    #TotalWrites := 0;
    #BufferFull := FALSE;
    #SampleTimer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  // Event trigger (rising edge) -- immediate log
  IF #EventTrigger AND NOT #PrevTrigger THEN
    #doLog := TRUE;
    #logCode := #EventCode;
  END_IF;
  #PrevTrigger := #EventTrigger;

  // Periodic sample timer
  #SampleTimer(IN := TRUE, PT := #SampleTime);
  IF #SampleTimer.Q THEN
    #SampleTimer(IN := FALSE, PT := T#0ms);  // Reset timer
    IF NOT #doLog THEN
      // Only log periodic if event didn't already log this scan
      #doLog := TRUE;
      #logCode := 0;  // 0 = periodic sample
    END_IF;
  END_IF;

  // Write entry to ring buffer
  IF #doLog THEN
    #Buffer[#WrIdx].Value := #LogValue;
    #Buffer[#WrIdx].EventCode := #logCode;
    #Buffer[#WrIdx].Timestamp := TIME_TO_DINT("Clock_1ms");
    #Buffer[#WrIdx].Valid := TRUE;

    #WrIdx := #WrIdx + 1;
    #TotalWrites := #TotalWrites + 1;

    IF #WrIdx >= #BUFFER_SIZE THEN
      #WrIdx := 0;
      #BufferFull := TRUE;
    END_IF;
  END_IF;

  // Outputs
  #WriteIndex := #WrIdx;
  IF #TotalWrites > 32767 THEN
    #EntryCount := 32767;  // Saturate INT
  ELSE
    #EntryCount := DINT_TO_INT(#TotalWrites);
  END_IF;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Logger1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_RingLogger"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp        : INT;
  rawAnalog   : INT;
  scaledTemp  : REAL;
  alarmActive : BOOL;
  readOK      : BOOL;
  readTS      : DINT;
  readVal     : REAL;
  readCode    : INT;
  readValid   : BOOL;
END_VAR
BEGIN
  // Scale analog input to temperature (0-27648 -> 0-200 degrees)
  #rawAnalog := %IW64;
  #scaledTemp := INT_TO_REAL(#rawAnalog) * 200.0 / 27648.0;

  // Alarm condition: temperature > 150 degrees
  #alarmActive := #scaledTemp > 150.0;

  // Call ring logger: periodic every 10s + event on alarm
  "DB_Logger1"(
    LogValue     := #scaledTemp,
    EventCode    := 1,                    // 1 = alarm event (used when EventTrigger fires)
    EventTrigger := #alarmActive,
    SampleTime   := T#10s,
    ClearAll     := %I1.0                 // Manual clear via input
  );

  // Read newest log entry for HMI display
  #readOK := "FC_GetLogEntry"(
    EntryIndex := 0,
    WriteIndex := "DB_Logger1".WriteIndex,
    BufferFull := "DB_Logger1".BufferFull,
    Buffer     := "DB_Logger1".Buffer,
    Timestamp  => #readTS,
    Value      => #readVal,
    EventCode  => #readCode,
    Valid      => #readValid
  );
END_ORGANIZATION_BLOCK
```

## MCP Commands Used
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

## Key Decisions
- Ring buffer with 100 entries -- wraps around when full, oldest data overwritten;
  100 entries x ~12 bytes = ~1.2 KB, well within S7-1200 DB limits
- Dual trigger: periodic (TON timer) + event (rising edge) -- captures both steady-state
  trends and transient alarm events without duplicating on the same scan
- FC_GetLogEntry with newest-first indexing -- index 0 = most recent, simplifies HMI
  display of recent history without requiring the HMI to know the write pointer
- WriteIndex and BufferFull exposed as outputs -- FC_GetLogEntry needs these to calculate
  actual buffer position and determine how many valid entries exist
- Timestamp via "Clock_1ms" system variable -- milliseconds since PLC startup, sufficient
  for relative timing; use real-time clock for absolute timestamps
- TotalWrites as DINT (up to 2 billion) with INT output saturated at 32767 -- prevents
  overflow while keeping output type compatible
- SampleTimer reset pattern: call with IN:=FALSE then re-enter state -- ensures clean
  rising edge for next period
- S7_Optimized_Access=FALSE on instance DB for S7.Net buffer readback
- Block order: UDT -> FC -> FB -> instance DB -> OB

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state -- empty buffer
S7ReadVariable(address="DB1.DBW0")      -> EntryCount (INT, expect 0)
S7ReadVariable(address="DB1.DBX2.0")    -> BufferFull (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBW4")      -> WriteIndex (INT, expect 0)

// Wait 10+ seconds for first periodic log entry
S7ReadVariable(address="DB1.DBW0")      -> EntryCount (INT, expect >= 1)
S7ReadVariable(address="DB1.DBW4")      -> WriteIndex (INT, expect >= 1)

// Read first log entry directly from buffer (entry 0 in ring buffer)
// UDT_LogEntry: Timestamp(DINT,4) + Value(REAL,4) + EventCode(INT,2) + Valid(BOOL,1) = ~11 bytes
S7ReadDBStruct(dbNumber=1, startByte=8, count=11)   -> First entry (Timestamp, Value, EventCode, Valid)
S7ReadVariable(address="DB1.DBD8")      -> Buffer[0].Timestamp (DINT, non-zero)
S7ReadVariable(address="DB1.DBD12")     -> Buffer[0].Value (REAL, current temperature)
S7ReadVariable(address="DB1.DBW16")     -> Buffer[0].EventCode (INT, expect 0=periodic)
S7ReadVariable(address="DB1.DBX18.0")   -> Buffer[0].Valid (BOOL, expect TRUE)

// Trigger alarm event: simulate temperature > 150 via analog input
// Write high value to analog input or force alarm condition
S7ReadVariable(address="DB1.DBW0")      -> EntryCount (INT, should increment)

// Wait for multiple entries, verify ring buffer wrapping
// After 100+ entries:
S7ReadVariable(address="DB1.DBX2.0")    -> BufferFull (BOOL, expect TRUE after wrap)

// Clear buffer
S7WriteVariable(address="%I1.0", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> EntryCount (INT, expect 0)
S7ReadVariable(address="DB1.DBW4")      -> WriteIndex (INT, expect 0)
S7WriteVariable(address="%I1.0", value="false", type="Bit")

S7Disconnect()
```
