# HMI Interface

## Frontmatter
- **Tags**: hmi, interface, screen, alarm, data-exchange, visualization
- **CPU**: Both
- **Difficulty**: Intermediate

## Requirements
Standard HMI data exchange pattern for Siemens Comfort/Unified panels. The PLC provides
a single "HMI interface DB" containing all data the HMI reads and writes. This pattern
enforces a clean separation: the PLC never reads HMI-internal state, and the HMI never
accesses internal PLC variables directly.

Key features:
- **Screen navigation**: PLC knows which screen the HMI is showing and can request screen changes
- **Operating mode**: Auto / Manual / Service with transition validation (only authorized transitions allowed)
- **Command handshake**: HMI writes a command request, PLC processes and acknowledges, HMI clears the request — prevents race conditions across scan cycles
- **Heartbeat**: PLC toggles a bit every second so the HMI can detect communication loss
- **Alarm interface**: PLC publishes active alarms as a packed WORD; HMI reads bits for alarm indicators

### HMI Data Flow
| Direction | Section | Description |
|-----------|---------|-------------|
| PLC -> HMI | Status | Machine state, temperatures, counts, alarm bits |
| HMI -> PLC | Commands | Operator commands, setpoint changes, mode requests |
| Bidirectional | Parameters | Recipe values, configuration — both sides read, PLC validates writes |

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| UDT_HmiCommand | UDT | Command handshake structure | CmdRequest, CmdID, CmdParam, CmdAck, CmdDone, CmdError |
| UDT_HmiStatus | UDT | Machine status for HMI display | Mode, State, Alarms, Temperatures, Counters, Heartbeat |
| DB_HmiInterface | DB | Global data block (non-optimized) for HMI tag binding | Status, Commands, Parameters sections |
| FB_HmiHandler | FB | Processes HMI commands, updates status, validates mode transitions | IN: process data; INOUT: HMI DB reference; OUT: Error, ErrorID |
| DB_HmiHandler | DB | Instance DB for FB_HmiHandler | Instance of FB_HmiHandler |
| Main (OB1) | OB | Cyclic call to FB_HmiHandler | Passes process signals and HMI DB |

## SCL Code

