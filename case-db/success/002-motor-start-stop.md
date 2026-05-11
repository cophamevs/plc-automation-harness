# Case 002: Motor Start/Stop with Overload Protection

## Frontmatter
- **Tags**: motor, state-machine, interlock, overload, timer, intermediate
- **CPU**: Both
- **Complexity**: Intermediate

## Requirements
Control a motor with Start/Stop buttons, overload trip protection, anti-bounce
restart interlock (2s minimum stop time before restart), and runtime accumulation.
Motor states: Idle, Starting, Running, Stopping, Fault.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_Motor | FB | Motor control state machine with interlocks |
| DB_Motor1 | DB | Instance for FB_Motor |
| Main (OB1) | OB | Calls FB_Motor with I/O mapping |

## SCL Code
```scl
FUNCTION_BLOCK "FB_Motor"
VERSION : 0.1
VAR_INPUT
  Start        : BOOL;
  Stop         : BOOL;
  Reset        : BOOL;
  OverloadTrip : BOOL;
END_VAR
VAR_OUTPUT
  Running      : BOOL;
  Contactor    : BOOL;
  Error        : BOOL;
  ErrorID      : INT;
  RunTime      : TIME;
END_VAR
VAR
  State        : INT := 0;       // 0=Idle, 1=Starting, 2=Running, 3=Stopping, 10=Fault
  StartDelay   : TON_TIME;       // Anti-bounce: 2s delay before restart allowed
  StopDelay    : TON_TIME;       // Stopping ramp-down timer
  RuntimeAcc   : TON_TIME;       // Runtime accumulator
  StopComplete : BOOL;           // Motor has been stopped long enough
  PrevStart    : BOOL;           // Rising-edge detection for Start
END_VAR
BEGIN
  // --- Overload protection: any state except Fault transitions to Fault ---
  IF #OverloadTrip AND #State <> 10 THEN
    #State := 10;
    #ErrorID := 1;   // 1 = Overload trip
  END_IF;

  // --- Anti-bounce interlock timer: must be in Idle for 2s before restart ---
  #StartDelay(IN := (#State = 0), PT := T#2s);
  #StopComplete := #StartDelay.Q;

  // --- Runtime accumulator: counts while Running ---
  #RuntimeAcc(IN := (#State = 2), PT := T#24d);
  #RunTime := #RuntimeAcc.ET;

  // --- State machine ---
  CASE #State OF
    0:  // Idle
      #Running := FALSE;
      #Contactor := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      // Rising edge of Start AND interlock satisfied
      IF #Start AND NOT #PrevStart AND #StopComplete AND NOT #Stop THEN
        #State := 1;
      END_IF;

    1:  // Starting
      #Contactor := TRUE;
      #Running := FALSE;
      // Immediate transition to Running (no start delay for DOL)
      #State := 2;

    2:  // Running
      #Contactor := TRUE;
      #Running := TRUE;
      IF #Stop THEN
        #State := 3;
      END_IF;

    3:  // Stopping
      #Contactor := FALSE;
      #Running := FALSE;
      #StopDelay(IN := TRUE, PT := T#500ms);
      IF #StopDelay.Q THEN
        #StopDelay(IN := FALSE, PT := T#0ms);
        #State := 0;
      END_IF;

    10: // Fault
      #Contactor := FALSE;
      #Running := FALSE;
      #Error := TRUE;
      // Reset only when overload is cleared
      IF #Reset AND NOT #OverloadTrip THEN
        #Error := FALSE;
        #ErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      // Unknown state — go to Fault
      #State := 10;
      #ErrorID := 99;
  END_CASE;

  #PrevStart := #Start;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Motor1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Motor"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_Motor1"(Start        := %I0.0,
              Stop         := %I0.1,
              Reset        := %I0.2,
              OverloadTrip := %I0.3);
  %Q0.0 := "DB_Motor1".Contactor;
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
- State machine with explicit integer states — clear, extensible, debuggable via S7Read
- Anti-bounce interlock uses TON: motor must stay in Idle for 2s before Start is accepted
  — prevents rapid Start/Stop cycling that damages contactors
- Rising-edge detection on Start — prevents re-triggering while button is held
- Stop priority: Stop input checked before Start in Running state
- Separate Starting state even for DOL — allows future extension (star-delta, soft-start)
- Runtime accumulator uses TON with 24-day PT — ET gives elapsed time while Running
- S7_Optimized_Access=FALSE for S7.Net runtime access
- ErrorID codes: 1=Overload, 99=Unknown state (defensive)

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state (Idle)
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX10.0") → Running (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX10.1") → Contactor (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX10.2") → Error (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBW12")   → ErrorID (INT, expect 0)

// Start motor (set I0.0, wait >2s for interlock)
S7WriteVariable(address="%I0.0", value="true", type="Bit")
// Wait 2s+ for anti-bounce interlock
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 2=Running)
S7ReadVariable(address="DB1.DBX10.0") → Running (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX10.1") → Contactor (BOOL, expect TRUE)

// Stop motor
S7WriteVariable(address="%I0.1", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 0=Idle after 500ms)

// Test overload fault
S7WriteVariable(address="%I0.3", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 10=Fault)
S7ReadVariable(address="DB1.DBX10.2") → Error (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBW12")   → ErrorID (INT, expect 1)

// Reset fault (clear overload first, then pulse reset)
S7WriteVariable(address="%I0.3", value="false", type="Bit")
S7WriteVariable(address="%I0.2", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 0=Idle)

S7Disconnect()
```
