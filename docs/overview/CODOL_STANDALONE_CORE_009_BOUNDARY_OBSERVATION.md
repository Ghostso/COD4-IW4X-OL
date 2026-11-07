# CODOL_STANDALONE_CORE_009
# Minimal External-Boundary Observation

## 0. Scope, sample, and method

```text
SAMPLE      = D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe
EXE SHA256  = 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
BASE        = D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll
BASE SHA256 = EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20

EXE Entry        = codoMP_client_shipRetail.exe+0x0E5DC690
EXE return site  = codoMP_client_shipRetail.exe+0x0E5DC696
Base ordinal 1   = codoMP_client_shipRetailBase.dll+0x1D6582C
```

Observation method:

```text
Temporary process-memory breakpoints only at:
  1. EXE Entry
  2. Base.dll ordinal-1 entry
  3. EXE return site

NO EXE FILE MODIFICATION
NO BASE FILE MODIFICATION
NO PATCH
NO HOOK INTO BASE INTERNALS
NO BASE DISASSEMBLY / CFG / .tvm0 ANALYSIS
NO PROCMON
NO API TRACING
NO TENCENT/TCLS/WEGAME INTERNAL ANALYSIS
```

Observer/tooling:

```text
core009_boundary_observation.py
core009_merge_artifacts.py
_core009_observer\Program.cs
```

## 1. Run matrix

```text
Case A: no arguments             3/3 ordinal-1 hits, 0/3 return hits
Case B: -q                       3/3 ordinal-1 hits, 0/3 return hits
Case C: -qa                      3/3 ordinal-1 hits, 0/3 return hits
Case D: -q -src=tgp              3/3 ordinal-1 hits, 0/3 return hits
TOTAL                            12/12 ordinal-1 hits, 0/12 return hits
```

Observed post-entry process exits:

```text
0xC0000409
0xC0000005
```

No process produced an EXE-side continuation after ordinal-1.

## 2. Boundary input register observations

Across all 12 ordinal-1 boundary entries:

```text
EAX     = 0x7AD4582C
          = Base.dll runtime base 0x78FE0000 + RVA 0x1D6582C
          = ordinal-1 code address

EDX     = 0x78FE0110
          = Base.dll runtime base + RVA 0x110

ESI     = 0x78FE0000
          = Base.dll runtime base + RVA 0

EBX     = 0x680B0000
          = stable module/runtime load address in this environment

EDI     = 0x00000020
EFLAGS  = 0x00000202

ECX     = variable per run
ESP     = variable stack address per run
EBP     = variable stack frame address per run
```

Evidence classification:

```text
INPUT_REGISTER_CONTRACT = UNKNOWN
```

Reason: repeatable values are process/module context, not a proven calling-convention argument list. CORE-008 confirmed that the EXE Entry performs no explicit register setup before the indirect call.

## 3. Boundary stack observations

Observed stack pattern at ordinal-1 boundary:

```text
[ESP]    = 0x680C1F2F   (stable in this environment)
[ESP+4]  = 0x38689866   (stable in this environment)
[ESP+8]  = variable heap/runtime pointer
[ESP+C]  = 0x00000000
[ESP+10] = variable stack pointer
[ESP+14] = 0x00000000
[ESP+18] = 0x6F646F63   (ASCII bytes "codo"; stable, data-like)
```

Classification:

```text
STACK_ARGUMENTS = NOT_CONFIRMED
```

Reason: the EXE Entry has no pushes and no explicit stack setup. Stable stack data exists, but stack data existence alone is not proof of explicit arguments under the CORE-009 rule.

## 4. Return boundary

```text
EXE return site = codoMP_client_shipRetail.exe+0x0E5DC696
ORDINAL1_RETURNED = NOT_CONFIRMED
return-site hits  = 0/12
EAX_out           = NOT_OBSERVED
ECX_out           = NOT_OBSERVED
EDX_out           = NOT_OBSERVED
EFLAGS_out        = NOT_OBSERVED
ESP_out           = NOT_OBSERVED
```

