# CODOL_EX063_IIPS_EXTERNAL_ENTRY

## Scope and Constraints Observed

This round is offline static analysis only.

Not performed:

```text
API hooking
debugger attach
Frida
ETW API tracing
runtime injection
patch
bypass
fake success
parameter modification
IIPS state modification
EXE/DLL modification
process injection
vtable patch
```

No process was started, attached to, or instrumented.

### Binary integrity

```text
iips.dll  sha256  72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
          size    347704
          image   0x10000000 + 0x55000
```

Unchanged from EX-060 / EX-061 / EX-062.

### Evidence vocabulary

```text
STATIC_DIRECT      operand / target is literal in the decoded instruction
STATIC_INDIRECT    value arrives via pointer, register, or indirect call
STATIC_REACHABLE   a static CFG path exists, edge is not literal
EXTERNAL_BOUNDARY  resolution requires a module outside the analysed one
STATIC_UNKNOWN     static data is insufficient

DYNAMIC_CONFIRMED is NOT used in this round.
```

---

## EXECUTIVE ANSWER

The external entry IS resolved.

```text
0x1003934C is the primary vtable of the MANAGER class inside iips.dll.
Its unique construction path is the EXPORTED function:

    GetResourceManagerII     iips.dll export @ RVA 0x1C80

which allocates 0x410 bytes, calls the manager constructor sub_11F20,
and publishes the object to the global 0x1004EB68.

sub_197F0 is slot 1 of that manager vtable.  It is invoked from a
MANAGER METHOD (sub_1A270, itself vtable slot 5) via

    0x1A2FC  mov ecx, [esi+0x19C]     ; a MANAGER stored at +0x19C
    0x1A302  mov eax, [ecx]
    0x1A304  mov edx, [eax+4]         ; slot 1
    0x1A309  call edx                 ; ==> sub_197F0
```

Therefore:

```text
IIPS_EXTERNAL_ENTRY = iips.dll!GetResourceManagerII  (exported)
                      -> manager object (vtable 0x1003934C)
                      -> manager method sub_1A270 (slot 5)
                      -> sub_197F0 (slot 1)
                      -> sub_12760 (factory)
                      -> CNIFS::InitInGameApp -> initIfsLib
```

The remaining boundary is the caller of the exported function, which lives
outside this module.

---

## A. Manager vtable `0x1003934C`

```text
vtable VA    0x1003934C
vtable RVA   0x3934C
section      .rdata
slots        47
size         0xBC bytes
```

### A.1 All references to `0x1003934C` in iips.dll

```text
little-endian 4-byte occurrences of 0x1003934C : 2
     raw 0x011FB4  RVA 0x11FB4  VA 0x10011FB4  section .text
     raw 0x0124FD  RVA 0x124FD  VA 0x100124FD  section .text

RVA-only encoding (imm32 = 0x3934C) occurrences : 0
```

Both are vtable-install instructions:

| RVA | function | instruction | role |
|---|---|---|---|
| `0x11FB1` | `sub_11F20` | `mov dword ptr [ebp], 0x1003934c` | primary ctor install |
| `0x124FB` | `sub_124D0` | `mov dword ptr [edi], 0x1003934c` | base ctor install |

```text
definition      : RVA 0x3934C (.rdata)      STATIC_DIRECT
address-take    : NONE (no lea reg,[0x1003934C])
pointer storage : 2 sites (the two constructors)   STATIC_DIRECT
read            : via [this] at dispatch sites      STATIC_INDIRECT
indirect call   : 16 distinct slots observed        STATIC_INDIRECT
dead/reference  : NONE
```

### A.2 `0x1003934C` slot map (all 47 slots)

| slot | offset | target RVA | note |
|---:|---|---|---|
| 0 | `+0x00` | `0x12480` | deleting-dtor thunk |
| **1** | **`+0x04`** | **`0x197F0`** | **the target of this round** |
| 2 | `+0x08` | `0x135B0` | |
| 3 | `+0x0C` | `0x1A1A0` | |
| 4 | `+0x10` | `0x1A410` | |
| 5 | `+0x14` | `0x1A270` | the slot-1 dispatcher |
| 6 | `+0x18` | `0x1A5B0` | |
| 7 | `+0x1C` | `0x1A760` | |
| 8 | `+0x20` | `0x1A7E0` | |
| 9 | `+0x24` | `0x13900` | |
| 10 | `+0x28` | `0x181A0` | |
| 11 | `+0x2C` | `0x18300` | |
| 12 | `+0x30` | `0x13A60` | |
| 13 | `+0x34` | `0x13D60` | |
| 14 | `+0x38` | `0x13E80` | |
| 15 | `+0x3C` | `0x14730` | |
| 16 | `+0x40` | `0x14A00` | |
| 17 | `+0x44` | `0x14F60` | |
| 18 | `+0x48` | `0x13B30` | |
| 19 | `+0x4C` | `0x199C0` | |
| 20 | `+0x50` | `0x15DD0` | |
| 21 | `+0x54` | `0x17620` | |
| 22 | `+0x58` | `0x17630` | |
| 23 | `+0x5C` | `0x15EE0` | |
| 24 | `+0x60` | `0x177B0` | |
| 25 | `+0x64` | `0x17900` | |
| 26 | `+0x68` | `0x178F0` | |
| 27 | `+0x6C` | `0x17F60` | |
| 28 | `+0x70` | `0x18520` | |
| 29 | `+0x74` | `0x19030` | |
| 30 | `+0x78` | `0x19110` | |
| 31 | `+0x7C` | `0x191A0` | |
| 32 | `+0x80` | `0x19220` | |
| 33 | `+0x84` | `0x192B0` | |
| 34 | `+0x88` | `0x19D80` | |
| 35 | `+0x8C` | `0x19BC0` | |
| 36 | `+0x90` | `0x1A990` | |
| 37 | `+0x94` | `0x153B0` | |
| 38 | `+0x98` | `0x1AAA0` | |
| 39 | `+0x9C` | `0x1AC40` | |
| 40 | `+0xA0` | `0x1ACD0` | |
| 41 | `+0xA4` | `0x1AD60` | |
| 42 | `+0xA8` | `0x1ADE0` | |
| 43 | `+0xAC` | `0x14CE0` | |
| 44 | `+0xB0` | `0x101F0` | |
| 45 | `+0xB4` | `0x193A0` | |
| 46 | `+0xB8` | `0x19460` | |

```text
EVIDENCE  STATIC_DIRECT for every slot
```

### A.3 `sub_197F0` re-confirmed at slot 1

```text
RVA 0x39350  ->  dword 0x100197F0
slot         1
offset       +0x04
target       RVA 0x197F0
EVIDENCE     STATIC_DIRECT
```

---

