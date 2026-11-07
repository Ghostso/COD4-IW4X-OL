# ICH-015 - IIPS Control-Flow Reachability

## Objective

Determine the actual runtime control flow from InitInGameApp through
QoS helper, initIfsLib, and LoadLibraryW("IFS2.dll") to establish
which step is reached and where divergence occurs.

## Evidence Basis

- ICH-013: IIPS gate status and 0x8189FEC classification
- ICH-014: Four-stage static pre-conditions all verified
- EX-057: Non-invasive kernel image trace (normal -q launch)
- EX-053: Three IFS2 path causality experiments
- ICH-015 passive observer: 3 debugger-created runs (this round)

## Experimental Results

### Passive Observer (3 runs, debugger-created, -q, timeout 20s)

```text
Run 1: EXITED 0xE06D7363 (MSVC C++ exception), 75 modules, IIPS loaded: NO
Run 2: EXITED 0xE06D7363 (MSVC C++ exception), 75 modules, IIPS loaded: NO
Run 3: EXITED 0xE06D7363 (MSVC C++ exception), 76 modules, IIPS loaded: NO

IIPS loaded: 0/3
IFS2 loaded: 0/3
```

**iips.dll does not load under a debugger-created process.** This is a
TenProtect anti-cheat response consistent with ICH-011 findings: when
the process is created with `DEBUG_ONLY_THIS_PROCESS`, the anti-cheat
detects the debugger and prevents iips.dll from loading.

This means **breakpoint-based observation of iips.dll internal control
flow is impossible without modifying the anti-cheat response** (which
is prohibited by ICH-015).

### Existing Non-Debug Evidence (EX-057 + EX-053)

```text
Normal -q launch (NO debugger, kernel image trace):
  iips.dll loads:     DYNAMIC_CONFIRMED (t = 15:35:08.812)
  iips.dll unloads:   DYNAMIC_CONFIRMED (t = 15:35:15.307)
  IFS2.dll loads:     NOT_OBSERVED (never appears in 6.49s window)
  iipsinit seen:      YES (from EX-053 experiments)

Three IFS2 path variants:
  IFS2 in IIPS/:               same fatal error, IFS2 NOT loaded
  IFS2 beside EXE:             same fatal error, IFS2 NOT loaded
  IFS2 in independent copy:    same fatal error, IFS2 NOT loaded
```

### Reconciliation

```text
Under debugger:    iips.dll never loads (anti-cheat response)
Without debugger:  iips.dll loads, but no breakpoint mechanism available

The task constraints (no patch, no injection, no hook) mean we cannot
install breakpoints in a normal-run iips.dll.
```

## Q&A Answers

### Q1: INITINGAMEAPP_REACHED

```text
INITINGAMEAPP_REACHED = NOT_OBSERVED

Reason: iips.dll internal execution cannot be observed without
breakpoints, which require a debugger, which prevents iips.dll from
loading due to anti-cheat detection.
```

### Q2: QOS_HELPER_REACHED

```text
QOS_HELPER_REACHED = NOT_OBSERVED

Reason: Same as Q1. No breakpoint mechanism is available for
normal-run iips.dll.
```

### Q3: INITIFSLIB_CALL_REACHED

```text
INITIFSLIB_CALL_REACHED = NOT_OBSERVED

Reason: Same as Q1. No breakpoint mechanism is available.

Indirect evidence: EX-053 confirms "iipsinit" is seen in normal runs,
suggesting InitInGameApp is at least partially reached, but the exact
control flow inside it remains unknown.
```

### Q4: LOADLIBRARYW_IFS2_REACHED

```text
LOADLIBRARYW_IFS2_REACHED = NOT_OBSERVED

Reason: Same as Q1. No caller-filtered LoadLibraryW trace is possible.

The strongest indirect evidence is:
  - IFS2.dll never appears in any module snapshot (EX-057)
  - Three IFS2 path variants produce identical outcomes (EX-053)
  - All static pre-conditions for IFS2 loading are satisfied (ICH-014)

These are compatible with both:
  A: LoadLibraryW is called but returns NULL (IFS2 loads/unloads transiently)
  B: LoadLibraryW is never called (control flow diverges before Stage 1)
```

