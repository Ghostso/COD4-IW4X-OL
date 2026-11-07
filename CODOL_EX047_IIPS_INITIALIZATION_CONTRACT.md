# EX-047 IIPS Initialization Contract and `8189FEC` Source Reconstruction

## Final Classification

```text
IIPS_DEPENDENCY_GRAPH_RECONSTRUCTED
IIPS_INITIALIZATION_STATE_PARTIAL
8189FEC_SOURCE_UNRESOLVED
FIRST_IIPS_PREREQUISITE_UNRESOLVED
IIPS_GATE_NOT_CROSSED
NEW_EXECUTION_NODE_NONE
TENCENT_LAUNCHER_NOT_REQUIRED
NO_TVM0_DEPENDENCY_IN_IIPS_TEXT
```

The IIPS failure is still reached only in the `-q` / `-qa` post-gate
path. `iips.dll` is loaded, but `8189FEC` remains
`PACKED_OR_RUNTIME_GENERATED`; no exact plaintext constant was found in
the relevant binaries.

## Method

No human clicks, no debugger, no IIPS patch.

Automatic normal-run observation used:

```text
CreateProcess with -q / -qa
window enumeration and popup child controls
module timeline capture
static PE/string/reference scan
```

All runs came from the independent copy `工具/EX035_DIR`.

## IIPS Location in Native Bootstrap

Observed after:

```text
TenProxy.dll
GbSpy.dll
```

And immediately before:

```text
iipsinit Environment List Box
WIN_IIPS_INIT_ERROR / 8189FEC
```

This is load-order/temporal evidence, not causal proof.

## `iips.dll` PE Inventory

```text
sections:
  .text   0x1000 size 0x31C3B
  .rdata  0x33000 size 0xEC81
  .data   0x42000 size 0xCB94
  .rsrc   0x4F000 size 0x4E8
  .reloc  0x50000 size 0x4C3E

exports:
  GetResourceManager
  GetResourceManagerII
  ReleaseResourceManager
  ReleaseResourceManagerII
```

Important imports:

```text
KERNEL32:
  LoadLibraryW
  GetProcAddress
  CreateThread
  CreateFileA/W
  GetPrivateProfileStringW
  WritePrivateProfileStringW
  CreateFileMappingA
  OpenFileMappingA/W
  MapViewOfFile
  CreateMutexA
  OpenMutexW
  CreateEventA/W
  SetEvent
  OpenProcess

USER32:
  CreateWindowExA

VERSION.dll:
  GetFileVersionInfoW

MSVCR80:
  _beginthreadex
  _endthreadex
```

No delay imports were observed.

## `iips.dll` Strings

```text
IIPSHostApp.exe          6 hits
CreateIFSLibDll          2 hits
IIPSERR_CACHE_INIT       1 hit
IIPSERR_ERROR_INIT      38 hits
LaunchIIPSHostApp failed  2 hits
Global\IIPSShareState_MMF_
Global\IIPSShareState_Mutex_
```

Also visible in `.rdata`:

```text
IIPS/IIPSHostApp.ini
IIPS/IIPSHostApp.exe
IFS2/
ifs2.dll
```

Presence is string-level evidence only; it does not prove runtime use.

## IFS2 Dependency Path

Inside `iips.dll`, `CNIFS::initIfsLib`-style logic references:

```text
ifs2.dll
CreateIFSLibDll
DestoryIFSLibDll
```

`CreateIFSLibDll` is resolved through `GetProcAddress`-style code:

```asm
0x10009770  mov esi, [0x10033014]          ; GetProcAddress
0x10009776  push 0x10034964                ; "CreateIFSLibDll"
0x1000977b  push eax
0x1000977c  call esi
0x1000977e  test eax, eax
...
```

If resolution fails:

```text
[CNIFS::initIfsLib()][Failed to get function CreateIFSLibDll]
```

If creation fails:

```text
[CNIFS::initIfsLib()][Failed to create ifs lib]
```

If destroy-proc resolution fails:

```text
[CNIFS::initIfsLib()][Failed to get proc DestoryIFSLibDll]
```

This is a concrete L2 IFS2 prerequisite path inside `iips.dll`.

