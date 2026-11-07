# EX-061_IIPS_THIS60_DATAFLOW

## Scope and Constraints Observed

This round is **pure static dataflow tracing** of the CNIFS field `+0x60`.

Not performed:

```text
API hooking
debugger attach
ETW API tracing
parameter matrix expansion
IIPS patch
bypass
fake success
dynamic execution proof
```

No process was started, attached to, or instrumented. `iips.dll` and the
CODOL EXE were opened read-only.

## Artifact Provenance

```text
iips.dll    tools/EX035_DIR/IIPS/iips.dll
            size     347704
            image    0x10000000 + 0x55000
            sha256   72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
            .text    0x1000 .. 0x32C3B   (60000020)
            exports  GetResourceManager        0x1BC0
                     ReleaseResourceManager    0x1C60
                     ReleaseResourceManagerII  0x1C60
                     GetResourceManagerII      0x1C80
```

The hash is unchanged from EX-060. No file was modified.

## Evidence Levels Used

```text
STATIC_DIRECT     the operand / target is literal in the decoded instruction
STATIC_INDIRECT   the value comes through a pointer/register/vtable
STATIC_REACHABLE  there is a static CFG path from an entry to this site
STATIC_UNKNOWN    the static data is insufficient

DYNAMIC_* is NOT used in this round.
```

## Method

```text
1. Linear sweep of the whole .text for every instruction with a memory
   operand of displacement 0x60 (145 hits).
2. Recursive-descent function recovery from 3,264 entry candidates
   (strict MSVC prologues widened by padding-boundary entries), giving
   60,559 owned instruction addresses.
3. Owner attribution: the OUTERMOST function whose recovered body
   contains the site.
4. Recursive-descent disassembly rejects sites that are not valid
   instruction boundaries (misaligned data false positives).
5. Object-identity check: compare each function's full `[base+disp]`
   field profile against the CNIFS constructor's 29-field profile.
```

---

## A. All WRITES to `+0x60`

### A.1 CNIFS-family writes (this == the CNIFS object)

**Exactly two writes exist in the entire image.**

| # | RVA | function | basic block | instruction | source value | predecessor | successor |
|---:|---|---|---|---|---|---|---|
| W1 | `+0x91CF` | `sub_90D0` **CNIFS::ctor** | BB @ `0x90D0` (linear) | `mov dword ptr [ebp + 0x60], ebx` | `ebx`, set by `xor ebx,ebx` at `0x90FF` ⇒ **0** | `0x91C9 call [0x100331A4]` (string dtor) | `0x91D2 mov [ebp+0x58], ebx` |
| W2 | `+0x97A9` | `sub_9570` **CNIFS::initIfsLib** | BB @ `0x97A1` | `mov dword ptr [ebp + 0x60], eax` | `eax` = return of the indirect call at `0x97A5` = **`CreateIFSLibDll(...)`** | `0x97A5 call eax` | `0x97AC jne 0x97C3` (non-zero) / `0x97AE` (zero) |

#### W1 in full context

```text
0x90FF  xor ebx, ebx                  ; ebx = 0
   ... (no instruction between 0x90FF and 0x91CF rewrites ebx: verified)
0x91C9  call dword ptr [0x100331A4]   ; MSVCP80 basic_string dtor
0x91CF  mov dword ptr [ebp + 0x60], ebx   ; <== [this+0x60] = 0
0x91D2  mov dword ptr [ebp + 0x58], ebx   ; [this+0x58] = 0
0x91D5  mov dword ptr [ebp + 0x5C], ebx   ; [this+0x5C] = 0
0x91D8  mov dword ptr [ebp + 0x54], ebx   ; [this+0x54] = 0
0x91DB  mov dword ptr [ebp + 0xCC], ebx   ; [this+0xCC] = 0
0x91E1  mov dword ptr [ebp + 0xF8], ebx
0x91E7  mov dword ptr [ebp + 0xFC], ebx
0x91ED  mov byte  ptr [ebp + 0x154], bl
0x91F3  mov byte  ptr [ebp + 0x155], bl
0x91F9  mov dword ptr [ebp + 0x100], ebx
0x91FF  mov eax, ebp                  ; return this
0x9214  ret 4                         ; pops one stack argument
```

#### W2 in full context

```text
0x9770  mov  esi, [0x10033014]        ; IAT KERNEL32!GetProcAddress
0x9776  push 0x10034964               ; "CreateIFSLibDll"
0x977B  push eax                      ; HMODULE from LoadLibraryW
0x977C  call esi                      ; GetProcAddress
0x977E  test eax, eax
0x9780  mov  [ebp+0x58], eax
0x9783  jne  0x97A1
0x97A1  lea  ecx, [ebp+0x50]          ; out-parameter slot
0x97A4  push ecx
0x97A5  call eax                      ; CreateIFSLibDll([this+0x50])
0x97A7  test eax, eax
0x97A9  mov  [ebp+0x60], eax          ; <== [this+0x60] = RESULT
0x97AC  jne  0x97C3
```

### A.2 Non-CNIFS writes to a `+0x60` field

The other 27 `mov [reg+0x60], x` instructions found in `.text` are on
**stack slots** (`base=esp`) or on **different object types**. They do
not touch the CNIFS object:

| base | representative sites | object |
|---|---|---|
| `esp` | `0x127D`, `0x3338`, `0x334D`, `0x3488`, `0x35E0`, `0x3774`, `0x4192`, `0x8E34`, `0x11A38`, `0x11BB8`, `0x12EEA`, `0x13F42`, `0x1623F`, `0x18426`, `0x18462`, `0x18499`, `0x1958F`, `0x196EA`, `0x1C512`, `0x1E28F`, `0x22ABC`, `0x272CB`, `0x29D38`, `0x2D66F`, `0x2E344`, `0x2E4F9`, `0x2EE85` | stack frame -- NOT the object |

Classification:

```text
CNIFS +0x60 WRITE count = 2   (W1 ctor, W2 initIfsLib)
```

---

## B. All READs of `+0x60`

### B.1 CNIFS-family reads

