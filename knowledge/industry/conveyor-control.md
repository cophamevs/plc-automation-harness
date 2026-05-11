# Conveyor Control

## Frontmatter
- **Tags**: conveyor, belt, sensor, jam, encoder, item-count, state-machine
- **CPU**: Both
- **Difficulty**: Intermediate

## Requirements
Belt conveyor with:
- Start/stop commands and emergency stop
- Entry and exit photoelectric sensors for item counting
- Encoder pulse input for jam detection (belt stall)
- State machine: Idle -> Starting -> Running -> Stopping -> Fault
- Jam detection: encoder not pulsing while motor is running for longer than JamTimeout

### Physical I/O Assumed
| Signal | Address | Description |
|--------|---------|-------------|
| CmdStart | I0.0 | Start pushbutton (NO) |
| CmdStop | I0.1 | Stop pushbutton (NC, wired NO in PLC) |
| EStop | I0.2 | Emergency stop (NC, TRUE = OK) |
| SensorEntry | I0.3 | Photoelectric sensor at belt entry |
| SensorExit | I0.4 | Photoelectric sensor at belt exit |
| EncoderPulse | I0.5 | Incremental encoder pulse (one pulse per revolution) |
| MotorRun | Q0.0 | Motor contactor output |

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| UDT_ConveyorData | UDT | Conveyor status structure for HMI | State, Running, Jammed, ItemCount, ErrorID |
| FB_Conveyor | FB | Complete conveyor control with state machine | Inputs: commands, sensors; Outputs: motor, status |
| DB_Conv1 | DB | Instance DB for conveyor 1 | Instance of FB_Conveyor |
| Main (OB1) | OB | Cyclic call to FB_Conveyor | Maps I/O to FB inputs/outputs |

## SCL Code

