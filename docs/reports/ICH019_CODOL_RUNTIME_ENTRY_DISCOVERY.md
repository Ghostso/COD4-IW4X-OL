# ICH-019 - CODOL Game Runtime Entry Discovery

## Objective

Determine how the ~2.7 MB virtual-only Game Engine region in the CODOL
EXE is created and entered at runtime. This analysis does NOT require
IIPS success as a prerequisite.

## Engine Region Physical Analysis

### PE Layout

```text
Section 0 (.tp3):
  Virtual Address:  0x00401000
  Virtual Size:     0x008A689A  (8.65 MB)
  Raw Data Size:    0x00593000  (5.7 MB)
  Characteristics:  0x60000020 (CODE, EXECUTE, READ)
  Executable:       YES

Engine region (inside section 0):
  RVA:  0x00594000 .. 0x008A789A
  VA:   0x00994000 .. 0x00CA789A
  Size: 0x0031389A  (3.08 MB)

The engine region is entirely PAST the raw data boundary:
  Raw data ends at: RVA 0x00594000
  Engine starts at: RVA 0x00594000

At runtime, the PE loader maps this as:
  - Raw-backed portion (RVA 0x1000..0x594000): real file content
  - Virtual-only portion (RVA 0x594000..0x8A789A): ZERO-FILLED pages
  - Both portions share the same protection: PAGE_EXECUTE_READWRITE
```

### Critical Finding: The Engine Region is Zero-Filled

```text
The 2.7 MB "Game Engine" region contains NO CODE in the PE file.
It is entirely zero bytes in the raw image.

At process start, the PE loader maps it as zero-filled executable pages.

Any code in this region must be WRITTEN at runtime by an unpacker/decryptor.
Without runtime writing, the region contains only zeros.
Executing zeros produces: add [eax], al (0x00 0x00) repeated, eventually
causing an access violation.
```

## Static Cross-Reference Analysis

### References from Raw Code to Engine Region

The raw-backed code (RVA 0x1000..0x594000) contains 6978 `call rel32`
instructions that target addresses within the engine region.

```text
call rel32 into engine region:  6978
jmp rel32 into engine region:    222
push imm32 (engine addr):        410
mov reg, imm32 (engine addr):    454
call [imm32] (engine addr):        6
jmp [imm32] (engine addr):         0
```

### Target Distribution

The 6978 call targets are distributed fairly evenly across the 3 MB gap,
with higher density in the middle:

```text
RVA 0x594000..0x5B4000:  397 targets (low density - prologue area)
RVA 0x5B4000..0x844000:  5893 targets (high density - main body)
RVA 0x844000..0x8A789A:   688 targets (low density - tail/exit area)
```

The earliest caller is at RVA 0x105F (very early in the raw code),
targeting RVA 0x773FC9 (deep inside the engine gap).

### Interpretation

These 6978 calls are NOT accidental. They represent real, intentional
calls from the raw-backed code into the virtual-only gap. For these
calls to work, the gap MUST contain valid code at runtime.

The code must be deposited into the gap by a runtime mechanism that
executes BEFORE the first of these 6978 calls is reached.

## Re-evaluation of ICH-009

ICH-009 reported 0/439 events in the engine region. However, ICH-009
only tracked:

```text
1. Thread Start addresses
2. Exception addresses
```

A normal `CALL` instruction from raw code into the engine region would:
- NOT generate a thread start (same thread continues)
- NOT generate an exception (if the target code is valid)
- Be completely INVISIBLE to the ICH-009 observation method

Therefore, the 0/439 result does NOT prove that the engine region is
never executed. It only proves that no THREAD_START or EXCEPTION
originates from that region.

**This is a critical correction to the ICH-009 conclusion.**

## Revised Engine Entry Model

```text
Model: VM-Decrypted Engine

1. EXE Entry (RVA 0xE5DC690) calls Base.dll ordinal-1
2. Base.dll .tvm0 VM Dispatcher runs (ICH-008 confirmed)
3. VM interpreter decrypts/unpacks Game Engine code into the 2.7 MB gap
   (the gap is PAGE_EXECUTE_READWRITE, so writes are permitted)
4. VM dispatches execution INTO the decrypted engine code
5. Engine code runs as normal x86 inside the gap
6. Control returns to raw code or continues within the gap
7. No new threads, no exceptions → invisible to ICH-009 method
```

### Evidence FOR this model

