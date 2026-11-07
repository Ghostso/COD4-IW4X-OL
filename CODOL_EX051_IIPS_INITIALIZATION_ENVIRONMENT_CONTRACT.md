# EX-051 IIPS Initialization Environment Contract / IIPS 初始化环境合约与状态图

## Final Classification

```text
IIPS_INIT_ENTRY_CANDIDATE
IIPS_ENVIRONMENT_CONTRACT_PARTIAL
IIPS_EXTERNAL_API_L2_CONFIRMED
IIPS_LOAD_DLL_FAILURE_BRANCH_L2_CONFIRMED
IIPS_HOSTAPP_LAUNCH_BRANCH_L2_CONFIRMED
IIPS_SHARED_STATE_CONTRACT_PARTIAL
IIPS_CACHE_INIT_BRANCH_UNRESOLVED
IIPS_ERROR_INIT_BRANCH_UNRESOLVED
IIPS_INIT_UI_BOUNDARY_PARTIAL
IFS2_STATIC_DEPENDENCY_CONFIRMED
IFS2_RUNTIME_EXECUTION_UNCONFIRMED
IFS2_CAUSALITY_TO_8189FEC_UNCONFIRMED
8189FEC_PACKED_OR_RUNTIME_GENERATED
IIPS_TO_EXE_ERROR_BOUNDARY_UNCONFIRMED
TVM0_BOUNDARY
OBSERVER_NO_DEBUGGER
NEW_L2_NODE_CONFIRMED
NEW_EXECUTION_NODE_NONE
TENCENT_LAUNCHER_NOT_REQUIRED
RUNTIME_OBSERVATION_VARIANT_UNRESOLVED
```

本轮完成的是 `iips.dll` 的静态环境合约恢复，而不是 IIPS 根因确认。
`CNIFS::InitInGameApp` 候选、`CNIFS::initIfsLib` 候选及其 IFS2
加载/解析/调用失败分支现在具备了普通 `.text` 的 L2 证据；
IIPSHostApp 启动也找到了静态 L2 分支。

但本轮没有获得新的 L3/L4 执行节点。`8189FEC` 的最终来源、
IIPS-to-EXE 错误边界和 IFS2 的实际失败因果仍然未确认。

## 1. 实验环境

```text
workspace       : D:\BaiduNetdiskDownload\使命召唤OL
game root       : COD OL
independent copy: 工具\EX035_DIR
analysis target : COD OL\IIPS\iips.dll
method          : PE import/export/string/static disassembly/dataflow
dynamic policy  : no debugger, no API hook, no patch, no .tvm0 analysis
```

本轮静态扫描脚本：

```text
_dyn_stage1\ex051_static_scan.py
_dyn_stage1\ex051_build_contract.py
```

## 2. File Hashes

| File | SHA256 |
| --- | --- |
| `codoMP_client_shipRetail.exe` | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| `codoMP_client_shipRetailBase.dll` | `EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20` |
| `IIPS\iips.dll` | `72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348` |
| `IIPS\IFS2.dll` | `5B0324E0B2BA3545A6C02626287D4FBC6A3116594744F4647333982D85508421` |
| `IIPS\IIPSHostApp.exe` | `B507B47A80CAF135EE95006AE1A3AD62777CB3DF8AA339EA835117A1B508F0C8` |

## 3. Normal Run Ground Truth

Historical normal-run command:

```text
codoMP_client_shipRetail.exe -q
working directory: 工具\EX035_DIR
```

Historical EX-049/EX-050 observation:

```text
TenRpcs -> GameRpcs -> tcj -> policyprobe -> TenProxy -> GbSpy
-> iips.dll loaded
-> iipsinit Environment List Box
-> WIN_IIPS_INIT_ERROR / 初始化IIPS错误：8189fec
```

The following were not observed in the final module snapshot:

```text
IFS2.dll
IIPSHostApp.exe
IIPSHost.dll
IIPSCheck.dll
IIPSVFS.dll
```

`not observed` does not mean `not loaded or not attempted`.