Because ordinal-1 did not return to the EXE boundary:

```text
RETURN_VALUE_CONSUMER    = NOT_FOUND
ORDINAL1_RETURN_CONTRACT = NOT_CONFIRMED
```

This matches CORE-008 static evidence: the byte stream after the Entry call is zero padding and no caller-side instruction consumes EAX.

## 5. EXE-visible state before / after

At ordinal-1 entry, before any return:

```text
0x0849413B q_gate       = 0x00 in all 12 runs
0x0849B501 src_tgp_gate = 0x00 in all 12 runs
argv_count 0x0196928C   = 0x00000000 in all 12 runs
argv_array 0x01969290   = 0x00000000 in all 12 runs
0x00CA827C              = 0x00A1517E in all 12 runs
```

After-state at the EXE return boundary:

```text
NOT_AVAILABLE because the EXE return site is never reached.
SIDE_EFFECT_CONTRACT = NOT_CONFIRMED
```

## 6. Command-line effect at the ordinal-1 boundary

### Case B: `-q`

```text
ordinal-1 hits = 3/3
return hits    = 0/3
EAX/EDX/ESI/EDI/EFLAGS match Case A in module-relative classification
ECX and stack addresses vary independently
EXE gate/global state at boundary = unchanged from Case A
-q CHANGES BOUNDARY INPUT = NOT_CONFIRMED
```

### Case C: `-qa`

```text
ordinal-1 hits = 3/3
return hits    = 0/3
EAX/EDX/ESI/EDI/EFLAGS match Case A in module-relative classification
ECX and stack addresses vary independently
EXE gate/global state at boundary = unchanged from Case A
-qa CHANGES BOUNDARY INPUT = NOT_CONFIRMED
```

### Case D: `-q -src=tgp`

```text
ordinal-1 hits = 3/3
return hits    = 0/3
No repeatable boundary-input difference from A/B/C
-src=tgp CHANGES BOUNDARY INPUT = NOT_CONFIRMED
```

This does not deny later startup effects. It only states that no repeatable register/stack/global input change was confirmed at the EXE -> Base ordinal-1 boundary.

## 7. Module and thread side effects

Detailed captures are preserved in:

```text
exe_core009_module_delta.csv
exe_core009_thread_delta.csv
```

Boundary-level result:

```text
Base.dll is loaded before ordinal-1 entry.
No EXE-side return exists, so no post-call EXE-visible module delta can be used as a return contract.
Thread count changes after ordinal-1 entry are process-internal side effects, not an EXE caller contract.
No TenProxy/TCLS/WeGame internals were entered or analyzed.
```
### 7.1 Filesystem side effects

Filesystem observation used only low-interference metadata snapshots. No file content was read and Procmon was not used.

```text
FS_METADATA_DELTA_ROWS = 0
create/open/read/write/rename/delete = NOT_CONFIRMED by metadata snapshot
Artifact = exe_core009_fs_delta.csv
```



## 8. Final required answers

```text
1. ordinal-1 input register contract
   = UNKNOWN

2. ordinal-1 stack argument contract
   = NOT_CONFIRMED

3. ordinal-1 return contract
   = NOT_CONFIRMED
   RETURN_VALUE_CONSUMER = NOT_FOUND

4. ordinal-1 whether returns
   = NOT_CONFIRMED / NO OBSERVED RETURN
   0/12 return-site hits.

5. ordinal-1 changes EXE-visible state
   = NOT_CONFIRMED at caller boundary
   No after-state exists because the EXE return site is not reached.

6. -q changes boundary input
   = NOT_CONFIRMED

7. -qa changes boundary input
   = NOT_CONFIRMED

8. repeatable module/thread side effects
   = NOT_CONFIRMED as a caller contract

9. can define a minimal ordinal-1 contract now
   = YES_WITH_EXPLICIT_UNKNOWNS

10. further boundary experiment needed
   = NO_SINGLE_NARROW_VARIABLE_CONFIRMED
```

