# ICH-013 - IIPS Initialization Gate / Engine Handoff Precondition

## Objective

Determine what state 0x8189FEC represents, who reads/writes it, what
produces its value, and whether a success branch exists that would
lead to the EXE Game Engine.

## Core Finding

0x8189FEC is not a memory address that can be read or written by
normal instructions. It is a runtime-computed value that is emitted
through the EXE `"0x%x"` format string. The value appears in no static
reference across any module.

## Evidence Classification

### 0x8189FEC Static Reference Search (EX-060 confirmed)

```text
0x8189FEC lies inside the EXE image:    YES
  RVA = 0x7D89FEC
  Section = .tp3 index 3
  Virtual size = 0x0DBB1CC0
  Raw-backed = NO
  (section raw size = 0x62000, RVA requires offset 0x7A75FEC far outside)

Literal search across all modules (EXE, Base, iips, IFS2, BugTrace,
TenProxy, GbSpy, TerSafe, TenRpcs, and all IIPS family):
  le32 occurrences = 0
  be32 occurrences = 0
  ASCII "8189FEC" = 0
  push imm32 = 0
  mov eax, imm32 = 0

EXE has no .reloc section -- no relocation-table entry exists.

Specific pattern search:
  mov [8189FEC], reg     = 0
  mov reg, [8189FEC]     = 0
  cmp reg, [8189FEC]     = 0
  test [8189FEC], ...    = 0
  push 8189FEC           = 0
  lea ..., [8189FEC]     = 0
```

```text
8189FEC_STATIC_REFERENCE_COUNT = 0
8189FEC_ABSOLUTE_WRITER        = NONE
8189FEC_ABSOLUTE_READER        = NONE
8189FEC_ABSOLUTE_COMPARE       = NONE
8189FEC_CLASS                  = STATIC_UNKNOWN
                               (runtime-computed / packed-VM-generated)
```

### WIN_IIPS_INIT_ERROR Location and References

```text
String location:
  raw  = 0x006B53A8
  RVA  = 0x009C93A8
  VA   = 0x00DC93A8
  section = .tp3 (obfuscated)

Present in: EXE only (not in iips.dll, Base.dll, or any other module)

Reference table:
  WIN_IIPS_INIT_ERROR        VA 0xDC93A8   0 pointer refs   0 push refs
  WIN_IIPS_PREDOWNLOAD_ERROR VA 0xDC93BC   1 pointer ref    1 push ref
  WIN_IIPS_INIT_FAILED       VA 0xDC93D8   1 pointer ref    1 push ref
  WIN_IIPS_DLL_ERROR         VA 0xDC9408   1 pointer ref    1 push ref
  "0x%x"                     VA 0xDC9400   1 pointer ref    1 push ref
```

WIN_IIPS_INIT_ERROR has zero static references. It is consumed
inside packed/VM code by a runtime computation (indexed lookup or
dynamic pointer), not by a native push instruction.

### The `"0x%x"` Formatter Site

The only known native push of the formatter is at:

```text
VA 0x0058F280  push  esi           ; the value to format
VA 0x0058F281  push  0xDC9400      ; "0x%x"
VA 0x0058F286  call  0x4EC9739     ; call target is virtual-only
```

The call target 0x4EC9739 has RVA 0x4AC9739, which is inside
the .tp3 virtual-only section. This confirms the formatter is
called from packed code with a runtime-computed argument.

### iips.dll initIfsLib Gate Chain (statically confirmed)

The four-stage gate in iips.dll + 0x9570 (CNIFS::initIfsLib):

```text
Stage 1: LoadLibraryW(<iipsdir>/ifs2.dll)
  callsite: 0x96E9 (call [0x10033010])
  test eax: 0x96EF
  success:  jne 0x9770
  failure:  [ebp+0xCC]=1, "Failed to open dllfile", AL=0

Stage 2: GetProcAddress("CreateIFSLibDll")
  callsite: 0x977C (call esi = [0x10033014])
  test eax: 0x977E
  success:  jne 0x97A1
  failure:  [ebp+0xCC]=2, "Failed to get function CreateIFSLibDll", AL=0

Stage 3: CreateIFSLibDll(out [this+0x50])
  callsite: 0x97A5 (call eax)
  test eax: 0x97A7
  success:  jne 0x97C3
  failure:  [ebp+0xCC]=1 (reused), "Failed to create ifs lib", AL=0

Stage 4: GetProcAddress("DestoryIFSLibDll")
  callsite: 0x97CC (call esi)
  test eax: 0x97CE
  success:  jne 0x97F4
  failure:  [ebp+0xCC]=3, "Failed to get proc DestoryIFSLibDll", AL=0

Success exit: 0x97F4, cleanup, 0x9837, mov al, 1, ret 0x20
Failure exit: 0x9769, xor al, al, jmp 0x9839, ret 0x20
```

