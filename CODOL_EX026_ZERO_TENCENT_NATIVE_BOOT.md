# EX-026 Zero Tencent Native Bootstrap Experiment

## 1. Experiment Environment

```text
Machine: m7-e8s3
OS: Windows 10/11, 64-bit
Shell: non-elevated
Game root: D:\BaiduNetdiskDownload\使命召唤OL\COD OL
```

Original binary hashes before the run:

```text
codoMP_client_shipRetail.exe
36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537

codoMP_client_shipRetailBase.dll
EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20

TenProxy.dll
A5EE7EDE762C473F58A87B214213097F6DDA8950AC537B0A959389AEF31348CB

libcef.dll
7E23D62507F9B2233D40A4542F5263E3DA74C1F57B5E866FA8D0198EBE68E51D
```

No binary was modified during the experiment.

## 2. Tencent Process Inventory

Before launch:

```text
No WeGame.exe
No WeGameLauncher.exe
No tgp_daemon.exe
No tcls_core.exe
No launcher.exe
No Client.exe
No TASLogin.exe
No wegame_env.exe
```

Baseline relevant named objects:

```text
\BaseNamedObjects FSyncSharedMemory (Section)
```

No `TPF_Share_Mem`, no `TCLSHOST_MUTEX`, no `TCLS_SHAREDMEMEMORY` was present before launch.

## 3. Launch Command

```text
CommandLine = "D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
CurrentDirectory = D:\BaiduNetdiskDownload\使命召唤OL\COD OL
```

No launcher, no TCLS, no WeGame process was started.

## 4. PID / ParentPID

```text
Game PID      = 18016
Parent PID    = 18048 (observer)
```

## 5. Module Load Order

Observed by Toolhelp polling; timestamps are first-observed times, not exact loader call times.

```text
t=0.263  codoMP_client_shipRetail.exe
t=0.263  codoMP_client_shipRetailBase.dll
t=0.263  libcef.dll
t=0.525  BugTrace.dll / dbghelp.dll
t=2.114  VSDDrvDll.dll
t=2.906  ACE-DRV32.dll
t=3.697  tersafe.dll
t=4.504  TenRpcs.dll
t=6.095  GameRpcs.dll
t=6.095  GDPLoader.dll
t=6.095  tcj.dll
t=6.632  policyprobe.dll
t=6.632  ace-ats32.dll
t=6.632  gcloudvoice.dll
t=6.632  GameDataPlatformServer.dll
t=6.632  mss32.dll / d3d9.dll
t=6.900  TenProxy.dll
t=6.900  GbSpy.dll
t=7.977  AudioHook.dll / AudioDsp.dll
```

This is new evidence: direct zero-Tencent startup loads TenProxy and multiple CODOL project DLLs without any launcher/TCLS context.

## 6. Thread Creation Records

Main thread:

```text
TID 14076 start 0x0E9DC690 = EXE Entry
```

New Base-native thread nodes observed after initial module snapshot:

```text
TID 4028  start 0x5063C96E = Base+0x2C96E
TID 15104 start 0x50C07000 = Base+0x5F7000
TID 15096 start 0x50BFB4E0 = Base+0x5EB4E0
TID 17204 start 0x50623A68 = Base+0x13A68
TID 12640/13492/9152/14064/4820/3344/18040 start 0x5062D68B = Base+0x1D68B
```

Project/security module threads:

```text
ACE-DRV32 threads: start 0x16EE41E8, 0x16D384F0
tcj threads:       start 0x1920A000, 0x192DD7D4
GameRpcs threads:  start 0x77A7FFF0, 0x779DBD20
GDPLoader threads: start 0x5014B52B
policyprobe thread: start 0x19917E40
GameDataPlatformServer threads: start 0x1B268180, 0x1B2658D0, 0x1B267C30
GbSpy thread:      start 0x12352FF0
AudioHook threads: start 0x505E71F0, 0x505EE290
```

These are actual thread start addresses in native code, not string hits.

## 7. LdrLoadDll / LoadLibrary Records

No API hook was installed. Module load order was captured by Toolhelp polling; exact `LdrLoadDll` call sites and return addresses were not recorded. This is marked `NO_HOOK`.

## 8. CreateFile / OpenFileMapping Records

