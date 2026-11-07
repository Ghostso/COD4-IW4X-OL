# CODOL_EX064_GETRESOURCEMANAGER_CALLERS

## Scope and Constraints Observed

This round is offline static analysis only.

Not performed:

```text
debugger attach
API hooking
Frida
ETW API tracing
runtime injection
patch
bypass
fake success
IAT modification
export modification
vtable modification
EXE/DLL modification
loader modification
parameter modification
```

No process was started, attached to, or instrumented.

### Binary integrity

```text
iips.dll  sha256  72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
```

Unchanged from EX-060 .. EX-063.

### Evidence vocabulary

```text
STATIC_DIRECT      operand / target is literal in the decoded instruction
STATIC_INDIRECT    value arrives via pointer, register, or resolved export
STATIC_REACHABLE   a static CFG path exists, edge is not literal
EXTERNAL_BOUNDARY  resolution requires a module outside the analysed one
STATIC_UNKNOWN     static data is insufficient

DYNAMIC_CONFIRMED is NOT used in this round.
```

---

## EXECUTIVE ANSWER

The external caller HAS been found.

```text
The iips.dll export GetResourceManagerII is NOT imported by any module.
It is resolved DYNAMICALLY by GetProcAddress in:

    IIPSLaunchRestore.dll
        0x3C48  call KERNEL32!LoadLibraryW      -> hMod = iips.dll
        0x3C89  push "GetResourceManagerII"
        0x3C8F  call KERNEL32!GetProcAddress
        0x3C99  call eax                        *** the external call ***
        0x3CA1  mov [esi+0xA8], eax             manager* cached

and IIPSLaunchRestore.dll is itself loaded dynamically by:

    WeGame\tcls\tcls_core.exe
        0x8D353 call KERNEL32!LoadLibraryW      -> hMod = IIPSLaunchRestore.dll
        0x8D382 push "CreateIIPSRepair"
        0x8D38A call KERNEL32!GetProcAddress
        0x8D39F call [ebp-0x30]                 *** the TCLS external call ***
```

Two further resolution sites exist for the same pair, confirming the
pattern:

```text
IIPSLaunchRestore.dll 0x744F  GetProcAddress("GetResourceManagerII")
IIPSLaunchRestore.dll 0x745F  call eax
IIPSLaunchRestore.dll 0x3608  GetProcAddress("ReleaseResourceManagerII")
IIPSLaunchRestore.dll 0x5CD4  GetProcAddress("ReleaseResourceManagerII")
tcls_core.exe         0x8D51F GetProcAddress("RealeaseIIPSRepair")
```

**Important correction to the EX-063 hypothesis:** the consumer does NOT
dispatch manager slot 5 (+0x14). It dispatches **slot 26 (+0x68)** and
then **slot 1 (+0x04)**.

The remaining boundary is now outside the iips/restore pair:

```text
EXTERNAL_BOUNDARY = who starts tcls_core.exe / the WeGame TCLS bootstrap
```

---

## A. `GetResourceManagerII` Export

Confirmed from EX-063; re-verified here.

```text
module           iips.dll
export name      GetResourceManagerII
ordinal          (by name; no ordinal-only export)
RVA              0x1C80
VA               0x10001C80
```

### A.1 Export table (all 4 entries)

| export | RVA |
|---|---|
| `GetResourceManager` | `0x1BC0` |
| `ReleaseResourceManager` | `0x1C60` |
| `ReleaseResourceManagerII` | `0x1C60` |
| `GetResourceManagerII` | `0x1C80` |

```text
EVIDENCE  STATIC_DIRECT
```

### A.2 Calling convention / arguments / return

```text
0x1C80  push -1
0x1C82  push 0x100325A9
0x1C87  mov eax, fs:[0]
0x1C8D  push eax
0x1C8E  push ecx
0x1C8F  mov eax, [0x10042020]
0x1C94  xor eax, esp
0x1C96  push eax
0x1C97  lea eax, [esp+8]
0x1C9B  mov fs:[0], eax
```

```text
no stack argument is read
no ECX is read as `this`
returns via EAX
ends with `ret` (no stack cleanup)

CONVENTION  = no argument; returns a pointer in EAX
EVIDENCE    = STATIC_DIRECT
```

### A.3 Return value

```text
0x1CB1  push 0x410                     ; sizeof(MANAGER) = 1040
0x1CBE  call operator new (sub_2BE34)  ; MSVCR80!??2@YAPAXI@Z
0x1CD4  call sub_11F20                 ; manager ctor
0x1CD9  mov [0x1004EB68], eax          ; global cache
0x1CED  ret                            ; EAX = manager*

failure path:
0x1CEE  xor eax, eax
0x1CF0  mov [0x1004EB68], eax          ; cache = NULL
0x1D04  ret                            ; EAX = NULL

cached path:
0x1D05  mov eax, [0x1004EB68]
0x1D15  ret
```

```text
EAX = manager*            STATIC_DIRECT
[0x1004EB68] = manager*   STATIC_DIRECT
SINGLETON / GLOBAL CACHE  = CONFIRMED
EVIDENCE = STATIC_DIRECT
```

---

## B. All-Module Import Map

### B.1 Method

```text
scanned     6072 PE files under the CODOL working tree
checked     IMAGE_DIRECTORY_ENTRY_IMPORT
            IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT
            IMAGE_DIRECTORY_ENTRY_EXPORT
            + raw ASCII / UTF-16LE string search
symbols     GetResourceManagerII, GetResourceManager,
            ReleaseResourceManagerII, ReleaseResourceManager
```

### B.2 Result

```text
GetResourceManagerII  as a normal IMPORT   : 0 modules
GetResourceManagerII  as a DELAY IMPORT    : 0 modules
GetResourceManagerII  as an EXPORT         : 1 module (iips.dll itself)
```

**No module imports the iips.dll manager exports.**

### B.3 String occurrences (the decisive evidence)

| module | string | encoding | location |
|---|---|---|---|
| `codoMP_client_shipRetail.exe` | `GetResourceManagerII` | ascii | VA `0xDC9294`, `.tp3` (packed data) |
| `codoMP_client_shipRetail.exe` | `ReleaseResourceManagerII` | ascii | VA `0xDC92AC`, `.tp3` (packed data) |
| `IIPSLaunchRestore.dll` | `GetResourceManagerII` | ascii | VA `0x1006F43C`, `.rdata` |
| `IIPSLaunchRestore.dll` | `ReleaseResourceManagerII` | ascii | VA `0x1006F454`, `.rdata` |

