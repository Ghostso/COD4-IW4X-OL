# ICH-022 - Engine Bootstrap Attribution

## Answer to Core Question

The function at **0x00CA0000** was executed at **t = 6.848s** (ICH-021
confirmed via global state change). However, its caller could NOT be
statically recovered from the EXE raw code, data sections, or Base.dll.

**CALLER_NOT_STATICALLY_RECOVERED** (STOP-4)

The caller is dynamically computed — most likely by the Base.dll .tvm0
VM dispatcher, which generates call targets as part of its bytecode
interpretation. This is consistent with the VM-decrypted engine model.

## Engine Bootstrap Chain

```text
Base.dll .tvm0 VM Dispatcher
  |
  | [VM decrypts code into gap: t≈5.075s]
  |
  | [VM dynamically dispatches to engine functions]
  |     [intermediate dispatch: NOT statically recoverable]
  |
  +-- 0x00CA0000: GLOBAL INITIALIZATION (t=6.848s)
  |     Writes pointer 0x009B9C00 to global slot 0x00E83C18
  |     Zeroes companion slot 0x00E83C1C
  |
  +-- [other engine functions, partially identified]
  |     0x009A0000: conditional dispatch → 0x9EE9B0 or 0x9FA390
  |     0x00B00000: virtual method dispatch via [esi+0x30]
  |
  |  t=7.630s: iips.dll loads (AFTER engine bootstrap)
  |  t≈8.0s: IIPS QoS failure
  |
  +-- Engine remains partially initialized
```

## The Value 0x009B9C00

This address is INSIDE the engine gap. It is stored into a global
variable by the first confirmed engine function. Its role is UNKNOWN
without runtime memory reading, but it is most likely:

- A pointer to an engine subsystem context object
- A configuration or descriptor structure

It is the FIRST known piece of engine state that persists after
initialization.

## IIPS Position

```text
Engine Bootstrap (0xCA0000) → ... → iips.dll loads → IIPS fails

IIPS appears AFTER initial engine bootstrap. It gates a LATER stage
of initialization (likely resource loading, filesystem access, or
network-dependent subsystems that require the IIPS/IFS2 framework).

The engine is NOT prevented from STARTING by IIPS.
The engine IS prevented from COMPLETING initialization by IIPS.
```

## Research Direction Update

The IIPS/Platform Glue investigation is now definitively closed.
The CODOL original runtime entry has been identified:

```text
Entry mechanism: Base.dll .tvm0 VM dispatch into decrypted engine code
Entry region:    VA 0x00994000..0x00CA789A (3.08 MB, zero-filled PE gap)
First confirmed function: 0x00CA0000 (global init)
First confirmed effect: 0x00E83C18 = 0x009B9C00
Time:            t = 6.848s (before iips.dll)
```

The next phase of research should focus on:
1. Reading the data at 0x009B9C00 during runtime (ReadProcessMemory)
2. Identifying the engine subsystem that this pointer represents
3. Determining what resources the engine needs that IIPS was
   supposed to provide (filesystem, network, configuration)
4. Evaluating whether the engine can be made to bypass IIPS
   for resource loading through alternative mechanisms
