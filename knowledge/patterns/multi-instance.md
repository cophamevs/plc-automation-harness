# Multi-Instance FB Pattern

## Frontmatter
- **Tags**: multi-instance, fb, memory, db-explosion, hierarchy, architecture
- **CPU**: Both
- **Difficulty**: Intermediate

## Problem
In large projects with many devices (10 motors, 8 valves, 4 conveyors), creating a
separate Instance DB for every FB call causes **DB explosion**: dozens of DBs scattered
in the project, high memory overhead, and hard-to-navigate structure.

On S7-1200 (150 KB work memory), DB explosion can exhaust memory before all logic is written.

## Solution: Multi-Instance Architecture

Declare child FBs inside a parent FB's `VAR` (static) section. The child instances'
memory lives inside the parent's single Instance DB — no separate DB per child.

### Block Structure
```
FB_ConveyorSystem (Parent FB)
├── inst_InfeedMotor  : FB_MotorControl   ← child instance (no separate DB)
├── inst_OutfeedMotor : FB_MotorControl   ← child instance (no separate DB)
├── inst_InfeedValve  : FB_ValveControl   ← child instance (no separate DB)
└── inst_CountTimer   : TON_TIME          ← IEC timer as child instance

DB_Conveyor1  ← ONE instance DB for the entire conveyor (parent + all children)
```

### SCL Code

```scl
FUNCTION_BLOCK "FB_MotorControl"
VERSION : 0.1
VAR_INPUT
  CmdStart : BOOL;
  CmdStop  : BOOL;
END_VAR
VAR_OUTPUT
  Running  : BOOL;
  Error    : BOOL;
  ErrorID  : INT;
END_VAR
VAR
  stat_RunTimer : TON_TIME;
  stat_State    : INT := 0;
END_VAR
BEGIN
  // Motor control logic...
  CASE #stat_State OF
    0:
      #Running := FALSE;
      IF #CmdStart AND NOT #CmdStop THEN
        #stat_State := 1;
      END_IF;
    1:
      #stat_RunTimer(IN := TRUE, PT := T#5s);
      #Running := TRUE;
      IF #CmdStop THEN
        #stat_State := 0;
        #stat_RunTimer(IN := FALSE, PT := T#0ms);
      END_IF;
    ELSE
      #stat_State := 0;
      #Error := TRUE;
      #ErrorID := 99;
  END_CASE;
END_FUNCTION_BLOCK


FUNCTION_BLOCK "FB_ConveyorSystem"
TITLE = 'Conveyor with multi-instance child FBs'
VERSION : 0.1

VAR_INPUT
  MasterStart   : BOOL;
  MasterStop    : BOOL;
  EmergencyStop : BOOL;
END_VAR

VAR_OUTPUT
  SystemRunning : BOOL;
  AnyFault      : BOOL;
  Error         : BOOL;
  ErrorID       : INT;
END_VAR

VAR
  // ✅ Child FBs declared in VAR — they become part of this FB's Instance DB
  // Naming: inst_ prefix to clearly identify multi-instance children
  inst_InfeedMotor  : "FB_MotorControl";
  inst_OutfeedMotor : "FB_MotorControl";
  inst_StartDelay   : TON_TIME;          // IEC timer also works as child instance
  stat_State        : INT := 0;
END_VAR

BEGIN
  // Call child FBs — no DB identifier needed (instance is local)
  #inst_InfeedMotor(
    CmdStart := #MasterStart AND NOT #EmergencyStop,
    CmdStop  := #MasterStop OR #EmergencyStop
  );

  // Outfeed starts only after infeed is confirmed running
  #inst_OutfeedMotor(
    CmdStart := #inst_InfeedMotor.Running AND NOT #EmergencyStop,
    CmdStop  := #MasterStop OR #EmergencyStop
  );

  #inst_StartDelay(IN := #MasterStart, PT := T#2s);

  // Aggregate outputs
  #SystemRunning := #inst_InfeedMotor.Running AND #inst_OutfeedMotor.Running;
  #AnyFault := #inst_InfeedMotor.Error OR #inst_OutfeedMotor.Error;

  IF #AnyFault THEN
    #Error := TRUE;
    #ErrorID := BOOL_TO_INT(#inst_InfeedMotor.Error) * 100
              + BOOL_TO_INT(#inst_OutfeedMotor.Error) * 200;
  END_IF;
END_FUNCTION_BLOCK


// Only ONE instance DB for the entire conveyor system
DATA_BLOCK "DB_Conveyor1"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
"FB_ConveyorSystem"
BEGIN
END_DATA_BLOCK
```

### Accessing Child State (Symbolic Path)
```scl
// From OB or SCADA — navigate the hierarchy via the single DB
"DB_Conveyor1".inst_InfeedMotor.Running    // BOOL
"DB_Conveyor1".inst_InfeedMotor.ErrorID    // INT
"DB_Conveyor1".inst_OutfeedMotor.Running   // BOOL
"DB_Conveyor1".stat_State                  // INT (parent state)

// S7.Net access (optimized access OFF):
// Address: DB_Conveyor1.inst_InfeedMotor.Running → read by symbolic name
```

### Before vs After: DB Count Comparison
| Approach | DBs Required | Memory Overhead |
|----------|-------------|-----------------|
| Separate Instance DB per FB | 1 parent + N children = N+1 DBs | High (each DB has header overhead) |
| Multi-instance | 1 DB total | Minimal (flat memory in one DB) |

**Example:** 10 conveyors × (1 parent + 3 children) = **40 DBs** with separate approach
vs **10 DBs** with multi-instance.

### S7-1200 Variant
Same pattern — actually MORE important on S7-1200 due to 150 KB work memory limit.
Respect the 6-level call nesting limit when designing parent/child hierarchy.

## Gotchas
1. **Nesting limit**: S7-1500 supports 16 levels; S7-1200 supports 6 levels. Don't over-nest.
2. **Naming clarity**: Use `inst_` prefix for child FB instances to distinguish them from regular static vars.
3. **IEC timers as instances**: `TON_TIME`, `TOF_TIME`, `CTU` can also be declared in parent VAR — they behave as child instances.
4. **Optimized Access and symbolic paths**: Multi-instance hierarchy is accessible by full symbolic path (`DB.inst_Child.Output`). With optimized access OFF, the same works for S7.Net/SCADA.
5. **No circular instances**: A FB cannot contain an instance of itself (infinite nesting).
6. **Child FB must be compiled first**: In external source files, child FBs must appear before parent FBs (dependency order).

## Related
- `state-machine.md` — State machines commonly use multi-instance for child FBs
- `../s7-1200-limitations.md` — DB size and work memory context
- `../s7-1500.md` — S7-1500 supports deeper nesting (16 levels)
- `../../case-db/success/012-multi-fb-system.md` — Working multi-FB example
