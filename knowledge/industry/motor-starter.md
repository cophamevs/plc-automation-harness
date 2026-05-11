# Motor Starter Patterns

## Frontmatter
- **Tags**: motor, dol, star-delta, vfd, contactor, overload, interlock, speed
- **CPU**: Both
- **Difficulty**: Intermediate

## Requirements
Three motor start methods, each as an independent FB with standard error interface:
1. **DOL (Direct On Line)**: Simple contactor with overload relay and start/stop buttons
2. **Star-Delta**: 3 contactors with timed transition and interlock logic
3. **VFD (Variable Frequency Drive)**: Analog speed setpoint with digital run command

### Physical I/O Summary
| Method | Inputs | Outputs |
|--------|--------|---------|
| DOL | Start, Stop, OverloadTrip, RunFeedback | Contactor |
| Star-Delta | Start, Stop, OverloadTrip, RunFeedback | MainContactor, StarContactor, DeltaContactor |
| VFD | Start, Stop, StatusWord, FaultWord, SpeedSetpoint(%) | RunCommand, SpeedOutput(REAL) |

---

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| FB_MotorDOL | FB | Direct on line starter | Start/Stop/Overload -> Contactor/Running/Error |
| FB_MotorStarDelta | FB | Star-delta starter with timed transition | Start/Stop/Overload -> 3 contactors/Running/Error |
| FB_MotorVFD | FB | VFD speed control | Start/Stop/Speed% -> RunCmd/SpeedOutput/Error |
| DB_MotorDOL1 | DB | Instance for DOL motor 1 | Instance of FB_MotorDOL |
| DB_MotorSD1 | DB | Instance for star-delta motor 1 | Instance of FB_MotorStarDelta |
| DB_MotorVFD1 | DB | Instance for VFD motor 1 | Instance of FB_MotorVFD |
| Main (OB1) | OB | Cyclic calls to all three FBs | Maps I/O to FB interfaces |

---

## SCL Code

### Method 1: Direct On Line (DOL)

```scl
// =============================================================================
// FB_MotorDOL — Direct On Line motor starter
// =============================================================================
FUNCTION_BLOCK "FB_MotorDOL"
TITLE = 'DOL Motor Starter with Overload Protection'
VERSION : 0.1

VAR_INPUT
  CmdStart      : BOOL;       // Start pushbutton (momentary)
  CmdStop       : BOOL;       // Stop pushbutton (momentary)
  CmdReset      : BOOL;       // Reset fault
  OverloadTrip  : BOOL;       // Overload relay trip (TRUE = tripped)
  RunFeedback   : BOOL;       // Aux contact from contactor
END_VAR

VAR_OUTPUT
  Contactor     : BOOL;       // Main contactor output
  Running       : BOOL;       // Motor confirmed running (feedback)
  Error         : BOOL;       // Fault active
  ErrorID       : INT;        // 0=none, 1=Overload, 2=FeedbackTimeout
  RunTime       : TIME;       // Accumulated run time
END_VAR

VAR
  State         : INT := 0;
  PrevState     : INT := -1;
  Latched       : BOOL;       // Start command latched (seal-in)
  StateTimer    : TON_TIME;   // Time in current state
  FbkTimeout    : TON_TIME;   // Feedback timeout
  RunTimer      : TON_TIME;   // Accumulated run timer
END_VAR

VAR CONSTANT
  ST_IDLE       : INT := 0;
  ST_STARTING   : INT := 1;
  ST_RUNNING    : INT := 2;
  ST_STOPPING   : INT := 3;
  ST_FAULT      : INT := 10;
END_VAR

BEGIN
  // ---- Entry action ----
  IF #State <> #PrevState THEN
    #StateTimer(IN := FALSE, PT := T#0ms);
    #FbkTimeout(IN := FALSE, PT := T#0ms);
    #PrevState := #State;
  END_IF;
  #StateTimer(IN := TRUE, PT := T#24h);

  // ---- Global overload check ----
  IF #OverloadTrip AND #State <> #ST_FAULT THEN
    #State := #ST_FAULT;
    #ErrorID := 1;  // Overload trip
  END_IF;

  CASE #State OF
    0: // ST_IDLE
      #Contactor := FALSE;
      #Running := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      #Latched := FALSE;
      IF #CmdStart AND NOT #CmdStop AND NOT #OverloadTrip THEN
        #Latched := TRUE;
        #State := #ST_STARTING;
      END_IF;

    1: // ST_STARTING
      #Contactor := TRUE;
      // Wait for run feedback with timeout
      #FbkTimeout(IN := TRUE, PT := T#5s);
      IF #RunFeedback THEN
        #State := #ST_RUNNING;
      END_IF;
      IF #FbkTimeout.Q THEN
        #State := #ST_FAULT;
        #ErrorID := 2;  // Feedback timeout
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    2: // ST_RUNNING
      #Contactor := TRUE;
      #Running := TRUE;
      // Accumulate run time
      #RunTimer(IN := TRUE, PT := T#24h);
      #RunTime := #RunTimer.ET;
      // Monitor feedback loss
      IF NOT #RunFeedback THEN
        #State := #ST_FAULT;
        #ErrorID := 2;  // Feedback lost
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    3: // ST_STOPPING
      #Contactor := FALSE;
      #Running := FALSE;
      #Latched := FALSE;
      // Coast-down time
      IF #StateTimer.ET >= T#1s THEN
        #State := #ST_IDLE;
      END_IF;

    10: // ST_FAULT
      #Contactor := FALSE;
      #Running := FALSE;
      #Error := TRUE;
      IF #CmdReset AND NOT #OverloadTrip THEN
        #ErrorID := 0;
        #State := #ST_IDLE;
      END_IF;

    ELSE
      #State := #ST_FAULT;
      #ErrorID := 99;
  END_CASE;
END_FUNCTION_BLOCK

// =============================================================================
// DB_MotorDOL1 — Instance DB
// =============================================================================
DATA_BLOCK "DB_MotorDOL1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_MotorDOL"
BEGIN
END_DATA_BLOCK
```

