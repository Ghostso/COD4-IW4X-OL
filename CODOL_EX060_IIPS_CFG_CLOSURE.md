# EX-060_IIPS_CFG_CLOSURE

## Scope and Constraints Observed

This round is **static IIPS CFG closure only**.

Not performed:

```text
patch
bypass
fake return
iips.dll modification
CODOL core logic modification
any further -q / -qa parameter matrix expansion
dynamic API tracing
```

No process was started, attached to, suspended, or instrumented. All new
evidence below comes from read-only file parsing of the on-disk artifacts.

## Artifact Provenance

```text
iips.dll    tools/EX035_DIR/IIPS/iips.dll
            size     347704
            sha256   72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
            image    0x10000000 + 0x55000
            identical to "COD OL/IIPS/iips.dll" (same sha256)

EXE         tools/EX035_DIR/codoMP_client_shipRetail.exe
            size     7841344
            sha256   36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
            image    0x400000 + 0xE659000
            sections: .tp3 (60000020), .tp3 (40000040), .tp3 (C0000040),
                      .tp3 (C0000040), .tp3 (40000040), .tvm0 (60000020),
                      .tp3 (E0000020)
            entry     RVA 0xE5DC690
            no .reloc section
```

`iips.dll` exports only:

```text
0x1BC0  GetResourceManager
0x1C60  ReleaseResourceManager
0x1C60  ReleaseResourceManagerII
0x1C80  GetResourceManagerII
```

Global constants used throughout:

```text
iips.dll image base      0x10000000
iips.dll IAT LoadLibraryW   slot 0x10033010
iips.dll IAT GetProcAddress slot 0x10033014
```

---

## 1. CNIFS::InitInGameApp CFG

```text
entry    iips.dll + 0x9860   (VA 0x10009860)
extent   iips.dll + 0x9860 .. 0xA833
         last instruction: 0x1000A833  ret 0x38
         1057 instructions, 162 basic blocks
         all 162 BBs statically reachable from 0x9860
         exactly one `ret` (0xA833)
         no indirect tail jumps, no unresolved jmp targets
```

Calling convention: MSVC x86 `__thiscall`.

```text
ecx            = this (CNIFS object)
[esp+0x04]     = arg1  (checked at 0x98E6 as [esp+0x118] after frame)
[esp+0x08]     = arg2  (checked at 0x95DA as [esp+0xB8] after frame)
[esp+0x0C]     = arg3  (checked at 0x9649 as [esp+0xBC] after frame)
```

### Prologue / shared state

```text
0x9867  mov eax, fs:[0]             ; SEH frame
0x9895  mov fs:[0], eax
0x989B  mov ebp, ecx                ; this
0x989D  mov [esp+0x24], ebp
0x98A1  mov [esp+0xFC], 0           ; SEH state
0x98AC  lea ebx, [ebp+0x120]        ; critical section
0x98B7  call [0x10033028]           ; KERNEL32!EnterCriticalSection
0x98BD  lea esi, [ebp+0xD0]         ; CNIFS sub-object
0x98C3  push 1
0x98C5  mov byte [esp+0x100], 2     ; SEH state
```

Global/static state touched:

```text
0x10042020   security cookie (read twice: 0x9874, 0x9886)
0x10033028   IAT KERNEL32!EnterCriticalSection          (0x98B7)
0x1003302C   IAT KERNEL32!LeaveCriticalSection           (7 sites)
0x100330B4   IAT KERNEL32!GetPrivateProfileIntW          (0x9A8B)
0x10033138   IAT MSVCP80!~basic_string<wchar_t>          (10 sites)
0x1003313C   IAT MSVCP80!basic_string<wchar_t>::ctor     (3 sites)
0x1003314C   IAT MSVCP80!basic_string<char>::ctor        (2 sites)
0x10033194   IAT MSVCP80!basic_string<char> assign       (2 sites)
0x10033198   IAT MSVCP80!basic_string<char> assign       (5 sites)
0x1003319C   IAT MSVCP80!operator+<char>                 (1 site)
0x100331A8   IAT MSVCP80!operator+<char>                 (2 sites)
0x10033268   IAT MSVCP80!basic_string<char>::ctor copy   (6 sites)
0x1003326C   IAT MSVCP80!~basic_string<char>            (31 sites)
0x100332A4   IAT MSVCR80!_invalid_parameter_noinfo      (20 sites)
```

### Conditional branches

| BB | condition | taken | fallthrough |
|---|---|---|---|
| 0x9860 | prologue; `test al,al` after QoS helper | 0x98E6 | 0x98D6 |
| 0x98E6 | `cmp [esp+0x118],0` / `je` | 0x995B | 0x98F0 |
| 0x995B | `cmp [esp+0x11C],0x10` / `jae` | 0x9977 | 0x9970 |
| 0x9977 | `test eax,eax` / `je` | 0x99BA | 0x99A9 |
| 0x99BA | `test al,al` after initIfsLib / `jne` | 0x9A2B | 0x99DB |
| 0x9A2B | post-init error branch | - | - |
| 0x9A6D | `cmp [eax+0x18],8` / `jb` | 0x9A78 | 0x9A73 |
| 0x9ADB.. | further string / HostApp branches | - | - |

### Calls and returns

```text
0x98B7  EnterCriticalSection
0x98CD  sub_6D20          QoS init helper ("Failed to init qos (true)")
0x98DE  sub_4310          error message store
0x99D2  sub_9570          ==> CNIFS::initIfsLib  (see SECTION 2)
0x9A8B  GetPrivateProfileIntW  IIPSHostApp.ini / ResPool / ReservedSize / 0x40000000
0x9B06  sub_7DC0
0x9BC0  sub_CF10
0x9BDC  sub_D220
0x9A35  indirect call [edx] (vtable [ecx]+0x2C)  x4  (0x9A35,0x9B5B,0x9B70,0x9B88)
0x9E09  sub_8DB0
0xA005  sub_4310
0xA024  sub_6E40
0xA416  sub_6E40
0xA461  sub_4310
0xA548  sub_6E40
0xA59B  sub_4310
0xA689  sub_4310
0xA77E  sub_F6E0
0xA84F  sub_2BEF1         (__security_check_cookie)

single exit:  0xA833  ret 0x38
success exit: AL = 1  (0x9A2B region)
failure exit: AL = 0  (0x9A24)
```

### Error paths inside InitInGameApp

```text
0x98D6  "[CNIFS::InitInGameApp()][Failed to init qos (true)]"
        -> log only, NON-FATAL; control rejoins at 0x98E6
0x99DB  initIfsLib returned false -> full cleanup, returns AL=0 via 0xA833
```

The `0x98CD` QoS helper result is **not** a gate: both its taken and
fallthrough edges converge at 0x98E6.

---

## 2. CNIFS::initIfsLib CFG

```text
entry    iips.dll + 0x9570   (VA 0x10009570)
extent   iips.dll + 0x9570 .. 0x985D
         last instruction: 0x1000985D  ret 0x20
         176 instructions, 24 basic blocks
         all 24 BBs statically reachable from 0x9570
         exactly one `ret` (0x9839) -> single exit
```