```text
The EXE occurrence sits inside the packed .tp3 region next to
WIN_IIPS_* strings (EX-060) and is not referenced by any plain instruction.

The IIPSLaunchRestore.dll occurrence sits in plain .rdata and IS
referenced by push instructions (see section D).
EVIDENCE  STATIC_DIRECT
```

### B.4 Modules that reference iips.dll at all

```text
tools/EX035_DIR/IIPS/IIPSHost.dll -> imports iips_policymsg.dll
```

(a companion policy-message DLL, not the manager export)

```text
NO module in the tree imports iips.dll itself by name in its import table.
EVIDENCE  STATIC_DIRECT
```

---

## C. Import Thunk Map

### C.1 `IIPSLaunchRestore.dll` IAT slots used

```text
base 0x10000000  size 0x9B000
sections:
   .text    VA 0x00001000  vsize 0x006A67C
   .rdata   VA 0x0006C000  vsize 0x00128E6
   .data    VA 0x0007F000  vsize 0x0013944
   .rsrc    VA 0x00093000  vsize 0x0000418
   .reloc   VA 0x00094000  vsize 0x0006046
```

| IAT VA | DLL | symbol |
|---|---|---|
| `0x1006C038` | `KERNEL32.dll` | `LoadLibraryW` |
| `0x1006C044` | `KERNEL32.dll` | `GetProcAddress` |
| `0x1006C0FC` | `KERNEL32.dll` | `LoadLibraryA` |
| `0x1006C050` | `KERNEL32.dll` | `FreeLibrary` |
| `0x1006C01C` | `KERNEL32.dll` | `WriteFile` |

```text
the module uses the IAT directly (`call dword ptr [IAT]`); there is no
compiler thunk layer to unwind.
EVIDENCE  STATIC_DIRECT
```

### C.2 `tcls_core.exe` IAT slots used

```text
base 0x400000  size 0x1E6000
```

| IAT VA | DLL | symbol |
|---|---|---|
| `0x00556044` | `KERNEL32.dll` | `GetProcAddress` |
| `0x00556058` | `KERNEL32.dll` | `LoadLibraryW` |
| `0x0055617C` | `KERNEL32.dll` | `LoadLibraryA` |
| `0x005562FC` | `KERNEL32.dll` | `LoadLibraryExW` |
| `0x00556040` | `KERNEL32.dll` | `FreeLibrary` |

### C.3 `iips.dll` IAT slots used on the path (from EX-060)

| IAT VA | DLL | symbol |
|---|---|---|
| `0x10033010` | `KERNEL32.dll` | `LoadLibraryW` |
| `0x10033014` | `KERNEL32.dll` | `GetProcAddress` |
| `0x10033018` | `KERNEL32.dll` | `FreeLibrary` |
| `0x10033028` | `KERNEL32.dll` | `EnterCriticalSection` |
| `0x1003302C` | `KERNEL32.dll` | `LeaveCriticalSection` |
| `0x100330B4` | `KERNEL32.dll` | `GetPrivateProfileIntW` |
| `0x1003328C` | `MSVCR80.dll` | `??2@YAPAXI@Z` (operator new) |
| `0x1003328C` | `MSVCR80.dll` | same slot used by both factories |

```text
EVIDENCE  STATIC_DIRECT
```

---

## D. `GetResourceManagerII` Callers

### D.1 Primary caller: `IIPSLaunchRestore.dll`

```text
module           IIPSLaunchRestore.dll
function         sub_3AF0  (CallBackThread::StartLauchRestore)
entry            0x3AF0
```

Instruction-level evidence:

```text
0x3B0D  (function body continues)
0x3B25  mov esi, ecx                        ; this = CallBackThread
0x3B27  lea edi, [esi+0x16C]
0x3B2D  call sub_15540
0x3B32  test al, al
0x3B34  jne 0x10003B60
...
0x3B78  mov ebx, 7
0x3BAD  call sub_119C0                      ; build the iips path (std::wstring)
0x3BB2  test al, al
0x3BB4  je 0x10003D8A
0x3BBA  mov edx, 0x100734A8
0x3BC3  call sub_8A20
0x3BD1  lea edx, [esp+0x18]
0x3BDD  call sub_116E0
0x3BF4  call sub_AB70
0x3C19  cmp dword [esp+0x48], 8
0x3C2C  mov edx, [esp+0x34]
0x3C31  call sub_47570                       ; free temp
0x3C39  cmp dword [esp+0x64], 8
0x3C3D  mov eax, [esp+0x50]                  ; <== the wide path buffer
0x3C41  jae 0x10003C47
0x3C43  lea eax, [esp+0x50]
0x3C47  push eax
0x3C48  call dword ptr [0x1006C038]          ; KERNEL32!LoadLibraryW
0x3C4E  cmp eax, edi
0x3C50  mov dword ptr [esi + 0xAC], eax      ; [this+0xAC] = hMod (iips.dll)
0x3C56  jne 0x10003C89                       ; success -> resolve the export
0x3C58  lea eax, [esi+0x34]
0x3C5B  mov ecx, 0x10073508                  ; "[...][IIPSRESTORE_LOADIIPSDLLFAILED]"
0x3C60  call sub_F2A0
0x3C65  mov eax, [esi+0xA4]
0x3C6B  mov dword [eax+0x2C], 0xE0000003
0x3C72  ...
0x3C84  jmp 0x10003DE9                       ; failure exit
0x3C89  push 0x1006F43C                      ; "GetResourceManagerII"
0x3C8E  push eax                             ; hMod
0x3C8F  call dword ptr [0x1006C044]          ; KERNEL32!GetProcAddress
0x3C95  cmp eax, edi
0x3C97  je 0x10003C9D
0x3C99  call eax                             ; *** GetResourceManagerII() ***
0x3C9B  jmp 0x10003C9F
0x3C9D  xor eax, eax
0x3C9F  cmp eax, edi
0x3CA1  mov dword ptr [esi + 0xA8], eax      ; [this+0xA8] = manager*
0x3CA7  je 0x10003D6B                        ; NULL -> GETIIPSRESOURCEMANAGERFAILED
0x3CAD  mov ecx, dword ptr [esi + 0x20]
0x3CB0  mov edx, dword ptr [eax]             ; manager vtable
0x3CB2  mov edx, dword ptr [edx + 0x68]      ; *** MANAGER SLOT 26 ***
0x3CB5  push ecx
0x3CB6  mov ecx, eax                         ; this = manager*
0x3CB8  call edx                             ; invoke slot 26
0x3CBA  mov ecx, esi
0x3CBC  call sub_79B0
0x3CC1  test al, al
0x3CC3  jne 0x10003CD4
0x3CC5  lea eax, [esi+0x34]
0x3CC8  mov ecx, 0x100735A0                  ; "[...][do before start iips failed]"
0x3CCD  call sub_F2A0
0x3CD2  jmp 0x10003C72
0x3CD4  mov ecx, dword ptr [esi + 0xA8]      ; reload manager*
0x3CDA  mov eax, dword ptr [ecx]
0x3CDC  mov edx, dword ptr [eax + 4]         ; *** MANAGER SLOT 1 ***
0x3CDF  push 0x100735E4                      ; "http://localhost"
0x3CE4  call edx                             ; invoke slot 1
0x3CE6  test al, al
0x3CE8  jne 0x10003D20
```