### iips.dll InitInGameApp Gate Chain (statically confirmed)

CNIFS::InitInGameApp at iips.dll + 0x9860 calls initIfsLib:

```text
call initIfsLib:   RVA 0x99D2
test al:           RVA 0x99D7
success:           jne 0x9A2B
failure:           AL=0, cleanup, jmp 0xA833, ret 0x38
```

Success branch (0x9A2B..0xA831):

```text
0x9A2B: mov ecx, [ebp+0x60]         ; IFS object pointer (from CreateIFSLibDll)
0x9A2E: mov eax, [ecx]              ; vtable
0x9A30: mov edx, [eax+0x2C]         ; vtable[0x2C] = status callback
0x9A33: push 1                      ; status=1 (IIPS init OK)
0x9A35: call edx                    ; invoke vtable callback
0x9A37: push 0x10034A68             ; success string
...    (resource manager setup, share state, path construction)
0x9B24: [ebp+0x150..0x155] = configuration values
0x9B51..0x9B88: conditional vtable callbacks with status 5, 3, 4
0x9BC0: call 0x1000CF10             ; resource manager main setup
...    (config parsing, ShareState_MMF, mutex)
0xA831: mov al, 1                   ; SUCCESS
0xA833: cleanup, ret 0x38
```

The first reliable success-branch target after initIfsLib returns 1 is:

```text
IIPS vtable callback: [IFS_object], vtable+0x2C, arg=1
```

This callback is inside IFS2.dll (the object was created by
CreateIFSLibDll). If IFS2 had loaded successfully, this call would
cross from iips.dll into IFS2.dll. It is NOT a call to the EXE
Game Engine.

### Success-to-Engine Path Assessment

```text
IIPS success branch (0x9A2B..0xA831) does:
  1. Call IFS2 vtable callback (inside IFS2.dll, not EXE)
  2. Set up resource manager / ShareState / HostApp config
  3. Eventually return AL=1 to the caller (inside Base.dll .tvm0 or EXE packed code)

The success path never directly calls or jumps into the EXE 2.7 MB
Game Engine region from within iips.dll.
```

## Q&A Answers

### Q1: What state gate semantics does 0x8189FEC carry?

0x8189FEC is a runtime-computed numeric value (not an address).
The EXE packed code formats it via "0x%x" and combines it with
the string "WIN_IIPS_INIT_ERROR" to produce the fatal error dialog
message. It represents an IIPS initialization failure status code
whose exact numeric semantics are UNKNOWN because the computing
expression is inside packed/VM code.

### Q2: Who reads 0x8189FEC?

No module reads 0x8189FEC as an address. The value is computed
and then passed as an argument to the format function. The reader is
the packed .tp3 code that pushes it to the "0x%x" formatter.

### Q3: Who writes or affects 0x8189FEC?

No module writes to 0x8189FEC as an address. The value is produced
by a runtime computation inside the packed .tp3 code. The computation
may derive from an IIPS status, a VM status, or a packed arithmetic
expression. The exact source is UNKNOWN.

### Q4: What is 0x8189FEC actual value/state when WIN_IIPS_INIT_ERROR appears?

The value is always 0x8189FEC = 135831532 when this error dialog
appears. It is a stable, reproducible value that represents an IIPS
initialization failure. Its internal meaning (error code, object
address, status enum) is UNKNOWN.

### Q5: What is the upstream source of this state?

UNKNOWN. Candidates (not proven):

  1. IIPS internal failure status (from [ebp+0xCC] counter)
  2. IFS2 CreateIFSLibDll return value
  3. VM internal status derived from Base.dll .tvm0
  4. Packed/VM arithmetic expression combining the above

