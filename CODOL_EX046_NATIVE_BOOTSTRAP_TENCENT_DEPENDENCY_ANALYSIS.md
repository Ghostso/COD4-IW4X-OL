# EX-046 Native Bootstrap and Tencent Dependency Analysis

## Final Classification

```text
NATIVE_BOOTSTRAP_CHAIN_DEEP_ANALYZED
TENCENT_DEPENDENCY_CLASSIFIED
MINIMAL_CONTEXT_PARTIAL
FIRST_POST_GATE_BLOCKER_CONFIRMED
POPUP_CONTENT_CAPTURE_CONFIRMED
NO_NEW_EXECUTION_NODE
NO_OBSERVER_DIVERGENCE_IN_GROUND_TRUTH
NO_TVM0_DEPENDENCY_IN_RECOVERED_CHAIN
```

Without starting WeGame/TCLS/Client.exe, CODOL reaches its own native
bootstrap. `-q` / `-qa` bypass `WIN_NO_TCLS`; the first real blocker is
IIPS initialization (`WIN_IIPS_INIT_ERROR / 8189FEC`). No tested local
context moved startup beyond that node.

## Executive Summary

CODOL does not require WeGame/TCLS/Client.exe to enter its native
bootstrap dispatcher. The recovered plain `.text` chain is:

```text
0x77F580 (argv/context gate)
  -> 0x77F8B3
  -> 0x4FD9B0
  -> 0x4FCEE0
  -> 0x808650
  -> 0x7E98F0
  -> 0x6212C0 (STUN/network mode init)
```

`WIN_NO_TCLS` is context-only, not a real TCLS shared-memory check.
`-q` / `-qa` select mode globals:

```text
-q  -> 0x849413B=1, 0x849B500=0
-qa -> 0x849413B=0, 0x849B500=1
```

The current hard blocker is IIPS initialization at Node E.

## No-Tencent Direct Launch Conclusion

```text
WeGame             : not started
TCLS Client.exe    : not started
tcls_core          : not started
TCLS.dll           : not loaded
TCLS shared memory : not present
TPF_Share_Mem      : not present
```

Native bootstrap still runs and loads project DLLs. Tencent launcher
components are not required for this phase.

## Gate Function `0x77F580`

`0x77F580` is the argv/context gate:

```text
scans argv
  -q  -> [0x849413B]=1
  -qa -> [0x849B500]=1
  -src=tgp -> [0x849B501]=1

if no -q and no -qa:
  WIN_NO_TCLS fatal

else:
  continue into bootstrap
  ...
  0x77F8B3 call 0x4FD9B0
```

Observed checks:

```text
argv/command line : yes
parent process    : no evidence
environment       : no evidence
window            : no evidence
mutex             : no evidence
shared memory     : no evidence
file              : no evidence
DLL               : no evidence
registry          : no evidence
```

No additional hidden Tencent launcher check was found in this gate body.

## Dispatcher Deep Analysis

### `0x4FD9B0`

Function boundaries:

```text
0x4FD9B0 .. 0x4FDADB
```

Key calls:

```text
0xC43280
0xC435C0
0x4FCEE0
0x774900
0x4F2FF0
0x4F2EC0
0x4F8B20
0x401130
0x7755D0
0x4FD900
```

It is a top-level bootstrap init candidate.

### `0x4FCEE0`

Function boundaries:

```text
0x4FCEE0 .. 0x4FD8DF
```

It is a large multi-subsystem dispatcher containing many init calls. The
network path is embedded:

```text
0x4FD287 call 0x808650
```

### `0x808650`

Function boundaries:

```text
0x808650 .. 0x808932
```

It calls `0x7E98F0` and then continues with more network/config init
calls. This is a subsystem dispatcher rather than a thin wrapper.

### `0x7E98F0`

Function boundaries:

```text
0x7E98F0 .. 0x7E9A35
```

Network subsystem init containing:

```text
0x7E84A0
0xB76D80
0x6212C0  STUN/network mode init
0x7FA4C0
0x7EF830
0x639D00
0x4A1F60
0x642620
0x4AB840
0x801020
0x4A9A60
0x4A3300
0x7F9F60
```

### `0x6212C0`

STUN/network mode function:

```text
0x6212C0 .. 0x621AF5
```

Reads:

```text
0x849413B
0x849B500
```

Selects between:

```text
stun1-tub.codol.qq.com
stun.us.demonware.net
```

`0x621AC6` is an internal recursive/re-entry call.

## Subsystem Initialization Graph

