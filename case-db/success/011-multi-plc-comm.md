# Case 011: Multi-PLC Communication

## Frontmatter
- **Tags**: communication, putget, s7, handshake, multi-plc
- **CPU**: Both
- **Complexity**: Advanced

## Requirements
PLC_A sends a setpoint (REAL) and mode (INT) to PLC_B via the PUT system function block.
PLC_B returns an actual value (REAL) and status (INT) — but this case focuses on the
PLC_A sender side only. A sequence counter in the shared UDT increments on each
successful PUT, allowing the receiver to detect stale data. Retry logic (up to 3
attempts) handles transient communication errors before flagging a permanent fault.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| UDT_CommData | UDT | Shared data structure: sequence counter, setpoint, mode, actual, status |
| FB_S7Writer | FB | PUT with REQ/DONE/ERROR handshake, retry logic, sequence counter |
| DB_SendBuffer | DB | Local buffer holding data to write to remote PLC |
| DB_Writer1 | DB | Instance DB for FB_S7Writer |
| Main (OB1) | OB | Fills send buffer, calls FB_S7Writer, maps diagnostics to outputs |

## SCL Code
```scl
// =============================================================================
// UDT_CommData — Shared data structure for inter-PLC exchange
// Must exist identically on both PLC_A and PLC_B
// =============================================================================
TYPE "UDT_CommData"
VERSION : 0.1
  STRUCT
    SeqCounter : DINT;          // Increments on each successful send
    Setpoint   : REAL;          // Setpoint value from PLC_A (e.g., speed in RPM)
    Mode       : INT;           // Operating mode from PLC_A (0=Off, 1=Manual, 2=Auto)
    ActualVal  : REAL;          // Actual process value from PLC_B
    Status     : INT;           // Status from PLC_B (0=OK, 1=Warning, 2=Fault)
    Spare      : INT;           // Reserved for future use / alignment
  END_STRUCT;
END_TYPE

// =============================================================================
// FB_S7Writer — PUT sender with handshake, retry, and sequence counter
// Writes UDT_CommData to a remote PLC's DB via PUT system FB.
// PUT is asynchronous: REQ triggers the write, DONE/ERROR signals completion.
// =============================================================================
FUNCTION_BLOCK "FB_S7Writer"
TITLE = 'S7 PUT sender with handshake and retry logic'
VERSION : 0.1

VAR_INPUT
  Enable        : BOOL;              // Enable cyclic sending
  SendInterval  : TIME := T#500ms;   // Minimum time between PUT requests
  ConnectionID  : WORD := W#16#0001; // S7 connection ID (from HW Config)
END_VAR

VAR_IN_OUT
  SendData      : "UDT_CommData";    // Data to send — caller fills Setpoint and Mode
END_VAR

VAR_OUTPUT
  Done          : BOOL;              // Last PUT completed successfully
  Busy          : BOOL;              // PUT in progress
  SendCount     : DINT;              // Total successful sends
  RetryCount    : INT;               // Current retry attempt (0 = first try)
  Error         : BOOL;
  ErrorID       : INT;               // 0=OK, 1=PUT error, 2=retries exhausted, 99=invalid state
END_VAR

VAR
  State         : INT := 0;          // 0=Idle, 1=Send, 2=WaitDone, 10=Fault
  CycleTimer    : TON_TIME;          // Interval timer between sends
  PutDone       : BOOL;
  PutBusy       : BOOL;
  PutError      : BOOL;
  PutStatus     : WORD;
  ReqPulse      : BOOL;              // One-shot REQ signal for PUT
  InternalRetry : INT := 0;
END_VAR

VAR CONSTANT
  MAX_RETRIES   : INT := 3;
END_VAR

BEGIN
  // ---- Disabled: reset everything ----
  IF NOT #Enable THEN
    #State := 0;
    #Done := FALSE;
    #Busy := FALSE;
    #Error := FALSE;
    #ErrorID := 0;
    #ReqPulse := FALSE;
    #InternalRetry := 0;
    #CycleTimer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  CASE #State OF

    0: // Idle — wait for send interval
      #Done := FALSE;
      #Busy := FALSE;
      #ReqPulse := FALSE;

      #CycleTimer(IN := TRUE, PT := #SendInterval);
      IF #CycleTimer.Q THEN
        #CycleTimer(IN := FALSE, PT := T#0ms);
        #InternalRetry := 0;
        #Error := FALSE;
        #ErrorID := 0;
        #State := 1;
      END_IF;

    1: // Send — assert REQ pulse
      #Busy := TRUE;
      #ReqPulse := TRUE;
      #State := 2;

    2: // WaitDone — monitor PUT completion
      #ReqPulse := FALSE;  // REQ is one-shot

      IF #PutDone AND NOT #PutBusy THEN
        // Success — increment sequence counter
        #SendData.SeqCounter := #SendData.SeqCounter + 1;
        #SendCount := #SendCount + 1;
        #Done := TRUE;
        #Busy := FALSE;
        #Error := FALSE;
        #ErrorID := 0;
        #RetryCount := 0;
        #InternalRetry := 0;
        #State := 0;

      ELSIF #PutError AND NOT #PutBusy THEN
        // Error — retry or escalate
        #InternalRetry := #InternalRetry + 1;
        #RetryCount := #InternalRetry;

        IF #InternalRetry >= #MAX_RETRIES THEN
          #Error := TRUE;
          #ErrorID := 2;  // Retries exhausted
          #Busy := FALSE;
          #Done := FALSE;
          #State := 10;
        ELSE
          #ErrorID := 1;  // Transient PUT error, retrying
          #State := 1;
        END_IF;

      ELSE
        // PutBusy = TRUE or not yet started — remain here
        ;
      END_IF;

    10: // Fault — permanent error, wait for Enable toggle to reset
      #Busy := FALSE;
      #Done := FALSE;
      #Error := TRUE;
      IF NOT #Enable THEN
        #State := 0;
      END_IF;

    ELSE
      #State := 0;
      #Error := TRUE;
      #ErrorID := 99;
  END_CASE;

  // ---- Call PUT system FB ----
  // Writes SendData to remote PLC's DB10, starting at byte 0
  // UDT size: DINT=4 + REAL=4 + INT=2 + REAL=4 + INT=2 + INT=2 = 18 bytes
  // Connection ID must be configured in TIA Portal Network View
  "PUT"(REQ    := #ReqPulse,
        ID     := #ConnectionID,
        ADDR_1 := P#DB10.DBX0.0 BYTE 18,
        SD_1   := #SendData,
        DONE   => #PutDone,
        BUSY   => #PutBusy,
        ERROR  => #PutError,
        STATUS => #PutStatus);
END_FUNCTION_BLOCK

// =============================================================================
// DB_SendBuffer — Local buffer holding data to send to remote PLC
// =============================================================================
DATA_BLOCK "DB_SendBuffer"
{ S7_Optimized_Access := 'FALSE' }
TITLE = 'Send buffer for inter-PLC data'
VERSION : 0.1
NON_RETAIN
  VAR
    Data : "UDT_CommData";
  END_VAR
BEGIN
  Data.SeqCounter := 0;
  Data.Setpoint := 0.0;
  Data.Mode := 0;
  Data.ActualVal := 0.0;
  Data.Status := 0;
  Data.Spare := 0;
END_DATA_BLOCK

// =============================================================================
// DB_Writer1 — Instance DB for FB_S7Writer
// =============================================================================
DATA_BLOCK "DB_Writer1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_S7Writer"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program for PLC_A (sender side)
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  // Fill send buffer with process data
  "DB_SendBuffer".Data.Setpoint := 1500.0;     // Speed setpoint (RPM)
  "DB_SendBuffer".Data.Mode := 2;               // Auto mode

  // Call sender FB
  "DB_Writer1"(
    Enable       := %I0.0,                      // Enable via input
    SendInterval := T#500ms,
    ConnectionID := W#16#0001,
    SendData     := "DB_SendBuffer".Data
  );

  // Map diagnostics to outputs
  %Q0.0 := "DB_Writer1".Done;                   // Send OK indicator
  %Q0.1 := "DB_Writer1".Busy;                   // Send in progress
  %Q0.2 := "DB_Writer1".Error;                  // Permanent fault indicator
END_ORGANIZATION_BLOCK
```

