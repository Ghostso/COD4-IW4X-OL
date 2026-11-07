# ICH-010/012 — Platform Boundary Synthesis

## Shared Startup Chain

```text
CODOL EXE
  → EXE Entry (RVA 0x0E5DC690, IAT call to Base.dll ordinal-1)
  → Base.dll ordinal-1 (RVA 0x1D6582C)
  → Base.dll .tvm0 VM Dispatcher (RVA 0x1F27FDC → 0x1F9DFFD)
  |
  ├─→ BugTrace.dll (Platform/anti-cheat, thread + ordinal-1 re-entry)
  ├─→ Base.dll .tvm0 internal threads
  ├─→ mswsock.dll (network)
  ├─→ kernel32.dll / combase.dll (OS calls)
  ├─→ ntdll.dll (fail-fast termination)
  |
  ├─→ [separate normal -q run] iips.dll (loads, internal handoff, fails)
  |     └─→ IFS2.dll: NEVER OBSERVED
  |
  └─→ EXE 2.7 MB Game Engine region: NEVER REACHED (0/439 events)

  → Process terminates 0xC0000409 (fail-fast)
```

## Component Classification

| Component | Role | Runtime Participation | Engine Reach |
|-----------|------|----------------------|-------------|
| Base.dll `.tvm0` | VM host / Platform dispatcher | CONFIRMED | NO |
| BugTrace.dll | Platform/anti-cheat/diagnostic | CONFIRMED | NO |
| iips.dll | IIPS resource manager (module level) | CONFIRMED | NO |
| IFS2.dll | FS / resource library | NOT_OBSERVED | N/A |
| Unknown Native Layer | — | NOT_OBSERVED | N/A |

## Final Verdict Fields

```text
ICH010_STATUS = COMPLETE
ICH011_STATUS = COMPLETE
ICH012_STATUS = COMPLETE

IIPS_RUNTIME_PARTICIPATION = CONFIRMED
IFS2_RUNTIME_PARTICIPATION = NOT_OBSERVED
IIPS_TO_IFS2 = NOT_OBSERVED
IFS2_TO_ENGINE = NOT_OBSERVED

BUGTRACE_RUNTIME_PARTICIPATION = CONFIRMED
BUGTRACE_TO_IIPS_IFS2 = NOT_OBSERVED
BUGTRACE_TO_ENGINE = NOT_OBSERVED
BUGTRACE_FAILURE_PATH = CONFIRMED

UNKNOWN_NATIVE_LAYER = NOT_OBSERVED
UNKNOWN_DLL_LOAD = NOT_OBSERVED
UNKNOWN_THREAD_HANDOFF = NOT_OBSERVED
PLATFORM_PRECONDITION = CONFIRMED
UNKNOWN_LAYER_TO_ENGINE = NOT_OBSERVED

ENGINE_REGION_HIT_COUNT = 0
FIRST_ENGINE_TARGET = UNKNOWN

PLATFORM_TO_ENGINE = NOT_OBSERVED
RUNTIME_ENTRY_IDENTIFIED = NO

PRIMARY_BLOCKING_BOUNDARY = IIPS initialization gate (WIN_IIPS_INIT_ERROR at 0x8189FEC)

SECONDARY_CANDIDATES = BugTrace fail-fast (TenProtect anti-debug), VM-controlled kernel32 access violation

EXCLUDED_COMPONENTS = IFS2.dll (never loads), Unknown Native Layer (ICH-009 resolved), BugTrace-to-IIPS bridge (no evidence)

UNRESOLVED_BOUNDARY = IIPS internal packed/VM status handoff between iips.dll load/unload and EXE error boundary at 0x8189FEC

NEXT_RESEARCH_DIRECTION = Minimal single-variable capture of iips.dll LoadLibraryW(ifs2 path) entry/return and GetLastError, caller-filtered to iips.dll only
```

## Primary Blocking Boundary Justification

`PRIMARY_BLOCKING_BOUNDARY` is assigned to the IIPS initialization gate
with **direct dynamic evidence**:

1. **ICH-009**: 0/439 post-ordinal-1 events fall in the EXE 2.7 MB
   Engine region across 3/3 stable runs. The Engine is never reached.

2. **ICH-010**: `iips.dll` loads and unloads with a 6.49 s window.
   `IFS2.dll` never appears. The first external dependency handoff from
   IIPS is not crossed.

3. **EX-053**: Three IFS2 path variants produce no change in outcome.
   The block is inside IIPS's internal logic, not a file-visibility issue.

4. **EX-057/058/059**: Non-invasive kernel image trace confirms IIPS
   module participation and IFS2 absence in the same interval.

These four independent evidence sources converge on the same conclusion:
the startup chain cannot progress past IIPS initialization to reach
any Engine-region code.

## Secondary Failure Paths

Two secondary failure mechanisms are confirmed but are not the primary
blocking boundary:

1. **BugTrace fail-fast**: In the debug-observer environment, BugTrace's
   re-entry into ordinal-1 leads to a VM-controlled thread that triggers
   an access violation and fail-fast. This is a TenProtect anti-debug
   response, not the normal-run failure mechanism.

2. **VM-controlled kernel32 AV**: The same VM thread that creates
   BugTrace's platform thread also attempts an OS call via combase.dll
   that fails. This is an ICH-008/009 confirmed secondary candidate.

## Unresolved Boundary

The only remaining unresolved link is the mechanism by which `iips.dll`
communicates its failure state to the EXE error boundary at
`0x8189FEC`. This is inside IIPS's packed/VM status handoff and has
not been decoded or captured at the function level. It is the
**UNRESOLVED_BOUNDARY**, not the primary blocking boundary.

## Hard Stop Compliance

- STOP-A: Platform → IIPS → IFS2 → EXE Engine: NOT triggered (IFS2 never loads)
- STOP-B: Platform → BugTrace → EXE Engine: NOT triggered (no Engine hit)
- STOP-C: Platform → Unknown Native Layer → EXE Engine: NOT triggered (no unknown layer)
- STOP-D: Platform component → failure/return → termination: **CONFIRMED** (IIPS internal failure, BugTrace fail-fast, kernel32 AV)
- STOP-E: All three directions fail to observe Engine handoff; Platform Native timeline is complete: **CONFIRMED**

STOP-E is satisfied. No further DLL scanning or Engine-region expansion
is authorized.

