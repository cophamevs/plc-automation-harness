# Batch Process Control

## Frontmatter
- **Tags**: batch, isa88, phase, recipe, fill, heat, drain, sequencer, state-machine
- **CPU**: Both
- **Difficulty**: Advanced

## Requirements
ISA-88 inspired 3-phase batch process with:
- **Fill phase**: Open fill valve until level sensor reaches target
- **Heat phase**: PID control to target temperature, hold for specified duration
- **Drain phase**: Open drain valve until vessel is empty (low-level sensor)
- Recipe parameters stored in a global DB
- Generic phase FB reused for each phase with phase-specific logic
- Sequencer FB that orchestrates the phases in order
- State per phase: Idle(0) -> Running(1) -> Hold(2) -> Complete(3) / Aborted(10)

### Physical I/O Assumed
| Signal | Address | Description |
|--------|---------|-------------|
| LevelSensorLow | I0.0 | Tank low level (TRUE = above low) |
| LevelSensorHigh | I0.1 | Tank high level (TRUE = above high) |
| TempSensor | IW64 | Temperature analog input (4-20mA) |
| FillValve | Q0.0 | Fill valve output |
| DrainValve | Q0.1 | Drain valve output |
| HeaterOn | Q0.2 | Heater contactor |
| AgitatorOn | Q0.3 | Agitator motor |

---

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| UDT_BatchRecipe | UDT | Recipe parameters structure | FillLevel, HeatTemp, HeatHoldTime, DrainTimeout |
| UDT_PhaseStatus | UDT | Phase runtime status | State, StateName, Timer, Error, ErrorID |
| FB_BatchPhase | FB | Generic phase controller | Start/Stop/Abort -> Done/Active/Error |
| FB_BatchSequencer | FB | Orchestrates 3 phases in sequence | Start/Stop/Abort -> phases, BatchComplete, Error |
| DB_Recipe | DB | Recipe parameters (global) | FillLevel, HeatTemp, HeatHoldTime, etc. |
| DB_Batch1 | DB | Instance for batch sequencer | Instance of FB_BatchSequencer |
| Main (OB1) | OB | Cyclic call with I/O mapping | Calls FB_BatchSequencer |

---

## SCL Code

