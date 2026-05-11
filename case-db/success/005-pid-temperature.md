# Case 005: PID Temperature Control

## Frontmatter
- **Tags**: pid, temperature, analog, PID_Compact, control, advanced
- **CPU**: 1500
- **Complexity**: Advanced

## Requirements
Control a heater to maintain a setpoint temperature using PID_Compact (S7-1500).
FB_TempController wraps PID_Compact with setpoint, process value from analog input,
manual override mode, at-setpoint detection, and error handling. Configuration DB
stores PID tuning parameters (Kp=2.0, Ti=T#10s, Td=T#1s).

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_TempController | FB | PID wrapper with mode control and diagnostics |
| DB_TempConfig | DB | PID tuning parameters and limits |
| DB_TempCtrl1 | DB | Instance for FB_TempController |
| Main (OB1) | OB | Calls FB_TempController with analog I/O |

## SCL Code
```scl
DATA_BLOCK "DB_TempConfig"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
VAR
  Kp           : REAL := 2.0;
  Ti           : TIME := T#10s;
  Td           : TIME := T#1s;
  OutputMin    : REAL := 0.0;
  OutputMax    : REAL := 100.0;
  SetpointMin  : REAL := 0.0;
  SetpointMax  : REAL := 500.0;
  DeadBand     : REAL := 2.0;       // At-setpoint tolerance (+/- degrees)
  SampleTime   : TIME := T#100ms;   // PID sample time
END_VAR
BEGIN
END_DATA_BLOCK

FUNCTION_BLOCK "FB_TempController"
VERSION : 0.1
VAR_INPUT
  Setpoint       : REAL;           // Target temperature (degrees)
  ProcessValue   : REAL;           // Current temperature from sensor
  ManualMode     : BOOL;           // TRUE = manual output override
  ManualOutput   : REAL;           // Manual output value (0-100%)
  Enable         : BOOL := TRUE;   // Enable PID control
END_VAR
VAR_OUTPUT
  ControlOutput  : REAL;           // Output to heater (0-100%)
  AtSetpoint     : BOOL;           // Process value within deadband
  Error          : BOOL;
  ErrorID        : INT;
END_VAR
VAR
  PID            : PID_Compact;
  State          : INT := 0;       // 0=Init, 1=Auto, 2=Manual, 3=Disabled, 10=Fault
  ClampedSP      : REAL;           // Setpoint after limit check
  ClampedOutput  : REAL;           // Output after clamping
  InitDone       : BOOL;           // PID initialized flag
END_VAR
BEGIN
  #Error := FALSE;
  #ErrorID := 0;

  // Disable handling
  IF NOT #Enable THEN
    #ControlOutput := 0.0;
    #AtSetpoint := FALSE;
    #State := 3;
    RETURN;
  END_IF;

  // Clamp setpoint to configured limits
  #ClampedSP := #Setpoint;
  IF #ClampedSP < "DB_TempConfig".SetpointMin THEN
    #ClampedSP := "DB_TempConfig".SetpointMin;
  END_IF;
  IF #ClampedSP > "DB_TempConfig".SetpointMax THEN
    #ClampedSP := "DB_TempConfig".SetpointMax;
  END_IF;

  // Validate process value (sensor range check)
  IF #ProcessValue < -50.0 OR #ProcessValue > 600.0 THEN
    #Error := TRUE;
    #ErrorID := 1;   // 1 = Sensor out of range
    #ControlOutput := 0.0;
    #AtSetpoint := FALSE;
    #State := 10;
    RETURN;
  END_IF;

  CASE #State OF
    0:  // Init — configure PID on first scan
      #PID.Config.SetpointUpperLimit := "DB_TempConfig".SetpointMax;
      #PID.Config.SetpointLowerLimit := "DB_TempConfig".SetpointMin;
      #PID.Config.OutputUpperLimit := "DB_TempConfig".OutputMax;
      #PID.Config.OutputLowerLimit := "DB_TempConfig".OutputMin;
      #PID.Config.Gain := "DB_TempConfig".Kp;
      #PID.Config.Ti := "DB_TempConfig".Ti;
      #PID.Config.Td := "DB_TempConfig".Td;
      #InitDone := TRUE;
      IF #ManualMode THEN
        #State := 2;
      ELSE
        #State := 1;
      END_IF;

    1:  // Auto mode — PID controls output
      IF #ManualMode THEN
        #State := 2;
      END_IF;
      #PID(Setpoint     := #ClampedSP,
           Input        := #ProcessValue,
           ManualEnable := FALSE,
           ManualValue  := 0.0,
           Reset        := FALSE);
      #ClampedOutput := #PID.Output;

    2:  // Manual mode — operator controls output
      IF NOT #ManualMode THEN
        #State := 1;
      END_IF;
      // Clamp manual output
      #ClampedOutput := #ManualOutput;
      IF #ClampedOutput < "DB_TempConfig".OutputMin THEN
        #ClampedOutput := "DB_TempConfig".OutputMin;
      END_IF;
      IF #ClampedOutput > "DB_TempConfig".OutputMax THEN
        #ClampedOutput := "DB_TempConfig".OutputMax;
      END_IF;
      // Still call PID in manual to keep it tracking
      #PID(Setpoint     := #ClampedSP,
           Input        := #ProcessValue,
           ManualEnable := TRUE,
           ManualValue  := #ClampedOutput,
           Reset        := FALSE);

    3:  // Disabled
      #ClampedOutput := 0.0;
      IF #Enable THEN
        #State := 0;
      END_IF;

    10: // Fault
      #ClampedOutput := 0.0;
      #Error := TRUE;
      // Auto-recover when sensor returns to valid range
      IF #ProcessValue >= -50.0 AND #ProcessValue <= 600.0 THEN
        #State := 0;
      END_IF;

    ELSE
      #State := 10;
      #ErrorID := 99;
  END_CASE;

  // At-setpoint detection with deadband
  IF ABS(#ProcessValue - #ClampedSP) <= "DB_TempConfig".DeadBand THEN
    #AtSetpoint := TRUE;
  ELSE
    #AtSetpoint := FALSE;
  END_IF;

  #ControlOutput := #ClampedOutput;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_TempCtrl1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_TempController"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp       : INT;
  rawAnalog  : INT;
  scaledTemp : REAL;
END_VAR
BEGIN
  // Read analog input (IW64 = channel 0 of analog module)
  // Scale 0-27648 raw → 0-500 degrees
  #rawAnalog := %IW64;
  #scaledTemp := INT_TO_REAL(#rawAnalog) * 500.0 / 27648.0;

  "DB_TempCtrl1"(Setpoint     := 150.0,
                 ProcessValue := #scaledTemp,
                 ManualMode   := %I0.0,
                 ManualOutput := 50.0,
                 Enable       := TRUE);

  // Scale output 0-100% → 0-27648 for analog output
  %QW80 := REAL_TO_INT("DB_TempCtrl1".ControlOutput * 27648.0 / 100.0);
END_ORGANIZATION_BLOCK
```

## MCP Commands Used
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

Note: PID_Compact is a system FB available on S7-1500 — no need for CreateTechObject.
If using the TIA Portal Technology Object wizard instead, use:
```
CreateTechObject(softwarePath="PLC_1/PLC_1", objectName="PID_Compact_1", type="PID_Compact")
```
Then configure via the Technology Object interface rather than SCL Config properties.

## Key Decisions
- PID_Compact (system FB) chosen over manual PID implementation — proven, auto-tunable
- Configuration DB (DB_TempConfig) separate from instance DB — allows runtime tuning
  without modifying code, and multiple controllers can share config
- Sensor range validation (-50 to 600) before PID — prevents integral windup on bad sensor
- Manual mode keeps PID tracking (ManualEnable=TRUE) — bumpless transfer back to auto
- Setpoint clamping — prevents operator from entering dangerous values
- Deadband for AtSetpoint — avoids oscillating TRUE/FALSE at setpoint boundary
- Analog scaling in OB1 (not inside FB) — keeps FB reusable with any input source
- S7_Optimized_Access=FALSE on all DBs for S7.Net runtime monitoring
- DB order: Config DB first (referenced by FB), then FB, then instance DB, then OB

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state
S7ReadVariable(address="DB2.DBW0")    → State (INT, expect 0=Init, then 1=Auto)
S7ReadVariable(address="DB2.DBD10")   → ControlOutput (REAL, expect >0.0 if PV < SP)
S7ReadVariable(address="DB2.DBX14.0") → AtSetpoint (BOOL, expect FALSE initially)
S7ReadVariable(address="DB2.DBX14.1") → Error (BOOL, expect FALSE)

// Read configuration DB
S7ReadVariable(address="DB1.DBD0")    → Kp (REAL, expect 2.0)
S7ReadVariable(address="DB1.DBD4")    → Ti (TIME, T#10s)
S7ReadVariable(address="DB1.DBD8")    → Td (TIME, T#1s)

// Verify PID responds to setpoint change
S7WriteVariable(address="DB2.DBD2", value="200.0", type="Real")  // Change setpoint to 200
// Wait a few scan cycles
S7ReadVariable(address="DB2.DBD10")   → ControlOutput (REAL, should increase if PV < 200)

// Test manual mode
S7WriteVariable(address="%I0.0", value="true", type="Bit")       // Enable manual mode
S7ReadVariable(address="DB2.DBW0")    → State (INT, expect 2=Manual)
S7ReadVariable(address="DB2.DBD10")   → ControlOutput (REAL, expect 50.0 = ManualOutput)

// Return to auto
S7WriteVariable(address="%I0.0", value="false", type="Bit")
S7ReadVariable(address="DB2.DBW0")    → State (INT, expect 1=Auto)

S7Disconnect()
```