### EX-051 fresh non-invasive probe note

A fresh EX-051 `-q` probe captured a different first dialog:

```text
Title : 警告码(0, 20002, 86)
Class : #32770
Button: 确定
```

Raw probe logs:

```text
工具/logs/ex051_q_runtime_probe_20260917-221137.log
工具/logs/ex051_q_runtime_probe_repeat_20260917-221256.log
```

This is recorded as:

```text
RUNTIME_OBSERVATION_VARIANT_UNRESOLVED
```

The fresh probe was terminated at the first dialog, so it is not used
to overturn the earlier EX-049/EX-050 IIPS-fatal timeline. It does show
that the current runtime state can produce a pre-IIPS warning variant.
No debugger or API hook was used; this is not classified as debugger
observer divergence.

## 4. IIPS Module Timeline

| Order | Module | Runtime evidence | Role in this round |
| ---: | --- | --- | --- |
| 1 | `TenRpcs.dll` | loaded before IIPS | pre-gate module chain |
| 2 | `GameRpcs.dll` | loaded before IIPS | pre-gate module chain |
| 3 | `tcj.dll` | loaded before IIPS | pre-gate module chain |
| 4 | `policyprobe.dll` | loaded before IIPS | pre-gate module chain |
| 5 | `TenProxy.dll` | loaded before IIPS | pre-gate module chain |
| 6 | `GbSpy.dll` | loaded before IIPS | pre-gate module chain |
| 7 | `iips.dll` | L3 load in historical `-q` run | current static target |
| 8 | `IFS2.dll` | not observed | static dependency candidate |
| 9 | `IIPSHostApp.exe` | no process observed | static launch branch exists |

## 5. IIPS Initialization Candidates

### `CNIFS::InitInGameApp` candidate

```text
function candidate: 0x10009860
evidence:
  calls 0x10006d20 QoS helper at 0x100098cd
  on false, logs "[CNIFS::InitInGameApp()][Failed to init qos (true)]"
  calls 0x10009570 at 0x100099d2
  on false, returns from InitInGameApp
```

The QoS call is non-fatal at this callsite. The IFS2 initialization call
is fatal to this function when it returns false.

### `CNIFS::initIfsLib` candidate

```text
function candidate: 0x10009570
path builder uses UTF-16 "ifs2.dll"
LoadLibraryW callsite: 0x100096e9
LoadLibraryW failure branch: 0x100096f4 -> 0x100096f6
failure string reference: 0x1000970d -> 0x10034920
GetProcAddress CreateIFSLibDll: 0x1000977c
CreateIFSLibDll call: 0x100097a5
GetProcAddress DestoryIFSLibDll: 0x100097cc
```

### Other candidates

```text
0x100051f0  privilege setup helper:
            OpenProcessToken / LookupPrivilegeValueA / AdjustTokenPrivileges

0x10011930  IIPS share-state object manager:
            Global\IIPSShareState_MMF_
            Global\IIPSShareState_Mutex_
            OpenFileMappingA / CreateMutexA paths

0x10015a00  ResourceManagerII::LaunchIIPSHostApp candidate:
            ShellExecuteExW callsite 0x10015cd1
            success/failure branch around 0x10015cd7..0x10015d26

0x10001c80  exported GetResourceManagerII:
            no plaintext init caller chain recovered in this round
```

## 6. External API Callsites

