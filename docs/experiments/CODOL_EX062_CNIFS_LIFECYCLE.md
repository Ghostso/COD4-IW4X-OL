# CODOL_EX062_CNIFS_LIFECYCLE

## Scope and Constraints Observed

This round is **offline static object-lifetime analysis only**.

Not performed:

```text
API hook
debugger attach
Frida
ETW API tracing
parameter matrix
patch
bypass
fake success
DLL/EXE modification
IIPS state modification
call-argument modification
code injection
import/export modification
vtable modification
```

No process was started, attached to, or instrumented. All evidence is from
read-only parsing of the on-disk `iips.dll`.

### Binary integrity

```text
iips.dll  sha256  72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
          size    347704
          image   0x10000000 + 0x55000
          .text   0x1000 .. 0x32C3B
          .rdata  0x33000 .. 0x41C81
          .data   0x42000 .. 0x4EB94

EXE       sha256  36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
```

Both hashes are identical to EX-060 / EX-061. Nothing was modified.

### Evidence vocabulary (as required)

```text
STATIC_DIRECT      operand / target is literal in the decoded instruction
STATIC_INDIRECT    value arrives via pointer, register, or vtable
STATIC_REACHABLE   a static CFG path exists, but the edge is not literal
EXTERNAL_BOUNDARY  resolution requires a module outside iips.dll
STATIC_UNKNOWN     static data is insufficient

DYNAMIC_CONFIRMED is NOT used in this round.
```

---

## EXECUTIVE ANSWER

**The object created by `sub_12760 -> sub_90D0` CAN be statically closed to
`CNIFS::InitInGameApp`. The closure is `STATIC_DIRECT` for every link of the
identity chain, including the final dispatch.**

The previously-missing link was found:

```text
0x12F40  mov ecx, [ebx+0x19C]     ; ECX := the object published at 0x12D06
0x12F46  mov eax, [ecx]           ; vtable := 0x1003530C (ctor's last write)
0x12F48  mov edx, [eax+0x50]      ; slot 20 := 0x10009860
0x12F56  call edx                 ; ECX == this  ==> CNIFS::InitInGameApp
```

Additionally:

```text
InitInGameApp IS a vtable method.
    vtable 0x1003530C  slot 20  offset +0x50  ->  0x10009860
It has ZERO immediate callers and EXACTLY ONE function-pointer
occurrence in the whole module.

sub_197F0 is NOT a wrapper for InitInGameApp.
    It is slot 1 of a DIFFERENT vtable (0x1003934C), and it calls the
    FACTORY sub_12760.  InitInGameApp is reached from inside that call.
```

---

## A. Constructor

```text
function     iips.dll + 0x90D0
extent       0x90D0 .. 0x9214
size         76 instructions, single linear basic block (no branches)
             (the whole body is reachable from 0x90D0 with no CFG joins)
```

### A.1 `this` source

```text
0x90D0  push -1
0x90D2  push 0x100321A1            ; SEH handler
0x90D7  mov eax, fs:[0]
0x90DD  push eax
0x90DE  push ebx
0x90DF  push ebp
0x90E0  push esi
0x90E1  push edi
0x90E2  mov eax, [0x10042020]      ; security cookie
0x90E7  xor eax, esp
0x90E9  push eax
0x90EA  lea eax, [esp+0x14]
0x90EE  mov fs:[0], eax
0x90F4  mov ebp, [esp+0x24]        ; <== this = STACK ARGUMENT 1
```

```text
EVIDENCE  STATIC_DIRECT
this comes from [esp+0x24], i.e. the first stack argument.
```

### A.2 `ret 4`

```text
0x9211  add esp, 0xC
0x9214  ret 4                      ; callee pops 1 argument
```

```text
EVIDENCE  STATIC_DIRECT
Calling convention: one pointer argument on the stack, callee-cleaned.
```

### A.3 vtable writes (7 immediates, 6 distinct vtables)

The constructor installs vtable pointers in **two groups**. The later group
overwrites the earlier, so the FINAL layout is the second group.

| order | RVA | destination | vtable VA | vtable RVA | group |
|---:|---|---|---|---|---|
| 1 | `0x90F8` | `[ebp+0x0]` | `0x10035204` | `0x35204` | base-object ctor |
| 2 | `0x9105` | `[ebp+0x4]` | `0x100352EC` | `0x352EC` | base-object ctor |
| 3 | `0x911A` | `[ebp+0x50]` | `0x100351F8` | `0x351F8` | base-object ctor |
| 4 | `0x9126` | `[esi+0x0]` (esi = `ebp+8`) | `0x10035408` | `0x35408` | embedded sub-object |
| 5 | `0x9134` | `[ebp+0x0]` | **`0x1003530C`** | **`0x3530C`** | **CNIFS final** |
| 6 | `0x913B` | `[ebp+0x4]` | `0x100353E8` | `0x353E8` | CNIFS secondary |
| 7 | `0x9142` | `[ebp+0x50]` | `0x10035418` | `0x35418` | CNIFS secondary |

```text
EVIDENCE  STATIC_DIRECT
FINAL primary vtable of the object = 0x1003530C  (write #5 wins)
```

### A.4 Every field initialised

The constructor zeroes/interprets these fields (register `ebx` = 0 from
`xor ebx, ebx` at `0x90FF`, unchanged through the sequence):

| RVA | field | value |
|---|---|---|
| `0x90F8` | `[this+0x00]` | `0x10035204` |
| `0x9105` | `[this+0x04]` | `0x100352EC` |
| `0x911A` | `[this+0x50]` | `0x100351F8` |
| `0x9126` | `[this+0x08]` (esi=this+8) | `0x10035408` |
| `0x9134` | `[this+0x00]` | `0x1003530C` |
| `0x913B` | `[this+0x04]` | `0x100353E8` |
| `0x9142` | `[this+0x50]` | `0x10035418` |
| `0x9189` | `[this+0x138]` | 0 |
| `0x9196` | `[this+0x144]` | 0 |
| `0x919C` | `[this+0x148]` | 0 |
| `0x91A2` | `[this+0x14C]` | 0 |
| `0x91B3` | `[this+0x150]` | 0 |
| **`0x91CF`** | **`[this+0x60]`** | **0** |
| `0x91D2` | `[this+0x58]` | 0 |
| `0x91D5` | `[this+0x5C]` | 0 |
| `0x91D8` | `[this+0x54]` | 0 |
| `0x91DB` | `[this+0xCC]` | 0 |
| `0x91E1` | `[this+0xF8]` | 0 |
| `0x91E7` | `[this+0xFC]` | 0 |
| `0x91ED` | `[this+0x154]` | 0 (byte) |
| `0x91F3` | `[this+0x155]` | 0 (byte) |
| `0x91F9` | `[this+0x100]` | 0 |

Also written indirectly by the helper calls:

```text
0x9115  call sub_F830   (init of the [this+0x08] sub-object)
0x9149  call sub_2AC0
0x916D  call [0x10033034]   InitCriticalSection-like on [this+0xDC]
0x9187  call [0x10033034]   InitCriticalSection-like on [this+0x120]
0x91B9  call sub_88F0       init of [this+0x158]
0x91C9  call [0x100331A4]   init of [this+0x1D4]
0x917A  call [0x100331A4]   init of [this+0x104]
0x9189  `[this+0x138] = 0`
0x918F  `[this+0x13C] = 1`  (byte, set before 0x9196)
```

### A.5 The six fields singled out in the task

```text
[this+0x54] = 0     0x91D8     HMODULE slot
[this+0x58] = 0     0x91D2     CreateIFSLibDll slot
[this+0x5C] = 0     0x91D5     DestoryIFSLibDll slot
[this+0x60] = 0     0x91CF     create result / interface pointer
[this+0xCC] = 0     0x91DB     status code
[this+0x120]        NOT zeroed directly; initialised by the
                    InitCriticalSection-like call at 0x9187
```