Calling convention: MSVC x86 `__thiscall`.

```text
ecx            = this (CNIFS object)
[esp+0x04]     = arg  (pointer used at 0x99CA)
```

### Parameters / provenance

```text
0x95A5  mov ebp, [esp+0xA0]      ; this
0x95AC  lea ebx, [ebp+0x120]     ; critical section
0x95BD  push ebx
0x95C2  call EnterCriticalSection
0x95D0  cmp [ebp+0x60], 0        ; member: CreateIFSLibDll fn ptr / init flag
0x95DA  cmp [esp+0xB8], 0        ; caller argument
0x9649  cmp [esp+0xBC], 0x10     ; std::string capacity (wide, 16)
0x96DE  cmp [esp+0x6C], 8        ; std::string capacity (narrow, 8)
```

`this` member layout observed in this function:

```text
[this+0x50]  out-pointer for CreateIFSLibDll   (pushed at 0x97A4)
[this+0x54]  HMODULE of the loaded ifs dll     (written 0x96F1, read 0x97C3)
[this+0x58]  CreateIFSLibDll function pointer  (written 0x9780)
[this+0x5C]  DestoryIFSLibDll function pointer (written 0x97D0)
[this+0x60]  CreateIFSLibDll call result       (written 0x97A9)
             also the "already initialised" flag tested at 0x95D0
[this+0x64]  std::string error/message buffer  (arg to sub_4310)
[this+0xCC]  status code 1 / 2 / 3             (written 0x971C/0x9795/0x97E5)
[this+0x104] std::string path buffer           (written 0x96CF)
[this+0x120] critical section
```

### The LoadLibraryW path argument

The wide string constant is at RVA **0x34908**:

```text
bytes : 2f 00 69 00 66 00 73 00 32 00 2e 00 64 00 6c 00 6c 00 00 00
value : L"/ifs2.dll"
```

The narrow seed at RVA 0x34904 is `b'\\/ '` (separator characters), used to
normalise the IIPS module directory before the filename is appended.

Construction sequence:

```text
0x95E4  push 0x10034904        ; narrow separator seed
0x95ED  basic_string<char>::ctor
0x960B  call sub_94C0          ; trims trailing separators via
                               ;   find_last_not_of / erase / clear
0x9623  basic_string<char>::assign into [this+0x104]
0x96A1  push 0x10034908        ; L"/ifs2.dll"
0x96B0  operator+<wchar_t>     ; wide path = f([this+0x104]) + L"/ifs2.dll"
0x96CF  basic_string<char>::assign
0x96D5  mov eax, [esp+0x58]    ; wide buffer
0x96DE  cmp [esp+0x6C], 8      ; SSO check
0x96E8  push eax               ; wide path pointer
0x96E9  call [0x10033010]      ; KERNEL32!LoadLibraryW
```

So the static path contract is:

```text
LoadLibraryW( <iips module directory> + L"/ifs2.dll" )
```

which on this installation resolves to:

```text
tools/EX035_DIR/IIPS/ifs2.dll
```

Note: `IFS2.dll` **is present** on disk. This round makes no claim that it
is missing.

### Conditional branches

| BB | instruction | condition | taken | fallthrough |
|---|---|---|---|---|
| 0x9570 | `jne 0x9818` | `[ebp+0x60] != 0` | 0x9818 | 0x95DA |
| 0x95DA | `je 0x9649` | `[esp+0xB8] == 0` | 0x9649 | 0x95E4 |
| 0x9649 | `jae 0x9661` | wide capacity >= 0x10 | 0x9661 | 0x965A |
| 0x9661 | `je 0x96A1` | `[esp+0x14] == 0` | 0x96A1 | 0x9690 |
| 0x96A1 | `jae 0x96E8` | narrow capacity >= 8 | 0x96E8 | 0x96E4 |
| 0x96E8 | `jne 0x9770` | `LoadLibraryW != NULL` | 0x9770 | 0x96F6 |
| 0x96F6 | `jae 0x9704` | narrow capacity >= 8 | 0x9704 | 0x9700 |
| 0x9770 | `jne 0x97A1` | `GetProcAddress != NULL` | 0x97A1 | 0x9785 |
| 0x97A1 | `jne 0x97C3` | `CreateIFSLibDll != 0` | 0x97C3 | 0x97AE |
| 0x97C3 | `jne 0x97F4` | `GetProcAddress != NULL` | 0x97F4 | 0x97D5 |

The `0x9649`, `0x96A1`, `0x96F6` branches are std::string SSO / capacity
checks, not IIPS semantic gates.

### The `[this+0x60]` gate (critical)

```text
0x95D0  cmp dword ptr [ebp + 0x60], 0
0x95D4  jne 0x10009818          ; non-zero -> skip to cleanup+success
0x9818  push ebx
0x9819  call LeaveCriticalSection
0x9837  mov al, 1
0x9839  ... ret 0x20
```

This is the **only** early exit before LoadLibraryW. It is an
already-initialised / idempotency short-circuit: if the CNIFS object
already holds a `CreateIFSLibDll` result, `initIfsLib` returns success
without reloading the ifs dll.

The `0x95DA` gate (`[esp+0xB8]`) does **not** bypass LoadLibraryW; it only
skips the narrow-string seed construction and rejoins at 0x9649.

### Error paths (4 total, each writes a distinct status)

```text
[E1] +0x96F6..0x971C    LoadLibraryW == NULL
     log : "[CNIFS::initIfsLib()][Failed to open dllfile][error %d][path %s]"
           arg1 = [ebp+0xCC] (previous status), arg2 = wide path
     state: [ebp+0xCC] = 1
     then : jmp 0x9726 (cleanup) -> AL = 0

[E2] +0x9785..0x9795    GetProcAddress("CreateIFSLibDll") == NULL
     log : "[CNIFS::initIfsLib()][Failed to get function CreateIFSLibDll]"
     state: [ebp+0xCC] = 2
     then : jmp 0x9726 (cleanup) -> AL = 0

[E3] +0x97AE..0x971C    CreateIFSLibDll returned 0
     log : "[CNIFS::initIfsLib()][Failed to create ifs lib]"
     state: [ebp+0xCC] = 1   (re-uses the LoadLibrary status value)
     then : jmp 0x971C -> 0x9726 (cleanup) -> AL = 0

[E4] +0x97D5..0x97E5    GetProcAddress("DestoryIFSLibDll") == NULL
     log : "[CNIFS::initIfsLib()][Failed to get proc DestoryIFSLibDll]"
     state: [ebp+0xCC] = 3
     then : jmp 0x9726 (cleanup) -> AL = 0
```

Return-value production:

```text
0x9769  xor al, al     -> AL = 0   (all four error paths converge here)
0x9837  mov al, 1      -> AL = 1   (success path / 0x9818 short-circuit)
0x9839  ... ret 0x20
```

Shared cleanup at 0x9726 / 0x97F4 / 0x9818:

```text
0x9732  ~basic_string<wchar_t>
0x9744  ~basic_string<wchar_t>
0x974B  LeaveCriticalSection
0x9763  ~basic_string<char>
```

### Global/static state touched by initIfsLib

