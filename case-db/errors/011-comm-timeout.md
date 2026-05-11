# Error 011: Communication Timeout Not Handled (PUT/GET)

## Frontmatter
- **Tags**: communication, timeout, putget, error-handling
- **Error Type**: Runtime

## Error Message
Runtime symptom -- no compile error:
```
PLC hangs or data goes stale when remote PLC disconnects.
PUT/GET BUSY output stays TRUE indefinitely. Data exchange silently stops.
No error logged because ERROR and STATUS outputs are never checked.
```

## Bad Code
```scl
// BAD: Fires PUT every scan, never checks ERROR/BUSY/STATUS, no timeout
FUNCTION_BLOCK "FB_BadCommSender"
TITLE = 'PUT without error handling -- WRONG'
VERSION : 0.1

VAR_INPUT
    SendData    : ARRAY[1..10] OF INT;  // Data to send to remote PLC
    ConnID      : WORD;                  // Connection ID
END_VAR

VAR_OUTPUT
    Error       : BOOL;
    ErrorID     : INT;
END_VAR

VAR
    PutBlock    : PUT;
    putDone     : BOOL;
    putBusy     : BOOL;
    putError    : BOOL;
    putStatus   : WORD;
END_VAR

BEGIN
    // ERROR 1: REQ := TRUE every scan -- re-triggers PUT continuously
    // ERROR 2: DONE/BUSY/ERROR/STATUS outputs captured but never checked
    // ERROR 3: No timeout -- if remote PLC goes offline, BUSY stays TRUE forever
    // ERROR 4: No retry logic -- no way to recover from transient errors
    #PutBlock(
        REQ    := TRUE,                            // always requesting!
        ID     := #ConnID,
        DONE   => #putDone,
        BUSY   => #putBusy,
        ERROR  => #putError,
        STATUS => #putStatus,
        ADDR_1 := P#DB5.DBX0.0 BYTE 20,           // Remote: DB5, 20 bytes
        SD_1   := #SendData
    );

    // No check on putError, no timeout, no retry
    // If remote PLC disconnects, this FB silently fails
    // The caller has no way to know data is stale
END_FUNCTION_BLOCK
```