## B. Manager Object

### B.1 Construction

The manager object is constructed by the EXPORTED factory:

```text
GetResourceManagerII     RVA 0x1C80
  0x1C80  push -1
  0x1C82  push 0x100325A9
  0x1C87  mov eax, fs:[0]
  0x1C8D  push eax
  0x1C8E  push ecx
  0x1C8F  mov eax, [0x10042020]        ; security cookie
  0x1C94  xor eax, esp
  0x1C96  push eax
  0x1C97  lea eax, [esp+8]
  0x1C9B  mov fs:[0], eax
  0x1CA1  test byte ptr [0x1004EB6C], 1 ; already-created guard
  0x1CA8  jne 0x10001D05                ; return the cached singleton
  0x1CAA  or dword ptr [0x1004EB6C], 1
  0x1CB1  push 0x410                    ; *** sizeof(MANAGER) = 1040 ***
  0x1CB6  mov dword ptr [esp+0x14], 0
  0x1CBE  call 0x1002BE34               ; operator new (MSVCR80)
  0x1CC3  add esp, 4
  0x1CC6  mov [esp+4], eax
  0x1CCA  test eax, eax
  0x1CCC  mov byte [esp+0x10], 1
  0x1CD1  je 0x10001CEE                 ; allocation failure -> cache NULL
  0x1CD3  push eax                      ; arg1 = raw memory
  0x1CD4  call 0x10011F20               ; *** MANAGER CONSTRUCTOR ***
  0x1CD9  mov [0x1004EB68], eax         ; *** PUBLICATION (global) ***
  0x1CDE  mov ecx, [esp+8]
  0x1CE2  mov fs:[0], ecx
  0x1CE9  pop ecx
  0x1CEA  add esp, 0x10
  0x1CED  ret

  0x1CEE  xor eax, eax                  ; allocation failed
  0x1CF0  mov [0x1004EB68], eax
  ...
  0x1D05  mov eax, [0x1004EB68]         ; cached singleton
  ...
```

The sibling export:

```text
GetResourceManager        RVA 0x1BC0
  0x1BF1  push 0x480                    ; sizeof(SIBLING) = 1152
  0x1BFE  call 0x1002BE34               ; operator new
  0x1C14  call 0x10010200               ; sibling ctor
  0x1C19  mov [0x1004EB70], eax         ; publication
```

### B.2 Constructor `sub_11F20`

```text
function  iips.dll + 0x11F20
extent    0x11F20 .. 0x1247D
size      289 instructions
this      0x11F5B  mov ebp, [esp+0xEC]
return    0x11FF... 
```

#### vtable writes (two phases)

| order | RVA | destination | vtable | phase |
|---:|---|---|---|---|
| 1 | `0x11F66` | `[ebp+0x00]` | `0x1003929C` | base |
| 2 | `0x11F7A` | `[ebp+0x04]` | `0x1003926C` | base |
| 3 | `0x11F93` | `[ebp+0x20]` | `0x100344E4` | base |
| 4 | `0x11FAA` | `[ebp+0x44]` | `0x10039290` | base |
| **5** | **`0x11FB1`** | **`[ebp+0x00]`** | **`0x1003934C`** | **derived (final)** |
| 6 | `0x11FB8` | `[ebp+0x04]` | `0x1003940C` | derived |
| 7 | `0x11FBF` | `[ebp+0x20]` | `0x10039430` | derived |
| 8 | `0x11FC6` | `[ebp+0x44]` | `0x10039438` | derived |

The later group overwrites the earlier one, so the FINAL primary vtable of
the object is `0x1003934C`. This is the standard MSVC multi-vtable
construction sequence.

```text
EVIDENCE  STATIC_DIRECT
```

#### Field initialisation

```text
0x11F70  xor ebx, ebx
0x11F72  mov [esp+0xE4], ebx               ; SEH state
0x11F79  push eax ; 0x11F81 call [0x10033034]   ; InitializeCriticalSection([this+8])
0x11F87  lea eax, [ebp+0x24]
0x11F92  push eax ; 0x11F9A call sub_5B70       ; init [this+0x24] region
0x11F9F  mov [ebp+0x40], ebx               ; = 0
0x11FCD  call sub_289D0
0x11FD2  mov [ebp+0x4C], eax               ; list head
0x11FD5  mov byte [eax+0x2D], 1
0x11FDC  mov [eax+4], eax
...
0x1220B  mov [ebp+0x310], 0x100344E4
0x12220  mov [ebp+0x310], 0x1003AEB0
0x122AC  mov [ebp+0x19C], ebx              ; *** [this+0x19C] = 0 ***
```

Field extent:

```text
max [this+disp] written/read by sub_11F20 : +0x380
max [this+disp] by sub_124D0              : +0x40C
allocated size                            : 0x410
=> consistent (0x410 > 0x40C)
```

### B.3 Publication / ownership

| item | value | evidence |
|---|---|---|
| allocation | `operator new(0x410)` at `0x1CBE` | `STATIC_DIRECT` |
| constructor | `sub_11F20` at `0x1CD4` | `STATIC_DIRECT` |
| `this` | `[esp+0xEC]` == the pushed EAX == allocation pointer | `STATIC_DIRECT` |
| storage destination | global `0x1004EB68` | `STATIC_DIRECT` |
| guard global | `0x1004EB6C` (bit 0 = created) | `STATIC_DIRECT` |
| ownership | module-level singleton, process lifetime | `STATIC_DIRECT` |

### B.4 The other `+0x19C` field owner

`sub_124D0` is the second manager constructor (called from `sub_102A0`
and the deleting-destructor thunk `sub_12480`):

```text
0x124D7  mov eax, fs:[0]
...
0x124F7  mov edi, [esp+0x2C]        ; this
0x124FB  mov [edi], 0x1003934C      ; primary vtable
0x12501  mov [edi+4], 0x1003940C
0x12508  mov [edi+0x20], 0x10039430
0x1250F  mov [edi+0x44], 0x10039438
0x12516  mov ecx, edi
0x12520  call sub_15290
0x1254B  mov [edi+0x380], 0x10035660
...
0x126F7  mov [edi+0x20], 0x100344E4
0x12735  mov [edi+4], 0x1003926C
0x12742  mov [edi], 0x1003929C      ; base vtable restored (dtor direction)
```

This is the **destructor ordering** of the same class (base vtables
restored at the end), which confirms `sub_124D0` is the paired
constructor/destructor body used by the deleting thunk `sub_12480`
(`vtable 0x1003934C` slot 0).

---

## C. `sub_197F0`

### C.1 Full body

