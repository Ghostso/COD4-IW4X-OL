# ICH-015 - Pre-Stage-1 Divergence

## Status: CANNOT BE CONFIRMED OR REFUTED

## Why

The ICH-015 task requires direct observation of:

```text
InitInGameApp
    |
    +-- QoS helper (iips.dll+0x6D20)
    |     returns non-zero: continue
    |     returns zero: error branch
    |
    +-- initIfsLib (iips.dll+0x9570)
          |
          +-- Stage 1: LoadLibraryW("IFS2.dll") at iips.dll+0x96E9
```

To observe this control flow, we need to set breakpoints inside iips.dll.
To set breakpoints, we need a debugger. When we use a debugger:

```text
Result from ICH-015 passive observer (3 runs):
  iips.dll NEVER loads under debugger
  Exit code = 0xE06D7363 (MSVC C++ exception)
  Anti-cheat (TenProtect) prevents iips.dll from loading

This is consistent with ICH-011:
  BugTrace fail-fast under debugger (0xC0000409)
  Anti-cheat detects DEBUG_ONLY_THIS_PROCESS flag
```

Without iips.dll loading, no internal breakpoints can fire. Without
internal breakpoints, no control flow can be observed.

## The Fundamental Constraint

```text
To observe:  Set breakpoints inside iips.dll
To set BPs:  Need debugger attached
To attach:   Must use DEBUG_ONLY_THIS_PROCESS flag
With flag:   Anti-cheat prevents iips.dll from loading
Without DLL: No code to break on
             → Infinite loop of constraint
```

## What CAN be observed (without debugger)

```text
Normal -q launch (EX-057, non-invasive kernel image trace):
  iips.dll loads:     YES (confirmed at module level)
  iips.dll unloads:   YES (confirmed after ~6.49s)
  IFS2.dll loads:     NO (never appears)
  Fatal error:        YES (WIN_IIPS_INIT_ERROR / 0x8189FEC)

EX-053 (three path causality experiments):
  IFS2.dll position changed 3 ways: no outcome change
  iipsinit_seen: YES in all experiments

These facts narrow the boundary but cannot tell us:
  - Whether initIfsLib is actually called
  - Whether LoadLibraryW is actually called
  - Whether QoS helper returns 0 or non-zero
  - Where the divergence occurs (if any)
```

## What is needed to break through

The minimum experiment to resolve pre-Stage-1 divergence requires
one of:

1. **Kernel-mode ETW** with function-level CallStack sampling
   - No user-mode breakpoint needed
   - Does not trigger anti-cheat
   - Can capture iips.dll function entry/return at kernel level
   - Complexity: HIGH (requires custom ETW provider or xperf)

2. **Hardware breakpoint (DR registers)**
   - Does not modify memory (no 0xCC byte)
   - May not trigger anti-cheat response
   - Still requires debugger (but anti-cheat may not detect DR-based BPs)
   - Complexity: MEDIUM

3. **Page-guard based observation**
   - Set PAGE_GUARD on iips.dll code pages
   - Single-step on guard exception
   - No 0xCC byte, but still requires debugger
   - Complexity: HIGH

4. **Detoured normal-run process with passive DLL**
   - Inject a passive observer DLL that monitors without patching
   - Still technically injection (prohibited)

All approaches except #1 are technically incompatible with the
"no injection / no patch / no hook" constraints. Approach #1 (ETW)
is the only method that could work within the letter of the constraints.

## Conclusion

```text
PRE_STAGE1_DIVERGENCE = UNKNOWN

Cannot be confirmed or refuted by ICH-015 because the observation
mechanism (breakpoints) is incompatible with the anti-cheat
protection that ICH-011 already confirmed.

This is NOT an experimental failure. It is a confirmed boundary of
the current constraint set. The boundary is: user-mode breakpoints
inside iips.dll trigger anti-cheat response that prevents iips.dll
from loading.
```

## Research Direction Impact

ICH-014 concluded: "Either pre-Stage-1 divergence or Stage 1 failure.
Cannot distinguish without caller-filtered trace."

ICH-015 attempted the trace and found: "Trace is impossible under
current constraints."

The combined conclusion is:

```text
The four-stage IIPS initialization gate exists statically.
All four stages have complete branch structures.
IFS2.dll satisfies all static pre-conditions.
BUT the actual runtime control flow cannot be observed because
anti-cheat prevents breakpoint-based observation of iips.dll.

PRIMARY_BLOCKING_BOUNDARY = IIPS initialization gate
REFINED_BOUNDARY = iips.dll internal control flow (unobservable
without kernel-mode trace or constraint modification)
```
