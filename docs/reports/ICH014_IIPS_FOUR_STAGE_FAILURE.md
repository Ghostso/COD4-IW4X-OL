# ICH-014 - IIPS Four-Stage Initialization Failure Localization

## Objective

Determine which of the four IIPS initialization stages fails first at
runtime: Stage 1 (LoadLibraryW), Stage 2 (GetProcAddress CreateIFSLibDll),
Stage 3 (CreateIFSLibDll call), or Stage 4 (GetProcAddress DestoryIFSLibDll).

## Evidence Basis

- EX-057: normal -q kernel image trace (iips.dll loads/unloads, IFS2 never appears)
- EX-053: three IFS2 path causality experiments (no outcome change)
- EX-050: static IIPS failure branch reconstruction
- EX-060: IIPS CFG closure, LoadLibraryW callsite analysis
- ICH-013: IIPS gate status and 0x8189FEC classification
- IFS2.dll PE analysis (this round)
- CODOL EXE PE section layout (this round)

## Static Pre-Condition Verification

### IFS2.dll File Verification

```text
File:           COD OL\IIPS\IFS2.dll
Size:           601,656 bytes
Exists:         YES
```

### IFS2.dll Architecture

```text
Machine:        0x014C (IMAGE_FILE_MACHINE_I386 / x86 32-bit)
ImageBase:      0x10000000
EntryPoint RVA: 0x51A94
Architecture:   CORRECT (matches iips.dll and EXE, both PE32/I386)
```

### IFS2.dll Exports

```text
CreateIFSLibDll:           RVA 0x166D0  PRESENT
DestoryIFSLibDll:          RVA 0x16740  PRESENT
IFSDllVerifyApiCompatable: RVA 0x16760  PRESENT
```

Both required exports exist. Stage 2 and Stage 4 cannot fail due to
missing exports.

### IFS2.dll Imports

```text
KERNEL32.dll:  100+ standard functions (file I/O, memory, threads, sync)
ADVAPI32.dll:  4 functions (process token, privileges)
SHLWAPI.dll:   1 function (StrTrimW)
```

All imports are standard Windows system DLLs. No third-party or
missing dependency identified. Stage 1 cannot fail due to missing
dependency DLLs.

### IFS2.dll Direct Dependency Availability

```text
KERNEL32.dll:  Already loaded in every process, always available
ADVAPI32.dll:  Standard system DLL, always available
SHLWAPI.dll:   Standard system DLL, always available
```

No dependency failure scenario exists for Stage 1.

## Four-Stage Static Gate Structure (confirmed in ICH-013)

```text
initIfsLib entry:        iips.dll + 0x9570

Stage 1: LoadLibraryW(<iipsdir>/ifs2.dll)
  callsite:              iips.dll + 0x96E9 (call [0x10033010])
  test eax:              iips.dll + 0x96EF
  success:               jne 0x9770 (continue to Stage 2)
  failure:               [ebp+0xCC]=1, "Failed to open dllfile", AL=0
  failure exit:          0x971C, 0x9769 (xor al,al), ret 0x20

Stage 2: GetProcAddress(hModule, "CreateIFSLibDll")
  callsite:              iips.dll + 0x977C (call esi = [0x10033014])
  test eax:              iips.dll + 0x977E
  success:               jne 0x97A1
  failure:               [ebp+0xCC]=2, "Failed to get function CreateIFSLibDll", AL=0

Stage 3: CreateIFSLibDll(out [this+0x50])
  callsite:              iips.dll + 0x97A5 (call eax)
  test eax:              iips.dll + 0x97A7
  success:               jne 0x97C3
  failure:               [ebp+0xCC]=1, "Failed to create ifs lib", AL=0

Stage 4: GetProcAddress(hModule, "DestoryIFSLibDll")
  callsite:              iips.dll + 0x97CC (call esi)
  test eax:              iips.dll + 0x97CE
  success:               jne 0x97F4
  failure:               [ebp+0xCC]=3, "Failed to get proc DestoryIFSLibDll", AL=0

Success exit:            0x97F4, cleanup, 0x9837, mov al,1, ret 0x20
```

## Runtime Observation

### What is dynamically confirmed

```text
iips.dll module load:    DYNAMIC_CONFIRMED (EX-057 kernel image trace)
iips.dll module unload:  DYNAMIC_CONFIRMED (EX-057, ~6.49s window)
IFS2.dll module load:    NOT_OBSERVED (across all runs and all path experiments)
IFS2.dll module unload:  NOT_OBSERVED
IIPSHostApp.exe load:    NOT_OBSERVED
```

### What is dynamically unknown