| Function candidate | API/resource | Callsite | L2 observation |
| --- | --- | --- | --- |
| `0x100051f0` | `OpenProcessToken` | `0x10005208` | `test eax,eax`; failure branch |
| `0x100051f0` | `LookupPrivilegeValueA` | `0x10005227` | `test eax,eax`; failure branch |
| `0x100051f0` | `AdjustTokenPrivileges` | `0x10005260` | result/`GetLastError` branch |
| `0x10009860` | internal QoS helper `0x10006d20` | `0x100098cd` | false result logs but continues |
| `0x10009860` | `IIPSHostApp.ini` `[ResPool] ReservedSize` | `0x10009a8b` | `GetPrivateProfileIntW`; default `0x40000000` |
| `0x10009570` | `LoadLibraryW` | `0x100096e9` | NULL handle -> open-DLL failure path |
| `0x10009570` | `GetProcAddress("CreateIFSLibDll")` | `0x1000977c` | NULL -> distinct failure string |
| `0x10009570` | `CreateIFSLibDll` | `0x100097a5` | zero EAX -> distinct failure string |
| `0x10009570` | `GetProcAddress("DestoryIFSLibDll")` | `0x100097cc` | NULL -> distinct failure string |
| `0x10011930` | `Global\IIPSShareState_MMF_` | `0x10011b18` | named mapping path |
| `0x10011930` | `Global\IIPSShareState_Mutex_` | `0x10011c98` | named mutex path |
| `0x10015a00` | `ShellExecuteExW` | `0x10015cd1` | success/failure branch and HostApp strings |

## 7. IIPS Environment Contract

Canonical CSV:

```text
工具/logs/ex051_environment_contract.csv
```

Static scan log:

```text
工具/logs/ex051_environment_contract.log
工具/logs/ex051_environment_contract_20260917-221029.log
```

Recovered contract:

```text
CNIFS::InitInGameApp
  -> QoS initialization helper (non-fatal here)
  -> CNIFS::initIfsLib
       -> LoadLibraryW(path containing ifs2.dll)
       -> GetProcAddress(CreateIFSLibDll)
       -> CreateIFSLibDll()
       -> GetProcAddress(DestoryIFSLibDll)

CNIFS::InitInGameApp
  -> GetPrivateProfileIntW(
         IIPSHostApp.ini,
         ResPool,
         ReservedSize,
         default = 0x40000000
     )

ResourceManagerII::LaunchIIPSHostApp candidate
  -> ShellExecuteExW(IIPSHostApp.exe)

IIPS share-state object manager
  -> Global\IIPSShareState_MMF_
  -> Global\IIPSShareState_Mutex_
```

`IIPSClient.ini` is present as an environment/config file and contains
the IIPS error-code table. It is currently L0/L1 evidence; the code that
consumes each entry was not reconstructed in this round.

Relevant configuration labels include:

```text
5  = IFS initialization error
6  = IIPS cache initialization error
7  = IIPS proxy-process initialization error
9  = IIPS shared-memory creation error
39 = Host shared-memory initialization error
41 = IFS DLL load failure
42 = IFS export lookup failure
```

These labels are environment-contract clues only. No mapping from these
labels to `8189FEC` was proven.

## 8. IIPS Status Flow

Canonical CSV:

```text
工具/logs/ex051_status_flow.csv
```

Recovered native branch flow:

```text
IIPS_INIT_ENTRY
  -> QOS_INIT_STATE
       -> failure: log and continue
  -> IFS2_LOAD_STATE
       -> LoadLibraryW
          -> success: IFS2_RESOLVE
          -> failure: "Failed to open dllfile"
  -> IFS2_RESOLVE
       -> success: IFS2_CREATE
       -> failure: "Failed to get function CreateIFSLibDll"
  -> IFS2_CREATE
       -> success: IFS2_DESTROY_PROBE
       -> failure: "Failed to create ifs lib"
  -> IFS2_DESTROY_PROBE
       -> success: continue
       -> failure: "Failed to get proc DestoryIFSLibDll"
  -> RESPOOL_CONFIG_STATE
       -> read IIPSHostApp.ini [ResPool] ReservedSize
  -> HOSTAPP_LAUNCH_STATE
       -> ShellExecuteExW / LaunchIIPSHostApp success or failure
```

This is a static status graph. It does not prove which state was reached
in the historical `8189fec` run.

## 9. IIPSHostApp Analysis

Static evidence:

```text
UTF-16 string: IIPSHostApp.exe
UTF-16 string: IIPSHostApp.ini
ShellExecuteExW callsite: 0x10015cd1
success string: [ResourceManagerII::LaunchIIPSHostApp()][LaunchIIPSHostApp success]
failure string: [ResourceManagerII::LaunchIIPSHostApp()][LaunchIIPSHostApp failed][error %d][sExec.hInstApp %d]
```