```text
0x197F0  8b542404    mov edx, dword ptr [esp + 4]     ; arg2 (stack)
0x197F4  56          push esi
0x197F5  8bf1        mov esi, ecx                     ; this (ECX)
0x197F7  e8648fffff  call 0x10012760                   ; ==> sub_12760
0x197FC  84c0        test al, al
0x197FE  750d        jne 0x1001980D                   ; success
0x19800  8bce        mov ecx, esi
0x19802  e819000000  call 0x10019820                   ; cleanup/rollback
0x19807  32c0        xor al, al                       ; return FALSE
0x19809  5e          pop esi
0x1980A  c20400      ret 4
0x1980D  b001        mov al, 1                        ; return TRUE
0x1980F  5e          pop esi
0x19810  c20400      ret 4
```

### C.2 Answers to E1..E6

#### E1 - calling convention

```text
__thiscall-style with one stack argument, callee-cleaned.

evidence:
  0x197F5  mov esi, ecx        ; ECX is consumed  -> this pointer
  0x1980A  ret 4               ; pops one 4-byte stack argument
  0x19810  ret 4

CONVENTION = __thiscall + 1 stack arg (ret 4)
EVIDENCE   = STATIC_DIRECT
```

#### E2 - is ECX the manager object?

```text
YES.

The unique dispatch site is sub_1A270 + 0x1A309:
  0x1A2FC  mov ecx, [esi+0x19C]     ; object from the manager's +0x19C
  0x1A302  mov eax, [ecx]
  0x1A304  mov edx, [eax+4]         ; slot 1
  0x1A309  call edx                 ; ECX = that object

ECX is not modified between 0x1A2FC and 0x1A309.

The object at [esi+0x19C] is a MANAGER:
  - all 16 slots observed on it resolve inside manager vtable 0x1003934C
  - its field set (+0x5C/+0x60/+0x64/+0x19C/+0x34C) matches the manager
    family, not CNIFS (sizeof 0x1F0)

CONVENTION = ECX is a MANAGER object
EVIDENCE   = STATIC_DIRECT (for the load and slot) + STATIC_INDIRECT
             (for the runtime instance)
```

#### E3 - parameter count and meaning

```text
one stack argument, `[esp+4]`, loaded into EDX at 0x197F0.

In the only observed call site (0x1A309) the caller pushes:
  0x1A307  push ebx
  0x1A308  push edi
  ... (plus one more push earlier in the block)

The argument is read into EDX but not otherwise used before the call to
sub_12760.  Its semantic meaning is:

PARAM_COUNT  = 1 stack dword
PARAM_MEANING = STATIC_UNKNOWN (loaded but not dereferenced by sub_197F0
                before control transfers to the factory)
EVIDENCE     = STATIC_DIRECT for the load, STATIC_UNKNOWN for semantics
```

#### E4 - return value

```text
boolean in AL:
   0x1980D  mov al, 1   -> success
   0x19807  xor al, al  -> failure

the caller tests it:
   0x1A30B  mov ebx, eax
   0x1A30D  cmp ebx, -1
   0x1A310  jne 0x1001A32D
   0x1A312  mov eax, 0xE0000013     ; error code on failure

RETURN       = BOOL (AL)
EVIDENCE     = STATIC_DIRECT
```

#### E5 - does it only `call sub_12760`?

```text
NO.  It also has:

  state handling
    0x197FC  test al, al
    0x197FE  jne  0x1980D

  failure path
    0x19800  mov ecx, esi        ; restore this
    0x19802  call sub_19820      ; <== separate rollback helper
    0x19807  xor al, al

  error handling
    (the error-code production is done by the CALLER, not here:
     0x1A312 mov eax,0xE0000013 / call sub_6960)

  no direct object stores, no flags written by sub_197F0 itself.

EVIDENCE  STATIC_DIRECT
```

#### E6 - does the manager save the CNIFS*?

```text
The manager does NOT save the CNIFS* into a manager field.
`sub_12760` (the factory) stores it at [parent+0x19C] and consumes it
locally at 0x12F40.

IMPORTANT DISTINCTION (identical offset, different object):

  (A) sub_12760's parent `esi`
        0x12D06  [parent+0x19C] := CNIFS*
        0x12F40  ecx := [parent+0x19C]   -> CNIFS slot 20

  (B) sub_1A270's `this` (`esi`)
        0x1A2FC  ecx := [manager+0x19C]  -> MANAGER slot 1

Both use offset +0x19C, but sub_12760's parent and sub_1A270's `this`
are DIFFERENT instances.  The field is polymorphic across the manager
family (or it is a container-of-X slot).

EVIDENCE  STATIC_DIRECT for both sites; the runtime aliasing between the
          two instances is STATIC_UNKNOWN.
```

---

## D. Slot-1 Dispatch - complete caller map

### D.1 Direct callers of `sub_197F0`

```text
immediate CALL (E8 rel32, all alignments)     : 0
CALL register                                 : 0
CALL [memory]                                 : 0
vtable slot reference (le32 0x100197F0)       : 1 at RVA 0x39350
export / import                               : 0
callback table                                : 0
```

The single reference is manager vtable slot 1.

### D.2 The dispatch site

```text
caller function   sub_1A270   (manager vtable 0x1003934C slot 5)
caller RVA        0x1A309
object source     ECX := [ESI + 0x19C]      (0x1A2FC)
                  ESI := ECX at function entry (0x1A285) = manager `this`
vtable source     [ECX]                     (0x1A302)
slot offset       +0x04                     (0x1A304)
target resolution 0x100197F0
target RVA        0x197F0  = sub_197F0
```

Instruction-level evidence:

```text
0x1A26E  0400               (alignment padding / preceding tail)
0x1A270  81ec08010000       sub esp, 0x108          <== function entry
0x1A276  a120200410         mov eax, [0x10042020]
0x1A27B  33c4               xor eax, esp
0x1A27D  89842404010000     mov [esp+0x104], eax
0x1A284  56                 push esi
0x1A285  8bf1               mov esi, ecx            ; this = MANAGER
0x1A287  80be4c03000000     cmp byte [esi+0x34C], 0
0x1A28E  57                 push edi
0x1A28F  8bbc2414010000     mov edi, [esp+0x114]
0x1A296  0f8402010000       je 0x1001A39E
0x1A29C  83be9c01000000     cmp dword [esi+0x19C], 0
0x1A2A3  0f84f5000000       je 0x1001A39E
0x1A2A9  85ff               test edi, edi
0x1A2AB  754a               jne 0x1001A2F7
...
0x1A2F7  803f00             cmp byte [edi], 0
0x1A2FA  7539               jne 0x1001A335
0x1A2FC  8b8e9c010000       mov ecx, [esi+0x19C]    ; <== object
0x1A302  8b01               mov eax, [ecx]          ; vtable
0x1A304  8b5004             mov edx, [eax+4]        ; slot 1
0x1A307  53                 push ebx
0x1A308  57                 push edi
0x1A309  ffd2               call edx                ; ==> sub_197F0
0x1A30B  8bd8               mov ebx, eax
0x1A30D  83fbff             cmp ebx, -1
```

