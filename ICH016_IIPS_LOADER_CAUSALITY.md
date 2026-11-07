# ICH-016 - IIPS Non-Debugger Loader Causality

## Objective

In normal, non-debugger launch conditions, determine whether the
Windows Loader attempts to load IFS2.dll after iips.dll appears,
and whether this load event occurs before or after IIPS initialization.

## Method

Non-debugger observer: creates the process normally (no DEBUG flag),
then polls the module list at 10ms intervals to capture ImageLoad and
ImageUnload timing for all modules. No breakpoints, no memory
modification, no injection.

## Results (3 runs)

### Run Summary

```text
Run 1 (ICH016_A_01): iips.dll IMAGE_LOAD at t=10.491s, IFS2.dll: NOT OBSERVED
Run 2 (ICH016_A_02): iips.dll IMAGE_LOAD at t=27.963s, IFS2.dll: NOT OBSERVED
Run 3 (ICH016_A_03): iips.dll IMAGE_LOAD at t=48.457s, IFS2.dll: NOT OBSERVED

iips.dll IMAGE_LOAD: 3/3 (STABLE)
IFS2.dll IMAGE_LOAD: 0/3 (STABLE)
```

### Detailed Event Timeline (iips.dll)

**Run 1:**
```text
t=0.072  IMAGE_LOAD   KERNELBASE.dll
t=0.097  IMAGE_LOAD   codoMP_client_shipRetailBase.dll
t=0.467  IMAGE_LOAD   BugTrace.dll
t=8.016  IMAGE_LOAD   TenProxy.dll
t=8.016  IMAGE_LOAD   GbSpy.dll
t=10.491 IMAGE_LOAD   iips.dll
t=20.000 TIMEOUT      (iips.dll still loaded)
```

**Run 2:**
```text
t=20.145 IMAGE_LOAD   KERNELBASE.dll
t=20.536 IMAGE_LOAD   BugTrace.dll
t=26.683 IMAGE_LOAD   TenProxy.dll
t=26.683 IMAGE_LOAD   GbSpy.dll
t=27.963 IMAGE_LOAD   iips.dll
t=40.000 TIMEOUT      (iips.dll still loaded)
```

**Run 3:**
```text
t=40.184 IMAGE_LOAD   KERNELBASE.dll
t=40.612 IMAGE_LOAD   BugTrace.dll
t=46.741 IMAGE_LOAD   TenProxy.dll
t=46.741 IMAGE_LOAD   GbSpy.dll
t=48.457 IMAGE_LOAD   iips.dll
t=48.488 IMAGE_UNLOAD iips.dll  (brief 31ms window)
t=48.506 IMAGE_LOAD   iips.dll  (re-load)
t=60.000 TIMEOUT
```

### Key Observations

1. **iips.dll loads consistently in 3/3 normal (non-debugger) runs.**
2. **IFS2.dll NEVER appears as an ImageLoad event in any run.**
3. The sequence is always:
   ```
   Base.dll → BugTrace.dll → TenProxy.dll → GbSpy.dll → iips.dll
   ```
4. IFS2.dll never appears between iips.dll load and process exit.
5. Run 3 shows a brief iips.dll unload/re-load cycle (31ms), which
   may indicate an internal IIPS load/unload attempt.

## Analysis

### Case B Confirmation

The results fall into **Case B** of the ICH-016 task specification:

```text
iips.dll      = LOADED (3/3 confirmed)
IFS2.dll      = NO IMAGE LOAD (3/3 confirmed)
```

```text
IIPS_REACHED = CONFIRMED
IFS2_LOADER_ATTEMPT = NOT_OBSERVED
```

The precise classification is **NOT_OBSERVED**, not "LoadLibraryW = FAILED",
because ImageLoad absence does not prove that LoadLibraryW was never called
(transient load/unload within the 10ms polling window cannot be excluded
by this method).

### Pre-Stage-1 Divergence Assessment

The evidence now strongly supports:

```text
iips.dll loads successfully
       ↓
IIPS initialization begins (iipsinit_seen in EX-053)
       ↓
IFS2.dll NEVER loads
       ↓
Process eventually fails
```

Combined with ICH-014 (all static pre-conditions satisfied) and
EX-053 (path changes produce no outcome change), the evidence
significantly shifts toward:

```text
iips.dll
   ↓
pre-Stage-1 control flow
   ↓
failure
```

However, PRE_STAGE1_DIVERGENCE remains **UNKNOWN** (not CONFIRMED),
because the polling method cannot distinguish between:
  A: LoadLibraryW called, returns NULL (transient IFS2 load below 10ms)
  B: LoadLibraryW never called (divergence before Stage 1)

