# ICH-012 — Unknown Native Layer / Platform Preconditions

## Objective

Determine whether an unrecognized Native intermediate layer exists
between VM Platform and the EXE 2.7 MB Game Engine region.

## Evidence Basis

- ICH-008 confirmed VM→Native transfer events
- ICH-009 complete post-ordinal-1 event attribution (17 events, run ORD1_A_01)
- ICH-009 module attribution of all thread starts and exceptions
- Base ordinal-1 lifecycle (3/3 stable runs)

## Previously Unresolved Target Resolution

ICH-008 identified one unresolved native thread start at `0x5F796178`.

### Resolution (ICH-009)

```text
Address:      0x5F796178
Module:       codoMP_client_shipRetailBase.dll
Module base:  0x5CE30000
RVA:          0x5F796178 - 0x5CE30000 = 0x2966178
Section:      .tvm0
Classification: Base.dll .tvm0 VM internal thread
```

This is NOT an unknown native layer. It is VM bytecode execution
inside Base.dll's protected section.

## Unknown Native Layer Assessment

```text
UNKNOWN_NATIVE_LAYER = NOT_OBSERVED
```

All post-ordinal-1 events in 3/3 stable runs resolve to known modules:

| Thread Start | Module | RVA | Classification |
|-------------|--------|-----|----------------|
| 0x5D07D060 | Base.dll | .tvm0+0x24D060 | VM internal |
| 0x5EB2CFAA | Base.dll | .tvm0+0x1FCFAA | VM internal |
| 0x76345D40 | system DLL | — | OS |
| 0x72A81D50 | mswsock.dll | .text+0x1D50 | OS (network) |
| 0x683BB233 | BugTrace.dll | .text+0xB233 | Platform (anti-cheat) |
| 0x5F796178 | Base.dll | .tvm0+0x2966178 | VM internal (resolved) |

No thread start address falls in an anonymous executable region,
no unexpected module is loaded, and no unknown native layer is
identified between VM Platform and Game Engine.

## Unknown DLL Load

```text
UNKNOWN_DLL_LOAD = NOT_OBSERVED
```

All module loads in the shared timeline (3/3 runs) are:

```text
codoMP_client_shipRetailBase.dll, libcef.dll, BugTrace.dll,
ntdll.dll, kernel32.dll, KernelBase.dll, combase.dll, mswsock.dll,
and standard Windows system DLLs.
```

No unknown or unexpected native module appears after ordinal-1.

## Unknown Thread Handoff

```text
UNKNOWN_THREAD_HANDOFF = NOT_OBSERVED
```

All thread starts resolve to confirmed modules. No thread start
address is unattributed or falls in the EXE 2.7 MB engine region.

## Platform Precondition

```text
PLATFORM_PRECONDITION = CONFIRMED
```

The IIPS initialization gate (`WIN_IIPS_INIT_ERROR` at `EXE 0x8189FEC`)
is the confirmed platform precondition that blocks Engine activation.
This is supported by:

1. ICH-010: `iips.dll` loads/unloads with no IFS2 ever observed
2. ICH-011: BugTrace participates in Platform but never reaches Engine
3. ICH-009: 0/439 post-ordinal-1 events hit the Engine region

## Unknown Layer to Engine

```text
UNKNOWN_LAYER_TO_ENGINE = NOT_OBSERVED
```

No unknown layer exists. No path from any component (known or unknown)
to the EXE 2.7 MB Game Engine region was observed.

## Hard Stop Check

Platform → failure/termination confirmed with no unknown intermediate
layer. Hard stop condition met.