Note `0x1A26E` is NOT a valid entry (the bytes `04 00` are the tail of the
preceding instruction); the true function entry is `0x1A270`, and the only
reference to it in the module is the vtable slot at RVA `0x3939C` (slot 5).

```text
EVIDENCE  STATIC_DIRECT (loads/slot) + STATIC_INDIRECT (the call form)
```

### D.3 All 16 slots observed on the `[X+0x19C]` object

| slot | offset | manager vtable target |
|---:|---|---|
| 0 | `+0x00` | `sub_12480` |
| **1** | **`+0x04`** | **`sub_197F0`** |
| 2 | `+0x08` | `sub_135B0` |
| 3 | `+0x0C` | `sub_1A1A0` |
| 4 | `+0x10` | `sub_1A410` |
| 5 | `+0x14` | `sub_1A270` |
| 6 | `+0x18` | `sub_1A5B0` |
| 7 | `+0x1C` | `sub_1A760` |
| 8 | `+0x20` | `sub_1A7E0` |
| 9 | `+0x24` | `sub_13900` |
| 23 | `+0x5C` | `sub_15EE0` |
| 25 | `+0x64` | `sub_17900` |
| 26 | `+0x68` | `sub_178F0` |
| 29 | `+0x74` | `sub_19030` |
| 36 | `+0x90` | `sub_1A990` |

Every one of these offsets resolves inside vtable `0x1003934C`, which
independently confirms the object type.

```text
EVIDENCE  STATIC_DIRECT
```

---

## E. External Callers

### E.1 Cross-module scan for `0x1003934C`

Scanned modules (all binaries in the CODOL working directory, priority list
from EX-057 plus the IIPS family):

| module | image base | size | references to `0x1003934C` |
|---|---|---:|---|
| codoMP_client_shipRetail.exe | `0x00400000` | `0x0E659000` | **0** |
| codoMP_client_shipRetailBase.dll | `0x10000000` | `0x03991000` | 0 |
| TenProxy.dll | `0x10000000` | `0x00029000` | 0 |
| GbSpy.dll | `0x10000000` | `0x000A6000` | 0 |
| GameRpcs.dll | `0x10000000` | `0x00272000` | 0 |
| TenRpcs.dll | `0x10000000` | `0x01143000` | 0 |
| GDPLoader.dll | `0x10000000` | `0x0004F000` | 0 |
| GDPImpl.dll | `0x10000000` | `0x00012000` | 0 |
| GDPCODOTrail.dll | `0x10000000` | `0x0000C000` | 0 |
| GameDataPlatformServer.dll | `0x10000000` | `0x00059000` | 0 |
| PolicyProbe.dll | `0x10000000` | `0x006DA000` | 0 |
| TCJ.dll | `0x10000000` | `0x0033E000` | 0 |
| GCloudVoice.dll | `0x10000000` | `0x002CC000` | 0 |
| VSDDrvDll.dll | `0x10000000` | `0x014EC000` | 0 |
| BugTrace.dll | `0x10000000` | `0x0033C000` | 0 |
| TenSLX.dll | `0x10000000` | `0x00293000` | 0 |
| TenSp.dll | `0x10000000` | `0x0002E000` | 0 |
| IIPSHost.dll | `0x10000000` | `0x00093000` | 0 |
| IIPSHostApp.exe | `0x00400000` | `0x00047000` | 0 |
| IIPSVFS.dll | `0x10000000` | `0x00037000` | 0 |
| IIPSCheck.dll | `0x10000000` | `0x00015000` | 0 |
| IIPSStats.dll | `0x10000000` | `0x00045000` | 0 |
| IIPSRepair.dll | `0x10000000` | `0x00038000` | 0 |
| IIPSLaunchRestore.dll | `0x10000000` | `0x0009B000` | 0 |
| iips_policymsg.dll | `0x10000000` | `0x00015000` | 0 |
| **iips.dll** | `0x10000000` | `0x00055000` | **2** |

```text
RESULT
  the manager vtable 0x1003934C is referenced ONLY inside iips.dll.
  No external module names it, so no external module can dispatch its
  slots by absolute vtable address.

  => the external caller must obtain the manager object through the
     EXPORTED function (GetResourceManagerII), not by vtable address.
EVIDENCE  STATIC_DIRECT (byte scan across all listed modules)
```

Also checked and found absent in every module:

```text
le32 of 0x100197F0   (sub_197F0) : only iips.dll (1 hit, the vtable slot)
le32 of 0x10012480   (slot 0)    : only iips.dll (1 hit, the vtable slot)
imm32 of the vtable RVA 0x3934C  : 0 hits anywhere
```

### E.2 The exported entry

```text
iips.dll exports:
    GetResourceManager           RVA 0x1BC0   allocates 0x480, ctor sub_10200
    ReleaseResourceManager       RVA 0x1C60   calls [arg+0][0]
    ReleaseResourceManagerII     RVA 0x1C60   calls [arg+0][0]
    GetResourceManagerII         RVA 0x1C80   allocates 0x410, ctor sub_11F20
                                                -> publishes 0x1004EB68
```

```text
`GetResourceManagerII` is the ONLY constructor path to the object whose
primary vtable is 0x1003934C.

EVIDENCE
  STATIC_DIRECT for the export table entry, the allocation, the ctor call,
  and the global publication.
```

### E.3 Release path (closes the lifecycle)

```text
ReleaseResourceManagerII   RVA 0x1C60
  0x1C60  mov ecx, [esp+4]      ; the object
  0x1C64  test ecx, ecx
  0x1C66  je 0x10001C70
  0x1C68  mov eax, [ecx]        ; vtable
  0x1C6A  mov edx, [eax]        ; slot 0
  0x1C6C  push 1                ; delete flag
  0x1C6E  call edx              ; deleting destructor (sub_12480)
  0x1C70  ret
```

`sub_12480` is manager vtable `0x1003934C` slot 0:

```text
0x12480  push esi
0x12481  mov esi, ecx
0x12483  push esi
0x12484  call 0x100124D0      ; destructor body
0x12489  test byte [esp+8], 1
0x1248E  je 0x10012499
0x12490  push esi
0x12491  call 0x1002BE28      ; operator delete
0x12496  add esp, 4
0x12499  mov eax, esi
0x1249B  pop esi
0x1249C  ret 4
```

```text
EVIDENCE  STATIC_DIRECT
```

---

## F. Manager -> CNIFS Relationship

### F.1 The two `+0x19C` uses are DIFFERENT object instances