### Q5: PRE_STAGE1_DIVERGENCE

```text
PRE_STAGE1_DIVERGENCE = UNKNOWN

Cannot be confirmed or refuted without direct observation of the
InitInGameApp → initIfsLib control flow.
```

### Q6: DIVERGENCE_TARGET

```text
DIVERGENCE_TARGET = UNKNOWN
```

### Q7: FIRST_CONFIRMED_IIPS_BRANCH

```text
FIRST_CONFIRMED_IIPS_BRANCH = NOT_OBSERVED

No internal iips.dll branch has been confirmed at runtime.
```

### Q8: IIPS_INIT_FAILURE_ORIGIN

```text
IIPS_INIT_FAILURE_ORIGIN = UNKNOWN

Candidates remain:
  1. PRE_STAGE1_CONTROL_FLOW (QoS helper fails, initIfsLib never reached)
  2. STAGE1_LOADER (LoadLibraryW called, returns NULL)

Cannot be distinguished without caller-filtered LoadLibraryW trace or
breakpoint-based control-flow observation, neither of which is
possible under current constraints.
```

## Reconciling Anti-Debug Constraint with Research Goal

The fundamental limitation is:

```text
Requirement: Observe iips.dll internal control flow
Method:      Set breakpoints (requires debugger)
Constraint:  Debugger causes anti-cheat to prevent iips.dll load
Result:      Impossible without violating prohibited actions
```

This is NOT an experimental design flaw. It is a confirmed anti-cheat
constraint that ICH-011 already documented (BugTrace fail-fast under
debugger).

### Possible Future Approaches (NOT attempted this round)

1. Hardware breakpoints (DR registers) - may not trigger anti-cheat
2. Page-guard based single-stepping - no memory modification
3. Kernel-mode observer with ETW - no user-mode breakpoints
4. Mock/emulate anti-cheat response (prohibited)

None of these have been attempted. All are candidates for future rounds
if the research direction justifies the complexity.

## Hard Stop Assessment

```text
STOP-1 (LoadLibraryW return observed): NOT MET (cannot observe)
STOP-2 (pre-Stage-1 divergence confirmed): NOT MET (cannot observe)
STOP-3 (control flow differs from four-stage model): NOT MET (cannot observe)
```

No stop condition is triggered. The experiment reaches its boundary:
the required observation mechanism (breakpoints inside iips.dll) is
incompatible with the anti-cheat protection that ICH-011 confirmed.

## Final Status Fields

```text
ICH015_STATUS = COMPLETE (within available evidence constraints)

INITINGAMEAPP_REACHED = NOT_OBSERVED
QOS_HELPER_REACHED = NOT_OBSERVED
INITIFSLIB_CALL_REACHED = NOT_OBSERVED
LOADLIBRARYW_IFS2_REACHED = NOT_OBSERVED
LOADLIBRARYW_RETURN = NOT_OBSERVED
LOADLIBRARYW_LAST_ERROR = NOT_OBSERVED

PRE_STAGE1_DIVERGENCE = UNKNOWN
DIVERGENCE_TARGET = UNKNOWN
FIRST_CONFIRMED_IIPS_BRANCH = NOT_OBSERVED

IIPS_INIT_FAILURE_ORIGIN = UNKNOWN
FIRST_FAILED_STAGE = UNKNOWN

ENGINE_REGION_HIT_COUNT = 0
RUNTIME_ENTRY_IDENTIFIED = NO

NEXT_RESEARCH_DIRECTION = 
  Kernel-mode ETW trace with CallStack sampling to capture
  iips.dll function-level execution without user-mode breakpoints.
  This is the only non-invasive method that can observe iips.dll
  internal control flow without triggering anti-cheat.
```

## Compliance

| Constraint | Status |
|-----------|--------|
| No binary modification | YES |
| No patch of QoS return | YES |
| No forced LoadLibraryW success | YES |
| No DLL search path modification | YES |
| No manual IFS2 load | YES |
| No injection | YES |
| No EXE modification | YES |
| No WeGame/TCLS recovery | YES |
| No 0x8189FEC as address | YES |
