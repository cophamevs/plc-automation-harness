# Case 013: Valve Sequencing with Interlocks

## Frontmatter
- **Tags**: valve, sequence, interlock, safety, state-machine
- **CPU**: Both
- **Complexity**: Advanced

## Requirements
Control 3 process valves (V1 inlet, V2 outlet, V3 drain) with interlock rules: V2 cannot
open unless V1 is open, V3 cannot open unless V2 is closed. Fill-drain sequence: Open V1
(inlet) -> wait for fill level sensor -> Open V2 (outlet) -> wait for drain-complete
sensor -> Close V2 -> Close V1. Each valve enforces its own interlock at the FB level so
the interlock logic is reusable across different sequences.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_InterlockValve | FB | Single valve with interlock input -- cannot open unless InterlockOK is TRUE |
| FB_ValveSequencer | FB | State machine orchestrating V1/V2/V3 fill-drain sequence |
| DB_ValveSequencer1 | DB | Instance for FB_ValveSequencer |
| Main (OB1) | OB | Calls FB_ValveSequencer with I/O mapping |

## SCL Code
```scl
FUNCTION_BLOCK "FB_InterlockValve"
TITLE = 'Valve with interlock -- cannot open unless InterlockOK is TRUE'
VERSION : 0.1

VAR_INPUT
  CmdOpen        : BOOL;         // Command to open the valve
  CmdClose       : BOOL;         // Command to close the valve
  InterlockOK    : BOOL;         // Interlock condition -- must be TRUE to open
  FeedbackOpen   : BOOL;         // Limit switch: valve is fully open
  FeedbackClosed : BOOL;         // Limit switch: valve is fully closed
  T_Travel       : TIME := T#5s; // Max travel time for open/close
END_VAR

VAR_OUTPUT
  ValveOut       : BOOL;         // Solenoid output to open valve
  IsOpen         : BOOL;         // Valve is confirmed open (feedback)
  IsClosed       : BOOL;         // Valve is confirmed closed (feedback)
  InterlockTrip  : BOOL;         // Interlock forced the valve closed
  Error          : BOOL;
  ErrorID        : INT;
END_VAR

VAR
  State          : INT := 0;     // 0=Closed, 1=Opening, 2=Open, 3=Closing, 10=Fault
  TravelTimer    : TON_TIME;     // Timeout for valve travel
END_VAR

BEGIN
  // Interlock enforcement -- if interlock lost while open, force close immediately
  IF NOT #InterlockOK AND (#State = 1 OR #State = 2) THEN
    #ValveOut := FALSE;
    #InterlockTrip := TRUE;
    #TravelTimer(IN := FALSE, PT := T#0ms);
    #State := 3;  // Go to closing state
  END_IF;

  CASE #State OF
    0:  // Closed -- valve solenoid off
      #ValveOut := FALSE;
      #IsOpen := FALSE;
      #IsClosed := #FeedbackClosed;
      #InterlockTrip := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      #TravelTimer(IN := FALSE, PT := T#0ms);
      IF #CmdOpen AND NOT #CmdClose AND #InterlockOK THEN
        #State := 1;
      END_IF;
      // CmdOpen without interlock -- report trip but stay closed
      IF #CmdOpen AND NOT #InterlockOK THEN
        #InterlockTrip := TRUE;
      END_IF;

    1:  // Opening -- solenoid energized, waiting for open feedback
      #ValveOut := TRUE;
      #IsOpen := FALSE;
      #IsClosed := FALSE;
      #TravelTimer(IN := TRUE, PT := #T_Travel);
      IF #FeedbackOpen THEN
        #TravelTimer(IN := FALSE, PT := T#0ms);
        #State := 2;
      END_IF;
      // Travel timeout -- valve stuck
      IF #TravelTimer.Q THEN
        #TravelTimer(IN := FALSE, PT := T#0ms);
        #ValveOut := FALSE;
        #Error := TRUE;
        #ErrorID := 1;  // 1 = Open travel timeout
        #State := 10;
      END_IF;
      // Close command during opening
      IF #CmdClose THEN
        #TravelTimer(IN := FALSE, PT := T#0ms);
        #State := 3;
      END_IF;

    2:  // Open -- valve confirmed open
      #ValveOut := TRUE;
      #IsOpen := #FeedbackOpen;
      #IsClosed := FALSE;
      #InterlockTrip := FALSE;
      // Loss of open feedback while supposedly open = fault
      IF NOT #FeedbackOpen THEN
        #Error := TRUE;
        #ErrorID := 3;  // 3 = Unexpected feedback loss
        #State := 10;
      END_IF;
      IF #CmdClose THEN
        #State := 3;
      END_IF;

    3:  // Closing -- solenoid de-energized, waiting for closed feedback
      #ValveOut := FALSE;
      #IsOpen := FALSE;
      #TravelTimer(IN := TRUE, PT := #T_Travel);
      IF #FeedbackClosed THEN
        #TravelTimer(IN := FALSE, PT := T#0ms);
        #IsClosed := TRUE;
        #State := 0;
      END_IF;
      // Travel timeout -- valve stuck open
      IF #TravelTimer.Q THEN
        #TravelTimer(IN := FALSE, PT := T#0ms);
        #Error := TRUE;
        #ErrorID := 2;  // 2 = Close travel timeout
        #State := 10;
      END_IF;

    10: // Fault -- solenoid off, wait for reset
      #ValveOut := FALSE;
      #IsOpen := FALSE;
      #IsClosed := FALSE;
      #Error := TRUE;
      // Reset: close command clears fault and returns to Closed
      IF #CmdClose AND NOT #CmdOpen THEN
        #Error := FALSE;
        #ErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      #State := 10;
      #ErrorID := 99;  // 99 = Invalid state
  END_CASE;
END_FUNCTION_BLOCK

FUNCTION_BLOCK "FB_ValveSequencer"
TITLE = 'Fill-drain valve sequence with 3 interlocked valves'
VERSION : 0.1

VAR_INPUT
  CmdStart       : BOOL;         // Start fill-drain sequence
  CmdStop        : BOOL;         // Abort sequence and close all valves
  CmdReset       : BOOL;         // Reset from fault state
  FillLevel      : BOOL;         // Fill level sensor -- TRUE when tank is full
  DrainComplete  : BOOL;         // Drain sensor -- TRUE when tank is empty
  EStop          : BOOL;         // Emergency stop
  V1_FbkOpen     : BOOL;         // V1 open limit switch
  V1_FbkClosed   : BOOL;         // V1 closed limit switch
  V2_FbkOpen     : BOOL;         // V2 open limit switch
  V2_FbkClosed   : BOOL;         // V2 closed limit switch
  V3_FbkOpen     : BOOL;         // V3 open limit switch
  V3_FbkClosed   : BOOL;         // V3 closed limit switch
END_VAR

VAR_OUTPUT
  V1_Out         : BOOL;         // V1 inlet solenoid
  V2_Out         : BOOL;         // V2 outlet solenoid
  V3_Out         : BOOL;         // V3 drain solenoid
  SeqState       : INT;          // Current sequence state for HMI
  SeqComplete    : BOOL;         // Sequence finished successfully
  Error          : BOOL;
  ErrorID        : INT;
END_VAR

VAR
  State          : INT := 0;     // 0=Idle,1=FillStart,2=Filling,3=DrainStart,4=Draining,5=Complete,10=Fault
  Valve1         : "FB_InterlockValve";
  Valve2         : "FB_InterlockValve";
  Valve3         : "FB_InterlockValve";
  FillTimeout    : TON_TIME;     // Max time to fill
  DrainTimeout   : TON_TIME;     // Max time to drain
  T_FillMax      : TIME := T#120s;  // Max fill time before fault
  T_DrainMax     : TIME := T#120s;  // Max drain time before fault
END_VAR

BEGIN
  // E-Stop -- immediate shutdown from any state
  IF #EStop AND #State <> 10 THEN
    #State := 10;
    #ErrorID := 1;  // 1 = E-Stop
  END_IF;

  CASE #State OF
    0:  // Idle -- all valves closed
      #Valve1(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
              FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      #Valve2(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := #Valve1.IsOpen,
              FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
      #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := NOT #Valve2.IsOpen,
              FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
      #SeqComplete := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      #FillTimeout(IN := FALSE, PT := T#0ms);
      #DrainTimeout(IN := FALSE, PT := T#0ms);
      #CloseDelay(IN := FALSE, PT := T#0ms);
      IF #CmdStart AND NOT #CmdStop THEN
        #State := 1;
      END_IF;

    1:  // FillStart -- open V1 (inlet)
      #Valve1(CmdOpen := TRUE, CmdClose := FALSE, InterlockOK := TRUE,
              FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      #Valve2(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := #Valve1.IsOpen,
              FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
      #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := NOT #Valve2.IsOpen,
              FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
      // Wait for V1 confirmed open
      IF #Valve1.IsOpen THEN
        #State := 2;
      END_IF;
      // Valve fault during opening
      IF #Valve1.Error THEN
        #ErrorID := 10;  // 10 = V1 fault
        #State := 10;
      END_IF;

    2:  // Filling -- V1 open, waiting for fill level
      #Valve1(CmdOpen := TRUE, CmdClose := FALSE, InterlockOK := TRUE,
              FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      #Valve2(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := #Valve1.IsOpen,
              FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
      #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := NOT #Valve2.IsOpen,
              FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
      // Fill timeout
      #FillTimeout(IN := TRUE, PT := #T_FillMax);
      IF #FillLevel THEN
        #FillTimeout(IN := FALSE, PT := T#0ms);
        #State := 3;
      END_IF;
      IF #FillTimeout.Q THEN
        #FillTimeout(IN := FALSE, PT := T#0ms);
        #ErrorID := 4;  // 4 = Fill timeout
        #State := 10;
      END_IF;

    3:  // DrainStart -- open V2 (outlet), V1 stays open
      // V2 interlock: V1 must be open
      #Valve1(CmdOpen := TRUE, CmdClose := FALSE, InterlockOK := TRUE,
              FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      #Valve2(CmdOpen := TRUE, CmdClose := FALSE, InterlockOK := #Valve1.IsOpen,
              FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
      #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := NOT #Valve2.IsOpen,
              FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
      // Wait for V2 confirmed open
      IF #Valve2.IsOpen THEN
        #State := 4;
      END_IF;
      // Valve fault
      IF #Valve2.Error THEN
        #ErrorID := 20;  // 20 = V2 fault
        #State := 10;
      END_IF;
      // Interlock trip (V1 closed unexpectedly)
      IF #Valve2.InterlockTrip THEN
        #ErrorID := 21;  // 21 = V2 interlock trip
        #State := 10;
      END_IF;

    4:  // Draining -- V1+V2 open, waiting for drain complete
      #Valve1(CmdOpen := TRUE, CmdClose := FALSE, InterlockOK := TRUE,
              FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      #Valve2(CmdOpen := TRUE, CmdClose := FALSE, InterlockOK := #Valve1.IsOpen,
              FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
      #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := NOT #Valve2.IsOpen,
              FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
      // Drain timeout
      #DrainTimeout(IN := TRUE, PT := #T_DrainMax);
      IF #DrainComplete THEN
        #DrainTimeout(IN := FALSE, PT := T#0ms);
        #State := 5;
      END_IF;
      IF #DrainTimeout.Q THEN
        #DrainTimeout(IN := FALSE, PT := T#0ms);
        #ErrorID := 5;  // 5 = Drain timeout
        #State := 10;
      END_IF;

    5:  // Complete -- close V2 first, then close V1
      #Valve1(CmdOpen := TRUE, CmdClose := NOT #Valve2.IsClosed, InterlockOK := TRUE,
              FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      #Valve2(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := #Valve1.IsOpen,
              FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
      #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := NOT #Valve2.IsOpen,
              FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
      // Once V2 is closed, close V1
      IF #Valve2.IsClosed THEN
        #Valve1(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
                FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      END_IF;
      // Both closed = sequence complete
      IF #Valve1.IsClosed AND #Valve2.IsClosed THEN
        #SeqComplete := TRUE;
        #State := 0;
      END_IF;
      // Valve faults during closing
      IF #Valve1.Error OR #Valve2.Error THEN
        #ErrorID := 6;  // 6 = Valve fault during close sequence
        #State := 10;
      END_IF;

    10: // Fault -- close all valves, wait for reset
      #Valve1(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
              FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
      #Valve2(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
              FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
      #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
              FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
      #Error := TRUE;
      #SeqComplete := FALSE;
      #FillTimeout(IN := FALSE, PT := T#0ms);
      #DrainTimeout(IN := FALSE, PT := T#0ms);
      // Reset: clear E-Stop + assert reset command
      IF NOT #EStop AND #CmdReset AND NOT #CmdStart THEN
        // Also reset valve-level faults
        #Valve1(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
                FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
        #Valve2(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
                FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
        #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
                FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
        #Error := FALSE;
        #ErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      #State := 10;
      #ErrorID := 99;  // 99 = Invalid state
  END_CASE;

  // Stop command -- abort from any running state
  IF #CmdStop AND #State >= 1 AND #State <= 5 THEN
    #Valve1(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
            FeedbackOpen := #V1_FbkOpen, FeedbackClosed := #V1_FbkClosed);
    #Valve2(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
            FeedbackOpen := #V2_FbkOpen, FeedbackClosed := #V2_FbkClosed);
    #Valve3(CmdOpen := FALSE, CmdClose := TRUE, InterlockOK := TRUE,
            FeedbackOpen := #V3_FbkOpen, FeedbackClosed := #V3_FbkClosed);
    #FillTimeout(IN := FALSE, PT := T#0ms);
    #DrainTimeout(IN := FALSE, PT := T#0ms);
    #State := 0;
  END_IF;

  // Aggregate outputs
  #V1_Out := #Valve1.ValveOut;
  #V2_Out := #Valve2.ValveOut;
  #V3_Out := #Valve3.ValveOut;
  #SeqState := #State;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_ValveSequencer1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_ValveSequencer"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_ValveSequencer1"(
    CmdStart      := %I0.0,
    CmdStop       := %I0.1,
    CmdReset      := %I0.2,
    FillLevel     := %I0.3,
    DrainComplete := %I0.4,
    EStop         := %I0.5,
    V1_FbkOpen    := %I1.0,
    V1_FbkClosed  := %I1.1,
    V2_FbkOpen    := %I1.2,
    V2_FbkClosed  := %I1.3,
    V3_FbkOpen    := %I1.4,
    V3_FbkClosed  := %I1.5
  );

  // Map valve solenoid outputs
  %Q0.0 := "DB_ValveSequencer1".V1_Out;    // V1 inlet solenoid
  %Q0.1 := "DB_ValveSequencer1".V2_Out;    // V2 outlet solenoid
  %Q0.2 := "DB_ValveSequencer1".V3_Out;    // V3 drain solenoid

  // Status outputs for HMI/indication
  %Q0.3 := "DB_ValveSequencer1".SeqComplete;  // Sequence complete lamp
  %Q0.4 := "DB_ValveSequencer1".Error;         // Fault lamp
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
- Interlock enforced at the FB level (FB_InterlockValve) rather than in the sequencer --
  makes interlock logic reusable across different processes; any sequence using this FB
  automatically gets interlock protection without reimplementing it
- Sequence implemented as a state machine (CASE) -- each state has a clear purpose,
  transitions are explicit, and the current state is visible on HMI via SeqState output;
  much easier to debug than combinational logic
- V2 interlock = V1.IsOpen (V2 cannot open unless V1 is confirmed open) -- prevents
  outlet flow without inlet, which could create vacuum or dry-run damage
- V3 interlock = NOT V2.IsOpen (V3 cannot open unless V2 is closed) -- prevents
  simultaneous drain and outlet flow, which could cause product loss or cross-contamination
- Valve travel timeout in FB_InterlockValve -- detects stuck valves early rather than
  waiting for process-level timeouts; ErrorID distinguishes open vs close timeout
- Fill and drain timeouts in FB_ValveSequencer -- catches process-level failures (sensor
  fault, pipe blockage) independently from valve-level faults
- Close sequence (state 5) closes V2 first, then V1 -- maintains V2 interlock (V1 must
  be open while V2 is open); closing V1 first would trigger V2 interlock trip
- InterlockTrip output on FB_InterlockValve -- allows the sequencer to distinguish between
  a valve fault and an interlock violation for targeted diagnostics
- ErrorID coding: 1=E-Stop, 4=Fill timeout, 5=Drain timeout, 6=Close fault,
  10/20/30=V1/V2/V3 fault, 21=V2 interlock trip, 99=Invalid state
- Fault state in sequencer passes InterlockOK=TRUE to all valves during close --
  ensures valves can close even when normal interlock conditions are not met
- S7_Optimized_Access=FALSE on instance DB for S7.Net runtime access
- Block order: FB_InterlockValve (dependency) -> FB_ValveSequencer -> instance DB -> OB

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state -- Idle, all valves closed
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX2.0")    -> V1_Out (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.1")    -> V2_Out (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.2")    -> V3_Out (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.7")    -> Error (BOOL, expect FALSE)

// Start sequence -- provide closed feedback for all valves
S7WriteVariable(address="%I1.1", value="true", type="Bit")  // V1 closed fbk
S7WriteVariable(address="%I1.3", value="true", type="Bit")  // V2 closed fbk
S7WriteVariable(address="%I1.5", value="true", type="Bit")  // V3 closed fbk
S7WriteVariable(address="%I0.0", value="true", type="Bit")  // CmdStart

// FillStart: V1 opening
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 1=FillStart)
S7ReadVariable(address="DB1.DBX2.0")    -> V1_Out (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.1")    -> V2_Out (BOOL, expect FALSE)

// Simulate V1 open feedback
S7WriteVariable(address="%I1.0", value="true", type="Bit")   // V1 open fbk
S7WriteVariable(address="%I1.1", value="false", type="Bit")  // V1 no longer closed

// Filling: V1 open, waiting for fill level
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 2=Filling)
S7ReadVariable(address="DB1.DBX2.0")    -> V1_Out (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.1")    -> V2_Out (BOOL, expect FALSE)

// Simulate fill level reached
S7WriteVariable(address="%I0.3", value="true", type="Bit")   // FillLevel

// DrainStart: V2 opening (interlock OK because V1 is open)
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 3=DrainStart)
S7ReadVariable(address="DB1.DBX2.1")    -> V2_Out (BOOL, expect TRUE)

// Simulate V2 open feedback
S7WriteVariable(address="%I1.2", value="true", type="Bit")   // V2 open fbk
S7WriteVariable(address="%I1.3", value="false", type="Bit")  // V2 no longer closed

// Draining: V1+V2 open, waiting for drain complete
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 4=Draining)
S7ReadVariable(address="DB1.DBX2.0")    -> V1_Out (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.1")    -> V2_Out (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.2")    -> V3_Out (BOOL, expect FALSE)

// Simulate drain complete
S7WriteVariable(address="%I0.4", value="true", type="Bit")   // DrainComplete

// Complete: V2 closing first, then V1
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 5=Complete)
S7ReadVariable(address="DB1.DBX2.1")    -> V2_Out (BOOL, expect FALSE -- V2 closing)

// Simulate V2 closed feedback
S7WriteVariable(address="%I1.2", value="false", type="Bit")  // V2 no longer open
S7WriteVariable(address="%I1.3", value="true", type="Bit")   // V2 closed fbk
// V1 should now start closing
S7ReadVariable(address="DB1.DBX2.0")    -> V1_Out (BOOL, expect FALSE)

// Simulate V1 closed feedback
S7WriteVariable(address="%I1.0", value="false", type="Bit")  // V1 no longer open
S7WriteVariable(address="%I1.1", value="true", type="Bit")   // V1 closed fbk

// Sequence complete -- back to Idle
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX2.3")    -> SeqComplete (BOOL, expect TRUE)

// Test interlock: try to open V2 without V1 (via manual test)
// V2.InterlockOK is driven by V1.IsOpen, so V2 cannot open when V1 is closed

// Test E-Stop during sequence
S7WriteVariable(address="%I0.0", value="true", type="Bit")   // CmdStart (restart)
// Wait for FillStart...
S7WriteVariable(address="%I0.5", value="true", type="Bit")   // E-Stop
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 10=Fault)
S7ReadVariable(address="DB1.DBX2.7")    -> Error (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBW4")      -> ErrorID (INT, expect 1=E-Stop)

// Reset from fault
S7WriteVariable(address="%I0.5", value="false", type="Bit")  // Clear E-Stop
S7WriteVariable(address="%I0.2", value="true", type="Bit")   // CmdReset
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX2.7")    -> Error (BOOL, expect FALSE)

S7Disconnect()
```