## 9. Minimal ordinal-1 boundary contract

```text
MINIMAL_ORDINAL1_CONTRACT:

Input:
  EXE executes an indirect call through IAT slot 0x0E5DC665.
  No explicit pushes.
  No explicit register setup by the Entry instruction sequence.
  Runtime registers may contain process/module context, but argument roles are UNKNOWN.
  Explicit stack arguments are NOT_CONFIRMED.

Execution:
  Base.dll ordinal-1 entry is reached reliably (12/12).

Return:
  No return to EXE+0x0E5DC696 observed (0/12).
  Return-value contract is NOT_CONFIRMED.
  Caller-side return consumer is NOT_FOUND.

EXE-visible state:
  At boundary entry, q/src_tgp gates and argv globals remain zero.
  0x00CA827C remains 0x00A1517E.
  No caller-side after-state exists because no return occurs.
```

## 10. Evidence levels

```text
CONFIRMED
  - EXE Entry RVA 0x0E5DC690 executes.
  - Base ordinal-1 RVA 0x1D6582C is reached.
  - 12/12 ordinal-1 entry observations.
  - 0/12 EXE return-site observations.
  - No caller-side return-value consumer.

CANDIDATE
  - EAX/EDX/ESI as module-context runtime values.
  - stable [ESP]/[ESP+4] data in this run family.

UNKNOWN
  - argument roles for any register.
  - ordinal-1 calling convention.
  - ordinal-1 output values.

BOUNDARY
  - Base.dll ordinal 1 remains the external boundary.

NOT_FOUND
  - return-value consumer.
  - command-line-induced boundary input delta.

NOT_CONFIRMED
  - explicit stack arguments.
  - return contract.
  - EXE-visible after-state side effects.

UNRESOLVED
  - why ordinal-1 terminates/exits without returning; resolving that would enter Base internals and is outside CORE-009 scope.
```

## 11. Artifact inventory

```text
CODOL_STANDALONE_CORE_009_BOUNDARY_OBSERVATION.md
exe_core009_runs.csv
exe_core009_registers.csv
exe_core009_stack.csv
exe_core009_state_delta.csv
exe_core009_module_delta.csv
exe_core009_thread_delta.csv
exe_core009_commandline_matrix.csv
exe_core009_contract_matrix.csv
exe_core009_fs_delta.csv
core009_boundary_observation.py
core009_merge_artifacts.py
core009_fs_metadata_probe.py
_core009_observer\Program.cs
```

## 12. Next-round decision

```text
INPUT_CONTRACT  = UNKNOWN
RETURN_CONTRACT = UNKNOWN / NOT_CONFIRMED
EXE-visible contract at boundary = sufficient with explicit unknowns
```

Therefore the correct next round is:

```text
EXE-CORE-010
Bootstrap Contract with Explicit Unknowns
```

## Final status

```text
ORDINAL1_INPUT_CONTRACT        = UNKNOWN
ORDINAL1_STACK_ARGUMENTS       = NOT_CONFIRMED
ORDINAL1_RETURNED              = NOT_CONFIRMED (0/12 observed)
ORDINAL1_RETURN_CONTRACT       = NOT_CONFIRMED
RETURN_VALUE_CONSUMER          = NOT_FOUND
SIDE_EFFECT_CONTRACT           = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_Q   = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_QA  = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_SRC = NOT_CONFIRMED
MODULE_THREAD_CALLER_CONTRACT  = NOT_CONFIRMED
NEXT_ROUND                     = EXE-CORE-010 Bootstrap Contract with Explicit Unknowns
FINAL_MARKER                   = ORDINAL1_BOUNDARY_NO_RETURN_UNRESOLVED
```