### Method 2: Star-Delta

```scl
// =============================================================================
// FB_MotorStarDelta — Star-Delta motor starter
// =============================================================================
FUNCTION_BLOCK "FB_MotorStarDelta"
TITLE = 'Star-Delta Motor Starter with Interlock'
VERSION : 0.1

VAR_INPUT
  CmdStart        : BOOL;       // Start command
  CmdStop         : BOOL;       // Stop command
  CmdReset        : BOOL;       // Reset fault
  OverloadTrip    : BOOL;       // Overload relay trip
  RunFeedback     : BOOL;       // Motor running feedback
  StarTime        : TIME := T#6s;  // Time in star before transition
  TransitionTime  : TIME := T#50ms; // Open-transition gap (star off before delta on)
END_VAR

VAR_OUTPUT
  MainContactor   : BOOL;       // Main contactor (K1)
  StarContactor   : BOOL;       // Star contactor (K2)
  DeltaContactor  : BOOL;       // Delta contactor (K3)
  Running         : BOOL;       // Motor confirmed running in delta
  Error           : BOOL;       // Fault active
  ErrorID         : INT;        // 0=none, 1=Overload, 2=FbkTimeout, 3=TransitionFault
END_VAR

VAR
  State           : INT := 0;
  PrevState       : INT := -1;
  StateTimer      : TON_TIME;
  FbkTimeout      : TON_TIME;
  TransTimer      : TON_TIME;   // Transition gap timer
END_VAR

VAR CONSTANT
  ST_IDLE         : INT := 0;
  ST_STAR         : INT := 1;   // Star connection phase
  ST_TRANSITION   : INT := 2;   // Open transition (both off)
  ST_DELTA        : INT := 3;   // Delta connection phase
  ST_RUNNING      : INT := 4;   // Full speed in delta
  ST_STOPPING     : INT := 5;
  ST_FAULT        : INT := 10;
END_VAR

BEGIN
  // ---- Entry action ----
  IF #State <> #PrevState THEN
    #StateTimer(IN := FALSE, PT := T#0ms);
    #FbkTimeout(IN := FALSE, PT := T#0ms);
    #TransTimer(IN := FALSE, PT := T#0ms);
    #PrevState := #State;
  END_IF;
  #StateTimer(IN := TRUE, PT := T#24h);

  // ---- Interlock: Star and Delta NEVER simultaneous ----
  // (enforced by state logic, but also hard-coded safety)
  IF #StarContactor AND #DeltaContactor THEN
    #StarContactor := FALSE;
    #DeltaContactor := FALSE;
    #MainContactor := FALSE;
    #State := #ST_FAULT;
    #ErrorID := 3;  // Interlock violation
  END_IF;

  // ---- Global overload check ----
  IF #OverloadTrip AND #State <> #ST_FAULT THEN
    #State := #ST_FAULT;
    #ErrorID := 1;
  END_IF;

  CASE #State OF
    0: // ST_IDLE
      #MainContactor := FALSE;
      #StarContactor := FALSE;
      #DeltaContactor := FALSE;
      #Running := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      IF #CmdStart AND NOT #CmdStop AND NOT #OverloadTrip THEN
        #State := #ST_STAR;
      END_IF;

    1: // ST_STAR — energize main + star contactors
      #MainContactor := TRUE;
      #StarContactor := TRUE;
      #DeltaContactor := FALSE;
      // Timed transition to delta
      IF #StateTimer.ET >= #StarTime THEN
        #State := #ST_TRANSITION;
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    2: // ST_TRANSITION — open transition gap
      #MainContactor := TRUE;
      #StarContactor := FALSE;
      #DeltaContactor := FALSE;
      #TransTimer(IN := TRUE, PT := #TransitionTime);
      IF #TransTimer.Q THEN
        #State := #ST_DELTA;
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    3: // ST_DELTA — energize main + delta contactors
      #MainContactor := TRUE;
      #StarContactor := FALSE;
      #DeltaContactor := TRUE;
      // Wait for feedback confirmation
      #FbkTimeout(IN := TRUE, PT := T#5s);
      IF #RunFeedback THEN
        #State := #ST_RUNNING;
      END_IF;
      IF #FbkTimeout.Q THEN
        #State := #ST_FAULT;
        #ErrorID := 2;  // Feedback timeout in delta
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    4: // ST_RUNNING — full speed in delta
      #MainContactor := TRUE;
      #StarContactor := FALSE;
      #DeltaContactor := TRUE;
      #Running := TRUE;
      IF NOT #RunFeedback THEN
        #State := #ST_FAULT;
        #ErrorID := 2;
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    5: // ST_STOPPING
      #MainContactor := FALSE;
      #StarContactor := FALSE;
      #DeltaContactor := FALSE;
      #Running := FALSE;
      IF #StateTimer.ET >= T#2s THEN
        #State := #ST_IDLE;
      END_IF;

    10: // ST_FAULT
      #MainContactor := FALSE;
      #StarContactor := FALSE;
      #DeltaContactor := FALSE;
      #Running := FALSE;
      #Error := TRUE;
      IF #CmdReset AND NOT #OverloadTrip THEN
        #ErrorID := 0;
        #State := #ST_IDLE;
      END_IF;

    ELSE
      #State := #ST_FAULT;
      #ErrorID := 99;
  END_CASE;
END_FUNCTION_BLOCK

// =============================================================================
// DB_MotorSD1 — Instance DB
// =============================================================================
DATA_BLOCK "DB_MotorSD1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_MotorStarDelta"
BEGIN
END_DATA_BLOCK
```