```scl
// =============================================================================
// UDT_HmiCommand — Command handshake structure
// =============================================================================
// Handshake protocol:
//   1. HMI sets CmdRequest := TRUE and CmdID := <command number>
//   2. PLC detects rising edge on CmdRequest, processes the command
//   3. PLC sets CmdAck := TRUE (and CmdDone or CmdError)
//   4. HMI sees CmdAck, clears CmdRequest := FALSE
//   5. PLC sees CmdRequest = FALSE, clears CmdAck := FALSE
// =============================================================================
TYPE "UDT_HmiCommand"
VERSION : 0.1
  STRUCT
    // HMI -> PLC (operator writes these)
    CmdRequest    : BOOL;       // TRUE = HMI is requesting a command
    CmdID         : INT;        // Command identifier (1=Start, 2=Stop, 3=Reset, 4=ModeChange, 5=SetParam)
    CmdParam1     : REAL;       // Generic parameter 1 (meaning depends on CmdID)
    CmdParam2     : REAL;       // Generic parameter 2
    CmdParamInt   : INT;        // Integer parameter (e.g., requested mode number)
    
    // PLC -> HMI (PLC writes these)
    CmdAck        : BOOL;       // TRUE = PLC has received and processed the command
    CmdDone       : BOOL;       // TRUE = command completed successfully
    CmdError      : BOOL;       // TRUE = command failed
    CmdErrorID    : INT;        // Error code for the failed command (0=none)
    CmdBusy       : BOOL;       // TRUE = command is being processed (multi-cycle)
  END_STRUCT;
END_TYPE

// =============================================================================
// UDT_HmiStatus — Machine status structure for HMI display
// =============================================================================
TYPE "UDT_HmiStatus"
VERSION : 0.1
  STRUCT
    // Operating mode
    Mode          : INT;        // 0=Auto, 1=Manual, 2=Service
    ModeName      : STRING[16]; // Current mode as text
    ModeChangeOk  : BOOL;      // TRUE = mode transition is allowed right now
    
    // Machine state
    State         : INT;        // Application-specific state number
    StateName     : STRING[20]; // Current state as text for display
    Running       : BOOL;       // Machine is in active production
    Ready         : BOOL;       // Machine is ready to start
    Stopped       : BOOL;       // Machine is stopped (safe state)
    
    // Process values (PLC -> HMI, read-only for operator)
    Temperature1  : REAL;       // Process temperature 1 [deg C]
    Temperature2  : REAL;       // Process temperature 2 [deg C]
    Pressure      : REAL;       // Process pressure [bar]
    Speed         : REAL;       // Line speed [m/min]
    
    // Counters
    ProductCount  : DINT;       // Total product count
    GoodCount     : DINT;       // Good products
    RejectCount   : DINT;       // Rejected products
    
    // Alarms (packed bits — each bit = one alarm)
    AlarmWord1    : WORD;       // Alarms 0-15
    AlarmWord2    : WORD;       // Alarms 16-31
    AlarmActive   : BOOL;       // TRUE if any alarm is active
    AlarmCount    : INT;        // Number of active alarms
    
    // Heartbeat
    Heartbeat     : BOOL;       // Toggles every ~1 second — HMI monitors this
    HeartbeatCount : DINT;      // Increments every toggle for diagnostics
    
    // Communication
    PlcTime       : DATE_AND_TIME; // Current PLC clock
    ScanTimeMs    : REAL;       // Last scan cycle time in ms
  END_STRUCT;
END_TYPE

// =============================================================================
// DB_HmiInterface — Global HMI data block (NON-OPTIMIZED for HMI tag binding)
// =============================================================================
// This DB MUST use S7_Optimized_Access := 'FALSE' so that HMI tags can be
// bound via absolute addresses. Optimized DBs hide the address layout and
// prevent direct HMI tag mapping in TIA Portal Comfort/Unified panels.
// =============================================================================
DATA_BLOCK "DB_HmiInterface"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    // =====================================================
    // Section 1: STATUS (PLC -> HMI, read-only for HMI)
    // =====================================================
    Status        : "UDT_HmiStatus";
    
    // =====================================================
    // Section 2: COMMANDS (HMI -> PLC, operator actions)
    // =====================================================
    Cmd           : "UDT_HmiCommand";
    
    // =====================================================
    // Section 3: PARAMETERS (bidirectional)
    // HMI writes requested values, PLC validates and applies
    // =====================================================
    // Screen navigation
    ActiveScreen  : INT := 1;   // Current screen ID reported by HMI
    RequestScreen : INT;        // PLC can request HMI to navigate to this screen
    ScreenChangeReq : BOOL;     // PLC sets TRUE to request screen change
    
    // Setpoints (operator-adjustable via HMI)
    SP_Temperature1 : REAL := 25.0;  // Temperature 1 setpoint [deg C]
    SP_Temperature2 : REAL := 25.0;  // Temperature 2 setpoint [deg C]
    SP_Pressure     : REAL := 1.0;   // Pressure setpoint [bar]
    SP_Speed        : REAL := 10.0;  // Speed setpoint [m/min]
    
    // Limits (PLC enforces these; HMI displays for reference)
    Lim_TempMin     : REAL := 0.0;
    Lim_TempMax     : REAL := 200.0;
    Lim_PressMin    : REAL := 0.0;
    Lim_PressMax    : REAL := 10.0;
    Lim_SpeedMin    : REAL := 0.0;
    Lim_SpeedMax    : REAL := 60.0;
    
    // Recipe identifier
    RecipeID        : INT;       // Active recipe number
    RecipeName      : STRING[32] := 'Default';
  END_STRUCT;
BEGIN
END_DATA_BLOCK

// =============================================================================
// FB_HmiHandler — Processes HMI commands and updates status
// =============================================================================
FUNCTION_BLOCK "FB_HmiHandler"
TITLE = 'HMI Command Handler and Status Updater'
VERSION : 0.1

VAR_INPUT
  // Process values from other FBs (PLC internal -> HMI)
  ActTemp1        : REAL;       // Actual temperature 1
  ActTemp2        : REAL;       // Actual temperature 2
  ActPressure     : REAL;       // Actual pressure
  ActSpeed        : REAL;       // Actual speed
  ProductCount    : DINT;       // Total products
  GoodCount       : DINT;       // Good products
  RejectCount     : DINT;       // Rejected products
  MachineState    : INT;        // Current state from main state machine
  MachineStateName : STRING[20]; // State name text
  MachineRunning  : BOOL;       // Machine running flag
  MachineReady    : BOOL;       // Machine ready flag
  MachineStopped  : BOOL;       // Machine stopped flag
  AlarmWord1      : WORD;       // Alarm bits 0-15
  AlarmWord2      : WORD;       // Alarm bits 16-31
  ScanTimeMs      : REAL;       // Cycle time from OB1 info
END_VAR

VAR_OUTPUT
  // Outputs to main program (HMI commands decoded)
  CmdStart        : BOOL;       // Operator pressed Start
  CmdStop         : BOOL;       // Operator pressed Stop
  CmdReset        : BOOL;       // Operator pressed Reset
  ModeRequested   : INT;        // Requested mode (0=Auto, 1=Manual, 2=Service)
  ModeChanged     : BOOL;       // Pulse: mode has been changed
  SP_Temp1        : REAL;       // Validated temperature 1 setpoint
  SP_Temp2        : REAL;       // Validated temperature 2 setpoint
  SP_Press        : REAL;       // Validated pressure setpoint
  SP_Speed        : REAL;       // Validated speed setpoint
  Error           : BOOL;       // Handler error
  ErrorID         : INT;        // Handler error code
END_VAR

VAR_IN_OUT
  HmiDb           : "DB_HmiInterface"; // Reference to the HMI interface DB
END_VAR

VAR
  // Internal state
  CurrentMode     : INT := 0;   // 0=Auto, 1=Manual, 2=Service
  PrevCmdRequest  : BOOL;       // Previous CmdRequest for edge detection
  HeartbeatTimer  : TON_TIME;   // 1-second heartbeat toggle timer
  HeartbeatState  : BOOL;       // Current heartbeat output
  HeartbeatCount  : DINT;       // Heartbeat toggle counter
  CmdProcessed    : BOOL;       // Command was processed this cycle
  
  // Mode change validation
  PrevMode        : INT := -1;  // Previous mode for change detection
  
  // Alarm counting
  TempAlarmWord   : WORD;
  AlarmBitIndex   : INT;
  TempAlarmCount  : INT;
END_VAR

VAR CONSTANT
  // Command IDs
  CMD_START       : INT := 1;
  CMD_STOP        : INT := 2;
  CMD_RESET       : INT := 3;
  CMD_MODE_CHANGE : INT := 4;
  CMD_SET_PARAM   : INT := 5;
  
  // Mode constants
  MODE_AUTO       : INT := 0;
  MODE_MANUAL     : INT := 1;
  MODE_SERVICE    : INT := 2;
  
  // Error codes
  ERR_NONE            : INT := 0;
  ERR_UNKNOWN_CMD     : INT := 1;
  ERR_INVALID_MODE    : INT := 2;
  ERR_MODE_NOT_ALLOWED : INT := 3;
  ERR_PARAM_OUT_RANGE : INT := 4;
  ERR_CMD_WHILE_BUSY  : INT := 5;
END_VAR

BEGIN
  // Reset outputs each cycle
  #CmdStart := FALSE;
  #CmdStop := FALSE;
  #CmdReset := FALSE;
  #ModeChanged := FALSE;
  #Error := FALSE;
  #ErrorID := #ERR_NONE;
  #CmdProcessed := FALSE;
  
  // ========================================================================
  // 1. HEARTBEAT — toggle every ~1 second so HMI can detect PLC is alive
  // ========================================================================
  #HeartbeatTimer(IN := NOT #HeartbeatTimer.Q, PT := T#1s);
  IF #HeartbeatTimer.Q THEN
    #HeartbeatState := NOT #HeartbeatState;
    #HeartbeatCount := #HeartbeatCount + 1;
  END_IF;
  
  // ========================================================================
  // 2. COMMAND HANDSHAKE — process HMI commands
  // ========================================================================
  // Detect rising edge of CmdRequest (HMI just sent a new command)
  IF #HmiDb.Cmd.CmdRequest AND NOT #PrevCmdRequest THEN
    // New command received — process it
    #HmiDb.Cmd.CmdAck := FALSE;
    #HmiDb.Cmd.CmdDone := FALSE;
    #HmiDb.Cmd.CmdError := FALSE;
    #HmiDb.Cmd.CmdErrorID := #ERR_NONE;
    #HmiDb.Cmd.CmdBusy := TRUE;
    
    CASE #HmiDb.Cmd.CmdID OF
      1: // CMD_START
        #CmdStart := TRUE;
        #HmiDb.Cmd.CmdDone := TRUE;
        #CmdProcessed := TRUE;
      
      2: // CMD_STOP
        #CmdStop := TRUE;
        #HmiDb.Cmd.CmdDone := TRUE;
        #CmdProcessed := TRUE;
      
      3: // CMD_RESET
        #CmdReset := TRUE;
        #HmiDb.Cmd.CmdDone := TRUE;
        #CmdProcessed := TRUE;
      
      4: // CMD_MODE_CHANGE
        // Validate the requested mode transition
        IF #HmiDb.Cmd.CmdParamInt >= #MODE_AUTO AND #HmiDb.Cmd.CmdParamInt <= #MODE_SERVICE THEN
          // Validate transition rules:
          //   Auto -> Manual: allowed only when machine is stopped
          //   Manual -> Auto: always allowed
          //   Service -> Auto/Manual: always allowed
          //   Auto/Manual -> Service: allowed only when machine is stopped
          IF #HmiDb.Cmd.CmdParamInt = #CurrentMode THEN
            // Same mode — nothing to do, but not an error
            #HmiDb.Cmd.CmdDone := TRUE;
            #CmdProcessed := TRUE;
          ELSIF (#CurrentMode = #MODE_AUTO AND #HmiDb.Cmd.CmdParamInt = #MODE_MANUAL AND NOT #MachineStopped) THEN
            // Auto -> Manual requires machine stopped
            #HmiDb.Cmd.CmdError := TRUE;
            #HmiDb.Cmd.CmdErrorID := #ERR_MODE_NOT_ALLOWED;
            #Error := TRUE;
            #ErrorID := #ERR_MODE_NOT_ALLOWED;
            #CmdProcessed := TRUE;
          ELSIF (#HmiDb.Cmd.CmdParamInt = #MODE_SERVICE AND NOT #MachineStopped) THEN
            // Entering Service mode requires machine stopped
            #HmiDb.Cmd.CmdError := TRUE;
            #HmiDb.Cmd.CmdErrorID := #ERR_MODE_NOT_ALLOWED;
            #Error := TRUE;
            #ErrorID := #ERR_MODE_NOT_ALLOWED;
            #CmdProcessed := TRUE;
          ELSE
            // Transition is valid — apply it
            #CurrentMode := #HmiDb.Cmd.CmdParamInt;
            #ModeRequested := #CurrentMode;
            #ModeChanged := TRUE;
            #HmiDb.Cmd.CmdDone := TRUE;
            #CmdProcessed := TRUE;
          END_IF;
        ELSE
          // Invalid mode number
          #HmiDb.Cmd.CmdError := TRUE;
          #HmiDb.Cmd.CmdErrorID := #ERR_INVALID_MODE;
          #Error := TRUE;
          #ErrorID := #ERR_INVALID_MODE;
          #CmdProcessed := TRUE;
        END_IF;
      
      5: // CMD_SET_PARAM — validate and apply setpoint changes
        // CmdParam1 = new value, CmdParamInt = parameter ID
        //   ParamID: 1=Temp1 SP, 2=Temp2 SP, 3=Pressure SP, 4=Speed SP
        CASE #HmiDb.Cmd.CmdParamInt OF
          1: // Temperature 1 setpoint
            IF #HmiDb.Cmd.CmdParam1 >= #HmiDb.Lim_TempMin AND #HmiDb.Cmd.CmdParam1 <= #HmiDb.Lim_TempMax THEN
              #HmiDb.SP_Temperature1 := #HmiDb.Cmd.CmdParam1;
              #HmiDb.Cmd.CmdDone := TRUE;
            ELSE
              #HmiDb.Cmd.CmdError := TRUE;
              #HmiDb.Cmd.CmdErrorID := #ERR_PARAM_OUT_RANGE;
              #Error := TRUE;
              #ErrorID := #ERR_PARAM_OUT_RANGE;
            END_IF;
            #CmdProcessed := TRUE;
          
          2: // Temperature 2 setpoint
            IF #HmiDb.Cmd.CmdParam1 >= #HmiDb.Lim_TempMin AND #HmiDb.Cmd.CmdParam1 <= #HmiDb.Lim_TempMax THEN
              #HmiDb.SP_Temperature2 := #HmiDb.Cmd.CmdParam1;
              #HmiDb.Cmd.CmdDone := TRUE;
            ELSE
              #HmiDb.Cmd.CmdError := TRUE;
              #HmiDb.Cmd.CmdErrorID := #ERR_PARAM_OUT_RANGE;
              #Error := TRUE;
              #ErrorID := #ERR_PARAM_OUT_RANGE;
            END_IF;
            #CmdProcessed := TRUE;
          
          3: // Pressure setpoint
            IF #HmiDb.Cmd.CmdParam1 >= #HmiDb.Lim_PressMin AND #HmiDb.Cmd.CmdParam1 <= #HmiDb.Lim_PressMax THEN
              #HmiDb.SP_Pressure := #HmiDb.Cmd.CmdParam1;
              #HmiDb.Cmd.CmdDone := TRUE;
            ELSE
              #HmiDb.Cmd.CmdError := TRUE;
              #HmiDb.Cmd.CmdErrorID := #ERR_PARAM_OUT_RANGE;
              #Error := TRUE;
              #ErrorID := #ERR_PARAM_OUT_RANGE;
            END_IF;
            #CmdProcessed := TRUE;
          
          4: // Speed setpoint
            IF #HmiDb.Cmd.CmdParam1 >= #HmiDb.Lim_SpeedMin AND #HmiDb.Cmd.CmdParam1 <= #HmiDb.Lim_SpeedMax THEN
              #HmiDb.SP_Speed := #HmiDb.Cmd.CmdParam1;
              #HmiDb.Cmd.CmdDone := TRUE;
            ELSE
              #HmiDb.Cmd.CmdError := TRUE;
              #HmiDb.Cmd.CmdErrorID := #ERR_PARAM_OUT_RANGE;
              #Error := TRUE;
              #ErrorID := #ERR_PARAM_OUT_RANGE;
            END_IF;
            #CmdProcessed := TRUE;
          
          ELSE
            // Unknown parameter ID
            #HmiDb.Cmd.CmdError := TRUE;
            #HmiDb.Cmd.CmdErrorID := #ERR_UNKNOWN_CMD;
            #Error := TRUE;
            #ErrorID := #ERR_UNKNOWN_CMD;
            #CmdProcessed := TRUE;
        END_CASE;
      
      ELSE
        // Unknown command ID
        #HmiDb.Cmd.CmdError := TRUE;
        #HmiDb.Cmd.CmdErrorID := #ERR_UNKNOWN_CMD;
        #Error := TRUE;
        #ErrorID := #ERR_UNKNOWN_CMD;
        #CmdProcessed := TRUE;
    END_CASE;
    
    // Mark command as acknowledged
    IF #CmdProcessed THEN
      #HmiDb.Cmd.CmdAck := TRUE;
      #HmiDb.Cmd.CmdBusy := FALSE;
    END_IF;
  END_IF;
  
  // Handshake phase 2: HMI has seen the ACK and cleared CmdRequest
  // PLC now clears the ACK and done/error flags
  IF NOT #HmiDb.Cmd.CmdRequest AND #PrevCmdRequest THEN
    #HmiDb.Cmd.CmdAck := FALSE;
    #HmiDb.Cmd.CmdDone := FALSE;
    #HmiDb.Cmd.CmdError := FALSE;
    #HmiDb.Cmd.CmdErrorID := #ERR_NONE;
    #HmiDb.Cmd.CmdBusy := FALSE;
  END_IF;
  
  // Store previous state for edge detection
  #PrevCmdRequest := #HmiDb.Cmd.CmdRequest;
  
  // ========================================================================
  // 3. UPDATE STATUS SECTION — copy process data into HMI DB
  // ========================================================================
  #HmiDb.Status.Mode := #CurrentMode;
  
  CASE #CurrentMode OF
    0: #HmiDb.Status.ModeName := 'Auto';
    1: #HmiDb.Status.ModeName := 'Manual';
    2: #HmiDb.Status.ModeName := 'Service';
    ELSE #HmiDb.Status.ModeName := 'Unknown';
  END_CASE;
  
  // Mode change allowed only when machine is stopped
  #HmiDb.Status.ModeChangeOk := #MachineStopped;
  
  // Machine state
  #HmiDb.Status.State := #MachineState;
  #HmiDb.Status.StateName := #MachineStateName;
  #HmiDb.Status.Running := #MachineRunning;
  #HmiDb.Status.Ready := #MachineReady;
  #HmiDb.Status.Stopped := #MachineStopped;
  
  // Process values
  #HmiDb.Status.Temperature1 := #ActTemp1;
  #HmiDb.Status.Temperature2 := #ActTemp2;
  #HmiDb.Status.Pressure := #ActPressure;
  #HmiDb.Status.Speed := #ActSpeed;
  
  // Counters
  #HmiDb.Status.ProductCount := #ProductCount;
  #HmiDb.Status.GoodCount := #GoodCount;
  #HmiDb.Status.RejectCount := #RejectCount;
  
  // Alarms
  #HmiDb.Status.AlarmWord1 := #AlarmWord1;
  #HmiDb.Status.AlarmWord2 := #AlarmWord2;
  #HmiDb.Status.AlarmActive := (#AlarmWord1 <> 16#0000) OR (#AlarmWord2 <> 16#0000);
  
  // Count active alarm bits (iterate bits in both alarm words)
  #TempAlarmCount := 0;
  #TempAlarmWord := #AlarmWord1;
  FOR #AlarmBitIndex := 0 TO 15 DO
    IF #TempAlarmWord.%X0 THEN
      #TempAlarmCount := #TempAlarmCount + 1;
    END_IF;
    #TempAlarmWord := SHR(IN := #TempAlarmWord, N := 1);
  END_FOR;
  #TempAlarmWord := #AlarmWord2;
  FOR #AlarmBitIndex := 0 TO 15 DO
    IF #TempAlarmWord.%X0 THEN
      #TempAlarmCount := #TempAlarmCount + 1;
    END_IF;
    #TempAlarmWord := SHR(IN := #TempAlarmWord, N := 1);
  END_FOR;
  #HmiDb.Status.AlarmCount := #TempAlarmCount;
  
  // Heartbeat
  #HmiDb.Status.Heartbeat := #HeartbeatState;
  #HmiDb.Status.HeartbeatCount := #HeartbeatCount;
  
  // Diagnostics
  #HmiDb.Status.ScanTimeMs := #ScanTimeMs;
  
  // ========================================================================
  // 4. OUTPUT VALIDATED SETPOINTS — always pass current DB values to caller
  // ========================================================================
  #SP_Temp1 := #HmiDb.SP_Temperature1;
  #SP_Temp2 := #HmiDb.SP_Temperature2;
  #SP_Press := #HmiDb.SP_Pressure;
  #SP_Speed := #HmiDb.SP_Speed;
  #ModeRequested := #CurrentMode;
  
  // ========================================================================
  // 5. SCREEN CHANGE REQUEST — clear after HMI has navigated
  // ========================================================================
  // If PLC requested a screen change and HMI has navigated (ActiveScreen matches),
  // clear the request flag
  IF #HmiDb.ScreenChangeReq AND (#HmiDb.ActiveScreen = #HmiDb.RequestScreen) THEN
    #HmiDb.ScreenChangeReq := FALSE;
  END_IF;
  
END_FUNCTION_BLOCK

// =============================================================================
// DB_HmiHandler — Instance DB for FB_HmiHandler
// =============================================================================
DATA_BLOCK "DB_HmiHandler"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_HmiHandler"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  tempInt : INT;
END_VAR
BEGIN
  // Call HMI handler — connect process data to HMI interface DB
  // In a real application, these inputs come from other FBs (motor control,
  // PID loops, sensor scaling, etc.). Here we use placeholder values.
  "DB_HmiHandler"(
    ActTemp1         := 42.5,
    ActTemp2         := 38.1,
    ActPressure      := 3.2,
    ActSpeed         := 15.0,
    ProductCount     := 1234,
    GoodCount        := 1200,
    RejectCount      := 34,
    MachineState     := 0,
    MachineStateName := 'Idle',
    MachineRunning   := FALSE,
    MachineReady     := TRUE,
    MachineStopped   := TRUE,
    AlarmWord1       := W#16#0000,
    AlarmWord2       := W#16#0000,
    ScanTimeMs       := 2.0,
    HmiDb            := "DB_HmiInterface"
  );
END_ORGANIZATION_BLOCK
```