| item | value | evidence |
|---|---|---|
| caller module | `IIPSLaunchRestore.dll` | `STATIC_DIRECT` |
| caller function | `sub_3AF0` (`CallBackThread::StartLauchRestore`) | `STATIC_DIRECT` |
| caller RVA | `0x3C99` | `STATIC_DIRECT` |
| basic block | `0x3C89 .. 0x3C9B` | `STATIC_DIRECT` |
| instruction | `call eax` where `eax = GetProcAddress(...)` | `STATIC_INDIRECT` |
| IAT/thunk target | `0x1006C044` (`GetProcAddress`), name at `0x1006F43C` | `STATIC_DIRECT` |
| predecessor | `0x3C8F call [0x1006C044]` | `STATIC_DIRECT` |
| successor | `0x3C9B jmp 0x3C9F` / `0x3C9F cmp eax, edi` | `STATIC_DIRECT` |

**This is the exact instruction-level caller the task required.**

### D.2 Secondary caller site (same module, same export)

```text
function    sub_7430   (worker / DoInitIIPSAfterDelete path)
0x744F      push 0x1006F43C                ; "GetResourceManagerII"
0x7454      push eax                        ; hMod
0x7455      call dword ptr [0x1006C044]    ; GetProcAddress
0x745B      cmp eax, ebp
0x745D      je 0x10007463
0x745F      call eax                        ; *** GetResourceManagerII() ***
0x7461      jmp 0x10007465
0x7463      xor eax, eax
0x7465      cmp eax, ebp
0x7467      mov dword ptr [edi + 0xA8], eax ; manager* cached (same field)
0x746D      je 0x10007511
0x7473      mov ecx, dword ptr [edi + 0x20]
0x7476      mov edx, dword ptr [eax]
0x7478      mov edx, dword ptr [edx + 0x68] ; *** MANAGER SLOT 26 again ***
0x747B      push ecx
0x747C      mov ecx, eax
0x747E      call edx
0x7480      mov ecx, dword ptr [edi + 0xA8]
0x7486      mov eax, dword ptr [ecx]
0x7488      mov edx, dword ptr [eax + 4]     ; *** MANAGER SLOT 1 again ***
0x748B      push 0x100735E4                  ; "http://localhost"
0x7490      call edx
```

### D.3 Release callers (for completeness)

```text
sub_3600   (helper, arg1 = hMod, arg2 = manager*)
   0x3600  test eax, eax / je 0x10003621
   0x3604  test esi, esi / je 0x10003621
   0x3608  push 0x1006F454                ; "ReleaseResourceManagerII"
   0x360D  push eax                       ; hMod
   0x360E  call dword ptr [0x1006C044]    ; GetProcAddress
   0x3614  test eax, eax / je 0x10003621
   0x3618  push esi                       ; manager*
   0x3619  call eax                       ; ReleaseResourceManagerII(manager*)
   0x361E  mov al, 1
   0x3620  ret

sub_8190-ish (DoRestoreSuccess)
   0x5CD4  push 0x1006F454                ; "ReleaseResourceManagerII"
   0x5CD9  push eax                       ; hMod
   0x5CDA  call dword ptr [0x1006C044]    ; GetProcAddress
   0x5CE0  cmp eax, ebp / je 0x10005CEA
   0x5CE4  push edi                       ; manager*
   0x5CE5  call eax
   0x5CE7  add esp, 4
   0x5CEA  mov eax, [esi+0xAC]            ; hMod
   0x5CF0  push eax
   0x5CF1  call dword ptr [0x1006C050]    ; KERNEL32!FreeLibrary
   0x5CF7  mov [esi+0xAC], ebp            ; clear hMod
   0x5CFD  mov [esi+0xA8], ebp            ; clear manager*
```

### D.4 EXE caller status

```text
IMPORT_PRESENT = NO
CALLER         = NOT RECOVERED (see section I)
```

The EXE contains the name `GetResourceManagerII` only as packed `.tp3`
data, with no plain instruction referencing it. This is recorded as
`PACKED_CALLER_UNRESOLVED`, not as a call site.

---

## E. EAX Manager Pointer Dataflow

### E.1 Path in `IIPSLaunchRestore.dll`

```text
0x3C8F  call [0x1006C044]      ; GetProcAddress -> EAX = address of the export
0x3C95  cmp eax, edi           ; edi = 0 (NULL check)
0x3C97  je 0x10003C9D
0x3C99  call eax               ; EAX = GetResourceManagerII() = manager*
0x3C9B  jmp 0x10003C9F
0x3C9D  xor eax, eax           ; NULL when resolution failed
0x3C9F  cmp eax, edi
0x3CA1  mov dword ptr [esi + 0xA8], eax   ; *** STORE manager* ***
0x3CA7  je 0x10003D6B                     ; NULL -> error path
```

```text
storage destination : [this + 0xA8] of the CallBackThread object
base register       : ESI
ESI source          : 0x3B25  mov esi, ecx     (this)
kind                : struct field, heap object, NOT a global
```

### E.2 All accesses to the manager field `+0xA8`