### A.6 Constructor return value

```text
0x91FF  mov eax, ebp      ; return `this`
0x9201  mov ecx, [esp+0x14]
0x9205  mov fs:[0], ecx
0x920C  pop ecx
0x920D  pop edi
0x920E  pop esi
0x920F  pop ebp
0x9210  pop ebx
0x9211  add esp, 0xC
0x9214  ret 4
```

```text
EVIDENCE  STATIC_DIRECT  (function returns the pointer it was given)
```

### A.7 Is this a real object initialisation, not a helper?

```text
YES. Evidence:
  1. it takes a single pointer argument and returns that same pointer
  2. it writes 7 vtable pointers into [this+0], [this+4], [this+8],
     [this+0x50]  (vtable installation is an object-initialisation act)
  3. it initialises exactly the 29 fields that the downstream CNIFS
     methods (initIfsLib, InitInGameApp, ~CNIFS) subsequently use
  4. it is invoked exactly once, immediately after operator new
  5. its result is returned by value to the allocation site and stored
EVIDENCE  STATIC_DIRECT
```

---

## B. Factory `sub_12760`

```text
function     iips.dll + 0x12760
extent       0x12760 .. 0x13587
size         819 instructions  (own-entry recovery; see note)
```

Note on function boundaries: `0x12760` starts with `push ebp ; mov ebp, esp ;
and esp, 0xFFFFFFF8` (a stack-aligned frame), then continues into the standard
SEH prologue at `0x12766`. The recursive-descent body used here is anchored at
`0x12760`, which is the true entry.

### B1. Which API allocates the object?

```text
0x12CD3  push 0x1F0                 ; size = 496
0x12CD8  call 0x1002BE34           ; ==> import thunk
0x12CDD  add esp, 4
```

`sub_2BE34` disassembles to a single instruction:

```text
0x2BE34  jmp dword ptr [0x1003328C]
```

IAT slot `0x1003328C` resolves to:

```text
MSVCR80.dll  ??2@YAPAXI@Z
```

which is the MSVC decorated name for:

```text
void * operator new(unsigned int)
```

```text
ANSWER  B1:  operator new  (MSVCR80.dll!??2@YAPAXI@Z)
             reached through the import thunk at iips.dll+0x2BE34
EVIDENCE:    STATIC_DIRECT (literal IAT slot 0x1003328C -> import name)
```

### B2. Is the allocation size confirmed as `0x1F0`?

```text
0x12CD3  68 f0 01 00 00        push 0x1F0
```

The literal is `0x1F0` = 496 bytes.

```text
ANSWER  B2:  CONFIRMED, 0x1F0 = 496 bytes
EVIDENCE:    STATIC_DIRECT (literal immediate)
```

Consistency check: every field the constructor and downstream methods touch
(`+0x60`, `+0xCC`, `+0x120`, `+0x138`, `+0x19C` is on the PARENT, not this
object; `+0x1D4` is the last this-object field) lies below `0x1F0`.

### B3. Is the constructor `this` provably the allocation pointer?

```text
0x12CD8  call 0x1002BE34       ; EAX = operator new(0x1F0)
0x12CDD  add esp, 4
0x12CE0  mov [esp+0x24], eax   ; save the raw pointer
0x12CE4  test eax, eax
0x12CEE  je 0x10012CFA         ; NULL -> skip construction
0x12CF0  push eax              ; <== arg1 = the SAME EAX
0x12CF1  call 0x100090D0       ; CNIFS ctor
```

Between `0x12CE0` and `0x12CF0`, `EAX` is only read by `test eax, eax`; no
instruction writes `EAX`. Therefore the value pushed at `0x12CF0` is exactly
the value returned by `operator new`.

The constructor then takes its `this` from `[esp+0x24]` (`0x90F4`), which in
the callee frame is the first stack argument.

```text
ANSWER  B3:  YES. constructor this == allocation return pointer.
EVIDENCE:    STATIC_DIRECT
```

### B4. Where does the object live after construction?

```text
0x12CF6  mov edi, eax          ; EDI = constructed CNIFS*
0x12CF8  jmp 0x10012CFC
0x12CFA  xor edi, edi          ; allocation-failure path
0x12CFC  test edi, edi
0x12CFE  mov byte [esp+0x1C8], 6
0x12D06  mov [esi+0x19C], edi  ; <== PUBLICATION
0x12D0C  je 0x10012D2A
```

Destination provenance:

```text
0x12CBD  mov esi, [esp+0x18]    ; ESI = the caller's parent object
0x12CC1  mov [esi+0x17C], eax   ; (sibling field, unrelated)
...
0x12D06  mov [esi+0x19C], edi   ; store CNIFS* into the parent
```

| item | record |
|---|---|
| store destination | `[parent + 0x19C]` |
| base register | `ESI` |
| ESI value source | `[esp+0x18]` (set at `0x12CBD`) |
| global static | no |
| heap owner | the CNIFS block itself is heap-allocated (`operator new`) |
| struct field | yes -- field `+0x19C` of the parent object |
| stack temporary | the pointer also transits `[esp+0x24]` and `EDI`, but the durable location is `[parent+0x19C]` |
| return register | `EAX` at the ctor return, immediately captured into `EDI` |

```text
ANSWER  B4:  the object is published into the PARENT object's field +0x19C.
EVIDENCE:    STATIC_DIRECT
```

### B5. How does the factory expose the CNIFS object?

Two mechanisms, both present:

```text
1. STORAGE   [parent+0x19C] = CNIFS*        (0x12D06)
2. DISPATCH  the factory then loads it back and calls a vtable slot:
                0x12F3C  mov ebx, [esp+0x50]      ; parent
                0x12F40  mov ecx, [ebx+0x19C]     ; CNIFS*
                0x12F46  mov eax, [ecx]           ; vtable
                0x12F48  mov edx, [eax+0x50]      ; slot 20
                0x12F56  call edx                 ; ECX = CNIFS*
```

The factory does **not** return the CNIFS pointer to its own caller as the
primary result; it returns a boolean. The object reference travels through
`[parent+0x19C]`.

Evidence for the boolean return:

```text
0x197F7  call 0x10012760
0x197FC  test al, al
0x197FE  jne 0x1001980D          ; success
0x19807  xor al, al              ; failure -> return 0
0x1980D  mov al, 1               ; success -> return 1
0x1980A / 0x19810  ret 4
```

```text
ANSWER  B5:  [parent+0x19C] = CNIFS*   AND
             immediate vtable dispatch of slot +0x50 on that object.
EVIDENCE:    STATIC_DIRECT for both the store and the load.
```

### B.6 The complete creation chain inside the factory

```text
sub_12760
   0x12CD3  push 0x1F0                       ; size
   0x12CD8  call operator new                ; allocation
   0x12CE0  mov [esp+0x24], eax
   0x12CEE  je 0x12CFA                       ; failure
   0x12CF0  push eax
   0x12CF1  call sub_90D0                    ; CONSTRUCTOR
   0x12CF6  mov edi, eax
   0x12D06  mov [esi+0x19C], edi             ; PUBLICATION
      |
      | ... post-construction initialisation of the parent object
      |     (string setup, HostApp.ini reads, resource registration)
      |
   0x12F40  mov ecx, [ebx+0x19C]             ; RETRIEVAL
   0x12F46  mov eax, [ecx]
   0x12F48  mov edx, [eax+0x50]
   0x12F56  call edx                         ; DISPATCH -> InitInGameApp
   0x12F58  test al, al
   0x12F5C  sete byte [esp+0x17]             ; record the result
      |
      | ... later, on a cleanup path:
   0x13026  mov ecx, [ebx+0x19C]
   0x13039  call eax                         ; vtable slot +0x4C
   0x13040  mov [ebx+0x19C], esi   (esi=0)   ; CLEAR
```

**Important ordering fact:** the clearing write at `0x13040` occurs AFTER the
dispatch at `0x12F56`. It cannot invalidate the identity chain for the
InitInGameApp call.

