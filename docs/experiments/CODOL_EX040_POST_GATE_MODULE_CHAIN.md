# EX-040 Post-Gate Project Module Chain and IIPS Upstream Dependency

## Final Classification

```text
POST_GATE_MODULE_CHAIN_RECONSTRUCTED
IIPS_UPSTREAM_EXECUTION_UNCONFIRMED
IIPS_CAUSALITY_UNRESOLVED
NO_NEW_EXECUTION_NODE
```

Normal direct `-q` startup from an independent copy produced a stable
module first-seen order. `iips.dll` loads after `TenProxy.dll` /
`GbSpy.dll`, immediately before the `WIN_IIPS_INIT_ERROR` dialog. No
plain PE import/export edge or static dataflow from another project
module to `iips.dll` was found, so this is load-order evidence, not
causality.

## Method

```text
independent copy   : 工具/EX035_DIR
command line       : codoMP_client_shipRetail.exe -q
current directory  : 工具/EX035_DIR
observer           : Toolhelp module/thread/window polling, no API hook,
                     no debugger, no memory write
```

Repeated runs produced consistent first-seen module order.

## Module First-Seen Order

Representative run:

```text
T+0.082  libcef.dll
T+0.417  BugTrace.dll
T+1.521  VSDDrvDll.dll
T+2.358  ACE-DRV32.dll
T+3.030  tersafe.dll
T+3.975  TenRpcs.dll
T+5.755  GameRpcs.dll
T+5.839  GDPLoader.dll
T+5.839  tcj.dll
T+5.839  GameDataPlatformServer.dll
T+6.173  policyprobe.dll
T+6.173  ace-ats32.dll
T+6.173  gcloudvoice.dll
T+6.426  TenProxy.dll
T+6.426  GbSpy.dll
T+7.615  iips.dll
```

Timestamps are first-seen sampling times, not exact loader call times.

## Last Non-IIPS Module Before iips.dll

```text
TenProxy.dll
GbSpy.dll
```

Both first appeared together at `T+6.426` in the representative run. They
are the last project modules observed before `iips.dll`.

## Thread Creation Cluster

Thread first-seen times cluster before and at the IIPS window:

```text
T+6.511  new thread cluster
T+7.706  new thread cluster at same sample as iips.dll
```

Thread start addresses could not be obtained with non-elevated
`NtQueryInformationThread`; therefore the module responsible for each
new thread is not proven.

## Observed UI

```text
#32770  fatal dialog
iipsinit  Environment List Box
```

The `iipsinit` window appears at the same stage as `iips.dll` load.

## Static Dependency Scan

Plain PE import/export scan of loaded project modules:

```text
module                 imports                     exports
TenProxy.dll           CRYPT32/MSVCP60/KERNEL32/... Invoke
GbSpy.dll              SHELL32/VERSION/WS2_32/...  none
TenRpcs.dll            WINHTTP/SETUPAPI/WS2_32/... NullExportFunction
GameRpcs.dll           KERNEL32/WS2_32/CRYPT32/... InitGameRpcs
tcj.dll                USERENV/WS2_32/ntdll/...    CreateObject
policyprobe.dll        WINHTTP/RASAPI32/WS2_32/... CreateObject
GDPLoader.dll          WINHTTP/SHLWAPI/WS2_32/...  InitGdp
GameDataPlatformServer KERNEL32/WS2_32/SHLWAPI/... GDP_manager
ACE-DRV32.dll          WS2_32/WINMM/...            CreateObject
tersafe.dll            WS2_32/WINMM/...            CreateObj/DllEntry*
VSDDrvDll.dll          SHLWAPI/WS2_32/...          CreateVSDIDrvObj
```

None of these import `iips.dll` or contain plaintext `iips.dll`
references.

`iips.dll` imports:

```text
KERNEL32, USER32, ADVAPI32, SHELL32, ole32, OLEAUT32,
MSVCP80, SHLWAPI, VERSION, WS2_32, MSVCR80, WSOCK32
```

It exports:

```text
GetResourceManager
GetResourceManagerII
ReleaseResourceManager
ReleaseResourceManagerII
```

No plain PE edge from a loaded project module to `iips.dll` was found.

## Loader Candidate Status

```text
plain .text reference to iips.dll from project module: NONE
PE import of iips.dll from project module: NONE
export/import dependency between project modules and iips.dll: NONE
L2 loader dataflow: NONE
```

The `iips.dll` loader is therefore still in packed EXE/Base code or a
dynamic resolver outside plain PE metadata.

## `0x8189FEC`

Searched as little-endian 32-bit and reversed bytes in:

```text
EXE, Base.dll, iips.dll, TenProxy.dll, GbSpy.dll, TenRpcs.dll,
GameRpcs.dll, tcj.dll, PolicyProbe.dll, GDPLoader.dll,
GameDataPlatformServer.dll, ACE-DRV32.dll, TerSafe.dll,
VSDDrvDll.dll, libcef.dll, BugTrace.dll
```

No hits. Classification remains:

```text
8189FEC_PACKED_OR_VM_GENERATED
```

## Answers

1. Complete project DLL load order after `-q`: captured above; `iips.dll` is last before the fatal UI in the observed runs.
2. Last verifiable project module before `iips.dll`: `TenProxy.dll` / `GbSpy.dll`.
3. New external loader/init caller evidence for `iips.dll`: none.
4. New source evidence for `8189FEC`: none.
5. New L3/L4 execution node: none; module load and thread-creation timing only.
6. If no new node, stop IIPS direction: yes; this report closes with no new IIPS upstream node.

## Final

```text
POST_GATE_MODULE_CHAIN_RECONSTRUCTED
IIPS_UPSTREAM_EXECUTION_UNCONFIRMED
IIPS_CAUSALITY_UNRESOLVED
NO_NEW_EXECUTION_NODE
```