```text
LoadLibraryW(ifs2.dll) called:     UNKNOWN (no caller-filtered API trace)
LoadLibraryW return value:         UNKNOWN
LoadLibraryW GetLastError:         UNKNOWN
GetProcAddress(CreateIFSLibDll):   UNKNOWN
CreateIFSLibDll() execution:       UNKNOWN
CreateIFSLibDll() return:          UNKNOWN
GetProcAddress(DestoryIFSLibDll):  UNKNOWN
initIfsLib return value:           UNKNOWN
InitInGameApp return value:        UNKNOWN
```

### EX-058 Scenario Analysis (still unresolved)

```text
Scenario A: LoadLibraryW was NOT called (pre-initIfsLib divergence)
Scenario B: LoadLibraryW was called and returned NULL
Scenario C: LoadLibraryW succeeded but a later IFS2 step failed
Scenario D: IIPS failed before the CNIFS path reached LoadLibraryW

All four scenarios remain compatible with the observed evidence.
No caller-filtered API trace exists to distinguish them.
```

## Analysis

### Elimination Analysis for Stage 1

Given the static pre-condition verification:

| Possible Stage 1 Failure Reason | Eliminated? | Evidence |
|--------------------------------|-------------|----------|
| DLL file does not exist | YES | IFS2.dll exists (601,656 bytes) |
| Wrong architecture | YES | IFS2.dll is x86 (0x14C), same as iips.dll |
| Missing dependency DLL | YES | All imports are standard system DLLs |
| Loader rejection (invalid PE) | NO | PE parses correctly but DllMain not tested |
| Path error | UNLIKELY | Path is self-referential: GetModuleFileNameW(iips.dll) + "ifs2.dll" |
| Access denied (permissions) | NO | Not tested (no ACL capture) |
| IFS2.dll DllMain returns FALSE | NO | No evidence either way |

**Conclusion:** The three most common Stage 1 failure reasons (file
missing, wrong architecture, missing dependencies) are all eliminated.
If Stage 1 is reached and executes, IFS2.dll should load successfully
under normal conditions.

### Control Flow Divergence Assessment

Since IFS2.dll satisfies all static pre-conditions yet never loads,
there are two possibilities:

**Possibility 1: Stage 1 is reached and fails**
- LoadLibraryW returns NULL despite valid file and dependencies
- Cause would be: DllMain failure, loader lock, or access denied
- This is possible but requires unusual environmental conditions

**Possibility 2: Control flow diverges before Stage 1**
- The code never reaches iips.dll + 0x96E9
- The failure occurs in InitInGameApp before the call to initIfsLib
- Candidate divergence point: InitInGameApp + 0x98D2 (QoS helper check)
  ```asm
  0x98CD: call 0x10006D20        ; QoS helper
  0x98D2: test al, al
  0x98D4: jne 0x100098E6         ; success: continue to initIfsLib
  0x98D6: push 0x10034A34        ; failure: error string
  ```
- If the QoS helper returns 0, InitInGameApp enters an error branch
  and never calls initIfsLib, meaning LoadLibraryW is never reached

**The EX-053 evidence supports Possibility 2:** Three IFS2 path variants
produce identical outcomes. If Stage 1 were reached and the path was
the only issue, changing the path should change the outcome. Since it
does not, the failure is likely BEFORE the path matters.

## Final Answer

```text
FIRST_FAILED_STAGE = UNKNOWN

Two compatible scenarios remain:
  Scenario A: Stage 1 (LoadLibraryW) reached but returns NULL
  Scenario B: Control flow diverges before Stage 1 (pre-initIfsLib failure)

The caller-filtered LoadLibraryW trace required to distinguish these
scenarios has not been performed in any prior round.
```

### Stage-by-Stage Status

```text
STAGE1_IFS2_LOAD = NOT_OBSERVED
  (LoadLibraryW execution not confirmed; IFS2.dll never appears as module)

STAGE2_CREATEIFS_RESOLUTION = NOT_OBSERVED
  (Cannot occur if Stage 1 did not succeed; no GetProcAddress trace)

STAGE3_CREATEIFSLIBDLL = NOT_OBSERVED
  (Cannot occur if Stage 2 did not succeed; no IFS2 object creation evidence)

STAGE4_DESTORYIFS_RESOLUTION = NOT_OBSERVED
  (Cannot occur if Stage 3 did not succeed; no IFS2 object destruction evidence)
```

### IFS2 Runtime Load Status

```text
IFS2_DLL_RUNTIME_LOAD = NOT_OBSERVED
```

IFS2.dll never appears in any module snapshot, kernel image trace,
or thread record across all observations. This is consistent with
both Scenario A (LoadLibraryW fails) and Scenario B (never called).

## Failure Attribution

```text
FAILURE_ORIGIN = UNKNOWN

Candidates (not proven):
  1. IIPS internal (QoS check fails, control flow diverges before Stage 1)
  2. OS_LOADER (LoadLibraryW succeeds in finding file but DllMain fails)
  3. PATH/ENVIRONMENT (IFS2 path resolves incorrectly at runtime)
  4. DEPENDENCY (IFS2.dll DllMain attempts to load a resource that fails)

Scenario 1 is the most supported by EX-053 path causality evidence
(changing IFS2 location produces no outcome change).
Scenario 2-4 are possible but lack direct evidence.
```