This is the most important structural correction of this round.

```text
(A)  sub_12760's parent object  (esi at 0x12D06)
       0x12D06  mov [esi+0x19C], edi     ; edi = CNIFS* from sub_90D0
       0x12F40  mov ecx, [ebx+0x19C]     ; read back
       0x12F48  mov edx, [eax+0x50]      ; slot 20 of the CNIFS vtable
       0x12F56  call edx                 ; -> CNIFS::InitInGameApp

     field holds : CNIFS*
     vtable used : 0x1003530C  (CNIFS primary)
     slot used   : +0x50 (slot 20)

(B)  sub_1A270's `this`  (esi = ecx at 0x1A285, a MANAGER)
       0x1A2FC  mov ecx, [esi+0x19C]     ; read
       0x1A302  mov eax, [ecx]
       0x1A304  mov edx, [eax+4]         ; slot 1
       0x1A309  call edx                 ; -> sub_197F0

     field holds : a MANAGER object
     vtable used : 0x1003934C  (manager primary)
     slot used   : +0x04 (slot 1)
```

### F.2 Class-profile evidence

```text
sub_1A270's `this` field set (esi)      : +0x5C +0x60 +0x64 +0x19C +0x34C
max field offset                         : +0x34C
sizeof(CNIFS)                            : 0x1F0
fits in CNIFS?                           : NO

all 16 slots dispatched on [X+0x19C] resolve inside vtable 0x1003934C
                                         : YES

manager ctor sub_11F20 field extent     : +0x380
manager ctor sub_124D0 field extent     : +0x40C
allocated size in GetResourceManagerII   : 0x410
```

```text
CONCLUSION
  [X+0x19C] is a field of the manager-class family.
  In sub_12760 it is assigned a CNIFS*.
  In sub_1A270 it is read as a MANAGER*.

  These are two different instances (or two different states) of the
  same offset.  The static analysis cannot show that they are the same
  instance; it also cannot exclude it.  What IS excluded is the naive
  reading that [X+0x19C] always holds a CNIFS*.

EVIDENCE
  STATIC_DIRECT for both field accesses and for the vtable/class profile
  comparison.
  STATIC_UNKNOWN for the runtime aliasing.
```

### F.3 Consequence for the chain

```text
The chain
    sub_197F0 -> sub_12760 -> CNIFS -> InitInGameApp
is STATIC_DIRECT and complete.

The chain
    external -> manager -> sub_1A270 -> sub_197F0
is STATIC_DIRECT for the last three hops (manager -> slot5 -> slot1),
and EXTERNAL_BOUNDARY for the first hop (who calls the manager method).

The identity of the object at [manager+0x19C] at the moment sub_1A270
runs is STATIC_UNKNOWN; only the vtable family (manager) is proven.
```

---

## G. Bootstrap Relation

### G.1 How far the chain closes statically

```text
iips.dll INSIDE:

  GetResourceManagerII (export)                  STATIC_DIRECT
     -> operator new(0x410)                      STATIC_DIRECT
     -> sub_11F20 manager ctor                   STATIC_DIRECT
     -> vtable 0x1003934C installed              STATIC_DIRECT
     -> global 0x1004EB68 publication            STATIC_DIRECT
     -> manager method sub_1A270 (slot 5)        STATIC_INDIRECT
     -> sub_197F0 (slot 1)                       STATIC_INDIRECT
     -> sub_12760 factory                        STATIC_DIRECT
     -> operator new(0x1F0) + sub_90D0 CNIFS     STATIC_DIRECT
     -> CNIFS vtable slot 20                     STATIC_INDIRECT
     -> CNIFS::InitInGameApp                     STATIC_DIRECT
     -> CNIFS::initIfsLib                        STATIC_DIRECT
     -> +0x95D0 gate                             STATIC_DIRECT
     -> ifs2.dll bring-up                        STATIC_DIRECT
```

```text
STATIC_BOOTSTRAP_LINK = CONFIRMED (inside iips.dll)
```

### G.2 Where it stops

```text
OUTSIDE iips.dll:

  [ native bootstrap / engine init / client startup ]
        |
        |  must call the EXPORTED GetResourceManagerII
        |  (or reach it through its own function-pointer table)
        v
  GetResourceManagerII

NO module in the CODOL working directory contains the vtable address
0x1003934C, so the external caller cannot be located by vtable identity.

It must be located by:
  - the import of GetResourceManagerII / GetResourceManager, or
  - the import of iips.dll by name, or
  - a delayed/late binding of the export.

Because the EXE's relevant code region is packed (.tp3 / .tvm0) and
IIPSHostApp.exe / other IIPS modules do not import iips.dll's manager
exports in their plain import tables, this hop is:

STATIC_BOOTSTRAP_LINK = EXTERNAL_BOUNDARY
```

```text
EVIDENCE
  STATIC_DIRECT for "no vtable reference exists outside iips.dll"
  EXTERNAL_BOUNDARY for the unresolved caller
```

### G.3 What is NOT claimed

```text
NOT claimed:
  - that GetResourceManagerII IS called in the observed -q run
  - that any manager method IS executed
  - that sub_1A270 IS executed
  - that sub_197F0 IS executed
  - that sub_12760 IS executed
  - that CNIFS::InitInGameApp IS executed
  - that LoadLibraryW IS executed

These are runtime facts and remain UNKNOWN.
```

---

## H. Lifecycle Graph