## Test Procedure

### 1. Deploy
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="hmi_interface", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="hmi_interface")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

### 2. Verify via S7 Runtime
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Read status section from DB_HmiInterface
S7ReadVariable(address="DB1.DBW0")      // Status.Mode (INT): 0=Auto, 1=Manual, 2=Service
S7ReadVariable(address="DB1.DBX34.0")   // Status.Running (BOOL)
S7ReadVariable(address="DB1.DBX34.1")   // Status.Ready (BOOL)
S7ReadVariable(address="DB1.DBX34.2")   // Status.Stopped (BOOL)
S7ReadVariable(address="DB1.DBD36")     // Status.Temperature1 (REAL)
S7ReadVariable(address="DB1.DBD40")     // Status.Temperature2 (REAL)
S7ReadVariable(address="DB1.DBD44")     // Status.Pressure (REAL)
S7ReadVariable(address="DB1.DBW72")     // Status.AlarmWord1 (WORD)
S7ReadVariable(address="DB1.DBX76.0")   // Status.AlarmActive (BOOL)
S7ReadVariable(address="DB1.DBX78.0")   // Status.Heartbeat (BOOL) — should toggle

// Read command section
S7ReadVariable(address="DB1.DBX84.0")   // Cmd.CmdRequest (BOOL)
S7ReadVariable(address="DB1.DBX84.1")   // Cmd.CmdAck (BOOL)

