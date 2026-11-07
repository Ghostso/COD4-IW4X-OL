# EX-028 Observer-Induced Divergence

## Final Classification

```text
DEBUGGER_DIVERGENCE_CONFIRMED
```

The normal run and the minimal debugger run diverge after BugTrace. MODE-A continues into project DLLs and later shows the fatal window. MODE-B enters the fatal/exit path before any project DLL loads.

## MODE-A: Normal Run

```text
PID        = 17732 (observer-reported game PID in MODE-A)
Command    = "D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
WorkingDir = D:\BaiduNetdiskDownload\使命召唤OL\COD OL
Debugger   = none
```

Observer method:

```text
Toolhelp process/module/thread polling
named-object scanning
file snapshot
no in-process breakpoints
```

Reproduced project module timeline:

```text
T+0.275 EXE / Base / libcef
T+0.551 BugTrace
T+2.704 ACE-DRV32.dll
T+3.509 tersafe.dll
T+4.317 TenRpcs.dll
T+5.933 GameRpcs.dll
T+5.933 GDPLoader.dll
T+5.933 tcj.dll
T+6.202 GameDataPlatformServer.dll
T+6.202 policyprobe.dll
T+6.474 TenProxy.dll
T+6.474 GbSpy.dll
```

Later fatal window:

```text
MainWindowTitle = 致命错误
```

## MODE-B: Minimal Debugger Run

Breakpoints installed:

```text
EXE Entry
Base+0x149C
libcef Entry
BugTrace Entry
```

No LdrLoadDll, no MessageBoxW, no ExitProcess breakpoints.

Observed:

```text
T+0.004 EXE mapped
T+0.035 Base mapped
T+0.059 libcef mapped
T+0.189 Base+0x149C entry hit
T+0.189 libcef entry hit
T+0.201 EXE entry hit
T+0.629 BugTrace mapped
T+0.633 BugTrace entry hit
T+0.642 C0000005 at kernel32+0x1015A
T+5.520 C++ exception E06D7363
T+8.108 exit code 0xE06D7363
```

No project DLL loaded:

```text
TenProxy absent
GbSpy absent
TenRpcs absent
GameRpcs absent
tcj absent
policyprobe absent
GDPLoader absent
GameDataPlatformServer absent
ACE-DRV32 absent
tersafe absent
```

## Unified Timeline

| Node | MODE-A | MODE-B |
|---|---|---|
| EXE | T+0.275 | T+0.004 |
| Base | T+0.275 | T+0.035 |
| libcef | T+0.275 | T+0.059 |
| Base entry | observed via thread code | T+0.189 |
| libcef entry | not instrumented | T+0.189 |
| EXE entry | main thread start | T+0.201 |
| BugTrace | T+0.551 | T+0.629 |
| BugTrace entry | not instrumented | T+0.633 |
| C0000005 | not observed before project DLLs | T+0.642 |
| ACE-DRV32 | T+2.704 | absent |
| TenRpcs | T+4.317 | absent |
| GameRpcs | T+5.933 | absent |
| tcj | T+5.933 | absent |
| TenProxy | T+6.474 | absent |
| Fatal/exit | fatal window later | E06D7363 at T+5.520 |

## Divergence Point

```text
Last common node: BugTrace
First divergent behavior:
  MODE-B: BugTrace entry -> IsBadReadPtr AV -> fatal exit
  MODE-A: BugTrace -> ACE-DRV32 -> ... -> TenProxy -> fatal window
```

The debugger does not just slow the chain; it changes the chain before project DLL initialization.

## Answers

1. Are EX-026 project DLL loads reproducible?

```text
YES.
Fresh MODE-A reproduced TenProxy/GbSpy/TenRpcs/GameRpcs/tcj/policyprobe/GDPLoader/GameDataPlatformServer.
```

2. Does CDB cause project DLL disappearance?

```text
YES.
Minimal MODE-B showed none of those project DLLs before exit.
```

3. Where is the first divergence?

```text
After BugTrace.
MODE-B enters fatal path; MODE-A continues into ACE-DRV32.
```

4. BugTrace exception position in both modes?

```text
MODE-A: BugTrace loads at T+0.551, but project DLLs still load.
MODE-B: BugTrace entry at T+0.633, AV at T+0.642, before TenProxy.
```

5. Actual project DLL order in normal run?

```text
ACE-DRV32 -> tersafe -> TenRpcs -> GameRpcs/GDPLoader/tcj -> GameDataPlatformServer/policyprobe -> TenProxy/GbSpy
```

6. Is game resource file access observed?

```text
NO.
No main\ / players\ / zone\ / *.ff access was captured.
```

7. Does fatal occur after project DLL initialization in normal run?

```text
YES in MODE-A.
Project DLLs load first, then the fatal window appears.
```

8. Earliest stable native bootstrap node?

```text
EXE Entry -> Base+0x149C -> libcef -> BugTrace
This prefix is stable in both modes.
```

## Consequence

EX-027's missing project DLLs cannot be used to deny EX-026. Future CDB/breakpoint experiments must be recalibrated against the normal-run chain.

## Deliverables

Divergence summary log:

```text
工具/logs/ex028_observer_divergence_20260917-121717.log
```

Unified timeline CSV:

```text
工具/logs/ex028_timeline_20260917-121717.csv
```

MODE-A raw log:

```text
工具/logs/ex028_mode_a_20260917-121353.log
```

MODE-B raw log:

```text
工具/logs/ex028_mode_b_20260917-121424.log
```

Timeline builder:

```text
_dyn_stage1/ex028_build_timeline.py
```