## Success Path Assessment

```text
IIPS_SUCCESS_PATH = STATIC_CONFIRMED (iips.dll + 0x9A2B..0xA831)
IIPS_SUCCESS_TO_ENGINE = UNKNOWN (success path never observed at runtime)
FIRST_NEXT_TARGET = IFS2 vtable callback (inside IFS2.dll, NOT EXE Engine)
```

## Hard Stop Assessment

```text
STOP-1 (FIRST_FAILED_STAGE determined): NOT MET (UNKNOWN)
STOP-2 (all four stages succeed): NOT MET
STOP-3 (control flow diverged from four-stage model): PARTIALLY MET
  (evidence is compatible with pre-Stage-1 divergence but not conclusively proven)
```

## Final Conclusion Fields

```text
ICH014_STATUS = COMPLETE (within available evidence constraints)

FIRST_FAILED_STAGE = UNKNOWN

STAGE1_IFS2_LOAD = NOT_OBSERVED
STAGE2_CREATEIFS_RESOLUTION = NOT_OBSERVED
STAGE3_CREATEIFSLIBDLL = NOT_OBSERVED
STAGE4_DESTORYIFS_RESOLUTION = NOT_OBSERVED

IFS2_DLL_RUNTIME_LOAD = NOT_OBSERVED

IIPS_INIT_RESULT = FAILURE (DYNAMIC_CONFIRMED: iips.dll loads, IFS2 never loads, fatal error occurs)
IIPS_FAILURE_DIRECT_CAUSE = UNKNOWN
FAILURE_ORIGIN = UNKNOWN (most supported: pre-Stage-1 divergence / IIPS internal)

IIPS_SUCCESS_PATH = STATIC_CONFIRMED (iips.dll + 0x9A2B..0xA831)
FIRST_NEXT_TARGET = IFS2 vtable callback (inside IFS2.dll, NOT EXE Engine)

ENGINE_REGION_HIT_COUNT = 0
IIPS_SUCCESS_TO_ENGINE = UNKNOWN

PRIMARY_BLOCKING_BOUNDARY = IIPS initialization gate (WIN_IIPS_INIT_ERROR at 0x8189FEC)
  refined: either pre-initIfsLib divergence or Stage 1 LoadLibraryW failure
  exact: UNKNOWN without caller-filtered API trace

RUNTIME_ENTRY_IDENTIFIED = NO

NEXT_RESEARCH_DIRECTION = Caller-filtered LoadLibraryW capture with return address
  filter for iips.dll. Distinguish Scenario A (called, returned NULL) from
  Scenario B (never called). If never called, trace backwards to find the
  pre-initIfsLib divergence point (QoS helper at iips.dll+0x6D20 is the
  first candidate).
```

## Next Research Direction Detail

The minimum experiment to resolve FIRST_FAILED_STAGE:

```text
1. Start process under debugger (CDB or custom observer)
2. Set breakpoint on kernel32!LoadLibraryW
3. When hit, check caller return address:
   - If caller = iips.dll + 0x96EF → Stage 1 reached
     - Record return value (EAX after return)
     - If NULL → FIRST_FAILED_STAGE = 1
     - If non-NULL → continue to Stage 2 observation
   - If caller is NOT iips.dll → ignore (other LoadLibraryW calls)
4. If breakpoint on LoadLibraryW is NEVER hit by iips.dll
   before iips.dll unloads:
   - FIRST_FAILED_STAGE = UNKNOWN (pre-Stage-1 divergence)
   - IIPS_INIT_CONTROL_FLOW = DIVERGED
   - Next: set breakpoint on iips.dll+0x9860 (InitInGameApp entry)
     and iips.dll+0x99D2 (call to initIfsLib) to trace control flow
5. If InitInGameApp entry is hit but initIfsLib call is NOT reached:
   - QoS helper (iips.dll+0x6D20) is the divergence candidate
   - Record its return value at iips.dll+0x98D2
```

## Compliance

| Constraint | Status |
|-----------|--------|
| No binary modification | YES |
| No patch/hook/injection | YES |
| No IFS2 replacement | YES |
| No manual IFS2 load | YES |
| No DLL search path modification | YES |
| No fake return values | YES |
| No 0x8189FEC re-investigation | YES |
| No ordinal-1 re-investigation | YES |
| No BugTrace re-investigation | YES |
| No Unknown Native Layer re-investigation | YES |
| No IFS2 internal reverse engineering | YES |
| No Game Engine internal investigation | YES |
| No WeGame/TCLS expansion | YES |