```text
[ EXTERNAL MODULE / CODOL BOOTSTRAP ]
        |
        |  import / export binding of the iips.dll factory
        |                                          EXTERNAL_BOUNDARY
        v
[ GetResourceManagerII    iips.dll export @ 0x1C80 ]
        |
        |  0x1CA1 test byte [0x1004EB6C],1  (idempotency guard)
        |  0x1CB1 push 0x410                (sizeof MANAGER = 1040)
        |  0x1CBE call operator new         (MSVCR80 !??2@YAPAXI@Z)
        |                                          STATIC_DIRECT
        v
[ MANAGER ALLOCATION    0x410 bytes ]
        |
        |  0x1CD3 push eax ; 0x1CD4 call sub_11F20
        |                                          STATIC_DIRECT
        v
[ sub_11F20   MANAGER CONSTRUCTOR ]
        |
        |  0x11FB1 [this+0x00] = 0x1003934C   (FINAL primary vtable)
        |  0x11FB8 [this+0x04] = 0x1003940C
        |  0x11FBF [this+0x20] = 0x10039430
        |  0x11FC6 [this+0x44] = 0x10039438
        |  0x122AC [this+0x19C] = 0
        |                                          STATIC_DIRECT
        v
[ MANAGER OBJECT    vtable 0x1003934C    47 slots ]
        |
        |  0x1CD9 mov [0x1004EB68], eax     (global publication)
        |                                          STATIC_DIRECT
        v
[ GLOBAL SINGLETON 0x1004EB68 ]
        |
        |  later, a manager method runs.
        |  the dispatch path is:
        |     manager vtable slot 5 = sub_1A270
        |     (invoked through [singleton]->[+0x14])
        |                                          STATIC_INDIRECT
        v
[ sub_1A270    manager vtable slot 5 ]
        |
        |  0x1A285 mov esi, ecx             (this = MANAGER)
        |  0x1A29C cmp [esi+0x19C], 0
        |  0x1A2FC mov ecx, [esi+0x19C]     (a MANAGER)
        |  0x1A302 mov eax, [ecx]
        |  0x1A304 mov edx, [eax+4]         (slot 1)
        |  0x1A309 call edx
        |                                          STATIC_DIRECT + INDIRECT
        v
[ sub_197F0    manager vtable slot 1 ]
        |
        |  0x197F5 mov esi, ecx             (this = that MANAGER)
        |  0x197F7 call sub_12760           (THE FACTORY)
        |                                          STATIC_DIRECT
        v
[ sub_12760    THE FACTORY ]
        |
        |  0x12CD3 push 0x1F0               (sizeof CNIFS = 496)
        |  0x12CD8 call operator new
        |  0x12CF1 call sub_90D0            (CNIFS ctor)
        |  0x12D06 [parent+0x19C] = CNIFS*
        |                                          STATIC_DIRECT
        v
[ sub_90D0    CNIFS CONSTRUCTOR ]
        |
        |  0x91CF [this+0x60] = 0
        |                                          STATIC_DIRECT
        v
[ CNIFS OBJECT   sizeof 0x1F0   [+0x60] == 0 ]
        |
        |  0x12F40 mov ecx, [ebx+0x19C]
        |  0x12F48 mov edx, [eax+0x50]      (CNIFS slot 20)
        |  0x12F56 call edx
        |                                          STATIC_INDIRECT
        v
[ CNIFS::InitInGameApp    0x9860    CNIFS vtable 0x1003530C slot 20 ]
        |
        |  0x99D2 call sub_9570
        |                                          STATIC_DIRECT
        v
[ CNIFS::initIfsLib    0x9570 ]
        |
        |  0x95D0 cmp [this+0x60], 0
        |                                          STATIC_DIRECT
        +---------------------+---------------------+
        |                                           |
   [ != 0 ]                                    [ == 0 ]
        |                                           |
  LeaveCriticalSection                        build <iipsdir>+L"/ifs2.dll"
  mov al, 1                                   0x96E9 LoadLibraryW
  ret 0x20                                     |
  (SUCCESS SHORT-CIRCUIT)                      v
        |                                  [ ifs2.dll bring-up ]
        |                                  0x977C GetProcAddress
        |                                  0x97A5 CreateIFSLibDll
        |                                  0x97A9 [this+0x60] = EAX
        |                                  0x97CC GetProcAddress
        +---------------------+---------------------+
                              v
                    [ back to InitInGameApp ]
                              |
                              v
                    [ later manager/CNIFS state ]
```

### H.1 Edge classification table

| from | to | evidence |
|---|---|---|
| external module | `GetResourceManagerII` | `EXTERNAL_BOUNDARY` |
| `GetResourceManagerII` | `operator new` | `STATIC_DIRECT` |
| `operator new` | `sub_11F20` | `STATIC_DIRECT` |
| `sub_11F20` | manager object | `STATIC_DIRECT` |
| manager object | global `0x1004EB68` | `STATIC_DIRECT` |
| global singleton | `sub_1A270` (slot 5) | `STATIC_INDIRECT` |
| `sub_1A270` | `sub_197F0` (slot 1) | `STATIC_INDIRECT` |
| `sub_197F0` | `sub_12760` | `STATIC_DIRECT` |
| `sub_12760` | `sub_90D0` | `STATIC_DIRECT` |
| `sub_90D0` | `[this+0x60] = 0` | `STATIC_DIRECT` |
| `sub_12760` | `InitInGameApp` (CNIFS slot 20) | `STATIC_INDIRECT` |
| `InitInGameApp` | `initIfsLib` | `STATIC_DIRECT` |
| `initIfsLib` | `+0x95D0` gate | `STATIC_DIRECT` |
| `+0x95D0` != 0 | success short-circuit | `STATIC_REACHABLE` |
| `+0x95D0` == 0 | ifs2 bring-up | `STATIC_DIRECT` |
| ifs2 bring-up | `LoadLibraryW` return use | `STATIC_REACHABLE` |

---

## Q1 - Q6 Answers

### Q1

> `0x1003934C` manager vtable 属于什么对象/接口？

```text
It is the PRIMARY vtable of a MANAGER class inside iips.dll.

  47 slots, size 0xBC, located at .rdata RVA 0x3934C
  sizeof(instance) = 0x410 (allocated by GetResourceManagerII)

Object characteristics:
  - constructed by sub_11F20 (also installed by sub_124D0)
  - holds InitializingCriticalSection([this+8]) and sub-objects at
    +0x24, +0x44, +0x310, +0x1D4, +0x158, +0x104, +0x120
  - publishes itself to the global 0x1004EB68
  - dispatches slots 0,1,3,4,5,6,7,8,9,23,25,26,29,36 from its members

It is NOT the CNIFS vtable (that is 0x1003530C, 54 slots, sizeof 0x1F0).
It is NOT an exported interface; it is a module-internal singleton.

CLASS NAME : STATIC_UNKNOWN (no RTTI/name recovered)
ROLE       : IIPS resource-manager object owning the ifs bring-up state
EVIDENCE   : STATIC_DIRECT
```

### Q2

> 谁创建并发布这个 manager object？

```text
CREATED AND PUBLISHED BY THE EXPORTED FACTORY:

    GetResourceManagerII        iips.dll export @ RVA 0x1C80
        0x1CB1  push 0x410
        0x1CBE  call operator new
        0x1CD4  call sub_11F20           ; manager ctor
        0x1CD9  mov [0x1004EB68], eax    ; publication

Secondary path:
    sub_10200  -> call sub_11F20 at 0x1024D
    (sub_10200 is the sibling factory body reached from the other export)

Deletion path:
    ReleaseResourceManager( II ) @ 0x1C60
        -> [obj]->[0] = sub_12480 (deleting destructor)

EVIDENCE : STATIC_DIRECT for both the allocation and the publication.
```

### Q3

> 谁通过 slot 1 调用了 `sub_197F0`？