## HostApp Lazy/Loaded Evidence

`IIPSHostApp.exe` strings exist in `iips.dll`, but `IIPSHostApp.exe` was
not observed as a process in normal `-q` runs.

Possible explanations:

```text
1. HostApp is lazy-loaded only after earlier prerequisites succeed
2. failure occurs before launch branch
3. HostApp path is encoded as a string but not reached in current run
```

No direct code path from `8189FEC` to HostApp was found. No process-state
or IPC evidence was observed.

## `8189FEC` Search

Searched binary forms:

```text
0x8189FEC
0x8189FD
0x8189FE
0x8189FF
0x8189FC
```

Across:

```text
EXE
Base.dll
iips.dll
IFS2.dll
IIPSHost.dll
IIPSCheck.dll
IIPSVFS.dll
IIPSHostApp.exe
```

No exact plaintext constant was found.

```text
8189FEC = PACKED_OR_RUNTIME_GENERATED
```

No reverse-engineering of `.tvm0` was performed.

## Baseline `-q` Run

POPUP:

```text
Title : 致命错误
Class : #32770
Text  : 初始化IIPS错误：8189fec。
Button: 确定
```

Modules:

```text
libcef
BugTrace
VSDDrvDll
ACE-DRV32
tersafe
TenRpcs
GameRpcs/GDPLoader/tcj
GameDataPlatformServer
policyprobe/ace-ats32/gcloudvoice
TenProxy/GbSpy
iips.dll
```

No IIPSHostApp process observed.

## Dependency Matrix

| Item | Static present | Loaded/observed | Hard dependency | Evidence |
| --- | --- | --- | --- | --- |
| WeGame | YES | NO | NO | L3 normal absent |
| TCLS Client.exe | YES | NO | NO | L3 absent |
| tcls_core | YES | NO | NO | L3 absent |
| TCLS.dll | YES | NO | NO | L3 absent |
| TCLS shared memory | string | NO | NO | L3 absent |
| TenProxy.dll | YES | YES | not proven | L3 load |
| GbSpy.dll | YES | YES | not proven | L3 load |
| `iips.dll` | YES | YES | blocker | L3 load + fatal |
| IFS2.dll | YES | not observed | unknown | L2 references |
| IIPSHostApp.exe | YES | NO | unknown | L2 strings |

## First IIPS Prerequisite

```text
FIRST_IIPS_PREREQUISITE_UNRESOLVED
```

Possible candidates from L2 evidence:

```text
IIFS2/IFS2.dll loading / CreateIFSLibDll
IIPSHostApp.exe startup / IPC
IIPS shared memory/mutex setup
```

No candidate was proven to fail first.

## Single-Variable Experiments

No new variable was added this round. Existing matrix:

```text
baseline        -> WIN_NO_TCLS
-q              -> IIPS fatal
-qa             -> IIPS fatal
-q -src=tgp     -> IIPS fatal
-qa -src=tgp    -> IIPS fatal
```

No tested variable crossed the IIPS gate.

## Answers

1. IIPS appears after network/bootstrap module loads and before fatal.
2. Who loads it: unproven; static loader caller unresolved.
3. Actual dependencies: L2 candidates are IFS2 and HostApp-related paths.
4. Hard dependencies: none proven; IIPS init itself is the observed blocker.
5. Historical/optional: WeGame/TCLS launcher stack.
6. Why HostApp absent: unresolved; likely lazy/unreached before fatal.
7. `8189FEC` source: unresolved, packed/runtime-generated.
8. First failing prerequisite: unresolved.
9. Can it be crossed by local condition: not demonstrated.
10. New node after crossing: none.
11. Tencent launcher still not required: YES.
12. Minimal verified context: full copy + `-q` / `-qa`; reaches IIPS fatal.

## Final

```text
IIPS_DEPENDENCY_GRAPH_RECONSTRUCTED
IIPS_INITIALIZATION_STATE_PARTIAL
8189FEC_SOURCE_UNRESOLVED
FIRST_IIPS_PREREQUISITE_UNRESOLVED
IIPS_GATE_NOT_CROSSED
NEW_EXECUTION_NODE_NONE
TENCENT_LAUNCHER_NOT_REQUIRED
```
