# PID Loop Control

## Frontmatter
- **Tags**: pid, temperature, control, tuning, analog, setpoint, PID_Compact, anti-windup
- **CPU**: 1500 (with S7-1200 alternative)
- **Difficulty**: Advanced

## Requirements
PID temperature/process control with:
- Setpoint and process value inputs (REAL)
- Manual/auto mode switching with bumpless transfer
- Output limits (0-100%) for actuator protection
- Configuration DB for tuning parameters (Kp, Ti, Td)
- S7-1500: wrapper around PID_Compact technology object
- S7-1200: custom P+I+D algorithm in SCL with anti-windup

### Physical I/O Assumed
| Signal | Address | Description |
|--------|---------|-------------|
| ProcessValue | IW64 (analog) | Temperature sensor (4-20mA -> 0.0-100.0 degC) |
| ControlOutput | QW80 (analog) | Heater power (0-27648 -> 0-100%) |
| ManualSwitch | I1.0 | Manual/auto selector switch |

---

## Block Structure
| Block | Type | Purpose | Interfaces |
|-------|------|---------|------------|
| FB_PIDController | FB | PID_Compact wrapper with manual mode | SP, PV, ManualMode -> Output, AtSetpoint, Error |
| DB_PIDConfig | DB | Tuning parameters (Kp, Ti, Td, limits) | Global data block |
| DB_PID1 | DB | Instance DB for PID controller 1 | Instance of FB_PIDController |
| FC_ScaleAnalog | FC | Scale raw analog to engineering units | RawValue -> ScaledValue |
| FC_UnscaleAnalog | FC | Scale engineering units to raw analog | ScaledValue -> RawValue |
| Main (OB1) | OB | Reads analog, calls PID, writes output | Maps I/O and config |

---

## SCL Code

### S7-1500: PID_Compact Wrapper

