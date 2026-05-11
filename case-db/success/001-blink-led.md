# Case 001: Blink LED

## Frontmatter
- **Tags**: timer, output, basic, blink, beginner
- **CPU**: Both
- **Complexity**: Beginner

## Requirements
Toggle output Q0.0 every 1 second (1s on, 1s off) creating a visible blink.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_Blink | FB | Toggle logic with TON timer |
| DB_Blink1 | DB | Instance for FB_Blink |
| Main (OB1) | OB | Calls FB_Blink, writes to output |

## SCL Code
```scl
FUNCTION_BLOCK "FB_Blink"
VERSION : 0.1
VAR_INPUT
  Enable   : BOOL := TRUE;
  Interval : TIME := T#1s;
END_VAR
VAR_OUTPUT
  Output   : BOOL;
END_VAR
VAR
  Timer    : TON_TIME;
  State    : BOOL;
END_VAR
BEGIN
  IF NOT #Enable THEN
    #State := FALSE;
    #Output := FALSE;
    #Timer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  #Timer(IN := NOT #State, PT := #Interval);
  IF #Timer.Q THEN
    #State := NOT #State;
    #Timer(IN := FALSE, PT := T#0ms);
  END_IF;
  #Output := #State;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Blink1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_Blink"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_Blink1"(Enable := TRUE, Interval := T#1s);
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
- Used TON with manual reset instead of TP — gives controllable on/off ratio
- Timer in VAR (static) — not VAR_TEMP — to retain state between scans
- Enable input allows runtime control without modifying code
- S7_Optimized_Access=FALSE for S7.Net read access

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")
S7ReadVariable(address="DB1.DBX6.0")  → Output (BOOL, should toggle every 1s)
S7ReadVariable(address="DB1.DBX6.1")  → State (BOOL, internal toggle state)
S7Disconnect()
```