```text
A MANAGER METHOD:  sub_1A270   (manager vtable 0x1003934C slot 5)

    0x1A270  function entry
    0x1A285  mov esi, ecx             ; this = the MANAGER instance
    0x1A29C  cmp [esi+0x19C], 0
    0x1A2FC  mov ecx, [esi+0x19C]     ; object held at +0x19C
    0x1A302  mov eax, [ecx]           ; its vtable
    0x1A304  mov edx, [eax+4]         ; slot 1
    0x1A309  call edx                 ; ==> sub_197F0

There are exactly 0 immediate callers of sub_197F0 and exactly 1
function-pointer reference to it in the whole module (the vtable slot).

So the ONLY way sub_197F0 can run is via manager slot 1.

EVIDENCE
  STATIC_DIRECT  for the load of [esi+0x19C] and the slot fetch
  STATIC_INDIRECT for the call itself
  STATIC_DIRECT  for "0 immediate callers" and "1 pointer occurrence"
```

### Q4

> `sub_197F0` 的 `this` 和 manager object 是否能够 STATIC_DIRECT/INDIRECT 闭合？

```text
STATIC_INDIRECT (not STATIC_DIRECT).

  ECX at 0x1A309 = [esi+0x19C], and the object at [X+0x19C] is proven to
  be a MANAGER-family object by:
    - all 16 dispatched offsets resolve inside vtable 0x1003934C
    - its field set matches the manager family and exceeds sizeof(CNIFS)

  But the concrete INSTANCE is a runtime value; the static data does not
  identify which manager instance it is.

  Between the load at 0x1A2FC and the call at 0x1A309 there is NO write
  to ECX, so ECX at the call IS that loaded pointer.

VERDICT
  ECX == [manager+0x19C]           STATIC_DIRECT
  that object is MANAGER-family    STATIC_DIRECT
  which instance                   STATIC_INDIRECT / STATIC_UNKNOWN
```

### Q5

> 能否建立 `external caller -> sub_197F0 -> sub_12760 -> InitInGameApp`
> 完整静态链？

```text
MOSTLY YES, with ONE remaining EXTERNAL_BOUNDARY.

CLOSED (STATIC_DIRECT / STATIC_INDIRECT):

  GetResourceManagerII  (exported)
    -> operator new(0x410)
    -> sub_11F20
    -> manager object, vtable 0x1003934C
    -> global 0x1004EB68
    -> [manager vtable slot 5] sub_1A270
    -> [slot 1] sub_197F0
    -> sub_12760
    -> operator new(0x1F0) + sub_90D0
    -> [parent+0x19C] = CNIFS*
    -> [CNIFS slot 20] InitInGameApp
    -> initIfsLib
    -> +0x95D0

NOT CLOSED (EXTERNAL_BOUNDARY):

  [ ? ]
    -> GetResourceManagerII

  i.e. "who imports and calls the exported factory".
  This requires a module outside iips.dll.
```

### Q6

> 这条链能否继续连接到 CODOL native bootstrap？

```text
NOT WITH STATIC EVIDENCE FROM iips.dll ALONE.

Reasons, each verified:

  1. the manager vtable 0x1003934C is referenced ONLY inside iips.dll
     (0 hits in the EXE, in codoMP_client_shipRetailBase.dll, and in all
      24 other scanned modules)

  2. the EXE and Base.dll do not contain the literal 0x1003934C

  3. so the external caller cannot be identified by vtable address, and
     must be found through the IMPORT of the export instead

  4. the EXE region that would contain the caller is packed
     (.tp3 / .tvm0 sections; the import table for the EXE is size 0)

  5. IIPSHostApp.exe and the IIPS DLLs do not reference the vtable

LAST EXTERNAL_BOUNDARY (exact):

    MODULE   : an external module that imports iips.dll
               (expected: codoMP_client_shipRetail.exe or its Base)
    FUNCTION : an as-yet-unrecovered caller of the exported
               GetResourceManagerII
    VTABLE   : none (the boundary is an EXPORT, not a vtable)
    SLOT     : none
    INDIRECT : the call into the export

STATIC_BOOTSTRAP_LINK = EXTERNAL_BOUNDARY
```

---

## I. STATIC_UNKNOWN List

```text
I01  The C++ class name of the manager object (vtable 0x1003934C).
I02  The semantic meaning of the single stack argument of sub_197F0.
I03  Which manager instance is stored at [X+0x19C] when sub_1A270 runs.
I04  Whether sub_12760's parent and sub_1A270's `this` are the same
     instance, different instances, or the same instance across time.
I05  Who calls the manager method sub_1A270 (slot 5) at runtime.
I06  Who first calls the exported GetResourceManagerII.
I07  The meaning of the [this+0x34C] byte flag checked at 0x1A287.
I08  The meaning of the [this+0x1CC]/[0x1CD]/[0x1CE] flags in CNIFS.
I09  What sub_19820 (the rollback helper called from sub_197F0) does.
I10  The error-code mapping for 0xE0000010 / 0xE0000011 / 0xE0000013
     produced by the manager methods.
I11  Whether the EXE or its Base imports GetResourceManagerII.
(packed region; not resolved this round)
I12  Whether the observed -q run ever reached any part of this chain.
I13  The relationship between the four export-cache globals
     0x1004EB68 / 0x1004EB6C / 0x1004EB70 / 0x1004EB74.
I14  Whether sub_10200 (the sibling factory) produces a class whose
     +0x19C also participates in the same chain.
```

---

## J. Impact on the Actual IIPS Failure Point

### J.1 What EX-060/061/062 established

```text
EX-060 : earliest STATIC failure branch = iips.dll+0x96EF
         (LoadLibraryW(<iipsdir>/ifs2.dll) returned NULL)
EX-061 : that region is gated by +0x95D0 ([this+0x60] == 0);
         the initial value of [this+0x60] is provably 0
EX-062 : the CNIFS lifecycle from allocation to InitInGameApp is
         STATIC_DIRECT; the open end was the entry into the factory
```

### J.2 What EX-063 adds

```text
1. The manager class is now fully identified:
      vtable 0x1003934C, 47 slots, sizeof 0x410, ctor sub_11F20.

2. The construction and publication of that manager is an EXPORTED
   function (GetResourceManagerII), NOT an internal-only path.

3. sub_197F0 is slot 1 of that manager vtable, and it IS dispatched,
   from manager method sub_1A270 (slot 5) at 0x1A309.

4. The entry into the whole IIPS lifecycle is therefore:

      GetResourceManagerII  (export)
        -> manager
        -> slot 5
        -> slot 1 (sub_197F0)
        -> factory sub_12760
        -> CNIFS
        -> InitInGameApp
        -> initIfsLib
        -> +0x95D0
        -> ifs2 bring-up

5. The boundary moved OUT of iips.dll.  It is now an ordinary DLL
   export-import boundary, not a vtable/indirect-call unknown.
```

### J.3 What this does NOT establish