```text
0x10042020   security cookie           (0x9581, 0x9590)
0x10033010   IAT KERNEL32!LoadLibraryW (0x96E9)
0x10033014   IAT KERNEL32!GetProcAddress (0x9770)
0x10033028   IAT KERNEL32!EnterCriticalSection (0x95C2)
0x1003302C   IAT KERNEL32!LeaveCriticalSection (0x974B, 0x9819)
0x10033138   IAT MSVCP80!~basic_string<wchar_t> (0x9732,0x9744,0x9800,0x9812)
0x1003313C   IAT MSVCP80!basic_string<wchar_t>::ctor (0x967A)
0x1003314C   IAT MSVCP80!basic_string<char>::ctor    (0x95ED)
0x10033158   IAT MSVCP80!operator+<wchar_t>          (0x96B0)
0x10033198   IAT MSVCP80!basic_string<char>::assign  (0x9623,0x96CF)
0x1003326C   IAT MSVCP80!~basic_string<char>  (0x9633,0x9643,0x9763,0x9831)
```

---

## 3. +0x96E9 Reachable Analysis

**Question:** is `iips.dll+0x96E9` reachable from the normal control flow of
`iips.dll+0x9860`?

**Answer: STATIC_REACHABLE (conditional on `[this+0x60] == 0`).**

### Evidence chain

```text
0x9860  InitInGameApp entry                                  [BB 0x9860]
  0x98CD  call sub_6D20        ; QoS helper; both edges join at 0x98E6
  0x98E6  cmp [esp+0x118],0
          je 0x995B                                    <-- gate 1
  0x995B  cmp [esp+0x11C],0x10
          jae 0x9977                                   <-- gate 2 (SSO only)
  0x9977  test eax,eax
          je 0x99BA                                    <-- gate 3 (ptr check)
  0x99BA  sub esp,0x1C
          lea edx,[esp+0x120]
          mov ecx,esp
          push edx
          call [0x10033268]                            ; string copy ctor
  0x99D1  push ebp                                     ; this
  0x99D2  call 0x10009570                              ; <== initIfsLib
  0x99D7  test al,al
  0x99D9  jne 0x9A2B
```

Shortest BB path inside InitInGameApp:

```text
0x9860 -> 0x98E6 -> 0x995B -> 0x9977 -> 0x99BA   (call 0x9570)
```

Inside initIfsLib:

```text
0x9570  entry
  0x95D0  cmp [ebp+0x60],0
          jne 0x9818            <-- ONLY pre-LoadLibrary early exit
  0x95DA  cmp [esp+0xB8],0
          je 0x9649             <-- does NOT skip LoadLibraryW
  0x96A1  ...
  0x96E8  push eax
  0x96E9  call [0x10033010]     ; <== LoadLibraryW
```

Shortest BB path inside initIfsLib:

```text
0x9570 -> 0x95DA -> 0x96A1 -> 0x96E8   (reaches 0x96E9)
```

### Classification table

| address | classification | note |
|---|---|---|
| `+0x9860` | `STATIC_REACHABLE` | function entry |
| `+0x98CD` | `STATIC_REACHABLE` | QoS helper call; not a gate |
| `+0x99D2` | `STATIC_REACHABLE` | call to `+0x9570` |
| `+0x9570` | `STATIC_REACHABLE` | callee |
| `+0x95D0` | `STATIC_REACHABLE` | first decision gate |
| `+0x96E9` | **`STATIC_REACHABLE`** | conditional on `[this+0x60] == 0` |

There is **no** static path from `+0x9860` that reaches `+0x96E9`
unconditionally. The single necessary precondition is:

```text
CNIFS::[this+0x60] == 0   at initIfsLib entry
```

If `[this+0x60] != 0`, initIfsLib short-circuits at `0x95D4` to `0x9818`
and returns `AL=1` without ever calling `LoadLibraryW`.

`+0x96E9` is therefore:

```text
STATIC_REACHABLE       (not STATIC_NOT_REACHABLE)
STATIC_REACHABLE_CONDITIONAL = TRUE
STATIC_REACHABLE_UNCONDITIONAL = FALSE
```

---

## 4. +0x977C / +0x97A5 / +0x97CC Analysis

### Gate after LoadLibraryW

```text
0x96E8  push eax               ; eax = wide path pointer
0x96E9  call [0x10033010]      ; LoadLibraryW
0x96EF  test eax, eax
0x96F1  mov [ebp+0x54], eax    ; HMODULE stored unconditionally
0x96F4  jne 0x9770             ; non-NULL -> resolver
```

### +0x977C - GetProcAddress("CreateIFSLibDll")

```text
0x9770  mov esi, [0x10033014]  ; IAT KERNEL32!GetProcAddress
0x9776  push 0x10034964        ; "CreateIFSLibDll"
0x977B  push eax               ; HMODULE
0x977C  call esi               ; <== GetProcAddress
0x977E  test eax, eax
0x9780  mov [ebp+0x58], eax    ; stored unconditionally
0x9783  jne 0x97A1             ; non-NULL -> indirect call
```

| item | value |
|---|---|
| callsite | `+0x977C` |
| call kind | `STATIC-INDIRECT` (`call esi`) |
| `esi` resolution | `STATIC-DIRECT`: `mov esi,[0x10033014]` = `KERNEL32!GetProcAddress` |
| arg1 | HMODULE from `LoadLibraryW` (`[ebp+0x54]`) |
| arg2 | RVA 0x34964 = `"CreateIFSLibDll"` |
| return use | stored to `[ebp+0x58]`, tested immediately |
| null branch | `+0x9785` -> `"Failed to get function CreateIFSLibDll"`, `[ebp+0xCC]=2` |

The `esi` binding is unambiguous: the IAT slot `0x10033014` resolves to
`KERNEL32.dll!GetProcAddress`, and no other write to `esi` occurs between
`0x9770` and `0x977C`.

### +0x97A5 - indirect CreateIFSLibDll

```text
0x97A1  lea ecx, [ebp+0x50]
0x97A4  push ecx               ; out-pointer argument
0x97A5  call eax               ; <== indirect call through resolved pointer
0x97A7  test eax, eax
0x97A9  mov [ebp+0x60], eax    ; result stored unconditionally
0x97AC  jne 0x97C3             ; non-zero -> destroy resolver
```

| item | value |
|---|---|
| callsite | `+0x97A5` |
| call kind | `STATIC-INDIRECT (register EAX)` |
| EAX provenance | `STATIC-DIRECT` chain: `eax = [ebp+0x58]` <- `GetProcAddress("CreateIFSLibDll")` at `+0x977C` |
| arg1 | `lea ecx,[ebp+0x50]` pushed -> out-parameter into `[this+0x50]` |
| return use | stored to `[ebp+0x60]`, tested immediately |
| zero branch | `+0x97AE` -> `"Failed to create ifs lib"`, `[ebp+0xCC]=1` |

This is a **two-step indirect**: the target address is not statically known
(it comes from a runtime export lookup), but its **data source is
statically resolved** to the `CreateIFSLibDll` export of the module
returned by `LoadLibraryW`.

### +0x97CC - GetProcAddress("DestoryIFSLibDll")

