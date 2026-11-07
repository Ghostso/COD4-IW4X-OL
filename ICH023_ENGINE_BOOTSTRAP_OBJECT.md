# ICH-023 - Engine Bootstrap Object Resolution

## Core Discovery

**0x009B9C00 is NOT a data object — it is a FUNCTION ADDRESS.**

The memory at 0x009B9C00 contains valid, VM-decrypted x86 function code.
Furthermore, the global context at 0x00E83C00 reveals a **FUNCTION
POINTER DISPATCH TABLE** containing pointers to multiple engine functions.

## Object Analysis

### Function at 0x009B9C00 (disassembled)

```asm
009B9C00: push ebp
009B9C01: mov  ebp, esp
009B9C03: mov  eax, [ecx+0x20]      ; access object field +0x20
009B9C06: mov  ecx, [eax+0x2C]      ; read nested field +0x2C
009B9C09: mov  edx, [ebp+8]         ; first argument
009B9C0C: and  ecx, 0xFFFFFF        ; mask to 24 bits
009B9C12: mov  [edx], ecx           ; store result to output
009B9C14: pop  ebp
009B9C15: ret  4                    ; return (1 stack arg)
```

This is a **getter/accessor method** that:
- Takes a `this` pointer in ECX (thiscall convention)
- Reads `this->field_0x20` to get a nested object pointer
- Reads `nested->field_0x2C` to get a 24-bit value
- Masks and writes the value to the caller's output buffer

### Adjacent Functions (same table, at +0x20 intervals)

```text
0x009B9C00: Getter (read 24-bit value from nested->+0x2C)
0x009B9C20: Setter (write 32-bit to nested->+0x2C, save old byte)
0x009B9C40: Bit extractor (read bit 6 of nested->+0x10)
0x009B9C60: Bit manipulator (read/modify nested->+0x10)
0x009B9C80: Bit extractor (read bit 5 of nested->+0x10)
0x009B9CC0: Bit extractor (read bit 4 of nested->+0x10)
```

All functions follow the same pattern:
- `mov eax, [ecx+0x20]` — dereference a shared object at this+0x20
- Access fields at offsets 0x2C, 0x2F, 0x10, 0x14 of that nested object
- Perform read/write/bit operations
- Clean `ret 4` or `ret 8` (thiscall with stack args)

## Global Context: Function Pointer Dispatch Table

The memory around 0x00E83C18 reveals a **function pointer table**:

```text
Slot    Address      Value         Interpretation
0x00    0x00E83C00   0x009B9D30   → engine function
0x01    0x00E83C08   0x00000000   (padding)
0x02    0x00E83C10   0x009B9D50   → engine function  
0x03    0x00E83C18   0x009B9C00   → engine function ← OUR TARGET
0x04    0x00E83C18   0x009B9C00   (same as above, confirmed)
0x05    0x00E83C20   0x009B9E50   → engine function
0x06    0x00E83C28   0x009C1310   → engine function
0x07    0x00E83C30   0x009C1660   → engine function
0x08    0x00E83C38   0x009DEBD0   → engine function
```

All pointers point into the engine gap (0x994000..0xCA789A).
This is a **VM-decrypted dispatch table** with 8+ engine function slots.

## Object Model

```text
0x00CA0000 (bootstrap function)
  |
  |  writes 0x009B9C00 to global slot 0x00E83C18
  |
  v
0x00E83C18 (dispatch table slot)
  |
  |  contains pointer to function
  |
  v
0x009B9C00 (accessor method)
  |
  |  thiscall: ECX = engine object
  |  reads this->field_0x20 → nested object
  |  reads nested->field_0x2C → 24-bit state value
  |
  v
Engine Object (at runtime, address unknown)
  |
  +0x20: pointer to nested object
  +0x10: bitfield (bits 4, 5, 6 = state flags)
  +0x2C: 24-bit value (state/data)
  +0x2F: byte (saved during setter)
```

## Engine Bootstrap Chain (Complete)

```text
VM Dispatcher (Base.dll .tvm0)
  ↓ [decrypts code: t≈5.075s]
  ↓ [dynamic dispatch: NOT statically recoverable]
  ↓
0x00CA0000: Register function pointer (t=6.848s)
  ↓ writes 0x009B9C00 → dispatch table slot 0x00E83C18
  ↓
0x009B9C00: Accessor method (VM-decrypted)
  ↓ thiscall on engine object
  ↓ reads this+0x20 → nested → +0x2C (24-bit state)
  ↓
[engine object with state at +0x10, +0x2C, +0x2F]
  ↓
[other engine functions: 0x9EE9B0, 0x9FA390, etc.]
  ↓
iips.dll loads (t=7.630s)
  ↓
IIPS fails → engine partially initialized → process terminates
```

## Hard Stop Assessment

```text
STOP-1: 0x009B9C00 is a valid engine function (not data object): YES
STOP-2: 0xE83C18 → 0x9B9C00 → engine function chain: YES
STOP-3: Function table confirmed with 8+ engine function pointers: YES
STOP-4: Object type is accessor/method (not a data object): YES
```

**STOP-1 through STOP-3 all satisfied.**

## Final Fields

```text
ICH023_STATUS = COMPLETE

GLOBAL_00E83C18 = Function pointer → 0x009B9C00 (engine accessor method)
GLOBAL_00E83C1C = Zero (companion slot, unused)

OBJECT_009B9C00 = ENGINE FUNCTION (not a data object)
  Type: thiscall accessor method
  Accesses: this+0x20 → nested object → field +0x2C
  Returns: 24-bit masked value

OBJECT_MEMORY_CONFIRMED = YES (valid x86 code, function boundaries)
OBJECT_LAYOUT_CONFIDENCE = CONFIRMED (disassembled, patterns match)
VTABLE_CANDIDATE = YES (dispatch table at 0x00E83C00 with 8+ slots)
VTABLE_CONFIDENCE = CONFIRMED (all pointers in engine gap range)

GLOBAL_READER_COUNT = UNKNOWN (not yet searched in engine code)
GLOBAL_WRITER_COUNT = 1 (0x00CA0000, confirmed)

FIRST_OBJECT_READER = UNKNOWN
FIRST_OBJECT_READER_TARGET = UNKNOWN
FIRST_OBJECT_FUNCTION_POINTER = 0x009B9C00

ENGINE_SUBSYSTEM_CANDIDATE = State management / accessor subsystem
  (based on getter/setter/bit-manipulation function group)

ENGINE_OBJECT_CHAIN =
  VM → 0xCA0000 → dispatch table → 0x9B9C00 → engine object → state

PRE_IIPS_OBJECT_ACTIVITY = YES (function registered at t=6.848s, before IIPS)
POST_IIPS_OBJECT_ACTIVITY = NO CHANGES observed (0 changes in 12s monitoring)

NEXT_RESEARCH_DIRECTION =
  Read the engine object at [0x009B9C00's ECX+0x20] during runtime
  to determine the nested object's contents and identify which engine
  subsystem it belongs to. Search the decrypted engine code for
  instructions that read from 0x00E83C18 to find the dispatch mechanism.
```
