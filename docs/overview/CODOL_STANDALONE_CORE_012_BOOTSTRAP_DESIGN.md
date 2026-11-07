# CODOL_STANDALONE_CORE_012
# EXE-CORE-012 - Standalone Bootstrap Design

## 0. Final Status

```text
STANDALONE_BOOTSTRAP_ENTRY = CANDIDATE
STANDALONE_MINIMUM_STATE = PARTIAL
BOUNDARY_REPLACEMENT_MODEL = DEFINED
NEXT_EXPERIMENT = E-012-01
FINAL_MARKER = STANDALONE_BOOTSTRAP_DESIGN_CANDIDATE
```

## 1. Fixed Goal

> Make `codoMP_client_shipRetail.exe` establish a controllable standalone
> bootstrap - independent of WeGame, TCLS, Client.exe or any other Tencent
> launcher context - and eventually enter the game runtime that already
> exists inside the EXE. This round does NOT try to restore the original
> Tencent launch chain.

## 2. Frozen Evidence Baseline

```text
EXE SHA256        : 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
ImageBase         : 0x00400000
Entry RVA / VA    : 0x0E5DC690 / 0x0E9DC690
Entry bytes       : FF 15 65 C6 9D 0E  (call dword ptr [0x0E9DC665])
IAT slot          : RVA 0x0E5DC665 -> Base.dll ordinal 1 (0x80000001)
Return site       : RVA 0x0E5DC696 (zero padding, no fall-through)
Base ordinal-1    : Base RVA 0x1D6582C
```

CORE-011 frozen verdict:

```text
EXE_IMAGE_EXECUTION_AFTER_BOUNDARY = NOT_OBSERVED   (7 historical candidates, 0/28 hits)
ENVIRONMENT_DEPENDENT              = NO
STANDALONE_BOOTSTRAP_DESIGN_READY  = YES
HISTORICAL_BOOTSTRAP_CHAIN         = NOT_PROVEN_CURRENT_PATH
```

## 3. Phase 1 - EXE Runtime Entry Inventory

### 3.A Entry-adjacent (CONFIRMED)

```text
Entry 0x0E5DC690  -> IAT[0x0E5DC665] -> Base.dll ordinal 1 (BOUNDARY)
0x0E5DC696        -> zero padding; no native fall-through continuation
ordinal-1         -> 12/12 entries, 0/12 EXE return-site hits (CORE-009)
boundary input    -> EAX/EDX/ESI/EDI/EFLAGS stable 12/12; semantic role UNKNOWN
boundary state    -> 0x849413B=0, 0x849B501=0, argv_count=0, argv_array=0 (12/12)
```

### 3.B Confirmed EXE native structures

| Address | Role | Evidence grade |
|---|---|---|
| `0x0849413B` | startup gate byte (`-q`); 1 write + 3 reads validated; runtime =1 during `-q` | CONFIRMED |
| `0x0849B500` | `-qa` gate byte; 0 static operand sites; runtime-observed only | NOT_FOUND (static) |
| `0x0849B501` | `-src=tgp` gate byte; 1 validated read, write NOT_FOUND | CONFIRMED read / NOT_FOUND write |
| `0x08189FEC` | IIPS fatal status slot; 0 static producers; PACKED_OR_VM_GENERATED | NOT_FOUND |
| `0x00CA827C` | argv provider dispatch slot; call site 0x00561133; runtime-bound | CANDIDATE |
| `0x0196928C` | argv count global; write site 0x00561119 validated | CONFIRMED (shape) |
| `0x01969290` | argv array global; sites 0x00239C2D/0x0056111E validated | CONFIRMED (shape) |
| gate token cluster | `-qa` @ file 0x6C7F64, `-src=tgp` @ 0x6C7F68, `WIN_NO_TCLS` @ 0x6C7F80 (EXE-owned) | CONFIRMED |

## 4. Phase 2 - Runtime Entry Candidates

Full table: `exe_core012_entry_candidates.csv` (12 rows). Key facts:

- All 7 historical candidates (`0x77F580`, `0x77F8B3`, `0x4FD9B0`, `0x4FCEE0`,
  `0x808650`, `0x7E98F0`, `0x6212C0`) are CANDIDATE-grade: static L2 chain
  CONFIRMED (EX-045, NO_TVM0_DEPENDENCY) but NOT_OBSERVED post-ordinal-1 (CORE-011).
- Standalone-entry suitability: MAYBE for chain head/dispatchers
  (`0x77F580`, `0x4FD9B0`, `0x4FCEE0`, `0x808650`, `0x7E98F0`); NO for leaf/mid sites
  (`0x77F8B3`, `0x6212C0`, `0x00561133`, `0x37FA70`, `0x759F50`, engine anchors).
- No candidate is CONFIRMED as a standalone entry. None depends on .tvm0 inside
  the chain; upstream caller of `0x77F580` UNKNOWN (possible .tvm0 boundary).

## 5. Phase 3 - Standalone Minimum State

Full table: `exe_core012_minimum_state.csv` (16 rows). Summary:

```text
required_for_standalone = YES     : EXE image at ImageBase; command line (-q/-qa);
                                    argv count/array globals; argv provider slot;
                                    gate byte 0x0849413B=1; system CRT/DLLs
required_for_standalone = NO      : Tencent launcher components (EX-026/046 proven)
required_for_standalone = UNKNOWN : Base ordinal-1 itself; -qa/-src bytes; working
                                    dir/tree; project module minimum; dispatch table
                                    minimum; IIPS/IFS2/CNIFS; network/STUN config
```

At the ordinal-1 boundary entry, argv globals and gate bytes are all still 0
(12/12, CORE-009): a standalone bootstrap must establish argv + gate state
itself; the observed pipeline establishes them only post-boundary.

## 6. Phase 4 - Boundary Replacement Models

Full table: `exe_core012_boundary_models.csv` (2 rows, facts only, no winner).

### Model A - Minimal native bootstrap replacing ordinal-1

```text
Entry -> [replacement minimal native bootstrap: argv/provider/gate] -> 0x77F580 chain -> EXE runtime
```

- Pros: all confirmed structures are plain .text, NO_TVM0_DEPENDENCY (EX-045);
  reuses known sufficient context (local tree + -q/-qa, EX-046); single
  controllable boundary at Entry.
- Cons: chain upstream caller UNKNOWN; CORE-011 proved the chain does NOT
  execute post-ordinal-1; argv provider binder UNKNOWN; Base ordinal-1
  pre-transfer side effects UNKNOWN.

### Model B - Establish argv/global/dispatch minimum state, then direct entry

```text
Entry -> [establish argv globals + gate byte + dispatch minimum] -> 0x4FD9B0/0x4FCEE0 (or 0x77F580 pre-gated) -> EXE runtime
```

- Pros: avoids reproducing gate/argv logic; incrementally testable per
  candidate; independent of argv-provider binding if globals written directly.
- Cons: no candidate proven executable post-ordinal-1 (CORE-011 0/28); none
  proven as cold entry (L2 static only); 0x4FCEE0 internal state and indirect
  slots UNKNOWN; skipping 0x77F580 skips its other setup; Base ordinal-1
  absence effect UNKNOWN.

No winner declared (spec section 10: factual comparison only).

## 7. Gap List

Full table: `exe_core012_gap_list.csv` (15 rows). P0 gaps:

```text
GAP-P0-001 POST_BOUNDARY_CONTROL_TRANSFER  UNKNOWN  (does ANY EXE code run after ordinal-1)
GAP-P0-002 BASE_ORDINAL1_BOUNDARY_CONTRACT UNKNOWN  (input/return/side-effect/termination)
GAP-P0-003 EXE_ENTRY_NATIVE_CONTINUATION   NOT_FOUND (structural absence; blocking UNKNOWN)
GAP-P0-004 OBSERVATION_ENV_DIVERGENCE      UNRESOLVED (0.67s vs 7.7s; Env B pre-ordinal exit)
```

