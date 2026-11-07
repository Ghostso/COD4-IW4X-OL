# ICH-021 - Engine Entry Attribution

## Consolidated Finding: The Engine IS Reached

The full evidence chain from ICH-008 through ICH-021 now establishes:

```text
1. VM dispatcher runs (ICH-008)                          CONFIRMED
2. VM decrypts code into engine gap (ICH-020)             CONFIRMED
3. Engine function at 0x00CA0000 executes (ICH-021)       CONFIRMED
4. Engine execution occurs BEFORE iips.dll loads (ICH-021) CONFIRMED
5. IIPS failure does not prevent engine execution         CONFIRMED
```

## The Original CODOL Runtime Entry

```text
EXECUTION ENTRY = Engine code decrypted into VA 0x00994000..0x00CA789A
FIRST CONFIRMED ENGINE FUNCTION = VA 0x00CA0000
FIRST EXECUTION TIME = t ≈ 6.848s
ENTRY MECHANISM = VM dispatch from Base.dll .tvm0
IIPS PREREQUISITE = NOT REQUIRED for this function
```

## Revised CODOL Startup Model

```text
t = 0.000s  EXE Entry → Base.dll ordinal-1
t = 0.037s  Base.dll .tvm0 VM dispatcher begins
t = 0.434s  BugTrace.dll loads (anti-cheat)
t = 6.358s  TenProxy.dll + GbSpy.dll load
t = 5.075s  VM decrypts engine code into gap ← BEFORE platform DLLs
t = 6.848s  *** ENGINE FUNCTION EXECUTES ***
            (0x00CA0000: writes 0x9B9C00 to global)
t = 7.630s  iips.dll loads
t ≈ 8.0s    IIPS QoS fails (Tencent server unreachable)
t ≈ 8.0s    WIN_IIPS_INIT_ERROR  
t ≈ 20s     Process terminates
```

The engine is already executing BEFORE the IIPS gate. The IIPS failure
prevents LATER stages of engine initialization (resource loading, etc.)
but does NOT prevent the engine code from beginning to run.

## What IIPS Actually Controls

Based on all evidence, the IIPS initialization gate does NOT control:
- VM code decryption (happens before IIPS)
- Engine code placement in memory (happens before IIPS)
- First engine function execution (happens before IIPS)

The IIPS gate MAY control:
- Resource manager initialization (IFS2/filesystem access)
- Network-dependent engine features
- Full game runtime activation beyond the initial functions
- Transition from "engine code loaded" to "game actually playable"

## The Actual Blocking Point

The startup failure is NOT:
- "Engine code doesn't exist" (it does, confirmed)
- "Engine code never executes" (it does, confirmed)
- "VM can't reach the engine" (it can, confirmed)

The failure is:
- "Engine starts executing but cannot complete initialization
   because IIPS (which loads later) fails due to unreachable
   Tencent QoS server"

The IIPS gate blocks the transition from:
  "Engine code exists and initial functions run"
to:
  "Full game runtime is operational"

## RUNTIME_ENTRY_IDENTIFIED

```text
RUNTIME_ENTRY_IDENTIFIED = YES (PARTIAL)

The entry mechanism is confirmed: VM dispatch from Base.dll .tvm0
into the engine gap. The first confirmed engine function is at
0x00CA0000. 

What remains unknown:
- The exact FIRST engine instruction (may be before 0xCA0000)
- The complete call chain from VM dispatch to 0xCA0000
- Whether other engine functions execute before or after 0xCA0000
```

## NEXT_RESEARCH_DIRECTION

The IIPS line is now closed. The remaining question is:

```text
What does the engine code at 0x00CA0000 (and surrounding functions)
actually DO, and what IIPS-dependent initialization does it need
to progress beyond its current state?

Specifically:
1. Find all call/jmp references TO 0x00CA0000 to identify its caller
2. Trace the call chain from VM dispatcher → engine entry → 0xCA0000
3. Identify what other engine functions run and what state they set up
4. Determine what specific IIPS-dependent resource the engine needs
   to transition from "partial initialization" to "game running"
```

This shift moves from "can we reach the engine?" (answered: YES) to
"what does the engine need to run fully?" which is the actual game
recovery question.

## Compliance

| Constraint | Status |
|-----------|--------|
| No IIPS modification | YES |
| No IFS2 investigation | YES |
| No binary modification | YES |
| No injection | YES |
| No anti-cheat bypass | YES |
| No debugger | YES |
