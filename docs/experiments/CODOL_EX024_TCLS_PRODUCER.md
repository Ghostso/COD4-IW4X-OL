# EX-024 TCLS_SHAREDMEMEMORY Producer and Minimal Context

## 1. Executive Summary

The direct `CreateFileMappingW("TCLS_SHAREDMEMEMORY+<suffix>")` producer is not yet dynamically captured, but static evidence now identifies two producer-capable modules and the exact mapping parameters:

```text
WeGame\tcls\tcls_core.exe
COD OL\TCLS\Tenio\TCLS.dll
```

`TCLS\ClientBase.dll` contains the same name and `%s%d` format strings but imports only `LoadLibraryA` / `GetProcAddress`, so it is best described as the orchestration/loader layer around the producer rather than the module that makes the direct `CreateFileMappingW` call in this static scan.

Both direct producer call sites use:

```text
hFile                 = INVALID_HANDLE_VALUE (-1)
lpFileMappingAttributes = initialized SECURITY_ATTRIBUTES with DACL
flProtect             = PAGE_READWRITE (4)
dwMaximumSizeHigh     = 0
dwMaximumSizeLow      = 0x80000 (512 KiB)
MapViewOfFile access  = 0xF001F (FILE_MAP_ALL_ACCESS)
```

Classification:

```text
PRODUCER_PARTIAL
CONSUMER_CONFIRMED
CONTEXT_STRUCTURE_PARTIAL
```

## 2. Producer

### WeGame\tcls\tcls_core.exe

Format strings decoded:

```text
0x5822E8 TCLS_SHAREDMEMEMORY
0x582310 %s%lu
0x5822B4 RAIL_TCLS_SHARED
0x5822D8 %s%llu
```

The TCLS mapping constructor:

```text
0x4078F0 builds "TCLS_SHAREDMEMEMORY" + "%s%lu"
  -> 0x4079B0 calls 0x407D10 with the generated name

0x407D10:
  0x407D81 CreateFileMappingW
  0x407D9A MapViewOfFile
  first DWORD written at view = 0x40
  internal pointers: base+4 and base+0x104
```

No direct static `E8` caller of `0x4078F0` was recovered; it appears to be invoked indirectly.

### COD OL\TCLS\Tenio\TCLS.dll

```text
0x103C3268 TCLS_SHAREDMEMEMORY
0x103C05F4 %s%d
0x103DD190 %s%d
```

Mapping function:

```text
0x10040761 pushes TCLS_SHAREDMEMEMORY into a wide buffer
0x10040822 CreateFileMappingW, size 0x80000, PAGE_READWRITE
```

The function starts at `0x100406E0`; no direct static caller was recovered, so it is also invoked indirectly.

### COD OL\TCLS\ClientBase.dll

```text
0x101D508C TCLS_SHAREDMEMEMORY
0x101D50B4 %s%d
```

Imports:

```text
kernel32.dll LoadLibraryA
kernel32.dll GetProcAddress
```

No direct mapping API call was found in this scan. ClientBase is therefore recorded as the context/orchestration writer, not the direct `CreateFileMappingW` caller in this static pass.

## 3. Consumer

`COD OL\TenProxy.dll` is the confirmed consumer:

```text
0x10020F70 TCLS_SHAREDMEMEMORY
0x10006176 name construction
0x100061E2 OpenFileMappingW
0x10006273 MapViewOfFile
```

Historic `TenproxyLog` evidence:

```text
OpenFileMapping TCLS_SHAREDMEMEMORY+<GamePID> Success!
MapViewOfFile Success!
GetGameSignatrue Success!
GetJumpSignatrue Success!
Post TCLS_TENPROXY_RESULT Message Success!
```

`GetGameSignatrue` / `GetJumpSignatrue` exist as strings in TenProxy but have no direct static pointer xrefs in the current scan; the historic logs provide L3 evidence that they run after mapping succeeds.

## 4. PID Relationship

Historic consumer log:

```text
GetCurrentProcessId = 13600
OpenFileMapping TCLS_SHAREDMEMEMORY+13600 Success
```

Therefore:

```text
mapping suffix = consumer game PID = GetCurrentProcessId() in the game process
```

Static producer format strings are numeric (`%s%lu` in tcls_core, `%s%d` in ClientBase/Tenio TCLS.dll), consistent with a decimal PID suffix. The exact producer-side argument source is not dynamically confirmed; the producer must either know the future game PID or create the mapping after process creation and before TenProxy initializes.

## 5. Mapping Creation

Static producer parameters:

```text
CreateFileMappingW(
  hFile = INVALID_HANDLE_VALUE,
  lpAttributes = SECURITY_ATTRIBUTES with DACL,
  flProtect = PAGE_READWRITE,
  dwMaximumSizeHigh = 0,
  dwMaximumSizeLow = 0x80000,
  lpName = "TCLS_SHAREDMEMEMORY" + decimal PID
)
```

Call sites:

```text
tcls_core.exe      0x407D81
Tenio\TCLS.dll     0x10040822
```

## 6. Mapping Size

Static evidence from both direct producer call sites:

```text
0x80000 bytes = 512 KiB
```

No dynamic mapping-size capture was possible because the observed launcher chain did not create the mapping within 35 seconds.

## 7. Mapping Lifetime

Static tcls_core wrapper:

```text
view handle stored at object+0x18
mapped view stored at object+0x00
destructor path 0x407E10 unmaps view and closes mapping handle
```

Dynamic launcher observation:

```text
Client.exe -> launcher.exe -> tgp_daemon.exe -> TASLogin/wegame_env/browser/tcls_core
observed objects:
  <pid>TPF_Share_Mem
  TCLSHOST_MUTEX_59C1948BC1838E7654172E7D2F159D64
observed:
  TCLS_SHAREDMEMEMORY: absent in 35s window
```

The TCLS mapping is therefore tied to game-start, not merely to launcher/tcls_core startup.

## 8. Structure Observations

Producer-side tcls_core initialization after mapping:

```text
[view+0x00] = 0x40
[view+0x04] = view+4
[view+0x08] = view+0x104
[view+0x0C] = view+0x104
```

This is recorded as L2 producer wrapper initialization. It is not yet sufficient to name fields inside the shared memory as GameSignature/JumpSignature.

## 9. GameSignature Boundary

Known:

```text
TenProxy string GetGameSignatrue  VA 0x10020C4A
historic log: called after MapViewOfFile
direct static xref: not recovered
```

Boundary classification: `L3 historic call / L2 static string`, not a recovered concrete field offset.

## 10. JumpSignature Boundary

Known:

```text
TenProxy string GetJumpSignatrue   VA 0x10020BCE
historic log: called after GetGameSignatrue
direct static xref: not recovered
```

Same classification as GameSignature.

## 11. WIN_NO_TCLS Failure Path

Known:

```text
EXE WIN_NO_TCLS     VA 0x00DDBF80
Base mapping string VA 0x1088FFFC
```

The direct `OpenFileMappingW -> WIN_NO_TCLS` caller chain was not captured dynamically in this round. Existing reports show Base/EXE code is TVM/TP3-protected and no direct static xref to `WIN_NO_TCLS` was recovered. The TenProxy consumer has its own failure path:

```text
OpenFileMappingW returns NULL
  -> GetLastError
  -> TenProxy failure log
```

## 12. Direct-Start vs Launcher-Start Comparison

Direct game start (previous CODOLLauncher runs):

```text
EXE -> Base.dll -> libcef loaded
TCLS_SHAREDMEMEMORY mapping manually created or not
process later reaches fatal window
TenProxy not observed loaded before fatal path
```

Official launcher chain (new dynamic probe):

```text
Client.exe -> launcher.exe -> tgp_daemon.exe
  -> TASLogin.exe / wegame_env.exe / browser.exe / tcls_core.exe
TPF_Share_Mem created
TCLS_SHAREDMEMEMORY not created in observed window
```

This proves:

```text
TCLS_SHAREDMEMEMORY is not created during launcher/tcls_core startup alone
manual mapping alone does not advance the direct-start game past Base/libcef
```

## 13. L3/L4 Evidence

| Node | Evidence level |
|---|---|
| TenProxy OpenFileMappingW + MapViewOfFile | L3 historic log |
| TenProxy GetGameSignatrue / GetJumpSignatrue | L3 historic log |
| tcls_core producer format string | L2 static |
| tcls_core CreateFileMappingW call site | L2 static |
| Tenio TCLS.dll CreateFileMappingW call site | L2 static |
| mapping size 0x80000 | L2 static |
| live CreateFileMappingW("TCLS_SHAREDMEMEMORY+pid") | not captured |

## Q1. Who creates `TCLS_SHAREDMEMEMORY+PID`?

Static candidates:

```text
WeGame\tcls\tcls_core.exe
COD OL\TCLS\Tenio\TCLS.dll
```

`ClientBase.dll` is the orchestration layer with the same strings and `%s%d` format, but no direct mapping import in this scan.

## Q2. When is it created?

Only at game-start dispatch, not during launcher/tcls_core startup. The 35-second official-chain probe saw no `TCLS_SHAREDMEMEMORY` object.

## Q3. Where does the PID suffix come from?

Static: decimal numeric argument to the producer name builder. Historic consumer: suffix equals game process `GetCurrentProcessId()`. Exact producer argument source remains unknown.

## Q4. What is the shared-memory size?

Static:

```text
0x80000 bytes = 512 KiB
```

## Q5. What does Base/TenProxy read from it?

TenProxy opens/maps it, then reads game and jump signatures, then posts `TCLS_TENPROXY_RESULT`. Exact field offsets are unknown.

## Q6. What are `GetGameSignatrue` / `GetJumpSignatrue` input/output?

Input/output are not fully recovered. Historic logs confirm they return success after mapping. No direct static xref to their strings was found in TenProxy.

## Q7. Direct double-click: OpenFileMappingW parameters/result?

Not captured. TenProxy was not observed loaded before the fatal path in direct-start runs, so no live `OpenFileMappingW` failure record was obtained.

## Q8. Successful launcher chain: parameters/result?

Historic successful chain:

```text
OpenFileMappingW("TCLS_SHAREDMEMEMORY+13600") -> success
MapViewOfFile -> success
GetGameSignatrue -> success
GetJumpSignatrue -> success
```

Caller RVA in TenProxy:

```text
OpenFileMappingW 0x100061E2
MapViewOfFile    0x10006273
```

## Remaining Unknowns

```text
Exact module that executes CreateFileMappingW in a real game-start flow
Producer-side PID source
Shared-memory field offsets for game/jump signatures
Structure bytes written by a successful producer before TenProxy reads it
OpenFileMappingW failure caller in direct-start (no debugger instrumentation available)
```

## Deliverables and Logs

Main scan log:

```text
工具/logs/ex024_tcls_producer_20260917-101204.log
```

Dynamic launcher observation log:

```text
工具/logs/ex024_tcls_producer_dynamic_20260917-102014.log
```

Reproducible scripts:

```text
_dyn_stage1/ex024_producer_scan.py
_dyn_stage1/ex024_focus2.py
_dyn_stage1/ex024_dynamic_probe.py
```