```scl
// =============================================================================
// UDT_BatchRecipe — Recipe parameters
// =============================================================================
TYPE "UDT_BatchRecipe"
VERSION : 0.1
  STRUCT
    RecipeName     : STRING[32];  // Recipe description
    FillLevelHigh  : BOOL;        // TRUE = fill to high level, FALSE = fill to low level
    HeatTarget     : REAL;        // Target temperature (engineering units)
    HeatTolerance  : REAL;        // Temperature tolerance for "at setpoint"
    HeatHoldTime   : TIME;        // Hold time at target temperature
    DrainTimeout   : TIME;        // Maximum drain time before fault
    FillTimeout    : TIME;        // Maximum fill time before fault
  END_STRUCT;
END_TYPE

// =============================================================================
// UDT_PhaseStatus — Phase runtime status for HMI
// =============================================================================
TYPE "UDT_PhaseStatus"
VERSION : 0.1
  STRUCT
    State       : INT;         // 0=Idle, 1=Running, 2=Hold, 3=Complete, 10=Aborted
    StateName   : STRING[20];  // State as text
    ElapsedTime : TIME;        // Time in current state
    Error       : BOOL;        // Phase faulted
    ErrorID     : INT;         // Phase error code
  END_STRUCT;
END_TYPE

// =============================================================================
// FB_BatchPhase — Generic batch phase controller
// =============================================================================
FUNCTION_BLOCK "FB_BatchPhase"
TITLE = 'Generic ISA-88 Batch Phase Controller'
VERSION : 0.1

VAR_INPUT
  CmdStart       : BOOL;        // Start this phase
  CmdHold        : BOOL;        // Hold (pause) this phase
  CmdResume      : BOOL;        // Resume from hold
  CmdAbort       : BOOL;        // Abort this phase
  CmdReset       : BOOL;        // Reset from Complete/Aborted to Idle
  PhaseComplete  : BOOL;        // External signal: phase objective achieved
  PhaseFault     : BOOL;        // External signal: phase-specific fault
  Timeout        : TIME := T#60s; // Maximum phase run time
END_VAR

VAR_OUTPUT
  Active         : BOOL;        // Phase is running (or held)
  Done           : BOOL;        // Phase completed successfully
  Held           : BOOL;        // Phase is in hold
  Aborted        : BOOL;        // Phase was aborted
  Error          : BOOL;        // Fault occurred
  ErrorID        : INT;         // 0=none, 1=Timeout, 2=PhaseFault
  Status         : "UDT_PhaseStatus"; // Aggregated status for HMI
END_VAR

VAR
  State          : INT := 0;
  PrevState      : INT := -1;
  StateTimer     : TON_TIME;
  TimeoutTimer   : TON_TIME;
END_VAR

VAR CONSTANT
  ST_IDLE        : INT := 0;
  ST_RUNNING     : INT := 1;
  ST_HOLD        : INT := 2;
  ST_COMPLETE    : INT := 3;
  ST_ABORTED     : INT := 10;
END_VAR

BEGIN
  // ---- Entry action ----
  IF #State <> #PrevState THEN
    #StateTimer(IN := FALSE, PT := T#0ms);
    #TimeoutTimer(IN := FALSE, PT := T#0ms);
    #PrevState := #State;
  END_IF;
  #StateTimer(IN := TRUE, PT := T#24h);

  // ---- Global abort check ----
  IF #CmdAbort AND #State <> #ST_ABORTED AND #State <> #ST_IDLE AND #State <> #ST_COMPLETE THEN
    #State := #ST_ABORTED;
    #ErrorID := 0;  // Operator abort, not a fault
  END_IF;

  // ---- Phase fault check ----
  IF #PhaseFault AND (#State = #ST_RUNNING OR #State = #ST_HOLD) THEN
    #State := #ST_ABORTED;
    #ErrorID := 2;  // Phase-specific fault
  END_IF;

  CASE #State OF
    0: // ST_IDLE
      #Active := FALSE;
      #Done := FALSE;
      #Held := FALSE;
      #Aborted := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      IF #CmdStart THEN
        #State := #ST_RUNNING;
      END_IF;

    1: // ST_RUNNING
      #Active := TRUE;
      #Done := FALSE;
      #Held := FALSE;
      // Timeout check
      #TimeoutTimer(IN := TRUE, PT := #Timeout);
      IF #TimeoutTimer.Q THEN
        #State := #ST_ABORTED;
        #ErrorID := 1;  // Timeout
      END_IF;
      // Phase objective achieved
      IF #PhaseComplete THEN
        #State := #ST_COMPLETE;
      END_IF;
      // Hold request
      IF #CmdHold THEN
        #State := #ST_HOLD;
      END_IF;

    2: // ST_HOLD
      #Active := TRUE;
      #Held := TRUE;
      // Timeout paused during hold (timer not advancing because we entered a new state)
      IF #CmdResume THEN
        #State := #ST_RUNNING;
      END_IF;

    3: // ST_COMPLETE
      #Active := FALSE;
      #Done := TRUE;
      #Held := FALSE;
      IF #CmdReset THEN
        #State := #ST_IDLE;
      END_IF;

    10: // ST_ABORTED
      #Active := FALSE;
      #Done := FALSE;
      #Held := FALSE;
      #Aborted := TRUE;
      IF #ErrorID <> 0 THEN
        #Error := TRUE;
      END_IF;
      IF #CmdReset THEN
        #State := #ST_IDLE;
      END_IF;

    ELSE
      #State := #ST_ABORTED;
      #ErrorID := 99;
  END_CASE;

  // ---- Update status structure ----
  #Status.State := #State;
  #Status.ElapsedTime := #StateTimer.ET;
  #Status.Error := #Error;
  #Status.ErrorID := #ErrorID;

  CASE #State OF
    0:  #Status.StateName := 'Idle';
    1:  #Status.StateName := 'Running';
    2:  #Status.StateName := 'Hold';
    3:  #Status.StateName := 'Complete';
    10: #Status.StateName := 'Aborted';
    ELSE #Status.StateName := 'Unknown';
  END_CASE;
END_FUNCTION_BLOCK

// =============================================================================
// FB_BatchSequencer — Orchestrates 3 batch phases in sequence
// =============================================================================
FUNCTION_BLOCK "FB_BatchSequencer"
TITLE = 'ISA-88 Batch Sequencer: Fill -> Heat -> Drain'
VERSION : 0.1

VAR_INPUT
  CmdStart         : BOOL;        // Start batch
  CmdStop          : BOOL;        // Stop / abort entire batch
  CmdHold          : BOOL;        // Hold current phase
  CmdResume        : BOOL;        // Resume current phase
  CmdReset         : BOOL;        // Reset after complete/abort
  // Sensor inputs
  LevelSensorLow   : BOOL;        // TRUE = above low level
  LevelSensorHigh  : BOOL;        // TRUE = above high level
  Temperature       : REAL;        // Current temperature (scaled)
  // Recipe
  Recipe            : "UDT_BatchRecipe"; // Active recipe parameters
END_VAR

VAR_OUTPUT
  // Actuator outputs
  FillValve         : BOOL;       // Open fill valve
  DrainValve        : BOOL;       // Open drain valve
  HeaterOn          : BOOL;       // Heater contactor
  AgitatorOn        : BOOL;       // Agitator motor
  HeaterOutput      : REAL;       // Heater PID output (0-100%)
  // Status
  BatchState        : INT;        // 0=Idle, 1=Fill, 2=Heat, 3=Drain, 4=Complete, 10=Aborted
  BatchComplete     : BOOL;       // Batch finished successfully
  CurrentPhase      : INT;        // 1=Fill, 2=Heat, 3=Drain
  Error             : BOOL;       // Fault in any phase
  ErrorID           : INT;        // Error code (100+phase*10+phaseError)
  FillStatus        : "UDT_PhaseStatus";  // Fill phase status
  HeatStatus        : "UDT_PhaseStatus";  // Heat phase status
  DrainStatus       : "UDT_PhaseStatus";  // Drain phase status
END_VAR

VAR
  SeqState          : INT := 0;
  PrevSeqState      : INT := -1;
  // Phase instances
  PhaseFill         : "FB_BatchPhase";
  PhaseHeat         : "FB_BatchPhase";
  PhaseDrain        : "FB_BatchPhase";
  // Heat control
  HeatTimer         : TON_TIME;    // Hold time at temperature
  AtTemp            : BOOL;        // Temperature within tolerance
  HeatHoldDone      : BOOL;        // Heat hold time elapsed
  // Simple proportional heater control (substitute for full PID)
  HeatError         : REAL;        // SP - PV
  HeatIntegral      : REAL;        // Integral accumulator
END_VAR

VAR CONSTANT
  SEQ_IDLE          : INT := 0;
  SEQ_FILL          : INT := 1;
  SEQ_HEAT          : INT := 2;
  SEQ_DRAIN         : INT := 3;
  SEQ_COMPLETE      : INT := 4;
  SEQ_ABORTED       : INT := 10;
END_VAR

BEGIN
  // ---- Entry action for sequencer ----
  IF #SeqState <> #PrevSeqState THEN
    #HeatTimer(IN := FALSE, PT := T#0ms);
    #HeatHoldDone := FALSE;
    #HeatIntegral := 0.0;
    #PrevSeqState := #SeqState;
  END_IF;

  // ---- Global stop/abort ----
  IF #CmdStop AND #SeqState <> #SEQ_IDLE AND #SeqState <> #SEQ_COMPLETE AND #SeqState <> #SEQ_ABORTED THEN
    // Abort current active phase
    #PhaseFill(CmdAbort := TRUE, CmdStart := FALSE, CmdHold := FALSE,
               CmdResume := FALSE, CmdReset := FALSE, PhaseComplete := FALSE,
               PhaseFault := FALSE, Timeout := T#0ms);
    #PhaseHeat(CmdAbort := TRUE, CmdStart := FALSE, CmdHold := FALSE,
               CmdResume := FALSE, CmdReset := FALSE, PhaseComplete := FALSE,
               PhaseFault := FALSE, Timeout := T#0ms);
    #PhaseDrain(CmdAbort := TRUE, CmdStart := FALSE, CmdHold := FALSE,
                CmdResume := FALSE, CmdReset := FALSE, PhaseComplete := FALSE,
                PhaseFault := FALSE, Timeout := T#0ms);
    #SeqState := #SEQ_ABORTED;
  END_IF;

  // ---- Default outputs ----
  #FillValve := FALSE;
  #DrainValve := FALSE;
  #HeaterOn := FALSE;
  #AgitatorOn := FALSE;
  #HeaterOutput := 0.0;

  CASE #SeqState OF
    0: // SEQ_IDLE
      #BatchState := 0;
      #BatchComplete := FALSE;
      #CurrentPhase := 0;
      #Error := FALSE;
      #ErrorID := 0;
      IF #CmdStart THEN
        // Reset all phases before starting
        #PhaseFill(CmdReset := TRUE, CmdStart := FALSE, CmdHold := FALSE,
                   CmdResume := FALSE, CmdAbort := FALSE, PhaseComplete := FALSE,
                   PhaseFault := FALSE, Timeout := T#0ms);
        #PhaseHeat(CmdReset := TRUE, CmdStart := FALSE, CmdHold := FALSE,
                   CmdResume := FALSE, CmdAbort := FALSE, PhaseComplete := FALSE,
                   PhaseFault := FALSE, Timeout := T#0ms);
        #PhaseDrain(CmdReset := TRUE, CmdStart := FALSE, CmdHold := FALSE,
                    CmdResume := FALSE, CmdAbort := FALSE, PhaseComplete := FALSE,
                    PhaseFault := FALSE, Timeout := T#0ms);
        #SeqState := #SEQ_FILL;
      END_IF;

    1: // SEQ_FILL — Fill vessel to target level
      #BatchState := 1;
      #CurrentPhase := 1;
      // Determine fill complete condition based on recipe
      IF #Recipe.FillLevelHigh THEN
        // Fill complete: high level sensor reached
        #PhaseFill(CmdStart := TRUE, CmdHold := #CmdHold, CmdResume := #CmdResume,
                   CmdAbort := FALSE, CmdReset := FALSE,
                   PhaseComplete := #LevelSensorHigh,
                   PhaseFault := FALSE,
                   Timeout := #Recipe.FillTimeout);
      ELSE
        // Fill complete: low level sensor reached (partial fill)
        #PhaseFill(CmdStart := TRUE, CmdHold := #CmdHold, CmdResume := #CmdResume,
                   CmdAbort := FALSE, CmdReset := FALSE,
                   PhaseComplete := #LevelSensorLow,
                   PhaseFault := FALSE,
                   Timeout := #Recipe.FillTimeout);
      END_IF;
      // Actuator: open fill valve while phase is active
      #FillValve := #PhaseFill.Active AND NOT #PhaseFill.Held;
      #FillStatus := #PhaseFill.Status;
      // Phase complete -> advance to heat
      IF #PhaseFill.Done THEN
        #SeqState := #SEQ_HEAT;
      END_IF;
      // Phase aborted -> batch aborted
      IF #PhaseFill.Aborted THEN
        #SeqState := #SEQ_ABORTED;
        #ErrorID := 110 + #PhaseFill.ErrorID;  // 110+x = fill phase error
      END_IF;

    2: // SEQ_HEAT — Heat to target temperature and hold
      #BatchState := 2;
      #CurrentPhase := 2;
      // Temperature within tolerance?
      #AtTemp := ABS(#Temperature - #Recipe.HeatTarget) <= #Recipe.HeatTolerance;
      // Hold timer: count hold time once at temperature
      #HeatTimer(IN := #AtTemp, PT := #Recipe.HeatHoldTime);
      #HeatHoldDone := #HeatTimer.Q;
      // Simple proportional + integral heater control
      #HeatError := #Recipe.HeatTarget - #Temperature;
      IF NOT #AtTemp THEN
        #HeatIntegral := #HeatIntegral + #HeatError * 0.01;
        // Anti-windup
        IF #HeatIntegral > 100.0 THEN
          #HeatIntegral := 100.0;
        END_IF;
        IF #HeatIntegral < 0.0 THEN
          #HeatIntegral := 0.0;
        END_IF;
      END_IF;
      #HeaterOutput := 2.0 * #HeatError + #HeatIntegral;
      IF #HeaterOutput < 0.0 THEN
        #HeaterOutput := 0.0;
      END_IF;
      IF #HeaterOutput > 100.0 THEN
        #HeaterOutput := 100.0;
      END_IF;

      #PhaseHeat(CmdStart := TRUE, CmdHold := #CmdHold, CmdResume := #CmdResume,
                 CmdAbort := FALSE, CmdReset := FALSE,
                 PhaseComplete := #HeatHoldDone,
                 PhaseFault := FALSE,
                 Timeout := T#3600s);  // 1 hour max heat time
      // Actuators
      #HeaterOn := #PhaseHeat.Active AND NOT #PhaseHeat.Held AND #HeaterOutput > 0.0;
      #AgitatorOn := #PhaseHeat.Active;  // Agitator runs during entire heat phase
      #HeatStatus := #PhaseHeat.Status;
      // Phase complete -> advance to drain
      IF #PhaseHeat.Done THEN
        #SeqState := #SEQ_DRAIN;
      END_IF;
      IF #PhaseHeat.Aborted THEN
        #SeqState := #SEQ_ABORTED;
        #ErrorID := 120 + #PhaseHeat.ErrorID;  // 120+x = heat phase error
      END_IF;

    3: // SEQ_DRAIN — Drain vessel until empty
      #BatchState := 3;
      #CurrentPhase := 3;
      // Drain complete: low level sensor goes FALSE (below low level = empty)
      #PhaseDrain(CmdStart := TRUE, CmdHold := #CmdHold, CmdResume := #CmdResume,
                  CmdAbort := FALSE, CmdReset := FALSE,
                  PhaseComplete := NOT #LevelSensorLow,
                  PhaseFault := FALSE,
                  Timeout := #Recipe.DrainTimeout);
      // Actuator: open drain valve while phase is active
      #DrainValve := #PhaseDrain.Active AND NOT #PhaseDrain.Held;
      #DrainStatus := #PhaseDrain.Status;
      // Phase complete -> batch complete
      IF #PhaseDrain.Done THEN
        #SeqState := #SEQ_COMPLETE;
      END_IF;
      IF #PhaseDrain.Aborted THEN
        #SeqState := #SEQ_ABORTED;
        #ErrorID := 130 + #PhaseDrain.ErrorID;  // 130+x = drain phase error
      END_IF;

    4: // SEQ_COMPLETE
      #BatchState := 4;
      #BatchComplete := TRUE;
      #CurrentPhase := 0;
      IF #CmdReset THEN
        #SeqState := #SEQ_IDLE;
      END_IF;

    10: // SEQ_ABORTED
      #BatchState := 10;
      #BatchComplete := FALSE;
      #Error := TRUE;
      // All actuators OFF (already set to FALSE above)
      IF #CmdReset THEN
        #ErrorID := 0;
        #SeqState := #SEQ_IDLE;
      END_IF;

    ELSE
      #SeqState := #SEQ_ABORTED;
      #ErrorID := 199;
  END_CASE;
END_FUNCTION_BLOCK

// =============================================================================
// DB_Recipe — Recipe parameters (global data block)
// =============================================================================
DATA_BLOCK "DB_Recipe"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  VAR
    ActiveRecipe : "UDT_BatchRecipe";
  END_VAR
BEGIN
  ActiveRecipe.RecipeName := 'Default Recipe';
  ActiveRecipe.FillLevelHigh := TRUE;
  ActiveRecipe.HeatTarget := 75.0;
  ActiveRecipe.HeatTolerance := 2.0;
  ActiveRecipe.HeatHoldTime := T#300s;
  ActiveRecipe.DrainTimeout := T#120s;
  ActiveRecipe.FillTimeout := T#60s;
END_DATA_BLOCK

// =============================================================================
// DB_Batch1 — Instance DB for batch sequencer
// =============================================================================
DATA_BLOCK "DB_Batch1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_BatchSequencer"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  scaledTemp : REAL;
  temp       : INT;
END_VAR
BEGIN
  // Scale temperature analog input: 0..27648 -> 0.0..150.0 degrees C
  IF %IW64 < 0 THEN
    #scaledTemp := 0.0;
  ELSE
    #scaledTemp := INT_TO_REAL(%IW64) / 27648.0 * 150.0;
  END_IF;

  // Call batch sequencer
  "DB_Batch1"(
    CmdStart        := %I1.0,
    CmdStop         := %I1.1,
    CmdHold         := %I1.2,
    CmdResume       := %I1.3,
    CmdReset        := %I1.4,
    LevelSensorLow  := %I0.0,
    LevelSensorHigh := %I0.1,
    Temperature     := #scaledTemp,
    Recipe          := "DB_Recipe".ActiveRecipe,
    FillValve       => %Q0.0,
    DrainValve      => %Q0.1,
    HeaterOn        => %Q0.2,
    AgitatorOn      => %Q0.3
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

### 2. Verify via S7 Runtime
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Read batch sequencer status
S7ReadVariable(address="DB2.DBW0")     // BatchState (INT): 0=Idle,1=Fill,2=Heat,3=Drain,4=Complete,10=Aborted
S7ReadVariable(address="DB2.DBX2.0")   // BatchComplete (BOOL)
S7ReadVariable(address="DB2.DBW4")     // CurrentPhase (INT): 1=Fill, 2=Heat, 3=Drain
S7ReadVariable(address="DB2.DBX6.0")   // Error (BOOL)
S7ReadVariable(address="DB2.DBW8")     // ErrorID (INT)

// Read actuator outputs
S7ReadVariable(address="DB2.DBX10.0")  // FillValve (BOOL)
S7ReadVariable(address="DB2.DBX10.1")  // DrainValve (BOOL)
S7ReadVariable(address="DB2.DBX10.2")  // HeaterOn (BOOL)
S7ReadVariable(address="DB2.DBX10.3")  // AgitatorOn (BOOL)
S7ReadVariable(address="DB2.DBD12")    // HeaterOutput (REAL, 0-100%)

// Read recipe parameters
S7ReadVariable(address="DB1.DBD36")    // HeatTarget (REAL)
S7ReadVariable(address="DB1.DBD40")    // HeatTolerance (REAL)

// Write recipe change for testing
S7WriteVariable(address="DB1.DBD36", value=80.0, type="Real")  // Change heat target

S7Disconnect()
```