| # | RVA | function | BB | instruction | destination | evidence |
|---:|---|---|---|---|---|---|
| R1 | `+0x929F` | `sub_9240` **CNIFS::dtor** | `0x9240` body | `mov ecx, dword ptr [esi + 0x60]` | `ecx` → `[ecx]` → `[edx+8]` → indirect call | `STATIC_DIRECT` |
| R2 | `+0x95D0` | `sub_9570` **initIfsLib** | `0x9570` prologue BB | `cmp dword ptr [ebp + 0x60], 0` | flags | `STATIC_DIRECT` |
| R3 | `+0x9A2B` | `sub_9860` **InitInGameApp** | BB `0x9A2B` | `mov ecx, dword ptr [ebp + 0x60]` | `ecx` → vtable `[eax+0x2C]`, `push 1` | `STATIC_DIRECT` |
| R4 | `+0x9B51` | `sub_9860` | BB `0x9B51` | `mov ecx, dword ptr [ebp + 0x60]` | vtable `[eax+0x2C]`, `push 5` | `STATIC_DIRECT` |
| R5 | `+0x9B66` | `sub_9860` | BB `0x9B66` | `mov ecx, dword ptr [ebp + 0x60]` | vtable `[eax+0x2C]`, `push 3` | `STATIC_DIRECT` |
| R6 | `+0x9B7B` | `sub_9860` | BB `0x9B7B` | `mov ebp, dword ptr [ebp + 0x60]` | `ebp` **overwritten** → `[ebp]` → `[eax+0x2C]`, `push 4` | `STATIC_DIRECT` |

Read detail:

```text
R3  0x9A2B  mov ecx, [ebp+0x60]     ; ecx = interface pointer
    0x9A2E  mov eax, [ecx]           ; eax = vtable
    0x9A30  mov edx, [eax+0x2C]      ; edx = slot
    0x9A33  push 1
    0x9A35  call edx

R4  0x9B51  mov ecx, [ebp+0x60] ; 0x9B54 mov eax,[ecx] ; 0x9B56 mov edx,[eax+0x2C]
    0x9B59  push 5 ; 0x9B5B call edx

R5  0x9B66  mov ecx, [ebp+0x60] ; 0x9B69 mov eax,[ecx] ; 0x9B6B mov edx,[eax+0x2C]
    0x9B6E  push 3 ; 0x9B70 call edx

R6  0x9B7B  mov ebp, [ebp+0x60]  ; EBP := interface pointer (NOT a stack frame!)
    0x9B7E  mov eax, [ebp]
    0x9B81  mov edx, [eax+0x2C]
    0x9B84  push 4
    0x9B86  mov ecx, ebp
    0x9B88  call edx

R1  0x929F  mov ecx, [esi+0x60]
    0x92A2  cmp ecx, ebx / je 0x92C0
    0x92A6  cmp byte [esi+0x13C], bl
    0x92AC  mov edx, [ecx]
    0x92B2  sete bl
    0x92B5  push ebx
    0x92B6  push eax                 ; [esi+0x138]
    0x92B7  mov eax, [edx+8]
    0x92BA  call eax                 ; vtable slot +8
```

**Reading of R3..R6:** `[this+0x60]` is used as an **interface pointer**
to an object with a C++-style vtable whose slot `+0x2C` takes a single
integer id. The ids observed are **1, 5, 3, 4**.

### B.2 Non-CNIFS reads of a `+0x60` field

| site | owner | base | instruction | object |
|---|---|---|---|---|
| `+0x929F` | `sub_9240` | `esi` | `mov ecx, [esi+0x60]` | **CNIFS** (see above) |
| `+0xC1E1` | `sub_3280`-family | `eax` | `mov eax, [eax+0x60]` | other |
| `+0xC3FD` | other | `eax` | `mov eax, [eax+0x60]` | other |
| `+0x10BE5` | other | `eax` | `mov eax, [eax+0x60]` | other |
| `+0xA327` | `sub_9860` | `ebx` | `mov ecx, [ebx+0x60]` | **NOT this** -- `ebx = [ebp+0x120]` critical-section region |
| `+0xA340` | `sub_9860` | `ebx` | `mov ecx, [ebx+0x60]` | same as above |
| `+0xA4D9` | `sub_9860` | `ebx` | `mov ecx, [ebx+0x60]` | same |
| `+0xA613` | `sub_9860` | `edi` | `mov ecx, [edi+0x60]` | `edi` = loop element, not this |
| `+0xA639` | `sub_9860` | `edi` | `mov ecx, [edi+0x60]` | same |
| `+0xA68E` | `sub_9860` | `edi` | `mov ecx, [edi+0x60]` | same |
| `+0xA93A` | `sub_A860` | `edi` | `mov ecx, [edi+0x60]` | other object (profile match 0.10) |
| `+0x127A2`, `+0x17978`, `+0x2E457` | other | `ebx` | ... | other |
| `+0xB0D0`, `+0xB0D6` | `sub_B0D0` | `ecx` | `cmp/mov [ecx+0x60]` | other object |
| `+0xCBA0`, `+0xCBA6` | `sub_CBA0` | `ecx` | `cmp/mov [ecx+0x60]` | other object |
| `+0x13629`..`+0x138D3` | `sub_135B0` | `ebp` | `mov edx/eax, [ebp+0x60]` | other framework object |
| `+0x15747` | `sub_15683` | `esi` | `lea ecx, [esi+0x60]` | other |
| `+0x15CF4` | `sub_15A00` | `ebp` | `lea ecx, [ebp+0x60]` | other (profile match 0.15) |
| `+0x2F01C` | `sub_2E310` | `ebp` | `mov ecx, [ebp+0x60]` | other |
| `+0x2F2A6` | `sub_2E310` | `ecx` | `mov eax, [ecx+0x60]` | other (nested) |
| `+0x28EBF` | other | `edx` | `mov edx, [edx+0x60]` | other |

**Important:** the offsets `+0xA327`/`+0xA340`/`+0xA4D9` are inside
`InitInGameApp` but their base register is `ebx`, which holds
`[ebp+0x120]` (the critical-section / embedded sub-object region), **not**
the CNIFS `this`. They are therefore NOT accesses to the CNIFS field
`+0x60` and must not be merged with R3..R6.

---

## C. All COMPARE / TEST / ADDRESS-TAKE of `+0x60`

