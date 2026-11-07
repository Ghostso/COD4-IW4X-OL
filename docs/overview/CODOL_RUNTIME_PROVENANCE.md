# CODOL_RUNTIME_PROVENANCE

## Scope

```text
EXPERIMENT = ONE_TARGETED_RUNTIME_TRACE
COMMAND_LINE = codoMP_client_shipRetail.exe -q
PROCESS_LAUNCHED = YES (one run)
BINARY_MODIFIED = NO
MODULES_LOADED = 75
PROJECT_MODULES_LOADED = 6
```

## Findings

### 1. New PE modules

The trace loaded 75 modules. Project-tree modules observed were:

```text
1 codoMP_client_shipRetail.exe 0x00400000
5 codoMP_client_shipRetailBase.dll 0x78FE0000
6 libcef.dll 0x0ED80000
7 libcef.dll 0x0ED80000
72 BugTrace.dll 0x680B0000
73 dbghelp.dll 0x68F70000
```

No previously unknown project runtime DLL appeared in the trace. The
project modules are consistent with the static module inventory.

### 2. Executable memory topology

| Snapshot | Total | IMAGE | MAPPED | PRIVATE |
|---|---:|---:|---:|---:|
| T0_CREATE | 4 | 4 | 0 | 0 |
| T1_ENTRY | 61 | 61 | 0 | 0 |
| T2_ORDINAL1 | 215 | 199 | 0 | 16 |
| T4_TIMEOUT | 89 | 80 | 0 | 9 |

Ordinal-1 did change the executable-memory topology: private executable
regions appeared by the ordinal-1 snapshot. The first observed private
executable region was:

```text
base = 0x14080000
end = 0x14090000
protect = 0x00000040
type = PRIVATE
allocation_base = 0x14080000
```

This observation alone is not a materialization proof.

### 3. First execution

```text
first_exec_va = 0x77781B53
first_exec_module = IMAGE_MAPPED_NO_MODULE
first_exec_type = IMAGE
first_private_exec = NOT_OBSERVED
```

The observed execution sequence reached the EXE entry breakpoint, then Base
ordinal-1, then a second ordinal-1 observation, then an exception in
kernel32. No execution observation entered a PRIVATE executable region.

### 4. .tvm0 relation

No byte-transform, copy, decrypt, decompress, relocation, or source-to-destination
relationship involving `.tvm0` was observed. Therefore:

```text
TVM0_MATERIALIZATION = NOT_OBSERVED
```

This does not prove `.tvm0` is unrelated to runtime materialization.

### 5. Base ordinal-1

```text
BEFORE_ORDINAL1_PRIVATE_EXEC = 0
AFTER_ORDINAL1_PRIVATE_EXEC = 16
NEW_MODULES_AFTER_ORDINAL1 = NOT_OBSERVED_IN_TRACE
FIRST_NEW_EXEC = NOT_OBSERVED
```

The trace observed new private executable memory after ordinal-1 entry, but
did not observe execution entering it. The bootstrap boundary therefore
produced executable memory transitions without a proven runtime transfer.

## Answers

1. **New PE modules?** No new project runtime PE module was observed.
2. **Did ordinal-1 change executable topology?** Yes: PRIVATE executable regions were absent at T0/T1 and present during/after ordinal-1.
3. **MEM_PRIVATE executable memory?** Yes, observed: 16 private executable regions at T2 and 9 at timeout.
4. **First new executable region?** 0x14080000 (0x00000040).
5. **First execution of new code?** No execution was observed in a PRIVATE region; the first observed executions remained IMAGE-backed.
6. **Ownership of first execution?** The observed first execution was in the mapped EXE image; the private-region first execution is NOT_OBSERVED.
7. **.tvm0 to runtime materialization?** NOT_OBSERVED.
8. **IW4/CODOL runtime fingerprint?** No new runtime fingerprint was established from the five execution observations.
9. **Current blocker:** `ORDINAL1_EXTERNAL_BOOTSTRAP_BOUNDARY`.

## Final Status

```text
NO_RUNTIME_MATERIALIZATION_OBSERVED
ORDINAL1_RUNTIME_MATERIALIZATION = NOT_OBSERVED
NEXT_TRACK = ORDINAL1_EXTERNAL_BOOTSTRAP_BOUNDARY
```

The next step is to characterize the ordinal-1 boundary and the newly created
private executable regions, not to resume a broad DLL scan.