```text
0x97C3  mov edx, [ebp+0x54]    ; HMODULE
0x97C6  push 0x100349E4        ; "DestoryIFSLibDll"  (original spelling)
0x97CB  push edx
0x97CC  call esi               ; <== GetProcAddress (esi still the resolver)
0x97CE  test eax, eax
0x97D0  mov [ebp+0x5C], eax    ; stored unconditionally
0x97D3  jne 0x97F4             ; non-NULL -> success path
```

| item | value |
|---|---|
| callsite | `+0x97CC` |
| call kind | `STATIC-INDIRECT` (`call esi`), `esi` = `KERNEL32!GetProcAddress` |
| arg1 | HMODULE from `[ebp+0x54]` |
| arg2 | RVA 0x349E4 = `"DestoryIFSLibDll"` (sic; misspelling is in the binary) |
| return use | stored to `[ebp+0x5C]`, tested immediately |
| null branch | `+0x97D5` -> `"Failed to get proc DestoryIFSLibDll"`, `[ebp+0xCC]=3` |
| success exit | `+0x97F4` -> cleanup -> `+0x9818` -> `AL=1` |

### Success contract

```text
LoadLibraryW != NULL
  -> GetProcAddress("CreateIFSLibDll") != NULL
       -> CreateIFSLibDll(out [this+0x50]) != 0
            -> GetProcAddress("DestoryIFSLibDll") != NULL
                 -> AL = 1   (initIfsLib success)
```

Every stage is a hard gate; a NULL/zero result at any stage jumps to
cleanup and returns `AL = 0`.

All of the above are STATIC classifications. None asserts that the call
actually executed at runtime.

---

## 5. 8189FEC Full Reference Table

`0x8189FEC` = `135831532` decimal, `0b1000000110001001111111101100`.

### 5.1 Does the address resolve to a module?

```text
0x8189FEC lies inside the EXE image:  [0x00400000, 0x0EA59000)  -> YES
  RVA     = 0x7D89FEC
  section = .tp3 index 3 (VA 0x00A16000, vsize 0x0DBB1CC0)
  raw-backed? NO
      that section has rawsize 0x00062000 (raw 0x00702000..0x00764000)
      RVA 0x7D89FEC requires raw offset 0x7A75FEC -> far outside
```

Not inside any DLL/EXE image we scanned:

```text
iips.dll                          [0x10000000, 0x10055000)   NO
IIPSHost.dll                      [0x10000000, 0x10093000)   NO
IIPSVFS.dll                       [0x10000000, 0x10037000)   NO
IIPSCheck.dll                     [0x10000000, 0x10015000)   NO
IIPSHostApp.exe                   [0x00400000, 0x00447000)   NO
TenProxy.dll                      [0x10000000, 0x10029000)   NO
GbSpy.dll                         [0x10000000, 0x100A6000)   NO
codoMP_client_shipRetailBase.dll  [0x10000000, 0x13991000)   NO
BugTrace.dll                      [0x10000000, 0x1033C000)   NO
TerSafe.dll                       [0x10000000, 0x107EC000)   NO
TenRpcs.dll                       [0x10000000, 0x11143000)   NO
```

`0x8189FEC` is a virtual address inside the packed CODOL EXE image, in a
section region that is not present in the raw file.

### 5.2 Literal / operand search

Encodings searched: `le32`, `be32`, ASCII `8189FEC`, ASCII `8189fec`,
ASCII `0x8189FEC`, `push imm32` pattern `68 EC 9F 18 08`, `mov eax,imm32`
pattern `B8 EC 9F 18 08`.

| module | raw occurrences |
|---|---|
| codoMP_client_shipRetail.exe | 0 |
| codoMP_client_shipRetailBase.dll | 0 |
| iips.dll | 0 |
| IIPSHost.dll | 0 |
| IIPSVFS.dll | 0 |
| IIPSCheck.dll | 0 |
| IIPSHostApp.exe | 0 |
| IIPSStats.dll | 0 |
| IIPSRepair.dll | 0 |
| IIPSLaunchRestore.dll | 0 |
| iips_policymsg.dll | 0 |
| TenProxy.dll | 0 |
| GbSpy.dll | 0 |
| BugTrace.dll | 0 |
| TerSafe.dll | 0 |
| TenRpcs.dll | 0 |

The EXE has **no `.reloc` section**, so there is no relocation-table entry
for this address either.

### 5.3 Full reference table

Because the raw literal count is zero everywhere, there is no instruction
to which a READ / WRITE / COMPARE / ADDRESS_TAKEN / CALL_ARGUMENT /
ERROR_UI_ARGUMENT classification can be assigned by absolute addressing.

| RVA | surrounding BB | instruction | predecessor | successor | function | in current IIPS CFG | class |
|---|---|---|---|---|---|---|---|
| (none) | - | - | - | - | - | - | no absolute-addressed reference exists in any scanned module |

Requested specific patterns:

| pattern | count |
|---|---|
| `mov [8189FEC], reg` | 0 |
| `mov reg, [8189FEC]` | 0 |
| `cmp reg, [8189FEC]` | 0 |
| `test [8189FEC], ...` | 0 |
| `push 8189FEC` | 0 |
| `lea ..., [8189FEC]` | 0 |

### 5.4 Why the value is still meaningful

`0x8189FEC` is not a data object; it is a **runtime-computed value** that is
*printed as an address-like number*. The EXE contains a dedicated formatter
string:

```text
RVA 0x9C9400   "0x%x"      (VA 0xDC9400)
```

Sibling strings that ARE pushed natively (inside packed `.tp3`):

```text
VA 0xDC93BC  WIN_IIPS_PREDOWNLOAD_ERROR   push at VA 0x0058F103
VA 0xDC93D8  WIN_IIPS_INIT_FAILED         push at VA 0x0058F3CC
VA 0xDC9408  WIN_IIPS_DLL_ERROR           push at VA 0x0058F35D
VA 0xDC9400  "0x%x"                       push at VA 0x0058F281
```

Those push sites sit inside obfuscated `.tp3` code whose surrounding
disassembly stream is not linearly valid x86. The siblings are produced by
native/packed code, but `0x8189FEC` itself is never stored or compared
anywhere; its only appearance is a numeric print.

### 5.5 Task 3 verdict

```text
8189FEC_STATIC_REFERENCE_COUNT = 0
8189FEC_ABSOLUTE_WRITER        = NONE
8189FEC_ABSOLUTE_READER        = NONE
8189FEC_ABSOLUTE_COMPARE       = NONE
8189FEC_ADDRESS_TAKEN          = NONE
8189FEC_CALL_ARGUMENT          = NONE
8189FEC_ERROR_UI_ARGUMENT      = UNKNOWN
8189FEC_CLASS                  = STATIC_UNKNOWN
                                 (runtime-computed / packed-VM-generated,
                                  emitted through the EXE "0x%x" formatter)
```

---

## 6. WIN_IIPS_INIT_ERROR Reference Table

### 6.1 Location

```text
file      codoMP_client_shipRetail.exe
raw       0x006B53A8
RVA       0x009C93A8
VA        0x00DC93A8
section   .tp3
```