### Method 3: VFD (Variable Frequency Drive)

```scl
// =============================================================================
// FB_MotorVFD — VFD speed control via analog output
// =============================================================================
FUNCTION_BLOCK "FB_MotorVFD"
TITLE = 'VFD Motor Control with Analog Speed Setpoint'
VERSION : 0.1

VAR_INPUT
  CmdStart        : BOOL;       // Start command
  CmdStop         : BOOL;       // Stop command
  CmdReset        : BOOL;       // Reset fault
  SpeedSetpoint   : REAL := 50.0; // Speed setpoint 0..100 (%)
  StatusWord      : WORD;       // VFD status word (digital input from drive)
  FaultWord       : WORD;       // VFD fault word (digital input from drive)
END_VAR

VAR_OUTPUT
  RunCommand      : BOOL;       // Digital run command to VFD
  SpeedOutput     : REAL;       // Analog speed output 0.0..1.0 (maps to 0-100%)
  Running         : BOOL;       // VFD reports running
  AtSpeed         : BOOL;       // VFD at target speed
  Error           : BOOL;       // Fault active
  ErrorID         : INT;        // 0=none, 1=VFDFault, 2=SpeedDeviation, 3=StartTimeout
  ActualSpeed     : REAL;       // Feedback speed (%) — derived from status
END_VAR

VAR
  State           : INT := 0;
  PrevState       : INT := -1;
  StateTimer      : TON_TIME;
  StartTimeout    : TON_TIME;
  ClampedSpeed    : REAL;
END_VAR

VAR CONSTANT
  ST_IDLE         : INT := 0;
  ST_STARTING     : INT := 1;
  ST_RUNNING      : INT := 2;
  ST_STOPPING     : INT := 3;
  ST_FAULT        : INT := 10;
END_VAR

BEGIN
  // ---- Entry action ----
  IF #State <> #PrevState THEN
    #StateTimer(IN := FALSE, PT := T#0ms);
    #StartTimeout(IN := FALSE, PT := T#0ms);
    #PrevState := #State;
  END_IF;
  #StateTimer(IN := TRUE, PT := T#24h);

  // ---- Speed clamping: 0..100% -> 0.0..1.0 ----
  #ClampedSpeed := #SpeedSetpoint;
  IF #ClampedSpeed < 0.0 THEN
    #ClampedSpeed := 0.0;
  END_IF;
  IF #ClampedSpeed > 100.0 THEN
    #ClampedSpeed := 100.0;
  END_IF;

  // ---- VFD fault check (bit 3 of fault word = general fault) ----
  IF (#FaultWord AND WORD#16#0008) <> WORD#16#0000 AND #State <> #ST_FAULT THEN
    #State := #ST_FAULT;
    #ErrorID := 1;  // VFD reported fault
  END_IF;

  // ---- Parse VFD status word ----
  // Bit 0 = Ready, Bit 1 = Running, Bit 2 = At Speed
  #Running := (#StatusWord AND WORD#16#0002) <> WORD#16#0000;
  #AtSpeed := (#StatusWord AND WORD#16#0004) <> WORD#16#0000;

  CASE #State OF
    0: // ST_IDLE
      #RunCommand := FALSE;
      #SpeedOutput := 0.0;
      #Error := FALSE;
      #ErrorID := 0;
      IF #CmdStart AND NOT #CmdStop THEN
        #State := #ST_STARTING;
      END_IF;

    1: // ST_STARTING
      #RunCommand := TRUE;
      #SpeedOutput := #ClampedSpeed / 100.0;
      // Wait for VFD running feedback
      #StartTimeout(IN := TRUE, PT := T#10s);
      IF #Running THEN
        #State := #ST_RUNNING;
      END_IF;
      IF #StartTimeout.Q THEN
        #State := #ST_FAULT;
        #ErrorID := 3;  // Start timeout
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    2: // ST_RUNNING
      #RunCommand := TRUE;
      #SpeedOutput := #ClampedSpeed / 100.0;
      // Monitor VFD running status
      IF NOT #Running THEN
        #State := #ST_FAULT;
        #ErrorID := 2;  // Unexpected speed deviation / stop
      END_IF;
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    3: // ST_STOPPING
      #RunCommand := FALSE;
      #SpeedOutput := 0.0;
      // Wait for VFD to decelerate
      IF #StateTimer.ET >= T#5s OR NOT #Running THEN
        #State := #ST_IDLE;
      END_IF;

    10: // ST_FAULT
      #RunCommand := FALSE;
      #SpeedOutput := 0.0;
      #Error := TRUE;
      IF #CmdReset AND (#FaultWord AND WORD#16#0008) = WORD#16#0000 THEN
        #ErrorID := 0;
        #State := #ST_IDLE;
      END_IF;

    ELSE
      #State := #ST_FAULT;
      #ErrorID := 99;
  END_CASE;
END_FUNCTION_BLOCK

// =============================================================================
// DB_MotorVFD1 — Instance DB
// =============================================================================
DATA_BLOCK "DB_MotorVFD1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_MotorVFD"
BEGIN
END_DATA_BLOCK
```