| RVA | instruction | role |
|---|---|---|
| `0x3CA1` | `mov [esi+0xA8], eax` | store (primary) |
| `0x3CD4` | `mov ecx, [esi+0xA8]` | load, then slot 1 |
| `0x3CEA` | `mov ecx, [esi+0xA8]` | load |
| `0x3CF9` | `mov ecx, [esi+0xA8]` | load |
| `0x3EEF` | `mov ecx, [edi+0xA8]` | load |
| `0x3F87` | `mov ecx, [edi+0xA8]` | load |
| `0x3F9B` | `mov esi, [edi+0xA8]` | load |
| `0x3FC8` | `mov [edi+0xA8], esi` | store (restore path) |
| `0x40C0` | `mov ecx, [edi+0xA8]` | load |
| `0x40D5` | `mov ecx, [edi+0xA8]` | load |
| `0x443F` | `mov ecx, [edi+0xA8]` | load |
| `0x4450` | `mov esi, [edi+0xA8]` | load |
| `0x4474` | `mov [edi+0xA8], ebp` | clear (NULL) |
| `0x45xx`..`0x4Fxx` | several loads | thread/state machine uses |
| `0x5CAF` | `mov ecx, [esi+0xA8]` | load before release |
| `0x5CC8` | `mov edi, [esi+0xA8]` | load for release arg |
| `0x5CFD` | `mov [esi+0xA8], ebp` | clear after release |
| `0x7467` | `mov [edi+0xA8], eax` | store (secondary site) |
| `0x7480` | `mov ecx, [edi+0xA8]` | load |
| `0x7496` | `mov ecx, [edi+0xA8]` | load |
| `0x74A3` | `mov esi, [edi+0xA8]` | load |
| `0x74CF` | `mov [edi+0xA8], ebp` | clear |

```text
the SAME struct field +0xA8 is used by both call sites
=> one manager* per CallBackThread instance
EVIDENCE  STATIC_DIRECT
```

### E.3 Relationship to the iips.dll singleton `[0x1004EB68]`

```text
iips.dll   GetResourceManagerII returns EAX
              and stores the SAME value into [0x1004EB68]  (0x1CD9)

IIPSLaunchRestore.dll
              receives that value in EAX and stores it into [this+0xA8]

therefore
   [CallBackThread+0xA8]  ==  [iips.dll+0x1004EB68]  ==  the singletons

CLASSIFICATION
   the *identity* of the pointer is STATIC_INDIRECT
     (it arrives through a call return, not through a literal load)
   the fact that BOTH storage locations hold the same object is
     STATIC_DIRECT for the iips.dll side (both writes use EAX)
     and STATIC_INDIRECT for the cross-module side

NOTE: this round does NOT claim [CallBackThread+0xA8] and
      [0x1004EB68] were equal at runtime.  It claims that the code
      paths that produce them both consume the same EAX value of the
      same export call.
```

### E.4 iips.dll-side global accesses

```text
0x1CA1  test byte ptr [0x1004EB6C], 1   ; created guard
0x1CAA  or   dword ptr [0x1004EB6C], 1  ; set the guard
0x1CD9  mov  dword ptr [0x1004EB68], eax ; store (success)
0x1CF0  mov  dword ptr [0x1004EB68], eax ; store (NULL on failure)
0x1D05  mov  eax, dword ptr [0x1004EB68] ; load (cached path)
```

```text
EVIDENCE  STATIC_DIRECT
```

---

## F. Manager Singleton `[0x1004EB68]`

```text
symbol          0x1004EB68   (iips.dll .data)
role            global pointer to the manager singleton
guard           0x1004EB6C   (bit 0 = constructed)
sibling cache   0x1004EB70   (the sibling class from GetResourceManager)
sibling guard   0x1004EB74
```

| global | writers | readers |
|---|---|---|
| `0x1004EB68` | `0x1CD9`, `0x1CF0` (both inside `GetResourceManagerII`) | `0x1D05` |
| `0x1004EB70` | `0x1C19`, `0x1C30` (both inside `GetResourceManager`) | `0x1C45` |
| `0x1004EB6C` | `0x1CAA` (or 1), `0x32598` | `0x1CA1` (test), `0x32590` |
| `0x1004EB74` | `0x1BEA` (or 1), `0x328F8` | `0x1BE1` (test), `0x328F0` |

```text
the manager global is written ONLY in the factory and read ONLY in the
factory's cached branch.  No other module touches it.

SINGLETON_CONFIRMED = STATIC_DIRECT
EVIDENCE            = STATIC_DIRECT
```

---

## G. Manager Slot-5 Consumers

### G.1 Correction to the EX-063 expectation

EX-063 predicted the consumer would dispatch manager slot 5
(`+0x14` -> `sub_1A270`). The actual code dispatches:

```text
slot 26  offset +0x68  -> 0x100178F0      (sub_178F0)
slot 1   offset +0x04  -> 0x100197F0      (sub_197F0)
```

Verification against the manager vtable `0x1003934C`:

| offset | slot | target |
|---|---|---|
| `+0x04` | 1 | `0x100197F0` (`sub_197F0`) |
| `+0x14` | 5 | `0x1001A270` (`sub_1A270`) |
| `+0x68` | 26 | `0x100178F0` (`sub_178F0`) |
| `+0x6C` | 27 | `0x10017F60` (`sub_17F60`) |

```text
vtable size = 47 slots = 0xBC bytes
+0x68 < 0xBC  -> slot 26 is INSIDE the vtable
+0x14 < 0xBC  -> slot  5 is INSIDE the vtable

EVIDENCE  STATIC_DIRECT
```

### G.2 Slot-5 dispatch sites inside iips.dll (unchanged from EX-063)

```text
sub_1A270 (manager vtable slot 5) is invoked from the manager itself.
Its own body dispatches:
    0x1A2FC  mov ecx, [esi+0x19C]
    0x1A302  mov eax, [ecx]
    0x1A304  mov edx, [eax+4]      ; slot 1 of the NESTED manager
    0x1A309  call edx              ; -> sub_197F0
EVIDENCE  STATIC_INDIRECT
```

### G.3 Slot-1 dispatch sites (as used by IIPSLaunchRestore.dll)

```text
inside IIPSLaunchRestore.dll:
   0x3CDC  mov edx, [eax+4]       ; slot 1
   0x3CE4  call edx
   0x7488  mov edx, [eax+4]       ; slot 1
   0x7490  call edx

both operate on the manager* returned by GetResourceManagerII
([this+0xA8]), NOT on a nested manager.
EVIDENCE  STATIC_DIRECT (slot fetch) + STATIC_INDIRECT (call)
```

### G.4 Slot-26 consumers

```text
0x3CB2  mov edx, [edx+0x68]  ; slot 26
0x3CB8  call edx
    arg:  push ecx  where ecx = [esi+0x20]
    this: ecx = eax (the manager*)

0x7478  mov edx, [edx+0x68]  ; slot 26
0x747E  call edx
```

```text
manager slot 26 target = sub_178F0 (0x100178F0)
EVIDENCE  STATIC_DIRECT (slot values) + STATIC_INDIRECT (call)
```

### G.5 Consequence for the slot-1 -> sub_197F0 chain