```text
EVIDENCE  STATIC_DIRECT (control-flow order within the recovered body)
```

---

## C. Allocation

```text
API              MSVCR80.dll!operator new(unsigned int)   [??2@YAPAXI@Z]
reached via      iips.dll import thunk at RVA 0x2BE34
                 `jmp dword ptr [0x1003328C]`
IAT slot         0x1003328C
size argument    0x1F0  (496)
call site        0x12CD8 inside sub_12760
```

```text
CATEGORY: operator new  (C++ allocation), NOT malloc / HeapAlloc /
          a custom allocator.
EVIDENCE: STATIC_DIRECT (IAT slot resolves to the decorated import name)
```

---

## D. Object Publication

```text
publication site   0x12D06   mov dword ptr [esi+0x19C], edi
publication slot   parent + 0x19C
source register    EDI (set at 0x12CF6 from EAX = ctor return)
base register      ESI (set at 0x12CBD from [esp+0x18])
```

### D.1 All writers of a `+0x19C` field in the whole module

| RVA | function | instruction | relevance |
|---|---|---|---|
| `0x016BD` | `sub_167E` | `mov byte [esp+0x19C], 2` | stack slot, unrelated |
| `0x122AC` | `sub_11F27` | `mov [ebp+0x19C], ebx` | different object type |
| **`0x12D06`** | **`sub_12760`** | **`mov [esi+0x19C], edi`** | **the publication** |
| `0x13040` | `sub_12760` | `mov [ebx+0x19C], esi` (esi=0) | the clear, AFTER dispatch |
| `0x137AB` | `sub_1375E` | `mov [ebp+0x19C], ebx` | different object type |

### D.2 All readers of `+0x19C` that matter

96 read sites exist across the manager-object family. The relevant ones
inside `sub_12760` itself are:

| RVA | instruction | role |
|---|---|---|
| **`0x12F40`** | `mov ecx, [ebx+0x19C]` | **the retrieval feeding the dispatch** |
| `0x12F89` | `mov eax, [ebx+0x19C]` | later use |
| `0x13026` | `mov ecx, [ebx+0x19C]` | teardown path |
| `0x13229` | `mov eax, [ebx+0x19C]` | later use |

Every read uses the same field offset and the same parent-object register
family (`ebx` from `[esp+0x50]`, `esi` from `[esp+0x18]`), and both are set
from the same `[esp+0x18]`-family slot.

```text
EVIDENCE  STATIC_DIRECT
```

---

## E. Vtable Reconstruction

### E.1 The six vtables the constructor installs

| vtable VA | RVA | slots | size | installed at | role |
|---|---:|---:|---:|---|---|
| `0x10035204` | `0x35204` | 51 | `0xCC` | `0x90F8` | base-object vtable (superseded) |
| `0x100352EC` | `0x352EC` | 7 | `0x1C` | `0x9105` | base sub-object (superseded) |
| `0x100351F8` | `0x351F8` | 2 | `0x08` | `0x911A` | base sub-object (superseded) |
| `0x10035408` | `0x35408` | 3 | `0x0C` | `0x9126` | embedded sub-object at `this+8` |
| **`0x1003530C`** | **`0x3530C`** | **54** | **`0xD8`** | **`0x9134`** | **CNIFS PRIMARY** |
| `0x100353E8` | `0x353E8` | 7 | `0x1C` | `0x913B` | CNIFS secondary |
| `0x10035418` | `0x35418` | 2 | `0x08` | `0x9142` | CNIFS secondary |

```text
The construction sequence is a two-phase C++ layout: base sub-objects are
constructed first (writes 1-4), then the derived CNIFS vtable pointers
replace the base ones (writes 5-7).  This is exactly how MSVC emits
multiple-inheritance / multi-vtable construction.

EVIDENCE  STATIC_DIRECT
```

### E.2 `CNIFS::InitInGameApp` and `sub_197F0` in the vtables

```text
InitInGameApp  0x9860  =  vtable 0x1003530C  slot 20  offset +0x50
sub_197F0      0x197F0 =  vtable 0x1003934C  slot 1   offset +0x04

sub_197F0 is NOT in any CNIFS vtable.
```

### E.3 `CNIFS_PRIMARY` vtable `0x1003530C`, all 54 slots

| slot | off | target RVA | notes |
|---:|---|---|---|
| 0 | `+0x00` | `0x76D0` | |
| 1 | `+0x04` | `0x7700` | |
| 2 | `+0x08` | `0x7720` | |
| 3 | `+0x0C` | `0x7230` | |
| 4 | `+0x10` | `0x78C0` | |
| 5 | `+0x14` | `0x71F0` | |
| 6 | `+0x18` | `0x7680` | |
| 7 | `+0x1C` | `0x78F0` | |
| 8 | `+0x20` | `0x7900` | |
| 9 | `+0x24` | `0x78A0` | |
| 10 | `+0x28` | `0x7AF0` | |
| 11 | `+0x2C` | `0x7B20` | |
| 12 | `+0x30` | `0x7B90` | |
| 13 | `+0x34` | `0x7D10` | |
| 14 | `+0x38` | `0x9430` | |
| 15 | `+0x3C` | `0x9380` | |
| 16 | `+0x40` | `0xAD60` | |
| 17 | `+0x44` | `0x75E0` | |
| 18 | `+0x48` | `0xBE80` | |
| 19 | `+0x4C` | `0x9220` | destructor-thunk region |
| **20** | **`+0x50`** | **`0x9860`** | **`CNIFS::InitInGameApp`** |
| 21 | `+0x54` | `0xB870` | |
| 22 | `+0x58` | `0xA860` | |
| 23 | `+0x5C` | `0xB010` | |
| 24 | `+0x60` | `0x7D30` | |
| 25 | `+0x64` | `0xAAB0` | |
| 26 | `+0x68` | `0xAC40` | |
| 27 | `+0x6C` | `0xB9C0` | |
| 28 | `+0x70` | `0x7770` | |
| 29 | `+0x74` | `0x7790` | |
| 30 | `+0x78` | `0xB020` | |
| 31 | `+0x7C` | `0xB070` | |
| 32 | `+0x80` | `0xB0B0` | |
| 33 | `+0x84` | `0xB600` | |
| 34 | `+0x88` | `0xB770` | |
| 35 | `+0x8C` | `0xB0D0` | |
| 36 | `+0x90` | `0xAED0` | |
| 37 | `+0x94` | `0xADC0` | |
| 38 | `+0x98` | `0xBF10` | |
| 39 | `+0x9C` | `0x77A0` | |
| 40 | `+0xA0` | `0xB080` | |
| 41 | `+0xA4` | `0xB780` | |
| 42 | `+0xA8` | `0xBC30` | |
| 43 | `+0xAC` | `0x7A30` | |
| 44 | `+0xB0` | `0xB0F0` | |
| 45 | `+0xB4` | `0xB240` | |
| 46 | `+0xB8` | `0xBCC0` | |
| 47 | `+0xBC` | `0xC860` | |
| 48 | `+0xC0` | `0xC8B0` | |
| 49 | `+0xC4` | `0xC930` | |
| 50 | `+0xC8` | `0xCBA0` | |
| 51 | `+0xCC` | `0xC890` | |
| 52 | `+0xD0` | `0xAFE0` | |
| 53 | `+0xD4` | `0x7A20` | |

```text
total 54 slots, 0xD8 bytes.
The dword immediately after the vtable at RVA 0x353E4 is NOT a code
pointer -- a new data structure begins there.
EVIDENCE  STATIC_DIRECT (all slot values are literal code pointers)
```

---

## F. `InitInGameApp` Classification

### F1. What kind of function is it?

```text
CLASSIFICATION:  vtable method (interface implementation)
                 + __thiscall (ECX = this)

NOT:  export
NOT:  ordinary internal function
NOT:  callback reached by name
NOT:  wrapper
```

