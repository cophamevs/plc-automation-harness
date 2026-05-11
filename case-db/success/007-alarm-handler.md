# Case 007: Centralized Alarm Handler

## Frontmatter
- **Tags**: alarm, fault, warning, priority, hmi, dword, intermediate
- **CPU**: Both
- **Complexity**: Intermediate

## Requirements
Centralized alarm system handling 8 alarm conditions: OverTemp, OverPress, LowLevel,
HighLevel, MotorFault, CommLoss, DoorOpen, and EStop. Each alarm has an assigned
priority (1=Critical, 2=Warning, 3=Info). OB1 packs alarm condition bits into a DWORD
and calls FB_AlarmHandler. A global DB stores alarm text descriptions for HMI display.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| UDT_Alarm | UDT | Single alarm data structure |
| FB_AlarmHandler | FB | Collects, prioritizes, and manages up to 32 alarms |
| DB_AlarmTexts | DB | Alarm name and priority lookup for HMI |
| DB_Alarms1 | DB | Instance for FB_AlarmHandler |
| Main (OB1) | OB | Packs alarm bits, calls handler |

## SCL Code
```scl
TYPE "UDT_Alarm"
VERSION : 0.1
  STRUCT
    Active          : BOOL;       // Alarm condition currently present
    Latched         : BOOL;       // Alarm was active (needs acknowledge)
    Acknowledged    : BOOL;       // Operator acknowledged
    Priority        : INT;        // 1=Critical, 2=Warning, 3=Info
    ActivationCount : DINT;       // How many times this alarm triggered
  END_STRUCT;
END_TYPE

FUNCTION_BLOCK "FB_AlarmHandler"
TITLE = 'Centralized Alarm Handler for up to 32 alarms'
VERSION : 0.1

VAR_INPUT
  AlarmBits       : DWORD;        // 32 alarm inputs packed as bits
  AckAll          : BOOL;         // Acknowledge all alarms
  ResetAll        : BOOL;         // Reset all latched alarms (if condition cleared)
END_VAR

VAR_OUTPUT
  AnyActive       : BOOL;         // At least one alarm active
  AnyUnacked      : BOOL;         // At least one alarm latched but not acknowledged
  ActiveCount     : INT;          // Number of currently active alarms
  HighestPriority : INT;          // Highest priority among active alarms (1=worst)
  Error           : BOOL;
  ErrorID         : INT;
END_VAR

VAR
  Alarms          : ARRAY[0..31] OF "UDT_Alarm";
END_VAR

VAR_TEMP
  i               : INT;
  bitVal          : BOOL;
  tmpActiveCount  : INT;
  tmpAnyActive    : BOOL;
  tmpAnyUnacked   : BOOL;
  tmpHighPri      : INT;
END_VAR

BEGIN
  #tmpActiveCount := 0;
  #tmpAnyActive := FALSE;
  #tmpAnyUnacked := FALSE;
  #tmpHighPri := 999;
  #Error := FALSE;
  #ErrorID := 0;

  FOR #i := 0 TO 31 DO
    // Extract bit from DWORD
    #bitVal := DWORD_TO_BOOL(SHR(IN := #AlarmBits, N := #i) AND DWORD#1);

    // Rising edge -- alarm just became active
    IF #bitVal AND NOT #Alarms[#i].Active THEN
      #Alarms[#i].ActivationCount := #Alarms[#i].ActivationCount + 1;
      #Alarms[#i].Latched := TRUE;
      #Alarms[#i].Acknowledged := FALSE;
    END_IF;

    #Alarms[#i].Active := #bitVal;

    // Acknowledge
    IF #AckAll AND #Alarms[#i].Latched THEN
      #Alarms[#i].Acknowledged := TRUE;
    END_IF;

    // Reset latched alarm if condition cleared AND acknowledged
    IF #ResetAll AND NOT #Alarms[#i].Active AND #Alarms[#i].Acknowledged THEN
      #Alarms[#i].Latched := FALSE;
      #Alarms[#i].Acknowledged := FALSE;
    END_IF;

    // Aggregate
    IF #Alarms[#i].Active THEN
      #tmpActiveCount := #tmpActiveCount + 1;
      #tmpAnyActive := TRUE;
      IF #Alarms[#i].Priority < #tmpHighPri THEN
        #tmpHighPri := #Alarms[#i].Priority;
      END_IF;
    END_IF;

    IF #Alarms[#i].Latched AND NOT #Alarms[#i].Acknowledged THEN
      #tmpAnyUnacked := TRUE;
    END_IF;
  END_FOR;

  #ActiveCount := #tmpActiveCount;
  #AnyActive := #tmpAnyActive;
  #AnyUnacked := #tmpAnyUnacked;
  IF #tmpHighPri = 999 THEN
    #HighestPriority := 0;
  ELSE
    #HighestPriority := #tmpHighPri;
  END_IF;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_AlarmTexts"
{ S7_Optimized_Access := 'FALSE' }
TITLE = 'Alarm text descriptions and priorities for HMI'
VERSION : 0.1
NON_RETAIN
VAR
  AlarmNames    : ARRAY[0..7] OF STRING[32];
  AlarmPriority : ARRAY[0..7] OF INT;
END_VAR
BEGIN
  // Bit 0: OverTemp
  AlarmNames[0] := 'Over Temperature';
  AlarmPriority[0] := 2;

  // Bit 1: OverPress
  AlarmNames[1] := 'Over Pressure';
  AlarmPriority[1] := 2;

  // Bit 2: LowLevel
  AlarmNames[2] := 'Low Level';
  AlarmPriority[2] := 3;

  // Bit 3: HighLevel
  AlarmNames[3] := 'High Level';
  AlarmPriority[3] := 3;

  // Bit 4: MotorFault
  AlarmNames[4] := 'Motor Fault';
  AlarmPriority[4] := 1;

  // Bit 5: CommLoss
  AlarmNames[5] := 'Communication Loss';
  AlarmPriority[5] := 2;

  // Bit 6: DoorOpen
  AlarmNames[6] := 'Door Open';
  AlarmPriority[6] := 3;

  // Bit 7: EStop
  AlarmNames[7] := 'Emergency Stop';
  AlarmPriority[7] := 1;
END_DATA_BLOCK

DATA_BLOCK "DB_Alarms1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_AlarmHandler"
BEGIN
  // Set priorities to match DB_AlarmTexts configuration
  Alarms[0].Priority := 2;   // OverTemp = Warning
  Alarms[1].Priority := 2;   // OverPress = Warning
  Alarms[2].Priority := 3;   // LowLevel = Info
  Alarms[3].Priority := 3;   // HighLevel = Info
  Alarms[4].Priority := 1;   // MotorFault = Critical
  Alarms[5].Priority := 2;   // CommLoss = Warning
  Alarms[6].Priority := 3;   // DoorOpen = Info
  Alarms[7].Priority := 1;   // EStop = Critical
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp      : INT;
  alarmWord : DWORD;
END_VAR
BEGIN
  // Pack 8 alarm conditions into DWORD bits
  #alarmWord := DWORD#0;
  IF %I0.0 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 0); END_IF;  // OverTemp
  IF %I0.1 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 1); END_IF;  // OverPress
  IF %I0.2 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 2); END_IF;  // LowLevel
  IF %I0.3 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 3); END_IF;  // HighLevel
  IF %I0.4 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 4); END_IF;  // MotorFault
  IF %I0.5 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 5); END_IF;  // CommLoss
  IF %I0.6 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 6); END_IF;  // DoorOpen
  IF %I0.7 THEN #alarmWord := #alarmWord OR SHL(IN := DWORD#1, N := 7); END_IF;  // EStop

  // Call alarm handler
  "DB_Alarms1"(
    AlarmBits := #alarmWord,
    AckAll    := %I1.0,
    ResetAll  := %I1.1
  );

  // Map summary outputs to physical outputs for HMI indication
  %Q0.0 := "DB_Alarms1".AnyActive;    // General alarm lamp
  %Q0.1 := "DB_Alarms1".AnyUnacked;   // Unacknowledged alarm horn
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
- FB_AlarmHandler uses DWORD input for alarm bits -- packs up to 32 alarms into a
  single call, efficient for OB1 to build from individual conditions
- Separate DB_AlarmTexts for HMI -- alarm names and priorities in a global DB that
  HMI can poll directly without parsing the alarm handler instance
- Priority stored in both DB_AlarmTexts and Alarms[].Priority (instance DB BEGIN
  section) -- handler uses instance priority for runtime logic, text DB for display
- Latch-acknowledge-reset pattern -- alarm stays visible after condition clears until
  operator acknowledges, preventing missed transient alarms
- ActivationCount tracks alarm frequency -- useful for predictive maintenance
- Priorities: EStop=1, MotorFault=1 (critical), OverTemp=2, OverPress=2, CommLoss=2
  (warning), LowLevel=3, HighLevel=3, DoorOpen=3 (info)
- HighestPriority output returns 0 when no alarms active (sentinel)
- S7_Optimized_Access=FALSE on all DBs for S7.Net runtime access
- Block order: UDT -> FB -> global DB -> instance DB -> OB

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state -- no alarms
S7ReadVariable(address="DB2.DBX0.0")    -> AnyActive (BOOL, expect FALSE)
S7ReadVariable(address="DB2.DBX0.1")    -> AnyUnacked (BOOL, expect FALSE)
S7ReadVariable(address="DB2.DBW2")      -> ActiveCount (INT, expect 0)
S7ReadVariable(address="DB2.DBW4")      -> HighestPriority (INT, expect 0)

// Trigger OverTemp alarm (bit 0, priority 2)
S7WriteVariable(address="%I0.0", value="true", type="Bit")
S7ReadVariable(address="DB2.DBX0.0")    -> AnyActive (BOOL, expect TRUE)
S7ReadVariable(address="DB2.DBX0.1")    -> AnyUnacked (BOOL, expect TRUE)
S7ReadVariable(address="DB2.DBW2")      -> ActiveCount (INT, expect 1)
S7ReadVariable(address="DB2.DBW4")      -> HighestPriority (INT, expect 2)

// Also trigger EStop (bit 7, priority 1)
S7WriteVariable(address="%I0.7", value="true", type="Bit")
S7ReadVariable(address="DB2.DBW2")      -> ActiveCount (INT, expect 2)
S7ReadVariable(address="DB2.DBW4")      -> HighestPriority (INT, expect 1)

// Acknowledge all
S7WriteVariable(address="%I1.0", value="true", type="Bit")
S7ReadVariable(address="DB2.DBX0.1")    -> AnyUnacked (BOOL, expect FALSE)

// Clear OverTemp condition, then reset
S7WriteVariable(address="%I0.0", value="false", type="Bit")
S7WriteVariable(address="%I1.1", value="true", type="Bit")
S7ReadVariable(address="DB2.DBW2")      -> ActiveCount (INT, expect 1, only EStop remains)

// Verify alarm text DB for HMI
S7ReadVariable(address="DB1.DBW272")    -> AlarmPriority[0] (INT, expect 2 = OverTemp)
S7ReadVariable(address="DB1.DBW286")    -> AlarmPriority[7] (INT, expect 1 = EStop)

S7Disconnect()
```