| # | RVA | function | kind | instruction | predecessor | successor | evidence |
|---:|---|---|---|---|---|---|---|
| C1 | `+0x95D0` | `sub_9570` initIfsLib | **COMPARE** | `cmp dword ptr [ebp + 0x60], 0` | `0x95C8 mov byte [esp+0x98],1` | `0x95D4 jne 0x10009818` (taken) / `0x95DA` (fallthrough) | `STATIC_DIRECT` |
| C2 | `+0x92C6` | `sub_9240` dtor | **COMPARE** | `cmp dword ptr [esi + 0x60], ebx` (ebx=0) | `0x92C0 mov [esi+0x138], ebx` | `0x92CC je 0x100092DA` / `0x92CE` | `STATIC_DIRECT` |
| C3 | `+0x92C9` | `sub_9240` dtor | **ADDRESS-TAKE** | `lea edi, [esi + 0x60]` | `0x92C6 cmp` | `0x92CC je 0x92DA` / `0x92CE mov eax,[esi+0x5C]` | `STATIC_DIRECT` |
| C4 | `+0x929F` | `sub_9240` dtor | READ+**COMPARE** | `mov ecx,[esi+0x60]` then `0x92A2 cmp ecx, ebx` | `0x929D je 0x92C6` | `0x92A4 je 0x92C0` / `0x92A6` | `STATIC_DIRECT` |

Any `test [...]` on `+0x60`:

```text
NONE.  No `test` instruction in iips.dll uses a +0x60 memory operand.
```

Any address-taken other than C3:

```text
The only lea whose destination operand is derived from a +0x60 memory
operand on the CNIFS object is C3 (0x92C9).
Other lea forms found (`0x15C19 lea edi,[esp+0x60]`,
`0x15CF4 lea ecx,[ebp+0x60]`, `0x15747 lea ecx,[esi+0x60]`) belong to
non-CNIFS objects / stack slots.
```

---

## D. Constructor / Initializer

### D.1 The CNIFS constructor is `sub_90D0`

```text
entry           iips.dll + 0x90D0
extent          +0x90D0 .. +0x9214
                76 instructions, one basic block (linear, no branches)
calling conv    arg on stack; `ret 4` (callee pops 1 argument)
this            obtained at 0x90F4:  mov ebp, [esp+0x24]
return value    obtained at 0x91FF:  mov eax, ebp   (returns this)
```

Evidence that it is the constructor:

```text
1. It installs vtable pointers as immediates:
     0x90F8  mov dword ptr [ebp+0x0],  0x10035204
     0x9105  mov dword ptr [ebp+0x4],  0x100352EC
     0x911A  mov dword ptr [ebp+0x50], 0x100351F8
     0x9126  mov dword ptr [esi+0x0],  0x10035408   (esi = ebp+8 subobject)
     0x9134  mov dword ptr [ebp+0x0],  0x1003530C
     0x913B  mov dword ptr [ebp+0x4],  0x100353E8
     0x9142  mov dword ptr [ebp+0x50], 0x10035418
2. It zeroes the whole "uninitialised" state:
     [this+0x54] = 0    [this+0x58] = 0
     [this+0x5C] = 0    [this+0x60] = 0
     [this+0xCC] = 0    [this+0xF8] = 0    [this+0xFC] = 0
     [this+0x100] = 0   [this+0x138] = 0
     [this+0x144..0x150] = 0
     [this+0x154] = 0   [this+0x155] = 0
3. It is invoked exactly once, right after operator new, by the factory.
4. The object it produces is stored at [parent+0x19C].
```

**⇒ The initial value of `[this+0x60]` is 0.**

### D.2 The factory that calls the constructor

```text
sub_12760 (0x12760 .. 0x13587), 819 instructions
    0x12CD3  push 0x1F0                 ; sizeof(CNIFS) = 496 bytes
    0x12CD8  call 0x1002BE34            ; operator new
    0x12CDD  add esp, 4
    0x12CE0  mov [esp+0x24], eax
    0x12CE4  test eax, eax
    0x12CEE  je 0x10012CFA              ; allocation failure -> edi = 0
    0x12CF0  push eax                   ; arg1 = raw memory
    0x12CF1  call 0x100090D0            ; ==> CNIFS::ctor (sub_90D0)
    0x12CF6  mov edi, eax               ; edi = CNIFS*
    0x12CFC  test edi, edi
    0x12D06  mov [esi+0x19C], edi       ; parent keeps the CNIFS*
```

The object is 496 bytes (`0x1F0`). Field `+0x60` is well inside it.

### D.3 The full creation chain

```text
sub_197F0 (0x197F0 .. 0x19810)   tiny wrapping entry, `ret 4`
    no static callers in iips.dll  -> STATIC_UNKNOWN how it is entered
    |
    +-- 0x197F7  call 0x10012760   -> the factory
            |
            +-- 0x12CF1  call 0x100090D0   -> CNIFS::ctor
                    |
                    +-- 0x91CF  [this+0x60] = 0
```

### D.4 The destructor is `sub_9240`

```text
entry        iips.dll + 0x9240 .. +0x937F   (89 insns)
calling conv mov esi, ecx (__thiscall), `ret`
```

```text
0x9293  mov eax, [esi+0x138]
0x9299  xor ebx, ebx
0x929B  cmp eax, ebx / je 0x92C6
0x929F  mov ecx, [esi+0x60]          ; interface pointer
0x92A2  cmp ecx, ebx / je 0x92C0
0x92A6  cmp byte [esi+0x13C], bl
0x92AC  mov edx, [ecx]
0x92B2  sete bl
0x92B5  push ebx
0x92B6  push eax
0x92B7  mov eax, [edx+8]
0x92BA  call eax                     ; vtable slot +8 teardown
0x92C0  mov [esi+0x138], ebx
0x92C6  cmp [esi+0x60], ebx / je 0x92DA
0x92C9  lea edi, [esi+0x60]
0x92CE  mov eax, [esi+0x5C]           ; DestoryIFSLibDll
0x92D1  cmp eax, ebx / je 0x92D8
0x92D5  push edi                      ; &[this+0x60]
0x92D6  call eax                      ; DestoryIFSLibDll(&[this+0x60])
0x92D8  mov [edi], ebx                ; [this+0x60] = 0
0x92DA  mov eax, [esi+0x54]           ; HMODULE
0x92DD  cmp eax, ebx / je 0x92EB
0x92E1  push eax
0x92E2  call [0x10033018]             ; KERNEL32!FreeLibrary
0x92E8  mov [esi+0x54], ebx           ; HMODULE = 0
```

The destructor consumes exactly the two values `initIfsLib` produced
(`[this+0x54]` HMODULE and `[this+0x5C]` DestoryIFSLibDll) and clears
`[this+0x60]`. This is a closed
`ctor → initIfsLib → dtor` lifecycle on **one** object.

---

## E. CreateIFSLibDll → `+0x60` Relationship