```text
The slot-1 offset IS used by IIPSLaunchRestore.dll on the manager* whose
slot 1 is sub_197F0.  So the chain

    GetResourceManagerII()
      -> manager*
      -> [manager*][+0x04] = 0x100197F0 = sub_197F0
      -> sub_12760
      -> CNIFS::InitInGameApp

IS statically constructible from the external caller.

However the call at 0x3CE4 / 0x7490 passes:
    0x3CDF  push 0x100735E4        ; "http://localhost"
    ECX = manager*
so sub_197F0's single stack argument is a string pointer.

EVIDENCE  STATIC_DIRECT for the slot value and the argument;
          STATIC_INDIRECT for the call.
```

---

## H. Dynamic `GetProcAddress` Paths

### H.1 Complete inventory

| module | site RVA | DLL argument source | symbol string | fnptr storage | call site |
|---|---|---|---|---|---|
| `IIPSLaunchRestore.dll` | `0x3C8F` | `EAX` = hMod from `0x3C48` (`[esi+0xAC]`) | `GetResourceManagerII` | `[esi+0xA8]` | `0x3C99` |
| `IIPSLaunchRestore.dll` | `0x7455` | `EAX` = hMod in `[edi+0xAC]` | `GetResourceManagerII` | `[edi+0xA8]` | `0x745F` |
| `IIPSLaunchRestore.dll` | `0x360E` | `EAX` = hMod (arg1) | `ReleaseResourceManagerII` | local `[esp]`-ish | `0x3619` |
| `IIPSLaunchRestore.dll` | `0x5CDA` | `EAX` = hMod in `[esi+0xAC]` | `ReleaseResourceManagerII` | local | `0x5CE5` |
| `tcls_core.exe` | `0x8D38A` | `[ebp-0x48]` = hMod from `0x8D353` | `CreateIIPSRepair` | `[ebp-0x30]` | `0x8D39F` |
| `tcls_core.exe` | `0x8D527` | `[ebp-0x20]` = hMod from `[obj+0x5268]` | `RealeaseIIPSRepair` | `[ebp-0x18]` | `0x8D53F` |

### H.2 Symbol strings

```text
IIPSLaunchRestore.dll .rdata:
    0x1006F43C  "GetResourceManagerII"      (push at 0x3C89, 0x744F)
    0x1006F454  "ReleaseResourceManagerII"  (push at 0x3608, 0x5CD4)

tcls_core.exe .rdata:
    0x0056A4B0  "CreateIIPSRepair"          (push at 0x8D382, 0x8D51F region)
    0x0056A4C4  "RealeaseIIPSRepair"        (push at 0x8D51F)
```

Every symbol string is confirmed as a literal, relocated push operand.

```text
EVIDENCE  STATIC_DIRECT
```

### H.3 The resolution is dynamic, not import-based

```text
no Import Name
no Import Ordinal
no Delay Import
no Forwarder
```

The path is:

```text
LoadLibraryW(<runtime path>)          -> HMODULE
GetProcAddress(HMODULE, "<name>")     -> function pointer
call <function pointer>               -> the export
```

which is exactly the "manual/dynamic import" case the task asked to check.

```text
EVIDENCE  STATIC_DIRECT
```

---

## I. `iips.dll` Acquisition Paths

### I.1 Two-stage acquisition (confirmed)

```text
STAGE 1  acquire IIPSLaunchRestore.dll

    module   WeGame\tcls\tcls_core.exe
    function sub_8D2A2
    0x8D2A2  push ebp ; mov ebp, esp ; ...   (function prologue)
    0x8D2CA  mov [ebp-0x2C], ecx              ; this
    0x8D2D3  push eax  ([this+0x38])
    0x8D2D7  push [this+0x34]
    0x8D2DA  push [this+0x30]
    0x8D2E1  call sub_8C8CF                   ; build the DLL path
    0x8D348  call sub_A631                    ; -> wide string pointer
    0x8D34D  mov [ebp-0x44], eax
    0x8D350  push [ebp-0x44]
    0x8D353  call dword ptr [0x556058]        ; KERNEL32!LoadLibraryW
    0x8D359  mov ecx, [ebp-0x2C]
    0x8D35C  mov [ecx+0x5268], eax            ; store HMODULE
    0x8D362  mov eax, [ebp-0x2C]
    0x8D365  cmp dword [eax+0x5268], 0
    0x8D36C  je 0x48D430                      ; failure exit
    0x8D372  mov eax, [ebp-0x2C]
    0x8D375  mov eax, [eax+0x5268]
    0x8D37B  mov [ebp-0x48], eax              ; hMod
    0x8D382  push 0x56A4B0                    ; "CreateIIPSRepair"
    0x8D387  push [ebp-0x48]
    0x8D38A  call dword ptr [0x556044]        ; KERNEL32!GetProcAddress
    0x8D390  mov [ebp-0x30], eax
    0x8D393  cmp dword [ebp-0x30], 0
    0x8D397  jne 0x48D39F
    0x8D399  and dword [ebp-0x38], 0
    0x8D39D  jmp 0x48D3A5
    0x8D39F  call dword ptr [ebp-0x30]        ; *** CreateIIPSRepair() ***
    0x8D3A2  mov [ebp-0x38], eax
    0x8D3A5  mov eax, [ebp-0x2C]
    0x8D3AB  mov [eax+0x526C], ecx            ; store the repair object

    loader API        : KERNEL32!LoadLibraryW        (IAT 0x556058)
    resolved symbol   : "CreateIIPSRepair"
    target module     : IIPSLaunchRestore.dll (path built at 0x8D2E1)
    IIPS_LOAD         : STATIC_CONFIRMED
    GETRESOURCE_CALL  : not in this module (it calls CreateIIPSRepair)

STAGE 2  acquire iips.dll

    module   IIPSLaunchRestore.dll
    function sub_3AF0  (CallBackThread::StartLauchRestore)
    0x3C39  cmp dword [esp+0x64], 8
    0x3C3D  mov eax, [esp+0x50]               ; wide path buffer
    0x3C47  push eax
    0x3C48  call dword ptr [0x1006C038]       ; KERNEL32!LoadLibraryW
    0x3C50  mov [esi+0xAC], eax               ; HMODULE of iips.dll
    0x3C89  push 0x1006F43C                   ; "GetResourceManagerII"
    0x3C8F  call dword ptr [0x1006C044]       ; KERNEL32!GetProcAddress
    0x3C99  call eax                          ; *** GetResourceManagerII() ***

    loader API        : KERNEL32!LoadLibraryW        (IAT 0x1006C038)
    resolved symbol   : "GetResourceManagerII"
    target module     : iips.dll (path built at 0x3BAD..0x3C3D)
    IIPS_LOAD         : STATIC_CONFIRMED
    GETRESOURCE_CALL  : STATIC_CONFIRMED
```