```scl
// =============================================================================
// FC_ScaleAnalog — Scale raw analog input (0..27648) to engineering units
// =============================================================================
FUNCTION "FC_ScaleAnalog" : REAL
VERSION : 0.1
VAR_INPUT
  RawValue    : INT;         // Raw analog value (0..27648 for 4-20mA)
  EngLow      : REAL;        // Engineering low (e.g., 0.0)
  EngHigh     : REAL;        // Engineering high (e.g., 100.0)
  RawLow      : INT := 0;   // Raw low limit
  RawHigh     : INT := 27648; // Raw high limit
END_VAR
VAR_TEMP
  rawRange    : REAL;
  engRange    : REAL;
END_VAR
BEGIN
  #rawRange := INT_TO_REAL(#RawHigh) - INT_TO_REAL(#RawLow);
  #engRange := #EngHigh - #EngLow;

  IF ABS(#rawRange) < 1.0E-10 THEN
    #FC_ScaleAnalog := #EngLow;
    ENO := FALSE;
    RETURN;
  END_IF;

  #FC_ScaleAnalog := (INT_TO_REAL(#RawValue) - INT_TO_REAL(#RawLow))
                     / #rawRange
                     * #engRange
                     + #EngLow;
END_FUNCTION

// =============================================================================
// FC_UnscaleAnalog — Scale engineering units back to raw analog output
// =============================================================================
FUNCTION "FC_UnscaleAnalog" : INT
VERSION : 0.1
VAR_INPUT
  EngValue    : REAL;        // Engineering value (e.g., 75.0%)
  EngLow      : REAL;        // Engineering low (e.g., 0.0)
  EngHigh     : REAL;        // Engineering high (e.g., 100.0)
  RawLow      : INT := 0;   // Raw low limit
  RawHigh     : INT := 27648; // Raw high limit
END_VAR
VAR_TEMP
  engRange    : REAL;
  rawRange    : REAL;
  rawResult   : REAL;
END_VAR
BEGIN
  #engRange := #EngHigh - #EngLow;
  #rawRange := INT_TO_REAL(#RawHigh) - INT_TO_REAL(#RawLow);

  IF ABS(#engRange) < 1.0E-10 THEN
    #FC_UnscaleAnalog := #RawLow;
    ENO := FALSE;
    RETURN;
  END_IF;

  #rawResult := (#EngValue - #EngLow) / #engRange * #rawRange + INT_TO_REAL(#RawLow);

  // Clamp to raw range
  IF #rawResult < INT_TO_REAL(#RawLow) THEN
    #rawResult := INT_TO_REAL(#RawLow);
  END_IF;
  IF #rawResult > INT_TO_REAL(#RawHigh) THEN
    #rawResult := INT_TO_REAL(#RawHigh);
  END_IF;

  #FC_UnscaleAnalog := REAL_TO_INT(#rawResult);
END_FUNCTION

// =============================================================================
// DB_PIDConfig — Tuning parameters (global data block)
// =============================================================================
DATA_BLOCK "DB_PIDConfig"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  VAR
    Kp          : REAL := 2.0;     // Proportional gain
    Ti          : REAL := 10.0;    // Integral time (seconds)
    Td          : REAL := 1.0;     // Derivative time (seconds)
    OutputMin   : REAL := 0.0;     // Output lower limit (%)
    OutputMax   : REAL := 100.0;   // Output upper limit (%)
    DeadBand    : REAL := 0.5;     // Setpoint deadband (engineering units)
    SampleTime  : REAL := 0.1;     // PID sample time (seconds)
  END_VAR
BEGIN
  Kp := 2.0;
  Ti := 10.0;
  Td := 1.0;
  OutputMin := 0.0;
  OutputMax := 100.0;
  DeadBand := 0.5;
  SampleTime := 0.1;
END_DATA_BLOCK

// =============================================================================
// FB_PIDController — PID_Compact wrapper with manual/auto mode
// =============================================================================
// NOTE: This FB wraps the PID_Compact technology object (S7-1500 only).
// PID_Compact must first be created in TIA Portal via:
//   CreateTechObject(softwarePath="PLC_1/PLC_1",
//                    objectName="PID_Compact_1",
//                    objectType="PID_Compact")
// This generates its own instance DB (typically DB assigned automatically).
// The wrapper FB below manages the PID_Compact interface.
// =============================================================================
FUNCTION_BLOCK "FB_PIDController"
TITLE = 'PID_Compact Wrapper with Manual/Auto Mode'
VERSION : 0.1

VAR_INPUT
  Setpoint       : REAL;        // Desired process value
  ProcessValue   : REAL;        // Measured process value
  ManualMode     : BOOL;        // TRUE = manual output control
  ManualOutput   : REAL := 0.0; // Manual output value (0-100%)
  Enable         : BOOL := TRUE; // Enable PID controller
  Kp             : REAL := 2.0; // Proportional gain
  Ti             : REAL := 10.0; // Integral time (seconds)
  Td             : REAL := 1.0;  // Derivative time (seconds)
  OutputMin      : REAL := 0.0;  // Output lower limit
  OutputMax      : REAL := 100.0; // Output upper limit
END_VAR

VAR_OUTPUT
  ControlOutput  : REAL;        // Output to actuator (0-100%)
  AtSetpoint     : BOOL;        // PV within deadband of SP
  Error          : BOOL;        // Fault active
  ErrorID        : INT;         // Error code
END_VAR

VAR
  PID            : PID_Compact; // PID_Compact technology object instance
  PrevManual     : BOOL;        // Previous manual mode for bumpless transfer
  OutputClamped  : REAL;        // Clamped output value
END_VAR

BEGIN
  IF NOT #Enable THEN
    #ControlOutput := 0.0;
    #AtSetpoint := FALSE;
    #Error := FALSE;
    #ErrorID := 0;
    RETURN;
  END_IF;

  // ---- Configure PID parameters ----
  #PID.sRet.i_Mode := 3;  // Mode 3 = Automatic
  IF #ManualMode THEN
    #PID.sRet.i_Mode := 4;  // Mode 4 = Manual
  END_IF;

  // ---- Set tuning parameters ----
  #PID.sConfig.r_Gain := #Kp;
  #PID.sConfig.r_Ti := #Ti;
  #PID.sConfig.r_Td := #Td;
  #PID.sConfig.r_OutputUpperLimit := #OutputMax;
  #PID.sConfig.r_OutputLowerLimit := #OutputMin;

  // ---- Call PID_Compact ----
  #PID(Setpoint       := #Setpoint,
       Input          := #ProcessValue,
       ManualValue    := #ManualOutput,
       ErrorAck       := FALSE);

  // ---- Read outputs ----
  #ControlOutput := #PID.Output;
  #Error := #PID.sRet.i_ErrorBits <> 0;
  IF #Error THEN
    #ErrorID := 1;  // PID internal error
  ELSE
    #ErrorID := 0;
  END_IF;

  // ---- Setpoint deadband check ----
  IF ABS(#ProcessValue - #Setpoint) <= 0.5 THEN
    #AtSetpoint := TRUE;
  ELSE
    #AtSetpoint := FALSE;
  END_IF;

  // ---- Bumpless transfer: on switch from manual to auto ----
  IF #PrevManual AND NOT #ManualMode THEN
    // PID_Compact handles bumpless transfer internally
    // when switching from manual mode back to auto
    ;
  END_IF;
  #PrevManual := #ManualMode;
END_FUNCTION_BLOCK

// =============================================================================
// DB_PID1 — Instance DB for PID controller 1
// =============================================================================
DATA_BLOCK "DB_PID1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_PIDController"
BEGIN
END_DATA_BLOCK

// =============================================================================
// Main (OB1) — Cyclic program
// =============================================================================
ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  scaledPV    : REAL;
  rawOutput   : INT;
  temp        : INT;
END_VAR
BEGIN
  // Scale analog input: 0..27648 -> 0.0..100.0 degrees C
  #scaledPV := "FC_ScaleAnalog"(
    RawValue := %IW64,
    EngLow   := 0.0,
    EngHigh  := 100.0,
    RawLow   := 0,
    RawHigh  := 27648
  );

  // Call PID controller
  "DB_PID1"(
    Setpoint      := 65.0,       // Target temperature
    ProcessValue  := #scaledPV,
    ManualMode    := %I1.0,
    ManualOutput  := 50.0,       // 50% in manual mode
    Enable        := TRUE,
    Kp            := "DB_PIDConfig".Kp,
    Ti            := "DB_PIDConfig".Ti,
    Td            := "DB_PIDConfig".Td,
    OutputMin     := "DB_PIDConfig".OutputMin,
    OutputMax     := "DB_PIDConfig".OutputMax
  );

  // Scale output: 0.0..100.0% -> 0..27648 raw
  #rawOutput := "FC_UnscaleAnalog"(
    EngValue := "DB_PID1".ControlOutput,
    EngLow   := 0.0,
    EngHigh  := 100.0,
    RawLow   := 0,
    RawHigh  := 27648
  );
  %QW80 := INT_TO_WORD(#rawOutput);
END_ORGANIZATION_BLOCK
```

