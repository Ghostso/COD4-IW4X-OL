# CODOL EX-057 IIPS Runtime Boundary

## Scope

This round only studies the `iips.dll` initialization contract after a
normal `-q` launch. It does not change the EXE/DLL files, patch the fatal
path, fake a return value, or investigate Launcher/TCLS/WeGame prerequisites.

Target copy:

```text
工具/EX035_DIR
command: codoMP_client_shipRetail.exe -q
```

The main dynamic source is the non-invasive Kernel Image trace exported to
`Y:\ex057_kernel.xml`. The target process for the clean run was PID `16640`.

## Executive Result

The normal launch portion of the run proves this boundary:

```text
TenProxy.dll / GbSpy.dll
  -> iips.dll image load
  -> approximately 6.49 seconds of IIPS presence
  -> iips.dll image unload
  -> fatal path
```

Observed timestamps:

```text
TenProxy.dll load       15:35:06.424095
GbSpy.dll load          15:35:06.432142
iips.dll load           15:35:08.811948
iips.dll unload/rundown  15:35:15.306854
```

The Kernel Image provider emits adjacent load/unload-style records during
image rundown. For this reason, the interval above uses the final stable
`iips.dll` load at `15:35:08.812147` and the later unload/rundown at
`15:35:15.306854`; the two records immediately around the first load are not
treated as separate IIPS initialization attempts.

The controller attempted a CDB late attach immediately after observing the
IIPS load. Therefore the load event is normal-launch evidence, while the
exact unload timestamp is observer-qualified and is not used as proof of a
pure baseline teardown path.

During that interval, no image-load event was observed for:

```text
IFS2.dll
IIPSHostApp.exe
IIPSHost.dll
IIPSVFS.dll
Download.dll
```

This does **not** prove that `LoadLibraryW`, `GetProcAddress`, or any IIPS
internal function was not called. It proves only that none of the listed
modules produced a normal observable image-load event in this run.

Current precise boundary:

```text
iips.dll loaded
  -> IIPS internal execution / status conversion UNKNOWN
  -> no observed IFS2 or HostApp module
  -> fatal / iips.dll unload
```

The `0x8189FEC` source is still not assigned to a concrete IIPS basic block.

## IIPS Call Graph

The following graph is STATIC. Addresses are RVAs relative to the observed
`iips.dll` image base, not CODOL EXE addresses.

```text
CNIFS::InitInGameApp candidate        iips.dll + 0x9860
  |
  +-- QoS helper                       iips.dll + 0x6D20
  |     callsite                       + 0x98CD
  |     false result: log and continue
  |
  +-- CNIFS::initIfsLib candidate      iips.dll + 0x9570
  |     |
  |     +-- path construction containing "ifs2.dll"
  |     +-- LoadLibraryW                + 0x96E9
  |     |     NULL -> "Failed to open dllfile"
  |     |
  |     +-- GetProcAddress              + 0x977C
  |     |     name: "CreateIFSLibDll"
  |     |     NULL -> "Failed to get function CreateIFSLibDll"
  |     |
  |     +-- indirect CreateIFSLibDll    + 0x97A5
  |     |     EAX == 0 -> "Failed to create ifs lib"
  |     |
  |     +-- GetProcAddress              + 0x97CC
  |           name: "DestoryIFSLibDll"
  |           NULL -> "Failed to get proc DestoryIFSLibDll"
  |
  +-- GetPrivateProfileIntW             + 0x9A8B
  |     section/key: IIPSHostApp.ini / ResPool / ReservedSize
  |     default: 0x40000000
  |
  +-- resource-manager / HostApp path
        ResourceManagerII candidate     iips.dll + 0x15A00
        ShellExecuteExW                 + 0x15CD1
        success requires API success and hInstApp > 0x20
        failure text: "LaunchIIPSHostApp failed"

IIPS share-state candidate              iips.dll + 0x11930
  +-- OpenFileMappingA                  + 0x1194E
  |     name family: Global\\IIPSShareState_MMF_
  +-- CreateMutexA                      + 0x1197B
        name family: Global\\IIPSShareState_Mutex_
```

The `GetResourceManagerII` export at `iips.dll + 0x1C80` exists, but a
runtime caller was not recovered. Export presence is not runtime evidence.

## Dynamic Evidence Table

