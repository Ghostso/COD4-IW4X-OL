# ICH-016 - IIPS/IFS2 Load Analysis

## Combined Evidence Chain (ICH-008 through ICH-016)

```text
ICH-008:  VM → Platform transfer            CONFIRMED
ICH-009:  Platform → Engine                 NOT_OBSERVED (0/439 events)
ICH-010:  IIPS module load                  CONFIRMED; IFS2 never loads
ICH-011:  BugTrace role = Platform/anti-cheat  CONFIRMED
ICH-012:  Unknown Native Layer              RESOLVED (Base .tvm0)
ICH-013:  IIPS gate = FAILURE at 0x8189FEC  CONFIRMED (boundary)
ICH-014:  Four-stage static pre-conditions  ALL SATISFIED; runtime UNKNOWN
ICH-015:  Debugger observability            BLOCKED (anti-cheat prevents iips.dll load)
ICH-016:  Normal startup loader causality   iips loads 3/3, IFS2 loads 0/3
```

## Refined Startup Sequence (ICH-016 confirmed)

```text
Process Start
  ↓
KERNELBASE.dll, ucrtbase.dll, combase.dll, CRYPTBASE.DLL   (system init)
  ↓
codoMP_client_shipRetailBase.dll                            (platform VM host)
  ↓
BugTrace.dll                                                (anti-cheat/telemetry)
  ↓
[anti-cheat validation cycles: unload/reload]
  ↓
TenProxy.dll, GbSpy.dll                                     (platform proxy + spy)
  ↓
iips.dll IMAGE_LOAD                                         ← IIPS reached
  ↓
[IFS2.dll should load here if Stage 1 is reached]           ← NEVER OBSERVED
  ↓
[pre-Stage-1 divergence OR Stage 1 transient failure]
  ↓
WIN_IIPS_INIT_ERROR / 0x8189FEC
  ↓
Process termination
```

## Stage 1 Status Assessment

```text
STAGE1_STATUS = NOT_OBSERVED

Two scenarios remain compatible with all evidence:

Scenario A: LoadLibraryW("IFS2.dll") called, returns NULL
  - IFS2.dll DllMain fails
  - Or loader rejects the DLL for an unseen reason
  - Or path resolution fails at runtime
  - Load/unload completes within <10ms (below polling resolution)

Scenario B: LoadLibraryW("IFS2.dll") NEVER called
  - Control flow diverges before initIfsLib entry
  - QoS helper (iips.dll+0x6D20) returns 0
  - Or InitInGameApp fails before calling initIfsLib
  - No IFS2 load attempt ever occurs

Scenario B is more strongly supported because:
  1. EX-053: three IFS2 path changes produce identical outcomes
  2. ICH-014: all static pre-conditions are satisfied
  3. ICH-016: 3/3 runs show no IFS2 ImageLoad at 10ms resolution
  4. A 600KB DLL load typically takes >1ms and spans multiple polling cycles

However, Scenario A cannot be conclusively excluded because:
  1. 10ms polling has a theoretical blind spot for sub-10ms loads
  2. No caller-filtered LoadLibraryW trace is available
```

## Primary Blocking Boundary (Refined)

```text
PRIMARY_BLOCKING_BOUNDARY = 
  IIPS initialization gate, refined to:
  pre-Stage-1 control flow divergence (most supported)
  OR Stage 1 LoadLibraryW transient failure (cannot exclude)

The boundary is inside iips.dll, after successful module load,
before any successful external dependency handoff to IFS2.
```

## What Has Been Excluded

| Component | Status | Evidence |
|-----------|--------|----------|
| IFS2.dll file missing | ELIMINATED | File exists (601KB, ICH-014) |
| IFS2.dll wrong architecture | ELIMINATED | x86, matches iips.dll |
| IFS2.dll missing exports | ELIMINATED | CreateIFSLibDll/DestoryIFSLibDll present |
| IFS2.dll missing dependencies | ELIMINATED | All imports are system DLLs |
| IFS2.dll path visibility | LOW IMPACT | EX-053: 3 path changes → no change |
| Unknown Native Layer | EXCLUDED | ICH-009 resolved 0x5F796178 |
| BugTrace → IIPS bridge | EXCLUDED | ICH-011: no shared call chain |
| Engine region reached | EXCLUDED | ICH-009: 0/439 events |

## What Remains Unknown

| Question | Status | Required Method |
|----------|--------|----------------|
| Is initIfsLib called at runtime? | UNKNOWN | Kernel ETW callstack |
| Is LoadLibraryW called from iips.dll? | UNKNOWN | Kernel ETW callstack |
| Does QoS helper return 0? | UNKNOWN | Kernel ETW callstack |
| What exact stage fails? | UNKNOWN | Kernel ETW callstack |
| Is there a sub-10ms IFS2 load? | UNKNOWN | Microsecond ETW trace |

## IFS2 Runtime Load Status

```text
IFS2_RUNTIME_LOAD = NOT_OBSERVED
```

Across ICH-010, ICH-014, ICH-015, and ICH-016, IFS2.dll has never been
observed as a loaded module in any run under any condition. Combined
with all static pre-conditions being satisfied, this points to a
failure that occurs before or at the moment of the first external
dependency call from iips.dll.