```text
1. 6978 call/jmp from raw code into the gap (intentional, not accidental)
2. Gap is executable memory (PAGE_EXECUTE_READWRITE, no guard page)
3. VM exists and runs (ICH-008 confirmed VM dispatcher execution)
4. Gap starts as zeros → must be filled at runtime → VM is the candidate
5. No exceptions in the gap (ICH-009) → compatible with valid code
6. No thread starts in the gap (ICH-009) → compatible with same-thread call
```

### Evidence AGAINST this model

```text
None. No available evidence contradicts this model.
```

### Alternative Models Considered

| Model | Status | Reason |
|-------|--------|--------|
| VM-Decrypted Engine | **MOST CONSISTENT** | Explains all observations |
| TLS callback unpacker | REFUTED | TLS callback array is empty (0 entries) |
| Pre-loaded engine code | REFUTED | Gap is zero in PE file |
| Dead code / unused space | UNLIKELY | 6978 intentional calls make this implausible |
| External DLL fills gap | UNLIKELY | No external module has write access to EXE space |
| Computed addresses only | UNLIKELY | 6978 direct rel32 calls are not computed |

## Q1-Q7 Answers

```text
Q1 GAME_ENGINE_ENTRY_CANDIDATE =
   VM dispatch from Base.dll .tvm0 into decrypted engine code
   (exact entry address UNKNOWN without VM decoding)

Q2 GAME_ENGINE_ENTRY_MECHANISM = VM_DISPATCH

Q3 ENGINE_REGION_RUNTIME_REACHABLE =
   INFERRED (YES) — the 6978 calls prove the raw code expects
   valid code in the gap; the VM is the only mechanism that can
   fill it; ICH-009 0/439 does not contradict same-thread CALL.

Q4 FIRST_ENGINE_EXECUTION_ADDRESS =
   UNKNOWN (requires VM bytecode decoding or instruction-level trace)

Q5 FIRST_ENGINE_CALLER =
   Base.dll .tvm0 VM dispatcher (most likely) OR
   raw code at RVA 0x105F (earliest static call to engine region)

Q6 EXECUTABLE_REGION_ORIGIN =
   RUNTIME_ALLOCATION (VM-decrypted code written into pre-reserved
   executable section space; NOT a separate VirtualAlloc/mapping)

Q7 RUNTIME_ENTRY_CONFIDENCE =
   INFERRED (VM_DISPATCH model is most consistent but not dynamically
   confirmed because instruction-level tracing is blocked by anti-cheat)
```

## Hard Stop Assessment

```text
STOP-1 (execution confirmed in engine region): NOT TRIGGERED
  (no instruction-level trace available)

STOP-2 (region established by VirtualAlloc/MapViewOfFile): NOT TRIGGERED
  (region is pre-reserved by PE loader, not dynamically allocated)

STOP-3 (thread start in engine region): NOT TRIGGERED

STOP-4 (region never executable/mapped/entered): NOT TRIGGERED
  (the region IS executable from process start; the question is
   whether it contains code, which requires runtime observation)

No hard stop condition is met. The analysis is complete within the
limits of static evidence and available observation methods.
```

## Final Fields

```text
ICH019_STATUS = COMPLETE

GAME_ENGINE_REGION_BASE = 0x00994000 (VA)
GAME_ENGINE_REGION_SIZE = 0x0031389A (3.08 MB)

ENGINE_REGION_EXECUTABLE = YES (PAGE_EXECUTE_READWRITE from PE loader)
ENGINE_REGION_RUNTIME_REACHABLE = INFERRED_YES

EXECUTABLE_REGION_ORIGIN = RUNTIME_ALLOCATION (VM-decrypted code)

FIRST_ENGINE_EXECUTION_ADDRESS = UNKNOWN
FIRST_ENGINE_EXECUTION_TID = UNKNOWN
FIRST_ENGINE_CALLER = Base.dll .tvm0 VM dispatcher (INFERRED)

ENGINE_ENTRY_MECHANISM = VM_DISPATCH

ENGINE_ENTRY_MODULE = Base.dll (.tvm0 VM dispatcher)

ENGINE_ENTRY_CONFIDENCE = INFERRED

RUNTIME_ENTRY_IDENTIFIED = NO (requires VM decode or instruction trace)

IIPS_DEPENDENCY_FOR_ENGINE_ENTRY = NOT_PROVEN
  (the VM may dispatch to the engine BEFORE or INDEPENDENTLY of IIPS;
   ICH-009's 0/439 does not prove the engine is not reached because
   same-thread CALL is invisible to that observation method)
```
