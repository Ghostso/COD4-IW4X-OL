# EX-027 Native Bootstrap Module Chain & Fatal Path

## Result

```text
MODULE_CHAIN_PARTIAL
FATAL_EXCEPTION_NODE_CONFIRMED
```

New L3 evidence obtained:

```text
EXE Entry actually executed
Base.dll Entry actually executed
libcef.dll Entry actually executed
BugTrace.dll Entry actually executed
BugTrace diagnostic thread created
LdrLoadDll caller/return evidence
Fatal exception chain captured
```

## 1. Zero Tencent Environment Reproduction

Before the debugger run:

```text
WeGame        absent
WeGameLauncher absent
tgp_daemon    absent
tcls_core     absent
TCLS_SHAREDMEMEMORY absent
TPF_Share_Mem absent
```

Launch:

```text
CommandLine = "D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
CurrentDirectory = D:\BaiduNetdiskDownload\使命召唤OL\COD OL
PID = 4564
ParentPID = debugger
```

No launcher/TCLS process was started.

## 2. Module Load Timeline

Loader-debugger timeline:

```text
T0  EXE mapped
T1  ntdll / kernel32 / KernelBase
T2  codoMP_client_shipRetailBase.dll
T3  libcef.dll
T4  user32/comdlg32/ole32/ws2_32/crypt32/etc
T5  Base+0x149C entry hit
T6  libcef entry hit
T7  EXE entry hit
T8  BugTrace.dll loaded
T9  BugTrace entry hit
T10 kernel32!IsBadReadPtr+0x5A access violation
T11 BugTrace diagnostic thread created
T12 C++ exception E06D7363
T13 process exit
```

Under this debugger run, TenProxy/TenRpcs/GameRpcs/tcj/GDPLoader/GameDataPlatformServer were not reached before the fatal path. The non-debug EX-026 run reached those modules later, so the debugger changes timing/behavior.

## 3. Entry Point Execution Evidence

### EXE Entry

```text
address = 0x0E9DC690
TID     = 2824
EIP     = 0x0E9DC690
ESP     = 0x0019FF74
return  = kernel32.dll+0x1FCC9
```

### Base DLL Entry

```text
address = 0x5002149C = Base+0x149C
TID     = 2824 and multiple worker threads
return  = ntdll.dll+0x731A6 (loader init routine)
```

Base+0x149C entry was hit repeatedly as worker threads started, which is a new execution node.

### libcef Entry

```text
address = 0x7A80A1FE = libcef.dll+0x1ECA1FE
TID     = 2824 / worker threads
return  = ntdll.dll+0x731A6
```

### BugTrace Entry

```text
address = 0x67E9D3B8 = BugTrace.dll+0x5D3B8
TID     = 13504
return  = ntdll.dll+0x731A6
```

## 4. LdrLoadDll Caller Evidence

From the loader-debugger run with an `LdrLoadDll` breakpoint:

```text
first LDR_TARGET = KERNEL32.DLL
return = ntdll.dll+0xABBA4
stack contains EXE+0x460084
```

Additional system API-set loads:

```text
LDR_TARGET api-ms-win-core-synch-l1-2-0
LDR_TARGET api-ms-win-core-fibers-l1-1-1
LDR_TARGET api-ms-win-core-localization-l1-2-1
LDR_TARGET api-ms-win-core-datetime-l1-1-1
return = KernelBase.dll+0x111DE6
```

These are real caller/return records, not static imports.

## 5. Fatal Path

Captured fatal chain:

```text
1. BugTrace.dll entry executed
2. access violation C0000005
   address = kernel32.dll+0x1015A
   module  = kernel32.dll
   = IsBadReadPtr+0x5A
3. BugTrace diagnostic thread created
   start = BugTrace.dll+0x5B233
4. C++ exception E06D7363
   address = KernelBase.dll+0x13B702
   first chance and second chance
5. ExitProcess code = 0xE06D7363 (3765269347)
```

The BugTrace thread is separate from the main thread and is classified as a secondary diagnostic path.

## 6. Game Resource / File Access

```text
Not captured.
No API hook for CreateFile/NtCreateFile was available.
No main\ / players\ / zone\ / *.ff access was proven.
```

## 7. Answers to the 8 Questions

### Q1. Who loads TenProxy?

```text
Not closed by this run.
TenProxy loads in non-debug EX-026, but the debugger fatal path exits before TenProxy.
```

### Q2. Who loads GameRpcs/TenRpcs/tcj/GDPLoader/GameDataPlatformServer?

```text
Not closed.
Module loads were observed in EX-026, but no caller/return edge was captured for them.
```

### Q3. What do Base+0x2C96E / +0x13A68 / +0x1D68B start?

```text
Not instrumented in EX-027.
They remain new thread-start addresses from EX-026, not confirmed responsibilities.
```

### Q4. Is Game/Renderer/FS initialization reached?

```text
No.
```

### Q5. What is the first game resource file access?

```text
None observed.
```

### Q6. Who creates the fatal-error window?

```text
Not confirmed.
MessageBoxW breakpoint was armed but the debugger run exited via C++ exception before a window appeared.
```

### Q7. Last healthy CODOL module before fatal?

Under the debugger:

```text
BugTrace.dll entry was the last project-module entry before C0000005.
```

Under non-debug EX-026:

```text
TenProxy/GbSpy/TenRpcs/GameRpcs/tcj/etc were loaded before the fatal window.
```

### Q8. How far can the chain be closed with L3 evidence?

```text
EXE Entry
  -> Base+0x149C entry
  -> libcef entry
  -> BugTrace entry
  -> kernel32!IsBadReadPtr+0x5A (C0000005)
  -> C++ exception E06D7363
  -> exit
```

This is closed with actual entry-point hits and exception records. It does not reach TenProxy under debugger conditions.

## 8. Module DAG

Proven edges:

```text
Loader -> Base.dll entry
Loader -> libcef.dll entry
Loader -> BugTrace.dll entry
EXE Entry -> kernel32 startup return
Base -> multiple new worker threads
```

Not proven:

```text
Base -> TenProxy
Base -> TenRpcs / GameRpcs / tcj / GDPLoader / GameDataPlatformServer
```

For those modules, only:

```text
MODULE LOADED
```

is recorded.

## 9. Final Classification

```text
MODULE_CHAIN_PARTIAL
FATAL_EXCEPTION_NODE_CONFIRMED
```

The debugger confirms entry execution and the fatal exception node, but does not close the full TenProxy/project-DLL chain.

## 10. Logs and CSV

Primary debugger log:

```text
工具/logs/ex027_native_bootstrap_module_chain_20260917-120236.log
```

Primary timeline CSV:

```text
工具/logs/ex027_module_timeline_20260917-120236.csv
```

LdrLoadDll caller capture:

```text
工具/logs/ex027_native_bootstrap_module_chain_20260917-115823.log
```

Debugger source/binary:

```text
_dyn_stage1/ex027_loader_debugger.cs
_dyn_stage1/ex027_loader_debugger.exe
```

## 11. Next Steps

```text
1. Set hardware breakpoints at Base+0x2C96E / +0x13A68 / +0x1D68B
2. Avoid LdrLoadDll breakpoints to let TenProxy load under debugger
3. Hook LdrLoadDll after Base entry instead of during loader init
4. Capture IsBadReadPtr caller stack at C0000005
5. Capture MessageBoxW/CreateWindowExW for fatal-window attribution
6. Use elevated WPR for file I/O
```