```scl
// =============================================================================
// UDT_ConveyorData — Status structure for HMI binding
// =============================================================================
TYPE "UDT_ConveyorData"
VERSION : 0.1
  STRUCT
    State       : INT;        // Current state number
    StateName   : STRING[20]; // Current state as text
    Running     : BOOL;       // Motor is running
    Jammed      : BOOL;       // Jam detected
    Error       : BOOL;       // Fault active
    ErrorID     : INT;        // Error code (0=none, 1=EStop, 2=Jam, 3=StartTimeout)
    ItemCount   : DINT;       // Total items passed exit sensor
    MotorRun    : BOOL;       // Motor contactor output
  END_STRUCT;
END_TYPE

// =============================================================================
// FB_Conveyor — Belt conveyor with jam detection and item counting
// =============================================================================
FUNCTION_BLOCK "FB_Conveyor"
TITLE = 'Belt Conveyor Control with Jam Detection'
VERSION : 0.1

VAR_INPUT
  CmdStart      : BOOL;       // Start command
  CmdStop       : BOOL;       // Stop command
  CmdReset      : BOOL;       // Reset from fault
  EStop         : BOOL;       // Emergency stop (TRUE = safe / OK)
  SensorEntry   : BOOL;       // Photoelectric at belt entry
  SensorExit    : BOOL;       // Photoelectric at belt exit
  EncoderPulse  : BOOL;       // Encoder pulse input
  JamTimeout    : TIME := T#3s; // Max time without encoder pulse while running
END_VAR

VAR_OUTPUT
  MotorRun      : BOOL;       // Motor contactor output
  Running       : BOOL;       // Conveyor is in Running state
  Jammed        : BOOL;       // Jam detected
  Error         : BOOL;       // Fault active
  ErrorID       : INT;        // Error code
  ItemCount     : DINT;       // Total items counted at exit sensor
  Status        : "UDT_ConveyorData"; // Aggregated status for HMI
END_VAR

VAR
  State         : INT := 0;
  PrevState     : INT := -1;
  StateTimer    : TON_TIME;    // Time in current state
  JamTimer      : TON_TIME;    // Jam detection timer
  StartTimeout  : TON_TIME;    // Start timeout (encoder must pulse within limit)
  PrevExitSensor : BOOL;       // Previous scan value for edge detection
  PrevEncoder   : BOOL;        // Previous encoder value for edge detection
  EncoderSeen   : BOOL;        // Encoder pulsed at least once since entering Running
END_VAR

VAR CONSTANT
  ST_IDLE       : INT := 0;
  ST_STARTING   : INT := 1;
  ST_RUNNING    : INT := 2;
  ST_STOPPING   : INT := 3;
  ST_FAULT      : INT := 10;
END_VAR

BEGIN
  // ---- Entry action: reset timers on state change ----
  IF #State <> #PrevState THEN
    #StateTimer(IN := FALSE, PT := T#0ms);
    #JamTimer(IN := FALSE, PT := T#0ms);
    #StartTimeout(IN := FALSE, PT := T#0ms);
    #EncoderSeen := FALSE;
    #PrevState := #State;
  END_IF;

  // Free-running state timer
  #StateTimer(IN := TRUE, PT := T#24h);

  // ---- Global EStop check ----
  IF NOT #EStop AND #State <> #ST_FAULT THEN
    #State := #ST_FAULT;
    #ErrorID := 1;  // Emergency stop
  END_IF;

  // ---- Item counting: rising edge on exit sensor ----
  IF #SensorExit AND NOT #PrevExitSensor THEN
    #ItemCount := #ItemCount + 1;
  END_IF;
  #PrevExitSensor := #SensorExit;

  // ---- Encoder edge detection ----
  IF #EncoderPulse AND NOT #PrevEncoder THEN
    #EncoderSeen := TRUE;
  END_IF;
  #PrevEncoder := #EncoderPulse;

  // ---- State machine ----
  CASE #State OF
    0: // ST_IDLE
      #MotorRun := FALSE;
      #Running := FALSE;
      #Jammed := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      IF #CmdStart AND NOT #CmdStop AND #EStop THEN
        #State := #ST_STARTING;
      END_IF;

    1: // ST_STARTING
      #MotorRun := TRUE;
      #Running := FALSE;
      // Wait for encoder confirmation or timeout
      #StartTimeout(IN := TRUE, PT := T#5s);
      IF #EncoderSeen THEN
        #State := #ST_RUNNING;
      END_IF;
      IF #StartTimeout.Q THEN
        #State := #ST_FAULT;
        #ErrorID := 3;  // Start timeout — encoder never pulsed
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    2: // ST_RUNNING
      #MotorRun := TRUE;
      #Running := TRUE;
      // Jam detection: reset jam timer on each encoder pulse
      IF #EncoderPulse AND NOT #PrevEncoder THEN
        // Edge already handled above; reset jam timer
        #JamTimer(IN := FALSE, PT := T#0ms);
      END_IF;
      #JamTimer(IN := TRUE, PT := #JamTimeout);
      IF #JamTimer.Q THEN
        #Jammed := TRUE;
        #State := #ST_FAULT;
        #ErrorID := 2;  // Jam — encoder stalled
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    3: // ST_STOPPING
      #MotorRun := FALSE;
      #Running := FALSE;
      // Allow belt to coast for 2 seconds
      IF #StateTimer.ET >= T#2s THEN
        #State := #ST_IDLE;
      END_IF;

    10: // ST_FAULT
      #MotorRun := FALSE;
      #Running := FALSE;
      #Error := TRUE;
      IF #CmdReset AND #EStop AND NOT #CmdStart THEN
        #Jammed := FALSE;
        #ErrorID := 0;
        #State := #ST_IDLE;
      END_IF;

    ELSE
      // Unknown state — go to fault
      #State := #ST_FAULT;
      #ErrorID := 99;
  END_CASE;

  // ---- Update HMI status structure ----
  #Status.State := #State;
  #Status.Running := #Running;
  #Status.Jammed := #Jammed;
  #Status.Error := #Error;
  #Status.ErrorID := #ErrorID;
  #Status.ItemCount := #ItemCount;
  #Status.MotorRun := #MotorRun;

  CASE #State OF
    0:  #Status.StateName := 'Idle';
    1:  #Status.StateName := 'Starting';
    2:  #Status.StateName := 'Running';
    3:  #Status.StateName := 'Stopping';
    10: #Status.StateName := 'Fault';
    ELSE #Status.StateName := 'Unknown';
  END_CASE;
END_FUNCTION_BLOCK

// =============================================================================
// DB_Conv1 — Instance DB for conveyor 1
// =============================================================================
DATA_BLOCK "DB_Conv1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Conveyor"
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
  "DB_Conv1"(
    CmdStart    := %I0.0,
    CmdStop     := %I0.1,
    CmdReset    := FALSE,
    EStop       := %I0.2,
    SensorEntry := %I0.3,
    SensorExit  := %I0.4,
    EncoderPulse := %I0.5,
    JamTimeout  := T#3s,
    MotorRun    => %Q0.0
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

// Read conveyor state
S7ReadVariable(address="DB1.DBW0")     // State (INT): 0=Idle, 1=Starting, 2=Running, 3=Stopping, 10=Fault
S7ReadVariable(address="DB1.DBX4.0")   // Running (BOOL)
S7ReadVariable(address="DB1.DBX4.1")   // Jammed (BOOL)
S7ReadVariable(address="DB1.DBX4.2")   // Error (BOOL)
S7ReadVariable(address="DB1.DBW6")     // ErrorID (INT)
S7ReadVariable(address="DB1.DBD8")     // ItemCount (DINT)

S7Disconnect()
```

### 3. Functional Tests
1. **Normal start**: Set CmdStart=TRUE -> State should go 0->1->2, MotorRun=TRUE
2. **Normal stop**: Set CmdStop=TRUE -> State should go 2->3->0, MotorRun=FALSE
3. **Jam detection**: While Running, stop encoder pulses for >3s -> State=10, Jammed=TRUE, ErrorID=2
4. **EStop**: Clear EStop input -> State=10 immediately, ErrorID=1
5. **Item count**: Toggle SensorExit -> ItemCount increments on each rising edge
6. **Reset**: In Fault state, set CmdReset=TRUE with EStop OK -> returns to Idle

## Variations

### S7-1200 Variant
The code is fully compatible with S7-1200. No S7-1500-specific features are used.
If using S7-1200 firmware < V4.0, replace `TON_TIME` with `TON` (IEC timer).

### Multiple Conveyors
Create additional instance DBs for each conveyor section:
```scl
DATA_BLOCK "DB_Conv2"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Conveyor"
BEGIN
END_DATA_BLOCK
```
Then call each in OB1 with different I/O mappings.

### Bidirectional Conveyor
Add a `Direction` input (BOOL) and a second motor output (`MotorRunFwd`, `MotorRunRev`).
Modify the Starting and Running states to energize the appropriate output based on direction.

### Speed Control (VFD)
Replace the digital `MotorRun` output with an analog speed setpoint (REAL, 0.0-1.0).
Add ramp-up/ramp-down logic in the Starting/Stopping states.
