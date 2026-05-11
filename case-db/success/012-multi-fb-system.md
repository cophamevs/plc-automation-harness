# Case 012: Multi-FB System with Error Propagation

## Frontmatter
- **Tags**: multi-fb, error-propagation, aggregation, hierarchy, advanced
- **CPU**: Both
- **Complexity**: Advanced

## Requirements
System with three function blocks (FB_Pump, FB_Valve, FB_Tank) where FB_Tank
orchestrates FB_Pump and FB_Valve to perform a tank fill/drain cycle. Errors from
child FBs propagate upward to FB_Tank's Error/ErrorID outputs using an offset
pattern: pump errors = 100 + child ErrorID, valve errors = 200 + child ErrorID.
FB nesting is exactly 1 level deep (OB1 calls FB_Tank, which calls FB_Pump and
FB_Valve).

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_Pump | FB | Start/stop pump with overload detection |
| FB_Valve | FB | Open/close valve with timeout monitoring |
| FB_Tank | FB | Orchestrates fill/drain cycle using pump + valve (contains Pump and Valve as multi-instances) |
| DB_Tank1 | DB | Instance for FB_Tank (includes embedded FB_Pump and FB_Valve data) |
| Main (OB1) | OB | Calls FB_Tank with I/O mapping |

## SCL Code
```scl
FUNCTION_BLOCK "FB_Pump"
TITLE = 'Pump control with overload detection'
VERSION : 0.1

VAR_INPUT
  CmdStart       : BOOL;         // Start pump command
  CmdStop        : BOOL;         // Stop pump command
  OverloadSignal : BOOL;         // Overload relay feedback
  Reset          : BOOL;         // Reset fault
END_VAR

VAR_OUTPUT
  Running        : BOOL;         // Pump is running
  Error          : BOOL;
  ErrorID        : INT;
END_VAR

VAR
  State          : INT := 0;     // 0=Stopped, 1=Running, 10=Fault
  RunTimer       : TON_TIME;     // Monitors minimum run time before overload check
END_VAR

VAR_TEMP
  temp           : INT;
END_VAR

BEGIN
  #Error := FALSE;
  #ErrorID := 0;

  CASE #State OF
    0:  // Stopped
      #Running := FALSE;
      #RunTimer(IN := FALSE, PT := T#0ms);

      IF #CmdStart AND NOT #CmdStop THEN
        #State := 1;
      END_IF;

    1:  // Running
      #Running := TRUE;

      // Monitor overload while running
      #RunTimer(IN := TRUE, PT := T#500ms);
      IF #OverloadSignal THEN
        #Running := FALSE;
        #Error := TRUE;
        #ErrorID := 1;  // 1 = Pump overload
        #State := 10;
        #RunTimer(IN := FALSE, PT := T#0ms);
      END_IF;

      // Stop command
      IF #CmdStop THEN
        #Running := FALSE;
        #RunTimer(IN := FALSE, PT := T#0ms);
        #State := 0;
      END_IF;

    10: // Fault
      #Running := FALSE;
      #Error := TRUE;
      #ErrorID := 1;  // 1 = Pump overload
      // Reset only when overload cleared
      IF #Reset AND NOT #OverloadSignal THEN
        #Error := FALSE;
        #ErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      #State := 10;
      #Error := TRUE;
      #ErrorID := 99;  // 99 = Invalid state
  END_CASE;
END_FUNCTION_BLOCK

FUNCTION_BLOCK "FB_Valve"
TITLE = 'Valve control with open/close timeout monitoring'
VERSION : 0.1

VAR_INPUT
  CmdOpen        : BOOL;         // Open valve command
  CmdClose       : BOOL;         // Close valve command
  FbkOpen        : BOOL;         // Limit switch: valve fully open
  FbkClosed      : BOOL;         // Limit switch: valve fully closed
  Reset          : BOOL;         // Reset fault
  T_Timeout      : TIME := T#10s; // Max time to reach commanded position
END_VAR

VAR_OUTPUT
  IsOpen         : BOOL;         // Valve is confirmed open
  IsClosed       : BOOL;         // Valve is confirmed closed
  Error          : BOOL;
  ErrorID        : INT;
END_VAR

VAR
  State          : INT := 0;     // 0=Closed, 1=Opening, 2=Open, 3=Closing, 10=Fault
  MoveTimer      : TON_TIME;     // Monitors valve travel timeout
END_VAR

VAR_TEMP
  temp           : INT;
END_VAR

BEGIN
  #Error := FALSE;
  #ErrorID := 0;

  CASE #State OF
    0:  // Closed
      #IsOpen := FALSE;
      #IsClosed := TRUE;
      #MoveTimer(IN := FALSE, PT := T#0ms);

      IF #CmdOpen AND NOT #CmdClose THEN
        #IsClosed := FALSE;
        #State := 1;
      END_IF;

    1:  // Opening -- waiting for open feedback
      #IsOpen := FALSE;
      #IsClosed := FALSE;

      #MoveTimer(IN := TRUE, PT := #T_Timeout);

      // Feedback received: valve is open
      IF #FbkOpen THEN
        #MoveTimer(IN := FALSE, PT := T#0ms);
        #State := 2;
      END_IF;

      // Timeout: valve did not reach open position
      IF #MoveTimer.Q AND NOT #FbkOpen THEN
        #Error := TRUE;
        #ErrorID := 1;  // 1 = Open timeout
        #MoveTimer(IN := FALSE, PT := T#0ms);
        #State := 10;
      END_IF;

      // Abort: close command during opening
      IF #CmdClose THEN
        #MoveTimer(IN := FALSE, PT := T#0ms);
        #State := 3;
      END_IF;

    2:  // Open
      #IsOpen := TRUE;
      #IsClosed := FALSE;
      #MoveTimer(IN := FALSE, PT := T#0ms);

      // Lost open feedback while supposed to be open
      IF NOT #FbkOpen THEN
        #Error := TRUE;
        #ErrorID := 3;  // 3 = Unexpected position loss
        #State := 10;
      END_IF;

      IF #CmdClose AND NOT #CmdOpen THEN
        #IsOpen := FALSE;
        #State := 3;
      END_IF;

    3:  // Closing -- waiting for closed feedback
      #IsOpen := FALSE;
      #IsClosed := FALSE;

      #MoveTimer(IN := TRUE, PT := #T_Timeout);

      // Feedback received: valve is closed
      IF #FbkClosed THEN
        #MoveTimer(IN := FALSE, PT := T#0ms);
        #State := 0;
      END_IF;

      // Timeout: valve did not reach closed position
      IF #MoveTimer.Q AND NOT #FbkClosed THEN
        #Error := TRUE;
        #ErrorID := 2;  // 2 = Close timeout
        #MoveTimer(IN := FALSE, PT := T#0ms);
        #State := 10;
      END_IF;

      // Abort: open command during closing
      IF #CmdOpen THEN
        #MoveTimer(IN := FALSE, PT := T#0ms);
        #State := 1;
      END_IF;

    10: // Fault
      #IsOpen := FALSE;
      #IsClosed := FALSE;
      #Error := TRUE;
      // Preserve ErrorID from the transition that entered fault
      IF #ErrorID = 0 THEN
        #ErrorID := 99;  // Fallback if no specific code was set
      END_IF;

      IF #Reset THEN
        #Error := FALSE;
        #ErrorID := 0;
        // Return to closed if feedback confirms, else stay in fault
        IF #FbkClosed THEN
          #State := 0;
        ELSIF #FbkOpen THEN
          #State := 2;
        ELSE
          // Neither feedback -- cannot determine position, remain faulted
          #Error := TRUE;
          #ErrorID := 4;  // 4 = Unknown position after reset
        END_IF;
      END_IF;

    ELSE
      #State := 10;
      #Error := TRUE;
      #ErrorID := 99;  // 99 = Invalid state
  END_CASE;
END_FUNCTION_BLOCK

FUNCTION_BLOCK "FB_Tank"
TITLE = 'Tank fill/drain orchestrator using pump and valve'
VERSION : 0.1

VAR_INPUT
  CmdFill        : BOOL;         // Start fill cycle
  CmdDrain       : BOOL;         // Start drain cycle
  CmdStop        : BOOL;         // Stop all operations
  LevelHigh      : BOOL;         // Tank level high sensor
  LevelLow       : BOOL;         // Tank level low sensor
  PumpOverload   : BOOL;         // Pump overload relay signal
  ValveFbkOpen   : BOOL;         // Valve open limit switch
  ValveFbkClosed : BOOL;         // Valve closed limit switch
  Reset          : BOOL;         // Reset all faults
END_VAR

VAR_OUTPUT
  PumpRunning    : BOOL;         // Pump status output
  ValveOpen      : BOOL;         // Valve status output
  ValveClosed    : BOOL;         // Valve status output
  Filling        : BOOL;         // Fill cycle active
  Draining       : BOOL;         // Drain cycle active
  Idle           : BOOL;         // System idle
  Error          : BOOL;
  ErrorID        : INT;
END_VAR

VAR
  State          : INT := 0;     // 0=Idle, 1=FillOpenValve, 2=FillPumping, 3=FillCloseValve,
                                  // 4=DrainOpenValve, 5=DrainWait, 6=DrainCloseValve, 10=Fault
  Pump           : "FB_Pump";    // Child FB instance: pump controller
  Valve          : "FB_Valve";   // Child FB instance: valve controller
  FaultErrorID   : INT;          // Latched error ID for fault state
END_VAR

VAR_TEMP
  pumpErr        : BOOL;
  pumpErrID      : INT;
  valveErr       : BOOL;
  valveErrID     : INT;
END_VAR

BEGIN
  // ------------------------------------------------------------------
  // Step 1: Call child FBs every scan
  // ------------------------------------------------------------------

  // Determine pump commands based on current state
  #Pump(
    CmdStart       := (#State = 2),
    CmdStop        := (#State <> 2),
    OverloadSignal := #PumpOverload,
    Reset          := #Reset
  );

  // Determine valve commands based on current state
  #Valve(
    CmdOpen        := (#State = 1) OR (#State = 4),
    CmdClose       := (#State = 3) OR (#State = 6),
    FbkOpen        := #ValveFbkOpen,
    FbkClosed      := #ValveFbkClosed,
    Reset          := #Reset,
    T_Timeout      := T#10s
  );

  // ------------------------------------------------------------------
  // Step 2: Capture child error states
  // ------------------------------------------------------------------
  #pumpErr := #Pump.Error;
  #pumpErrID := #Pump.ErrorID;
  #valveErr := #Valve.Error;
  #valveErrID := #Valve.ErrorID;

  // Map child statuses to outputs
  #PumpRunning := #Pump.Running;
  #ValveOpen := #Valve.IsOpen;
  #ValveClosed := #Valve.IsClosed;

  // ------------------------------------------------------------------
  // Step 3: Error propagation -- check children BEFORE state machine
  // ------------------------------------------------------------------
  #Error := FALSE;
  #ErrorID := 0;

  IF #pumpErr THEN
    #Error := TRUE;
    #ErrorID := 100 + #pumpErrID;   // Pump errors: 101, 199, etc.
    #FaultErrorID := #ErrorID;
    #Filling := FALSE;
    #Draining := FALSE;
    #Idle := FALSE;
    #State := 10;
    RETURN;
  END_IF;

  IF #valveErr THEN
    #Error := TRUE;
    #ErrorID := 200 + #valveErrID;  // Valve errors: 201, 202, 203, etc.
    #FaultErrorID := #ErrorID;
    #Filling := FALSE;
    #Draining := FALSE;
    #Idle := FALSE;
    #State := 10;
    RETURN;
  END_IF;

  // ------------------------------------------------------------------
  // Step 4: Tank state machine
  // ------------------------------------------------------------------
  CASE #State OF
    0:  // Idle -- everything stopped
      #Filling := FALSE;
      #Draining := FALSE;
      #Idle := TRUE;

      IF #CmdFill AND NOT #CmdStop THEN
        #State := 1;
      ELSIF #CmdDrain AND NOT #CmdStop THEN
        #State := 4;
      END_IF;

    // ---- FILL CYCLE: open valve -> pump -> close valve ----
    1:  // Fill: Opening valve
      #Filling := TRUE;
      #Draining := FALSE;
      #Idle := FALSE;

      IF #Valve.IsOpen THEN
        #State := 2;  // Valve open, start pumping
      END_IF;

      IF #CmdStop THEN
        #State := 3;  // Abort: close valve
      END_IF;

    2:  // Fill: Pumping (valve open, pump running)
      #Filling := TRUE;
      #Draining := FALSE;
      #Idle := FALSE;

      // Tank full -- stop pumping, close valve
      IF #LevelHigh THEN
        #State := 3;
      END_IF;

      IF #CmdStop THEN
        #State := 3;
      END_IF;

    3:  // Fill: Closing valve (pump stopped by CmdStop logic above)
      #Filling := TRUE;
      #Draining := FALSE;
      #Idle := FALSE;

      IF #Valve.IsClosed THEN
        #Filling := FALSE;
        #State := 0;  // Cycle complete
      END_IF;

    // ---- DRAIN CYCLE: open valve -> wait for low level -> close valve ----
    4:  // Drain: Opening valve
      #Filling := FALSE;
      #Draining := TRUE;
      #Idle := FALSE;

      IF #Valve.IsOpen THEN
        #State := 5;  // Valve open, draining by gravity
      END_IF;

      IF #CmdStop THEN
        #State := 6;  // Abort: close valve
      END_IF;

    5:  // Drain: Waiting for tank empty (gravity drain)
      #Filling := FALSE;
      #Draining := TRUE;
      #Idle := FALSE;

      // Tank empty -- close valve
      IF #LevelLow THEN
        #State := 6;
      END_IF;

      IF #CmdStop THEN
        #State := 6;
      END_IF;

    6:  // Drain: Closing valve
      #Filling := FALSE;
      #Draining := TRUE;
      #Idle := FALSE;

      IF #Valve.IsClosed THEN
        #Draining := FALSE;
        #State := 0;  // Cycle complete
      END_IF;

    10: // Fault -- propagated from child FB
      #Filling := FALSE;
      #Draining := FALSE;
      #Idle := FALSE;
      #Error := TRUE;
      #ErrorID := #FaultErrorID;

      // Reset: wait for children to clear their faults
      IF #Reset AND NOT #Pump.Error AND NOT #Valve.Error THEN
        #Error := FALSE;
        #ErrorID := 0;
        #FaultErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      #FaultErrorID := 999;  // Unknown state
      #State := 10;
  END_CASE;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Tank1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Tank"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_Tank1"(
    CmdFill        := %I0.0,      // Fill command
    CmdDrain       := %I0.1,      // Drain command
    CmdStop        := %I0.2,      // Stop command
    LevelHigh      := %I0.3,      // High level sensor
    LevelLow       := %I0.4,      // Low level sensor
    PumpOverload   := %I0.5,      // Pump overload relay
    ValveFbkOpen   := %I0.6,      // Valve open feedback
    ValveFbkClosed := %I0.7,      // Valve closed feedback
    Reset          := %I1.0       // Fault reset
  );

  // Map status outputs for HMI indication
  %Q0.0 := "DB_Tank1".PumpRunning;   // Pump running lamp
  %Q0.1 := "DB_Tank1".ValveOpen;     // Valve open lamp
  %Q0.2 := "DB_Tank1".Filling;       // Filling indicator
  %Q0.3 := "DB_Tank1".Draining;      // Draining indicator
  %Q0.4 := "DB_Tank1".Idle;          // Idle indicator
  %Q0.5 := "DB_Tank1".Error;         // Fault lamp
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
- Error offset pattern (100+x for pump, 200+x for valve) -- allows FB_Tank's
  consumer to disambiguate error source from a single ErrorID value without
  inspecting child instances; extensible to more children (300+x, 400+x)
- 1-level nesting only (OB1 -> FB_Tank -> FB_Pump/FB_Valve) -- keeps the call
  hierarchy shallow for readability, fits within S7-1200's 6-level nesting limit,
  and simplifies debugging since each level's errors are clearly separated
- Separate FBs vs one monolithic FB -- FB_Pump and FB_Valve are reusable across
  projects; a different system could use FB_Pump for a different purpose without
  carrying valve logic, promoting composability
- Child FBs called every scan regardless of tank state -- ensures timers and
  fault detection remain active even during states where the child is "idle";
  command inputs are driven by state comparison expressions
- Child errors checked BEFORE the CASE statement -- guarantees immediate fault
  propagation regardless of which tank state is active; uses RETURN to skip
  normal state logic entirely
- FaultErrorID latched in a static variable -- preserves the original error code
  in state 10 across scans, since child FBs may clear their errors on reset
  before FB_Tank transitions out of fault state
- Valve feedback-based transitions -- state machine advances when limit switches
  confirm position rather than on timer, making the design robust against
  varying valve travel times
- Pump and Valve instances declared as VAR (static) inside FB_Tank -- the child
  instance data is embedded in DB_Tank1, no separate instance DBs needed at the
  project level; this is the standard TIA Portal pattern for multi-instance FBs
- S7_Optimized_Access=FALSE on all DBs for S7.Net runtime access
- Block order: FB_Pump -> FB_Valve -> FB_Tank -> instance DB -> OB (dependency order)

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state -- idle, no errors
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX2.5")    -> Idle (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.6")    -> Error (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBW4")      -> ErrorID (INT, expect 0)

// Verify pump child status (embedded in DB_Tank1)
S7ReadVariable(address="DB1.DBX6.0")    -> PumpRunning (BOOL, expect FALSE)
// Verify valve child status
S7ReadVariable(address="DB1.DBX6.1")    -> ValveOpen (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX6.2")    -> ValveClosed (BOOL, expect TRUE)

// === Test 1: Normal fill cycle ===
// Start fill
S7WriteVariable(address="%I0.0", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 1=FillOpenValve)
S7ReadVariable(address="DB1.DBX2.2")    -> Filling (BOOL, expect TRUE)

// Simulate valve open feedback
S7WriteVariable(address="%I0.6", value="true", type="Bit")
S7WriteVariable(address="%I0.7", value="false", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 2=FillPumping)
S7ReadVariable(address="DB1.DBX2.0")    -> PumpRunning (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.1")    -> ValveOpen (BOOL, expect TRUE)

// Simulate tank full
S7WriteVariable(address="%I0.3", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 3=FillCloseValve)
S7ReadVariable(address="DB1.DBX2.0")    -> PumpRunning (BOOL, expect FALSE)

// Simulate valve closed feedback
S7WriteVariable(address="%I0.6", value="false", type="Bit")
S7WriteVariable(address="%I0.7", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX2.5")    -> Idle (BOOL, expect TRUE)

// === Test 2: Pump overload during fill ===
// Clear previous inputs
S7WriteVariable(address="%I0.0", value="false", type="Bit")
S7WriteVariable(address="%I0.3", value="false", type="Bit")
S7WriteVariable(address="%I0.7", value="true", type="Bit")

// Start fill cycle again
S7WriteVariable(address="%I0.0", value="true", type="Bit")
S7WriteVariable(address="%I0.6", value="true", type="Bit")
S7WriteVariable(address="%I0.7", value="false", type="Bit")
// Wait for state 2 (pumping)

// Trigger pump overload
S7WriteVariable(address="%I0.5", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 10=Fault)
S7ReadVariable(address="DB1.DBX2.6")    -> Error (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBW4")      -> ErrorID (INT, expect 101 = 100 + pump overload)

// Reset fault: clear overload, assert reset
S7WriteVariable(address="%I0.5", value="false", type="Bit")
S7WriteVariable(address="%I1.0", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX2.6")    -> Error (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBW4")      -> ErrorID (INT, expect 0)

// === Test 3: Valve timeout during drain ===
// Start drain cycle
S7WriteVariable(address="%I1.0", value="false", type="Bit")
S7WriteVariable(address="%I0.0", value="false", type="Bit")
S7WriteVariable(address="%I0.1", value="true", type="Bit")
S7WriteVariable(address="%I0.6", value="false", type="Bit")
S7WriteVariable(address="%I0.7", value="false", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 4=DrainOpenValve)

// Do NOT provide valve open feedback -- wait 10s for timeout
S7ReadVariable(address="DB1.DBW0")      -> Tank State (INT, expect 10=Fault after timeout)
S7ReadVariable(address="DB1.DBX2.6")    -> Error (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBW4")      -> ErrorID (INT, expect 201 = 200 + valve open timeout)

S7Disconnect()
```