---

### S7-1200 Alternative: Custom PID Algorithm in SCL

S7-1200 does not have PID_Compact. Below is a complete P+I+D implementation
with anti-windup clamping.

```scl
// =============================================================================
// FB_PID_Basic — Manual PID algorithm with anti-windup (S7-1200 compatible)
// =============================================================================
FUNCTION_BLOCK "FB_PID_Basic"
TITLE = 'Basic PID Controller with Anti-Windup'
VERSION : 0.1

VAR_INPUT
  Setpoint       : REAL;        // Desired process value
  ProcessValue   : REAL;        // Measured process value
  ManualMode     : BOOL;        // TRUE = manual output
  ManualOutput   : REAL := 0.0; // Manual output (0-100%)
  Enable         : BOOL := TRUE;
  Kp             : REAL := 2.0; // Proportional gain
  Ti             : REAL := 10.0; // Integral time (seconds), 0=disable integral
  Td             : REAL := 1.0;  // Derivative time (seconds), 0=disable derivative
  SampleTime     : REAL := 0.1;  // Cycle time (seconds)
  OutputMin      : REAL := 0.0;  // Output lower limit
  OutputMax      : REAL := 100.0; // Output upper limit
  DeadBand       : REAL := 0.5;  // Setpoint deadband
END_VAR

VAR_OUTPUT
  ControlOutput  : REAL;        // Output (0-100%)
  AtSetpoint     : BOOL;        // PV within deadband of SP
  Error          : BOOL;        // Fault (invalid config)
  ErrorID        : INT;         // Error code
END_VAR

VAR
  IntegralSum    : REAL := 0.0; // Integral accumulator
  PrevError      : REAL := 0.0; // Previous error for derivative
  PrevPV         : REAL := 0.0; // Previous PV for derivative-on-PV
  Initialized    : BOOL := FALSE;
  OutputRaw      : REAL;        // Unclamped output
END_VAR

BEGIN
  // ---- Validate configuration ----
  IF #Kp < 0.0 OR #SampleTime <= 0.0 THEN
    #Error := TRUE;
    #ErrorID := 1;  // Invalid PID parameters
    #ControlOutput := 0.0;
    RETURN;
  END_IF;
  #Error := FALSE;
  #ErrorID := 0;

  IF NOT #Enable THEN
    #ControlOutput := 0.0;
    #AtSetpoint := FALSE;
    #IntegralSum := 0.0;
    #Initialized := FALSE;
    RETURN;
  END_IF;

  // ---- Manual mode ----
  IF #ManualMode THEN
    #ControlOutput := #ManualOutput;
    // Clamp manual output
    IF #ControlOutput < #OutputMin THEN
      #ControlOutput := #OutputMin;
    END_IF;
    IF #ControlOutput > #OutputMax THEN
      #ControlOutput := #OutputMax;
    END_IF;
    // Track output for bumpless transfer
    #IntegralSum := #ControlOutput / #Kp;
    #PrevError := 0.0;
    #PrevPV := #ProcessValue;
    #Initialized := TRUE;
    #AtSetpoint := ABS(#ProcessValue - #Setpoint) <= #DeadBand;
    RETURN;
  END_IF;

  // ---- Initialize on first run ----
  IF NOT #Initialized THEN
    #PrevError := #Setpoint - #ProcessValue;
    #PrevPV := #ProcessValue;
    #IntegralSum := 0.0;
    #Initialized := TRUE;
  END_IF;

  // ---- PID calculation ----
  // Error = SP - PV
  #OutputRaw := #Setpoint - #ProcessValue;

  // P term
  #ControlOutput := #Kp * #OutputRaw;

  // I term (with anti-windup)
  IF #Ti > 0.0 THEN
    #IntegralSum := #IntegralSum + (#OutputRaw * #SampleTime / #Ti);
    // Anti-windup: clamp integral to output limits
    IF #IntegralSum * #Kp > #OutputMax THEN
      #IntegralSum := #OutputMax / #Kp;
    END_IF;
    IF #IntegralSum * #Kp < #OutputMin THEN
      #IntegralSum := #OutputMin / #Kp;
    END_IF;
    #ControlOutput := #ControlOutput + #Kp * #IntegralSum;
  END_IF;

  // D term (derivative on PV to avoid setpoint kick)
  IF #Td > 0.0 AND #SampleTime > 0.0 THEN
    #ControlOutput := #ControlOutput - #Kp * #Td * (#ProcessValue - #PrevPV) / #SampleTime;
  END_IF;

  #PrevError := #OutputRaw;
  #PrevPV := #ProcessValue;

  // ---- Output clamping ----
  IF #ControlOutput < #OutputMin THEN
    #ControlOutput := #OutputMin;
  END_IF;
  IF #ControlOutput > #OutputMax THEN
    #ControlOutput := #OutputMax;
  END_IF;

  // ---- Setpoint check ----
  #AtSetpoint := ABS(#ProcessValue - #Setpoint) <= #DeadBand;
END_FUNCTION_BLOCK

// =============================================================================
// DB_PID_Basic1 — Instance DB (S7-1200)
// =============================================================================
DATA_BLOCK "DB_PID_Basic1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_PID_Basic"
BEGIN
END_DATA_BLOCK
```