### OB1 — Calling All Three Methods

```scl
// =============================================================================
// Main (OB1) — Cyclic program calling all motor starters
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  // --- DOL Motor ---
  "DB_MotorDOL1"(
    CmdStart     := %I0.0,
    CmdStop      := %I0.1,
    CmdReset     := %I0.2,
    OverloadTrip := %I0.3,
    RunFeedback  := %I0.4,
    Contactor    => %Q0.0
  );

  // --- Star-Delta Motor ---
  "DB_MotorSD1"(
    CmdStart       := %I1.0,
    CmdStop        := %I1.1,
    CmdReset       := %I1.2,
    OverloadTrip   := %I1.3,
    RunFeedback    := %I1.4,
    StarTime       := T#6s,
    TransitionTime := T#50ms,
    MainContactor  => %Q1.0,
    StarContactor  => %Q1.1,
    DeltaContactor => %Q1.2
  );

  // --- VFD Motor ---
  "DB_MotorVFD1"(
    CmdStart      := %I2.0,
    CmdStop       := %I2.1,
    CmdReset      := %I2.2,
    SpeedSetpoint := 75.0,
    StatusWord    := %IW10,
    FaultWord     := %IW12,
    RunCommand    => %Q2.0,
    SpeedOutput   => %QD14
  );
END_ORGANIZATION_BLOCK
```

