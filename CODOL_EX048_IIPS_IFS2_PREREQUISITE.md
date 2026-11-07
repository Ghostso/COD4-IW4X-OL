# EX-048 IIPS → IFS2 Prerequisite and First Blocking Condition

## Final Classification

```text
IFS2_STATIC_READINESS_CONFIRMED
IIPS_IFS2_RESOLUTION_UNCONFIRMED
CREATE_IFS_EXECUTION_UNCONFIRMED
8189FEC_IFS2_CAUSALITY_UNCONFIRMED
IIPS_FIRST_PREREQUISITE_UNRESOLVED
IIPS_GATE_NOT_CROSSED
NEW_EXECUTION_NODE_NONE
TENCENT_LAUNCHER_NOT_REQUIRED
NO_TVM0_DEPENDENCY_IN_RECOVERED_TEXT
```

`IFS2.dll` exists and exports `CreateIFSLibDll` / `DestoryIFSLibDll`.
`iips.dll` statically references those exports through
`GetProcAddress`-style code, but during normal `-q` runs `IFS2.dll` was
not observed in the module list. No path proves that `8189FEC` is caused
by `CreateIFSLibDll` failure.

## Method

Unattended observation:

```text
prepare independent copy
launch -q
auto wait for dialog
enumerate modules
record popup
terminate
```

No debugger, no patches, no human click.

## IFS2 Inventory

Path:

```text
COD OL/IIPS/IFS2.dll
```

Archive:

```text
SHA256 = 5B0324E0B2BA3545A6C02626287D4FBC6A3116594744F4647333982D85508421
PE32 x86
ImageBase = 0x10000000
Entry = 0x51A94
```

Sections:

```text
.text  0x1000 size 0x763C0
.rdata 0x78000 size 0xFC DA
.data  0x88000 size 0x71C4
.rsrc  0x90000 size 0x3E8
.reloc 0x91000 size 0x4786
```

Exports:

```text
0x166D0 CreateIFSLibDll
0x16740 DestoryIFSLibDll
0x16760 IFSDllVerifyApiCompatable
```

Imports:

```text
KERNEL32.dll
ADVAPI32.dll
SHLWAPI.dll
```

No delay imports were observed.

## `iips.dll` IFS2 Call Shape

The relevant code in `iips.dll`:

```asm
0x10009770  mov esi, [0x10033014] ; GetProcAddress
0x10009776  push 0x10034964       ; "CreateIFSLibDll"
0x1000977b  push eax
0x1000977c  call esi
0x1000977e  test eax, eax
0x10009780  mov [ebp+0x58], eax
0x10009783  jne 0x100097a1
...
0x10009785  push 0x10034974       ; "Failed to get function CreateIFSLibDll"
```

If resolution succeeds:

```asm
0x100097a1  lea ecx, [ebp+0x50]
0x100097a4  push ecx
0x100097a5  call eax             ; call CreateIFSLibDll
0x100097a7  test eax, eax
0x100097a9  mov [ebp+0x60], eax
0x100097ac  jne 0x100097c3
```

If creation fails:

```text
[CNIFS::initIfsLib()][Failed to create ifs lib]
```

Then `DestoryIFSLibDll` is resolved separately; if that fails:

```text
[CNIFS::initIfsLib()][Failed to get proc DestoryIFSLibDll]
```

This is L2 static dataflow inside `iips.dll`.

## Runtime Module Observation

During `-q` fatal dialog:

```text
TenRpcs.dll loaded
GameRpcs.dll loaded
tcj.dll loaded
policyprobe.dll loaded
TenProxy.dll loaded
GbSpy.dll loaded
iips.dll loaded       0x12B80000
IFS2.dll NOT OBSERVED
```

No `IIPSHostApp.exe` process observed.

Interpretation:

```text
IFS2 was not observed loaded.
not observed != resolve failed
not observed can mean not attempted or loaded through alternate mechanism.
```

## `8189FEC` Causality

Possible classes:

```text
A = CreateIFSLibDll resolution failure
B = CreateIFSLibDll execution failure
C = another IFS2 prerequisite
D = another IIPS prerequisite
E = CODOL-side conversion of IIPS error
F = runtime-generated packed status
G = unresolved
```

Classification:

```text
G = UNRESOLVED
```

No plaintext constant was found and no runtime evidence ties `8189FEC` to
`CreateIFSLibDll`.

## Local Prerequisite Candidate

`IFS2.dll` is statically ready:

```text
IFS2_STATIC_READINESS_CONFIRMED
```

No missing import or missing export was found for IFS2 static loading.
It was not observed loaded at runtime, so the next question is whether
`iips.dll` reaches its `LoadLibraryW` / `let`-star of IFS2 before failing
at another earlier prerequisite.

## Answers

1. IFS2 exists: yes, `COD OL/IIPS/IFS2.dll`.
2. IFS2 structurally complete: yes by PE/export/import inspection.
3. `CreateIFSLibDll` exists: yes.
4. `DestoryIFSLibDll` exists: yes.
5. How IIPS loads IFS2: static evidence is `GetProcAddress("CreateIFSLibDll")` after a loader handle; exact DLL handle source is not fully reconstructed.
6. How IIPS resolves exports: via `GetProcAddress`; failure strings show distinct branches.
7. Parameters: not fully reconstructed; one stack object at `[ebp+0x50]` is passed to `CreateIFSLibDll`.
8. Did runtime enter IFS2: not observed loaded.
9. If failure, where: unresolved; not attributable to IFS2 export list.
10. L2/L3/L4 causality to `8189FEC`: no.
11. Supplying missing prerequisite produced new node: no missing prerequisite was proven.
12. Next IIPS prerequisite: unresolved.

## Final

```text
IFS2_STATIC_READINESS_CONFIRMED
IIPS_IFS2_RESOLUTION_UNCONFIRMED
CREATE_IFS_EXECUTION_UNCONFIRMED
8189FEC_IFS2_CAUSALITY_UNCONFIRMED
IIPS_FIRST_PREREQUISITE_UNRESOLVED
IIPS_GATE_NOT_CROSSED
NEW_EXECUTION_NODE_NONE
```
