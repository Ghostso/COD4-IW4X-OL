# ICH-020 - Engine Entry Attribution

## Summary of ICH-013 through ICH-020

| Round | Finding | Impact on Engine Entry |
|-------|---------|----------------------|
| ICH-013 | IIPS gate failure at 0x8189FEC | IIPS is A blocking boundary, not THE only one |
| ICH-014 | Four-stage pre-conditions satisfied | IFS2 would load if reached |
| ICH-015 | Debugger blocked by anti-cheat | Cannot trace iips.dll internals |
| ICH-016 | iips loads 3/3, IFS2 0/3 | IFS2 never loads normally |
| ICH-017 | Sub-ms transient refuted at 1ms | IFS2 load attempt confirmed absent |
| ICH-018 | QoS helper = Tencent QoS network check | IIPS fails due to unreachable server |
| ICH-019 | 6978 call targets to engine gap | Engine code expected by raw code |
| **ICH-020** | **Engine gap filled with valid x86 at t=5.075s** | **Engine code EXISTS before IIPS loads** |

## Revised Timeline

```text
t=0.000s   Process starts
t=0.037s   Base.dll loads (Platform VM host)
t=0.434s   BugTrace.dll loads (anti-cheat)
t=6.358s   TenProxy.dll + GbSpy.dll load (platform proxy)
t=5.075s   ← ENGINE GAP FILLED WITH x86 CODE ← BEFORE IIPS
t=7.630s   iips.dll loads
t≈8.0s     IIPS QoS helper fails (Tencent server unreachable)
t≈8.0s     WIN_IIPS_INIT_ERROR
t≈20s      Process terminates
```

**The engine code is decrypted at t≈5.075s, BEFORE iips.dll loads at
t≈7.6s. The engine gap filling is NOT dependent on IIPS.**

## Revised Blocking Boundary

```text
OLD MODEL (ICH-013 through ICH-018):
  IIPS failure → Engine never reached

REVISED MODEL (ICH-019/020):
  VM decrypts engine code into gap (t=5.075s)
  → Engine code EXISTS in memory
  → IIPS loads later (t=7.6s) and fails
  → Process terminates
  → Engine code was present but was it EXECUTED?

The blocking boundary is NOT "engine code not present"
The blocking boundary is "engine code present but execution path
not reaching it" OR "engine code reached but encountered an error"
```

## What We Know Now

```text
CONFIRMED:
  1. Engine gap contains valid x86 code at runtime (t=5.075s)
  2. Code has proper function boundaries (ret, int3 padding, prologue)
  3. Code includes virtual method calls (call ecx via vtable)
  4. Code includes global initialization (mov [0xE83C18], eax)
  5. Code is written BEFORE IIPS loads (t=5.075s < t=7.6s)
  6. The VM interpreter in Base.dll .tvm0 is the mechanism

UNKNOWN:
  1. Whether the engine code is ever EXECUTED (not just present)
  2. What is the first engine function called
  3. Why the process still terminates if engine code exists
  4. Whether engine execution requires IIPS success or not
```

## IIPS Dependency Re-evaluation

```text
IIPS_DEPENDENCY_FOR_ENGINE_ENTRY = NOT_PROVEN

The engine code is decrypted at t=5.075s, before iips.dll loads at
t=7.6s. This proves the VM's code decryption phase is independent
of IIPS.

However, engine code PRESENCE does not equal engine code EXECUTION.
The IIPS gate may control whether execution reaches the engine code
(e.g., by gating a jump/call from platform glue into the engine).

The distinction is:
  - Code DECRYPTION: independent of IIPS (confirmed)
  - Code EXECUTION: possibly dependent on IIPS (unknown)
```

## The Remaining Question

```text
The single remaining question for the CODOL startup chain:

  Is the decrypted engine code ever EXECUTED during the normal
  startup lifecycle, or does it sit in memory as prepared code
  that is never reached because the IIPS gate blocks the
  control flow transition?

Answer methods:
  1. Monitor global variables written by engine code (e.g., 0xE83C18)
     for value changes → confirms execution
  2. Hardware breakpoint on any engine address → blocked by anti-cheat
  3. ETW instruction-level trace → requires kernel-mode tooling
  4. Analyze the process's EIP/RIP at termination → requires debugger
```

## Final Status

```text
ICH020_STATUS = COMPLETE

ENGINE_REGION_BASE = 0x00994000
ENGINE_REGION_SIZE = 0x0031389A (3.08 MB)

DISK_ZERO_CONFIRMED = YES
RUNTIME_NONZERO_CONFIRMED = YES (952/1274 reads)
DECODE_TRANSITION_OBSERVED = YES
DECODE_TIME_FIRST = 5.075s
DECODE_TIME_COMPLETE = ~5.075s (bulk fill)

X86_CODE_CONFIRMED = YES (valid functions, ret, call, int3)
ENGINE_EXECUTION_CONFIRMED = NOT_YET (code exists, execution not traced)

FIRST_NONZERO_ADDRESS = 0x00994000
FIRST_CODE_ADDRESS = 0x00B00000 (complete function)
FIRST_EXECUTION_ADDRESS = UNKNOWN
FIRST_EXECUTION_TID = UNKNOWN
FIRST_EXECUTION_CALLER = UNKNOWN

VM_TO_ENGINE_CONFIDENCE = CONFIRMED
ENGINE_ENTRY_MECHANISM = VM_DISPATCH
RUNTIME_ENTRY_IDENTIFIED = PARTIAL

IIPS_DEPENDENCY_FOR_ENGINE_ENTRY = NOT_PROVEN
  (code decryption is IIPS-independent; execution dependency unknown)

NEXT_RESEARCH_DIRECTION = 
  Monitor global variables at engine-known addresses (e.g., 0xE83C18)
  during process lifetime to confirm engine code execution.
  If values change → engine code has executed.
  If values remain at initial state → engine code is present but dormant.
```