It exists in **no** other module. `iips.dll` does not contain the string
`WIN_IIPS_INIT_ERROR` at all.

### 6.2 Reference table

| string | VA | pointer (le32) refs | push imm32 refs |
|---|---|---|---|
| `WIN_IIPS_INIT_ERROR` | `0xDC93A8` | **0** | **0** |
| `WIN_IIPS_PREDOWNLOAD_ERROR` | `0xDC93BC` | 1 (`0x0058F104`) | 1 (`0x0058F103`) |
| `WIN_IIPS_INIT_FAILED` | `0xDC93D8` | 1 (`0x0058F3CD`) | 1 (`0x0058F3CC`) |
| `WIN_IIPS_DLL_ERROR` | `0xDC9408` | 1 (`0x0058F35E`) | 1 (`0x0058F35D`) |
| `IIPS\iips.dll` | `0xDC93F0` | **0** | **0** |
| `0x%x` | `0xDC9400` | 1 (`0x0058F282`) | 1 (`0x0058F281`) |

`WIN_IIPS_INIT_ERROR` and `IIPS\iips.dll` are the **only two** members of
this error cluster with zero references. Every other member is referenced
exactly once, by a `push imm32` inside packed `.tp3` code.

### 6.3 The MessageBox search

```text
iips.dll imports USER32!MessageBoxW at IAT 0x10033418.
No statically recovered .text callsite in iips.dll pushes
WIN_IIPS_INIT_ERROR (the string is not even present in iips.dll).
In the EXE, the only MessageBox-family resolution is inside packed code.
```

No `MessageBoxW` (or any `MessageBox*`) call site referencing the
`WIN_IIPS_*` cluster was recovered.

### 6.4 String cluster layout

```text
raw 0x6B5360  VA 0xDC9360  "IIPS: %d:%d:%s-%u:%s:%s:%lld:%lld:%d"
raw 0x6B5380  VA 0xDC9380  "IIPS: %d:%d:%s-%u:xx:xx:0:0:0"
raw 0x6B53A0  VA 0xDC93A0  "\x15" "1140"
raw 0x6B53A8  VA 0xDC93A8  "WIN_IIPS_INIT_ERROR"          <- 0 refs
raw 0x6B53BC  VA 0xDC93BC  "WIN_IIPS_PREDOWNLOAD_ERROR"   <- 1 ref
raw 0x6B53D8  VA 0xDC93D8  "WIN_IIPS_INIT_FAILED"         <- 1 ref
raw 0x6B53F0  VA 0xDC93F0  "IIPS\iips.dll"                <- 0 refs
raw 0x6B5400  VA 0xDC9400  "0x%x"                         <- 1 ref
raw 0x6B5408  VA 0xDC9408  "WIN_IIPS_DLL_ERROR"           <- 1 ref
raw 0x6B541C  VA 0xDC941C  "This program requires Windows NT!"
raw 0x6B5440  VA 0xDC9440  "Environment List Box"
```

`"0x%x"` is the formatter that produces `0x8189FEC`.

### 6.5 Task 6 verdict

```text
WIN_IIPS_INIT_ERROR_LOCATION        = EXE .tp3 VA 0xDC93A8 only
WIN_IIPS_INIT_ERROR_DIRECT_REFS     = 0
WIN_IIPS_INIT_ERROR_MESSAGEBOX_SITE = NONE_RECOVERED
WIN_IIPS_INIT_ERROR_CONSUMER        = STATIC_UNKNOWN
                                      (packed/VM code; accessed by index or
                                       by a computation, not by address)
```

---

## 7. Error Producer -> Transformer -> Consumer

### 7.1 The IIPS error-code vocabulary is now known

`IIPS/IIPSClient.ini` contains the complete `[ErrMsg]` index table. This is
the semantic key to the `IIPSERR_*` strings inside `iips.dll`:

| idx | IIPSClient.ini text | iips.dll `IIPSERR_*` label |
|---:|---|---|
| 0 | No Error | `IIPSERR_SUCCESS` |
| 1 | IIPS 获取模块路径出错 | `IIPSERR_GETMODULEPATH` |
| 2 | IIPS 设置全局名称权限出错 | `IIPSERR_PRIVILEGE_SE_CREATE_GLOBAL_NAME` |
| 3 | IIPS 初始化窗口消息出错 | `IIPSERR_WINMSG_INIT` |
| 4 | IIPS 获取主程序路径出错 | `IIPSERR_GETMAINMODULEPATH` |
| 5 | IFS 初始化出错 | `IIPSERR_IFS_INIT` |
| 6 | IIPS 初始化缓存出错 | `IIPSERR_CACHE_INIT` |
| 7 | IIPS 初始化代理进程出错 | `IIPSERR_IIPSHOST_INIT` |
| 8 | IIPS 初始化管道出错 | `IIPSERR_PIPE_INIT` |
| 9 | IIPS 创建共享内存出错 | `IIPSERR_SHARESTATE_INIT` |
| 10 | IIPS 加载统计文件出错 | `IIPSERR_RESOURCEUSAGERECORDER_LOAD` |
| 12 | IIPS 保存统计文件出错 | `IIPSERR_RESOURCEUSAGERECORDER_SAVE` |
| 13 | IIPS 反初始化代理进程失败 | `IIPSERR_IIPSHOST_INIT` / `IIPSERR_PIPE_CLOSE` |
| 14 | IIPS 反初始化窗口消息出错 | `IIPSERR_WINMSG_CLOSE` |
| 15 | 缓存不可用 | `IIPSERR_CACHE_NULL` |
| 16 | 参数出错 | `IIPSERR_PARAM` |
| 17 | 标准化路径出错 | (none recovered) |
| 18 | 参数不应为目录 | `IIPSERR_INPUT_FILE` |
| 19 | 没有找到文件 | `IIPSERR_NOT_FOUND` |
| 20 | IFS 打开文件出错 | `IIPSERR_IFS_OPEN_FAIL` |
| 21 | IFS 查找文件大小出错 | `IIPSERR_IFS_GETFILESIZE_FAIL` |
| 22 | 文件已关闭 | `IIPSERR_CLOSED` |
| 23 | 读取的大小出错 | `IIPSERR_READSIZE` |
| 24 | 文件大小为0 | `IIPSERR_FILESIZE_NULL` |
| 25 | 取文件属性时,参数出错 | `IIPSERR_PARAM` |
| 26 | 同步的IFS文件,非预下载 | `IIPSSTATE_NOT_DOWNLOADED` |
| 27 | 同步ID查找失败 | `IIPSERR_NOT_FOUND_SYNCID` |
| 28 | 发送消息出错 | `IIPSERR_SENDMSG` |
| 29 | 解压时,删除文件出错 | `IIPSERR_DELETE` |
| 30 | 文件已经存在 | `IIPSERR_FILEEXIST` |
| 31 | 创建目录出错 | `IIPSERR_CREATEPATH` |
| 32 | 解压文件出错 | `IIPSERR_EXTRACT` |
| 33 | 参数不应为文件 | `IIPSERR_INPUT_DIR` |
| 34 | 查找目录出错 | `IIPSERR_GETCHILD` |
| 35 | 查找已关闭 | `IIPSERR_FIND_CLOSED` |
| 36 | 查找目录完成 | `IIPSERR_SUCCESS` |
| 37 | 文件未下载完成 | `IIPSSTATE_NOT_DOWNLOADED` |
| 38 | 初始化失败, 正在修复中 | `IIPSSTATE_START_REPAIR_IFSFILE` |
| 39 | 初始化失败, 打开Host进程的共享内存出错 | `IIPSERR_OPEN_HOSTSHAREINFO` |
| 40 | FileList出错导致的IFS加载失败 | `IIPSERR_FILELIST_ERROR` |
| **41** | **IFS DLL加载失败, DLL不存在或者依赖有误** | **`IIPSERR_IFS_LOAD_DLL_ERROR`** |
| **42** | **IFS DLL加载后没找到需要的导出函数** | **`IIPSERR_IFS_DLL_CANT_FIND_FUNCTION`** |
| 43 | IFS IFSReadFile读取文件失败 | `IIPSERR_IFS_READ_ERROR` |
| 44 | IFS IFSReadFile读取文件内容时校验出错 | `IIPSERR_IFS_DATA_VERIFY_ERROR` |
| 45 | IIPS内部参数错误,与上层无关 | `IIPSERR_INTERNAL_HANDLE_ERROR` |
| 46 | IIPS未初始化完成 | `IIPSERR_ERROR_INIT` |
| 47 | 设置游戏客户端上报内容时index越界 | `IIPSERR_PARAM` |

