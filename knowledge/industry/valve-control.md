# Valve Control

## Frontmatter
- **Tags**: valve, control, feedback, solenoid, modulating
- **CPU**: Both
- **Difficulty**: Intermediate

## Requirements
On/off solenoid valve with:
- Open and close discrete feedback sensors (limit switches)
- Timer-based timeout detection (valve must reach position within configurable time)
- State machine: Idle -> Opening -> Open -> Closing -> Closed -> Fault
- Error reporting with specific error codes for each fault condition
- Manual override input that bypasses the state machine and drives the output directly
- Interlock input to prevent valve operation when process conditions are unsafe

### Physical I/O Assumed
| Signal | Address | Description |
|--------|---------|-------------|
| CmdOpen | I0.0 | Open command (momentary pushbutton or HMI) |
| CmdClose | I0.1 | Close command (momentary pushbutton or HMI) |
| CmdReset | I0.2 | Fault reset command |
| ManualOverride | I0.3 | Manual override enable (TRUE = manual mode) |
| ManualOutput | I0.4 | Manual output value when override is active |
| Interlock | I0.5 | Interlock OK (TRUE = safe to operate) |
| FbkOpen | I1.0 | Open limit switch feedback (TRUE = valve is fully open) |
| FbkClosed | I1.1 | Closed limit switch feedback (TRUE = valve is fully closed) |
| ValveOut | Q0.0 | Solenoid output (TRUE = energize to open) |

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| UDT_ValveData | UDT | Valve status structure for HMI | State, Position, Error, ErrorID, ManualActive |
| FB_Valve | FB | Valve control with state machine and timeout | Inputs: commands, feedbacks, config; Outputs: solenoid, status |
| DB_Valve1 | DB | Instance DB for valve 1 | Instance of FB_Valve |
| Main (OB1) | OB | Cyclic call to FB_Valve | Maps I/O to FB inputs/outputs |

## SCL Code

