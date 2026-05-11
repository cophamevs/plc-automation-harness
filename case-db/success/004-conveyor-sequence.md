# Case 004: Multi-Section Conveyor Sequence

## Frontmatter
- **Tags**: conveyor, multi-fb, sequence, state-machine, sensor, intermediate
- **CPU**: Both
- **Complexity**: Intermediate

## Requirements
Control 3 conveyor sections in sequence. Start section 1, wait for product at transfer
point sensor, start section 2, wait for next sensor, start section 3. Master FB
orchestrates the 3 sections. Each section has Run/Stop control, a motor output, and a
product-present sensor at the discharge end.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_Conveyor | FB | Single conveyor section control |
| FB_ConveyorLine | FB | Master orchestrator for 3 sections |
| DB_ConveyorLine1 | DB | Instance for FB_ConveyorLine |
| Main (OB1) | OB | Calls FB_ConveyorLine with I/O mapping |

## SCL Code
```scl
FUNCTION_BLOCK "FB_Conveyor"
VERSION : 0.1
VAR_INPUT
  RunCmd         : BOOL;          // Command to run this section
  StopCmd        : BOOL;          // Command to stop this section
  SensorPresent  : BOOL;          // Product-present sensor at discharge end
  EStopActive    : BOOL;          // Emergency stop
END_VAR
VAR_OUTPUT
  MotorOn        : BOOL;          // Motor contactor output
  ProductAtEnd   : BOOL;          // Product detected at discharge
  Running        : BOOL;          // Section is running
  Error          : BOOL;
  ErrorID        : INT;
END_VAR
VAR
  State          : INT := 0;      // 0=Stopped, 1=Running, 2=Fault
  JamTimer       : TON_TIME;      // Jam detection: motor on but no product for too long
END_VAR
BEGIN
  // E-Stop overrides everything
  IF #EStopActive THEN
    #MotorOn := FALSE;
    #Running := FALSE;
    #Error := TRUE;
    #ErrorID := 1;  // 1 = E-Stop
    #State := 2;
    RETURN;
  END_IF;

  #ProductAtEnd := #SensorPresent;

  CASE #State OF
    0:  // Stopped
      #MotorOn := FALSE;
      #Running := FALSE;
      #Error := FALSE;
      #ErrorID := 0;
      #JamTimer(IN := FALSE, PT := T#0ms);
      IF #RunCmd AND NOT #StopCmd THEN
        #State := 1;
      END_IF;

    1:  // Running
      #MotorOn := TRUE;
      #Running := TRUE;
      // Jam detection: if running for 60s without product at sensor, fault
      #JamTimer(IN := NOT #SensorPresent, PT := T#60s);
      IF #JamTimer.Q THEN
        #JamTimer(IN := FALSE, PT := T#0ms);
        #State := 2;
        #ErrorID := 2;  // 2 = Jam timeout
      END_IF;
      IF #StopCmd THEN
        #JamTimer(IN := FALSE, PT := T#0ms);
        #State := 0;
      END_IF;

    2:  // Fault
      #MotorOn := FALSE;
      #Running := FALSE;
      #Error := TRUE;
      // Reset by removing E-Stop and issuing RunCmd
      IF NOT #EStopActive AND #RunCmd THEN
        #Error := FALSE;
        #ErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      #State := 2;
      #ErrorID := 99;
  END_CASE;
END_FUNCTION_BLOCK

FUNCTION_BLOCK "FB_ConveyorLine"
VERSION : 0.1
VAR_INPUT
  StartLine      : BOOL;          // Start the whole conveyor line
  StopLine       : BOOL;          // Stop the whole conveyor line
  Sensor1        : BOOL;          // Product sensor at end of section 1
  Sensor2        : BOOL;          // Product sensor at end of section 2
  Sensor3        : BOOL;          // Product sensor at end of section 3
  EStop          : BOOL;          // Emergency stop for all sections
END_VAR
VAR_OUTPUT
  Motor1         : BOOL;          // Section 1 motor output
  Motor2         : BOOL;          // Section 2 motor output
  Motor3         : BOOL;          // Section 3 motor output
  LineRunning    : BOOL;          // At least one section active
  Error          : BOOL;
  ErrorID        : INT;
END_VAR
VAR
  State          : INT := 0;      // 0=Idle, 1=StartSec1, 2=WaitTransfer1, 3=StartSec2, 4=WaitTransfer2, 5=StartSec3, 6=AllRunning, 10=Fault
  Section1       : "FB_Conveyor";
  Section2       : "FB_Conveyor";
  Section3       : "FB_Conveyor";
  TransferDelay  : TON_TIME;      // Brief delay between section starts
END_VAR
BEGIN
  // E-Stop handling
  IF #EStop AND #State <> 10 THEN
    #State := 10;
    #ErrorID := 1;
  END_IF;

  CASE #State OF
    0:  // Idle — all stopped
      #Section1(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor3, EStopActive := #EStop);
      #Error := FALSE;
      #ErrorID := 0;
      IF #StartLine AND NOT #StopLine THEN
        #State := 1;
      END_IF;

    1:  // Start section 1
      #Section1(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor3, EStopActive := #EStop);
      IF #Section1.Running THEN
        #State := 2;
      END_IF;

    2:  // Wait for product at end of section 1
      #Section1(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor3, EStopActive := #EStop);
      IF #Section1.ProductAtEnd THEN
        #TransferDelay(IN := TRUE, PT := T#500ms);
        IF #TransferDelay.Q THEN
          #TransferDelay(IN := FALSE, PT := T#0ms);
          #State := 3;
        END_IF;
      ELSE
        #TransferDelay(IN := FALSE, PT := T#0ms);
      END_IF;

    3:  // Start section 2 (section 1 still running)
      #Section1(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor3, EStopActive := #EStop);
      IF #Section2.Running THEN
        #State := 4;
      END_IF;

    4:  // Wait for product at end of section 2
      #Section1(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor3, EStopActive := #EStop);
      IF #Section2.ProductAtEnd THEN
        #TransferDelay(IN := TRUE, PT := T#500ms);
        IF #TransferDelay.Q THEN
          #TransferDelay(IN := FALSE, PT := T#0ms);
          #State := 5;
        END_IF;
      ELSE
        #TransferDelay(IN := FALSE, PT := T#0ms);
      END_IF;

    5:  // Start section 3 (all sections running)
      #Section1(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor3, EStopActive := #EStop);
      IF #Section3.Running THEN
        #State := 6;
      END_IF;

    6:  // All running — normal operation
      #Section1(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := TRUE, StopCmd := FALSE, SensorPresent := #Sensor3, EStopActive := #EStop);
      // Check for section errors
      IF #Section1.Error OR #Section2.Error OR #Section3.Error THEN
        #State := 10;
        #ErrorID := 2;  // 2 = Section fault
      END_IF;

    10: // Fault — stop all
      #Section1(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor1, EStopActive := #EStop);
      #Section2(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor2, EStopActive := #EStop);
      #Section3(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor3, EStopActive := #EStop);
      #Error := TRUE;
      // Reset when E-Stop cleared and StartLine re-asserted
      IF NOT #EStop AND #StartLine THEN
        #Error := FALSE;
        #ErrorID := 0;
        #State := 0;
      END_IF;

    ELSE
      #State := 10;
      #ErrorID := 99;
  END_CASE;

  // Stop command from any running state
  IF #StopLine AND #State >= 1 AND #State <= 6 THEN
    #Section1(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor1, EStopActive := #EStop);
    #Section2(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor2, EStopActive := #EStop);
    #Section3(RunCmd := FALSE, StopCmd := TRUE, SensorPresent := #Sensor3, EStopActive := #EStop);
    #State := 0;
  END_IF;

  // Aggregate outputs
  #Motor1 := #Section1.MotorOn;
  #Motor2 := #Section2.MotorOn;
  #Motor3 := #Section3.MotorOn;
  #LineRunning := #Section1.Running OR #Section2.Running OR #Section3.Running;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_ConveyorLine1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_ConveyorLine"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_ConveyorLine1"(StartLine := %I0.0,
                     StopLine  := %I0.1,
                     Sensor1   := %I0.2,
                     Sensor2   := %I0.3,
                     Sensor3   := %I0.4,
                     EStop     := %I0.5);
  %Q0.0 := "DB_ConveyorLine1".Motor1;
  %Q0.1 := "DB_ConveyorLine1".Motor2;
  %Q0.2 := "DB_ConveyorLine1".Motor3;
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
- Two-level FB architecture: FB_Conveyor (reusable section) + FB_ConveyorLine (orchestrator)
  — each section is independently testable, orchestrator handles sequencing
- Sequential startup: sections start one at a time as product reaches transfer points
  — prevents running empty conveyors and wasting energy
- Transfer delay (500ms) between detecting product and starting next section
  — ensures product is stable at transfer point before next belt moves
- Jam detection timer (60s) in each section — catches stuck product or broken sensor
- E-Stop propagated to all sections via FB_Conveyor EStopActive input
- StopLine checked after CASE to override any running state immediately
- S7_Optimized_Access=FALSE for S7.Net runtime access to all instance data

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state (Idle)
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 0=Idle)
S7ReadVariable(address="DB1.DBX60.0") → Motor1 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX60.1") → Motor2 (BOOL, expect FALSE)
S7ReadVariable(address="DB1.DBX60.2") → Motor3 (BOOL, expect FALSE)

// Start line
S7WriteVariable(address="%I0.0", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 1 then 2)
S7ReadVariable(address="DB1.DBX60.0") → Motor1 (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX60.1") → Motor2 (BOOL, expect FALSE — waiting)

// Simulate product at sensor 1
S7WriteVariable(address="%I0.2", value="true", type="Bit")
// Wait 500ms transfer delay
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 3 then 4)
S7ReadVariable(address="DB1.DBX60.1") → Motor2 (BOOL, expect TRUE)

// Simulate product at sensor 2
S7WriteVariable(address="%I0.3", value="true", type="Bit")
// Wait 500ms transfer delay
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 5 then 6=AllRunning)
S7ReadVariable(address="DB1.DBX60.2") → Motor3 (BOOL, expect TRUE)
S7ReadVariable(address="DB1.DBX60.3") → LineRunning (BOOL, expect TRUE)

// Stop line
S7WriteVariable(address="%I0.1", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 0=Idle)

// Test E-Stop
S7WriteVariable(address="%I0.5", value="true", type="Bit")
S7ReadVariable(address="DB1.DBW0")    → State (INT, expect 10=Fault)
S7ReadVariable(address="DB1.DBX60.4") → Error (BOOL, expect TRUE)

S7Disconnect()
```