Evidence:

| fact | value | evidence |
|---|---|---|
| export table | NOT present (only `GetResourceManager`, `ReleaseResourceManager( II )`, `GetResourceManagerII`) | `STATIC_DIRECT` |
| vtable membership | slot 20 of `0x1003530C` | `STATIC_DIRECT` |
| calling convention | `__thiscall` (`mov ebp, ecx` at `0x989B`, `ret 0x38`) | `STATIC_DIRECT` |
| immediate callers | **0** | `STATIC_DIRECT` |
| function-pointer occurrences in the file | **1** (RVA `0x3535C`, `.rdata`) | `STATIC_DIRECT` |

```text
The single occurrence of the 4-byte value 0x10009860 anywhere in iips.dll
IS the vtable slot.  There is no other reference of any width.
```

### F2. All possible references

| reference form | count | location |
|---|---:|---|
| direct `CALL` (E8 rel32, any alignment) | 0 | - |
| `CALL` register / `CALL [mem]` | 0 | - |
| vtable slot reference | **1** | `.rdata` RVA `0x3535C` (vtable `0x1003530C` slot 20) |
| function pointer assignment | 0 | - |
| export table | 0 | - |
| IAT/EAT | 0 | - |
| string / interface-ID reference | 0 | - |

```text
EVIDENCE  STATIC_DIRECT
```

### F3. How is it reached?

```text
reached ONLY through the vtable dispatch at sub_12760 + 0x12F56
  -> classification of the EDGE: STATIC_INDIRECT
  -> classification of the TARGET: STATIC_DIRECT (slot value is literal)
```

---

## G. `sub_197F0` Relationship

### G.1 Full body

```text
0x197F0  8b542404      mov edx, dword ptr [esp + 4]    ; arg1 (ignored here)
0x197F4  56            push esi
0x197F5  8bf1          mov esi, ecx                    ; ESI = this (thiscall)
0x197F7  e8648fffff    call 0x10012760                 ; ==> THE FACTORY
0x197FC  84c0          test al, al
0x197FE  750d          jne 0x1001980D                  ; success
0x19800  8bce          mov ecx, esi                    ; this
0x19802  e819000000    call 0x10019820                 ; cleanup / uninit
0x19807  32c0          xor al, al                      ; return FALSE
0x19809  5e            pop esi
0x1980A  c20400        ret 4
0x1980D  b001          mov al, 1                       ; return TRUE
0x1980F  5e            pop esi
0x19810  c20400        ret 4
```

### G.2 Answers to the seven questions

| # | question | answer | evidence |
|---:|---|---|---|
| 1 | Does it call `InitInGameApp`? | **NO** -- it does not reference `0x9860` in any form | `STATIC_DIRECT` |
| 2 | Is it only a wrapper? | **NO, not a wrapper for `InitInGameApp`.** It is a thin initialiser entry that invokes the FACTORY, and then calls a cleanup/rollback helper on failure | `STATIC_DIRECT` |
| 3 | What parameters does it take? | one stack argument (`[esp+4]`, loaded into `EDX` at `0x197F0`), plus `ECX` as `this`; `ret 4` (callee pops the stack arg) | `STATIC_DIRECT` |
| 4 | How does it obtain the CNIFS `this`? | **It does not.** The CNIFS object is created *inside* the factory it calls and published at `[parent+0x19C]`; `sub_197F0` never holds the CNIFS pointer | `STATIC_DIRECT` |
| 5 | What does it return? | a boolean in `AL` (0 = failure, 1 = success) | `STATIC_DIRECT` |
| 6 | Is it reached through a vtable? | **YES** -- slot 1 of vtable `0x1003934C` (RVA `0x39350`) | `STATIC_DIRECT` |
| 7 | Is it at an external/interface boundary? | It is a vtable method of the MANAGER object, whose own caller is outside `iips.dll` -> the path terminates at `EXTERNAL_BOUNDARY` | `EXTERNAL_BOUNDARY` |

### G.3 Does `sub_197F0 -> InitInGameApp` hold?

```text
DIRECTLY:  NO.
INDIRECTLY (through the factory): YES, one call level deeper.

   sub_197F0  (vtable 0x1003934C slot 1)
       |
       +-- 0x197F7 call sub_12760   <== THE FACTORY
               |
               +-- 0x12CF1 call sub_90D0    (construct CNIFS)
               +-- 0x12D06 [parent+0x19C]=CNIFS*
               |
               +-- 0x12F56 call [CNIFS+0x50] = call InitInGameApp
                       |
                       +-- 0x99D2 call initIfsLib
                               |
                               +-- 0x95D0 [this+0x60] gate
```

So the accurate relation is:

```text
sub_197F0
   --(0x197F7)-->  sub_12760  (factory)
                      --(0x12F56)-->  CNIFS::InitInGameApp
                                          --(0x99D2)-->  initIfsLib
                                                            --(0x95D0)--> gate
```

```text
EVIDENCE  STATIC_DIRECT for each hop's instruction; the 0x12F56 hop is
          STATIC_INDIRECT in form and STATIC_DIRECT in resolved target.
```

---

## H. All Caller Candidates

### H.1 `InitInGameApp` (`0x9860`)

| scan | count |
|---|---:|
| `CALL` immediate (`E8 rel32`, all offsets 0x1000..0x32C3B) | **0** |
| `CALL` register | 0 |
| `CALL [memory]` | 0 |
| `CALL [reg+offset]` | 0 |
| vtable dispatch | **1** (slot 20 of `0x1003530C`) |
| export / import | 0 |
| callback table | 0 |
| function-pointer table | **1** (the vtable slot itself) |

### H.2 The one dispatch site

```text
caller function   sub_12760
caller RVA        0x12F56
object source     ECX, loaded at 0x12F40 from [EBX + 0x19C]
                  EBX loaded at 0x12F3C from [ESP + 0x50]
vtable source     [ECX]  -> 0x1003530C
slot offset       +0x50  (slot 20)
target resolution 0x10009860
target RVA        0x9860  = CNIFS::InitInGameApp
```

Instruction-level dispatch sequence:

```text
0x12F3C  8b5c2450         mov ebx, [esp+0x50]
0x12F40  8b8b9c010000     mov ecx, [ebx+0x19C]
0x12F46  8b01             mov eax, [ecx]
0x12F48  8b5050           mov edx, [eax+0x50]
0x12F4B  83c050           add eax, 0x50
0x12F4E  c684240002000015 mov byte [esp+0x200], 0x15
0x12F56  ffd2             call edx
0x12F58  84c0             test al, al
0x12F5C  0f94442417       sete byte [esp+0x17]
```

### H.3 "`push argument ; mov ecx,this ; call`" pattern check

```text
NO such site exists for InitInGameApp.
The call is a pure vtable dispatch; ECX is the object pointer and no
additional stack argument is pushed for this callee
(InitInGameApp takes only `this` in ECX).
EVIDENCE  STATIC_DIRECT
```

### H.4 Other `[..+0x50]` slot dispatch sites in the module

19 near-pattern sites exist, of which only one resolves through the CNIFS
primary vtable:

| owner | slot fetch | call | resolves to |
|---|---|---|---|
| **`sub_12760`** | **`0x12F48 mov edx,[eax+0x50]`** | **`0x12F56`** | **`0x9860` InitInGameApp** |
| `sub_B870` / `sub_B95B` family | `0xB970` | `0xB97C` | other object vtable (`[eax]` is not `0x1003530C`) |
| `sub_BF10` | `0xBF51` | `0xBF56` | other |
| others | - | - | stack slots / unrelated objects |

```text
Only sub_12760's site has the CNIFS object in ECX at the dispatch.
EVIDENCE  STATIC_DIRECT (the object source is [parent+0x19C] which holds
          the value published at 0x12D06)
```

---

## I. `this` Propagation

### I.1 Which registers carry which object inside `InitInGameApp`?

