# Case 008: MODBUS TCP Client

## Frontmatter
- **Tags**: modbus, tcp, communication, mb_client, state-machine, registers, advanced
- **CPU**: Both
- **Complexity**: Advanced

## Requirements
Read 10 holding registers from an external MODBUS TCP device (e.g., power meter) on a
cyclic basis. FB_ModbusReader implements a state machine: Connect, Read, Process, Wait,
and loops back to Read. Raw registers are parsed into meaningful values (Voltage,
Current, Power, Energy). On communication error, retry up to 3 times before setting a
communication fault flag. Connection ID is configured for the target device IP.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_ModbusReader | FB | State machine for cyclic MODBUS register reading |
| DB_ModbusConfig | DB | Connection parameters and polling interval |
| DB_Modbus1 | DB | Instance for FB_ModbusReader |
| Main (OB1) | OB | Calls FB_ModbusReader, maps parsed values to outputs |

## SCL Code
```scl
FUNCTION_BLOCK "FB_ModbusReader"
TITLE = 'Cyclic MODBUS TCP holding register reader with retry'
VERSION : 0.1

VAR_INPUT
  Enable          : BOOL;         // Enable cyclic reading
  ConnID          : WORD;         // TCON connection ID (configured in HW Config)
  UnitID          : BYTE := 1;   // MODBUS unit/slave ID
  StartRegister   : WORD;         // Starting holding register address
  Quantity        : WORD;         // Number of registers to read
  PollInterval    : TIME := T#1s; // Time between read cycles
END_VAR

VAR_OUTPUT
  Voltage         : REAL;         // Parsed: registers 0-1 (32-bit float)
  Current         : REAL;         // Parsed: registers 2-3 (32-bit float)
  Power           : REAL;         // Parsed: registers 4-5 (32-bit float)
  Energy          : REAL;         // Parsed: registers 6-7 (32-bit float)
  StatusWord      : WORD;         // Parsed: register 8
  DeviceID        : WORD;         // Parsed: register 9
  Connected       : BOOL;         // Communication established
  CommFault       : BOOL;         // Communication fault after max retries
  Error           : BOOL;
  ErrorID         : INT;
END_VAR

VAR
  State           : INT := 0;    // 0=Idle, 1=Connect, 2=Read, 3=Process, 4=Wait, 10=Fault
  MbClient        : MB_CLIENT;
  WaitTimer       : TON_TIME;
  RetryCount      : INT := 0;
  RawRegisters    : ARRAY[1..10] OF WORD;
  TempDWord       : DWORD;
END_VAR

VAR CONSTANT
  MAX_RETRIES     : INT := 3;
END_VAR

BEGIN
  #Error := FALSE;
  #ErrorID := 0;

  IF NOT #Enable THEN
    #State := 0;
    #Connected := FALSE;
    #CommFault := FALSE;
    #RetryCount := 0;
    #WaitTimer(IN := FALSE, PT := T#0ms);
    RETURN;
  END_IF;

  CASE #State OF
    0:  // Idle -- start connection when enabled
      #Connected := FALSE;
      #CommFault := FALSE;
      #RetryCount := 0;
      #State := 1;

    1:  // Connect -- initiate MODBUS connection
      // MB_CLIENT handles connection via ConnID (TCON configured in HW Config)
      // Transition to read immediately; MB_CLIENT manages connection internally
      #Connected := TRUE;
      #State := 2;

    2:  // Read -- send read holding registers request
      #MbClient(
        REQ          := TRUE,
        DISCONNECT   := FALSE,
        MB_MODE      := 0,              // 0 = Read holding registers
        MB_DATA_ADDR := WORD_TO_UINT(#StartRegister),
        MB_DATA_LEN  := WORD_TO_UINT(#Quantity),
        MB_DATA_PTR  := #RawRegisters,
        CONNECT      := #ConnID
      );

      IF #MbClient.NDR THEN
        // Read complete successfully
        #RetryCount := 0;
        #State := 3;
      ELSIF #MbClient.ERROR THEN
        // Read failed -- retry or fault
        #RetryCount := #RetryCount + 1;
        IF #RetryCount >= #MAX_RETRIES THEN
          #State := 10;
        ELSE
          // Retry: go back to read state
          #MbClient(REQ := FALSE, DISCONNECT := FALSE, MB_MODE := 0,
                    MB_DATA_ADDR := 0, MB_DATA_LEN := 0,
                    MB_DATA_PTR := #RawRegisters, CONNECT := #ConnID);
          #State := 2;
        END_IF;
      ELSE
        // Busy -- keep calling
        // MB_CLIENT is async, continue calling each scan
      END_IF;

    3:  // Process -- parse raw registers into meaningful values
      // Registers 0-1: Voltage (32-bit float, big-endian word order)
      #TempDWord := SHL(IN := WORD_TO_DWORD(#RawRegisters[1]), N := 16)
                    OR WORD_TO_DWORD(#RawRegisters[2]);
      #Voltage := DWORD_TO_REAL(#TempDWord);

      // Registers 2-3: Current
      #TempDWord := SHL(IN := WORD_TO_DWORD(#RawRegisters[3]), N := 16)
                    OR WORD_TO_DWORD(#RawRegisters[4]);
      #Current := DWORD_TO_REAL(#TempDWord);

      // Registers 4-5: Power
      #TempDWord := SHL(IN := WORD_TO_DWORD(#RawRegisters[5]), N := 16)
                    OR WORD_TO_DWORD(#RawRegisters[6]);
      #Power := DWORD_TO_REAL(#TempDWord);

      // Registers 6-7: Energy
      #TempDWord := SHL(IN := WORD_TO_DWORD(#RawRegisters[7]), N := 16)
                    OR WORD_TO_DWORD(#RawRegisters[8]);
      #Energy := DWORD_TO_REAL(#TempDWord);

      // Register 8: Status word
      #StatusWord := #RawRegisters[9];

      // Register 9: Device ID
      #DeviceID := #RawRegisters[10];

      // Reset MB_CLIENT REQ for next cycle
      #MbClient(REQ := FALSE, DISCONNECT := FALSE, MB_MODE := 0,
                MB_DATA_ADDR := 0, MB_DATA_LEN := 0,
                MB_DATA_PTR := #RawRegisters, CONNECT := #ConnID);

      #WaitTimer(IN := FALSE, PT := T#0ms);
      #State := 4;

    4:  // Wait -- poll interval before next read
      #WaitTimer(IN := TRUE, PT := #PollInterval);
      IF #WaitTimer.Q THEN
        #WaitTimer(IN := FALSE, PT := T#0ms);
        #State := 2;
      END_IF;

    10: // Fault -- communication failure after max retries
      #CommFault := TRUE;
      #Connected := FALSE;
      #Error := TRUE;
      #ErrorID := 1;   // 1 = Communication fault
      // Reset MB_CLIENT
      #MbClient(REQ := FALSE, DISCONNECT := TRUE, MB_MODE := 0,
                MB_DATA_ADDR := 0, MB_DATA_LEN := 0,
                MB_DATA_PTR := #RawRegisters, CONNECT := #ConnID);
      // Auto-recover: if Enable toggled off and on, restart from Idle
      IF NOT #Enable THEN
        #State := 0;
      END_IF;

    ELSE
      #State := 10;
      #ErrorID := 99;
  END_CASE;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_ModbusConfig"
{ S7_Optimized_Access := 'FALSE' }
TITLE = 'MODBUS connection parameters'
VERSION : 0.1
NON_RETAIN
VAR
  ConnID        : WORD := W#16#0001;   // Connection ID from HW Config (TCON)
  UnitID        : BYTE := 1;           // MODBUS slave ID
  StartRegister : WORD := W#16#0000;   // First holding register
  Quantity      : WORD := 10;          // Number of registers to read
  PollInterval  : TIME := T#1s;        // Read cycle interval
END_VAR
BEGIN
END_DATA_BLOCK

DATA_BLOCK "DB_Modbus1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_ModbusReader"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_Modbus1"(
    Enable        := %I0.0,
    ConnID        := "DB_ModbusConfig".ConnID,
    UnitID        := "DB_ModbusConfig".UnitID,
    StartRegister := "DB_ModbusConfig".StartRegister,
    Quantity      := "DB_ModbusConfig".Quantity,
    PollInterval  := "DB_ModbusConfig".PollInterval
  );

  // Comm status to outputs
  %Q0.0 := "DB_Modbus1".Connected;
  %Q0.1 := "DB_Modbus1".CommFault;
END_ORGANIZATION_BLOCK
```

