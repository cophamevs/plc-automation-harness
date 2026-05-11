# OSCAT Basic

## Frontmatter
- **Tags**: oscat, open-source, math, string, datetime, building
- **CPU**: Both
- **Source**: https://store.siemens.com (search OSCAT) or oscat.de
- **Version**: V3.33

## Overview
OSCAT Basic is an open-source IEC 61131-3 function block library providing
500+ reusable blocks across multiple domains: mathematical functions, string
manipulation, date/time operations, building automation, signal processing,
astronomy, and network utilities. Community-maintained and free to use, it is
one of the largest openly available PLC libraries in the IEC 61131-3 ecosystem.

OSCAT is not officially supported by Siemens. Evaluate thoroughly before
deploying in production systems.

---

## Installation

1. Download the OSCAT library file (`.zal` format) from
   [Siemens Industry Online Support](https://support.industry.siemens.com)
   (search "OSCAT") or from [oscat.de](http://www.oscat.de).
2. In TIA Portal: **Project > Libraries > Open Global Library** and navigate
   to the downloaded `.zal` file.
3. Expand the OSCAT library in the Libraries panel, then drag-and-drop (or
   copy/paste) the blocks you need into your project library.
4. Only copy blocks you actually use — importing the entire library adds
   significant compile time and memory usage.

---

## Key Function Blocks

| Block | Purpose | Inputs | Outputs |
|-------|---------|--------|---------|
| `SCALE` | Generic scaling with offset and gain | `IN : REAL`, `IN_MIN : REAL`, `IN_MAX : REAL`, `OUT_MIN : REAL`, `OUT_MAX : REAL` | `OUT : REAL` |
| `CTRL_PID` | Alternative PID controller (simpler than PID_Compact) | `ACT : REAL`, `SET : REAL`, `KP : REAL`, `TN : TIME`, `TV : TIME`, `CYCLE : TIME` | `Y : REAL` |
| `FILTER_I` | Integer signal filter (moving average) | `IN : INT`, `N : INT` (window size) | `OUT : INT` |
| `DT_TO_STRING` | Date/time to formatted string conversion | `DT_IN : DT`, `FMT : STRING` | `OUT : STRING` |
| `HOUR_METER` | Operating hours counter | `IN : BOOL`, `RESET : BOOL` | `HOURS : REAL`, `COUNT : DINT` |
| `BLINK` | Blink generator with configurable on/off times | `ENABLE : BOOL`, `T_ON : TIME`, `T_OFF : TIME` | `Q : BOOL` |
| `SEQUENCE` | Step sequencer with configurable timing | `START : BOOL`, `STEPS : INT`, `T_STEP : TIME` | `STEP : INT`, `Q : BOOL` |
| `SUN_POS` | Sun position from GPS coordinates | `LAT : REAL`, `LON : REAL`, `DT_IN : DT`, `UTC_OFFSET : INT` | `AZIMUTH : REAL`, `ELEVATION : REAL` |

---

## Usage Examples

### Example 1 — Scaling an Analog Input

```scl
FUNCTION_BLOCK "FB_ScaleExample"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1

VAR_INPUT
    RawValue : INT;         // Raw analog value (0..27648)
END_VAR

VAR_OUTPUT
    ScaledValue : REAL;     // Engineering units (e.g. 0.0..100.0)
END_VAR

VAR
    ScaleInst : "SCALE";   // OSCAT SCALE instance
END_VAR

BEGIN
    #ScaleInst(IN  := INT_TO_REAL(#RawValue),
               IN_MIN  := 0.0,
               IN_MAX  := 27648.0,
               OUT_MIN := 0.0,
               OUT_MAX := 100.0);

    #ScaledValue := #ScaleInst.OUT;
END_FUNCTION_BLOCK
```

### Example 2 — Operating Hours Counter

```scl
FUNCTION_BLOCK "FB_HourMeterExample"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1

VAR_INPUT
    MotorRunning : BOOL;    // TRUE while motor is on
    ResetCounter : BOOL;    // Pulse to reset hours
END_VAR

VAR_OUTPUT
    TotalHours : REAL;      // Accumulated operating hours
    StartCount : DINT;      // Number of start events
END_VAR

VAR
    HourMeterInst : "HOUR_METER";  // OSCAT HOUR_METER instance
END_VAR

BEGIN
    #HourMeterInst(IN    := #MotorRunning,
                   RESET := #ResetCounter);

    #TotalHours := #HourMeterInst.HOURS;
    #StartCount := #HourMeterInst.COUNT;
END_FUNCTION_BLOCK
```

### Example 3 — Blink Generator for Warning Lamp

```scl
FUNCTION_BLOCK "FB_BlinkExample"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1

VAR_INPUT
    AlarmActive : BOOL;    // Enable blinking when alarm is active
END_VAR

VAR_OUTPUT
    LampOutput : BOOL;     // Blinking output for warning lamp
END_VAR

VAR
    BlinkInst : "BLINK";  // OSCAT BLINK instance
END_VAR

BEGIN
    #BlinkInst(ENABLE := #AlarmActive,
               T_ON  := T#500ms,
               T_OFF := T#500ms);

    #LampOutput := #BlinkInst.Q;
END_FUNCTION_BLOCK
```

---

## Compatibility Notes

- **IEC 61131-3 compliance**: OSCAT is designed to the IEC 61131-3 standard and
  works on both S7-1500 and S7-1200. However, some blocks internally use data
  types (`LREAL`, `LINT`) or features (`VARIANT`, `ARRAY[*]`) that are only
  available on S7-1500. Check the VAR declarations of each block before using
  on S7-1200.
- **TIA Portal versions**: OSCAT V3.33 is compatible with TIA Portal V15 and
  later. Earlier TIA Portal versions may require an older OSCAT release.
- **Optimized DB access**: When using OSCAT blocks with S7.Net runtime access,
  set `{ S7_Optimized_Access := 'FALSE' }` on all instance DBs.
- **Not officially supported**: OSCAT is a community project and is not
  maintained or warranted by Siemens. Use at your own risk in production
  environments. Always validate block behavior against your application
  requirements.
- **Performance**: Some OSCAT blocks (especially astronomy and complex math)
  have higher cycle times than native Siemens instructions. Profile in your
  OB1 scan cycle if using on time-critical applications.