Index **41** and **42** correspond exactly to the two error paths in
`initIfsLib`:

```text
index 41  "IFS DLL load failed"       <-> LoadLibraryW == NULL    (+0x96F6)
index 42  "IFS DLL export not found"  <-> GetProcAddress == NULL  (+0x9785 / +0x97D5)
index  5  "IFS init error"            <-> the aggregate IFS init state
index 40  "FileList error -> IFS load failure"
```

The presence of index 41/42 in the product's own error table confirms that
the `CNIFS::initIfsLib` branches we recovered are the intended, documented
failure modes of this product.

### 7.2 The IIPSERR_* strings are not code-referenced

```text
distinct IIPSERR_* strings in iips.dll : 44
pointer (le32) references to them       : 0
push-imm32 references to them           : 0
pointer table in .rdata                 : NONE
```

The `IIPSERR_*` names are not passed as string pointers. They are symbolic
labels for an enum index, resolved through the ini text table (or a
localisation/ID mechanism). They name a status state; they are not the
dataflow value that reaches the fatal path.

### 7.3 Chain

```text
ERROR PRODUCER
  iips.dll  CNIFS::initIfsLib  (+0x9570)
    +0x96E9  LoadLibraryW( <iipsdir>/ifs2.dll )
    +0x96EF  test eax,eax
    +0x96F1  mov [this+0x54], eax          ; HMODULE
    +0x96F4  jne 0x9770
    +0x96F6  [LoadLibraryW NULL branch]
    +0x971C  mov [this+0xCC], 1            ; <== STATUS = 1
    (index-41 state "IFS DLL load failed")

  iips.dll  CNIFS::initIfsLib  (+0x9570)
    +0x977C  GetProcAddress(hMod, "CreateIFSLibDll")
    +0x9780  mov [this+0x58], eax
    +0x9785  [NULL branch]
    +0x9795  mov [this+0xCC], 2            ; <== STATUS = 2
    (index-42 state "IFS DLL export not found")

  iips.dll  CNIFS::initIfsLib  (+0x9570)
    +0x97A5  call CreateIFSLibDll
    +0x97A9  mov [this+0x60], eax
    +0x97AE  [EAX == 0 branch]
    +0x971C  mov [this+0xCC], 1            ; <== STATUS = 1

  iips.dll  CNIFS::initIfsLib  (+0x9570)
    +0x97CC  GetProcAddress(hMod, "DestoryIFSLibDll")
    +0x97D0  mov [this+0x5C], eax
    +0x97E5  mov [this+0xCC], 3            ; <== STATUS = 3

  ALL FOUR converge at +0x9769  xor al,al  -> AL = 0
```

```text
ERROR TRANSFORMER
  iips.dll  CNIFS::initIfsLib  returns  AL = 0        (+0x9839 ret 0x20)
     |
     v
  iips.dll  CNIFS::InitInGameApp  (+0x9860)
    +0x99D2  call 0x10009570
    +0x99D7  test al,al
    +0x99D9  jne 0x9A2B
    +0x99DB  [failure path: full CFG cleanup]
    +0x9A24  xor al, al
    +0x9A26  jmp 0xA833  -> ret 0x38   AL = 0

  The boolean AL=0 is the ONLY value that crosses the CNIFS boundary.
  The numeric status [this+0xCC] is retained inside the object and is
  echoed into the DIAGNOSTIC LOG at +0x9704/+0x9714 via sub_4310
  (the "error %d" argument of the "Failed to open dllfile" message).
     -> that is a LOGGING transformer, not the fatal-state transformer.

  Beyond iips.dll the surviving value is either
    - the object member [this+0xCC], or
    - the CNIFS object pointer,
  crossing back to the EXE through the vtable / export boundary.
  The exact marshalling is STATIC_UNKNOWN: iips.dll contains no absolute
  reference into the EXE image (verified: 0 refs into [0x400000,0xEA59000)),
  so the hand-off is by pointer/return convention only, and the EXE-side
  consumer lives in the packed .tp3 / .tvm0 code.

ERROR CONSUMER
  codoMP_client_shipRetail.exe  packed .tp3 error emitter
    VA 0x0058F103  push 0xDC93BC  WIN_IIPS_PREDOWNLOAD_ERROR
    VA 0x0058F281  push 0xDC9400  "0x%x"
    VA 0x0058F35D  push 0xDC9408  WIN_IIPS_DLL_ERROR
    VA 0x0058F3CC  push 0xDC93D8  WIN_IIPS_INIT_FAILED
    (WIN_IIPS_INIT_ERROR at 0xDC93A8 has NO push site: 0 refs)
```

### 7.4 Classification

```text
ERROR PRODUCER    = iips.dll CNIFS::initIfsLib (+0x9570)
                    four distinct producers, all write [this+0xCC]
ERROR TRANSFORMER = iips.dll CNIFS::initIfsLib   AL = 0
                    iips.dll CNIFS::InitInGameApp AL = 0
                    sub_4310 diagnostic log echo ([this+0xCC] -> log text)
ERROR CONSUMER    = codoMP_client_shipRetail.exe packed .tp3 emitter
                    (WIN_IIPS_DLL_ERROR / WIN_IIPS_INIT_FAILED /
                     WIN_IIPS_PREDOWNLOAD_ERROR / "0x%x")
                    WIN_IIPS_INIT_ERROR has no recovered consumer
```

---

## 8. Current Earliest Static Failure Branch

"Earliest" is evaluated along the static CFG path
`0x9860 -> 0x99D2 -> 0x9570 -> 0x96E9`, in execution order.