### I.2 Important separation

```text
IIPS_LOAD (iips.dll)          = STATIC_CONFIRMED   (LoadLibraryW at 0x3C48)
GETRESOURCE_RESOLUTION        = STATIC_CONFIRMED   (GetProcAddress at 0x3C8F)
GETRESOURCE_CALL              = STATIC_CONFIRMED   (call eax at 0x3C99)

these are three DIFFERENT facts and are NOT collapsed into one.
EVIDENCE  STATIC_DIRECT for each
```

### I.3 The path strings are built at runtime

```text
0x3BAD  call sub_119C0     ; builds a std::wstring from the module dir
0x3BD1  call sub_116E0
0x3BF4  call sub_AB70
0x3C3D  mov eax, [esp+0x50]  ; the wide buffer

and in tcls_core.exe:
0x8D2E1 call sub_8C8CF     ; builds the IIPSLaunchRestore path from
                            ;   [this+0x30], [this+0x34], [this+0x38]
                            ;   + [this+0x38] buffer
```

```text
the literal DLL name string is NOT present as a plain immediate;
the paths are composed at runtime.

therefore the target DLL identity is inferred from:
  1. the resolved symbol names ("GetResourceManagerII" ->
     iips.dll, per its export table),
  2. the error string "[...][IIPSRESTORE_LOADIIPSDLLFAILED]",
  3. the error string "[...][IIPSRESTORE_GETIIPSRESOURCEMANAGERFAILED]",
  4. the function name CallBackThread::StartLauchRestore.

classification: the SYMBOL is STATIC_DIRECT;
                the DLL PATH ARGUMENT is STATIC_INDIRECT.
```

---

## J. Native Bootstrap Relation

### J.1 What was checked

```text
candidate modules examined for a connection to the known CODOL native
bootstrap chain:
    codoMP_client_shipRetail.exe
    codoMP_client_shipRetailBase.dll
    WeGame\tcls\tcls_core.exe
    IIPSLaunchRestore.dll

known native bootstrap addresses searched as 4-byte immediates:
    0x77F580  0x77F8B3  0x4FD9B0  0x4FCEE0
    0x808650  0x7E98F0  0x6212C0
```

### J.2 Import-table check

| module | imports | exports |
|---|---|---|
| `codoMP_client_shipRetail.exe` | `codoMP_client_shipRetailBase.dll` (1) | 22 Scaleform `System`/`AcquireInterface` symbols |
| `codoMP_client_shipRetailBase.dll` | `kernel32.dll`, `libcef.dll` (2) | 0 |
| `tcls_core.exe` | PSAPI, RPCRT4, VERSION, **common.dll**, KERNEL32, USER32, SHELL32, ADVAPI32, SHLWAPI, WS2_32, WINMM, ole32 (12) | 0 |
| `IIPSLaunchRestore.dll` | KERNEL32, USER32, SHELL32, ole32, OLEAUT32, SHLWAPI, WS2_32 (7) | `CreateIIPSRepair`, `RealeaseIIPSRepair` (2) |

```text
NONE of the four modules imports any of the others at the manager level,
NONE has an import entry that connects the iips family to the EXE, and
NONE contains the known native bootstrap addresses as immediates.
EVIDENCE  STATIC_DIRECT
```

### J.3 Why the two halves cannot be joined statically

```text
HALF 1 (now closed):
    tcls_core.exe
      -> LoadLibraryW(IIPSLaunchRestore.dll)     0x8D353
      -> GetProcAddress("CreateIIPSRepair")      0x8D38A
      -> call CreateIIPSRepair()                 0x8D39F
      -> IIPSLaunchRestore.dll
           -> LoadLibraryW(iips.dll)             0x3C48
           -> GetProcAddress("GetResourceManagerII") 0x3C8F
           -> call GetResourceManagerII()        0x3C99
           -> manager* -> slot 26 -> slot 1 -> sub_197F0 -> CNIFS

HALF 2 (existing CODOL native bootstrap):
    codoMP_client_shipRetail.exe
      -> codoMP_client_shipRetailBase.dll
      -> native bootstrap dispatcher at 0x77F580 etc.

The EXE never references GetResourceManagerII by a plain instruction and
never imports iips.dll.  tcls_core.exe is a separate WeGame/TCLS process
binary with its own 12-import set and no reference to the CODOL EXE.

=> no CALL, no function pointer, no vtable, no import, and no dataflow
   node joins HALF 1 to HALF 2 in the static image.
```

### J.4 Result

```text
STATIC_BOOTSTRAP_LINK = EXTERNAL_BOUNDARY

the boundary is the process-level / launcher-level relation between
tcls_core.exe (TCLS) and codoMP_client_shipRetail.exe.  That relation is
not expressed in the binary import graph of either module.
EVIDENCE  STATIC_DIRECT for "no link exists in the image";
          EXTERNAL_BOUNDARY for the unresolved relation
```

### J.5 What is NOT claimed

```text
NOT claimed:
  - that tcls_core.exe IS running during a normal -q launch
  - that CreateIIPSRepair IS called
  - that IIPSLaunchRestore.dll IS loaded
  - that iips.dll IS loaded by it
  - that GetResourceManagerII IS called
  - that manager slot 26 / slot 1 IS dispatched
  - that sub_197F0 or CNIFS::InitInGameApp or LoadLibraryW(ifs2.dll)
    IS executed

Each of these remains a RUNTIME fact.
```

---

## K. External Boundaries

```text
K1  the WeGame/TCLS launcher that hosts tcls_core.exe
      MODULE   : outside the CODOL binary set (WeGame installation)
      FUNCTION : unknown
      RVA      : n/a
      KIND     : process/launcher boundary
      EVIDENCE : EXTERNAL_BOUNDARY

K2  the runtime-built LoadLibraryW argument in tcls_core.exe
      MODULE   : tcls_core.exe
      FUNCTION : sub_8D2A2
      RVA      : 0x8D353
      ARGUMENT : built at 0x8D2E1 from [this+0x30], [this+0x34], [this+0x38]
      KIND     : LoadLibraryW (dynamic import)
      REACHED  : STATIC_DIRECT
      TARGET   : resolved at runtime; symbol "CreateIIPSRepair" confirms
                 IIPSLaunchRestore.dll
      EVIDENCE : STATIC_DIRECT for the call, STATIC_INDIRECT for the path

K3  the runtime-built LoadLibraryW argument in IIPSLaunchRestore.dll
      MODULE   : IIPSLaunchRestore.dll
      FUNCTION : sub_3AF0
      RVA      : 0x3C48
      ARGUMENT : built at 0x3BAD..0x3C3D (std::wstring)
      KIND     : LoadLibraryW (dynamic import)
      REACHED  : STATIC_DIRECT
      TARGET   : symbol "GetResourceManagerII" confirms iips.dll
      EVIDENCE : STATIC_DIRECT for the call, STATIC_INDIRECT for the path

K4  the CreateIFSLibDll export inside ifs2.dll
      (from EX-060; unchanged this round)
      EVIDENCE : EXTERNAL_BOUNDARY

K5  the whole load order tcls_core -> IIPSLaunchRestore -> iips
      depends on file presence and the TCLS configuration; it is not
      forced by any static link.
      EVIDENCE : EXTERNAL_BOUNDARY
```

