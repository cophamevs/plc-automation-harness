# State Machine Pattern

## Frontmatter
- **Tags**: fsm, sequence, step, case, state, transition
- **CPU**: Both
- **Difficulty**: Intermediate

## Problem
Most industrial control logic is sequential: idle → starting → running → stopping → idle.
A state machine organizes this cleanly, prevents illegal transitions, and makes
debugging easy (just read the state variable).

## Solution

### Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| FB_StateMachine | FB | Generic state machine with timed transitions |
| DB_Machine1 | DB | Instance for one machine |

### SCL Code

```scl
FUNCTION_BLOCK "FB_StateMachine"
TITLE = 'Generic State Machine with Timed Transitions'
VERSION : 0.1

VAR_INPUT
  CmdStart   : BOOL;    // Request transition to Running
  CmdStop    : BOOL;    // Request transition to Idle
  CmdReset   : BOOL;    // Reset from Fault to Idle
  Fault      : BOOL;    // External fault signal
END_VAR

VAR_OUTPUT
  State      : INT;     // Current state number
  StateName  : STRING[20]; // Current state as text
  Running    : BOOL;    // TRUE when in Running state
  Error      : BOOL;    // TRUE when in Fault state
  ErrorID    : INT;     // Fault code
END_VAR

VAR
  PrevState    : INT := -1;
  StateTimer   : TON_TIME;
  StartTimeout : TON_TIME;
END_VAR

VAR CONSTANT
  ST_IDLE      : INT := 0;
  ST_STARTING  : INT := 1;
  ST_RUNNING   : INT := 2;
  ST_STOPPING  : INT := 3;
  ST_FAULT     : INT := 10;
END_VAR

BEGIN
  // Entry action: reset timer on state change
  IF #State <> #PrevState THEN
    #StateTimer(IN := FALSE, PT := T#0ms);
    #StartTimeout(IN := FALSE, PT := T#0ms);
    #PrevState := #State;
  END_IF;

  // Free-running state timer (measures time in current state)
  #StateTimer(IN := TRUE, PT := T#24h);

  // Global fault check — any state except FAULT can transition to FAULT
  IF #Fault AND #State <> #ST_FAULT THEN
    #State := #ST_FAULT;
    #ErrorID := 1;  // External fault
  END_IF;

  CASE #State OF
    0: // ST_IDLE
      #Running := FALSE;
      #Error := FALSE;
      #StateName := 'Idle';
      IF #CmdStart AND NOT #CmdStop AND NOT #Fault THEN
        #State := #ST_STARTING;
      END_IF;

    1: // ST_STARTING
      #StateName := 'Starting';
      #StartTimeout(IN := TRUE, PT := T#10s);
      // Simulated: transition to Running after 2 seconds
      IF #StateTimer.ET >= T#2s THEN
        #State := #ST_RUNNING;
      END_IF;
      // Timeout protection
      IF #StartTimeout.Q THEN
        #State := #ST_FAULT;
        #ErrorID := 2;  // Start timeout
      END_IF;
      IF #CmdStop THEN
        #State := #ST_IDLE;
      END_IF;

    2: // ST_RUNNING
      #Running := TRUE;
      #StateName := 'Running';
      IF #CmdStop THEN
        #State := #ST_STOPPING;
      END_IF;

    3: // ST_STOPPING
      #Running := FALSE;
      #StateName := 'Stopping';
      // Transition to Idle after 1 second
      IF #StateTimer.ET >= T#1s THEN
        #State := #ST_IDLE;
      END_IF;

    10: // ST_FAULT
      #Running := FALSE;
      #Error := TRUE;
      #StateName := 'Fault';
      IF #CmdReset AND NOT #Fault THEN
        #ErrorID := 0;
        #State := #ST_IDLE;
      END_IF;

    ELSE
      // Unknown state — go to fault
      #State := #ST_FAULT;
      #ErrorID := 99;
  END_CASE;
END_FUNCTION_BLOCK

DATA_BLOCK "DB_Machine1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_StateMachine"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp : INT;
END_VAR
BEGIN
  "DB_Machine1"(
    CmdStart := "Tag_Start",
    CmdStop  := "Tag_Stop",
    CmdReset := "Tag_Reset",
    Fault    := "Tag_Fault"
  );
END_ORGANIZATION_BLOCK
```

### S7-1200 Variant
Same as S7-1500 version — no S7-1500-only features used.

## Usage Example
```
// Read state via MCP:
S7ReadVariable(address="DB1.DBW0")   → State (INT)
S7ReadVariable(address="DB1.DBX4.0") → Running (BOOL)
S7ReadVariable(address="DB1.DBX4.1") → Error (BOOL)
```

## Gotchas
1. Always include an ELSE branch in CASE — unknown states should go to FAULT
2. Timer must be in VAR (static), never VAR_TEMP
3. Reset the state timer on every state transition (entry action pattern)
4. Timeout protection in transitional states (STARTING, STOPPING) prevents hangs
5. Global fault check BEFORE the CASE — ensures fault is caught regardless of current state
6. **CASE outperforms long IF-ELSIF chains**: For state machines, `CASE #State OF` is evaluated in O(1) — the CPU jumps directly to the matching branch. A chain of `IF #State = 0 ... ELSIF #State = 1 ...` evaluates every condition top-down. With 10+ states this creates measurable scan-time jitter. Use CASE for any integer-selector branching with 3 or more branches.

## Related
- `timer-counter.md` — Timer patterns used in state transitions
- `error-handling.md` — Error aggregation across multiple state machines
- `../industry/conveyor-control.md` — State machine applied to conveyor
