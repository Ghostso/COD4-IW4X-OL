# ICH-017 - Pre-Stage-1 External State

## Status

```text
PRE_STAGE1_DIVERGENCE = CONFIRMED (high confidence)
EXTERNAL_STATE_CANDIDATE = UNKNOWN
```

## Evidence Basis

The following evidence converges to confirm that IIPS failure occurs
BEFORE the first external dependency handoff (LoadLibraryW("IFS2.dll")):

### 1. IFS2.dll never loads at any resolution (ICH-016 + ICH-017)

```text
10ms polling:   0/3 IFS2 events (ICH-016)
1ms polling:    0/3 IFS2 events (ICH-017)
Total:          0/6 IFS2 events across 6 independent runs
```

A 600KB DLL requires at least 0.5-2ms for file I/O and 2-5ms for
section mapping. The probability of a complete load/unload cycle
occurring within a 1ms gap across 3 runs is negligible.

### 2. All static pre-conditions are satisfied (ICH-014)

IFS2.dll exists, correct architecture, correct exports, all dependencies
are system DLLs. If LoadLibraryW were called, it should succeed. Its
consistent absence implies it was never called.

### 3. Path changes produce no outcome (EX-053)

Three different IFS2 path locations → identical fatal error. If the
failure were in the loader/path, changing the path should change the
outcome.

### 4. No file system activity during launch (ICH-017 Exp B)

Zero file changes in the IIPS directory during the entire game launch
window. No new log files. Stale HostPid. This means iips.dll did not
perform any observable file I/O in its own directory, consistent with
an early internal failure before reaching any file-dependent code path.

### 5. Stable module loading order (ICH-016 + ICH-017)

All 6 runs show the identical module sequence:
```
system DLLs → Base.dll → BugTrace.dll → TenProxy.dll → GbSpy.dll → iips.dll
[IFS2.dll NEVER appears]
```

The platform environment is fully established before iips.dll loads,
ruling out a platform-level environment failure.

## Pre-Stage-1 Divergence Model

Based on static analysis (ICH-013) and runtime evidence (ICH-016/017):

```text
iips.dll loads (DllMain succeeds)
       ↓
InitInGameApp is entered (iipsinit_seen confirms partial execution)
       ↓
┌─────────────────────────────────────────────────────────┐
│ PRE-STAGE-1 REGION (where failure occurs)               │
│                                                         │
│ 1. QoS helper call (iips.dll+0x98CD → 0x6D20)          │
│    What it checks: UNKNOWN                              │
│    Candidates: network status, process privileges,     │
│    system configuration, environment variable,         │
│    shared state, mutex/semaphore                       │
│                                                         │
│    If returns 0 → error branch → AL=0 → FAIL           │
│    If returns non-zero → continue                      │
│                                                         │
│ 2. Other conditional checks before initIfsLib          │
│    (exact structure depends on CFG beyond 0x98D4)      │
│                                                         │
│ 3. initIfsLib call (iips.dll+0x99D2 → 0x9570)          │
│    [NEVER REACHED if pre-Stage-1 failure]              │
└─────────────────────────────────────────────────────────┘
       ↓
initIfsLib (iips.dll+0x9570)
       ↓
Stage 1: LoadLibraryW("IFS2.dll") at 0x96E9   ← NEVER OBSERVED
Stage 2: GetProcAddress("CreateIFSLibDll")     ← NEVER OBSERVED
Stage 3: CreateIFSLibDll()                     ← NEVER OBSERVED
Stage 4: GetProcAddress("DestoryIFSLibDll")    ← NEVER OBSERVED
       ↓
SUCCESS: AL=1                                  ← NEVER OBSERVED
```

## QoS Helper Analysis

The QoS helper at `iips.dll+0x6D20` is the first function called inside
`InitInGameApp` (after setup) that has a conditional branch controlling
whether `initIfsLib` is reached.

### Static context (from ICH-013 disassembly)

```text
0x98B7: call [0x10033028]    ; some setup call
0x98BD: lea esi, [ebp+0xD0]  ; object field
0x98C3: push 1               ; argument
0x98C5: mov byte [esp+0x100], 2  ; state tracking
0x98CD: call 0x10006D20      ; QoS helper (← FIRST CONDITIONAL)
0x98D2: test al, al          ; check return
0x98D4: jne 0x100098E6       ; non-zero: continue to initIfsLib path
0x98D6: push 0x10034A34      ; zero: failure string
```

### What does the QoS helper check?

Without reverse engineering iips.dll+0x6D20 (prohibited), candidates
include:

1. **Network status** (is a network connection available?)
2. **Process token/privileges** (is the process running with sufficient rights?)
3. **Shared state/mutex** (is another IIPS instance already running?)
4. **Environment check** (is the working directory correct? are required files present?)
5. **Configuration value** (is a registry key or INI value set correctly?)
6. **Timeout condition** (did a previous step take too long?)
7. **Platform callback** (does Base.dll/TenProxy report "ready"?)

Without runtime observation, we cannot determine which candidate is
correct. The function's imports (KERNEL32, ADVAPI32, SHLWAPI) and the
presence of "QoS" in its name suggest network quality-of-service or
system condition checking.

## External State Events Observed

```text
File system:    NOT_OBSERVED (0 events in IIPS directory)
Registry:       NOT_OBSERVED (no coverage guarantee)
Log files:      NOT_OBSERVED (0 new IIPS log files)
HostPid:        STALE (previous run PID, not updated)
Shared memory:  NOT_OBSERVED (no coverage)
Named objects:  NOT_OBSERVED (no coverage)
```

**No external state event was identified that could be attributed to
the IIPS pre-Stage-1 failure.** The failure appears to be internal to
iips.dll's own logic (checking a condition that evaluates to false),
rather than being caused by a missing external resource.

## iipsinit_seen Interpretation

EX-053 reports `iipsinit_seen = YES` in all experiments. This likely
refers to the `iipsinit` Environment List Box window class being
registered or an `iipsinit` string being present in the process.
This is compatible with InitInGameApp being partially entered (enough
to register UI elements) before failing at the QoS check.

## Conclusion

```text
PRE_STAGE1_DIVERGENCE = CONFIRMED (high confidence, not absolute certainty)

The failure mechanism is:
  iips.dll loads → InitInGameApp begins → QoS helper (or equivalent
  pre-Stage-1 check) returns failure → error branch taken →
  initIfsLib is never called → IFS2.dll is never loaded →
  IIPS reports failure to EXE → WIN_IIPS_INIT_ERROR

The exact condition checked by the QoS helper remains UNKNOWN.
It may be an internal state, a platform callback result, or an
environment variable. Without runtime breakpoints (blocked by
anti-cheat) or IIPS internal reverse engineering (prohibited),
the exact precondition cannot be identified from external observation
alone.
```
