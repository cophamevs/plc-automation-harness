# LGF — Library of General Functions

## Frontmatter
- **Tags**: lgf, siemens, utility, general, library
- **CPU**: Both
- **Source**: Shipped with TIA Portal V16+
- **Version**: V6.0+

## Overview
The Siemens Library of General Functions (LGF) is a standardized collection of
approximately 100 FBs and FCs that ships with TIA Portal. It provides
ready-to-use blocks for common automation tasks, eliminating the need to write
boilerplate logic from scratch.

Categories covered:
- **Pulse generators** — configurable pulse/clock signals with duty cycle
- **Edge detection** — rising/falling edge with pulse output
- **Multiplexers** — select one of N inputs by index
- **Comparators** — hysteresis, window, threshold comparisons
- **Data manipulation** — sorting, searching, shifting, FIFO/LIFO
- **Signal conditioning** — debouncing, filtering, ramp limiting
- **Arithmetic** — min/max, averaging, integration
- **Conversion** — scaling, unit conversion, format transforms

All blocks follow Siemens naming conventions (`LGF_` prefix) and include
built-in error handling with `Error` and `Status` outputs.

## Installation
LGF is already included in TIA Portal V16 and later. No separate download is
required.

**To add blocks to your project:**
1. Open TIA Portal and load your project
2. In the Project tree, navigate to **Libraries** (right sidebar)
3. Under **Global libraries**, expand **Library of General Functions**
4. Browse categories or search for the block you need
5. Drag the block into your project's **Program blocks** folder, or
   right-click and select **Add to project**

Alternatively, add a library reference via **Project > Libraries > Open global
library** so blocks are linked rather than copied.

## Key Function Blocks
| Block | Purpose | Inputs | Outputs |
|-------|---------|--------|---------|
| `LGF_PulseGenerator` | Configurable pulse generator with adjustable duty cycle | `Enable : BOOL`, `PulseTime : TIME`, `PauseTime : TIME` | `Q : BOOL`, `Error : BOOL`, `Status : WORD` |
| `LGF_RampFunction` | Linear ramp with configurable rate for smooth transitions | `Enable : BOOL`, `SetValue : REAL`, `RampUpTime : TIME`, `RampDownTime : TIME` | `OutValue : REAL`, `RampActive : BOOL`, `Error : BOOL` |
| `LGF_Limiter` | Clamp a value between min and max limits | `InputValue : REAL`, `MinValue : REAL`, `MaxValue : REAL` | `OutputValue : REAL`, `LimitActive : BOOL` |
| `LGF_ScaleLinear` | Linear scaling from raw range to engineering units | `InputValue : REAL`, `InMin : REAL`, `InMax : REAL`, `OutMin : REAL`, `OutMax : REAL` | `OutputValue : REAL`, `Error : BOOL` |
| `LGF_EdgeDetection` | Rising/falling edge detection with configurable pulse | `SignalIn : BOOL`, `Mode : INT` | `Q : BOOL`, `RisingEdge : BOOL`, `FallingEdge : BOOL` |
| `LGF_MultiplexerInt` | Select one of N integer inputs by index | `Selector : INT`, `In0..InN : INT` | `Output : INT`, `Error : BOOL` |
| `LGF_Debounce` | Signal debouncing with configurable delay time | `SignalIn : BOOL`, `DebounceTime : TIME` | `SignalOut : BOOL`, `Error : BOOL` |
| `LGF_Hysteresis` | Hysteresis comparator with high/low thresholds | `InputValue : REAL`, `HighLimit : REAL`, `LowLimit : REAL` | `Q : BOOL`, `Error : BOOL` |

## Usage Examples

### Example 1: Scaling an Analog Input (0-27648 to 0.0-100.0%)

Scale a raw analog input value from the S7 standard range (0-27648) to an
engineering percentage (0.0-100.0%).

