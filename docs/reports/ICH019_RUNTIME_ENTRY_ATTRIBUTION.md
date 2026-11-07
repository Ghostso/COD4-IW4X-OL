# ICH-019 - Runtime Entry Attribution

## ICH-009 Correction

ICH-009 concluded `PLATFORM_TO_ENGINE = NOT_OBSERVED` based on 0/439
post-ordinal-1 events in the engine region. This conclusion requires
a critical correction:

ICH-009 tracked only:
1. CREATE_THREAD start addresses
2. EXCEPTION addresses

A same-thread CALL from raw code into the engine region would not
generate either event type. The 0/439 result is therefore **not
sufficient** to conclude that the engine region is never executed.

## Revised Assessment

```text
ICH-009 original conclusion:  Platform → Engine = NOT_OBSERVED
ICH-019 revised conclusion:   Platform → Engine = UNKNOWN

The 0/439 result only proves that no NEW THREAD starts in or
no EXCEPTION occurs in the engine region. It does NOT rule out
same-thread CALL execution.

The engine region is executable memory (PAGE_EXECUTE_READWRITE)
that starts as zero-filled pages. The 6978 call rel32 references
from raw code into the gap prove that the raw code expects valid
code to exist there at runtime.
```

## Engine Entry Mechanism

```text
EXECUTABLE_REGION_ORIGIN = RUNTIME_ALLOCATION (VM-decrypted code)

The mechanism is:
  1. Base.dll .tvm0 VM interpreter decrypts code into the 2.7 MB gap
  2. The gap is already mapped as PAGE_EXECUTE_READWRITE by the PE loader
  3. No VirtualAlloc/MapViewOfFile is needed (pre-reserved by PE)
  4. VM writes decrypted code, then dispatches execution into it

This is NOT:
  - Dynamic allocation (region is pre-reserved)
  - Section mapping (region is part of the EXE image)
  - Thread start (same thread executes)
  - External module (the gap is in the EXE's own address space)
```

## Evidence Summary

| Evidence | Supports VM-Decrypted Engine? | Notes |
|----------|------------------------------|-------|
| 6978 call rel32 from raw code to gap | YES | Raw code expects code in gap |
| Gap is zero in PE file | YES | Must be filled at runtime |
| Gap is PAGE_EXECUTE_READWRITE | YES | Writes are permitted |
| VM dispatcher confirmed running | YES | ICH-008 confirmed |
| TLS callback array empty | YES | Not TLS-based unpacker |
| No guard page exceptions | YES | Section is RWX, no guard |
| 0/439 events (ICH-009) | NEUTRAL | Does not detect same-thread CALL |
| Anti-cheat blocks debugger | NEUTRAL | Prevents instruction-level trace |
| 2.7 MB is substantial | YES | Consistent with game engine size |

## IIPS Dependency for Engine Entry

```text
IIPS_DEPENDENCY_FOR_ENGINE_ENTRY = NOT_PROVEN

The VM dispatch could theoretically reach the engine code:
  A) BEFORE IIPS initialization (VM runs first, decrypts engine, then IIPS)
  B) AFTER IIPS success (IIPS gates the engine activation)
  C) INDEPENDENTLY of IIPS (parallel path, not gated by IIPS)

The ICH-009 observation window (8.7s) did not detect engine execution,
but this observation is insufficient (does not detect CALL).

Without instruction-level tracing, we cannot determine whether the
VM dispatches to the engine before or after the IIPS gate.

The conservative conclusion is:
  IIPS is a PLATFORM PRECONDITION (it must succeed for the startup
  chain to progress normally), but it may not be the ONLY path to
  the engine code.
```

## What Would Confirm the Engine Entry

The minimum additional evidence needed:

1. **Memory read of the engine gap during runtime**: Read 100 bytes
   at RVA 0x594000 (or any engine address) while the process is
   running. If non-zero → code has been written → VM decrypted it.

2. **Instruction-level trace**: Set a hardware breakpoint or use
   Intel PT to capture execution at any engine address. This would
   directly confirm engine execution.

3. **VM bytecode decoding**: Decode the Base.dll .tvm0 bytecode to
   find VM instructions that write to the engine gap address range.

None of these have been attempted due to constraint limitations.

## NEXT_RESEARCH_DIRECTION

```text
1. Read the engine gap memory (e.g., ReadProcessMemory at RVA 0x594000)
   during a running CODOL process to confirm VM-decrypted code exists.

2. If non-zero code is found, identify the exact entry point by
   examining the code structure (function prologues, vtable pointers).

3. If zero, the engine gap is unused reserved space and the actual
   game runtime must be elsewhere (inside Base.dll .tvm0 or another
   mechanism entirely).
```