```scl
// =============================================================================
// UDT_ValveData — Valve status structure for HMI binding
// =============================================================================
TYPE "UDT_ValveData"
VERSION : 0.1
  STRUCT
    State         : INT;        // Current state number
    StateName     : STRING[20]; // Current state as text
    Position      : INT;        // 0=Unknown, 1=Open, 2=Closed, 3=Intermediate
    Error         : BOOL;       // Fault active
    ErrorID       : INT;        // Error code (0=none, 1=OpenTimeout, 2=CloseTimeout, 3=BothFeedbacks)
    ManualActive  : BOOL;       // Manual override is active
    ValveOut      : BOOL;       // Solenoid output state
    CycleCount    : DINT;       // Total open/close cycles for maintenance
  END_STRUCT;
END_TYPE

// =============================================================================
// FB_Valve — On/off valve control with feedback monitoring
// =============================================================================
FUNCTION_BLOCK "FB_Valve"
TITLE = 'On/Off Valve Control with Feedback and Timeout'
VERSION : 0.1

VAR_INPUT
  CmdOpen         : BOOL;       // Command to open the valve
  CmdClose        : BOOL;       // Command to close the valve
  CmdReset        : BOOL;       // Reset from fault state
  ManualOverride  : BOOL;       // Enable manual override mode
  ManualOutput    : BOOL;       // Manual solenoid output when override is active
  Interlock       : BOOL;       // Interlock OK (TRUE = safe to operate)
  FbkOpen         : BOOL;       // Open limit switch feedback
  FbkClosed       : BOOL;       // Closed limit switch feedback
  OpenTimeout     : TIME := T#10s;  // Max time to reach open position
  CloseTimeout    : TIME := T#10s;  // Max time to reach closed position
END_VAR

VAR_OUTPUT
  ValveOut        : BOOL;       // Solenoid output (TRUE = open)
  IsOpen          : BOOL;       // Valve is confirmed open
  IsClosed        : BOOL;       // Valve is confirmed closed
  Error           : BOOL;       // Fault active
  ErrorID         : INT;        // Error code
  Status          : "UDT_ValveData"; // Aggregated status for HMI
END_VAR

VAR
  State           : INT := 4;   // Start in Closed state (default safe)
  PrevState       : INT := -1;
  OpenTimer       : TON_TIME;   // Opening timeout timer
  CloseTimer      : TON_TIME;   // Closing timeout timer
  FeedbackCheck   : TON_TIME;   // Feedback contradiction debounce
  PrevFbkOpen     : BOOL;       // Previous open feedback for edge detection
  CycleCount      : DINT := 0;  // Total open/close cycles
  FbkDebounceTime : TIME := T#500ms; // Debounce time for contradictory feedbacks
END_VAR

VAR CONSTANT
  ST_IDLE         : INT := 0;
  ST_OPENING      : INT := 1;
  ST_OPEN         : INT := 2;
  ST_CLOSING      : INT := 3;
  ST_CLOSED       : INT := 4;
  ST_FAULT        : INT := 10;
  
  ERR_NONE           : INT := 0;
  ERR_OPEN_TIMEOUT   : INT := 1;
  ERR_CLOSE_TIMEOUT  : INT := 2;
  ERR_BOTH_FEEDBACKS : INT := 3;
  ERR_INTERLOCK      : INT := 4;
  ERR_UNKNOWN        : INT := 99;
END_VAR

BEGIN
  // ---- Entry action: reset timers on state change ----
  IF #State <> #PrevState THEN
    #OpenTimer(IN := FALSE, PT := T#0ms);
    #CloseTimer(IN := FALSE, PT := T#0ms);
    #PrevState := #State;
  END_IF;
  
  // ---- Manual override mode ----
  // When ManualOverride is TRUE, bypass the state machine entirely.
  // The solenoid output follows ManualOutput directly.
  IF #ManualOverride THEN
    #ValveOut := #ManualOutput;
    #IsOpen := #FbkOpen AND NOT #FbkClosed;
    #IsClosed := #FbkClosed AND NOT #FbkOpen;
    #Error := FALSE;
    #ErrorID := #ERR_NONE;
    
    // Update HMI status for manual mode
    #Status.State := #State;
    #Status.ManualActive := TRUE;
    #Status.Error := FALSE;
    #Status.ErrorID := #ERR_NONE;
    #Status.ValveOut := #ValveOut;
    #Status.CycleCount := #CycleCount;
    #Status.StateName := 'Manual';
    
    IF #FbkOpen AND NOT #FbkClosed THEN
      #Status.Position := 1;  // Open
    ELSIF #FbkClosed AND NOT #FbkOpen THEN
      #Status.Position := 2;  // Closed
    ELSIF NOT #FbkOpen AND NOT #FbkClosed THEN
      #Status.Position := 3;  // Intermediate
    ELSE
      #Status.Position := 0;  // Unknown (both feedbacks — abnormal)
    END_IF;
    
    RETURN;  // Skip state machine processing
  END_IF;
  
  // ---- Feedback contradiction check (both open AND closed simultaneously) ----
  #FeedbackCheck(IN := #FbkOpen AND #FbkClosed, PT := #FbkDebounceTime);
  IF #FeedbackCheck.Q AND #State <> #ST_FAULT THEN
    #State := #ST_FAULT;
    #ErrorID := #ERR_BOTH_FEEDBACKS;
  END_IF;
  
  // ---- Interlock check ----
  IF NOT #Interlock AND #State <> #ST_FAULT AND #State <> #ST_CLOSED AND #State <> #ST_CLOSING THEN
    // Lost interlock while valve is open or opening — force close
    #State := #ST_CLOSING;
  END_IF;
  
  // ---- Cycle counting: rising edge on FbkOpen ----
  IF #FbkOpen AND NOT #PrevFbkOpen THEN
    #CycleCount := #CycleCount + 1;
  END_IF;
  #PrevFbkOpen := #FbkOpen;
  
  // ---- State machine ----
  CASE #State OF
    0: // ST_IDLE — Valve position unknown after startup
      #ValveOut := FALSE;
      #Error := FALSE;
      #ErrorID := #ERR_NONE;
      #IsOpen := FALSE;
      #IsClosed := FALSE;
      // Transition based on actual feedback
      IF #FbkClosed AND NOT #FbkOpen THEN
        #State := #ST_CLOSED;
      ELSIF #FbkOpen AND NOT #FbkClosed THEN
        #State := #ST_OPEN;
      ELSIF #CmdClose OR NOT #Interlock THEN
        #State := #ST_CLOSING;
      ELSIF #CmdOpen AND #Interlock THEN
        #State := #ST_OPENING;
      END_IF;
    
    1: // ST_OPENING — Solenoid energized, waiting for open feedback
      #ValveOut := TRUE;
      #IsOpen := FALSE;
      #IsClosed := FALSE;
      #Error := FALSE;
      #ErrorID := #ERR_NONE;
      
      #OpenTimer(IN := TRUE, PT := #OpenTimeout);
      
      IF #FbkOpen AND NOT #FbkClosed THEN
        // Valve reached open position
        #State := #ST_OPEN;
      END_IF;
      
      IF #OpenTimer.Q THEN
        // Timeout — valve did not reach open position
        #State := #ST_FAULT;
        #ErrorID := #ERR_OPEN_TIMEOUT;
      END_IF;
      
      IF #CmdClose THEN
        #State := #ST_CLOSING;
      END_IF;
      
      IF NOT #Interlock THEN
        #State := #ST_CLOSING;
      END_IF;
    
    2: // ST_OPEN — Valve is confirmed fully open
      #ValveOut := TRUE;
      #IsOpen := TRUE;
      #IsClosed := FALSE;
      #Error := FALSE;
      #ErrorID := #ERR_NONE;
      
      IF #CmdClose OR NOT #Interlock THEN
        #State := #ST_CLOSING;
      END_IF;
      
      // Monitor: if open feedback is lost while we expect the valve to be open
      IF NOT #FbkOpen THEN
        #State := #ST_FAULT;
        #ErrorID := #ERR_OPEN_TIMEOUT;
      END_IF;
    
    3: // ST_CLOSING — Solenoid de-energized, waiting for closed feedback
      #ValveOut := FALSE;
      #IsOpen := FALSE;
      #IsClosed := FALSE;
      #Error := FALSE;
      #ErrorID := #ERR_NONE;
      
      #CloseTimer(IN := TRUE, PT := #CloseTimeout);
      
      IF #FbkClosed AND NOT #FbkOpen THEN
        // Valve reached closed position
        #State := #ST_CLOSED;
      END_IF;
      
      IF #CloseTimer.Q THEN
        // Timeout — valve did not reach closed position
        #State := #ST_FAULT;
        #ErrorID := #ERR_CLOSE_TIMEOUT;
      END_IF;
      
      // Allow re-opening if interlock is OK and operator commands open
      IF #CmdOpen AND #Interlock THEN
        #State := #ST_OPENING;
      END_IF;
    
    4: // ST_CLOSED — Valve is confirmed fully closed
      #ValveOut := FALSE;
      #IsOpen := FALSE;
      #IsClosed := TRUE;
      #Error := FALSE;
      #ErrorID := #ERR_NONE;
      
      IF #CmdOpen AND #Interlock THEN
        #State := #ST_OPENING;
      END_IF;
      
      // Monitor: if closed feedback is lost unexpectedly
      IF NOT #FbkClosed THEN
        #State := #ST_FAULT;
        #ErrorID := #ERR_CLOSE_TIMEOUT;
      END_IF;
    
    10: // ST_FAULT — Valve in error state, solenoid de-energized (safe)
      #ValveOut := FALSE;
      #IsOpen := FALSE;
      #IsClosed := FALSE;
      #Error := TRUE;
      // ErrorID is preserved from the fault that caused entry
      
      IF #CmdReset AND NOT #CmdOpen AND NOT #CmdClose THEN
        #ErrorID := #ERR_NONE;
        // After reset, determine starting state from feedback
        IF #FbkClosed AND NOT #FbkOpen THEN
          #State := #ST_CLOSED;
        ELSIF #FbkOpen AND NOT #FbkClosed THEN
          #State := #ST_OPEN;
        ELSE
          #State := #ST_IDLE;
        END_IF;
      END_IF;
    
    ELSE
      // Unknown state — go to fault
      #State := #ST_FAULT;
      #ErrorID := #ERR_UNKNOWN;
  END_CASE;
  
  // ---- Update HMI status structure ----
  #Status.State := #State;
  #Status.Error := #Error;
  #Status.ErrorID := #ErrorID;
  #Status.ManualActive := FALSE;
  #Status.ValveOut := #ValveOut;
  #Status.CycleCount := #CycleCount;
  
  // Determine position from feedbacks
  IF #FbkOpen AND NOT #FbkClosed THEN
    #Status.Position := 1;  // Open
  ELSIF #FbkClosed AND NOT #FbkOpen THEN
    #Status.Position := 2;  // Closed
  ELSIF NOT #FbkOpen AND NOT #FbkClosed THEN
    #Status.Position := 3;  // Intermediate (travelling)
  ELSE
    #Status.Position := 0;  // Unknown (contradictory)
  END_IF;
  
  CASE #State OF
    0:  #Status.StateName := 'Idle';
    1:  #Status.StateName := 'Opening';
    2:  #Status.StateName := 'Open';
    3:  #Status.StateName := 'Closing';
    4:  #Status.StateName := 'Closed';
    10: #Status.StateName := 'Fault';
    ELSE #Status.StateName := 'Unknown';
  END_CASE;
END_FUNCTION_BLOCK

// =============================================================================
// DB_Valve1 — Instance DB for valve 1
// =============================================================================
DATA_BLOCK "DB_Valve1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Valve"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_Valve1"(
    CmdOpen        := %I0.0,
    CmdClose       := %I0.1,
    CmdReset       := %I0.2,
    ManualOverride := %I0.3,
    ManualOutput   := %I0.4,
    Interlock      := %I0.5,
    FbkOpen        := %I1.0,
    FbkClosed      := %I1.1,
    OpenTimeout    := T#10s,
    CloseTimeout   := T#10s,
    ValveOut       => %Q0.0
  );
END_ORGANIZATION_BLOCK
```