```text
ECX   = this, ONLY at the function boundary (consumed immediately at 0x989B)
EBP   = the ORIGINAL CNIFS `this`, until 0x9B7B
EBX   = [ebp+0x120]  (the critical-section / embedded sub-object region),
        set at 0x98AC `lea ebx, [ebp+0x120]`, reloaded from [esp+0x1C]
ESI   = [ebp+0xD0] sub-object (0x98BD), later reused for other temporaries
EDI   = transient string/loop temporaries
```

### I.2 The `0x9B7B` alias break (carried from EX-061, now fully placed)

```text
0x9B72  80bdcc01000000   cmp byte ptr [ebp+0x1CC], 0
0x9B79  740f             je 0x10009B8A
0x9B7B  8b6d60           mov ebp, dword ptr [ebp + 0x60]   ; <== EBP REPLACED
0x9B7E  8b4500           mov eax, dword ptr [ebp]
0x9B81  8b502c           mov edx, dword ptr [eax + 0x2C]
0x9B84  6a04             push 4
0x9B86  8bcd             mov ecx, ebp
0x9B88  ffd2             call edx
0x9B8A  8b4304           mov eax, dword ptr [ebx + 4]       ; EBX still = [orig this+0x120]
```

After `0x9B7B`, `EBP` is **no longer the CNIFS object**; it is the interface
pointer from `[CNIFS+0x60]`.

### I.3 Strict separation

| role | register | establishing instruction | lifetime |
|---|---|---|---|
| original CNIFS `this` | `ECX` -> `EBP` | `0x989B mov ebp, ecx` | `0x989B` .. `0x9B7B` (and via `[esp+0x24]` beyond) |
| saved original `this` | `[esp+0x24]` | `0x989D mov [esp+0x24], ebp` | whole frame |
| other object base | `EBP` (reused) | `0x9B7B mov ebp, [ebp+0x60]` | `0x9B7B` .. epilogue |
| critical-section region | `EBX` | `0x98AC lea ebx, [ebp+0x120]`; also `[esp+0x1C]` | whole frame |
| `[ebp+0xD0]` sub-object | `ESI` | `0x98BD lea esi, [ebp+0xD0]` | until ESI reused |

### I.4 Consequence for the `+0x60` reads

```text
0x9A2B  mov ecx, [ebp+0x60]   ; EBP == original this  -> CNIFS+0x60   OK
0x9B51  mov ecx, [ebp+0x60]   ; EBP == original this  -> CNIFS+0x60   OK
0x9B66  mov ecx, [ebp+0x60]   ; EBP == original this  -> CNIFS+0x60   OK
0x9B7B  mov ebp, [ebp+0x60]   ; EBP == original this  -> CNIFS+0x60   OK,
                              ; and it then REPLACES EBP
```

All four are genuine `CNIFS+0x60` reads.

By contrast, the other `+0x60` accesses inside the same function use
different bases and are NOT the CNIFS field:

```text
0xA327 / 0xA340 / 0xA4D9   base EBX  (= [CNIFS+0x120] region)  -> other object
0xA613 / 0xA639 / 0xA68E   base EDI  (loop element)             -> other object
EVIDENCE  STATIC_DIRECT
```

### I.5 `+0x1CE` / `+0x1CD` / `+0x1CC` guards on the `+0x60` reads

```text
0x9B24  cmp byte [ebp+0x1CE], 0   ; gate for the 0x9B51 read (id 5)
0x9B5D  cmp byte [ebp+0x1CD], 0   ; gate for the 0x9B66 read (id 3)
0x9B72  cmp byte [ebp+0x1CC], 0   ; gate for the 0x9B7B read (id 4)
```

So the three guarded dispatches through `[this+0x60]` run only when the
corresponding byte flag is non-zero.

```text
EVIDENCE  STATIC_DIRECT
```

---

## J. Object Identity Proof

### J.1 The chain

```text
  factory this                 sub_12760 receives ECX at entry
        =                      and also [esp+0x50] / [esp+0x18]
        |                      (the same parent object)
        v
  allocation                  0x12CD8  call operator new(0x1F0) -> EAX
        |
        v
  constructor this            0x12CF0  push eax ; 0x12CF1 call sub_90D0
                              0x90F4  mov ebp, [esp+0x24]  == arg1 == EAX
        |
        v
  published object            0x12CF6  mov edi, eax   (ctor return == this)
                              0x12D06  mov [esi+0x19C], edi
        |
        v
  dispatch object             0x12F40  mov ecx, [ebx+0x19C]
        |
        v
  InitInGameApp this          0x12F56  call edx   (ECX == the above)
                              0x989B  mov ebp, ecx
```

### J.2 Evidence level per link

| link | evidence |
|---|---|
| factory `this` -> parent object | `STATIC_DIRECT` |
| `operator new` result -> ctor arg1 | `STATIC_DIRECT` (EAX saved, tested, pushed; not rewritten) |
| ctor arg1 -> ctor `this` | `STATIC_DIRECT` (`0x90F4 mov ebp,[esp+0x24]`) |
| ctor `this` -> ctor return | `STATIC_DIRECT` (`0x91FF mov eax, ebp`) |
| ctor return -> `EDI` | `STATIC_DIRECT` (`0x12CF6 mov edi, eax`) |
| `EDI` -> `[parent+0x19C]` | `STATIC_DIRECT` (`0x12D06`) |
| `[parent+0x19C]` -> `ECX` at dispatch | `STATIC_DIRECT` (`0x12F40`, same offset, no intervening write on this path) |
| `ECX` -> `[ECX]` vtable | `STATIC_DIRECT` (`0x12F46`) |
| vtable -> slot 20 value | `STATIC_DIRECT` (`0x1003530C + 0x50` = `0x10009860`, literal in `.rdata`) |
| slot value -> call target | `STATIC_INDIRECT` in form, `STATIC_DIRECT` in resolved identity (`call edx`, EDX = literal slot) |
| call target -> `InitInGameApp` `this` | `STATIC_DIRECT` (`ECX` survives to the call -- verified) |

### J.3 ECX liveness between retrieval and dispatch

```text
Between 0x12F40 (mov ecx,[ebx+0x19C]) and 0x12F56 (call edx),
NO instruction writes ECX.

Verified by scanning the recovered body for any instruction whose first
operand is ECX in the range (0x12F40, 0x12F56): NONE.

The intervening instructions are:
   0x12F46 mov eax,[ecx]      (reads ECX)
   0x12F48 mov edx,[eax+0x50]
   0x12F4B add eax,0x50
   0x12F4E mov byte [esp+0x200],0x15

=> ECX at the call is still the CNIFS pointer loaded at 0x12F40.
EVIDENCE  STATIC_DIRECT
```

### J.4 Verdict

```text
OBJECT_IDENTITY = STATIC_DIRECT

"The object constructed at sub_12760 -> sub_90D0 is the SAME object
 whose vtable slot 20 is invoked as CNIFS::InitInGameApp."
```

The closure does **not** rely on function names, similar parameters, or mere
vtable-shape similarity. Every hop is a literal operand or a
no-intervening-write register fact inside one function.

---

## K. Lifecycle Graph