## 8. ONE Next Experiment

Full record: `exe_core012_next_experiment.csv` (1 row).

```text
E-012-01  Post-boundary EXE .text execution census
variable  EXE_IMAGE_CODE_EXECUTED_AFTER_ORDINAL1 in {OBSERVED, NOT_OBSERVED}
method    guard-page / execute-breakpoint coverage over the EXE image .text range,
          armed AFTER the ordinal-1 entry breakpoint fires (CORE-009 observer reused),
          Environment A only, -q and no-arg cases
success   first post-ordinal-1 EXE .text hit recorded with RVA+thread (OBSERVED),
          or 0 hits in both cases with ordinal-1 confirmed (NOT_OBSERVED)
stop      first attributed hit / exit / timeout; stop immediately on the known
          post-ordinal-1 0xC0000005 (RtlFreeHeap) exception
constraints: read-only observation; reversible; no EXE/DLL/Tencent modification
```

Priority question answer:

> Does a file-backed, EXE-proven native control-transfer target exist that can
> serve as the experimental standalone bootstrap entry? **UNKNOWN** - static
  candidates exist (MAYBE grade), but none is EXE-execution-proven in the
  CORE-009 reproduction environment (CORE-011: 0/28). E-012-01 is the minimal
  single-variable census that resolves this without manufacturing a candidate.

## 9. Stop-condition evaluation

```text
STOP-A (candidate with enough control-flow support) : NOT MET
        (candidates exist but control-flow support is L2 static only;
         execution linkage post-boundary is exactly what E-012-01 must test)
STOP-B (no implementable candidate)                 : NOT MET
        (MAYBE candidates exist; scanning is not expanded further)
STOP-C (all viable candidates depend on .tvm0/Base/TenProxy/TCLS) : NOT MET
        (chain itself is plain .text, NO_TVM0_DEPENDENCY, EX-045)
=> verdict: continue with ONE experiment E-012-01 (minimal fixed-point dynamic validation)
```

## 10. Compliance Checklist

| Spec requirement | Status |
|---|---|
| Only EXE analyzed; existing CORE-001..011 artifacts reused | PASS |
| No Base.dll/.tvm0/TenProxy/TCLS/WeGame internals | PASS |
| No Procmon/Sandboxie; no whole-EXE bootstrap rescan | PASS |
| 7 dead historical candidates not re-investigated (used as frozen inputs only) | PASS |
| No EXE/DLL modification; no .tvm0 patch; no Tencent hook | PASS |
| 0x849B500 old-report error NOT re-introduced (kept NOT_FOUND) | PASS |
| required_for_standalone column on every state row | PASS |
| Two boundary models, no winner | PASS |
| Exactly ONE next experiment (E-012-01), single-variable, read-only, reversible | PASS |
| UNKNOWN kept UNKNOWN; no fake CONFIRMED | PASS |
| generator/artifact/hash/row-count validation in generator | PASS |

## 11. Artifacts

```text
CODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md   (this file)
exe_core012_entry_candidates.csv                (12 rows)
exe_core012_minimum_state.csv                   (16 rows)
exe_core012_boundary_models.csv                 (2 rows)
exe_core012_gap_list.csv                        (15 rows)
exe_core012_next_experiment.csv                 (1 row)
core012_bootstrap_design.py                     (generator, re-run to reproduce)
```

## 12. Final Status (repeat, per spec)

```text
STANDALONE_BOOTSTRAP_ENTRY = CANDIDATE
STANDALONE_MINIMUM_STATE = PARTIAL
BOUNDARY_REPLACEMENT_MODEL = DEFINED
NEXT_EXPERIMENT = E-012-01
FINAL_MARKER = STANDALONE_BOOTSTRAP_DESIGN_CANDIDATE
```

> Prefer one honest UNKNOWN over one fabricated CONFIRMED.