Recovered branch shape:

```asm
call ShellExecuteExW
test eax, eax
je   launch_failure
cmp  hInstApp, 0x20
jle  launch_failure
; success path
...
launch_failure:
    GetLastError
    append LaunchIIPSHostApp failed
```

Current classification:

```text
IIPS_HOSTAPP_LAUNCH_BRANCH_L2_CONFIRMED
IIPS_HOSTAPP_RUNTIME_EXECUTION_UNCONFIRMED
```

No IIPSHostApp process was observed in the historical fatal run.

## 10. Cache Initialization Analysis

The string `IIPSERR_CACHE_INIT` exists at `iips.dll` VA `0x10035b8a`.

No direct ordinary `.text` reference to the exact string VA was recovered
by the current scan.

```text
IIPS_CACHE_INIT_BRANCH_UNRESOLVED
```

This is not a claim that the cache path is absent. It means the current
static scan did not connect this label to a native branch.

## 11. Error Initialization Analysis

`IIPSERR_ERROR_INIT` appears 38 times in the string area. The current
scan found no direct ordinary `.text` xref to those exact string VAs.

```text
IIPS_ERROR_INIT_BRANCH_UNRESOLVED
```

The error-code table in `IIPSClient.ini` is an environment/config input,
but no individual code-to-branch mapping was proven in this round.

## 12. `iipsinit` Boundary

Historical runtime evidence contains:

```text
iipsinit Environment List Box
```

Static evidence inside `iips.dll` includes a window-creation candidate:

```text
USER32!CreateWindowExA at 0x10005d84
window-create error string: [IIPSWndMsgProcessor::CreateWnd()][CreateWnd error]
```

The exact `iipsinit` class/name construction and the CODOL-side creator
were not recovered from plain `.text`.

```text
IIPS_INIT_UI_BOUNDARY_PARTIAL
```

## 13. IFS2 Evidence Status

Static readiness:

```text
IFS2.dll exists
CreateIFSLibDll exists
DestoryIFSLibDll exists
IFSDllVerifyApiCompatable exists
```

New L2 result from this round:

```text
[CNIFS::initIfsLib()][Failed to open dllfile][error %d][path %s]
```

is reached from the `LoadLibraryW` result branch:

```asm
call LoadLibraryW
test eax, eax
mov  [ebp+0x54], eax
jne  0x10009770
; failure:
push 0x10034920
```

Current status:

```text
IFS2_STATIC_DEPENDENCY_CONFIRMED
IFS2_LOAD_FAILURE_BRANCH_L2_CONFIRMED
IFS2_RUNTIME_EXECUTION_UNCONFIRMED
IFS2_CAUSALITY_TO_8189FEC_UNCONFIRMED
```

## 14. `8189FEC` Status

No plaintext constant mapping to `8189FEC` was recovered in this round.

```text
8189FEC_PACKED_OR_RUNTIME_GENERATED
IIPS_TO_EXE_ERROR_BOUNDARY_UNCONFIRMED
```

The known IIPS error strings are localized in `iips.dll`; the EXE-side
`WIN_IIPS_INIT_ERROR` formatter remains at the packed/TVM boundary.

## 15. TVM0 Boundary

No `.tvm0` file was modified, decoded, or reverse engineered.

The unresolved transition is:

```text
iips.dll status/error path
        |
        +-- plain .text branches used in this report
        |
        +-- TVM0 / packed EXE formatter boundary
                 |
                 +-- WIN_IIPS_INIT_ERROR / 8189fec
```

## 16. Observer Divergence

No debugger was used in this round.

No API hook, injection, breakpoint, patch, or memory-write observer was
used.

The fresh `-q` probe produced the separate `警告码(0, 20002, 86)` variant,
but because it was a normal non-invasive run terminated at the first
dialog, it is classified as a runtime observation variant rather than
debugger-induced divergence.

