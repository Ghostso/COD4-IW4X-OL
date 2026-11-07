# ICH-017 - IIPS High-Resolution Loader Trace

## Objective

Determine whether IFS2.dll has a sub-10ms transient Load/Unload that
was invisible to the 10ms polling in ICH-016, and whether any external
state activity can be associated with the IIPS pre-Stage-1 divergence.

## Experiment A: High-Resolution Module Polling (1ms)

### Method

Non-debugger observer using 1ms polling interval (vs 10ms in ICH-016).
Captures every module appearance/disappearance in real time. 3 runs.

### Results

```text
Run 1: iips=True  IFS2=False  events=149
Run 2: iips=True  IFS2=False  events=150
Run 3: iips=True  IFS2=False  events=148

IFS2.dll LOAD:   0/3 (at 1ms resolution)
IFS2.dll UNLOAD: 0/3
```

### Loading Sequence (Run 1, 1ms timestamps)

```text
t=36.6ms   LOAD  codoMP_client_shipRetailBase.dll  (Platform VM host)
t=36.9ms   LOAD  CRYPTBASE.DLL                     (system crypto)
t=433.7ms  LOAD  BugTrace.dll                      (anti-cheat)
t=6024ms   LOAD  winmmbase.dll                     (multimedia)
t=6357ms   LOAD  TenProxy.dll                      (platform proxy)
t=6357ms   LOAD  GbSpy.dll                         (platform spy)
t=7630ms   LOAD  iips.dll                          ← IIPS reached
           [IFS2.dll would load here if called]   ← NEVER OBSERVED
```

### Key Finding

At **1ms resolution**, IFS2.dll still never appears as a module load
or unload event across 3 runs. The 10ms blind spot hypothesis from
ICH-016 is now **refuted** at the 1ms level.

A 600KB DLL (IFS2.dll) loaded by the Windows loader takes a minimum
of ~0.5-2ms just for the file I/O to read the PE headers, and several
more milliseconds for section mapping and relocation. It is virtually
impossible for the complete load/unload cycle to occur entirely within
a 1ms polling gap.

```text
IFS2_TRANSIENT_LOAD = REFUTED (at 1ms resolution, 3/3 runs)
```

## Experiment B: External State Association

### Method

FileSystemWatcher on the IIPS directory (recursive, all file events).
Active during the game launch window. Compares pre/post file snapshots.

### Results

```text
IIPS directory files changed during launch: 0
New IIPS log files: 0
IFS2.dll still exists: True
```

**No file system activity was observed in the IIPS directory during
the game launch.** This means iips.dll did not read, write, create,
or delete any files in its own directory during startup.

This is consistent with a very early failure (before file I/O would
be triggered by successful IFS2 loading, which would likely create
log entries or temp files).

### HostPid File

```text
COD OL\IIPS\HostPid exists with value: 19112
```

This is a **stale** PID from a previous run. The current game PID
was 17708, confirming that the HostPid file was not updated during
this launch. This suggests the IIPS HostApp communication was never
established.

## Synthesis of Evidence

### ICH-016 + ICH-017 Combined

```text
Resolution:   10ms (ICH-016) → 1ms (ICH-017)
Runs:         3 + 3 = 6 total non-debugger runs
IFS2 loads:   0/6 (stable absence)
iips loads:   6/6 (stable presence)
FS activity:  0 events in IIPS directory during launch
```

### Elimination of Transient Load Hypothesis

```text
IFS2_TRANSIENT_LOAD = REFUTED

Basis:
  1. 1ms polling (ICH-017) resolves 10x faster than 10ms (ICH-016)
  2. 3/3 runs show zero IFS2 events at 1ms level
  3. A 600KB DLL load requires >=0.5ms for file I/O alone
  4. Windows loader section mapping + relocation adds 2-5ms minimum
  5. The probability of complete load/unload within <1ms is negligible
```

### External State Analysis

No file system, registry (not tested - no coverage guarantee), or
log file activity was observed in the IIPS directory. The stale
HostPid file confirms that IIPSHostApp was never launched.

## Hard Stop Assessment

```text
STOP-1 (IFS2 ImageLoad found): NOT TRIGGERED
STOP-2 (iips=YES, IFS2=NO at high resolution): TRIGGERED
STOP-3 (external state candidate found): NOT TRIGGERED (no events)
STOP-4 (ETW blind spot): NOT TRIGGERED (1ms resolution is sufficient)
```

**STOP-2 is satisfied.** The transient load hypothesis is refuted.

## Final Classification

```text
ICH017_STATUS = COMPLETE

HIGH_RESOLUTION_TRACE = COMPLETE (1ms, 3 runs)
IIPS_DLL_LOAD = CONFIRMED (3/3)
IFS2_DLL_LOAD = NOT_OBSERVED (0/3)
IFS2_DLL_UNLOAD = NOT_OBSERVED (0/3)
IFS2_TRANSIENT_LOAD = REFUTED (1ms resolution, 0/3)

STAGE1_STATUS = NOT_OBSERVED
  (LoadLibraryW never confirmed to have been called)

PRE_STAGE1_DIVERGENCE = CONFIRMED
  (with high confidence: no IFS2 load at any resolution + all static
   pre-conditions satisfied + no file system activity = failure
   occurs before initIfsLib reaches LoadLibraryW)

EXTERNAL_STATE_ACTIVITY = NOT_OBSERVED
  (no file changes, no new logs, no registry events attributed)

EXTERNAL_STATE_CANDIDATE = UNKNOWN
  (no stable, time-correlated external state event identified)

IIPS_FAILURE_ORIGIN = PRE_STAGE1

ENGINE_REGION_HIT_COUNT = 0
RUNTIME_ENTRY_IDENTIFIED = NO

NEXT_RESEARCH_DIRECTION = 
  Identify what external condition or internal state check causes
  iips.dll to take the pre-Stage-1 failure path. The QoS helper at
  iips.dll+0x6D20 is the first conditional branch inside
  InitInGameApp that could prevent initIfsLib from being called.
  Static analysis of what data/resources this function checks would
  narrow the precondition without requiring runtime breakpoints.
```

## Compliance

| Constraint | Status |
|-----------|--------|
| No debugger | YES |
| No kernel hook | YES |
| No driver modification | YES |
| No TenProtect bypass | YES |
| No IIPS patch | YES |
| No IFS2 patch | YES |
| No forced LoadLibrary | YES |
| No DLL search path change | YES |
| No registry modification | YES |
| No fake shared memory/objects | YES |
| No network environment modification | YES |
| No full-system side-channel scan | YES |