```text
RELATION: STRICT ONE-WAY ASSIGNMENT
          a  ->  [CNIFS+0x60]
```

```text
0x977C  call esi              ; GetProcAddress(hMod, "CreateIFSLibDll")
0x977E  test eax, eax
0x9780  mov  [ebp+0x58], eax  ; [this+0x58] = the resolved address
0x9783  jne  0x97A1

0x97A1  lea  ecx, [ebp+0x50]  ; arg1 = &[this+0x50]  (out slot)
0x97A4  push ecx
0x97A5  call eax              ; eax == [this+0x58] == CreateIFSLibDll
0x97A7  test eax, eax
0x97A9  mov  [ebp+0x60], eax  ; *** [this+0x60] := CreateIFSLibDll(...) ***
0x97AC  jne  0x97C3
```

### E.1 Exact identity of the producer

| item | value | evidence |
|---|---|---|
| callee address source | `[this+0x58]` | `STATIC_INDIRECT` |
| `[this+0x58]` producer | `GetProcAddress(hMod, "CreateIFSLibDll")` at `0x977C` | `STATIC_DIRECT` |
| call form | `call eax` (indirect through a resolved export pointer) | `STATIC_INDIRECT` |
| argument | `lea ecx,[ebp+0x50]` pushed ⇒ out-parameter `&[this+0x50]` | `STATIC_DIRECT` |
| result consumed by | `mov [ebp+0x60], eax` at `0x97A9` | `STATIC_DIRECT` |
| branch on result | `jne 0x97C3` (non-zero ⇒ continue), fallthrough `0x97AE` (zero ⇒ error) | `STATIC_DIRECT` |

### E.2 Is the assignment unconditional?

```text
YES, on the code path that reaches 0x97A9.
The instruction has no guard of its own; it always executes when control
arrives at 0x97A5->0x97A9.

Two facts matter:
  (a) `mov [ebp+0x60], eax` is executed even when eax == 0
      (the zero test at 0x97A7 does not guard the store; the store is
      after the test and before the branch).  So on error path E3 the
      field is explicitly set to 0, not left stale.
  (b) The store happens before `[this+0x5C]` (DestoryIFSLibDll) is
      resolved.  So the field can be non-zero while the destroy slot is
      still 0.
```

### E.3 What the field is NOT

```text
[this+0x60] != HMODULE                (that is [this+0x54])
[this+0x60] != CreateIFSLibDll addr   (that is [this+0x58])
[this+0x60] != DestoryIFSLibDll addr  (that is [this+0x5C])
[this+0x60] != status code            (that is [this+0xCC])

[this+0x60] IS the object/handle returned by CreateIFSLibDll, used later
as an interface pointer with a vtable at slot +0x2C and slot +8.
```

### E.4 Cross-check with the destructor

The destructor calls `[this+0x5C]` (which `GetProcAddress` set) with
`&[this+0x60]` as its single argument (`push edi` at `0x92D5`, with
`edi = &[this+0x60]` from `0x92C9`). So `DestoryIFSLibDll` takes the
address of exactly the field that `CreateIFSLibDll`'s result was stored
into. This is a self-consistent create/destroy pairing on the same slot.

### E.5 Classification

```text
CreateIFSLibDll -> [this+0x60]      STATIC_DIRECT
  (the assignment instruction is literal; the callee target is
   STATIC_INDIRECT through a GetProcAddress-resolved pointer)
```

---

## F. `+0x95D0` Decision Tree

### F.1 The instruction

```text
CNIFS::initIfsLib
  0x95C8  mov byte ptr [esp+0x98], 1     ; SEH state
  0x95D0  cmp dword ptr [ebp + 0x60], 0  ; <== THE DECISION
  0x95D4  jne 0x10009818
```

### F.2 Taken branch: `[this+0x60] != 0`

```text
0x95D4  jne 0x10009818
   |
   v
0x9818  push ebx
0x9819  call dword ptr [0x1003302C]   ; KERNEL32!LeaveCriticalSection
0x981F  lea ecx, [esp+0xA4]
0x9826  mov dword ptr [esp+0x98], 0xFFFFFFFF
0x9831  call [0x1003326C]             ; ~basic_string<char>
0x9837  mov al, 1
0x9839  ... epilogue ...
0x985D  ret 0x20
```

```text
RESULT:  initIfsLib returns TRUE (AL = 1)
EFFECT:  LoadLibraryW is NOT called
         GetProcAddress("CreateIFSLibDll") is NOT called
         CreateIFSLibDll is NOT called
         [this+0x54] / [this+0x58] / [this+0x5C] / [this+0x60] unchanged
         [this+0xCC] unchanged
CLASS:   STATIC_REACHABLE
```

This is an **idempotency / already-initialised short circuit**, not an
error branch: it sets `AL = 1`, i.e. success.

### F.3 Fallthrough: `[this+0x60] == 0`

```text
0x95DA  cmp dword ptr [esp+0xB8], 0
0x95E2  je  0x10009649          ; skips ONLY the narrow path-seed build
0x95E4  push 0x10034904         ; "\/ "
0x95ED  std::string ctor
0x960B  call sub_94C0           ; strip trailing separators
0x9623  assign -> [this+0x104]
0x9649  cmp [esp+0xBC], 0x10 / jae 0x9661     (wide SSO check)
0x9661  push eax / call sub_1EF0
0x967A  basic_string<wchar_t>::ctor
0x9690  (free temp if non-null)
0x96A1  push 0x10034908         ; L"/ifs2.dll"
0x96B0  operator+<wchar_t>      ; <iipsdir> + L"/ifs2.dll"
0x96CF  assign -> [this+0x104]
0x96D5  mov eax, [esp+0x58]
0x96DE  cmp [esp+0x6C], 8 / jae 0x96E8        (narrow SSO check)
0x96E8  push eax
0x96E9  call [0x10033010]       ; KERNEL32!LoadLibraryW
0x96EF  test eax, eax
0x96F1  mov [ebp+0x54], eax     ; HMODULE
0x96F4  jne 0x9770              ; NULL -> E1
   ...
0x97A9  mov [ebp+0x60], eax     ; <== the only way this field becomes != 0
   ...
0x9837  mov al, 1
0x9839  ... ret 0x20
```

```text
RESULT:  initIfsLib returns TRUE (AL = 1) on success
         initIfsLib returns FALSE (AL = 0) on any of E1..E4
CLASS:   STATIC_REACHABLE
```