## 17. New Evidence Nodes

New plain-`.text` L2 nodes:

```text
IIPS_LOAD_DLL_FAILURE_BRANCH_L2_CONFIRMED
IIPS_HOSTAPP_LAUNCH_BRANCH_L2_CONFIRMED
IIPS_RESPOOL_CONFIG_READ_L2_CONFIRMED
IIPS_SHARED_STATE_OBJECT_BRANCH_PARTIAL
CNIFS_INIT_IN_GAME_APP_CALL_GRAPH_PARTIAL
```

New L3/L4 execution nodes:

```text
NEW_EXECUTION_NODE_NONE
```

The historical L3 module load and IIPS fatal popup are reused evidence,
not a new execution node produced by this round.

## 18. Unresolved Issues

```text
IIPS exact public init entry
IIPS init caller above the CNIFS candidate
IIPS cache-init branch
IIPS error-init branch
IIPSHostApp launch runtime result
IFS2 runtime load result
IFS2 return value
IIPS-to-EXE error handoff
8189fec constant origin
fresh -q warning variant (0, 20002, 86)
```

## 19. Next Experiment Recommendation

Do not add a broad debugger or API hook.

The next highest-value static step is:

```text
reconstruct the callers of 0x10009860 and 0x10015a00
```

and separately determine whether the fresh `警告码(0, 20002, 86)`
variant is caused by an external runtime state change or by the
termination timing of the non-invasive probe.

If dynamic work is resumed later, use at most one already-proven ordinary
`.text` callsite and treat a runtime variant as a separate observation;
do not expand the hook surface.

## Required Answers

1. IIPS initialization entry candidate: `CNIFS::InitInGameApp` at
   `iips.dll RVA 0x9860`, calling `CNIFS::initIfsLib` at RVA `0x9570`.
2. External environment contract: module loading, process launch,
   privilege setup, named shared objects, INI configuration, and IFS2
   exports. It is partial, not complete.
3. Cache-init branch confirmed: no. `IIPS_CACHE_INIT_BRANCH_UNRESOLVED`.
4. Error-init branch confirmed: no. `IIPS_ERROR_INIT_BRANCH_UNRESOLVED`.
5. IIPSHostApp launch branch: static L2 branch confirmed; runtime result
   unconfirmed.
6. IFS2 first analyzable prerequisite: `LoadLibraryW(ifs2.dll)` path,
   with an L2 failure branch to `Failed to open dllfile`.
7. IFS2 runtime execution: unconfirmed.
8. `8189fec`: packed/runtime-generated; EXE/IIPS boundary unresolved.
9. New L3/L4 execution node: none.
10. `.tvm0`: boundary only; not analyzed.

## Final

```text
IIPS_INIT_ENTRY_CANDIDATE
IIPS_ENVIRONMENT_CONTRACT_PARTIAL
IIPS_EXTERNAL_API_L2_CONFIRMED
IIPS_LOAD_DLL_FAILURE_BRANCH_L2_CONFIRMED
IIPS_HOSTAPP_LAUNCH_BRANCH_L2_CONFIRMED
IIPS_CACHE_INIT_BRANCH_UNRESOLVED
IIPS_ERROR_INIT_BRANCH_UNRESOLVED
IIPS_INIT_UI_BOUNDARY_PARTIAL
IFS2_STATIC_DEPENDENCY_CONFIRMED
IFS2_RUNTIME_EXECUTION_UNCONFIRMED
IFS2_CAUSALITY_TO_8189FEC_UNCONFIRMED
8189FEC_PACKED_OR_RUNTIME_GENERATED
IIPS_TO_EXE_ERROR_BOUNDARY_UNCONFIRMED
TVM0_BOUNDARY
OBSERVER_NO_DEBUGGER
NEW_L2_NODE_CONFIRMED
NEW_EXECUTION_NODE_NONE
TENCENT_LAUNCHER_NOT_REQUIRED
RUNTIME_OBSERVATION_VARIANT_UNRESOLVED
```
