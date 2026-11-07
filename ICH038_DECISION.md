# ICH-038 — Engine Waiting Trigger / VM Dispatch Continuation 定位

## A/B 实验结果

### Run A (with -q)

```text
Lifetime: 30.0s (timeout)
Modules: 148
Threads: 64+
Gate: CROSSED (96 entries)
RM+0x3BC: 0 (never modified)
RM vtable calls: 0
Exit code: 0x00000103 (still running at timeout)
```

### Run B (without -q)

```text
Lifetime: 30.1s (timeout)
Modules: 149
Threads: 64+
Gate: CROSSED (96 entries)
RM+0x3BC: 0 (never modified)
RM vtable calls: 0
Exit code: 0x00000103 (still running at timeout)
```

### A/B Comparison

```text
Q_AB_DIFFERENCE = NONE

Both runs show IDENTICAL behavior:
  - Same gate crossing
  - Same module loading pattern
  - Same RM state (0x3BC = 0)
  - Same absence of RM vtable calls
  - Same absence of FF loading
  - Same process lifetime (30s+ stable)

Conclusion: The -q flag does NOT affect resource loading path.
The engine's waiting state is independent of the -q command-line flag.
```

## Engine Waiting State Analysis

### What we know

```text
1. RM pointer is valid and non-NULL
2. Dispatch table is populated (96 entries)
3. Engine loads additional subsystem DLLs (d3d9, bink2, mss32, etc.)
4. Engine creates additional threads
5. Engine does NOT call any RM vtable method
6. RM+0x3BC remains 0
7. Process is stable and does not crash
8. -q flag does not change this behavior
```

### What Engine is NOT waiting for

```text
❌ RM vtable call trigger (Engine doesn't call RM at all)
❌ IIPS_IsPackReady (never called)
❌ CRITICAL_SECTION (never used)
❌ -q flag (A/B test shows no difference)
❌ More time (30 seconds is sufficient for any reasonable init)
```

### What Engine MIGHT be waiting for

```text
✓ Base.dll .tvm0 VM dispatch continuation
    The VM dispatched execution to engine code
    Engine completed its bootstrap
    But VM may need to dispatch the NEXT instruction
    which would trigger resource loading

✓ A specific Engine internal state variable
    Some global/object state that transitions
    from "initialized" to "ready-to-load-resources"

✓ A platform callback that never arrives
    TCLS/WeGame/other platform component
    that was supposed to signal readiness

✓ A window/message/timer event
    Engine might need a message loop to continue
```

## ROOT_WAITING_TRIGGER

```text
ROOT_WAITING_TRIGGER = UNKNOWN

The Engine has completed:
  ✅ Bootstrap
  ✅ Code decryption (3.08 MB)
  ✅ Dispatch table registration (96 functions)
  ✅ RM interface acceptance
  ✅ Subsystem DLL loading (149 modules)
  ✅ Thread creation (64+ threads)

The Engine has NOT executed:
  ❌ RM vtable methods
  ❌ loadfastfile()
  ❌ Zone allocation
  ❌ Asset database initialization
  ❌ Dvar registration
  ❌ Game configuration loading

The waiting trigger is OUTSIDE the RM/IIPS/FF chain.
It is likely in the VM dispatch sequence or in an
Engine-internal state machine that we haven't identified.

At this point, further investigation of the RM/FF/Zone/Asset
chain without understanding the VM dispatch continuation
is unlikely to produce new results.
```

## NEXT_TARGET

```text
The most promising next investigation directions are:

1. VM Dispatch Continuation
   - The VM dispatched Engine code for bootstrap
   - After bootstrap, the VM may need to dispatch MORE code
   - This would be the natural "continue" signal
   - Method: Monitor Base.dll .tvm0 VM activity after t=9s

2. Engine Global State Monitoring
   - Track ALL global variable changes in the Engine gap
   - Find which state transitions happen and which don't
   - Identify the missing transition that would trigger FF loading

3. Window/Message System
   - Check if Engine needs a message pump
   - The -q flag might suppress window creation
   - Without a window/message loop, Engine might be blocked

4. TCLS Platform Signal
   - There may be a TCLS component that signals "platform ready"
   - This signal would be independent of IIPS
   - It may require TCLS authentication/login

RECOMMENDATION: Direction 2 (Engine Global State Monitoring) is the most
actionable, as it requires only ReadProcessMemory and can identify the
exact state variable that blocks progression.
```
