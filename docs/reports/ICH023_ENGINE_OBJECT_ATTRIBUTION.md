# ICH-023 - Engine Object Attribution

## What We Now Know About the CODOL Engine Bootstrap

The investigation has progressed from "does the engine exist?" to
"what does the engine look like internally?" Here is the complete chain:

### Complete Bootstrap Chain

```text
1. VM Decryption (t≈5.075s)
   Base.dll .tvm0 VM interpreter decrypts ~3.08 MB of code
   into the EXE's virtual-only gap (VA 0x994000..0xCA789A)

2. Dynamic Dispatch (caller not statically recoverable)
   VM generates and executes a call to 0x00CA0000

3. Function Registration (t=6.848s)
   0x00CA0000 stores the address 0x009B9C00 into
   global dispatch table slot 0x00E83C18

4. Function Pointer Table
   0x00E83C00 is a dispatch table with 8+ slots,
   each containing a pointer to a VM-decrypted engine function.
   All pointers are in the engine gap range.

5. Accessor Methods
   0x009B9C00 and adjacent functions (+0x20 intervals) form a
   set of getter/setter/bit-manipulation methods that operate
   on an engine object accessed via ECX (thiscall).

6. Engine Object Structure
   The object accessed by these methods has:
   - field +0x20: pointer to nested object
   - nested +0x10: bitfield (state flags at bits 4, 5, 6)
   - nested +0x2C: 24-bit value (state/data)
   - nested +0x2F: byte (saved state)
```

### What This Means

The CODOL engine is a **real, complex native code system** that:
- Is decrypted into memory by the TenProtect VM
- Has a dispatch table of function pointers
- Uses object-oriented patterns (thiscall, vtable-like dispatch)
- Manages state through accessor methods with bit manipulation
- Begins executing BEFORE the IIPS platform gate

### IIPS Role Clarification

IIPS does NOT prevent the engine from:
- Being decrypted into memory
- Having its dispatch table populated
- Having its initial functions execute

IIPS DOES appear to gate:
- Full engine initialization beyond the bootstrap phase
- Resource loading / filesystem access
- Network-dependent subsystems
- The transition from "engine code running" to "game playable"

### The IIPS Gate Re-examined

The original model was:
```
IIPS gate → Engine activation
```

The corrected model is:
```
Engine bootstrap (independent of IIPS)
  ↓
Engine initial functions run
  ↓
IIPS loads and fails (external dependency)
  ↓
Engine cannot proceed to full initialization
  ↓
Process terminates
```

The IIPS gate is a **mid-chain checkpoint**, not an entry gate.
It sits between "engine bootstrap" and "full engine operation."

### Research Phase Transition

The project has moved through three phases:

1. **ICH-001~009**: "Can we find the Runtime?" → YES, in VM-decrypted engine gap
2. **ICH-010~018**: "Does IIPS block it?" → YES, but AFTER bootstrap
3. **ICH-019~023**: "What IS the engine?" → Object-oriented native code with dispatch tables and accessor methods

The next phase should focus on:
- Identifying the engine subsystem that the accessor methods serve
- Understanding what resources the engine needs to progress
- Determining if the IIPS dependency can be satisfied or bypassed