S7Disconnect()
```

### 3. Functional Tests

1. **Heartbeat monitoring**: Read `Status.Heartbeat` twice with ~2 second gap. The value must toggle, confirming PLC is running and updating the HMI DB.

2. **Command handshake — Start**:
   - Write `Cmd.CmdRequest := TRUE` and `Cmd.CmdID := 1` (Start) via `S7WriteVariable`
   - Read `Cmd.CmdAck` — must become TRUE within one scan cycle
   - Read `Cmd.CmdDone` — must be TRUE (Start accepted)
   - Write `Cmd.CmdRequest := FALSE` (HMI clears request)
   - Read `Cmd.CmdAck` — must become FALSE (PLC clears handshake)

3. **Command handshake — Mode change to Manual (valid)**:
   - Ensure machine is stopped (`Status.Stopped = TRUE`)
   - Write `Cmd.CmdID := 4`, `Cmd.CmdParamInt := 1` (Manual), `Cmd.CmdRequest := TRUE`
   - Read `Cmd.CmdDone` — must be TRUE
   - Read `Status.Mode` — must be 1 (Manual)
   - Clear `Cmd.CmdRequest`

4. **Mode change rejected (machine running)**:
   - Set machine running in OB1 (MachineRunning := TRUE, MachineStopped := FALSE)
   - Attempt mode change Auto -> Service: `CmdID := 4`, `CmdParamInt := 2`
   - Read `Cmd.CmdError` — must be TRUE
   - Read `Cmd.CmdErrorID` — must be 3 (ERR_MODE_NOT_ALLOWED)

5. **Setpoint validation (in range)**:
   - Write `Cmd.CmdID := 5`, `Cmd.CmdParamInt := 1` (Temp1 SP), `Cmd.CmdParam1 := 75.0`
   - `Cmd.CmdRequest := TRUE`
   - Read `Cmd.CmdDone` — must be TRUE
   - Read `SP_Temperature1` from Parameters section — must be 75.0

6. **Setpoint validation (out of range)**:
   - Write `Cmd.CmdID := 5`, `Cmd.CmdParamInt := 1` (Temp1 SP), `Cmd.CmdParam1 := 999.0`
   - `Cmd.CmdRequest := TRUE`
   - Read `Cmd.CmdError` — must be TRUE
   - Read `Cmd.CmdErrorID` — must be 4 (ERR_PARAM_OUT_RANGE)
   - SP_Temperature1 must remain at previous value (75.0)

7. **Unknown command**:
   - Write `Cmd.CmdID := 99`, `Cmd.CmdRequest := TRUE`
   - Read `Cmd.CmdError` — must be TRUE
   - Read `Cmd.CmdErrorID` — must be 1 (ERR_UNKNOWN_CMD)

8. **Screen change request from PLC**:
   - Write `RequestScreen := 5`, `ScreenChangeReq := TRUE` from PLC side
   - Simulate HMI navigation: Write `ActiveScreen := 5`
   - Read `ScreenChangeReq` — must auto-clear to FALSE

9. **Alarm bits**:
   - Set `AlarmWord1 := W#16#0005` in OB1 (bits 0 and 2 active)
   - Read `Status.AlarmActive` — must be TRUE
   - Read `Status.AlarmCount` — must be 2

