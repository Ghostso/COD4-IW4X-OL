# CODOL EX-059 RESULT

## Scope

EX-059 was limited to non-invasive telemetry during a normal:

```text
codoMP_client_shipRetail.exe -q
```

The following were not used:

```text
DebugActiveProcess
debugger attach
software breakpoint
hardware breakpoint
SuspendThread / single-step
target patch
iips.dll patch
fake return value
Fatal bypass
Frida Interceptor / runtime code hook
```

The Frida files prepared during exploration were removed before any Frida
run. Frida `Interceptor` would rewrite target API entrypoints at runtime and
would violate this round's no-patch requirement, even if disk files remained
unchanged.

## Available Non-Invasive Telemetry

The existing normal-run Kernel Image/File telemetry can establish:

```text
process and thread events
image load/unload events
some kernel file events
```

It cannot establish:

```text
user-mode API ReturnAddress
LoadLibraryW return HMODULE
GetLastError immediately after LoadLibraryW
GetProcAddress returned address
GetPrivateProfileIntW return value
ShellExecuteExW return value
CreateIFSLibDll EAX
```

The registered `Microsoft-Windows-Kernel-Audit-API-Calls` provider was
queried, but a usable independent trace session could not be created in the
current non-elevated environment. Existing kernel sessions were not
reconfigured or disturbed.

## Normal Dynamic Facts Reused

EX-057's normal `-q` run remains valid module-level evidence:

```text
TenProxy.dll / GbSpy.dll
  -> iips.dll image load
  -> no observed IFS2.dll image load
  -> no observed IIPSHostApp.exe image/process
  -> iips.dll cleanup/unload
  -> WIN_IIPS_INIT_ERROR / 0x8189FEC
```

The module observation does not answer whether `LoadLibraryW("ifs2.dll")`
was called:

```text
no IFS2.dll image event != no LoadLibraryW call
```

EX-059 also ran a fresh non-invasive normal module baseline with PID
`19464`. Its observed IIPS period was:

```text
iips.dll first seen  t=9.163 s
iips.dll gone        t=14.368 s
```

The final module set contained `iips.dll`, but did not contain `IFS2.dll` or
`IIPSHostApp.exe`. This confirms the EX-057 module-level result on a new
normal run; it does not upgrade any API-level field below.

## Required Result Fields

```text
LOADLIBRARY_IIPS_CALL = UNKNOWN
IFS2_LOAD_RESULT = UNKNOWN
IFS2_PATH = UNKNOWN
LOADLIBRARY_LAST_ERROR = UNKNOWN
CREATEIFS_RESOLUTION = UNKNOWN
CREATEIFS_EXECUTION = UNKNOWN
CREATEIFS_RETURN = UNKNOWN
PROFILE_READ = unknown
HOSTAPP_LAUNCH = unknown
FIRST_OBSERVED_IIPS_EXTERNAL_FAILURE = UNKNOWN
```

No caller-filtered user-mode API event was accepted in this round. There is
therefore no valid ReturnAddress record satisfying:

```text
iips_base <= ReturnAddress < iips_base + iips_size
```

## STATIC / DYNAMIC / INFERRED

### STATIC

The following callsites remain statically established:

```text
CNIFS::InitInGameApp candidate       iips.dll+0x9860
CNIFS::initIfsLib candidate          iips.dll+0x9570
LoadLibraryW                         iips.dll+0x96E9
GetProcAddress(CreateIFSLibDll)      iips.dll+0x977C
CreateIFSLibDll indirect call        iips.dll+0x97A5
GetProcAddress(DestoryIFSLibDll)     iips.dll+0x97CC
GetPrivateProfileIntW                iips.dll+0x9A8B
ShellExecuteExW                      iips.dll+0x15CD1
OpenFileMappingA                     iips.dll+0x1194E
CreateMutexA                         iips.dll+0x1197B
```

Static branch contracts:

```text
LoadLibraryW NULL       -> "Failed to open dllfile"
Create resolver NULL    -> "Failed to get function CreateIFSLibDll"
CreateIFSLibDll EAX=0  -> "Failed to create ifs lib"
Destroy resolver NULL   -> "Failed to get proc DestoryIFSLibDll"
```

### DYNAMIC

```text
iips.dll module load in a normal -q run: CONFIRMED by EX-057
IFS2.dll image load: NOT_OBSERVED by EX-057 telemetry
IIPSHostApp.exe image/process: NOT_OBSERVED by existing normal-run telemetry
caller-filtered LoadLibraryW: NOT_CAPTURED
caller-filtered GetProcAddress: NOT_CAPTURED
caller-filtered CreateIFSLibDll: NOT_CAPTURED
caller-filtered profile read: NOT_CAPTURED
caller-filtered ShellExecuteExW: NOT_CAPTURED
```

### INFERRED

```text
IIPS internal or packed status handling is the current module-level
boundary before the next visible IFS2/HostApp image.
```

This is an inference only. It does not select A-G as the first failure.

## A-G Classification

```text
A. LoadLibraryW failure       UNKNOWN
B. GetProcAddress failure     UNKNOWN
C. CreateIFSLibDll failure    UNKNOWN
D. Configuration read failure UNKNOWN
E. HostApp launch failure     UNKNOWN
F. Shared-state failure       UNKNOWN
G. Other internal check       UNKNOWN
```

No category can be promoted from temporal module absence to an API failure.

## First Failure

```text
FIRST_OBSERVED_IIPS_EXTERNAL_FAILURE = UNKNOWN
```

This is the correct result under the caller-filter requirement. The round
did not obtain a valid first external API return and did not alter CODOL to
make one observable.

## `0x8189FEC` Relationship

```text
STATIC:
  WIN_IIPS_INIT_ERROR data and IIPS failure branches are present.

DYNAMIC:
  iips.dll loads before the normal fatal outcome.
  no caller-filtered API return carrying 0x8189FEC was captured.

INFERRED:
  0x8189FEC may be packed/runtime-generated or converted at the EXE/IIPS
  boundary, but its relation to LoadLibraryW/GetProcAddress/CreateIFSLibDll
  is UNKNOWN.
```

## Next Experiment

The next useful experiment requires a telemetry mechanism that can observe
user-mode API entry/return and call stacks without modifying target code or
suspending the target. The mechanism must expose a real call stack or
ReturnAddress and preserve the immediate `GetLastError` read.

If that capability is unavailable in the current machine without elevated
ETW/API tracing support, the next permitted action is static caller recovery
around `iips.dll+0x9860` and `iips.dll+0x9570`, not a guessed runtime result.

## Final Classification

```text
NONINTRUSIVE_IMAGE_TELEMETRY_CONFIRMED
USERMODE_API_RETURN_TELEMETRY_UNAVAILABLE
LOADLIBRARY_IIPS_CALL_UNKNOWN
IFS2_LOAD_RESULT_UNKNOWN
CREATEIFS_RESOLUTION_UNKNOWN
CREATEIFS_EXECUTION_UNKNOWN
PROFILE_READ_UNKNOWN
HOSTAPP_LAUNCH_UNKNOWN
FIRST_FAILURE_API_UNKNOWN
8189FEC_EXACT_SOURCE_UNKNOWN
NO_TARGET_MODIFICATION
NO_FATAL_BYPASS
```
