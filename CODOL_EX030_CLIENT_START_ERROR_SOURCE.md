# EX-030 Native Bootstrap "Start From Client" Error Source

## Final Classification

```text
ERROR_STRING_SOURCE_CONFIRMED
CLIENT_CONTEXT_CHECK_PARTIAL
NO_PERSISTENT_WRITE_OBSERVED
```

The error text is confirmed to come from `localization.txt` key `WIN_NO_TCLS`, displayed by the CODOL process through a standard dialog. The exact predicate that decides "not started from Client" is not yet reconstructed.

## Observed Error

Normal direct launch, no debugger:

```text
Window class = #32770
Window title = 致命错误
Button       = 确定
Static text  = 请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。
```

Window owner PID = game process.

## String Source

### localization.txt

```text
WIN_NO_TCLS key offset = 0x10BC
message start offset   = 0x10C9
encoding               = GBK/ANSI
exact text:
  "请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。"
```

### codoMP_client_shipRetail.exe

```text
localization.txt string
  file offset = 0x6C73C4
  RVA         = 0x9DB3C4

WIN_NO_TCLS token
  file offset = 0x6C7F80
  RVA         = 0x9DBF80
```

No project DLL contains the literal error phrase. The full message exists only in `localization.txt`.

## XREF Status

Static xref scan:

```text
EXE WIN_NO_TCLS      0x00DDBF80 -> no direct static xref
EXE localization.txt 0x00DDB3C4 -> no direct static xref
```

The EXE is TP3/TVM-packed, so the consumer code is not visible in plain section data.

## Last CODOL Modules Before Error

At the moment the dialog appeared, the normal-run process had loaded:

```text
codoMP_client_shipRetailBase.dll
libcef.dll
BugTrace.dll
ACE-DRV32.dll
tersafe.dll
TenRpcs.dll
GameRpcs.dll
GDPLoader.dll
tcj.dll
GameDataPlatformServer.dll
policyprobe.dll
TenProxy.dll
GbSpy.dll
```

Therefore:

```text
The error appears AFTER project DLL initialization, not before it.
```

## Answers

1. Where is the "start from Client" string?

```text
COD OL/localization.txt, key WIN_NO_TCLS.
```

2. RVA / file offset?

```text
localization.txt message offset 0x10C9
EXE WIN_NO_TCLS token offset 0x6C7F80 / RVA 0x9DBF80
```

3. Who references it?

```text
Only the EXE contains localization.txt and WIN_NO_TCLS tokens.
Direct caller unresolved because EXE is VM-packed.
```

4. Who displays it?

```text
The CODOL process displays a standard #32770 dialog with title 致命错误.
Exact module that calls the dialog API is unresolved.
```

5. Last CODOL module before error?

```text
TenProxy.dll and GbSpy.dll were present at dialog time.
All earlier project DLLs were already loaded.
```

6. Trigger condition?

```text
Not reconstructed.
It is a runtime predicate that fires after project DLL initialization.
```

7. CommandLine check?

```text
Not proven.
Direct command line was recorded, but no code path proves it is the predicate.
```

8. ParentPID check?

```text
Not proven.
```

9. Client.exe check?

```text
Not proven.
The message text names TCLS\Client.exe, but no predicate was recovered.
```

10. Window check?

```text
Not proven.
```

11. TCLS/IPC check?

```text
Not proven.
No TCLS_SHAREDMEMEMORY object was created or observed in the normal run.
```

12. File/registry access?

```text
File snapshot observed no persistent writes.
Registry was not monitored.
```

13. Persistent write?

```text
NO_PERSISTENT_WRITE_OBSERVED.
```

14. If no write, is this a runtime predicate?

```text
LIKELY, but not proven.
The error appears to be computed during this launch, not loaded from a previous persistent marker.
```

## "Client" Meaning

The literal message says:

```text
TCLS文件夹内的Client.exe
```

So the message names `TCLS\Client.exe`. Whether the predicate actually checks that process remains unresolved.

## TCLS Exclusion

Normal run without TCLS:

```text
No TCLS_SHAREDMEMEMORY
No TPF_Share_Mem
No TCLS host mutex
No WeGame / tcls_core
```

The error still appeared after project DLL initialization. This alone does not prove TCLS causes it; the predicate is unknown.

## Deliverables

String scan log:

```text
工具/logs/ex030_client_start_error_source_20260917-122435.log
```

Window probe log:

```text
工具/logs/ex030_window_probe_20260917-122637.log
```

File activity summary:

```text
工具/logs/ex030_file_activity.csv
```

Scan/probe scripts:

```text
_dyn_stage1/ex030_string_scan.py
_dyn_stage1/ex030_window_probe.py
```

## Next Step

```text
Recover the EXE/Base predicate that consumes WIN_NO_TCLS.
Focus on which startup-mode flag or launcher-context check is false after TenProxy/GbSpy initialize.
```