## MCP Commands Used
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

Note: MODBUS TCP requires a TCON connection configured in TIA Portal Hardware
Configuration. The ConnID (e.g., W#16#0001) must match the connection configured
in Network View pointing to the target device IP (e.g., 192.168.0.10, port 502).

## Key Decisions
- State machine pattern for async communication -- MB_CLIENT is asynchronous,
  state machine tracks connection lifecycle (Connect -> Read -> Process -> Wait -> Read)
- 3 retry limit before fault -- prevents infinite retry loops on permanent failures,
  MAX_RETRIES constant makes it easy to adjust
- Separate DB_ModbusConfig for connection parameters -- allows runtime reconfiguration
  without code changes (change register address, poll rate, etc.)
- 32-bit float parsing with big-endian word order -- MODBUS standard for IEEE 754
  floats: high word first, then low word. Some devices use swapped order; adjust
  RawRegisters indexing if needed
- Poll interval via TON timer in Wait state -- prevents hammering the device on every
  scan cycle; configurable from 100ms to minutes
- Fault state auto-recovery via Enable toggle -- operator can reset by cycling Enable
- MB_CLIENT REQ reset between reads -- ensures clean rising edge for next request
- S7_Optimized_Access=FALSE on all DBs for S7.Net access to parsed values
- Block order: FB -> config DB -> instance DB -> OB

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify initial state (Idle before enable)
S7ReadVariable(address="DB2.DBW0")      -> State (INT, expect 0=Idle)
S7ReadVariable(address="DB2.DBX4.0")    -> Connected (BOOL, expect FALSE)
S7ReadVariable(address="DB2.DBX4.1")    -> CommFault (BOOL, expect FALSE)

// Enable MODBUS reading
S7WriteVariable(address="%I0.0", value="true", type="Bit")
// Wait a few scan cycles for connection + first read
S7ReadVariable(address="DB2.DBW0")      -> State (INT, expect cycling 2->3->4->2)
S7ReadVariable(address="DB2.DBX4.0")    -> Connected (BOOL, expect TRUE)

// Read parsed values (actual values depend on connected device)
S7ReadVariable(address="DB2.DBD6")      -> Voltage (REAL)
S7ReadVariable(address="DB2.DBD10")     -> Current (REAL)
S7ReadVariable(address="DB2.DBD14")     -> Power (REAL)
S7ReadVariable(address="DB2.DBD18")     -> Energy (REAL)
S7ReadVariable(address="DB2.DBW22")     -> StatusWord (WORD)
S7ReadVariable(address="DB2.DBW24")     -> DeviceID (WORD)

// Verify configuration DB
S7ReadVariable(address="DB1.DBW0")      -> ConnID (WORD, expect 0x0001)
S7ReadVariable(address="DB1.DBW4")      -> Quantity (WORD, expect 10)

// Test error recovery: disable and re-enable after fault
S7WriteVariable(address="%I0.0", value="false", type="Bit")
S7ReadVariable(address="DB2.DBW0")      -> State (INT, expect 0=Idle)
S7WriteVariable(address="%I0.0", value="true", type="Bit")
S7ReadVariable(address="DB2.DBW0")      -> State (INT, expect cycling again)

S7Disconnect()
```
