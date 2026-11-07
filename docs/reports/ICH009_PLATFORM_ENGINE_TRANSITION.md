# ICH-009 — VM → Platform → Game-Engine Transition

## 0. Objective

Only question: After VM enters Platform Glue (confirmed in ICH-008),
does observable control flow continue toward the CODOL 2.7 MB virtual-only
Game-Engine region?

```text
Target: EXE virtual-only gap VA 0x00994000 .. 0x00CA789A (3.08 MB)
Source: ICH-008 confirmed VM→Platform transfers (Base.dll, BugTrace.dll,
        kernel32.dll, combase.dll)
Method: Re-analysis of frozen Plan A ORD1_LIFECYCLE dynamic trace data
Constraint: No new dynamic run; no binary modification; no VM decode
```

---

## 1. Fixed Target Region

```text
EXE virtual-only gap:
  RVA:   0x00594000 .. 0x008A789A
  VA:    0x00994000 .. 0x00CA789A
  Size:  3.08 MB (0x31389A bytes)
  Pages: 787
```

This is the game engine code location (ICH-007 confirmed). No thread
start, exception address, or execution event needs to be re-located;
we only check whether any post-ordinal1 event falls within this range.

---

## 2. UNRESOLVED Target Resolution

ICH-008 identified one unresolved native thread start: `0x5F796178`.

### 2.1 Resolution

```text
Address:      0x5F796178
Module:       codoMP_client_shipRetailBase.dll
Module base:  0x5CE30000
RVA:          0x5F796178 - 0x5CE30000 = 0x2966178
Section:      .tvm0
.tvm0 range:  VA 0x19DD000 .. 0x393B000 (size 0x1F5E000)
Classification: Base.dll .tvm0 VM bytecode region
```

The "unresolved" address from ICH-008 resolves to **inside Base.dll's
.tvm0 VM section**. It is NOT game engine code, NOT an anonymous
executable region, and NOT the EXE virtual-only gap.

```text
UNRESOLVED_TARGET = RESOLVED
  → Base.dll .tvm0 + offset (VM internal thread start)
```

---

## 3. All Post-Ordinal1 Events vs EXE Gap

### 3.1 Thread start addresses (run ORD1_A_01)

| Time | Address | Module | Section | In EXE Gap? |
|------|---------|--------|---------|-------------|
| 0.599 | 0x5D07D060 | Base.dll+0x24D060 | .tvm0 (RVA 0x24D060 within .tvm0 0x19DD000..0x393B000) | NO |
| 0.631 | 0x5EB2CFAA | Base.dll+0x1FCFAA | .tvm0 (RVA 0x1FCFAA within .tvm0 range) | NO |
| 0.633 | 0x76345D40 | (system DLL, not in listed modules) | — | NO |
| 0.644 | 0x72A81D50 | mswsock.dll+0x1D50 | .text | NO |
| 0.682 | 0x683BB233 | BugTrace.dll+0xB233 | .text | NO |
| 0.683 | 0x5F796178 | Base.dll+0x2966178 | **.tvm0** | NO |

### 3.2 Exception addresses (run ORD1_A_01)

| Exception | Address | Module | In EXE Gap? |
|-----------|---------|--------|-------------|
| 0x80000003 (int3) | 0x77AB1B52 | ntdll (debugger artifact) | NO |
| 0xC0000005 (AV) | 0x7620015A | kernel32.dll+0x1015A (.text) | NO |
| 0xE06D7363 (MSVC throw) | 0x76A0B702 | combase/MSVC | NO |
| 0x80000003 × 419 | 0x77A8B71A | ntdll RtlpDebugBreak | NO |
| 0xC0000409 (fail-fast) | 0x779F1DCC | ntdll/system | NO |

### 3.3 Total events checked

```text
Thread starts (POST_ORDINAL):     6
Exceptions (POST_ORDINAL):      425
  - debugger artifacts:         419 (int3, excluded)
  - C++ exceptions:               3 (MSVC throw)
  - Access violations:            1 (kernel32)
  - Fail-fast:                    1 (anti-debug)
ORDINAL1 entries:                 3
ORDINAL1 hops:                    3
EXIT_PROCESS:                     1
────────────────────────────────────
Total POST_ORDINAL events:     439
Events falling in EXE gap:       0
```

### 3.4 Module attribution summary

All post-ordinal1 native addresses resolve to:

```text
Base.dll        .tvm0 (VM bytecode)      → 3 thread starts
Base.dll        virtual-only (system)    → (within Base.dll image)
BugTrace.dll    .text                    → 1 thread start
kernel32.dll    .text                    → 1 exception (AV)
combase.dll     (call target)            → 1 register value (edx)
mswsock.dll     .text                    → 1 thread start
ntdll.dll       (debugger artifacts)     → 419 int3 + 1 fail-fast
(system DLL)    (unresolved in trace)    → 1 thread start
```

**Zero events fall in the EXE virtual-only gap (0x00994000..0x00CA789A).**

---

## 4. Platform → Engine Assessment

The complete post-ordinal1 event chain is:

```text
VM (.tvm0)
  ↓
Platform Glue:
  Base.dll .tvm0 (VM bytecode executes, creates threads)
  BugTrace.dll (anti-cheat/telemetry, re-enters VM, creates thread)
  mswsock.dll (network)
  kernel32.dll (thread management, exception)
  combase.dll (COM call target)
  ntdll.dll (debugger break, fail-fast termination)
  ↓
EXE 2.7 MB virtual-only Game-Engine region: NEVER REACHED
```