```scl
FUNCTION_BLOCK "FB_AnalogScaling"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1

VAR_INPUT
    RawAnalogValue : INT;       // Raw value from analog input (0-27648)
END_VAR

VAR_OUTPUT
    ScaledPercent : REAL;       // Scaled output in percent (0.0-100.0)
    ScaleError : BOOL;          // Error flag from scaling block
END_VAR

VAR
    ScaleInst : "LGF_ScaleLinear";  // Instance of LGF scaling block
END_VAR

BEGIN
    // Call the LGF scaling function block
    #ScaleInst(InputValue := INT_TO_REAL(#RawAnalogValue),
               InMin     := 0.0,
               InMax     := 27648.0,
               OutMin    := 0.0,
               OutMax    := 100.0);

    #ScaledPercent := #ScaleInst.OutputValue;
    #ScaleError   := #ScaleInst.Error;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_AnalogScaling"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
    "FB_AnalogScaling"
BEGIN
END_DATA_BLOCK
```

### Example 2: Debouncing a Pushbutton Input

Filter a noisy pushbutton signal with a 50 ms debounce time to prevent
false triggers.

```scl
FUNCTION_BLOCK "FB_ButtonHandler"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1

VAR_INPUT
    RawButton : BOOL;          // Raw pushbutton signal (noisy)
END_VAR

VAR_OUTPUT
    CleanButton : BOOL;        // Debounced button output
    ButtonError : BOOL;        // Error flag
END_VAR

VAR
    DebounceInst : "LGF_Debounce";  // Instance of LGF debounce block
END_VAR

BEGIN
    // Debounce the raw button signal with 50 ms filter time
    #DebounceInst(SignalIn     := #RawButton,
                  DebounceTime := T#50ms);

    #CleanButton := #DebounceInst.SignalOut;
    #ButtonError := #DebounceInst.Error;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_ButtonHandler"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
    "FB_ButtonHandler"
BEGIN
END_DATA_BLOCK
```

### Example 3: Ramping a Speed Setpoint

Smoothly ramp a motor speed setpoint from the current value to a target
value, with separate ramp-up and ramp-down rates to prevent mechanical shock.

```scl
FUNCTION_BLOCK "FB_SpeedRamp"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1

VAR_INPUT
    Enable : BOOL;             // Enable ramp function
    TargetSpeed : REAL;        // Desired speed setpoint (RPM)
END_VAR

VAR_OUTPUT
    CurrentSpeed : REAL;       // Ramped output speed (RPM)
    Ramping : BOOL;            // TRUE while ramp is active
    RampError : BOOL;          // Error flag
END_VAR

VAR
    RampInst : "LGF_RampFunction";  // Instance of LGF ramp block
END_VAR

BEGIN
    // Ramp the speed setpoint: 5 seconds up, 3 seconds down
    #RampInst(Enable       := #Enable,
              SetValue     := #TargetSpeed,
              RampUpTime   := T#5s,
              RampDownTime := T#3s);

    #CurrentSpeed := #RampInst.OutValue;
    #Ramping      := #RampInst.RampActive;
    #RampError    := #RampInst.Error;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_SpeedRamp"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
    "FB_SpeedRamp"
BEGIN
END_DATA_BLOCK
```

## Compatibility Notes
- **TIA Portal version**: LGF is available from TIA Portal V16 onward.
  Earlier versions do not include this library.
- **S7-1200 and S7-1500**: Most LGF blocks work on both CPU families.
  Blocks that use only standard data types (BOOL, INT, REAL, TIME) are
  fully compatible with S7-1200.
- **S7-1500 only**: Some advanced LGF blocks use the `VARIANT` data type
  for generic interfaces. These blocks are restricted to S7-1500, since
  S7-1200 does not support `VARIANT`. Check the block documentation in
  TIA Portal for the "CPU compatibility" indicator.
- **Firmware**: Certain newer LGF blocks may require minimum firmware
  versions. Consult the library release notes in TIA Portal Help for
  specific firmware requirements.
- **Optimized vs. standard access**: LGF blocks work with both optimized
  and standard DB access modes. When using S7.Net for runtime access,
  set `{ S7_Optimized_Access := 'FALSE' }` on your instance DBs.