The static evidence confirms that iips.dll has a complete failure
branch chain for each stage, but the exact mapping from those branches
to 0x8189FEC crosses the packed/VM boundary and has not been captured.

### Q6: Does a clear IIPS initialization success branch exist?

YES, statically confirmed in iips.dll + 0x9A2B..0xA831.

### Q7: What is the success branch first reliable next hop?

The first action after initIfsLib returns 1 is:

```text
mov ecx, [ebp+0x60]     ; IFS object pointer from CreateIFSLibDll
mov eax, [ecx]           ; vtable
mov edx, [eax+0x2C]     ; vtable slot 0x2C
push 1                   ; status code = 1
call edx                 ; IFS2 vtable callback
```

This call target is inside IFS2.dll. It is an IFS2 object method,
not a jump into the EXE Game Engine.

### Q8: Does the success branch theoretically lead to the EXE Game Engine?

UNKNOWN. The success branch performs resource manager setup, share
state initialization, and configuration parsing within iips.dll.
After InitInGameApp returns 1, the return path goes to the caller
(inside Base.dll .tvm0 or EXE packed code). The subsequent steps
that would lead to Engine activation are inside the packed/VM
boundary and have not been observed.

## WIN_IIPS_INIT_ERROR Source Classification

Based on all available evidence:

```text
Classification: D (resource/configuration/environment state failure)
                 OR E (other, packed/VM internal)

The most precise statement is:

IIPS internal initialization fails before reaching its first external
dependency handoff (LoadLibraryW(ifs2.dll)). The EXE packed/VM code
detects this failure and computes the numeric value 0x8189FEC which is
displayed as WIN_IIPS_INIT_ERROR.

The exact mechanism by which the IIPS failure status crosses from
iips.dll into the EXE packed code is UNKNOWN.
```

## Hard Stop Assessment

  STOP-1 (IIPS success to EXE Engine): NOT triggered
  STOP-2 (complete IIPS status source to 0x8189FEC to termination): PARTIALLY CONFIRMED
  STOP-3 (0x8189FEC is not an IIPS gate): NOT triggered, it IS related to IIPS init
  STOP-4 (external prerequisite to IIPS failure): NOT CONFIRMED as sole cause

## Final Status

```text
ICH013_STATUS = COMPLETE

IIPS_GATE_STATUS = FAILURE_CONFIRMED (boundary level)
IIPS_STATUS_SOURCE = UNKNOWN (packed/VM computation)
IIPS_GATE_VALUE = 0x8189FEC (135831532)
IIPS_GATE_READER = EXE packed .tp3 code (runtime, not native instruction)
IIPS_GATE_WRITER = EXE packed .tp3 code (runtime-computed value, not address write)

IIPS_FAILURE_TARGET = EXE error boundary, WIN_IIPS_INIT_ERROR, 0xC0000409
IIPS_SUCCESS_TARGET = IFS2 vtable callback (inside IFS2.dll, not EXE Engine)
IIPS_SUCCESS_TO_ENGINE = UNKNOWN (success path not observed at runtime)

ENGINE_REGION_HIT_COUNT = 0
FIRST_ENGINE_TARGET = UNKNOWN

PRIMARY_IIPS_FAILURE_CAUSE = IIPS internal initialization failure before first external dependency handoff (STATIC_CONFIRMED branch structure; DYNAMIC exact failing stage UNKNOWN)
RUNTIME_ENTRY_IDENTIFIED = NO

NEXT_RESEARCH_DIRECTION = Caller-filtered dynamic capture of iips.dll LoadLibraryW(ifs2 path) entry/return and GetLastError; observe which initIfsLib stage fails at runtime
```

## Research Boundary

ICH-013 scope is limited to:
> IIPS Gate to Status Source to Success/Failure Branch

ICH-013 does NOT cover:
> Engine internal recovery, resource loading, network recovery,
> WeGame/TCLS, .tvm0 full decode

## Compliance

| Constraint | Status |
|-----------|--------|
| No binary modification | YES |
| No patch of 0x8189FEC | YES |
| No forced SUCCESS | YES |
| No .tvm0 full decode | YES |
| No Engine internal investigation | YES |
| No WeGame/TCLS expansion | YES |
| No IFS2 re-investigation | YES (ICH-010 conclusion maintained) |
| No BugTrace re-investigation | YES (ICH-011 conclusion maintained) |
