# Multi-PLC Communication (PUT/GET)

## Frontmatter
- **Tags**: communication, putget, s7comm, multi-plc, handshake
- **CPU**: Both
- **Difficulty**: Advanced

## Requirements
Two Siemens S7 PLCs exchanging data via PUT/GET system function blocks:
- **PLC_A** (sender): writes setpoint data to PLC_B using PUT, includes a sequence counter that increments on each successful transmission
- **PLC_B** (receiver): reads status data from PLC_A using GET, detects stale data when the sequence counter has not changed for longer than a configurable timeout
- Handshake mechanism: sequence counter in the shared data structure allows both sides to detect stale or lost communication
- Retry logic: up to 3 retries on communication error before flagging a permanent fault
- Both FBs expose Error/ErrorID outputs for diagnostics and HMI integration

PUT and GET are asynchronous system FBs that span multiple scan cycles. The sender and receiver FBs use internal state machines to manage the REQ/DONE/BUSY/ERROR handshake properly.

### Communication Parameters
| Parameter | PLC_A (Sender) | PLC_B (Receiver) |
|-----------|----------------|------------------|
| IP Address | 192.168.0.1 | 192.168.0.2 |
| CPU Type | S7-1500 or S7-1200 | S7-1500 or S7-1200 |
| Connection ID | W#16#0001 | W#16#0002 |
| Remote DB | DB10 (on PLC_B) | DB10 (on PLC_A) |
| Data Direction | Sends setpoints to PLC_B | Reads status from PLC_A |
| Cycle Time | Configurable (default T#500ms) | Configurable (default T#500ms) |
| Stale Timeout | N/A | Configurable (default T#5s) |

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| UDT_CommData | UDT | Shared data structure for inter-PLC exchange | SeqCounter, Setpoint1, Setpoint2, StatusWord, Heartbeat |
| FB_S7Sender | FB | PUT with handshake, retry logic, state machine | IN: Enable, RemoteAddr, SendData; OUT: Done, Error, ErrorID, SendCount, RetryCount |
| FB_S7Receiver | FB | GET with stale detection, retry logic, state machine | IN: Enable, RemoteAddr, StaleTimeout; OUT: RecvData, CommFault, Stale, Error, ErrorID, LastSeqCounter |
| DB_CommSendData | DB | Local data block holding data to send (PLC_A) | Instance of UDT_CommData |
| DB_CommRecvData | DB | Local data block holding received data (PLC_B) | Instance of UDT_CommData |
| DB_Sender1 | DB | Instance DB for FB_S7Sender on PLC_A | Instance of FB_S7Sender |
| DB_Receiver1 | DB | Instance DB for FB_S7Receiver on PLC_B | Instance of FB_S7Receiver |
| Main (OB1) | OB | Cyclic call — sender on PLC_A, receiver on PLC_B | Maps parameters and I/O |

## SCL Code

### PLC_A: Sender Side (PUT with Handshake)

```scl
// =============================================================================
// UDT_CommData — Shared data structure for inter-PLC communication
// Both PLC_A and PLC_B must have this identical UDT
// =============================================================================
TYPE "UDT_CommData"
VERSION : 0.1
  STRUCT
    SeqCounter   : DINT;         // Sequence counter — increments on each successful send
    Setpoint1    : REAL;         // Process setpoint 1 (e.g., speed)
    Setpoint2    : REAL;         // Process setpoint 2 (e.g., temperature)
    StatusWord   : WORD;         // Bit-packed status flags
    Heartbeat    : BOOL;         // Toggling heartbeat bit
    Spare1       : BYTE;         // Reserved for alignment
    Spare2       : INT;          // Reserved for future use
  END_STRUCT;
END_TYPE

// =============================================================================
// FB_S7Sender — PUT with handshake, retry logic, and state machine
// Sends UDT_CommData to a remote PLC via the PUT system FB.
// PUT is asynchronous: REQ triggers the send, DONE/ERROR complete it.
// =============================================================================
FUNCTION_BLOCK "FB_S7Sender"
TITLE = 'S7 Communication Sender with PUT and Handshake'
VERSION : 0.1

VAR_INPUT
  Enable        : BOOL;         // Enable cyclic sending
  SendCycleTime : TIME := T#500ms; // Minimum interval between sends
  MaxRetries    : INT := 3;      // Max retries before permanent error
  ConnectionID  : WORD := W#16#0001; // S7 connection ID (HW identifier)
END_VAR

VAR_IN_OUT
  SendData      : "UDT_CommData"; // Data to send (caller fills Setpoint1, Setpoint2, etc.)
END_VAR

VAR_OUTPUT
  Done          : BOOL;         // Last send completed successfully
  Busy          : BOOL;         // Send in progress
  Error         : BOOL;         // Permanent error (retries exhausted)
  ErrorID       : INT;          // Error code: 0=OK, 1=PUT error, 2=retries exhausted, 3=disabled
  SendCount     : DINT;         // Total successful sends
  RetryCount    : INT;          // Current retry attempt (0 = first try)
  LastStatus    : WORD;         // Last STATUS output from PUT
END_VAR

VAR
  State         : INT := 0;     // State machine: 0=Idle, 1=Requesting, 2=WaitDone
  CycleTimer    : TON_TIME;     // Timer for send interval
  PutDone       : BOOL;         // PUT DONE output
  PutBusy       : BOOL;         // PUT BUSY output
  PutError      : BOOL;         // PUT ERROR output
  PutStatus     : WORD;         // PUT STATUS output
  ReqPulse      : BOOL;         // One-shot REQ signal
  InternalRetry : INT := 0;     // Internal retry counter
  HeartbeatToggle : BOOL;       // Alternating heartbeat
END_VAR

VAR CONSTANT
  ST_IDLE       : INT := 0;
  ST_REQUESTING : INT := 1;
  ST_WAIT_DONE  : INT := 2;
END_VAR

BEGIN
  // ---- Disabled handling ----
  IF NOT #Enable THEN
    #State := #ST_IDLE;
    #Done := FALSE;
    #Busy := FALSE;
    #Error := FALSE;
    #ErrorID := 3;
    #ReqPulse := FALSE;
    #InternalRetry := 0;
    #CycleTimer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  // ---- State machine ----
  CASE #State OF

    0: // ST_IDLE — wait for cycle timer to elapse
      #Done := FALSE;
      #Busy := FALSE;
      #ReqPulse := FALSE;

      #CycleTimer(IN := TRUE, PT := #SendCycleTime);

      IF #CycleTimer.Q THEN
        // Time to send — prepare data
        #CycleTimer(IN := FALSE, PT := T#0ms); // Reset timer
        #InternalRetry := 0;
        #Error := FALSE;
        #ErrorID := 0;
        #State := #ST_REQUESTING;
      END_IF;

    1: // ST_REQUESTING — issue REQ pulse to PUT
      #Busy := TRUE;
      #ReqPulse := TRUE;
      #State := #ST_WAIT_DONE;

    2: // ST_WAIT_DONE — wait for PUT to complete
      #ReqPulse := FALSE; // REQ is one-shot, clear after one scan

      IF #PutDone AND NOT #PutBusy THEN
        // Success
        #SendData.SeqCounter := #SendData.SeqCounter + 1;
        #HeartbeatToggle := NOT #HeartbeatToggle;
        #SendData.Heartbeat := #HeartbeatToggle;
        #SendCount := #SendCount + 1;
        #Done := TRUE;
        #Busy := FALSE;
        #Error := FALSE;
        #ErrorID := 0;
        #RetryCount := 0;
        #InternalRetry := 0;
        #LastStatus := #PutStatus;
        #State := #ST_IDLE;

      ELSIF #PutError AND NOT #PutBusy THEN
        // Error — retry or fail
        #LastStatus := #PutStatus;
        #InternalRetry := #InternalRetry + 1;
        #RetryCount := #InternalRetry;

        IF #InternalRetry >= #MaxRetries THEN
          // Permanent error — retries exhausted
          #Error := TRUE;
          #ErrorID := 2;
          #Busy := FALSE;
          #Done := FALSE;
          #State := #ST_IDLE;
        ELSE
          // Retry
          #ErrorID := 1;
          #State := #ST_REQUESTING;
        END_IF;

      ELSIF NOT #PutBusy AND NOT #PutDone AND NOT #PutError THEN
        // PUT not yet started — keep waiting (should not happen after REQ)
        ;
      END_IF;
      // If PutBusy is TRUE, remain in this state

    ELSE
      // Unknown state — reset
      #State := #ST_IDLE;
      #Error := TRUE;
      #ErrorID := 99;
  END_CASE;

  // ---- Call PUT system FB ----
  // PUT writes SendData to the remote PLC's DB
  // The ADDR parameter uses a hardware-configured S7 connection
  // NOTE: In a real TIA Portal project, PUT is called with the
  // connection ID and remote DB address configured in hardware.
  // The call below shows the logical structure:
  "PUT"(REQ    := #ReqPulse,
        ID     := #ConnectionID,
        ADDR_1 := P#DB10.DBX0.0 BYTE 20,  // Remote DB10, offset 0, 20 bytes
        SD_1   := #SendData,
        DONE   => #PutDone,
        BUSY   => #PutBusy,
        ERROR  => #PutError,
        STATUS => #PutStatus);
END_FUNCTION_BLOCK

// =============================================================================
// DB_CommSendData — Local buffer for data to be sent (PLC_A side)
// =============================================================================
DATA_BLOCK "DB_CommSendData"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  VAR
    Data : "UDT_CommData";
  END_VAR
BEGIN
  Data.SeqCounter := 0;
  Data.Setpoint1 := 0.0;
  Data.Setpoint2 := 0.0;
  Data.StatusWord := W#16#0000;
  Data.Heartbeat := FALSE;
END_DATA_BLOCK

// =============================================================================
// DB_Sender1 — Instance DB for FB_S7Sender on PLC_A
// =============================================================================
DATA_BLOCK "DB_Sender1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_S7Sender"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program for PLC_A (Sender)
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  // Fill setpoints from process or HMI
  "DB_CommSendData".Data.Setpoint1 := 1500.0;    // Speed setpoint (RPM)
  "DB_CommSendData".Data.Setpoint2 := 75.0;       // Temperature setpoint (degC)
  "DB_CommSendData".Data.StatusWord := W#16#0001;  // Bit 0 = system ready

  // Call sender FB
  "DB_Sender1"(
    Enable        := TRUE,
    SendCycleTime := T#500ms,
    MaxRetries    := 3,
    ConnectionID  := W#16#0001,
    SendData      := "DB_CommSendData".Data
  );

  // Map sender status to outputs for diagnostics
  %Q0.0 := "DB_Sender1".Done;        // Send OK indicator
  %Q0.1 := "DB_Sender1".Error;       // Comm error indicator
END_ORGANIZATION_BLOCK
```

---

### PLC_B: Receiver Side (GET with Stale Detection)

```scl
// =============================================================================
// UDT_CommData — Shared data structure (must be identical to PLC_A)
// =============================================================================
TYPE "UDT_CommData"
VERSION : 0.1
  STRUCT
    SeqCounter   : DINT;         // Sequence counter — increments on each successful send
    Setpoint1    : REAL;         // Process setpoint 1 (e.g., speed)
    Setpoint2    : REAL;         // Process setpoint 2 (e.g., temperature)
    StatusWord   : WORD;         // Bit-packed status flags
    Heartbeat    : BOOL;         // Toggling heartbeat bit
    Spare1       : BYTE;         // Reserved for alignment
    Spare2       : INT;          // Reserved for future use
  END_STRUCT;
END_TYPE

// =============================================================================
// FB_S7Receiver — GET with stale data detection, retry logic, state machine
// Reads UDT_CommData from a remote PLC via the GET system FB.
// GET is asynchronous: REQ triggers the read, NDR/ERROR complete it.
// Stale detection: if SeqCounter does not change within StaleTimeout,
// the CommFault output is set.
// =============================================================================
FUNCTION_BLOCK "FB_S7Receiver"
TITLE = 'S7 Communication Receiver with GET and Stale Detection'
VERSION : 0.1

VAR_INPUT
  Enable        : BOOL;         // Enable cyclic receiving
  RecvCycleTime : TIME := T#500ms; // Minimum interval between GET requests
  StaleTimeout  : TIME := T#5s;  // Max time without new SeqCounter before CommFault
  MaxRetries    : INT := 3;      // Max retries before permanent error
  ConnectionID  : WORD := W#16#0002; // S7 connection ID (HW identifier)
END_VAR

VAR_OUTPUT
  RecvData      : "UDT_CommData"; // Last successfully received data
  NewData       : BOOL;         // New data received this scan (NDR)
  CommFault     : BOOL;         // Communication fault — stale data or permanent error
  Stale         : BOOL;         // Stale data detected (SeqCounter not changing)
  Busy          : BOOL;         // GET in progress
  Error         : BOOL;         // Permanent error (retries exhausted)
  ErrorID       : INT;          // Error code: 0=OK, 1=GET error, 2=retries exhausted,
                                 //             3=disabled, 4=stale data
  LastSeqCounter : DINT;        // Last received sequence counter
  RecvCount     : DINT;         // Total successful receives
  RetryCount    : INT;          // Current retry attempt
  LastStatus    : WORD;         // Last STATUS output from GET
END_VAR

VAR
  State         : INT := 0;     // State machine: 0=Idle, 1=Requesting, 2=WaitDone
  CycleTimer    : TON_TIME;     // Timer for receive interval
  StaleTimer    : TON_TIME;     // Timer for stale data detection
  GetNDR        : BOOL;         // GET NDR (New Data Ready) output
  GetBusy       : BOOL;         // GET BUSY output
  GetError      : BOOL;         // GET ERROR output
  GetStatus     : WORD;         // GET STATUS output
  ReqPulse      : BOOL;         // One-shot REQ signal
  InternalRetry : INT := 0;     // Internal retry counter
  PrevSeqCounter : DINT := -1;  // Previous sequence counter for change detection
  RecvBuffer    : "UDT_CommData"; // Receive buffer for GET target
  FirstReceive  : BOOL := TRUE; // First successful receive flag
END_VAR

VAR CONSTANT
  ST_IDLE       : INT := 0;
  ST_REQUESTING : INT := 1;
  ST_WAIT_DONE  : INT := 2;
END_VAR

BEGIN
  // ---- Disabled handling ----
  IF NOT #Enable THEN
    #State := #ST_IDLE;
    #NewData := FALSE;
    #Busy := FALSE;
    #Error := FALSE;
    #ErrorID := 3;
    #CommFault := FALSE;
    #Stale := FALSE;
    #ReqPulse := FALSE;
    #InternalRetry := 0;
    #FirstReceive := TRUE;
    #CycleTimer(IN := FALSE, PT := T#0ms);
    #StaleTimer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  // Clear one-shot flags
  #NewData := FALSE;

  // ---- Stale data detection ----
  // Timer runs continuously; reset when SeqCounter changes
  IF NOT #FirstReceive THEN
    #StaleTimer(IN := TRUE, PT := #StaleTimeout);
    IF #StaleTimer.Q THEN
      #Stale := TRUE;
      #CommFault := TRUE;
      #ErrorID := 4;
    END_IF;
  END_IF;

  // ---- State machine ----
  CASE #State OF

    0: // ST_IDLE — wait for cycle timer to elapse
      #Busy := FALSE;
      #ReqPulse := FALSE;

      #CycleTimer(IN := TRUE, PT := #RecvCycleTime);

      IF #CycleTimer.Q THEN
        #CycleTimer(IN := FALSE, PT := T#0ms); // Reset timer
        #InternalRetry := 0;
        #State := #ST_REQUESTING;
      END_IF;

    1: // ST_REQUESTING — issue REQ pulse to GET
      #Busy := TRUE;
      #ReqPulse := TRUE;
      #State := #ST_WAIT_DONE;

    2: // ST_WAIT_DONE — wait for GET to complete
      #ReqPulse := FALSE; // REQ is one-shot

      IF #GetNDR AND NOT #GetBusy THEN
        // New data received successfully
        #RecvData := #RecvBuffer;
        #LastSeqCounter := #RecvBuffer.SeqCounter;
        #RecvCount := #RecvCount + 1;
        #NewData := TRUE;
        #Busy := FALSE;
        #RetryCount := 0;
        #InternalRetry := 0;
        #LastStatus := #GetStatus;

        // Check if sequence counter changed (new data from sender)
        IF #RecvBuffer.SeqCounter <> #PrevSeqCounter THEN
          #PrevSeqCounter := #RecvBuffer.SeqCounter;
          #Stale := FALSE;
          #CommFault := FALSE;
          #Error := FALSE;
          #ErrorID := 0;
          // Reset stale timer
          #StaleTimer(IN := FALSE, PT := T#0ms);
          #FirstReceive := FALSE;
        END_IF;
        // If SeqCounter is same, data was received but sender has not updated
        // StaleTimer continues running

        #State := #ST_IDLE;

      ELSIF #GetError AND NOT #GetBusy THEN
        // Error — retry or fail
        #LastStatus := #GetStatus;
        #InternalRetry := #InternalRetry + 1;
        #RetryCount := #InternalRetry;

        IF #InternalRetry >= #MaxRetries THEN
          // Permanent error — retries exhausted
          #Error := TRUE;
          #ErrorID := 2;
          #CommFault := TRUE;
          #Busy := FALSE;
          #NewData := FALSE;
          #State := #ST_IDLE;
        ELSE
          // Retry
          #ErrorID := 1;
          #State := #ST_REQUESTING;
        END_IF;

      ELSIF NOT #GetBusy AND NOT #GetNDR AND NOT #GetError THEN
        // GET not yet started — keep waiting
        ;
      END_IF;
      // If GetBusy is TRUE, remain in this state

    ELSE
      // Unknown state — reset
      #State := #ST_IDLE;
      #Error := TRUE;
      #ErrorID := 99;
  END_CASE;

  // ---- Call GET system FB ----
  // GET reads data from the remote PLC's DB into RecvBuffer
  "GET"(REQ    := #ReqPulse,
        ID     := #ConnectionID,
        ADDR_1 := P#DB10.DBX0.0 BYTE 20,  // Remote DB10, offset 0, 20 bytes
        RD_1   := #RecvBuffer,
        NDR    => #GetNDR,
        BUSY   => #GetBusy,
        ERROR  => #GetError,
        STATUS => #GetStatus);
END_FUNCTION_BLOCK

// =============================================================================
// DB_CommRecvData — Local buffer for received data (PLC_B side)
// =============================================================================
DATA_BLOCK "DB_CommRecvData"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  VAR
    Data : "UDT_CommData";
  END_VAR
BEGIN
  Data.SeqCounter := 0;
  Data.Setpoint1 := 0.0;
  Data.Setpoint2 := 0.0;
  Data.StatusWord := W#16#0000;
  Data.Heartbeat := FALSE;
END_DATA_BLOCK

// =============================================================================
// DB_Receiver1 — Instance DB for FB_S7Receiver on PLC_B
// =============================================================================
DATA_BLOCK "DB_Receiver1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_S7Receiver"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program for PLC_B (Receiver)
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  // Call receiver FB
  "DB_Receiver1"(
    Enable        := TRUE,
    RecvCycleTime := T#500ms,
    StaleTimeout  := T#5s,
    MaxRetries    := 3,
    ConnectionID  := W#16#0002
  );

  // Use received setpoints in local process
  // Example: map received data to local variables or outputs
  %QD0 := REAL_TO_DWORD("DB_Receiver1".RecvData.Setpoint1);  // Speed setpoint
  %QD4 := REAL_TO_DWORD("DB_Receiver1".RecvData.Setpoint2);  // Temp setpoint

  // Map comm status to diagnostic outputs
  %Q1.0 := "DB_Receiver1".NewData;     // New data indicator (pulse)
  %Q1.1 := "DB_Receiver1".CommFault;   // Communication fault lamp
  %Q1.2 := "DB_Receiver1".Stale;       // Stale data warning
  %Q1.3 := "DB_Receiver1".Error;       // Permanent error indicator
END_ORGANIZATION_BLOCK
```

## Test Procedure

### 1. Deploy

**PLC_A (Sender):**
```
SetExternalSourceContent(softwarePath="PLC_A/PLC_A", sourceName="main", content=<PLC_A SCL above>)
GenerateBlocksFromSource(softwarePath="PLC_A/PLC_A", sourceName="main")
CompileSoftware(softwarePath="PLC_A/PLC_A")
DownloadSoftware(softwarePath="PLC_A/PLC_A", downloadOptions="Software")
```

**PLC_B (Receiver):**
```
SetExternalSourceContent(softwarePath="PLC_B/PLC_B", sourceName="main", content=<PLC_B SCL above>)
GenerateBlocksFromSource(softwarePath="PLC_B/PLC_B", sourceName="main")
CompileSoftware(softwarePath="PLC_B/PLC_B")
DownloadSoftware(softwarePath="PLC_B/PLC_B", downloadOptions="Software")
```

**Prerequisites:**
- Both PLCs must have S7 connections configured in TIA Portal hardware configuration (Network view)
- PUT/GET communication must be enabled on both PLCs (Device configuration > Protection & Security > "Permit access with PUT/GET communication from remote partner")
- DB10 must exist on each remote PLC as the target/source data block

### 2. Verify via S7 Runtime

**PLC_A — Sender diagnostics:**
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Sender state and status
S7ReadVariable(address="DB_Sender1.State")          // State: 0=Idle, 1=Requesting, 2=WaitDone
S7ReadVariable(address="DB_Sender1.Done")           // Last send OK (BOOL)
S7ReadVariable(address="DB_Sender1.Error")          // Permanent error (BOOL)
S7ReadVariable(address="DB_Sender1.ErrorID")        // Error code (INT)
S7ReadVariable(address="DB_Sender1.SendCount")      // Total successful sends (DINT)
S7ReadVariable(address="DB_Sender1.RetryCount")     // Current retry count (INT)
S7ReadVariable(address="DB_Sender1.LastStatus")     // PUT STATUS word

// Send data buffer
S7ReadVariable(address="DB_CommSendData.Data.SeqCounter")  // Sequence counter (DINT)
S7ReadVariable(address="DB_CommSendData.Data.Setpoint1")   // Speed setpoint (REAL)
S7ReadVariable(address="DB_CommSendData.Data.Setpoint2")   // Temp setpoint (REAL)
S7ReadVariable(address="DB_CommSendData.Data.Heartbeat")   // Heartbeat toggle (BOOL)

S7Disconnect()
```

**PLC_B — Receiver diagnostics:**
```
S7Connect(ipAddress="192.168.0.2", cpuType="S71500")

// Receiver state and status
S7ReadVariable(address="DB_Receiver1.State")          // State: 0=Idle, 1=Requesting, 2=WaitDone
S7ReadVariable(address="DB_Receiver1.NewData")        // New data this scan (BOOL)
S7ReadVariable(address="DB_Receiver1.CommFault")      // Communication fault (BOOL)
S7ReadVariable(address="DB_Receiver1.Stale")          // Stale data detected (BOOL)
S7ReadVariable(address="DB_Receiver1.Error")          // Permanent error (BOOL)
S7ReadVariable(address="DB_Receiver1.ErrorID")        // Error code (INT)
S7ReadVariable(address="DB_Receiver1.RecvCount")      // Total successful receives (DINT)
S7ReadVariable(address="DB_Receiver1.RetryCount")     // Current retry count (INT)
S7ReadVariable(address="DB_Receiver1.LastSeqCounter") // Last received SeqCounter (DINT)

// Received data
S7ReadVariable(address="DB_CommRecvData.Data.SeqCounter")  // Sequence counter (DINT)
S7ReadVariable(address="DB_CommRecvData.Data.Setpoint1")   // Speed setpoint (REAL)
S7ReadVariable(address="DB_CommRecvData.Data.Setpoint2")   // Temp setpoint (REAL)
S7ReadVariable(address="DB_CommRecvData.Data.Heartbeat")   // Heartbeat (BOOL)

S7Disconnect()
```

### 3. Functional Tests

1. **Normal communication**: Enable both sender and receiver. Verify SeqCounter increments on PLC_A every ~500ms and the same value appears on PLC_B with NewData=TRUE. SendCount and RecvCount should increase at the same rate.

2. **Data integrity**: Change Setpoint1 on PLC_A from 1500.0 to 2000.0. Verify PLC_B receives the updated value within one send cycle. Confirm SeqCounter incremented.

3. **Stale data detection**: Disable the sender on PLC_A (Enable=FALSE) while the receiver on PLC_B continues. After StaleTimeout (5s), verify PLC_B shows Stale=TRUE, CommFault=TRUE, ErrorID=4.

4. **Communication recovery**: Re-enable the sender after a stale fault. Verify PLC_B clears CommFault and Stale when a new SeqCounter value arrives. ErrorID should return to 0.

5. **Retry on error**: Temporarily disconnect the network cable. Verify RetryCount increments up to MaxRetries (3). After 3 failed retries, Error=TRUE, ErrorID=2, CommFault=TRUE. Reconnect cable and re-enable to recover.

6. **Heartbeat toggle**: Monitor the Heartbeat field in UDT_CommData. It should toggle between TRUE and FALSE on each successful send, providing a visual indication of active communication.

7. **Sequence counter rollover**: Set SeqCounter near DINT max (2,147,483,647) and verify the system continues to function after rollover.

## Variations

### Open User Communication (OUC) via TCP

Instead of PUT/GET, use TSEND_C and TRCV_C for TCP-based communication. This approach is more flexible and works across different PLC families, including S7-1200 to S7-1500 communication.

Key differences:
- Use `TSEND_C` (FB sending) and `TRCV_C` (FB receiving) instead of PUT/GET
- Connection is established via TCON parameters (IP address, port) rather than hardware-configured S7 connections
- Data is sent as raw byte arrays — serialize UDT_CommData to/from BYTE arrays
- OUC supports TCP, UDP, and ISO-on-TCP protocols
- No need to enable "PUT/GET access" on the remote PLC

```scl
// Example: TSEND_C call structure (replaces PUT in FB_S7Sender)
// TSEND_C establishes the connection AND sends data in one block
"TSEND_C_DB"(
  CONT   := TRUE,               // Maintain connection
  CONNECT := #TconParams,        // Connection parameters (IP, port)
  DATA   := #SendData,           // Data to send
  LEN    := 20,                  // Length in bytes
  REQ    := #ReqPulse,
  DONE   => #SendDone,
  BUSY   => #SendBusy,
  ERROR  => #SendError,
  STATUS => #SendStatus
);
```

### S7-1200 Notes

The SCL code is compatible with S7-1200 with these considerations:

1. **PUT/GET must be explicitly enabled**: In TIA Portal, navigate to Device configuration > Properties > Protection & Security > Connection mechanisms, and check "Permit access with PUT/GET communication from remote partner". This is disabled by default on S7-1200.

2. **Timer type**: If using S7-1200 firmware < V4.0, replace `TON_TIME` with `TON` (IEC timer).

3. **Data block size**: The UDT_CommData structure is well within the S7-1200 DB size limit of 16 KB. Keep transferred data structures small to minimize communication overhead.

4. **Connection resources**: S7-1200 has limited connection resources (typically 8-16 depending on CPU variant). Each PUT/GET connection consumes one resource. Plan connection usage carefully in multi-PLC systems.

5. **No LREAL/LINT**: The UDT_CommData uses REAL and DINT, which are compatible with S7-1200. Avoid LREAL or LINT in the shared data structure.

### Bidirectional Communication

For full duplex communication where both PLCs send and receive, deploy both FB_S7Sender and FB_S7Receiver on each PLC:

- **PLC_A**: FB_S7Sender (sends setpoints) + FB_S7Receiver (reads PLC_B status)
- **PLC_B**: FB_S7Receiver (reads PLC_A setpoints) + FB_S7Sender (sends status back)

Each direction uses its own connection ID, remote DB address, and UDT_CommData instance. Define separate UDTs for each data direction (e.g., `UDT_SetpointData` and `UDT_StatusData`) to keep interfaces clean.

```scl
// PLC_A: OB1 with bidirectional communication
"DB_Sender1"(Enable := TRUE, SendData := "DB_SetpointSend".Data, ConnectionID := W#16#0001);
"DB_Receiver1"(Enable := TRUE, StaleTimeout := T#5s, ConnectionID := W#16#0002);

// Use received status from PLC_B
IF "DB_Receiver1".RecvData.StatusWord.%X0 THEN
  // PLC_B reports ready
  ;
END_IF;
```

### Multi-PLC Ring Network (3+ PLCs)

For systems with more than two PLCs, extend the pattern into a ring or star topology:
- Each PLC sends its status to all peers using multiple FB_S7Sender instances
- Each PLC receives data from all peers using multiple FB_S7Receiver instances
- Use a master coordinator PLC to aggregate status from all nodes
- Assign unique connection IDs for each PLC-to-PLC link (e.g., W#16#0001 for PLC_A->PLC_B, W#16#0003 for PLC_A->PLC_C)
- Monitor CommFault on each link independently to isolate which PLC has lost communication