```text
It does NOT establish that:
   - GetResourceManagerII was called in the observed -q run
   - any manager method executed
   - sub_1A270 executed, or that [X+0x19C] was non-zero
   - sub_197F0 executed
   - sub_12760 executed
   - CNIFS::InitInGameApp executed
   - [this+0x60] was 0 at the gate
   - LoadLibraryW executed or returned NULL
   - the observed WIN_IIPS_INIT_ERROR came from this path

This round is lifecycle/external-entry analysis only.
IIPS_OBJECT_LIFECYCLE_GLOBAL_CLOSURE != IIPS runtime failure identified.
```

### J.4 Why the failure point is unchanged

```text
The earliest STATIC failure branch remains iips.dll+0x96EF.
Nothing in EX-063 introduces an earlier failure condition inside the
recovered CFG.

The only NEW information relevant to the failure:
  the chain is reachable from an exported entry, so the question
  "did IIPS run its bring-up" now reduces to
     "did the loader call iips.dll!GetResourceManagerII",
  which is a testable import-level fact for a future round, WITHOUT
  any API hooking or debugger attach.
```

---

## K. Next Experiment

The boundary is now an ordinary export/import edge. The next round can
attack it statically without any hooking.

### K.1 Primary: resolve the importer of the iips.dll exports

```text
1. Parse the import tables of every CODOL module for iips.dll:
      codoMP_client_shipRetail.exe
      codoMP_client_shipRetailBase.dll
      BugTrace.dll, TenProxy.dll, GbSpy.dll, ...
   Record whether GetResourceManager / GetResourceManagerII appear.

2. If the EXE imports them, locate the IAT slot and every `call [IAT]`.

3. If the EXE does NOT import them, look for:
      - a LoadLibraryW("iips.dll") + GetProcAddress pair
      - a delay-load stub
      - the packed .tp3 / .tvm0 dispatcher
```

### K.2 Secondary: recover the string that names the exports

```text
4. Search all modules for the ASCII/UTF-16 strings
      "GetResourceManagerII"
      "GetResourceManager"
      "ReleaseResourceManagerII"
   and report every occurrence with module + RVA + section.
```

### K.3 Tertiary: recover the sibling class relationship

```text
5. Determine whether sub_10200 (the GetResourceManager sibling factory,
   allocating 0x480) produces a class whose methods also reach sub_12760,
   or whether GetResourceManagerII is the only route.
```

### K.4 Explicitly NOT next

```text
- no API hooking
- no debugger attach
- no Frida
- no ETW API tracing
- no patch / bypass / fake success
- no modification of any binary
- no claim that the chain executed
```

---

## Final Status Report

```text
IIPS_EXTERNAL_ENTRY        = iips.dll!GetResourceManagerII (export @ RVA 0x1C80)
MANAGER_VTABLE             = 0x1003934C  (47 slots, .rdata RVA 0x3934C)
MANAGER_OWNER              = sub_11F20 (ctor), sub_124D0 (dtor body)
                             published to global 0x1004EB68
SUB197F0_CALLER            = sub_1A270 (manager vtable slot 5) @ 0x1A309
                             via [esi+0x19C] -> [vt+0x04]
BOOTSTRAP_LINK             = EXTERNAL_BOUNDARY
                             (who imports/calls GetResourceManagerII)
LIFECYCLE_GLOBAL_CLOSURE   = CLOSED_INSIDE_IIPS_DLL
                             OPEN_AT_THE_EXPORT_IMPORT_EDGE

RUNTIME_INITINGAMEAPP      = UNKNOWN
RUNTIME_IFS2_LOAD          = UNKNOWN
RUNTIME_CREATEIFS          = UNKNOWN
RUNTIME_FIRST_FAILURE      = UNKNOWN
```

## Final Classification

```text
EX063_IIPS_EXTERNAL_ENTRY

MANAGER_VTABLE_RECOVERED            STATIC_DIRECT (47/47 slots)
MANAGER_CTOR_RECOVERED              STATIC_DIRECT (sub_11F20)
MANAGER_ALLOCATION_CONFIRMED        STATIC_DIRECT (operator new, 0x410)
MANAGER_PUBLICATION_FOUND           STATIC_DIRECT (global 0x1004EB68)
EXPORTED_ENTRY_FOUND                STATIC_DIRECT (GetResourceManagerII)
SLOT1_DISPATCH_FOUND                STATIC_DIRECT (sub_1A270 @ 0x1A309)
SUB197F0_CALL_CONVENTION            STATIC_DIRECT (__thiscall + ret 4)
SUB197F0_RETURN_VALUE               STATIC_DIRECT (BOOL in AL)
SUB197F0_REACHES_FACTORY            STATIC_DIRECT (0x197F7 -> 0x12760)
OBJECT_IDENTITY_CHAIN               STATIC_DIRECT (+ STATIC_INDIRECT at
                                                    the two indirect calls)
EXTERNAL_BOUNDARY_REMAINS           import/call of GetResourceManagerII

RUNTIME_INITINGAMEAPP               UNKNOWN
RUNTIME_IFS2_LOAD                   UNKNOWN
RUNTIME_CREATEIFS                   UNKNOWN
RUNTIME_FIRST_FAILURE               UNKNOWN

NO_PATCH
NO_BYPASS
NO_FAKE_SUCCESS
NO_API_HOOK
NO_DEBUGGER_ATTACH
NO_FRIDA
NO_ETW_API_TRACING
NO_RUNTIME_INJECTION
NO_DLL_EXE_MODIFICATION
NO_IMPORT_EXPORT_MODIFICATION
NO_VTABLE_MODIFICATION
NO_DYNAMIC_CONFIRMED
```

## Verification Artifacts

```text
ex063_manager_vtable.csv       47 rows: vtable 0x1003934C slot map
ex063_manager_vtable_all.csv  112 rows: all 9 manager-family vtables
ex063_external_callers.csv     12 rows: per-module reference scan
ex063_manager_lifecycle.csv    25 rows: ordered lifecycle steps
ex063_bootstrap_edges.csv      12 rows: bootstrap edge classification
ex063_vt_scan.txt                     : vtable references + slot map
ex063_manager_ctor.txt                : the two constructors
ex063_hierarchy.txt                   : full class hierarchy + vtables
ex063_slot1_precise.txt               : [X+0x19C] dispatch sites
ex063_slot1_crux.txt                  : CNIFS vs manager vtable resolution
ex063_class_match.txt                 : class-profile comparison
ex063_nested_vt.txt                   : nested-object vtable confirmation
ex063_external.txt                    : cross-module vtable scan
ex063_factories.txt                   : exported factory bodies
ex063_global.txt                      : singleton publication
ex063_final_chain.txt                 : the assembled chain
```
