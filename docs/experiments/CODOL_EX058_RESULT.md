# CODOL EX-058 RESULT

## Scope

EX-058 only attempted caller-filtered observation of `iips.dll`'s external
API contract during a normal `-q` launch. No CODOL binary was patched, no
IIPS return value was changed, no fatal branch was skipped, and no alternate
implementation was injected.

Target:

```text
工具/EX035_DIR/codoMP_client_shipRetail.exe -q
```

## Result Summary

The requested API-level first failure was **not dynamically captured**.
Every attempted breakpoint-based path changed or interrupted the CODOL
startup state before the target reached the normal IIPS call window.

The strongest valid result remains the normal-run ETW evidence from EX-057:

```text
TenProxy.dll / GbSpy.dll
  -> iips.dll image load at approximately 15:35:08.812
  -> no observed IFS2.dll image load
  -> no observed IIPSHostApp.exe image/process
  -> iips.dll image cleanup/unload around 15:35:15.307
```

That evidence does not identify which IIPS API was called or returned an
error.

## Caller-Filtered Attempts

| Attempt | Method | Result | Classification |
|---|---|---|---|
| EX-058-A | Start under x86 debug event loop; install IIPS breakpoints only after `iips.dll` load | Target exited with `0xC0000409` before `iips.dll` load event | `OBSERVER_DIVERGENCE` |
| EX-058-B | Normal start, attach at approximately 250 ms | `DebugActiveProcess` failed with Win32 error 5 | `ATTACH_FAILED` |
| EX-058-C | Normal start, attach at approximately 4 s | `DebugActiveProcess` failed with Win32 error 5 | `ATTACH_FAILED` |
| EX-058-D | Normal start, attach at approximately 1 s with `SeDebugPrivilege` attempt | Attach succeeded, but target exited with `0xC0000409` before IIPS load | `OBSERVER_DIVERGENCE` |

The privilege call reported `ok=True` but `GetLastError=1300`
(`ERROR_NOT_ALL_ASSIGNED`), so a fully effective debug privilege was not
available in this user session.

## Requested API Timeline

The following is the complete EX-058 status. `UNKNOWN` means no
caller-filtered entry or return record was captured.

| API / operation | IIPS static callsite | Caller-filtered dynamic entry | Return / error | Result |
|---|---:|---|---|---|
| `LoadLibraryW` for IFS2 | `iips.dll+0x96E9` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `GetLastError` after LoadLibraryW | error branch after `+0x96EF` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `GetProcAddress("CreateIFSLibDll")` | `iips.dll+0x977C` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `CreateIFSLibDll` indirect call | `iips.dll+0x97A5` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `GetProcAddress("DestoryIFSLibDll")` | `iips.dll+0x97CC` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `GetPrivateProfileIntW` | `iips.dll+0x9A8B` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `ShellExecuteExW` | `iips.dll+0x15CD1` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `OpenFileMappingA` | `iips.dll+0x1194E` | UNKNOWN | UNKNOWN | `UNKNOWN` |
| `CreateMutexA` | `iips.dll+0x1197B` | UNKNOWN | UNKNOWN | `UNKNOWN` |

## Static Contract Used By EX-058

```text
CNIFS::InitInGameApp candidate     iips.dll+0x9860
  -> QoS helper                    iips.dll+0x6D20
  -> CNIFS::initIfsLib             iips.dll+0x9570
      -> LoadLibraryW              iips.dll+0x96E9
      -> GetProcAddress(CreateIFSLibDll)  iips.dll+0x977C
      -> CreateIFSLibDll            iips.dll+0x97A5
      -> GetProcAddress(DestoryIFSLibDll) iips.dll+0x97CC
  -> GetPrivateProfileIntW         iips.dll+0x9A8B

ResourceManagerII / HostApp candidate
  -> ShellExecuteExW               iips.dll+0x15CD1

IIPS shared-state candidate
  -> OpenFileMappingA               iips.dll+0x1194E
  -> CreateMutexA                   iips.dll+0x1197B
```

These are STATIC callsites. They are not execution claims.

## First Failure API

```text
FIRST_FAILURE_API = UNKNOWN
```

The evidence does not distinguish the requested alternatives:

```text
A. LoadLibraryW was not called
B. LoadLibraryW was called and returned NULL
C. LoadLibraryW succeeded, but a later IFS2 step failed
D. IIPS failed before the CNIFS path reached LoadLibraryW
E. HostApp/share-state path failed before or after another internal check
F. Packed/VM IIPS status was converted before the public error boundary
G. Other internal IIPS check
```

In particular:

```text
no IFS2.dll image event != no LoadLibraryW call
```

This remains an explicit UNKNOWN, as required.

## `0x8189FEC` Relationship

| Link | Status |
|---|---|
| `iips.dll` was loaded before the fatal state | DYNAMIC CONFIRMED by normal ETW |
| IIPS-specific fatal state followed the module phase | DYNAMIC/temporal evidence |
| `0x8189FEC` was returned by `CreateIFSLibDll` | UNKNOWN |
| `0x8189FEC` equals `GetLastError` from `LoadLibraryW` | UNKNOWN |
| `0x8189FEC` was produced by a known IIPS basic block | UNKNOWN |
| `0x8189FEC` was converted by packed/VM EXE code | INFERRED candidate, not proven |

The exact error source remains outside the currently observable plain-code
boundary.

## Why EX-058 Did Not Close The API Boundary

The machine's normal run and debug run are observably different. Existing
evidence already established that breakpoints around BugTrace cause the
project module chain to disappear. EX-058 reproduced the same class of
problem:

```text
normal run       -> TenProxy -> GbSpy -> iips.dll
debugged run     -> BugTrace/CRT or stack-cookie exit before iips.dll
```

Late attachment is also not reliable on this process. At some timings it is
rejected with error 5; at another timing it attaches but the target exits
with `0xC0000409` before IIPS. The IIPS API breakpoint handler itself was
never reached, so no API result is being withheld or guessed.

## Current Boundary

```text
iips.dll
  -> internal IIPS dispatcher / packed status path
  -> WIN_IIPS_INIT_ERROR / 0x8189FEC
```

The boundary is narrower than before at the module level, but not yet at the
first external API.

## Next Experiment

Do not expand parameter matrices and do not patch IIPS. The next permitted
step should use a caller-preserving, non-pausing observation mechanism that
can record user-mode call stacks or API returns without attaching a debugger
to the live CODOL process. The capture must emit only records satisfying:

```text
return_address in [iips.dll base, iips.dll base + image size)
```

The first target remains:

```text
iips.dll+0x96E9 -> LoadLibraryW return -> GetLastError
```

If that call is absent, move to the first branch in `CNIFS::InitInGameApp`
before `iips.dll+0x96E9`; if it is present, continue to the resolver and
indirect `CreateIFSLibDll` call.

## Final Classification

```text
IIPS_MODULE_LOAD_DYNAMIC_CONFIRMED
CALLER_FILTERED_LOADLIBRARYW_UNKNOWN
CALLER_FILTERED_GETPROCADDRESS_UNKNOWN
CALLER_FILTERED_CREATEIFS_UNKNOWN
CALLER_FILTERED_PROFILE_READ_UNKNOWN
CALLER_FILTERED_HOSTAPP_LAUNCH_UNKNOWN
FIRST_FAILURE_API_UNKNOWN
8189FEC_EXACT_SOURCE_UNKNOWN
DEBUGGER_OBSERVER_DIVERGENCE_REPRODUCED
NO_PATCH
NO_FAKE_SUCCESS
```