### F.4 Full decision tree

```text
CNIFS::initIfsLib(this)
  |
  +- EnterCriticalSection([this+0x120])
  |
  +- IF [this+0x60] != 0
  |     LeaveCriticalSection ; return TRUE
  |     (no ifs2.dll load, no resolver, no create)
  |
  +- ELSE  ([this+0x60] == 0)
        |
        +- build path = f([this+0x104]) + L"/ifs2.dll"
        |
        +- LoadLibraryW(path)  -> [this+0x54]
        |     |
        |     +- NULL  -> log "Failed to open dllfile"
        |     |           [this+0xCC] = 1
        |     |           AL = 0, return FALSE            [E1]
        |     |
        |     +- ok
        |           |
        |           +- GetProcAddress(h, "CreateIFSLibDll") -> [this+0x58]
        |           |     |
        |           |     +- NULL -> log "Failed to get function CreateIFSLibDll"
        |           |     |           [this+0xCC] = 2
        |           |     |           AL = 0, return FALSE      [E2]
        |           |     |
        |           |     +- ok
        |           |           |
        |           |           +- CreateIFSLibDll(&[this+0x50]) -> [this+0x60]
        |           |           |     |
        |           |           |     +- 0 -> log "Failed to create ifs lib"
        |           |           |     |        [this+0x60] = 0  (stored!)
        |           |           |     |        [this+0xCC] = 1
        |           |           |     |        AL = 0, return FALSE   [E3]
        |           |           |     |
        |           |           |     +- != 0
        |           |           |           |
        |           |           |           +- GetProcAddress(h,"DestoryIFSLibDll") -> [this+0x5C]
        |           |           |                 |
        |           |           |                 +- NULL -> log "Failed to get proc DestoryIFSLibDll"
        |           |           |                 |           [this+0xCC] = 3
        |           |           |                 |           AL = 0, return FALSE  [E4]
        |           |           |                 |
        |           |           |                 +- ok  ->  [this+0xCC] stays 0
        |           |           |                            AL = 1, return TRUE    [OK]
```

### F.5 Decision-tree consequence table

| entry `[this+0x60]` | what initIfsLib does | return | LoadLibraryW called? |
|---|---|---|---|
| `!= 0` | short-circuit | `TRUE` | **NO** |
| `== 0` | full IFS2 bring-up | `TRUE` (OK) or `FALSE` (E1..E4) | **YES** |

```text
CLASSIFICATION
  the branch itself                     STATIC_DIRECT
  the branch is statically reachable    STATIC_REACHABLE
  which edge is taken at runtime        STATIC_UNKNOWN (value is runtime state)
```

---

## G. The IIPS State Machine the Static Evidence Can Explain

### G.1 Object identity

```text
ONE object class: CNIFS, sizeof = 0x1F0 (496 bytes)
allocated by      operator new at 0x12CD8 (from factory sub_12760)
constructed by    sub_90D0  (this = [esp+0x24], ret 4)
stored at         [parent+0x19C]
initialised by    sub_9570  CNIFS::initIfsLib   (this = [esp+0xA0], ret 0x20)
destroyed by      sub_9240  CNIFS::~CNIFS       (this = ecx, ret)
```

Proof that all three use the SAME object type:

```text
constructor field set          : 29 distinct [this+disp] offsets
initIfsLib field set           : 9 offsets
  +0x50 +0x54 +0x58 +0x5C +0x60 +0x64 +0xCC +0x104 +0x120
  -> a strict SUBSET of the constructor's field set  (9/9)
InitInGameApp field set        : 16 offsets
  -> 10 of 16 appear in the constructor's field set
                                  (the other 6 are on other registers)
```

The competing `+0x60` sites in `sub_135B0`, `sub_2E310`, `sub_15A00`,
`sub_A860`, `sub_B0D0`, `sub_CBA0` do **not** match this profile
(their `this`-shaped fields include +0x3F0, +0x404, +0x18C, +0x1A0,
+0x218, +0x310 and negative displacements), so they are **different
object types** and must not be merged with CNIFS.

### G.2 States

```text
S0  UNCONSTRUCTED
      no object exists.

S1  CONSTRUCTED, UNINITIALISED      <- produced by sub_90D0 @ 0x91CF
      [this+0x50] = 0
      [this+0x54] = 0        HMODULE
      [this+0x58] = 0        CreateIFSLibDll
      [this+0x5C] = 0        DestoryIFSLibDll
      [this+0x60] = 0        <== create result / interface pointer
      [this+0xCC] = 0        status
      [this+0xF8] = [this+0xFC] = [this+0x100] = 0
      [this+0x138] = 0
      [this+0x144..0x150] = 0
      [this+0x154] = [this+0x155] = 0
      vtables at [this+0], [this+4], [this+0x50]

S2  IFS INITIALISED                 <- produced by sub_9570 success path
      [this+0x50] = ifs object handle (out from CreateIFSLibDll)
      [this+0x54] = HMODULE(<iipsdir>/ifs2.dll)
      [this+0x58] = CreateIFSLibDll
      [this+0x5C] = DestoryIFSLibDll
      [this+0x60] = CreateIFSLibDll result, non-NULL
      [this+0xCC] = 0
      reaches 0x97F4 -> 0x9818 -> 0x9837 mov al,1

S3  IFS INIT FAILED                 <- produced by sub_9570 error paths
      sub-state by [this+0xCC]:
        1  E1  LoadLibraryW NULL                 (0x9704 -> 0x971C)
        2  E2  GetProcAddress Create NULL        (0x9785 -> 0x9795)
        1  E3  CreateIFSLibDll returned 0        (0x971C via 0x97BE)
        3  E4  GetProcAddress Destory NULL       (0x97D5 -> 0x97E5)
      [this+0x60] on failure:
        E1: never written -> remains 0
        E2: never written -> remains 0
        E3: written to 0 at 0x97A9 (result was 0)
        E4: non-zero (set at 0x97A9), destroy slot still 0
      returns AL = 0

S4  TEARDOWN                        <- produced by sub_9240
      DestoryIFSLibDll(&[this+0x60]); [this+0x60] = 0
      FreeLibrary([this+0x54]);        [this+0x54] = 0
```

### G.3 State-transition graph