| Question | STATIC | DYNAMIC | INFERRED | Verdict |
|---|---|---|---|---|
| `0x8189FEC` exact function/basic block | EXE contains `WIN_IIPS_INIT_ERROR` data in a packed/VM boundary; no plaintext producer in EXE/Base/iips | No register or stack capture of the value | It is likely a packed/runtime-generated IIPS status converted at the EXE error boundary | **UNKNOWN** |
| `CNIFS::InitInGameApp` executed | Candidate `iips.dll + 0x9860` and a complete static contract exist | `iips.dll` loaded and `iipsinit` was seen in earlier normal probes; no function hit | IIPS initialization work probably began | **UNKNOWN at function level** |
| `LoadLibraryW("ifs2.dll")` executed | Callsite `iips.dll + 0x96E9` confirmed | No API call trace; no `IFS2.dll` image load | If reached, likely failed before a persistent IFS2 image appeared, but this is not proven | **UNKNOWN** |
| Actual IFS2 path | Static path builder contains `ifs2.dll`; file exists under `EX035_DIR\IIPS` | Actual argument pointer was not captured | Expected path is under the IIPS directory | **UNKNOWN** |
| `LoadLibraryW` return | Static NULL failure branch exists | EAX/return not captured | No IFS2 load is compatible with NULL or transient load/unload | **UNKNOWN** |
| `GetLastError` after load | Static error formatting path exists | No API return/error capture | Cannot assign Win32 error code | **UNKNOWN** |
| `GetProcAddress("CreateIFSLibDll")` | Static callsite and NULL branch confirmed | No resolver hit or return captured | Cannot distinguish missing export from earlier LoadLibrary failure | **UNKNOWN** |
| `CreateIFSLibDll()` execution | Static indirect call at `iips.dll + 0x97A5` | No call hit and no IFS2 image | Not reached, or reached through an unobserved/transient mechanism | **UNKNOWN** |
| `CreateIFSLibDll` return | Static EAX test and failure string confirmed | No EAX capture | Zero is a candidate only, not evidence | **UNKNOWN** |
| `DestoryIFSLibDll` resolution | Static resolver at `iips.dll + 0x97CC` | No call hit or return | Cannot determine whether IFS2 create stage completed | **UNKNOWN** |
| `IIPSHostApp.ini` read | Static `GetPrivateProfileIntW` callsite and config contract | No FileIO/API argument capture for this call | Config read may be after IFS2 success, so its absence is compatible with an earlier failure | **UNKNOWN** |
| `IIPSHostApp.exe` launch | Static `ShellExecuteExW` path at `iips.dll + 0x15CD1` | No HostApp image load and no HostApp process observed | HostApp branch was not reached, failed immediately, or was transient | **UNKNOWN at call level; no process observed** |
| Share-state path | Static mapping/mutex names and callsites | No mapping/mutex API trace in this round | May be an earlier or later internal prerequisite | **UNKNOWN** |

## Debugger / Observer Qualification

Two debugger attempts were intentionally not promoted to normal-run evidence.

1. Full-start CDB runs exposed the expected BugTrace `IsBadReadPtr` and C++
   exception path before IIPS. This changes timing and prevents a clean
   IIPS breakpoint result.
2. Late attach saw `iips.dll` in the target, but the process was already in
   its fatal/exit transition when CDB attached. CDB returned `No runnable
   debuggees`; no IIPS breakpoint was hit.

The final dynamic result therefore comes from the normal, non-pausing Kernel
Image trace, not from the debugger sessions.

## Current Minimal Failure Point

The smallest failure statement supported by all evidence is:

```text
IIPS initialization is entered at the module level,
but the first successful external dependency handoff below iips.dll
has not been observed.
```

For the requested A-G classification:

```text
A. DLL loading       UNKNOWN
B. Export resolving  UNKNOWN
C. CreateIFSLibDll   UNKNOWN
D. Config reading    UNKNOWN
E. HostApp startup   UNKNOWN at call level; process not observed
F. Shared state      UNKNOWN
G. Other internal    CURRENT BEST BOUNDARY / UNKNOWN DETAIL
```

`G` is not a claim that a particular internal check failed. It means the
observed boundary currently ends at `iips.dll`'s internal/packed status
handoff, before any one of A-F has been dynamically proven.

The highest-value candidate for the next boundary experiment is the first
branch in `CNIFS::initIfsLib`:

```text
LoadLibraryW(ifs2 path)
  -> return value
  -> GetLastError immediately on NULL
```

That is a test target, not the current root-cause verdict.

## What Is Now Proven

```text
STATIC:
  iips.dll contains the CNIFS/IFS2/HostApp/share-state branch structure.
  iips.dll contains distinct failure branches for load, export, create,
  destroy-export, and HostApp launch.

DYNAMIC:
  normal -q loads iips.dll after TenProxy/GbSpy.
  iips.dll remains observable for roughly 6.49 seconds and then unloads.
  no IFS2.dll or IIPSHostApp.exe image load appears in that interval.
  no IIPSHostApp process appears in the existing normal-run observations.

INFERRED:
  the failing transition is inside IIPS or at its packed/VM status handoff,
  before the next visible external module boundary.
```

## Next Experiment

The next experiment should be a single-variable, non-pausing API capture that
starts before the process and filters calls whose return address belongs to
`iips.dll`:

```text
1. Capture LoadLibraryW entry/return only when caller is iips.dll.
2. Capture GetLastError immediately after that LoadLibraryW call if EAX=0.
3. Capture GetProcAddress only when the name is CreateIFSLibDll or
   DestoryIFSLibDll.
4. Capture the indirect CreateIFSLibDll call and its EAX return.
5. Capture GetPrivateProfileIntW and ShellExecuteExW with the caller filter.
6. Keep the normal -q command, same working directory, same files.
```

The success criterion is a caller-filtered return-value record. A module
timeline alone is no longer sufficient to choose between A, B, C, D, E, F,
and G.

## Final Classification

```text
IIPS_MODULE_LOAD_DYNAMIC_CONFIRMED
IIPS_MODULE_UNLOAD_DYNAMIC_CONFIRMED
IFS2_IMAGE_LOAD_NOT_OBSERVED
IIPSHOSTAPP_IMAGE_LOAD_NOT_OBSERVED
IIPS_INTERNAL_CALLS_UNKNOWN
8189FEC_EXACT_SOURCE_UNKNOWN
MINIMAL_BOUNDARY_IIPS_INTERNAL_OR_PACKED_HANDOFF
NO_BINARY_PATCH
NO_SECURITY_CHECK_REMOVED
NO_SUCCESS_RETURN_FAKED
```