## Variations

### Multiple HMI Panels
When two or more HMI panels connect to the same PLC, create a separate HMI interface DB
for each panel. This prevents one panel's commands from being overwritten by another:

```scl
DATA_BLOCK "DB_HmiPanel1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    Status : "UDT_HmiStatus";
    Cmd    : "UDT_HmiCommand";
    ActiveScreen : INT := 1;
    RequestScreen : INT;
    ScreenChangeReq : BOOL;
    SP_Temperature1 : REAL := 25.0;
    SP_Temperature2 : REAL := 25.0;
    SP_Pressure     : REAL := 1.0;
    SP_Speed        : REAL := 10.0;
    Lim_TempMin     : REAL := 0.0;
    Lim_TempMax     : REAL := 200.0;
    Lim_PressMin    : REAL := 0.0;
    Lim_PressMax    : REAL := 10.0;
    Lim_SpeedMin    : REAL := 0.0;
    Lim_SpeedMax    : REAL := 60.0;
    RecipeID        : INT;
    RecipeName      : STRING[32] := 'Default';
  END_STRUCT;
BEGIN
END_DATA_BLOCK

DATA_BLOCK "DB_HmiPanel2"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    Status : "UDT_HmiStatus";
    Cmd    : "UDT_HmiCommand";
    ActiveScreen : INT := 1;
    RequestScreen : INT;
    ScreenChangeReq : BOOL;
    SP_Temperature1 : REAL := 25.0;
    SP_Temperature2 : REAL := 25.0;
    SP_Pressure     : REAL := 1.0;
    SP_Speed        : REAL := 10.0;
    Lim_TempMin     : REAL := 0.0;
    Lim_TempMax     : REAL := 200.0;
    Lim_PressMin    : REAL := 0.0;
    Lim_PressMax    : REAL := 10.0;
    Lim_SpeedMin    : REAL := 0.0;
    Lim_SpeedMax    : REAL := 60.0;
    RecipeID        : INT;
    RecipeName      : STRING[32] := 'Default';
  END_STRUCT;
BEGIN
END_DATA_BLOCK
```
Then instantiate `FB_HmiHandler` once per panel in OB1. The status section is copied
identically to both DBs, but each panel has its own independent command channel.
Add a priority scheme if both panels send conflicting commands (e.g., Panel 1 = Start,
Panel 2 = Stop): typically the safer command wins (Stop > Start).