```text
  S0  --sub_90D0 @0x91CF-->  S1      ([this+0x60] = 0)

  S1  --initIfsLib, [this+0x60]==0--> S2  ([this+0x60] = CreateIFSLibDll())
  S1  --initIfsLib, [this+0x60]!=0--> S1  (no-op, returns TRUE)
  S1  --initIfsLib, [this+0x60]==0--> S3  (any of E1..E4, returns FALSE)

  S2  --initIfsLib (re-entered)-->     S2  (short-circuit, returns TRUE)
  S2  --sub_9240-->                    S4

  S3  --initIfsLib (re-entered)-->     S3  if [this+0x60]==0 (E1/E2),
                                            retries the whole bring-up
                                       S2  if [this+0x60]!=0 (E4),
                                            short-circuits to "success"
```

Note the asymmetry: an object left in E4 (`[this+0x60] != 0`,
`[this+0x5C] == 0`) will on re-entry take the `+0x95D4` short-circuit and
report success even though the destroy slot was never resolved. That is a
static property of the code, independent of any run.

### G.4 How `InitInGameApp` fits

```text
CNIFS::InitInGameApp (0x9860)  this = ecx
  no immediate callers in iips.dll  -> STATIC_UNKNOWN entry path
                                       (vtable/export boundary)
  0x98B7  EnterCriticalSection([this+0x120])
  0x98CD  call sub_6D20                QoS helper (log-only on failure)
  0x98E6  early-exit gate on [esp+0x118]
  0x99D2  call initIfsLib(this)        <== the +0x95D0 decision happens here
  0x99D7  test al,al / jne 0x9A2B
     |
     +- al == 0  -> 0x99DB cleanup -> 0x9A24 xor al,al -> ret 0x38 (FALSE)
     |
     +- al == 1  -> 0x9A2B..           reads [this+0x60] as an interface
                                       pointer and calls vtable slot +0x2C
                                       with ids 1, 5, 3, 4
```

Consumption order in the success branch:

```text
0x9A2B  vtable call id 1     (immediately after initIfsLib succeeds)
0x9A37  IIPSHostApp.ini string ctor   (push 0x10034A68)
0x9A8B  GetPrivateProfileIntW   IIPSHostApp.ini / ResPool / ReservedSize
0x9B51  vtable call id 5      (guarded by [this+0x1CE])
0x9B66  vtable call id 3      (guarded by [this+0x1CD])
0x9B7B  vtable call id 4      (guarded by [this+0x1CC])
```

Because the three guarded calls test `[this+0x1CE]`, `[this+0x1CD]`,
`[this+0x1CC]` and then dispatch through `[this+0x60]`, the value written
by `CreateIFSLibDll` is the **dispatch object for the IFS bring-up
sequence**.

---

## H. Still-Unexplained State

```text
H01  Runtime value of [this+0x60] when InitInGameApp reaches 0x99D2.
H02  Whether the CNIFS object is constructed before the first
     InitInGameApp call in every execution path.
     (sub_197F0 has no static caller -> the entry order is STATIC_UNKNOWN.)
H03  Whether InitInGameApp is ever called a second time on the same object
     (which would engage the 0x95D4 short-circuit).
H04  The concrete object behind [this+0x60] after CreateIFSLibDll
     (it comes from ifs2.dll, which was not analysed this round).
H05  The meaning of vtable slot +0x2C and its ids 1 / 3 / 4 / 5.
H06  The meaning of vtable slot +8 used by the destructor.
H07  Whether [this+0x138] (read by the destructor and pushed to vtable +8)
     is ever set outside the destructor.
H08  The exact content/purpose of [this+0x104] that seeds the ifs2 path
     (it is a std::string; its producer was not fully traced this round).
H09  The relationship between the [this+0x1CC]/[0x1CD]/[0x1CE] flags and
     the HostApp / share-state / resource-manager region of iips.dll.
H10  Whether any execution path can set [this+0x60] != 0 WITHOUT going
     through initIfsLib.  Static answer: NO within iips.dll
     (only W1 and W2 exist), but a foreign module could write it if it
     had the pointer, which is STATIC_UNKNOWN from iips.dll alone.
H11  The runtime order of the factory (0x12CF1) relative to InitInGameApp.
H12  Why IIPSHostApp.ini / ResPool / ReservedSize is read AFTER the
     initIfsLib gate rather than before.
H13  Whether sub_6D20 (QoS helper) can fail in a way that matters later.
     (Its result is not a gate on the recovered path.)
H14  Whether the constructor's operator new failure path (0x12CEE) is
     reachable in practice; if taken, edi = 0 and no CNIFS exists.
```

### H.15 The residual ambiguity, stated precisely

```text
The static data proves the INITIAL value of [this+0x60] is 0 (ctor W1).
The static data proves the ONLY other writer is initIfsLib (W2).

Therefore:
  - If InitInGameApp is entered AFTER the constructor and BEFORE any
    successful initIfsLib, then [this+0x60] == 0 and the +0x95D4 jne is
    NOT taken; the full bring-up (incl. LoadLibraryW) runs.
  - If a previous initIfsLib already succeeded, or if the same
    InitInGameApp ran once already on this object, then
    [this+0x60] != 0 and initIfsLib short-circuits to TRUE.

The static data does NOT establish which of those two orderings held in
the observed -q run.  That remains STATIC_UNKNOWN.
```

---

## I. Impact on the Actual Failure Point

### I.1 What EX-060 established

```text
EARLIEST_STATIC_FAILURE_BRANCH = iips.dll + 0x96EF
   LoadLibraryW(<iipsdir>/ifs2.dll) returns NULL
   -> "Failed to open dllfile", [this+0xCC] = 1, AL = 0
```

### I.2 What EX-061 adds

EX-061 shows that `+0x96EF` is **inside a conditional region that is only
entered when `[this+0x60] == 0`**:

```text
   0x95D0  cmp [this+0x60], 0
   0x95D4  jne 0x9818        ; if != 0 -> SKIP ENTIRELY (return TRUE)
   ...
   0x96E9  call LoadLibraryW
   0x96EF  test eax,eax
```

So there are now **two** candidate explanations for the observed
`WIN_IIPS_INIT_ERROR / 0x8189FEC` outcome:

```text
EXPLANATION A  (the EX-060 reading)
   [this+0x60] == 0 at 0x95D0
   -> LoadLibraryW ran
   -> returned NULL
   -> error path E1, [this+0xCC] = 1
   -> initIfsLib FALSE
   CLASS: STATIC_REACHABLE, but the runtime outcome is DYNAMIC_UNKNOWN

EXPLANATION B  (new in EX-061)
   [this+0x60] != 0 at 0x95D0
   -> short-circuit, return TRUE
   -> InitInGameApp proceeds to consume [this+0x60] as an interface
      pointer (0x9A2B vtable call id 1)
   -> the failure, if any, is in a LATER stage (HostApp.ini read,
      HostApp launch, share-state, or the vtable target itself)
   CLASS: STATIC_REACHABLE

EXPLANATION C
   [this+0x60] == 0, LoadLibraryW succeeded, and one of
   E2 / E3 / E4 fired instead.
   CLASS: STATIC_REACHABLE
```

### I.3 Why this matters for the original question

EX-060's framing — "IIPS 在其内部 CFG 中最早在哪一个条件/状态转换上无法
继续向下" — is now refined:

```text
The EARLIEST state transition that decides whether IIPS continues
downward is not +0x96EF (LoadLibraryW) but +0x95D0 ([this+0x60]).

+0x95D0 is a pure OBJECT-STATE test:
    a previously-completed initialisation
  vs
    an uninitialised object

It is not a probe of any external resource.
```

The most useful way to state the static boundary is now:

```text
  iips.dll+0x95D0   [this+0x60] == 0 ?
      |
      +-- NO  -> the IFS2 dependency is NOT re-checked; IIPS continues
      |          into InitInGameApp's consumer region
      |
      +-- YES -> the IFS2 dependency IS checked, starting at
                 LoadLibraryW(+0x96E9) whose first failure branch is
                 +0x96EF
```

### I.4 Does this change the EX-060 earliest-failure claim?

```text
NO.  The EX-060 statement remains correct as stated:
     +0x96EF is the earliest STATIC FAILURE branch on the path
     InitInGameApp -> initIfsLib -> ifs2.dll.

EX-061 adds a PRECONDITION to that path:
     the path is only entered when [this+0x60] == 0.

EX-061 also adds a SIBLING hypothesis (Explanation B) for the observed
failure that does not involve LoadLibraryW at all.
```

### I.5 New lower bound on the static reasoning

```text
If (and only if) the observed crash came from the IFS2 bring-up region,
then the earliest failing transition must be one of:

   E1  +0x96EF  LoadLibraryW NULL            [this+0xCC] = 1
   E2  +0x977E  GetProcAddress Create NULL   [this+0xCC] = 2
   E3  +0x97A7  CreateIFSLibDll == 0         [this+0xCC] = 1
   E4  +0x97CE  GetProcAddress Destory NULL  [this+0xCC] = 3

and the status value observed would discriminate them.  The status value
is NOT available in any current telemetry (EX-057/058/059).

If the observed crash did NOT come from that region, then [this+0x60]
was already non-zero and the failure lies downstream in the consumer
region (0x9A2B..0xA6CB) or beyond iips.dll.
```

### I.6 Which explanation is consistent with the module-level evidence?

```text
EX-057 / EX-059 module evidence:
    iips.dll loads
    no IFS2.dll image event
    no IIPSHostApp.exe process
    iips.dll unloads
    WIN_IIPS_INIT_ERROR / 0x8189FEC

Consistency check:
  Explanation A (LoadLibraryW -> NULL):
      consistent -- ifs2.dll never maps, so no image event.
  Explanation B (short-circuit, [this+0x60] != 0):
      requires a PRIOR successful CreateIFSLibDll on this object, which
      would have mapped ifs2.dll.  Since ifs2.dll was never observed to
      map in the SAME run, Explanation B would require the map to be
      invisible to the image telemetry or to have happened in another
      process.  This is possible but not established.
  Explanation C (E2/E3/E4):
      E2 requires ifs2.dll to have mapped then unmapped (possible,
         image events can be missed at this granularity);
      E3 requires ifs2.dll resident with a CreateIFSLibDll that returns 0
         (no image event observed -> weaker);
      E4 requires ifs2.dll resident and CreateIFSLibDll non-zero
         (same objection as B).

Under the module-level evidence alone, Explanation A is the LEAST
CONTRADICTED.  This is a plausibility ranking, NOT a dynamic proof, and
it is NOT written as DYNAMIC_CONFIRMED.
```

---

## Core Question Answer

> 【为什么 InitInGameApp 到达 +0x95D0 时，`[this+0x60]` 会使控制流
>   进入或不进入 initIfsLib？】

```text
1. InitInGameApp does NOT itself test +0x95D0.  It calls
   CNIFS::initIfsLib at 0x99D2, and the test happens INSIDE initIfsLib
   at 0x95D0.

2. [this+0x60] is a CNIFS member field, 4 bytes at CNIFS+0x60.
   It has exactly TWO writers in the whole iips.dll image:

      W1  0x91CF  sub_90D0 (CNIFS ctor)    [this+0x60] := 0
      W2  0x97A9  sub_9570 (initIfsLib)    [this+0x60] := CreateIFSLibDll(...)

3. The constructor writes 0 UNCONDITIONALLY:
      xor ebx, ebx            (0x90FF)
      mov [ebp+0x60], ebx     (0x91CF)
   and no instruction between those two touches ebx.
   => the field's INITIAL value is exactly 0.

4. Therefore:
      - on the FIRST initIfsLib call for a freshly constructed object,
        [this+0x60] == 0, the 0x95D4 jne is NOT taken, and control
        FALLS INTO the ifs2.dll bring-up (LoadLibraryW at 0x96E9 etc.).
      - after a SUCCESSFUL initIfsLib, [this+0x60] == the non-NULL
        CreateIFSLibDll result, so any LATER initIfsLib call takes the
        0x95D4 jne, SHORT-CIRCUITS, and returns TRUE without touching
        ifs2.dll.

5. The branch is thus an IDEMPOTENCY gate:
      [this+0x60] == 0   =>  "not yet initialised"  =>  do the work
      [this+0x60] != 0   =>  "already initialised"  =>  return success

6. CONTROL-FLOW CONSEQUENCE (the direct answer):
      InitInGameApp reaches 0x95D0 with [this+0x60] == 0 on a
      first-use object  ->  ENTERS the ifs2.dll bring-up path.
      InitInGameApp reaches 0x95D0 with [this+0x60] != 0 on a
      re-used object    ->  does NOT enter it.

7. WHAT CANNOT BE DETERMINED STATICALLY:
      whether the object was freshly constructed or already initialised
      at the moment of the observed run.
      The constructor call site exists (0x12CF1) and the initial value
      is provably 0, but the RUNTIME ORDER of
          factory(0x12CF1)  vs  InitInGameApp(0x9860)
      is not recoverable from iips.dll alone, because
          - InitInGameApp has ZERO immediate callers, and
          - the factory wrapper sub_197F0 has ZERO immediate callers,
      i.e. both are entered through a vtable/export boundary whose
      dispatcher is STATIC_UNKNOWN from this module.

   FINAL:  INITIAL_VALUE_OF_this_60      = 0        STATIC_DIRECT (proven)
           ONLY_OTHER_WRITER             = initIfsLib W2  STATIC_DIRECT
           WHICH_EDGE_AT_0x95D0_IN_RUN   = UNKNOWN  (runtime object state)
```