## MCP Commands Used
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

Note: Before downloading, the remote PLC (PLC_B) must have DB10 created with the same
UDT_CommData layout. PUT/GET access must be enabled on PLC_B: Device Properties >
Protection & Security > "Permit access with PUT/GET communication from remote partner".
The S7 connection must be configured in TIA Portal Network View with the correct remote
IP address and connection ID (W#16#0001).

## Key Decisions
- PUT/GET over Open User Communication (OUC) — PUT/GET is simpler for S7-to-S7
  communication: no socket management, no byte serialization, no TCON/TDISCON lifecycle.
  OUC is more flexible (works with non-Siemens devices, supports TCP/UDP) but adds
  complexity that is unnecessary for direct PLC-to-PLC data exchange
- Sequence counter for handshake — the receiver can compare the current SeqCounter with
  the previous value to detect stale data. If the counter stops incrementing, the sender
  has stopped or the link is down. This is simpler and more reliable than a heartbeat
  timer alone
- Non-optimized DB access (`S7_Optimized_Access := 'FALSE'`) — PUT/GET accesses remote
  DB memory by absolute address (P#DB10.DBX0.0). Optimized DBs rearrange memory layout
  at compile time, breaking cross-PLC address references. Non-optimized DBs guarantee
  stable byte offsets
- Retry with escalation — transient errors (e.g., network congestion) are retried up to
  3 times before declaring a permanent fault. This prevents nuisance alarms while still
  catching genuine failures
- Fault state requires Enable toggle to reset — prevents automatic restart after a
  permanent error, giving the operator a chance to investigate before re-enabling
  communication
- Single-direction focus — this case covers PLC_A sending only. For bidirectional
  communication, add an FB_S7Reader (GET) on PLC_A and an FB_S7Writer (PUT) on PLC_B,
  each with their own connection ID and remote DB address

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state (disabled)
S7ReadVariable(address="DB2.DBW0")       -> State (INT, expect 0=Idle)
S7ReadVariable(address="DB2.DBX2.0")     -> Done (BOOL, expect FALSE)
S7ReadVariable(address="DB2.DBX2.2")     -> Error (BOOL, expect FALSE)

// Enable communication
S7WriteVariable(address="%I0.0", value="true", type="Bit")

// Wait ~500ms for first send cycle, then verify
S7ReadVariable(address="DB2.DBW0")       -> State (INT, expect cycling 0->1->2->0)
S7ReadVariable(address="DB2.DBX2.0")     -> Done (BOOL, expect TRUE after first send)
S7ReadVariable(address="DB2.DBD4")       -> SendCount (DINT, expect >= 1)

// Verify send buffer — sequence counter should be incrementing
S7ReadVariable(address="DB1.DBD0")       -> SeqCounter (DINT, expect >= 1)
S7ReadVariable(address="DB1.DBD4")       -> Setpoint (REAL, expect 1500.0)
S7ReadVariable(address="DB1.DBW8")       -> Mode (INT, expect 2)

// Wait a few seconds, re-read to confirm counter is advancing
S7ReadVariable(address="DB1.DBD0")       -> SeqCounter (DINT, expect higher than before)
S7ReadVariable(address="DB2.DBD4")       -> SendCount (DINT, expect matching SeqCounter)

// Verify on remote PLC (PLC_B) — data arrived in DB10
S7Disconnect()
S7Connect(ipAddress="192.168.0.2", cpuType="S71500")
S7ReadVariable(address="DB10.DBD0")      -> SeqCounter (DINT, should match PLC_A)
S7ReadVariable(address="DB10.DBD4")      -> Setpoint (REAL, expect 1500.0)
S7ReadVariable(address="DB10.DBW8")      -> Mode (INT, expect 2)
S7Disconnect()

// Test error recovery on PLC_A
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Disable and re-enable to reset after fault
S7WriteVariable(address="%I0.0", value="false", type="Bit")
S7ReadVariable(address="DB2.DBW0")       -> State (INT, expect 0=Idle)
S7WriteVariable(address="%I0.0", value="true", type="Bit")
S7ReadVariable(address="DB2.DBW0")       -> State (INT, expect cycling again)

// Check error outputs (should be clear during normal operation)
S7ReadVariable(address="DB2.DBX2.2")     -> Error (BOOL, expect FALSE)
S7ReadVariable(address="DB2.DBW10")      -> ErrorID (INT, expect 0)
S7ReadVariable(address="DB2.DBW8")       -> RetryCount (INT, expect 0)

S7Disconnect()
```