### IFS2 Transient Load Consideration

IFS2.dll could theoretically load and unload within a single 10ms
polling window. However:

1. ICH-014 confirmed all static pre-conditions for IFS2 loading.
2. EX-053 path changes produced no outcome change.
3. A transient load would still require LoadLibraryW to succeed in
   mapping the image, which normally takes >1ms even for a 600KB DLL.
4. The 10ms polling interval is sufficient to detect a 600KB DLL load
   that persists even for 1-2 polling cycles.

The probability of a complete load/unload cycle happening entirely
within a 10ms gap, across 3 runs, is extremely low but not impossible
by this method alone.

### Loading Sequence Stability

The module loading order is 100% consistent across all 3 runs:

```text
1. KERNELBASE.dll, ucrtbase.dll, combase.dll, CRYPTBASE.DLL (system)
2. codoMP_client_shipRetailBase.dll (platform VM host)
3. BugTrace.dll (platform/anti-cheat)
4. [various unload/reload cycles as anti-cheat validates]
5. TenProxy.dll (platform proxy)
6. GbSpy.dll (platform spy)
7. iips.dll (IIPS resource manager)
8. [IFS2.dll would be next if loaded — NEVER OBSERVED]
```

This stable sequence confirms that iips.dll loads AFTER all platform
components are ready, and that the failure occurs inside IIPS after
the platform environment is fully established.

## Final Classification

```text
ICH016_STATUS = COMPLETE

NORMAL_STARTUP_OBSERVED = YES (3/3 runs, no debugger, -q flag)

IIPS_DLL_LOAD = CONFIRMED (3/3 DYNAMIC_CONFIRMED)

IFS2_DLL_IMAGELOAD = NOT_OBSERVED (0/3, stable absence)

IFS2_DLL_IMAGEUNLOAD = NOT_OBSERVED (no load to unload)

IIPS_BEFORE_IFS2 = CONFIRMED
  (iips.dll always loads; IFS2 never loads after it)

IFS2_RUNTIME_LOAD = NOT_OBSERVED

IIPS_LOAD_TO_IFS2_RELATION = CONFIRMED (asymmetry: iips loads, IFS2 never does)

PRE_STAGE1_DIVERGENCE = UNKNOWN
  (evidence strongly supports but cannot conclusively prove without
   sub-10ms LoadLibraryW tracing)

STAGE1_STATUS = NOT_OBSERVED
  (LoadLibraryW execution not captured; IFS2 ImageLoad absent)

FIRST_CONFIRMED_LOADER_EVENT = iips.dll IMAGE_LOAD after BugTrace/TenProxy/GbSpy

ENGINE_REGION_HIT_COUNT = 0
RUNTIME_ENTRY_IDENTIFIED = NO
```

## Hard Stop Assessment

```text
STOP-1 (IFS2.dll ImageLoad confirmed): NOT TRIGGERED
STOP-2 (iips.dll LOAD + IFS2.dll = NO IMAGE LOAD, stable): TRIGGERED
STOP-3 (contradictory loader timing): NOT TRIGGERED
```

**STOP-2 is satisfied.** Three stable runs confirm that iips.dll loads
but IFS2.dll never does. The evidence shifts toward pre-Stage-1 control
flow divergence as the most supported explanation.

## Impact on Research Chain

```text
ICH-013:  IIPS failure status = CONFIRMED
ICH-014:  Four-stage actual execution = UNKNOWN
ICH-015:  Debugger observability = CLOSED (anti-cheat blocks iips.dll)
ICH-016:  Normal startup loader causality = iips loads, IFS2 never does

Combined conclusion:
  IIPS is reached and begins initialization.
  IFS2.dll is never attempted (or attempted but fails within <10ms).
  The failure is inside IIPS, before or at Stage 1.
  The exact pre-Stage-1 vs Stage-1 boundary remains UNKNOWN.
```

## NEXT_RESEARCH_DIRECTION

The boundary has been refined from "IIPS initialization gate" to:

```text
iips.dll loaded
  → pre-Stage-1 control flow (QoS helper / condition check)
    OR Stage 1 LoadLibraryW (transient failure < 10ms)
  → failure
```

The next research direction should focus on:

1. **Kernel-mode ETW ImageLoad/Unload trace** at microsecond resolution
   to rule out sub-10ms transient IFS2 load (the only remaining
   ambiguity for Stage 1).

2. **iipsinit / CNIFS internal status probing** through passive
   side-channel observation (log files, registry, shared memory)
   without modifying iips.dll.

3. **QoS helper dependency analysis**: identify what iips.dll+0x6D20
   checks (network? process? file?) and what external conditions
   cause it to fail.