---

## Final Classification

```text
EX061_IIPS_THIS60_DATAFLOW

A. CNIFS+0x60 WRITES
     count = 2
     W1  0x91CF  sub_90D0  CNIFS::ctor      source = ebx = 0    STATIC_DIRECT
     W2  0x97A9  sub_9570  initIfsLib       source = eax        STATIC_INDIRECT
                                             (eax = CreateIFSLibDll result)

B. CNIFS+0x60 READS
     R1  0x929F  sub_9240  ctor-teardown path (vtable slot +8)  STATIC_DIRECT
     R2  0x95D0  sub_9570  the decision compare                 STATIC_DIRECT
     R3  0x9A2B  sub_9860  interface ptr, vtable +0x2C, id 1    STATIC_DIRECT
     R4  0x9B51  sub_9860  interface ptr, vtable +0x2C, id 5    STATIC_DIRECT
     R5  0x9B66  sub_9860  interface ptr, vtable +0x2C, id 3    STATIC_DIRECT
     R6  0x9B7B  sub_9860  interface ptr, vtable +0x2C, id 4    STATIC_DIRECT

C. CNIFS+0x60 COMPARE / TEST / ADDRESS-TAKE
     C1  0x95D0  COMPARE      cmp [ebp+0x60], 0               STATIC_DIRECT
     C2  0x92C6  COMPARE      cmp [esi+0x60], ebx  (ebx=0)     STATIC_DIRECT
     C3  0x92C9  ADDRESS-TAKE lea edi, [esi+0x60]              STATIC_DIRECT
     C4  0x929F  READ+COMPARE mov ecx,[esi+0x60]; cmp ecx,ebx  STATIC_DIRECT
     test [...] on +0x60 : NONE

D. CONSTRUCTOR / INITIALIZER
     constructor  sub_90D0  0x90D0..0x9214  ret 4   this=[esp+0x24]
     initial      [this+0x60] = 0            at 0x91CF          STATIC_DIRECT
     factory      sub_12760  0x12760..0x13587
                   0x12CD3 push 0x1F0   (sizeof CNIFS = 496)
                   0x12CD8 operator new
                   0x12CF1 call sub_90D0
                   0x12D06 store CNIFS* at [parent+0x19C]
     wrapper      sub_197F0  0x197F0..0x19810   ret 4
                   no immediate callers        STATIC_UNKNOWN entry
     destructor   sub_9240  0x9240..0x937F  __thiscall
                   DestoryIFSLibDll(&[this+0x60]) then [this+0x60]=0
                   FreeLibrary([this+0x54]) then [this+0x54]=0

E. CreateIFSLibDll -> +0x60
     strict one-way assignment found
     0x977C GetProcAddress("CreateIFSLibDll") -> [this+0x58]
     0x97A5 call eax                          (indirect)
     0x97A9 mov [this+0x60], eax              STATIC_INDIRECT (callee),
                                              STATIC_DIRECT (assignment)
     assignment is unconditional on the reached path (executes even for 0)
     [this+0x60] is NOT the HMODULE and NOT a function pointer

F. +0x95D0 DECISION TREE
     [this+0x60] != 0  -> jne 0x9818 -> LeaveCriticalSection -> AL=1
                          (no LoadLibraryW, no resolver, no create)
     [this+0x60] == 0  -> fallthrough -> path build
                          -> LoadLibraryW 0x96E9
                          -> resolver 0x977C
                          -> CreateIFSLibDll 0x97A5 -> 0x97A9
                          -> resolver 0x97CC
                          -> AL=1 (ok) or AL=0 (E1..E4)
     branch reached  : STATIC_REACHABLE
     edge at runtime : STATIC_UNKNOWN

G. STATE MACHINE (explained)
     S0 unconstructed
     S1 constructed/uninitialised   [this+0x60] = 0
     S2 IFS initialised             [this+0x60] = Create result != 0
     S3 IFS init failed             [this+0xCC] in {1,2,3}
     S4 teardown                    [this+0x60] = 0, [this+0x54] = 0
     one object class, sizeof 0x1F0, 29 constructor fields

H. UNEXPLAINED
     H01..H15 (see Section H)
     core: whether the object was freshly constructed at 0x95D0 in the
           observed run            -> STATIC_UNKNOWN

I. IMPACT
     EX-060's +0x96EF remains the earliest STATIC failure branch on the
     ifs2 bring-up path.
     EX-061 adds that this path is guarded by +0x95D0, so the earliest
     DECISION is the object-state test at 0x95D0, and a second
     (non-LoadLibrary) failure explanation now exists (Explanation B).
     Which explanation holds in the observed -q run remains UNKNOWN.

NOT WRITTEN IN THIS ROUND
     no API hooking
     no debugger attach
     no ETW API tracing
     no parameter matrix
     no IIPS patch
     no bypass
     no fake success
     no DYNAMIC_CONFIRMED claim
```

## Verification Artifacts

```text
ex061_this60_table.csv       145 rows: every [reg+0x60] touch in .text
ex061_this60_scan.txt        base/index/scale breakdown
ex061_owner_map.json         site -> owning function
ex061_all_writes.txt         WRITE/READ/COMPARE/TEST table
ex061_ctor_dtor.txt          constructor and destructor member writes
ex061_ctor_site.txt          the 0x12CF1 construction site
ex061_callconv.txt           initIfsLib frame math and argument proof
ex061_ebp_shadow.txt         proof that 0x9B7B overwrites EBP with the field
ex061_offset_collision.txt   CNIFS profile vs other object types
ex061_identity_proof.txt     object-identity and lifecycle proof
ex061_final_verify.txt       the two-writer / initial-value-0 verification
ex061_chain.txt              full chain and state machine
```