## Test Procedure

### 1. Deploy
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

### 2. Verify via S7 Runtime
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Read valve state
S7ReadVariable(address="DB1.DBW0")     // State (INT): 0=Idle, 1=Opening, 2=Open, 3=Closing, 4=Closed, 10=Fault
S7ReadVariable(address="DB1.DBX4.0")   // Error (BOOL)
S7ReadVariable(address="DB1.DBW6")     // ErrorID (INT): 0=None, 1=OpenTimeout, 2=CloseTimeout, 3=BothFeedbacks
S7ReadVariable(address="DB1.DBX8.0")   // ValveOut (BOOL)
S7ReadVariable(address="DB1.DBX8.1")   // IsOpen (BOOL)
S7ReadVariable(address="DB1.DBX8.2")   // IsClosed (BOOL)

S7Disconnect()
```

### 3. Functional Tests
1. **Normal open**: Set CmdOpen=TRUE with Interlock=TRUE, FbkClosed=TRUE -> State goes 4->1, ValveOut=TRUE. Then set FbkOpen=TRUE, FbkClosed=FALSE -> State goes 1->2, IsOpen=TRUE
2. **Normal close**: In Open state, set CmdClose=TRUE -> State goes 2->3, ValveOut=FALSE. Then set FbkClosed=TRUE, FbkOpen=FALSE -> State goes 3->4, IsClosed=TRUE
3. **Open timeout**: Set CmdOpen=TRUE but never provide FbkOpen -> after 10s, State=10, ErrorID=1
4. **Close timeout**: Set CmdClose=TRUE but never provide FbkClosed -> after 10s, State=10, ErrorID=2
5. **Both feedbacks fault**: Set FbkOpen=TRUE and FbkClosed=TRUE simultaneously -> after 500ms debounce, State=10, ErrorID=3
6. **Interlock trip**: While Open, clear Interlock -> valve starts closing (State=3)
7. **Manual override**: Set ManualOverride=TRUE -> ValveOut follows ManualOutput directly, state machine is bypassed
8. **Fault reset**: In Fault state, set CmdReset=TRUE -> returns to Closed/Open/Idle based on current feedback
9. **Cycle count**: Each full open operation (rising edge on FbkOpen) increments CycleCount

## Variations

### S7-1200 Variant
The code is fully compatible with S7-1200. No S7-1500-specific features are used.
If using S7-1200 firmware < V4.0, replace `TON_TIME` with `TON` (IEC timer).

### Multiple Valves
Create additional instance DBs for each valve:
```scl
DATA_BLOCK "DB_Valve2"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Valve"
BEGIN
END_DATA_BLOCK
```
Then call each in OB1 with different I/O mappings. The FB is fully reentrant — each instance maintains its own state, timers, and cycle count.

### Modulating Valve with Analog Setpoint
For proportional control valves (e.g., globe valve with 4-20mA positioner), replace the solenoid output with an analog setpoint. Key changes:
- Replace `ValveOut : BOOL` with `AnalogOut : REAL` (0.0 to 100.0%)
- Replace discrete feedbacks with an analog position feedback `AnalogFbk : REAL`
- Use a position tolerance band for "at setpoint" detection:
```scl
// Inside the FB, use epsilon comparison for REAL position
VAR_INPUT
  AnalogSetpoint : REAL;       // Desired position 0.0-100.0%
  AnalogFbk      : REAL;       // Actual position feedback 0.0-100.0%
  PosTolerance   : REAL := 2.0; // Position tolerance band in %
END_VAR

// Position reached check (REAL comparison with epsilon)
IF ABS(#AnalogFbk - #AnalogSetpoint) < #PosTolerance THEN
  // Valve is at target position
  #AtSetpoint := TRUE;
END_IF;
```
Note: The modulating variant adds complexity for ramp control and analog scaling. Consider using the `CONT_V` system FB for integrated valve control on S7-1500.

### Fail-Safe Valve (Spring Return)
For fail-safe configurations where the valve returns to a safe position (typically closed) on loss of air or power:
- Invert the solenoid logic: `ValveOut := TRUE` means the valve is held away from its fail-safe position
- On fault or interlock trip, simply de-energize (`ValveOut := FALSE`) — the spring/air returns the valve
- Adjust timeout expectations: spring-return closing is typically faster than powered closing