### K.1 The single remaining boundary, stated precisely

```text
MODULE     : WeGame TCLS launcher (host of tcls_core.exe)
FUNCTION   : the code that creates the object whose entry reaches
             sub_8D2A2 in tcls_core.exe
RVA        : UNKNOWN (outside the analysed CODOL binary set)
IMPORT     : none
EXPORT     : none used
IAT        : none
GetProcAddr: none

the first RECOVERED node is:
    tcls_core.exe  sub_8D2A2  @ 0x8D353   LoadLibraryW
```

---

## L. STATIC_UNKNOWN

```text
L01  Which process/module starts tcls_core.exe and drives sub_8D2A2.
L02  The exact runtime string passed to LoadLibraryW at 0x8D353.
L03  The exact runtime string passed to LoadLibraryW at 0x3C48.
L04  Whether IIPSRestoreManager::BeginIIPSRepair / the CallBackThread
     is actually started in a normal -q launch.
L05  The semantics of manager slot 26 (sub_178F0).
L06  The semantics of manager slot 1 when called with a string argument
     ("http://localhost") from IIPSLaunchRestore.dll, as opposed to the
     internal call from sub_1A270.
L07  Whether [CallBackThread+0xA8] and iips.dll![0x1004EB68] are equal
     at runtime (only the code paths are proven, not the values).
L08  Whether sub_7430 and sub_3AF0 both run, or only one.
L09  What the EXE does with its packed .tp3 copy of the string
     "GetResourceManagerII" (no plain instruction references it).
L10  Whether codoMP_client_shipRetailBase.dll (the EXE's only import)
     reaches the iips family by any indirect route.
L11  The meaning of the error code 0xE0000003 written at 0x3C6B.
L12  Whether the TCLS chain is active during a normal game launch, or
     only during repair / pre-download flows.
L13  The contents of the CallBackThread object (its 0xA8/0xAC fields are
     proven; the rest was not reconstructed).
L14  Whether any third path resolves GetResourceManagerII that the
     import/string scan could not see (e.g. names built at runtime).
```

---

## Q1 - Q7 Answers

### Q1

> 哪些模块 import `GetResourceManagerII`？

```text
NONE.

   normal import   : 0 modules
   delay import    : 0 modules
   export (self)   : 1 module (iips.dll)
   dynamic resolve : 1 module (IIPSLaunchRestore.dll) via GetProcAddress

scan scope: 6072 PE files in the CODOL working tree.
EVIDENCE  : STATIC_DIRECT
```

### Q2

> 实际 caller 是哪些函数？

```text
MODULE    : IIPSLaunchRestore.dll
FUNCTION  : sub_3AF0   (CallBackThread::StartLauchRestore)
RVA       : 0x3C99
BB        : 0x3C89 .. 0x3C9B
INSN      : call eax          ; eax = GetProcAddress(hMod, "GetResourceManagerII")

MODULE    : IIPSLaunchRestore.dll
FUNCTION  : sub_7430
RVA       : 0x745F
BB        : 0x744F .. 0x7461
INSN      : call eax

MODULE    : (none)  -- the EXE does not have a recoverable caller
STATUS    : PACKED_CALLER_UNRESOLVED

EVIDENCE  : STATIC_INDIRECT for the calls;
            STATIC_DIRECT for the surrounding GetProcAddress and stores.
```

### Q3

> `GetResourceManagerII` 返回的 manager* 如何传播？

```text
0x3C99  call eax                       EAX = manager*
0x3C9F  cmp eax, edi                   NULL test
0x3CA1  mov [esi+0xA8], eax            store into CallBackThread+0xA8
0x3CAD  mov ecx, [esi+0x20]
0x3CB0  mov edx, [eax]                 manager->vtable
0x3CB2  mov edx, [edx+0x68]            slot 26
0x3CB6  mov ecx, eax                   this = manager*
0x3CB8  call edx
0x3CD4  mov ecx, [esi+0xA8]            reload manager*
0x3CDC  mov edx, [eax+4]               slot 1
0x3CE4  call edx

and inside iips.dll the SAME value is also stored at [0x1004EB68]
by the factory itself (0x1CD9).

CLASSIFICATION of the propagation: STATIC_INDIRECT
   (the pointer travels through a call return and a struct field)
```

### Q4

> 是否能连接：`GetResourceManagerII -> manager slot 5 -> sub_1A270`？

```text
NO.

The foreign consumer dispatches slot 26 (+0x68) and slot 1 (+0x04).
It never dispatches slot 5 (+0x14).

   IIPSLaunchRestore.dll slot fetches on the manager:
      0x3CB2  [edx+0x68]  slot 26   STATIC_DIRECT
      0x3CDC  [eax+0x04]  slot  1   STATIC_DIRECT
      0x7478  [edx+0x68]  slot 26   STATIC_DIRECT
      0x7488  [eax+0x04]  slot  1   STATIC_DIRECT

slot 5 (sub_1A270) is reached only from INSIDE iips.dll, and its own
body then dispatches slot 1 of a NESTED manager at [this+0x19C].
EVIDENCE  : STATIC_DIRECT for the negative result.
```

### Q5

> 是否能继续连接：`sub_1A270 -> manager slot 1 -> sub_197F0`？

```text
The internal half is unchanged from EX-063 and remains valid:

    sub_1A270 (manager slot 5)
      0x1A2FC  mov ecx, [esi+0x19C]
      0x1A302  mov eax, [ecx]
      0x1A304  mov edx, [eax+4]
      0x1A309  call edx                -> sub_197F0

EX-064 adds an EXTERNAL route to the SAME target:

    IIPSLaunchRestore.dll
      0x3C99  call GetResourceManagerII()      -> manager*
      0x3CDC  mov edx, [eax+4]                 slot 1
      0x3CE4  call edx                         -> sub_197F0

  and the second site:

      0x745F  call GetResourceManagerII()
      0x7488  mov edx, [eax+4]                 slot 1
      0x7490  call edx                         -> sub_197F0

So sub_197F0 IS reachable from the external caller directly through
slot 1, WITHOUT passing through slot 5 / sub_1A270.

EVIDENCE  : STATIC_DIRECT (slot values) + STATIC_INDIRECT (calls)
```