| order | site | condition | branch target | class |
|---:|---|---|---|---|
| 1 | `0x95D0` | `[this+0x60] != 0` | `0x9818` (AL=1) | `STATIC_REACHABLE` init short-circuit, not a failure |
| 2 | `0x96EF` | `LoadLibraryW == NULL` | `0x96F6` | `STATIC_REACHABLE` - first failure branch on this path |
| 3 | `0x977E` | `GetProcAddress("CreateIFSLibDll") == NULL` | `0x9785` | `STATIC_REACHABLE` |
| 4 | `0x97A7` | `CreateIFSLibDll() == 0` | `0x97AE` | `STATIC_REACHABLE` |
| 5 | `0x97CE` | `GetProcAddress("DestoryIFSLibDll") == NULL` | `0x97D5` | `STATIC_REACHABLE` |

### Verdict

```text
EARLIEST_STATIC_FAILURE_BRANCH = iips.dll+0x96EF
  condition : LoadLibraryW(.../ifs2.dll) returns NULL
  error     : +0x96F6 -> +0x9704
              "[CNIFS::initIfsLib()][Failed to open dllfile][error %d][path %s]"
              error = [this+0xCC], path = the constructed wide path
  status    : [this+0xCC] = 1
              (maps to the IIPS index-41 family, "IFS DLL load failed")
  return    : AL = 0 -> InitInGameApp failure path -> AL = 0
```

This is the first place on the statically reachable
`InitInGameApp -> initIfsLib` path where the IIPS CFG can fail to proceed
downward, treating `0x95D0` as an intentional "already initialised" exit
rather than a failure.

Caveat: this is the earliest branch that *can* produce the failure. It is
**not** established that this branch was taken in any observed run.

### The earlier decision point that is not a failure

```text
iips.dll+0x95D0   cmp dword ptr [ebp+0x60], 0
                  jne 0x10009818
```

If `[this+0x60] != 0` when initIfsLib is entered, the function returns
success without calling LoadLibraryW. In that case the whole `+0x96E9`
chain is skipped, the caller sees `AL=1`, and InitInGameApp continues past
`0x9A2B` into the `GetPrivateProfileIntW` / HostApp / share-state region.

```text
CLASSIFICATION
  +0x95D0 gate evaluation              : STATIC_UNKNOWN (runtime object state)
  +0x95D4 taken edge                   : STATIC_REACHABLE (success short-circuit)
  +0x96EF LoadLibraryW NULL branch     : STATIC_REACHABLE
  actual first failure in observed -q  : UNKNOWN (no API telemetry)
```

### Why the earliest point cannot be pushed further down statically

Any failure *after* `initIfsLib` succeeds would have to come from the later
region of `InitInGameApp`:

```text
+0x9A8B  GetPrivateProfileIntW  (IIPSHostApp.ini / ResPool / ReservedSize)
+0x9A35  vtable call [ecx]+0x2C  (post-init state push)
+0x9B5B / +0x9B70 / +0x9B88      (further vtable state pushes)
+0xA330 / +0xA348 / +0xA3CF / +0xA4E1 / +0xA61B / +0xA635 / +0xA643 /
+0xA69A / +0xA6A7 / +0xA6CB / +0xA6F4   (indirect calls, HostApp region)
```

The HostApp / share-state / resource-manager region of `iips.dll`
(`ShellExecuteExW` at `+0x15CD1`, `OpenFileMappingA` at `+0x1194E`,
`CreateMutexA` at `+0x1197B`) is **not** part of the recovered
`InitInGameApp` CFG. It is reached through the vtable/indirect calls, so its
position relative to `initIfsLib` in execution order is `STATIC_UNKNOWN`.

Therefore the static analysis can bound the earliest failure branch to
`+0x96EF`, but it cannot prove that no earlier internal state transition
(inside the QoS helper `sub_6D20`, or inside the `0x95D0` object state)
already blocked progress.

---

## 9. Current Dynamic Boundary

Unchanged from EX-057/058/059 and explicitly **not** extended this round:

```text
dynamic API telemetry     : NOT AVAILABLE
LoadLibraryW return       : UNKNOWN
GetLastError              : UNKNOWN
GetProcAddress return     : UNKNOWN
CreateIFSLibDll EAX       : UNKNOWN
debugger attach           : OBSERVER_DIVERGENCE (EX-058 reproduced)
ETW user-mode provider    : INSUFFICIENT
```

Normal `-q` module-level facts (EX-057 / EX-059, still the strongest
dynamic evidence available):

```text
TenProxy.dll / GbSpy.dll
  -> iips.dll image load
  -> no observed IFS2.dll image load
  -> no observed IIPSHostApp.exe image/process
  -> iips.dll cleanup/unload
  -> WIN_IIPS_INIT_ERROR / 8189FEC
```

Two new dynamic-adjacent facts produced by this round's static work:

```text
The observed error token is printed by the EXE formatter "0x%x"
  (EXE VA 0xDC9400), which is natively pushed at EXE VA 0x58F281.

0x8189FEC is a VA-shaped value inside the EXE image that no module
  stores, reads, compares, or takes the address of.
  => it is produced by computation, not by a constant.
```

The dynamic boundary therefore remains:

```text
iips.dll module load
  -> IIPS internal / packed status hand-off   <-- UNKNOWN
  -> WIN_IIPS_INIT_ERROR / 0x8189FEC
```

No claim is made that `LoadLibraryW`, `GetProcAddress`, or
`CreateIFSLibDll` executed or returned anything in any run.

### Notable exclusion

The absence of an observed `IFS2.dll` image load is **not** evidence that
`LoadLibraryW` was not called, and it is **not** evidence that `ifs2.dll`
is missing:

```text
tools/EX035_DIR/IIPS/ifs2.dll   exists on disk
static contract                 LoadLibraryW(<iipsdir>/L"/ifs2.dll")
```

The static prerequisite exists; only the runtime outcome is unknown.

---

## 10. UNKNOWN List

```text
U01  Runtime value of CNIFS member [this+0x60] at initIfsLib entry
U02  Whether iips.dll+0x96E9 LoadLibraryW was reached in the -q run
U03  LoadLibraryW return value (HMODULE or NULL)
U04  GetLastError immediately after LoadLibraryW
U05  Whether the constructed path resolved to IIPS/ifs2.dll on disk
U06  GetProcAddress("CreateIFSLibDll") return value
U07  CreateIFSLibDll return value (EAX) and [this+0x50] output
U08  GetProcAddress("DestoryIFSLibDll") return value
U09  Runtime value of [this+0xCC] and how the EXE reads it
U10  The exact IIPS -> EXE marshalling of the failure state
U11  Which EXE packed block consumes WIN_IIPS_INIT_ERROR (0xDC93A8)
U12  How the EXE computes 0x8189FEC (packed/VM expression, source operands)
U13  Whether 0x8189FEC is the CNIFS object address, the [this+0xCC] value,
     a pointer-derived value, or a packed-status encoding
U14  Whether the observed fatal state was produced by +0x96EF, or by a
     different branch (+0x977E / +0x97A7 / +0x97CE), or by a post-initIfsLib
     failure (HostApp / share-state / IIPSHostApp.ini read)
U15  The internal semantics of the .tvm0 section (0xE5D3000, size 0x4000)
U16  Whether IFS2.dll ever produced a transient/rollback image load
     (module absence is not proof of LoadLibraryW absence)
U17  Whether IIPSERR_* index -> string resolution is ini-driven, ID-driven,
     or a compiled localisation table
U18  The consumer chain of "IIPS\iips.dll" (VA 0xDC93F0, 0 refs)
U19  The EXE-side loader of iips.dll itself (packed; no plain .text caller)
U20  Whether the 0x95D0 short-circuit was taken in the observed run
U21  Whether the vtable targets called at 0x9A35/0x9B5B/0x9B70/0x9B88 are
     reached before or after the IFS2 dependency is satisfied
U22  Whether sub_6D20 (QoS helper) can fail in a way that matters later
     (both of its edges currently converge, so it is not a gate here)
```