```text
[MANAGER OBJECT]  (external caller / vtable 0x1003934C)
        |
        |  sub_197F0 = vtable 0x1003934C slot 1            EXTERNAL_BOUNDARY
        v
[sub_197F0  0x197F0]
        |
        |  0x197F7  call 0x10012760                        STATIC_DIRECT
        v
[sub_12760  0x12760  THE FACTORY]
        |
        |  0x12CD3 push 0x1F0 ; 0x12CD8 call sub_2BE34      STATIC_DIRECT
        |           sub_2BE34 = jmp [0x1003328C]
        |           0x1003328C = MSVCR80!operator new      EXTERNAL_BOUNDARY (API)
        v
[ALLOCATION  0x1F0 bytes]
        |
        |  0x12CE0 mov [esp+0x24],eax ; 0x12CF0 push eax    STATIC_DIRECT
        v
[sub_90D0  CNIFS CONSTRUCTOR]
        |
        |  0x90F4  mov ebp,[esp+0x24]   this = arg1         STATIC_DIRECT
        |  0x9134  [this+0x00] = 0x1003530C  (final vtable) STATIC_DIRECT
        |  0x91CF  [this+0x60] = 0                          STATIC_DIRECT
        |  0x91FF  mov eax, ebp        return this         STATIC_DIRECT
        v
[CNIFS OBJECT  this, sizeof 0x1F0, [+0x60] == 0]
        |
        |  0x12CF6 mov edi,eax ; 0x12D06 mov [esi+0x19C],edi STATIC_DIRECT
        v
[PUBLICATION  parent + 0x19C  =  CNIFS*]
        |
        |  0x12F3C mov ebx,[esp+0x50]                       STATIC_DIRECT
        |  0x12F40 mov ecx,[ebx+0x19C]                      STATIC_DIRECT
        |  0x12F46 mov eax,[ecx]                            STATIC_DIRECT
        |  0x12F48 mov edx,[eax+0x50]                       STATIC_DIRECT
        |  0x12F56 call edx                                 STATIC_INDIRECT
        v
[CNIFS::InitInGameApp  0x9860   (vtable 0x1003530C slot 20)]
        |
        |  0x989B mov ebp,ecx                               STATIC_DIRECT
        |  0x98B7 EnterCriticalSection([this+0x120])        STATIC_DIRECT
        |  0x98CD call sub_6D20   QoS helper (log-only)     STATIC_DIRECT
        |  0x99D2 call 0x10009570  arg1 = this              STATIC_DIRECT
        v
[CNIFS::initIfsLib  0x9570]
        |
        |  0x95A5 mov ebp,[esp+0xA0]  arg1 = this           STATIC_DIRECT
        |  0x95D0 cmp [ebp+0x60], 0                         STATIC_DIRECT
        |
        +------ [this+0x60] != 0 ----------------------------+
        |                                                    |
        |  0x95D4 jne 0x10009818                             |
        |  0x9818 LeaveCriticalSection                       |
        |  0x9837 mov al, 1                                  |
        |  0x985D ret 0x20                                   |
        v                                                    |
   [SUCCESS SHORT-CIRCUIT]                                   |
   no LoadLibraryW, no resolver, no CreateIFSLibDll          |
        |                                                    |
        +------ [this+0x60] == 0 ----------------------------+
        |
        |  0x96A1..0x96CF build  <iipsdir> + L"/ifs2.dll"    STATIC_DIRECT
        |  0x96E9 call [0x10033010]  KERNEL32!LoadLibraryW   STATIC_DIRECT
        |  0x96EF test eax,eax
        |        |
        |        +-- NULL --> 0x9704 log "Failed to open dllfile"
        |        |            0x971C [this+0xCC] = 1 ; AL = 0
        |        |
        |        +-- ok --> 0x9770 mov esi,[0x10033014]
        |                   0x977C call esi  "CreateIFSLibDll"
        |                         |
        |                         +-- NULL --> 0x9785 log ; [this+0xCC]=2 ; AL=0
        |                         |
        |                         +-- ok --> 0x97A1 lea ecx,[ebp+0x50]
        |                                   0x97A4 push ecx
        |                                   0x97A5 call eax  CreateIFSLibDll()
        |                                       |
        |                                       +-- 0 --> 0x97AE log ; AL=0
        |                                       |
        |                                       +-- !=0 --> 0x97A9 [this+0x60]=EAX
        |                                                   0x97CC GetProcAddress
        |                                                          "DestoryIFSLibDll"
        |                                                         |
        |                                                         +-- NULL -> [this+0xCC]=3 ; AL=0
        |                                                         |
        |                                                         +-- ok -> AL=1
        v
[InitInGameApp consumer region]
        |
        |  0x99D7 test al,al
        |  0x99D9 jne 0x9A2B            (success)
        |  0x99DB ... failure path -> 0x9A24 xor al,al -> 0xA833 ret 0x38
        |
        |  0x9A2B mov ecx,[ebp+0x60]  ; interface pointer      STATIC_DIRECT
        |  0x9A35 call [vtable+0x2C] with id 1                 STATIC_INDIRECT
        |  0x9A8B GetPrivateProfileIntW IIPSHostApp.ini        STATIC_DIRECT
        |  0x9B51 call [vtable+0x2C] with id 5  (if [+0x1CE])  STATIC_INDIRECT
        |  0x9B66 call [vtable+0x2C] with id 3  (if [+0x1CD])  STATIC_INDIRECT
        |  0x9B7B mov ebp,[ebp+0x60]                           STATIC_DIRECT
        |  0x9B88 call [vtable+0x2C] with id 4  (if [+0x1CC])  STATIC_INDIRECT
        v
[later state / teardown]
        |
        |  sub_9240  CNIFS::~CNIFS  (vtable 0x1003530C slot 19 region)
        |  0x92D6 call [this+0x5C](&[this+0x60])  DestoryIFSLibDll
        |  0x92D8 [this+0x60] = 0
        |  0x92E2 FreeLibrary([this+0x54])
        |  0x92E8 [this+0x54] = 0
        v
[END]
```

### K.1 Edge classification summary

| edge | class |
|---|---|
| manager vtable -> `sub_197F0` | `EXTERNAL_BOUNDARY` |
| `sub_197F0` -> factory | `STATIC_DIRECT` |
| factory -> `operator new` | `STATIC_DIRECT` (import thunk), API itself `EXTERNAL_BOUNDARY` |
| allocation -> ctor arg | `STATIC_DIRECT` |
| ctor -> `[this+0x60] = 0` | `STATIC_DIRECT` |
| ctor -> publication | `STATIC_DIRECT` |
| publication -> retrieval | `STATIC_DIRECT` |
| retrieval -> vtable slot 20 | `STATIC_DIRECT` |
| slot 20 -> `InitInGameApp` | `STATIC_INDIRECT` (form) / `STATIC_DIRECT` (resolved target) |
| `InitInGameApp` -> `initIfsLib` | `STATIC_DIRECT` |
| `+0x95D0` -> short-circuit | `STATIC_REACHABLE` |
| `+0x95D0` -> ifs2 bring-up | `STATIC_DIRECT` |
| `LoadLibraryW` return use | `STATIC_REACHABLE` (outcome is runtime) |
| resolver -> `CreateIFSLibDll` | `STATIC_INDIRECT` |
| `CreateIFSLibDll` -> `[this+0x60]` | `STATIC_DIRECT` (assignment) |
| dtor -> `DestoryIFSLibDll` | `STATIC_INDIRECT` |

---

## L. External Boundaries

```text
L1  MSVCR80.dll!operator new (??2@YAPAXI@Z)
      via iips.dll import thunk RVA 0x2BE34, IAT slot 0x1003328C
      allocation size 0x1F0
      CLASS: EXTERNAL_BOUNDARY (API); the call SITE is STATIC_DIRECT

L2  KERNEL32.dll!LoadLibraryW
      via IAT slot 0x10033010, call site 0x96E9
      argument: <iipsdir> + L"/ifs2.dll"  (wide string RVA 0x34908)
      CLASS: EXTERNAL_BOUNDARY

L3  KERNEL32.dll!GetProcAddress
      via IAT slot 0x10033014
      names: "CreateIFSLibDll" (RVA 0x34964) at call 0x977C
             "DestoryIFSLibDll" (RVA 0x349E4) at call 0x97CC
      CLASS: EXTERNAL_BOUNDARY

L4  the resolved export CreateIFSLibDll
      target address NOT statically known (returned by L3)
      call site 0x97A5 `call eax`
      CLASS: EXTERNAL_BOUNDARY + STATIC_INDIRECT
      NOTE: its RESULT is stored at [this+0x60] (STATIC_DIRECT assignment)

L5  the resolved export DestoryIFSLibDll
      call site 0x92D6 in ~CNIFS, argument &[this+0x60]
      CLASS: EXTERNAL_BOUNDARY + STATIC_INDIRECT

L6  KERNEL32.dll!FreeLibrary
      via IAT slot 0x10033018, call site 0x92E2, argument [this+0x54]
      CLASS: EXTERNAL_BOUNDARY

L7  KERNEL32.dll!GetPrivateProfileIntW
      via IAT slot 0x100330B4, call site 0x9A8B
      section/key: IIPSHostApp.ini / ResPool / ReservedSize / default 0x40000000
      CLASS: EXTERNAL_BOUNDARY

L8  the MANAGER vtable 0x1003934C (owner of sub_197F0)
      who calls it is outside iips.dll
      CLASS: EXTERNAL_BOUNDARY  <== the remaining open end
```

