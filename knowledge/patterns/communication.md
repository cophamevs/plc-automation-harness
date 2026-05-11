# Communication Patterns

## Frontmatter
- **Tags**: comm, tcp, modbus, putget, ouc, s7, send, receive
- **CPU**: Both
- **Difficulty**: Advanced

## Problem
PLCs frequently need to communicate with other PLCs, HMIs, SCADA systems,
or external devices via various protocols.

## Solution

### Pattern 1: PUT/GET (S7-to-S7, Simplest)

PUT/GET allows one PLC to directly read/write memory in another PLC.
Must be enabled in both PLCs: Device Properties → Protection → Permit PUT/GET.

```scl
FUNCTION_BLOCK "FB_S7GetData"
TITLE = 'Read data from remote PLC via GET'
VERSION : 0.1

VAR_INPUT
  Execute    : BOOL;       // Trigger read
  ConnID     : WORD;       // Connection ID (configured in NetPro/HW Config)
END_VAR

VAR_OUTPUT
  Done       : BOOL;
  Busy       : BOOL;
  Error      : BOOL;
  ErrorID    : WORD;
  RemoteData : ARRAY[1..10] OF INT;
END_VAR

VAR
  GetBlock   : GET;
END_VAR

BEGIN
  #GetBlock(
    REQ     := #Execute,
    ID      := #ConnID,
    NDR     => #Done,
    BUSY    => #Busy,
    ERROR   => #Error,
    STATUS  => #ErrorID,
    ADDR_1  := P#DB1.DBX0.0 BYTE 20,  // Remote: DB1, 20 bytes starting at byte 0
    RD_1    := #RemoteData
  );
END_FUNCTION_BLOCK
```

### Pattern 2: MODBUS TCP Client

```scl
FUNCTION_BLOCK "FB_ModbusReader"
TITLE = 'Read holding registers from Modbus TCP server'
VERSION : 0.1

VAR_INPUT
  Execute      : BOOL;
  ConnID       : WORD;       // TCON connection ID
  UnitID       : BYTE := 1; // Modbus Unit ID
  StartRegister: WORD;       // Starting register address
  Quantity     : WORD;       // Number of registers to read
END_VAR

VAR_OUTPUT
  Done         : BOOL;
  Busy         : BOOL;
  Error        : BOOL;
  ErrorID      : WORD;
  Registers    : ARRAY[1..20] OF WORD;
END_VAR

VAR
  MbClient : MB_CLIENT;
END_VAR

BEGIN
  #MbClient(
    REQ            := #Execute,
    DISCONNECT     := FALSE,
    MB_MODE        := 0,             // 0=read
    MB_DATA_ADDR   := WORD_TO_UINT(#StartRegister),
    MB_DATA_LEN    := WORD_TO_UINT(#Quantity),
    MB_DATA_PTR    := #Registers,
    CONNECT        := #ConnID,
    NDR            => #Done,
    BUSY           => #Busy,
    ERROR          => #Error,
    STATUS         => #ErrorID
  );
END_FUNCTION_BLOCK
```

### Pattern 3: Open User Communication (OUC TCP)

```scl
// TCON establishes TCP connection
// TSEND sends data
// TRCV receives data
// TDISCON closes connection

// Typically configured via connection parameters in HW Config,
// then used in SCL with the assigned connection ID.

FUNCTION_BLOCK "FB_TcpSender"
TITLE = 'Send data via TCP (OUC)'
VERSION : 0.1

VAR_INPUT
  Execute    : BOOL;
  ConnID     : WORD;
  Data       : ARRAY[1..100] OF BYTE;
  DataLength : UINT;
END_VAR

VAR_OUTPUT
  Done       : BOOL;
  Busy       : BOOL;
  Error      : BOOL;
  ErrorID    : WORD;
END_VAR

VAR
  SendBlock : TSEND;
END_VAR

BEGIN
  #SendBlock(
    REQ    := #Execute,
    ID     := #ConnID,
    LEN    := #DataLength,
    DATA   := #Data,
    DONE   => #Done,
    BUSY   => #Busy,
    ERROR  => #Error,
    STATUS => #ErrorID
  );
END_FUNCTION_BLOCK
```

### S7-1200 Variant
- PUT/GET: Available on S7-1200 (must be enabled in device config)
- MODBUS TCP: Available on S7-1200 via MB_CLIENT/MB_SERVER
- OUC: Available but with fewer simultaneous connections
- S7 Communication: Fewer connection resources than S7-1500

## Gotchas
1. **PUT/GET must be enabled**: Both source and target PLC need PUT/GET enabled in protection settings
2. **Connection resources are limited**: S7-1200 has ~8-16 connections, S7-1500 has more
3. **MODBUS byte order**: Big-endian by default — watch for WORD swap on 32-bit values
4. **Async execution**: Communication blocks are asynchronous — use Done/Busy/Error pattern
5. **Connection ID**: Must match HW Config — misconfigured ConnID = silent failure

## Related
- `error-handling.md` — Handle communication errors gracefully
- `../../case-db/success/008-modbus-tcp-client.md` — Complete MODBUS TCP example