### 3. Functional Tests
1. **Normal batch cycle**: Start batch -> observe Fill (valve open) -> Heat (heater on, agitator on) -> Drain (drain valve open) -> Complete
2. **Fill phase**: Verify FillValve=TRUE until LevelSensorHigh=TRUE, then phase advances
3. **Heat phase**: Verify heater modulates toward target, hold timer starts when within tolerance
4. **Drain phase**: Verify DrainValve=TRUE until LevelSensorLow=FALSE (tank empty)
5. **Hold/Resume**: During any phase, set CmdHold -> actuators pause; CmdResume -> continue
6. **Abort**: Set CmdStop -> all actuators OFF, BatchState=10
7. **Timeout**: If fill takes longer than FillTimeout -> phase aborts, ErrorID=111

### 4. Recipe Modification Test
```
// Change recipe to partial fill, higher temperature
S7WriteVariable(address="DB1.DBX34.0", value=false, type="Bool")  // FillLevelHigh=FALSE
S7WriteVariable(address="DB1.DBD36", value=90.0, type="Real")     // HeatTarget=90.0
S7WriteVariable(address="DB1.DBD44", value=T#600s, type="Time")   // HeatHoldTime=600s
```

## Variations

### S7-1200 Variant
The code is fully compatible with S7-1200. No S7-1500-specific features are used.

### Multiple Recipes
Extend DB_Recipe to hold an array of recipes:
```scl
DATA_BLOCK "DB_Recipes"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  VAR
    Recipes      : ARRAY[0..9] OF "UDT_BatchRecipe";
    ActiveIndex  : INT := 0;
  END_VAR
BEGIN
END_DATA_BLOCK
```
Load the active recipe before starting the batch:
`"DB_Recipe".ActiveRecipe := "DB_Recipes".Recipes["DB_Recipes".ActiveIndex];`

### CIP (Clean-In-Place) Phase
Add a fourth phase after Drain: CIP rinse cycle that fills with cleaning solution,
circulates for a timed duration, then drains. Reuse FB_BatchPhase with a different
completion condition (timed rather than level-based).

### Multi-Vessel Batching
Create multiple DB_Batch instances and a master scheduler FB that assigns recipes
to available vessels, enabling parallel batch execution across multiple tanks.

### Alarm Integration
Connect phase Error/ErrorID outputs to the alarm management pattern
(`knowledge/patterns/alarm-management.md`) for centralized alarm handling and
HMI alarm display.