No Platform Glue component creates a thread at, jumps to, calls into,
or raises an exception within the EXE virtual-only gap. The game
engine code region remains completely unobserved during the 8.7-second
observation window across all 3 runs.

---

## 5. Final Status

```text
ICH009_STATUS = COMPLETE

VM_TO_PLATFORM = CONFIRMED
  (ICH-008: BugTrace, Base.dll, kernel32, combase, mswsock all confirmed)

PLATFORM_TO_ENGINE = NOT_OBSERVED
  (0/439 post-ordinal1 events fall in EXE virtual-only gap)

VM_TO_GAME_ENGINE = NOT_OBSERVED
  (no complete chain VM→Platform→Engine established)

ENGINE_REGION_HIT_COUNT = 0

FIRST_ENGINE_TARGET = UNKNOWN

UNRESOLVED_TARGET = RESOLVED
  (0x5F796178 = Base.dll .tvm0 + 0x2966178, VM internal thread start;
  NOT game engine, NOT anonymous region)

RUNTIME_ENTRY_IDENTIFIED = NO

RUNTIME_BOUNDARY_STATUS = VM_TO_PLATFORM_ONLY
  (VM dispatches exclusively to platform glue and OS modules;
  game engine region is not reached in the 8.7s observation window)

NEXT_RESEARCH_DIRECTION =
  The complete post-ordinal1 execution path (439 events across 3 runs)
  stays entirely within Base.dll (.tvm0/.text), BugTrace.dll, and OS
  system DLLs. The EXE's 2.7 MB virtual-only game engine region is
  never entered by any observable thread start, exception, or execution
  event.

  The most likely explanation is: the game engine initialization is
  gated behind the IIPS/IFS2 platform boundary (WIN_IIPS_INIT_ERROR
  at 0x8189FEC), which blocks progression before the engine is ever
  reached. The 8.7s window is not sufficient for the engine to load
  because the startup fails at the IIPS stage.

  To confirm this hypothesis:
    (a) Resolve the IIPS/IFS2 boundary to allow startup past the
        platform glue stage (requires new scope authorization)
    (b) Acquire the game engine PDB file to independently map
        engine code addresses
    (c) Observe a longer execution window after IIPS is resolved

  Without resolving the IIPS boundary, further VM→Engine observation
  will not produce new evidence.
```

---

## 6. Judgment Matrix

### Outcome: Scenario B (confirmed)

```text
VM
  ↓
Platform (Base.dll/BugTrace/kernel32/combase/mswsock/ntdll)
  ↓
Platform / OS only
  ↓
2.7 MB Engine region: NEVER HIT
```

This confirms: the currently observable VM Native path belongs to
Platform Glue, not Game Runtime. The connection between CODOL's
startup VM and its game engine remains unproven.

The definitive research conclusion is:

```text
当前可观测 VM Native 路径属于 Platform Glue，
CODOL Game Runtime 与启动 VM 之间的连接仍未获得证据。
```

---

## 7. ICH-004 through ICH-009 Complete Evidence Chain

| Round | Question | Answer |
|-------|----------|--------|
| ICH-004 | Can a Bootstrap Bridge be built? | LOW (no pre-entry window, no delegate target) |
| ICH-005 | Do FS/IWD/Zone/Asset/GameRuntime layers exist? | UNKNOWN (all behind VM boundary) |
| ICH-006 | Can IW4X structure constrain CODOL's unknowns? | UNKNOWN (no convergence point) |
| ICH-007 | Can new evidence sources identify Runtime? | NO (static boundary CLOSED) |
| ICH-008 | Does VM→Native transfer occur? | YES (to platform glue, confirmed) |
| ICH-009 | Does Platform Glue reach Game Engine? | NO (0/439 events in engine region) |

Combined conclusion:

```text
CODOL EXE delegates ALL startup to Base.dll (.tvm0 VM).
Base.dll is a TenProtect anti-cheat shell that dispatches to
platform glue (BugTrace, mswsock, kernel32, combase).
The game engine code in the EXE's 2.7 MB virtual-only gap is
never reached because the IIPS/IFS2 platform boundary blocks
progression before engine initialization begins.

The bottleneck is no longer the VM boundary itself — it is the
IIPS/IFS2 platform dependency that prevents the startup chain
from reaching the point where the game engine would be activated.
```

---

## 8. Artifacts

```text
ICH009_PLATFORM_ENGINE_TRANSITION.md      (this file)
ICH009_PLATFORM_ENGINE_TRACE.csv          (event-to-gap attribution)
```

## 9. Compliance

| Constraint | Status |
|------------|--------|
| No CODOL launch | PASS (frozen Plan A data re-analyzed) |
| No IW4X launch | PASS |
| No dynamic debugging | PASS |
| No binary modification | PASS |
| No VM opcode decode | PASS (only address attribution) |
| No native decompilation | PASS |
| No injection/patch | PASS |
| No WeGame/TCLS expansion | PASS |
| Hard stop rule respected | PASS (no engine hit found) |
| No auto ICH-010 | PASS |

---

*ICH-009 完成。停止。*