---

## Test Procedure

### 1. Deploy (S7-1500 with PID_Compact)
```
// Step 1: Create PID_Compact technology object
CreateTechObject(softwarePath="PLC_1/PLC_1",
                 objectName="PID_Compact_1",
                 objectType="PID_Compact")

// Step 2: Deploy SCL code
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<S7-1500 SCL above>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

### 2. Deploy (S7-1200 with FB_PID_Basic)
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<S7-1200 SCL above>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

### 3. Verify via S7 Runtime
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Read PID controller outputs
S7ReadVariable(address="DB2.DBD0")     // ControlOutput (REAL, 0.0-100.0)
S7ReadVariable(address="DB2.DBX4.0")   // AtSetpoint (BOOL)
S7ReadVariable(address="DB2.DBX4.1")   // Error (BOOL)
S7ReadVariable(address="DB2.DBW6")     // ErrorID (INT)

// Read configuration
S7ReadVariable(address="DB1.DBD0")     // Kp (REAL)
S7ReadVariable(address="DB1.DBD4")     // Ti (REAL)
S7ReadVariable(address="DB1.DBD8")     // Td (REAL)

// Write new setpoint for testing
S7WriteVariable(address="DB2.DBD10", value=75.0, type="Real")  // Change setpoint

S7Disconnect()
```

### 4. Functional Tests
1. **Auto mode**: Set SP=65.0, observe ControlOutput ramp up as PV is below setpoint
2. **Manual mode**: Switch ManualMode=TRUE, verify output follows ManualOutput
3. **Bumpless transfer**: Switch from manual back to auto, verify no output jump
4. **Anti-windup (S7-1200)**: Set SP=100.0 with OutputMax=100.0, verify IntegralSum does not overflow
5. **Tuning**: Modify Kp in DB_PIDConfig, observe response change in ControlOutput

## Variations

### Cascade PID
Use two FB_PIDController instances: the outer loop (slow) controls setpoint of
the inner loop (fast). Example: outer loop = temperature, inner loop = flow rate.

### Split-Range Output
For heating + cooling control, map output 0-50% to cooling valve and 50-100% to
heating element. Add an FC_SplitRange that takes ControlOutput and produces two
separate outputs.

### PID Autotuning (S7-1500 Only)
PID_Compact supports autotuning modes. Set `PID.sRet.i_Mode := 1` for
pretuning or `PID.sRet.i_Mode := 2` for fine tuning. The controller will
automatically determine optimal Kp, Ti, Td values.