### Q6

> external caller 能否连接到已知 native bootstrap？

```text
NOT with the static evidence from this binary set.

   the four candidate modules have no mutual import link at the manager
   level, do not contain the known bootstrap addresses as immediates,
   and the EXE's copy of "GetResourceManagerII" is unreferenced
   packed .tp3 data.

   the two halves are:

      tcls_core.exe -> IIPSLaunchRestore.dll -> iips.dll -> CNIFS
      codoMP_client_shipRetail.exe -> Base.dll -> native bootstrap

   and nothing in the static image joins them.

STATIC_BOOTSTRAP_LINK = EXTERNAL_BOUNDARY
EVIDENCE              : STATIC_DIRECT (no link exists in the image)
```

### Q7

> 如果无法跨越，最后一个无法跨越的边界在哪里？

```text
MODULE     : the WeGame TCLS launcher that hosts tcls_core.exe
FUNCTION   : the caller of tcls_core.exe's sub_8D2A2
             (the code that drives LoadLibraryW at 0x8D353)
RVA        : UNKNOWN (outside the analysed CODOL binary set)
IMPORT     : none
EXPORT     : none
IAT        : none
GetProcAddr: none

the last RECOVERED node is:
    tcls_core.exe  sub_8D2A2  @ 0x8D353   KERNEL32!LoadLibraryW
                                          (argument built at 0x8D2E1)
EVIDENCE   : EXTERNAL_BOUNDARY
```

---

## Final Status

```text
GETRESOURCE_EXPORT             = STATIC_CONFIRMED  (iips.dll RVA 0x1C80)
GETRESOURCE_IMPORTERS          = NONE              (0 of 6072 PE files)
GETRESOURCE_CALLERS            = STATIC_CONFIRMED  (IIPSLaunchRestore.dll
                                                    0x3C99 and 0x745F)
GETRESOURCE_RETURN_DATAFLOW    = STATIC_INDIRECT   (EAX -> [this+0xA8])
MANAGER_SINGLETON              = STATIC_CONFIRMED  ([0x1004EB68])
MANAGER_SLOT5                  = STATIC_CONFIRMED  (but NOT used by the
                                                    external consumer)
MANAGER_SLOT26                 = STATIC_CONFIRMED  (used by the external
                                                    consumer -> sub_178F0)
MANAGER_SLOT1                  = STATIC_CONFIRMED  (used by the external
                                                    consumer -> sub_197F0)
SUB197F0                       = STATIC_CONFIRMED
CNIFS_LIFECYCLE                = CLOSED_INSIDE_IIPS

IIPS_ACQUISITION               = STATIC_CONFIRMED  two-stage dynamic:
                                   tcls_core.exe   -> LoadLibraryW
                                   IIPSLaunchRestore.dll -> LoadLibraryW
NATIVE_BOOTSTRAP_LINK          = EXTERNAL_BOUNDARY

RUNTIME_GETRESOURCE_CALL       = UNKNOWN
RUNTIME_INITINGAMEAPP          = UNKNOWN
RUNTIME_IFS2_LOAD              = UNKNOWN
RUNTIME_CREATEIFS              = UNKNOWN
RUNTIME_FIRST_FAILURE          = UNKNOWN
```

## Final Classification

```text
EX064_GETRESOURCEMANAGER_CALLERS

EXPORT_DEFINITION_CONFIRMED        STATIC_DIRECT
IMPORT_SCAN_ALL_MODULES            STATIC_DIRECT (6072 files)
GETRESOURCE_IMPORT_COUNT_ZERO      STATIC_DIRECT
DYNAMIC_RESOLVE_FOUND              STATIC_DIRECT (IIPSLaunchRestore.dll)
EXTERNAL_CALLER_RECOVERED          STATIC_DIRECT (0x3C99, 0x745F)
RETURN_VALUE_DATAFLOW_RECOVERED    STATIC_INDIRECT
MANAGER_CONSUMER_SLOTS_RECOVERED   STATIC_DIRECT (slot 26, slot 1)
SLOT5_HYPOTHESIS_CORRECTED         STATIC_DIRECT
TWO_STAGE_IIPS_ACQUISITION_FOUND   STATIC_DIRECT
TCLS_ENTRY_FOUND                   STATIC_DIRECT (tcls_core.exe 0x8D39F)
BOOTSTRAP_LINK                     EXTERNAL_BOUNDARY

RUNTIME_GETRESOURCE_CALL           UNKNOWN
RUNTIME_INITINGAMEAPP              UNKNOWN
RUNTIME_IFS2_LOAD                  UNKNOWN
RUNTIME_CREATEIFS                  UNKNOWN
RUNTIME_FIRST_FAILURE              UNKNOWN

NO_PATCH
NO_BYPASS
NO_FAKE_SUCCESS
NO_DEBUGGER_ATTACH
NO_API_HOOKING
NO_FRIDA
NO_ETW_API_TRACING
NO_RUNTIME_INJECTION
NO_IAT_MODIFICATION
NO_EXPORT_MODIFICATION
NO_VTABLE_MODIFICATION
NO_DYNAMIC_CONFIRMED
```

## Verification Artifacts

```text
ex064_import_map.csv          12 rows: definitions, negatives, acquisitions
ex064_getres_callers.csv      14 rows: every resolution and call site
ex064_manager_consumers.csv   14 rows: what the consumer does with manager*
ex064_bootstrap_edges.csv     11 rows: bootstrap edge classification
ex064_dynamic_getproc.csv      6 rows: all dynamic GetProcAddress sites
ex064_iips_acquisition.csv     4 rows: LoadLibrary/GetProcAddress chain
ex064_import_map.txt                 : full 6072-file scan output
ex064_strings.txt                    : EXE vs IIPSLaunchRestore strings
ex064_restore_gpa.txt                : restore-module resolution sites
ex064_gpa_sites.txt                  : disassembly of the four sites
ex064_slot68.txt                     : the slot-26 finding
ex064_manager_use.txt                : [X+0xA8] consumer analysis
ex064_tcls.txt / ex064_tcls_gpa.txt  : the TCLS external entry
ex064_bootstrap_check.txt            : no link to native bootstrap
```