---

## Test Procedure

### 1. Deploy
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

### 2. DOL Motor Test
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

S7ReadVariable(address="DB1.DBW0")     // State (INT)
S7ReadVariable(address="DB1.DBX4.0")   // Running (BOOL)
S7ReadVariable(address="DB1.DBX4.1")   // Error (BOOL)
S7ReadVariable(address="DB1.DBW6")     // ErrorID (INT)

S7Disconnect()
```

**Test sequence**:
1. Set CmdStart -> State 0->1->2, Contactor=TRUE, wait for RunFeedback
2. Set CmdStop -> State 2->3->0, Contactor=FALSE
3. Set OverloadTrip -> State=10, ErrorID=1
4. Set CmdReset (with OverloadTrip cleared) -> State=0

### 3. Star-Delta Motor Test
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

S7ReadVariable(address="DB2.DBW0")     // State (INT)
S7ReadVariable(address="DB2.DBX4.0")   // MainContactor (BOOL)
S7ReadVariable(address="DB2.DBX4.1")   // StarContactor (BOOL)
S7ReadVariable(address="DB2.DBX4.2")   // DeltaContactor (BOOL)
S7ReadVariable(address="DB2.DBX4.3")   // Running (BOOL)
S7ReadVariable(address="DB2.DBX4.4")   // Error (BOOL)
S7ReadVariable(address="DB2.DBW6")     // ErrorID (INT)

S7Disconnect()
```

**Test sequence**:
1. Set CmdStart -> State 0->1 (Star: Main+Star ON, Delta OFF)
2. Wait 6s -> State 1->2 (Transition: Star OFF, Delta OFF, Main ON)
3. Wait 50ms -> State 2->3 (Delta: Main+Delta ON, Star OFF)
4. Verify interlock: StarContactor and DeltaContactor never TRUE simultaneously

### 4. VFD Motor Test
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

S7ReadVariable(address="DB3.DBW0")     // State (INT)
S7ReadVariable(address="DB3.DBX4.0")   // RunCommand (BOOL)
S7ReadVariable(address="DB3.DBD6")     // SpeedOutput (REAL, 0.0-1.0)
S7ReadVariable(address="DB3.DBX10.0")  // Running (BOOL)
S7ReadVariable(address="DB3.DBX10.1")  // AtSpeed (BOOL)
S7ReadVariable(address="DB3.DBX10.2")  // Error (BOOL)
S7ReadVariable(address="DB3.DBW12")    // ErrorID (INT)

S7Disconnect()
```

**Test sequence**:
1. Set CmdStart with SpeedSetpoint=75.0 -> RunCommand=TRUE, SpeedOutput=0.75
2. Simulate VFD status word bit 1 -> Running=TRUE, State goes to Running
3. Set CmdStop -> RunCommand=FALSE, SpeedOutput=0.0
4. Set fault word bit 3 -> State=10, ErrorID=1

## Variations

### S7-1200 Variant
All three methods work on S7-1200 without modification. If using firmware < V4.0,
replace `TON_TIME` with `TON` (IEC timer).

### Star-Delta Closed Transition
Replace the open-transition gap with a resistor-transition variant by adding a
fourth contactor output (TransitionContactor) and modifying state 2 to energize
it during the gap. This reduces current transients.

### VFD with PROFINET
For PROFINET-connected VFDs, replace the WORD-based status/fault with
DPRD_DAT / DPWR_DAT system function calls to read/write the process data directly.
The SpeedOutput would then be written as a 16-bit integer (0-16384 = 0-100%).
