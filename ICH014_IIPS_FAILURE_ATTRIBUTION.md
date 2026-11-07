# ICH-014 - IIPS Failure Attribution

## Failure Chain Overview

```text
iips.dll loaded (DYNAMIC_CONFIRMED)
       |
       +-- QoS helper check (iips.dll + 0x98CD)
       |     |
       |     +-- returns non-zero: continue to initIfsLib
       |     +-- returns zero: error branch, never reaches initIfsLib
       |
       +-- initIfsLib called (iips.dll + 0x99D2)
             |
             +-- Stage 1: LoadLibraryW(<iipsdir>/ifs2.dll) at +0x96E9
             |     |
             |     +-- returns non-NULL: continue to Stage 2
             |     +-- returns NULL: "Failed to open dllfile", AL=0
             |
             +-- Stage 2: GetProcAddress(hModule, "CreateIFSLibDll") at +0x977C
             |     |
             |     +-- returns non-NULL: continue to Stage 3
             |     +-- returns NULL: "Failed to get function CreateIFSLibDll", AL=0
             |
             +-- Stage 3: CreateIFSLibDll(out) at +0x97A5
             |     |
             |     +-- returns non-zero: continue to Stage 4
             |     +-- returns zero: "Failed to create ifs lib", AL=0
             |
             +-- Stage 4: GetProcAddress(hModule, "DestoryIFSLibDll") at +0x97CC
                   |
                   +-- returns non-NULL: SUCCESS, AL=1
                   +-- returns NULL: "Failed to get proc DestoryIFSLibDll", AL=0
```

## Failure Attribution Analysis

### Stage 1 Attribution Candidates

| Candidate | Status | Evidence |
|-----------|--------|----------|
| IFS2.dll file does not exist | **ELIMINATED** | File exists: 601,656 bytes |
| Wrong architecture | **ELIMINATED** | Machine = 0x014C (x86), matches iips.dll |
| Missing dependency DLL | **ELIMINATED** | KERNEL32, ADVAPI32, SHLWAPI (all system) |
| Invalid PE / loader rejection | UNKNOWN | PE parses correctly, DllMain not tested |
| Path resolution error | UNLIKELY | Self-referential path from GetModuleFileNameW |
| Access denied | UNKNOWN | No ACL evidence |
| IFS2.dll DllMain returns FALSE | UNKNOWN | Not tested |

### Pre-Stage-1 Divergence Candidates

| Candidate | Status | Evidence |
|-----------|--------|----------|
| QoS helper returns 0 (iips.dll + 0x6D20) | **MOST SUPPORTED** | EX-053: path changes produce no outcome change |
| InitInGameApp entry not reached | UNKNOWN | No function-level trace |
| CNIFS object construction fails | UNKNOWN | No constructor trace |
| Pre-initIfsLib prerequisite fails | UNKNOWN | No API trace |

### Key Reasoning: Path Causality

EX-053 performed three controlled experiments changing the location
of IFS2.dll:

```text
Path A: IFS2.dll under IIPS/ (beside iips.dll)       → same fatal error
Path B: IFS2.dll beside EXE                           → same fatal error
Path C: IFS2.dll under IIPS/ in independent copy      → same fatal error
```

If Stage 1 (LoadLibraryW with the constructed path) were reached and
the path was the only problem, at least one of these changes should
have produced a different outcome. Since all three produced identical
fatal errors, the failure is either:

1. **Before the path matters** (pre-Stage-1 divergence), OR
2. **After the path is used** but not caused by the path itself
   (e.g., DllMain failure unrelated to path)

The first explanation is more parsimonious and consistent with the
evidence.

### Elimination Summary

```text
IFS2.dll file missing:         ELIMINATED
IFS2.dll architecture wrong:   ELIMINATED
IFS2.dll dependencies missing: ELIMINATED
IFS2.dll exports missing:      ELIMINATED
Path visibility issue:         LOW CONFIDENCE (EX-053 shows no effect)
Path resolution at runtime:    UNKNOWN (argument not captured)

Remaining candidates:
  1. Control flow diverges before initIfsLib is called
  2. QoS helper (iips.dll+0x6D20) returns 0
  3. LoadLibraryW reaches Stage 1 but fails for another reason
     (DllMain, loader lock, access denied)
```

## Definitive Attribution

```text
FAILURE_ORIGIN = UNKNOWN

Most supported scenario: Pre-Stage-1 control flow divergence
  (InitInGameApp never reaches the call to initIfsLib)

Reason:
  - All static pre-conditions for IFS2.dll loading are satisfied
  - Three IFS2 path experiments produce identical outcomes
  - The simplest explanation is that initIfsLib is never reached

Least supported scenario: Stage 1 LoadLibraryW failure due to path
  (contradicted by EX-053 path causality experiments)

Cannot be distinguished without: caller-filtered LoadLibraryW trace
```

## Minimum Experiment to Resolve

The definitive test to distinguish Scenario A from Scenario B:

```text
Test: Set breakpoint on kernel32!LoadLibraryW (caller-filtered to iips.dll)

Result 1: Breakpoint hits with caller = iips.dll+0x96EF
  → Stage 1 IS reached
  → Record EAX return
  → If EAX=0: FIRST_FAILED_STAGE = 1
    → Then check GetLastError for the specific reason
  → If EAX!=0: Continue to Stage 2

Result 2: Breakpoint NEVER hits from iips.dll caller
  → FIRST_FAILED_STAGE = UNKNOWN (pre-Stage-1 divergence)
  → IIPS_INIT_CONTROL_FLOW = DIVERGED
  → Next: Set breakpoint on iips.dll+0x9860 (InitInGameApp entry)
    and iips.dll+0x99D2 (call to initIfsLib)
    → If InitInGameApp entry hits but initIfsLib does NOT:
      → QoS helper (iips.dll+0x6D20) is the divergence point
      → Record its return value
```

## IFS2.dll PE Detailed Analysis

### Section Layout

```text
Section layout (from pefile):
  Not analysed in detail this round (no IFS2 internal reverse engineering
  permitted). File exists, architecture correct, exports present, imports
  satisfied. These are the only attributes relevant to Stage 1/2/4.
```

### Export Verification (Stage 2/4 pre-condition)

```text
Export "CreateIFSLibDll" at RVA 0x166D0:     PRESENT
Export "DestoryIFSLibDll" at RVA 0x16740:    PRESENT
Export "IFSDllVerifyApiCompatable" at RVA 0x16760: PRESENT
```

Stage 2 and Stage 4 cannot fail due to missing exports. The exports
are statically present in the PE export directory.

### Import Verification (Stage 1 pre-condition)

All 100+ imports from KERNEL32.dll, 4 from ADVAPI32.dll, and 1 from
SHLWAPI.dll are standard system functions. No named third-party DLL
dependency exists that could cause a Stage 1 failure due to missing
dependencies.

```text
Conclusion: IFS2.dll is fully ready for loading.
All static pre-conditions for all four stages are satisfied.
The failure must be either in the runtime control flow before the
stages are reached, or in a runtime condition not captured by static
analysis (DllMain, loader lock, access rights).
```