## Good Code
```scl
// GOOD: State machine with timeout, retry, and error reporting
FUNCTION_BLOCK "FB_CommSender"
TITLE = 'PUT with state machine, timeout, and retry logic'
VERSION : 0.1

VAR_INPUT
    Execute     : BOOL;                  // Rising edge triggers send
    SendData    : ARRAY[1..10] OF INT;   // Data to send to remote PLC
    ConnID      : WORD;                  // Connection ID
    MaxRetries  : INT := 3;              // Max retry attempts
    TimeoutDur  : TIME := T#5S;          // Timeout for BUSY state
END_VAR

VAR_OUTPUT
    Done        : BOOL;                  // Send completed successfully
    Busy        : BOOL;                  // Send in progress
    Error       : BOOL;                  // Permanent failure after retries
    ErrorID     : INT;                   // Error code (0 = none)
END_VAR

VAR
    // State machine
    state       : INT;                   // 0=Idle, 1=Requesting, 2=WaitDone, 3=Success, 4=Error
    // PUT block instance
    PutBlock    : PUT;
    putDone     : BOOL;
    putBusy     : BOOL;
    putError    : BOOL;
    putStatus   : WORD;
    // Timeout timer -- MUST be in VAR (static), NOT VAR_TEMP
    timeoutTmr  : TON_TIME;
    // Retry tracking
    retryCount  : INT;
    // Edge detection
    execPrev    : BOOL;
    execRising  : BOOL;
END_VAR

BEGIN
    // Rising edge detection on Execute
    #execRising := #Execute AND NOT #execPrev;
    #execPrev := #Execute;

    // Reset outputs each scan (set in appropriate state)
    #Done := FALSE;
    #Busy := FALSE;

    CASE #state OF
        0:  // ---- IDLE ----
            #Error := FALSE;
            #ErrorID := 0;
            #retryCount := 0;
            IF #execRising THEN
                #state := 1;
                #Busy := TRUE;
            END_IF;

        1:  // ---- REQUESTING (trigger PUT) ----
            #Busy := TRUE;
            // Call PUT with REQ TRUE for one scan to trigger
            #PutBlock(
                REQ    := TRUE,
                ID     := #ConnID,
                DONE   => #putDone,
                BUSY   => #putBusy,
                ERROR  => #putError,
                STATUS => #putStatus,
                ADDR_1 := P#DB5.DBX0.0 BYTE 20,
                SD_1   := #SendData
            );
            #state := 2;

        2:  // ---- WAIT FOR DONE/ERROR ----
            #Busy := TRUE;
            // Continue calling PUT with REQ FALSE while waiting
            #PutBlock(
                REQ    := FALSE,
                ID     := #ConnID,
                DONE   => #putDone,
                BUSY   => #putBusy,
                ERROR  => #putError,
                STATUS => #putStatus,
                ADDR_1 := P#DB5.DBX0.0 BYTE 20,
                SD_1   := #SendData
            );

            // Timeout timer: if BUSY for longer than TimeoutDur, abort
            #timeoutTmr(IN := #putBusy, PT := #TimeoutDur);

            IF #putDone THEN
                // Success
                #state := 3;
            ELSIF #putError THEN
                // PUT reported an error -- try again or fail
                #retryCount := #retryCount + 1;
                IF #retryCount >= #MaxRetries THEN
                    #state := 4;  // Permanent failure
                ELSE
                    #state := 1;  // Retry
                END_IF;
            ELSIF #timeoutTmr.Q THEN
                // Timeout -- BUSY stuck TRUE, remote PLC likely unreachable
                #retryCount := #retryCount + 1;
                IF #retryCount >= #MaxRetries THEN
                    #state := 4;  // Permanent failure after max retries
                ELSE
                    #state := 1;  // Retry
                END_IF;
            END_IF;

        3:  // ---- SUCCESS ----
            #Done := TRUE;
            IF NOT #Execute THEN
                #state := 0;  // Reset when Execute drops
            END_IF;

        4:  // ---- ERROR (permanent) ----
            #Error := TRUE;
            #ErrorID := WORD_TO_INT(#putStatus);
            // Special error code for timeout (putStatus may be 0 on timeout)
            IF #ErrorID = 0 THEN
                #ErrorID := 16#7100;  // Custom: communication timeout
            END_IF;
            IF NOT #Execute THEN
                #state := 0;  // Reset when Execute drops
            END_IF;

        ELSE
            // Invalid state -- reset
            #state := 0;
            #Error := TRUE;
            #ErrorID := 16#7FFF;  // Internal error
    END_CASE;
END_FUNCTION_BLOCK
```

## Why
PUT and GET are asynchronous system function blocks -- they do NOT complete
in a single scan cycle. When you call `PUT(REQ := TRUE)`, the PLC initiates
the communication request and sets `BUSY := TRUE`. The actual data transfer
happens over subsequent scan cycles. When it finishes, the block signals
either `DONE := TRUE` (success) or `ERROR := TRUE` with a `STATUS` code.

If the ERROR output is never checked, the FB stays in a requesting state
forever when the remote PLC is unreachable. The PLC itself continues running
normally -- OB1 executes, other logic works fine -- but the data exchange
silently stops. The values in the receive buffer go stale (they retain their
last-good values), giving the false impression that communication is healthy.

Without a timeout timer, even transient network issues (cable disconnect,
remote PLC restart) cause the communication to hang indefinitely. Without
a retry counter, there is no way to distinguish between a temporary glitch
and a permanent failure.

## Detection
- **Watch Table**: `BUSY` output of the PUT/GET block stays TRUE indefinitely
  (normally it should toggle back to FALSE within a few scan cycles)
- **Stale data**: Data values from the remote PLC never update -- they show
  the same values as the last successful transfer
- **No error indication**: The caller FB shows no Error flag because the
  ERROR output of PUT/GET is never propagated
- **Diagnostic buffer**: May show S7 communication warnings, but these are
  easy to miss without explicit error handling in the program
- **Network trace**: TCP retransmissions or connection timeouts visible in
  Wireshark, but no corresponding alarm in the PLC program

## Related
- `knowledge/patterns/communication.md` -- PUT/GET, MODBUS, OUC patterns and async execution
- `knowledge/patterns/error-handling.md` -- Standard Done/Busy/Error/ErrorID interface pattern
- `case-db/errors/004-timer-in-temp.md` -- Why timers must be in VAR (static)
- `.claude/rules/scl-rules.md` -- Mandatory Error/ErrorID outputs on every FB