### Alarm Text Integration with TIA Portal Alarm System
Instead of using packed alarm WORDs, integrate with the TIA Portal Discrete Alarm system
for multilingual alarm text display on Comfort/Unified panels:

1. Configure Discrete Alarms in TIA Portal under the HMI device
2. Map each alarm trigger bit to a PLC tag in `DB_HmiInterface`
3. Assign alarm texts (with variables for dynamic values) in the alarm editor
4. The HMI automatically displays alarm popups, logs to alarm history, and supports
   acknowledgement — no additional SCL code needed for the display side

For the PLC side, add an acknowledgement handshake to `DB_HmiInterface`:
```scl
// Add to DB_HmiInterface STRUCT
AlarmAckRequest : WORD;      // HMI sets bit = operator acknowledged alarm N
AlarmAckDone    : WORD;      // PLC confirms acknowledgement of alarm N
```
The FB_HmiHandler processes acknowledgement by clearing the alarm source after
the operator acknowledges on the HMI, following the same handshake pattern as commands.

### S7-1200 Variant
The code is fully compatible with S7-1200 with one adjustment:
- Replace `TON_TIME` with `TON` if firmware is below V4.0
- `DATE_AND_TIME` for `PlcTime` may need to be replaced with individual `DATE` and
  `TIME_OF_DAY` fields on older S7-1200 firmware versions
- The maximum DB size on S7-1200 is 16 KB. The `DB_HmiInterface` structure above is
  well within this limit, but if you add large arrays or many STRING fields, monitor the
  DB size in the block properties