```text
4FD9B0
  -> 4FCEE0
       -> ... init ...
       -> 808650
            -> 7E98F0
                 -> 6212C0  STUN mode
            -> more network/config init
       -> ... init ...
  -> more bootstrap init
```

Callee subsystem classification is intentionally limited because callee
identities are unresolved. The code evidence supports network and
multi-subsystem initialization, but not named project-DLL call edges.

## Tencent/TCLS Dependency Matrix

| Component | Static present | Direct-launch loaded | Direct-launch executed | Absence result | Hard dependency |
| --- | --- | --- | --- | --- | --- |
| WeGame | YES | NO | NO | not required | NO |
| tcls_core | YES | NO | NO | not required | NO |
| TCLS.dll | YES | NO | NO | not required | NO |
| Client.exe | YES | NO | NO | not required | NO |
| TenProxy.dll | YES | YES | UNKNOWN | loaded without TCLS | not proven |
| TCLS shared memory | string only | NO | NO | no effect on gate | NO |
| TPF_Share_Mem | string only | NO | NO | no effect observed | NO |

Distinction:

```text
string present != loaded != executed != control-flow dependency != hard dependency
```

## Command-Line/Context Dependency

Required to pass first gate:

```text
-q
or
-qa
```

`-src=tgp` alone is insufficient.

## Normal-Run Module Timeline

Representative `-q` timeline:

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

This is load-order evidence, not causality.

## Popup Timeline

Captured from normal runs:

```text
A no args   T+8.102  #32770 致命错误
  Static: 请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。
  Button: 确定

B -q       T+7.680  #32770 致命错误
  Static: 初始化IIPS错误：8189fec。
  Button: 确定

C -qa      T+7.688  #32770 致命错误
  Static: 初始化IIPS错误：8189fec。
  Button: 确定
```

## Fatal Source Summary

```text
WIN_NO_TCLS
  localization -> gate 0x37F580 -> display 0x37FA70

WIN_IIPS_INIT_ERROR
  localization -> IIPS init failure -> 8189FEC
  source: PACKED_OR_VM_GENERATED
```

No new IIPS error caller was recovered without entering `.tvm0`.

## First True Blocker

```text
IIPS initialization
WIN_IIPS_INIT_ERROR / 8189FEC
```

This is the first verified blocker after the argv gate. It is not a
Tencent launcher dependency.

## Minimal Native Bootstrap Context

```text
MINIMAL_CONTEXT_PARTIAL
```

Known sufficient:

```text
full local game tree
working directory = game root
argv contains -q or -qa
```

This reaches IIPS fatal. No condition was found that advances beyond IIPS.

## Uncertainties

```text
0x8189FEC source unresolved
IIPS error dispatcher unresolved
callee subsystem identities unresolved
return/status propagation of many init calls unresolved
```

## TVM0 Boundaries

```text
recovered chain: NO_TVM0_DEPENDENCY
above 0x77F580 caller: potential TVM0 boundary
IIPS error source: PACKED_OR_VM_GENERATED
```

## Hashes

Original and experiment copy hashes are identical:

```text
codoMP_client_shipRetail.exe
36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537

codoMP_client_shipRetailBase.dll
EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20

TenProxy.dll
A5EE7EDE762C473F58A87B214213097F6DDA8950AC537B0A959389AEF31348CB
```

## Answers

Q1: CODOL enters native bootstrap without WeGame/TCLS: YES.
Q2: First layer requires only normal game tree plus `-q` / `-qa` argv.
Q3: `-q`/`-qa` select mode globals and bypass the argv gate.
Q4: `0x4FD9B0` and `0x4FCEE0` are bootstrap dispatchers; `0x808650` is subsystem init containing network init.
Q5: WeGame, tcls_core, TCLS.dll, Client.exe, TCLS shared memory are not involved in normal direct launch.
Q6: TenProxy/GbSpy/etc load, but no Tencent launcher hard dependency was proven before IIPS.
Q7: First blocker is IIPS initialization.
Q8: Popup title `致命错误`, class `#32770`, text `初始化IIPS错误：8189fec。`, button `确定`.
Q9: No earlier hard Tencent dependency was found.
Q10: Minimal verified context is full local tree + `-q` / `-qa`; reaches IIPS fatal.
Q11: Blocker class: IIPS initialization / unknown internal status.

## Final Conclusion

```text
NATIVE_BOOTSTRAP_CHAIN_DEEP_ANALYZED
TENCENT_DEPENDENCY_CLASSIFIED
MINIMAL_CONTEXT_PARTIAL
FIRST_POST_GATE_BLOCKER_CONFIRMED
POPUP_CONTENT_CAPTURE_CONFIRMED
NO_NEW_EXECUTION_NODE
```
