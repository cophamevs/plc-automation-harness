# Case 010: Star-Delta Motor Starter

## Frontmatter
- **Tags**: motor, star-delta, contactor, interlock, timer, sequence, intermediate
- **CPU**: Both
- **Complexity**: Intermediate

## Requirements
Implement a star-delta motor starting sequence with 3 contactors: KM1 (main), KM2
(star), KM3 (delta). Sequence: assert KM1+KM2 on start command, wait T_star (5s default),
de-energize KM2, wait T_transition (80ms) for arc extinction, energize KM3. Hardware
interlock ensures KM2 and KM3 are never energized simultaneously. Overload trip signal
immediately stops the sequence and enters fault state. Uses cascaded timer pattern for
the starting phases.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_StarDelta | FB | Star-delta starting sequence with interlock and fault handling |
| DB_StarDelta1 | DB | Instance for FB_StarDelta |
| Main (OB1) | OB | Calls FB_StarDelta with I/O mapping |

## SCL Code
```scl
FUNCTION_BLOCK "FB_StarDelta"
TITLE = 'Star-delta motor starter with interlock and overload protection'
VERSION : 0.1

VAR_INPUT
  CmdStart       : BOOL;         // Start command (momentary or maintained)
  CmdStop        : BOOL;         // Stop command
  OverloadTrip   : BOOL;         // Thermal overload relay trip signal
  EStop          : BOOL;         // Emergency stop
  T_Star         : TIME := T#5s; // Duration of star phase
  T_Transition   : TIME := T#80ms; // Dead time between star and delta
END_VAR

VAR_OUTPUT
  KM1            : BOOL;         // Main contactor output
  KM2            : BOOL;         // Star contactor output
  KM3            : BOOL;         // Delta contactor output
  Running        : BOOL;         // Motor is running (in delta)
  Starting       : BOOL;         // Motor is in start sequence
  Fault          : BOOL;         // Fault condition active
  Error          : BOOL;
  ErrorID        : INT;
END_VAR

VAR
  State          : INT := 0;     // 0=Stopped, 1=StarPhase, 2=Transition, 3=DeltaRun, 10=Fault
  StarTimer      : TON_TIME;     // Star phase duration timer
  TransTimer     : TON_TIME;     // Transition dead-time timer
END_VAR

BEGIN
  #Error := FALSE;
  #ErrorID := 0;

  // Emergency stop -- immediate shutdown from any state
  IF #EStop THEN
    #KM1 := FALSE;
    #KM2 := FALSE;
    #KM3 := FALSE;
    #Running := FALSE;
    #Starting := FALSE;
    #Fault := TRUE;
    #Error := TRUE;
    #ErrorID := 1;  // 1 = E-Stop
    #State := 10;
    #StarTimer(IN := FALSE, PT := T#0ms);
    #TransTimer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  // Overload trip -- immediate shutdown from any state
  IF #OverloadTrip THEN
    #KM1 := FALSE;
    #KM2 := FALSE;
    #KM3 := FALSE;
    #Running := FALSE;
    #Starting := FALSE;
    #Fault := TRUE;
    #Error := TRUE;
    #ErrorID := 2;  // 2 = Overload trip
    #State := 10;
    #StarTimer(IN := FALSE, PT := T#0ms);
    #TransTimer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  CASE #State OF
    0:  // Stopped -- all contactors off
      #KM1 := FALSE;
      #KM2 := FALSE;
      #KM3 := FALSE;
      #Running := FALSE;
      #Starting := FALSE;
      #Fault := FALSE;
      #StarTimer(IN := FALSE, PT := T#0ms);
      #TransTimer(IN := FALSE, PT := T#0ms);
      IF #CmdStart AND NOT #CmdStop THEN
        #State := 1;
      END_IF;

    1:  // Star phase -- KM1 + KM2 energized
      #KM1 := TRUE;
      #KM2 := TRUE;
      #KM3 := FALSE;     // Interlock: KM3 OFF during star
      #Starting := TRUE;
      #Running := FALSE;

      // Star phase timer
      #StarTimer(IN := TRUE, PT := #T_Star);
      IF #StarTimer.Q THEN
        #StarTimer(IN := FALSE, PT := T#0ms);
        #State := 2;
      END_IF;

      // Stop command during start
      IF #CmdStop THEN
        #StarTimer(IN := FALSE, PT := T#0ms);
        #State := 0;
      END_IF;

    2:  // Transition -- KM2 off, brief dead time before KM3
      #KM1 := TRUE;      // Main stays energized
      #KM2 := FALSE;     // Star contactor off
      #KM3 := FALSE;     // Delta not yet on -- interlock gap
      #Starting := TRUE;
      #Running := FALSE;

      // Transition timer (arc extinction dead time)
      #TransTimer(IN := TRUE, PT := #T_Transition);
      IF #TransTimer.Q THEN
        #TransTimer(IN := FALSE, PT := T#0ms);
        #State := 3;
      END_IF;

      // Stop command during transition
      IF #CmdStop THEN
        #TransTimer(IN := FALSE, PT := T#0ms);
        #State := 0;
      END_IF;

    3:  // Delta run -- KM1 + KM3 energized, normal operation
      #KM1 := TRUE;
      #KM2 := FALSE;     // Interlock: KM2 OFF during delta
      #KM3 := TRUE;
      #Starting := FALSE;
      #Running := TRUE;

      // Stop command
      IF #CmdStop THEN
        #State := 0;
      END_IF;

    10: // Fault -- all contactors off, wait for reset
      #KM1 := FALSE;
      #KM2 := FALSE;
      #KM3 := FALSE;
      #Running := FALSE;
      #Starting := FALSE;
      #Fault := TRUE;
      #Error := TRUE;
      // Reset: clear fault conditions + start command
      IF NOT #EStop AND NOT #OverloadTrip AND #CmdStart THEN
        #Fault := FALSE;
        #Error := FALSE;
        #ErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      #State := 10;
      #ErrorID := 99;
  END_CASE;

  // Hardware interlock enforcement (defense in depth)
  // KM2 and KM3 must NEVER be on simultaneously
  IF #KM2 AND #KM3 THEN
    #KM2 := FALSE;
    #KM3 := FALSE;
    #KM1 := FALSE;
    #Fault := TRUE;
    #Error := TRUE;
    #ErrorID := 3;  // 3 = Interlock violation
    #State := 10;
  END_IF;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_StarDelta1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_StarDelta"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_StarDelta1"(
    CmdStart     := %I0.0,
    CmdStop      := %I0.1,
    OverloadTrip := %I0.2,
    EStop        := %I0.3,
    T_Star       := T#5s,
    T_Transition := T#80ms
  );

  // Map contactor outputs
  %Q0.0 := "DB_StarDelta1".KM1;       // Main contactor
  %Q0.1 := "DB_StarDelta1".KM2;       // Star contactor
  %Q0.2 := "DB_StarDelta1".KM3;       // Delta contactor

  // Status indication
  %Q0.3 := "DB_StarDelta1".Running;   // Running lamp
  %Q0.4 := "DB_StarDelta1".Starting;  // Starting lamp
  %Q0.5 := "DB_StarDelta1".Fault;     // Fault lamp
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
- Cascaded timer pattern for star-delta sequence -- StarTimer controls star phase
  duration, TransTimer controls dead time gap, clean phase transitions
- Hardware interlock enforcement in software (defense in depth) -- even though physical
  interlock contactors should prevent KM2+KM3 simultaneous energization, software
  double-checks and faults if violated
- Transition dead time (80ms default) -- allows arc extinction on KM2 before KM3
  closes, prevents short circuit between star and delta windings
- E-Stop and OverloadTrip checked BEFORE CASE statement -- ensures immediate response
  regardless of current state, cannot be bypassed by state logic
- Configurable T_Star and T_Transition via inputs -- different motors need different
  star phase durations (typically 3-10s); adjustable without code change
- Fault state requires clearing ALL fault conditions + CmdStart to reset -- prevents
  restart while overload relay is still tripped
- ErrorID codes: 1=E-Stop, 2=Overload, 3=Interlock violation, 99=Invalid state
- Stop command honored in all running states (star, transition, delta) -- immediate
  contactor de-energization
- All timers in VAR (static) -- retain state between scans
- S7_Optimized_Access=FALSE for S7.Net runtime monitoring
- Block order: FB -> instance DB -> OB

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state -- all stopped
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 0=Stopped)
S7ReadVariable(address="DB1.DBX2.0")    -> KM1 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.1")    -> KM2 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.2")    -> KM3 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.3")    -> Running (BOOL, expect FALSE)

// Start motor
S7WriteVariable(address="%I0.0", value="true", type="Bit")

// Star phase: KM1+KM2 on, KM3 off
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 1=StarPhase)
S7ReadVariable(address="DB1.DBX2.0")    -> KM1 (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.1")    -> KM2 (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.2")    -> KM3 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.4")    -> Starting (BOOL, expect TRUE)

// Wait 5 seconds for star phase to complete
// Transition phase: KM2 off, KM3 not yet on
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 2=Transition)
S7ReadVariable(address="DB1.DBX2.1")    -> KM2 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.2")    -> KM3 (BOOL, expect FALSE)

// Wait 80ms -- delta run: KM1+KM3 on, KM2 off
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 3=DeltaRun)
S7ReadVariable(address="DB1.DBX2.0")    -> KM1 (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.1")    -> KM2 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.2")    -> KM3 (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.3")    -> Running (BOOL, expect TRUE)

// Stop motor
S7WriteVariable(address="%I0.1", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 0=Stopped)
S7ReadVariable(address="DB1.DBX2.0")    -> KM1 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX2.2")    -> KM3 (BOOL, expect FALSE)

// Test overload trip during running
S7WriteVariable(address="%I0.1", value="false", type="Bit")
S7WriteVariable(address="%I0.0", value="true", type="Bit")
// Wait for delta run state...
S7WriteVariable(address="%I0.2", value="true", type="Bit")  // Overload trip
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 10=Fault)
S7ReadVariable(address="DB1.DBX2.5")    -> Fault (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX2.6")    -> Error (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBW4")      -> ErrorID (INT, expect 2=Overload)

// Reset fault: clear overload + assert start
S7WriteVariable(address="%I0.2", value="false", type="Bit")
S7WriteVariable(address="%I0.0", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")      -> State (INT, expect 0=Stopped)
S7ReadVariable(address="DB1.DBX2.5")    -> Fault (BOOL, expect FALSE)

S7Disconnect()
```
