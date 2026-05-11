# Case 003: Traffic Light Controller

## Frontmatter
- **Tags**: state-machine, timer, traffic-light, pedestrian, outputs, intermediate
- **CPU**: Both
- **Complexity**: Intermediate

## Requirements
Control a 4-way intersection traffic light with North-South and East-West directions.
Cycle through Green(20s) → Yellow(3s) → All-Red(1s safety gap) for each direction.
Pedestrian button interrupts sequence — shortens current green phase, completes cycle,
then serves pedestrian crossing before resuming normal operation.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_TrafficLight | FB | Traffic light state machine with timers |
| DB_Traffic1 | DB | Instance for FB_TrafficLight |
| Main (OB1) | OB | Calls FB_TrafficLight, maps to outputs |

## SCL Code
```scl
FUNCTION_BLOCK "FB_TrafficLight"
VERSION : 0.1
VAR_INPUT
  Enable          : BOOL := TRUE;
  PedestrianBtn   : BOOL;         // Pedestrian crossing request
END_VAR
VAR_OUTPUT
  NorthSouth_Green  : BOOL;
  NorthSouth_Yellow : BOOL;
  NorthSouth_Red    : BOOL;
  EastWest_Green    : BOOL;
  EastWest_Yellow   : BOOL;
  EastWest_Red      : BOOL;
  PedCrossing       : BOOL;       // Pedestrian walk signal active
  Error             : BOOL;
  ErrorID           : INT;
END_VAR
VAR
  State           : INT := 0;     // 0=GreenNS, 1=YellowNS, 2=AllRed1, 3=GreenEW, 4=YellowEW, 5=AllRed2, 6=PedPhase
  PhaseTimer      : TON_TIME;
  PedRequest      : BOOL;         // Latched pedestrian request
  PedTimer        : TON_TIME;
  TimerDone       : BOOL;
  GreenTime       : TIME := T#20s;
  YellowTime      : TIME := T#3s;
  AllRedTime       : TIME := T#1s;
  PedTime         : TIME := T#10s;
END_VAR
BEGIN
  IF NOT #Enable THEN
    // All red — safe default
    #NorthSouth_Green := FALSE;
    #NorthSouth_Yellow := FALSE;
    #NorthSouth_Red := TRUE;
    #EastWest_Green := FALSE;
    #EastWest_Yellow := FALSE;
    #EastWest_Red := TRUE;
    #PedCrossing := FALSE;
    #PhaseTimer(IN := FALSE, PT := T#0ms);
    #PedTimer(IN := FALSE, PT := T#0ms);
    #State := 0;
    #Error := FALSE;
    #ErrorID := 0;
    RETURN;
  END_IF;

  // Latch pedestrian request (cleared after serving)
  IF #PedestrianBtn THEN
    #PedRequest := TRUE;
  END_IF;

  // Default all outputs off — set per state
  #NorthSouth_Green := FALSE;
  #NorthSouth_Yellow := FALSE;
  #NorthSouth_Red := FALSE;
  #EastWest_Green := FALSE;
  #EastWest_Yellow := FALSE;
  #EastWest_Red := FALSE;
  #PedCrossing := FALSE;
  #Error := FALSE;
  #ErrorID := 0;

  CASE #State OF
    0:  // Green NS, Red EW
      #NorthSouth_Green := TRUE;
      #EastWest_Red := TRUE;
      #PhaseTimer(IN := TRUE, PT := #GreenTime);
      IF #PhaseTimer.Q THEN
        #PhaseTimer(IN := FALSE, PT := T#0ms);
        #State := 1;
      END_IF;

    1:  // Yellow NS, Red EW
      #NorthSouth_Yellow := TRUE;
      #EastWest_Red := TRUE;
      #PhaseTimer(IN := TRUE, PT := #YellowTime);
      IF #PhaseTimer.Q THEN
        #PhaseTimer(IN := FALSE, PT := T#0ms);
        #State := 2;
      END_IF;

    2:  // All Red (safety gap NS→EW)
      #NorthSouth_Red := TRUE;
      #EastWest_Red := TRUE;
      #PhaseTimer(IN := TRUE, PT := #AllRedTime);
      IF #PhaseTimer.Q THEN
        #PhaseTimer(IN := FALSE, PT := T#0ms);
        // Serve pedestrian if requested, otherwise go to Green EW
        IF #PedRequest THEN
          #State := 6;
        ELSE
          #State := 3;
        END_IF;
      END_IF;

    3:  // Red NS, Green EW
      #NorthSouth_Red := TRUE;
      #EastWest_Green := TRUE;
      #PhaseTimer(IN := TRUE, PT := #GreenTime);
      IF #PhaseTimer.Q THEN
        #PhaseTimer(IN := FALSE, PT := T#0ms);
        #State := 4;
      END_IF;

    4:  // Red NS, Yellow EW
      #NorthSouth_Red := TRUE;
      #EastWest_Yellow := TRUE;
      #PhaseTimer(IN := TRUE, PT := #YellowTime);
      IF #PhaseTimer.Q THEN
        #PhaseTimer(IN := FALSE, PT := T#0ms);
        #State := 5;
      END_IF;

    5:  // All Red (safety gap EW→NS)
      #NorthSouth_Red := TRUE;
      #EastWest_Red := TRUE;
      #PhaseTimer(IN := TRUE, PT := #AllRedTime);
      IF #PhaseTimer.Q THEN
        #PhaseTimer(IN := FALSE, PT := T#0ms);
        // Serve pedestrian if requested, otherwise go to Green NS
        IF #PedRequest THEN
          #State := 6;
        ELSE
          #State := 0;
        END_IF;
      END_IF;

    6:  // Pedestrian crossing phase (all traffic red)
      #NorthSouth_Red := TRUE;
      #EastWest_Red := TRUE;
      #PedCrossing := TRUE;
      #PedTimer(IN := TRUE, PT := #PedTime);
      IF #PedTimer.Q THEN
        #PedTimer(IN := FALSE, PT := T#0ms);
        #PedRequest := FALSE;
        #PedCrossing := FALSE;
        #State := 0;   // Resume with Green NS
      END_IF;

    ELSE
      // Unknown state — all red, set error
      #NorthSouth_Red := TRUE;
      #EastWest_Red := TRUE;
      #Error := TRUE;
      #ErrorID := 99;
      #State := 0;
  END_CASE;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Traffic1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_TrafficLight"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_Traffic1"(Enable        := TRUE,
                PedestrianBtn := %I0.0);
  // Map outputs: NS on Q0.0-Q0.2, EW on Q0.3-Q0.5, Ped on Q0.6
  %Q0.0 := "DB_Traffic1".NorthSouth_Green;
  %Q0.1 := "DB_Traffic1".NorthSouth_Yellow;
  %Q0.2 := "DB_Traffic1".NorthSouth_Red;
  %Q0.3 := "DB_Traffic1".EastWest_Green;
  %Q0.4 := "DB_Traffic1".EastWest_Yellow;
  %Q0.5 := "DB_Traffic1".EastWest_Red;
  %Q0.6 := "DB_Traffic1".PedCrossing;
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
- 6+1 state machine (6 traffic states + 1 pedestrian phase) — clear, linear cycle
- All-Red safety gap between direction changes — mandatory in real traffic systems
- Pedestrian request is latched (not edge-triggered) — button press is remembered
- Pedestrian phase served only during All-Red transitions — never interrupts mid-green
- Default outputs all FALSE at top of CASE, then set per state — prevents stale outputs
- Pedestrian phase returns to state 0 (Green NS) — deterministic restart
- All timers in VAR (static) — retained between scans
- S7_Optimized_Access=FALSE for S7.Net runtime monitoring

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify Green NS phase (state 0)
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 0=GreenNS)
S7ReadVariable(address="DB1.DBX28.0") → NorthSouth_Green (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX28.1") → NorthSouth_Yellow (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX28.2") → NorthSouth_Red (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX28.3") → EastWest_Green (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX28.4") → EastWest_Yellow (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX28.5") → EastWest_Red (BOOL, expect TRUE)

// Wait 20s, verify Yellow NS (state 1)
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 1=YellowNS)
S7ReadVariable(address="DB1.DBX28.1") → NorthSouth_Yellow (BOOL, expect TRUE)

// Wait 3s, verify All-Red (state 2)
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 2=AllRed1)
S7ReadVariable(address="DB1.DBX28.2") → NorthSouth_Red (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX28.5") → EastWest_Red (BOOL, expect TRUE)

// Wait 1s, verify Green EW (state 3)
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 3=GreenEW)
S7ReadVariable(address="DB1.DBX28.3") → EastWest_Green (BOOL, expect TRUE)

// Test pedestrian button
S7WriteVariable(address="%I0.0", value="true", type="Bit")
// Wait for next All-Red phase, then verify pedestrian phase
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 6=PedPhase)
S7ReadVariable(address="DB1.DBX28.6") → PedCrossing (BOOL, expect TRUE)

S7Disconnect()
```