### L.1 The open boundary, stated precisely

```text
The identity chain INSIDE iips.dll is closed and STATIC_DIRECT.
The only unresolved hop is the ENTRY into sub_197F0 / the factory from
outside this module:

   [external caller]
        --?> manager vtable 0x1003934C slot 1  = sub_197F0
        --?> (or another manager slot that drives the factory)

`sub_197F0` has 0 immediate callers and is not exported.
`sub_12760` has exactly 1 immediate caller: sub_197F0.

Therefore: the question "was InitInGameApp actually executed in a given
run" cannot be answered from iips.dll alone.  It requires the caller of
the manager vtable, which lives in another module.

CLASS: EXTERNAL_BOUNDARY
```

---

## M. STATIC_UNKNOWN

```text
M01  Was InitInGameApp actually executed in any observed run?
     (needs the external caller of manager vtable 0x1003934C -> EXTERNAL_BOUNDARY)

M02  Was sub_197F0 executed in any observed run?
     (same boundary)

M03  Does sub_12760 have any caller other than sub_197F0?
     Static answer inside iips.dll: NO (1 immediate caller).
     A caller from another module using the manager vtable is possible
     and unobservable from iips.dll.                     -> STATIC_UNKNOWN

M04  Which manager vtable slot drives sub_12760 in a given run?
     Many manager slots (0x13900, 0x13A60, 0x13D60, 0x13E80, 0x14A00,
     0x14CED, 0x15EE7, 0x16FCD, 0x1852D, 0x1A1A0, 0x1A26E, 0x1A410,
     0x1A5B0, 0x1A760, 0x1A7E0, 0x1AC40, 0x1ACD0, 0x1AD60, 0x1ADE0 ...)
     read [obj+0x19C], i.e. they all consume the same published CNIFS.
     Which one runs first is runtime-dependent.          -> STATIC_UNKNOWN

M05  The runtime value of [this+0x60] at the 0x95D0 gate.
     (initial value is provably 0; whether it is still 0 at that moment
      depends on whether a prior successful initIfsLib ran) -> STATIC_UNKNOWN

M06  Whether LoadLibraryW was reached in a given run.     -> STATIC_UNKNOWN

M07  LoadLibraryW return value and GetLastError.          -> STATIC_UNKNOWN

M08  GetProcAddress("CreateIFSLibDll") result.            -> STATIC_UNKNOWN

M09  CreateIFSLibDll return value / behaviour.
     (lives in ifs2.dll, which was not analysed this round) -> STATIC_UNKNOWN

M10  The concrete object behind [this+0x60] after a successful
     CreateIFSLibDll, and the meaning of vtable slot +0x2C ids 1/3/4/5
     and slot +8 / +0x4C / +0x4C.                         -> STATIC_UNKNOWN

M11  The semantics of the [this+0x1CC] / [this+0x1CD] / [this+0x1CE]
     byte flags that gate the three [this+0x60] dispatches. -> STATIC_UNKNOWN

M12  What sub_19820 (the failure cleanup called from sub_197F0) does
     to the CNIFS object.                                 -> STATIC_UNKNOWN
     (not analysed this round; it is the rollback path)

M13  The manager object's own class identity and its +0x19C field name.
     The field is confirmed by offset and by consistent use, but the
     owning class was not reconstructed.                  -> STATIC_UNKNOWN

M14  Whether the observed WIN_IIPS_INIT_ERROR / 0x8189FEC outcome came
     from this lifecycle path at all.                     -> STATIC_UNKNOWN

M15  Whether the W1 write (0x91CF) is the ONLY source of the initial 0
     in a run where the object memory is reused after a previous free.
     The constructor always writes 0, so the field is 0 after ctor
     unconditionally; but a foreign module holding the object pointer
     could write +0x60 without iips.dll knowing.  -> STATIC_UNKNOWN
     (within iips.dll: exactly 2 writers, both proven)
```

---

## N. Impact on the Actual IIPS Failure Point

### N.1 What EX-060 / EX-061 established

```text
EX-060   earliest STATIC failure branch on the ifs2 bring-up path
         = iips.dll + 0x96EF  (LoadLibraryW returned NULL)

EX-061   that path is guarded by +0x95D0 ([this+0x60] == 0)
         initial value of [this+0x60] = 0  (constructor W1, STATIC_DIRECT)
         only other writer = initIfsLib W2 (0x97A9)
```

### N.2 What EX-062 adds

```text
1. InitInGameApp is NOT an unreachable orphan.  It IS reachable, and the
   reachability is now fully static:

       operator new -> CNIFS::ctor -> publication -> vtable slot 20
         -> CNIFS::InitInGameApp -> initIfsLib -> +0x95D0 -> ifs2 bring-up

   Every hop inside iips.dll is STATIC_DIRECT except the final `call edx`
   whose FORM is STATIC_INDIRECT and whose TARGET is STATIC_DIRECT.

2. The "vtable/interface boundary" that EX-061 left as the reason for
   STATIC_UNKNOWN is now RESOLVED inside iips.dll:
       vtable 0x1003530C, slot 20, dispatched from sub_12760 at 0x12F56.

3. The remaining unknown is NOT a vtable resolution problem.
   It is purely a RUNTIME-EXECUTION question:
       "did the manager object's caller drive the factory in this run?"
   That is an EXTERNAL_BOUNDARY (L8), not an indirect-call unknown.
```

### N.3 Consequence for the failure point

```text
The static causal chain is now:

   [external loader]
        -> manager object
        -> sub_197F0 (manager vtable slot 1)
        -> sub_12760 factory
        -> operator new + CNIFS::ctor     [this+0x60] = 0
        -> [parent+0x19C] = CNIFS*
        -> call [CNIFS vtable +0x50] = InitInGameApp
        -> call initIfsLib
        -> +0x95D0: [this+0x60] == 0
        -> LoadLibraryW(<iipsdir>/ifs2.dll)   FIRST FAILURE BRANCH +0x96EF
        -> GetProcAddress("CreateIFSLibDll")
        -> CreateIFSLibDll() -> [this+0x60]

Nothing in this chain is unreachable.  The chain's status is:

   STATIC_REACHABLE from the factory entry
   STATIC_DIRECT for the identity links
   STATIC_INDIRECT only for the three resolved-export calls
   EXTERNAL_BOUNDARY only at (a) the manager caller and (b) the APIs
```

### N.4 What this does NOT establish

```text
It does NOT establish that:
   - InitInGameApp executed in the observed -q run
   - LoadLibraryW executed
   - CreateIFSLibDll executed
   - [this+0x60] was 0 at the 0x95D0 gate during that run
   - the observed WIN_IIPS_INIT_ERROR came from this path

This round is object-lifetime analysis only.
IIPS OBJECT LIFECYCLE CLOSURE != IIPS runtime failure identified.
```

---

## Q1 - Q5 Answers

### Q1

> Is the object created by `sub_12760 -> sub_90D0` statically closable to
> `InitInGameApp`?

