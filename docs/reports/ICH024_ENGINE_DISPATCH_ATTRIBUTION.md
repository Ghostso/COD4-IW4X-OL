# ICH-024 - Engine Dispatch Attribution

## Summary

The CODOL Engine dispatch table at 0x00E83B00..0x00E83E00 contains
**96 confirmed VM-decrypted function pointers**, all targeting valid
x86 code within the engine gap (VA 0x00994000..0x00CA789A).

## Complete Engine Bootstrap Architecture

```text
Base.dll .tvm0 VM Dispatcher
       │
       │ t≈5.075s: Decrypts 3.08 MB code into engine gap
       │
       ▼
┌─────────────────────────────────────────────────┐
│ ENGINE GAP (VA 0x00994000..0x00CA789A)          │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │ Dispatch Table (0x00E83B00..0x00E83E00)  │  │
│  │ 96 function pointers, 8 bytes per entry  │  │
│  │                                          │  │
│  │  Slot 0x18: → 0x009B9C00 (state getter)  │  │
│  │  Slot 0x00: → 0x009B9D30 (state accessor)│  │
│  │  ... 94 more function pointers ...       │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │ Engine Functions (VM-decrypted x86)      │  │
│  │                                          │  │
│  │  0x009B9C00..0x009B9CC0: State accessors │  │
│  │  0x009B9D30..0x009B9E90: FP operations   │  │
│  │  0x009C0010..0x009C3920: Complex init    │  │
│  │  0x009C4670..0x009C8FE0: Subsystem ops   │  │
│  │  0x009CD630..0x009DEBD0: Large functions │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │ Engine Objects (runtime, in data area)   │  │
│  │                                          │  │
│  │  Primary State Object:                   │  │
│  │    +0x20 → Nested State                  │  │
│  │      +0x10: bitfield (bits 4/5/6)        │  │
│  │      +0x2C: 24-bit state value           │  │
│  │      +0x2F: saved byte                   │  │
│  │                                          │  │
│  │  Secondary Object: accessed via +0x14    │  │
│  │  Tertiary Object: accessed via +0x4C     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
       │
       │  t=6.848s: First confirmed engine function executes
       │           (0x00CA0000 → writes to dispatch table)
       │
       │  t=7.630s: iips.dll loads
       │  t≈8.0s:   IIPS QoS fails
       │
       ▼
  Engine remains partially initialized
  Process terminates
```

## Research Progress Summary

| Metric | ICH-019 | ICH-020 | ICH-021 | ICH-022 | ICH-023 | ICH-024 |
|--------|---------|---------|---------|---------|---------|---------|
| Engine code exists | INFERRED | CONFIRMED | — | — | — | — |
| Engine code executes | — | — | CONFIRMED | — | — | — |
| Bootstrap function | — | — | 0xCA0000 | — | — | — |
| Dispatch table | — | — | — | 8 slots | 8 slots | **96 slots** |
| Engine objects | — | — | — | — | 1 (state) | **3+ types** |
| Known engine functions | 6978 call targets | 7 probes | 1 confirmed | 9 classified | 6 family | **96 unique** |

## The Engine is Real

The CODOL Game Engine is a substantial native code system:

- **96 virtual functions** in the dispatch table alone
- **At least 3 distinct subsystem objects** (accessed via +0x20, +0x14, +0x4C)
- **State management** with bitfields and 24-bit values
- **Floating-point computation** functions
- **Complex initialization routines** with large stack frames
- **Object-oriented architecture** (thiscall, virtual dispatch, nested objects)

This is NOT a stub, NOT a loader shim, NOT a decryption stub.
This is a **game engine**.

## NEXT_RESEARCH_DIRECTION

The IIPS/Platform Glue investigation is definitively closed.
The Engine runtime entry is confirmed. The next phase should focus on:

1. **Identify the engine object that owns the dispatch table**:
   Search the engine code for `mov ecx, 0x00E83B00` or similar
   patterns that set up the vtable pointer on an engine object.

2. **Map subsystem objects to their functions**:
   Group the 96 functions by which object they access (+0x20, +0x14, +0x4C)
   to identify distinct subsystems.

3. **Determine what the engine needs to progress**:
   The engine bootstrap runs, but something prevents full initialization.
   Identify what state the engine is in when the process terminates
   and what it was trying to do next.