---

## 11. Next Experiment

Dynamic API tracing was stopped by instruction, and this round forbids
patch / bypass / fake-return / parameter-matrix expansion. The next
experiment must therefore be static-first, and must attack the specific
unknowns that block closure of the failure chain.

### Primary: static recovery of the EXE packed error emitter

Goal: recover the expression that computes `0x8189FEC` and the block that
consumes `WIN_IIPS_INIT_ERROR`.

```text
1. Identify the .tp3 VM entry that owns VA 0x58F0xx..0x58F4xx (the region
   containing the IIPS error push sites) and determine the bytecode
   encoding used there.
2. Recover that VM region's operand/constant pool and search for a
   constant or expression whose value yields 0x8189FEC under the VM's
   rules (e.g. an OR/ADD/SHL combination, or a 4-byte pool entry).
3. Locate the consumer block for VA 0xDC93A8 (WIN_IIPS_INIT_ERROR) by
   scanning the VM constant pool / index tables for its index, not for
   its absolute address.
4. Decide whether the printed value is a pointer (object address) or a
   status integer, by checking whether the same VM block also loads from
   the CNIFS object pointer.
```

### Secondary: CNIFS object construction

Goal: determine whether `[this+0x60]` is non-zero when `InitInGameApp`
calls `initIfsLib`, without running the target.

```text
5. Recover the CNIFS constructor in iips.dll (the function that
   initialises +0x50 / +0x54 / +0x58 / +0x5C / +0x60 / +0xCC / +0x120)
   and record the initial value written to +0x60.
6. Find every writer of [this+0x60] in the whole iips.dll image and
   determine whether any of them can execute before the first initIfsLib.
```

### Tertiary: bounded arithmetic search for 0x8189FEC

```text
7. Scan the EXE packed .tp3 region for any byte sequence that, decoded
   under the VM's operand encoding, would produce 0x8189FEC. Report
   STATIC_UNKNOWN if the encoding cannot be established with evidence.
```

### Validation criterion

```text
The next round succeeds only if it can state, with a file offset and a
decoded instruction or bytecode operand, either:

  (a) the exact expression / pool entry that yields 0x8189FEC, or
  (b) that the .tp3 VM encoding is not recoverable from static data alone
      (in which case 0x8189FEC remains STATIC_UNKNOWN, and that is the
       honest result).
```

### Explicitly NOT next

```text
- no debugger attach (reproduces OBSERVER_DIVERGENCE)
- no user-mode API breakpoints
- no iips.dll patch
- no -q / -qa parameter expansion
- no "IFS2 is missing" claim
```

---

## Core Question Answer

> IIPS 在其内部 CFG 中,最早在哪一个条件/状态转换上无法继续向下。

```text
Within the statically reachable IIPS CFG (InitInGameApp -> initIfsLib),
the earliest conditional transition whose outcome decides whether IIPS can
continue downward is:

  iips.dll+0x95D0
      cmp dword ptr [ebp+0x60], 0
      jne 0x10009818

  [this+0x60] == 0  ->  continue to LoadLibraryW (+0x96E9)
  [this+0x60] != 0  ->  short-circuit success, no LoadLibraryW

If and only if that gate permits continuation, the earliest *failure*
transition on the downward path is:

  iips.dll+0x96EF
      test eax, eax             ; eax = LoadLibraryW(<iipsdir>/ifs2.dll)
      jne  0x10009770
  NULL -> +0x96F6  "Failed to open dllfile"
          [this+0xCC] = 1
          return AL = 0

Which of these two transitions actually blocked the observed -q run is NOT
determinable from static data, because:

  - the runtime value of [this+0x60] is unknown (U01 / U20);
  - the LoadLibraryW return is unknown (U02 / U03);
  - 0x8189FEC is produced by a packed computation and has zero static
    references anywhere (U12 / U13).

Therefore:

  EARLIEST_STATIC_FAILURE_BRANCH       = iips.dll+0x96EF  STATIC_REACHABLE
  EARLIEST_STATIC_DECISION_POINT       = iips.dll+0x95D0  STATIC_UNKNOWN value
  ACTUAL_FIRST_FAILURE_IN_OBSERVED_RUN = UNKNOWN
```

---

## Final Classification

```text
EX060_IIPS_CFG_CLOSURE

STATIC_CONFIRMED
  InitInGameApp  +0x9860  1057 insns / 162 BBs / 1 ret (0xA833)
  initIfsLib     +0x9570   176 insns /  24 BBs / 1 ret (0x9839)
  initIfsLib argument and path provenance recovered
  LoadLibraryW path = <iipsdir> + L"/ifs2.dll" (RVA 0x34908)
  four distinct error paths, statuses 1 / 2 / 3 in [this+0xCC]
  four error strings recovered verbatim

STATIC_REACHABLE
  +0x9860 -> +0x99D2 -> +0x9570 -> +0x96E9
  conditional only on [this+0x60] == 0 at +0x95D0

STATIC_NOT_REACHABLE
  (no error branch inside initIfsLib is unreachable)

STATIC_UNKNOWN
  +0x95D0 runtime value
  0x8189FEC producing expression (packed)
  WIN_IIPS_INIT_ERROR consumer (packed)
  IIPS -> EXE failure-state marshalling

DYNAMIC_CONFIRMED   (carried from EX-057 / EX-059)
  iips.dll module load in normal -q
  no observed IFS2.dll image load
  no observed IIPSHostApp.exe image / process
  iips.dll unload
  WIN_IIPS_INIT_ERROR / 0x8189FEC observed as the fatal token

DYNAMIC_UNKNOWN
  every user-mode API return on the initIfsLib path

0x8189FEC_REFERENCE_COUNT     = 0   (all modules, all encodings)
0x8189FEC_CLASS               = VA-shaped, EXE-image-internal,
                                runtime-computed, never stored / compared
WIN_IIPS_INIT_ERROR_REF_COUNT = 0
WIN_IIPS_INIT_ERROR_CLASS     = packed / VM-consumed EXE error label

NO_PATCH
NO_BYPASS
NO_FAKE_RETURN
NO_iips.dll_MODIFICATION
NO_CODOL_CORE_LOGIC_MODIFICATION
NO_PARAMETER_MATRIX_EXPANSION
NO_DYNAMIC_API_TRACING
NO_IFS2_MISSING_CLAIM
```