```text
YES.

The closure was not previously visible because the link is not a CALL
between two named functions; it is:

   0x12D06  mov [parent+0x19C], <CNIFS*>
   0x12F40  mov ecx, [parent+0x19C]
   0x12F46  mov eax, [ecx]
   0x12F48  mov edx, [eax+0x50]
   0x12F56  call edx

and the same function sub_12760 performs both the store and the load.
Evidence level: STATIC_DIRECT for storage/retrieval, STATIC_INDIRECT for
the call form, STATIC_DIRECT for the resolved target (slot value 0x10009860
is a literal in .rdata).
```

### Q2

> Is `InitInGameApp` a vtable/interface method of that CNIFS object?

```text
YES.
   vtable 0x1003530C  (installed by the ctor at 0x9134 as the FINAL
                       [this+0x0] value)
   slot   20
   offset +0x50
   value  0x10009860

It has 0 immediate callers and exactly 1 function-pointer occurrence in
the entire module -- the slot itself.
```

### Q3

> What is the exact relationship between `sub_197F0` and `InitInGameApp`?

```text
NOT a wrapper.

   sub_197F0  =  slot 1 of manager vtable 0x1003934C
                 (0x197F0: `mov esi, ecx`; `push`; `call sub_12760`; `ret 4`)

   sub_197F0  --0x197F7-->  sub_12760 (factory)
                              |
                              +--0x12CF1--> CNIFS::ctor
                              +--0x12D06--> publication
                              +--0x12F56--> InitInGameApp

`sub_197F0` never touches 0x9860 and never holds the CNIFS pointer.
It reaches InitInGameApp only indirectly, through the factory it invokes.
```

### Q4

> If it cannot be closed, where exactly is the break?

```text
It CAN be closed inside iips.dll.  The only remaining break is the ENTRY
to this whole lifecycle from outside the module:

   EXTERNAL_BOUNDARY
     at the caller of manager vtable 0x1003934C
        -> which dispatches sub_197F0 (slot 1)
        -> which calls the factory sub_12760

   The break is NOT:
     - a function identity problem (sub_197F0 / sub_12760 / sub_90D0 / sub_9860
       are all identified)
     - a vtable resolution problem (0x1003530C slot 20 resolves literally)
     - an indirect-call ambiguity (the target set has exactly one member,
       0x10009860, at that slot)

   It is an out-of-module caller boundary.
```

### Q5

> Does the current evidence prove that
> `constructor -> [this+0x60]=0 -> InitInGameApp -> +0x95D0==0 -> initIfsLib`
> is the path that actually occurred at runtime?

```text
NO.

The path is proven STATIC_REACHABLE and its identity links are
STATIC_DIRECT, but no runtime observation exists in this round:

   RUNTIME_INITINGAMEAPP   = UNKNOWN
   RUNTIME_IFS2_LOAD       = UNKNOWN
   RUNTIME_CREATEIFS       = UNKNOWN
   RUNTIME_FIRST_FAILURE   = UNKNOWN

Independent dynamic evidence from earlier rounds remains limited to the
module level:
   module-level observed : iips.dll load, no IFS2.dll image event,
                           no IIPSHostApp process, WIN_IIPS_INIT_ERROR
   function-level executed: NOT determined
```

---

## Final Status Report

```text
CONSTRUCTOR              = sub_90D0        (iips.dll+0x90D0, ret 4, this=[esp+0x24])
FACTORY                  = sub_12760       (iips.dll+0x12760)
ALLOCATION               = MSVCR80.dll!operator new(unsigned int)
                           0x1F0 bytes, via iips.dll thunk 0x2BE34
VTABLE                   = 0x1003530C  (CNIFS primary, 54 slots, 0xD8)
                             InitInGameApp = slot 20 = offset +0x50 = 0x9860
INITINGAMEAPP_ENTRY      = vtable method, __thiscall, 0 immediate callers,
                           1 function-pointer occurrence (the slot itself)
SUB197F0_RELATION        = slot 1 of a DIFFERENT vtable (0x1003934C);
                           it calls the FACTORY, not InitInGameApp
OBJECT_IDENTITY          = STATIC_DIRECT across the whole chain
                           (allocation -> ctor -> publication ->
                            retrieval -> vtable slot -> callee this)
LIFECYCLE_CLOSURE        = CLOSED inside iips.dll

RUNTIME_INITINGAMEAPP    = UNKNOWN
RUNTIME_IFS2_LOAD        = UNKNOWN
RUNTIME_CREATEIFS        = UNKNOWN
RUNTIME_FIRST_FAILURE    = UNKNOWN

EXTERNAL_BOUNDARY
   - caller of manager vtable 0x1003934C (entry into sub_197F0)
   - MSVCR80.dll!operator new
   - KERNEL32.dll!LoadLibraryW
   - KERNEL32.dll!GetProcAddress
   - the CreateIFSLibDll export object (inside ifs2.dll)
   - the DestoryIFSLibDll export object (inside ifs2.dll)
   - KERNEL32.dll!FreeLibrary
   - KERNEL32.dll!GetPrivateProfileIntW

NO_PATCH
NO_BYPASS
NO_FAKE_SUCCESS
NO_DLL_EXE_MODIFICATION
NO_IMPORT_EXPORT_MODIFICATION
NO_VTABLE_MODIFICATION
NO_CODE_INJECTION
NO_API_HOOK
NO_DEBUGGER_ATTACH
NO_ETW_API_TRACING
NO_DYNAMIC_CONFIRMED
```

## Final Classification

```text
EX062_CNIFS_LIFECYCLE

CONSTRUCTOR_RECOVERED              STATIC_DIRECT
FACTORY_RECOVERED                  STATIC_DIRECT
ALLOCATION_CONFIRMED               STATIC_DIRECT (operator new, 0x1F0)
PUBLICATION_RECOVERED              STATIC_DIRECT ([parent+0x19C])
VTABLE_RECONSTRUCTED               STATIC_DIRECT (7 vtables, 173 slots)
INITINGAMEAPP_IS_VTABLE_METHOD     STATIC_DIRECT (slot 20 of 0x1003530C)
INITINGAMEAPP_HAS_ZERO_DIRECT_CALL STATIC_DIRECT
INITINGAMEAPP_DISPATCH_FOUND       STATIC_DIRECT (sub_12760 @ 0x12F56)
SUB197F0_IS_NOT_A_WRAPPER          STATIC_DIRECT
SUB197F0_REACHES_VIA_FACTORY       STATIC_DIRECT
OBJECT_IDENTITY_CLOSED             STATIC_DIRECT
LIFECYCLE_CLOSURE                  CLOSED_INSIDE_IIPS_DLL
EXTERNAL_BOUNDARY_REMAINS          manager caller of 0x1003934C

RUNTIME_INITINGAMEAPP              UNKNOWN
RUNTIME_IFS2_LOAD                  UNKNOWN
RUNTIME_CREATEIFS                  UNKNOWN
RUNTIME_FIRST_FAILURE              UNKNOWN
```

## Verification Artifacts

```text
ex062_vtable.csv             173 rows: all 8 reconstructed vtables
ex062_lifecycle_edges.csv     23 rows: every lifecycle edge + evidence level
ex062_this_chain.csv          17 rows: this-pointer propagation register by register
ex062_caller_map.json               : caller/dispatch map for the key functions
ex062_vtable.txt                    : vtable walk of the ctor's immediates
ex062_vtable_identity.txt           : final vtable determination + 54 slots
ex062_dispatch.txt                  : all reference forms to 0x9860
ex062_closure.txt                   : the 6-segment identity chain
ex062_sub197f0.txt                  : sub_197F0 body + vtable membership
ex062_vt_39350.txt                  : manager vtable 0x1003934C, 47 slots
ex062_identity.txt                  : identity ledger + [..+0x19C] writers
ex062_parent_stability.txt          : parent-object stability across publish/dispatch
ex062_alloc.txt                     : the allocation thunk -> operator new
```
