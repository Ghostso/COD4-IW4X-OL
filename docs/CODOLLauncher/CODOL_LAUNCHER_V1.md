# CODOL Launcher V1

## What the launcher does now

`CODOLLauncher.exe` is a Win32 console launcher that reproduces the launch shape the original CODOL stack used, without running `TCLS\Client.exe`, WeGame, or the official launcher UI.

Flow:

```text
CODOLLauncher.exe
  -> load CODOLLauncher.ini
  -> locate codoMP_client_shipRetail.exe
  -> create game process suspended
  -> get Game PID
  -> create validated IPC before resume
  -> resume primary thread
  -> monitor module load
  -> report BOOT_DEPTH
```

Command-line flags:

```text
--diagnostic
--verbose
--wait
--no-monitor
```

## What the old launcher did

Historical artifacts are preserved in this workspace. The relevant confirmed launcher/game handoff is in `COD OL\TenproxyLog\*.log`:

```text
OpenFileMapping TCLS_SHAREDMEMEMORY+<GamePID> Success!
MapViewOfFile Success!
GetGameSignatrue Success!
GetJumpSignatrue Success!
Post TCLS_TENPROXY_RESULT Message Success!
```

Recent `TCLS\Client.exe` observers show the old launcher stack was:

```text
TCLS\Client.exe
  -> WeGameLauncher\launcher.exe
  -> WeGame\tgp_daemon.exe
```

The current CODOLLauncher does not require any of those processes.

## Confirmed startup context

Confirmed:

```text
TCLS_SHAREDMEMEMORY+GamePID mapping name
Game PID is GetCurrentProcessId() from the game process
TenProxy posted TCLS_TENPROXY_RESULT after mapping
```

Implemented:

```text
TCLSCompatibility creates TCLS_SHAREDMEMEMORY+<GamePID> before ResumeThread
```

The buffer is zeroed because no offset/size/encoding for `GameSignature` or `JumpSignature` is confirmed in this workspace.

## Still unknown

```text
TCLS_SHAREDMEMEMORY full structure
GameSignature full structure
JumpSignature full structure
Exact Base bootstrap exit contract
Whether TCLS mapping is sufficient to increase BOOT_DEPTH
```

## Source layout

```text
CODOLLauncher/
  src/
    main.cpp
    Launcher.cpp
    Launcher.h
    GameProcess.cpp
    GameProcess.h
    LauncherContext.cpp
    LauncherContext.h
    TCLSCompatibility.cpp
    TCLSCompatibility.h
    BootstrapMonitor.cpp
    BootstrapMonitor.h
  config/
    CODOLLauncher.ini
  logs/
  build/
    CODOLLauncher.vcxproj
    build.ps1
```

## Build

This machine does not currently have `cl.exe`, `g++`, or `cmake` on PATH. The project includes:

1. `build\CODOLLauncher.vcxproj` for Visual Studio.
2. `build\build.ps1` for a machine with MSVC or MinGW on PATH.
3. `build\CODOLLauncher.cs` and the same build script fallback, which uses the installed .NET Framework `csc.exe` to produce a managed `CODOLLauncher.exe` with the same launch flow.

Once compiled, run:

```text
CODOLLauncher.exe --diagnostic
```

Logs are written to `logs\CODOLLauncher_*.log`.

## Known current limit

The direct double-click root cause in this workspace was Base bootstrap failing before returning to EXE. This launcher restores the only launcher IPC that historical TenProxy logs prove, keeps game/exe files untouched, and uses module loading plus known DLL names to infer `BOOT_DEPTH`. Actual progression past the current `BOOT_DEPTH=3` chain still requires a real build and test run on a machine with the game binaries available.

## Real empirical result on this machine

The managed launcher (`CODOLLauncher.exe --diagnostic`) successfully created `codoMP_client_shipRetail.exe` with `CREATE_SUSPENDED`, obtained `PID/TID`, created the optional `TCLS_SHAREDMEMEMORY+GamePID` mapping when enabled, then resumed the process.

Observed behavior:

```text
WITHOUT TCLS MAPPING:
  Game PID created
  Base.dll visible in module enumeration after resume
  libcef.dll visible in module enumeration after resume
  process later showed fatal-error window: Fatal Error (Chinese UI caption)
  BOOT_DEPTH=2 (module-based)

WITH TCLS MAPPING:
  Game PID created
  mapping name TCLS_SHAREDMEMEMORY+<PID> created before resume
  Base.dll visible in module enumeration after resume
  libcef.dll visible in module enumeration after resume
  process later showed fatal-error window: Fatal Error (Chinese UI caption)
  BOOT_DEPTH=2 (module-based)
```

Update: repeated runs with a longer module poll now load `codoMP_client_shipRetailBase.dll` and `libcef.dll` into the game process, so a non-immediate snapshot reports `BOOT_DEPTH=2`. The process still reaches the fatal-error window after this, consistent with the earlier reverse-engineering finding that Base/VM bootstrap starts but does not return to EXE before the crash path begins. The TCLS mapping alone did not move the observable module set beyond this in the test run. Exact signature bytes and required shared-memory fields remain unknown, so the next iteration should target those offsets from a captured successful old launch.