No API hook was available. The observer recorded:

```text
No OpenFileMapping object for TCLS_SHAREDMEMEMORY
No CreateFileMapping object for TCLS_SHAREDMEMEMORY
No file-change events in players/main/Logs/TenproxyLog/BugTrace.log/debug.log
```

File-access monitoring is marked `NO_HOOK / PARTIAL`.

## 9. TCLS_SHAREDMEMEMORY Search Result

During the 20-second direct run:

```text
No object named TCLS_SHAREDMEMEMORY+*
No TPF_Share_Mem created by this run
No TCLSHOST_MUTEX created by this run
```

Result:

```text
TCLS_SHAREDMEMEMORY = NOT PRESENT
```

## 10. EXE Entry

Main thread start address:

```text
0x0E9DC690
```

## 11. Base ordinal_1

Known static chain, not re-instrumented:

```text
EXE Entry
  -> Base ordinal_1
  -> Base+0x149C
  -> Base+0x1AA13B0 (.tvm0 boundary)
```

## 12. Base +0x149C

Known static address:

```text
Base+0x149C
```

## 13. Base +0x1AA13B0

Known static boundary:

```text
Base+0x1AA13B0
```

No `.tvm0` return instrumentation was available, so "first node after .tvm0" cannot be proven directly.

## 14. First Observable Native Node After Bootstrap

Newly observed Base-native thread starts:

```text
Base+0x2C96E  at t=1.588
Base+0x5F7000 at t=1.849
Base+0x5EB4E0 at t=1.849
Base+0x13A68  at t=4.227
Base+0x1D68B  at t=5.033
```

These are real native execution nodes recorded after the initial Base/libcef load snapshot.

## 15. BugTrace Thread Relation

BugTrace loaded at `t=0.525`:

```text
base 0x54160000
thread TID 12108 start 0x541BB233 = BugTrace+0x5B233
```

This thread is separate from the main thread (`TID 14076`). It is classified as:

```text
SECONDARY DIAGNOSTIC PATH
```

## 16. Exit / Fatal Call Chain

The 20-second observer run:

```text
Process was still alive at t=20s
No ExitProcess/exit code observed
Observer terminated the process
```

Separate 12-second UI-state run:

```text
MainWindowTitle = 致命错误
MainWindowHandle = 460248
Responding = True
CPU = 5.234 seconds
Handles = 718
```

No exit call stack was captured.

## 17. New Execution Nodes

New evidence beyond previous reports:

```text
TenProxy.dll loaded without TCLS_SHAREDMEMEMORY
GbSpy.dll loaded and started a native thread
TenRpcs.dll / GameRpcs.dll / tcj.dll / policyprobe.dll loaded
multiple Base-native thread start addresses recorded
```

No evidence of FS `main\` / `players\` / `*.ff` access was captured.

## 18. Final Classification

```text
NATIVE_BOOTSTRAP_PARTIAL
```

Reason:

```text
Native bootstrap progressed beyond previous known nodes:
  Base native threads
  TenProxy and multiple project DLLs
  native threads inside tcj / GameRpcs / GbSpy / policyprobe

But:
  no Engine/Game/Renderer initialization was proven
  no game filesystem/resource access was proven
  fatal-error window still appears
```

## 19. Consistency with EX-025

EX-025 conclusion was:

```text
TCLS_SHAREDMEMEMORY appears only at game-start dispatch
```

EX-026 direct run:

```text
No TCLS_SHAREDMEMEMORY object existed
TenProxy and project DLLs still loaded
```

This does not contradict EX-025. It means the mapping is not a hard precondition for loading TenProxy/project DLLs, though the client still reaches a fatal path later.

## 20. Next Steps

```text
1. Instrument Base+0x2C96E / Base+0x13A68 / Base+0x1D68B thread code
2. Capture TenProxy.dll initialization without mapping
3. Hook OpenFileMappingW / CreateFileMappingW with an elevated observer
4. Capture file I/O with elevated WPR FileIO profile
5. Determine why fatal-error window appears after TenProxy/project DLL load
```

## Deliverable Log

```text
工具/logs/ex026_zero_tencent_native_boot_20260917-111137.log
```

Observer script:

```text
_dyn_stage1/ex026_zero_tencent_probe.py
```
