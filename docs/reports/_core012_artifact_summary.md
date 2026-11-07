# EXE-CORE-012 Artifact Summary

Mined from existing artifacts only (no new disassembly/debugging/modification).
Primary sample: `COD OL\codoMP_client_shipRetail.exe`
SHA-256 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`,
ImageBase `0x00400000`. Boundary DLL: `codoMP_client_shipRetailBase.dll`
SHA-256 `EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20`.

Evidence grading rule used throughout: CONFIRMED = directly observed in an
artifact; CANDIDATE = inferred/plausible; UNKNOWN = not proven.

---

## 1. Entry-Adjacent Inventory

Confirmed EXE entry / IAT / ordinal-1 boundary facts (CORE-008/009/010/011):

| Fact | Value | Evidence grade | Source |
|---|---|---|---|
| EXE Entry RVA | `0x0E5DC690` (VA `0x0E9DC690`) | CONFIRMED | CORE-001/006/008/010, re-verified CORE-010 |
| Entry bytes | `FF 15 65 C6 9D 0E` = `call dword ptr [0x0E9DC665]` | CONFIRMED | CORE-006/008/010 (re-decode PASS) |
| IAT slot | VA `0x0E9DC665` (RVA `0x0E5DC665`), file value `0x80000001` = Base.dll ordinal 1 | CONFIRMED | CORE-008/010 |
| Import descriptors | exactly 1: `codoMP_client_shipRetailBase.dll` only | CONFIRMED | CORE-006/010 |
| Base relocations | directory size 0 (none) | CONFIRMED | CORE-010 |
| Entry fall-through | RVA `0x0E5DC696` onward = 2410 bytes of zero padding; no EAX consumer | CONFIRMED | CORE-006/008/010 |
| EXE return site RVA | `0x0E5DC696` | CONFIRMED (address) | CORE-009 |
| Base ordinal-1 target | Base RVA `0x1D6582C` | BOUNDARY / reachability CONFIRMED | CORE-008/009 |
| Ordinal-1 reachability | 12/12 entries (cases A/B/C/D) | CONFIRMED | CORE-009 |
| Ordinal-1 return | 0/12 return-site hits; return-value consumer NOT_FOUND | NOT_FOUND / contract NOT_CONFIRMED | CORE-009 |
| Boundary input registers (stable 12/12) | EAX=`0x7AD4582C` (Base+`0x1D6582C`), EDX=`0x78FE0110` (Base+`0x110`), ESI=`0x78FE0000` (Base+0), EDI=`0x20`, EFLAGS=`0x202`; ECX/ESP/EBP variable | CONFIRMED (values) / role UNKNOWN | CORE-009 |
| Boundary stack data | `[ESP]=0x680C1F2F`, `[ESP+4]=0x38689866`, `[ESP+18]=0x6F646F63` ("codo"); explicit stack arguments NOT_CONFIRMED | CANDIDATE / NOT_CONFIRMED | CORE-009 |
| Command-line effect at boundary | `-q`, `-qa`, `-src=tgp` produce NO confirmed delta in boundary registers/stack/globals | NOT_CONFIRMED | CORE-009 |
| EXE state at boundary entry (12/12) | `0x0849413B=0`, `0x0849B501=0`, `argv_count 0x0196928C=0`, `argv_array 0x01969290=0`, `0x00CA827C=0x00A1517E` | CONFIRMED | CORE-009 §5 |
| Post-boundary process activity | thread counts [8,10], 73 distinct modules, FS metadata delta 0 rows; exits `0xC0000005` / `0xC0000409` (observer-conditional) | CONFIRMED (process-level) | CORE-009/010 |
| Entry-connected native edges | 0 (EXE_SELF_BOOTSTRAP = NOT_FOUND) | CONFIRMED (static absence) | CORE-005/006/010 |
| CORE-011 post-boundary execution | `EXE_IMAGE_EXECUTION_AFTER_BOUNDARY = NOT_OBSERVED`; 0/28 candidate x run breakpoint hits; `ENVIRONMENT_DEPENDENT = NO` | CONFIRMED (observation) | CORE-011 |
| CORE-011 Env B divergence | direct-launch env exits `0x4000001E` before ordinal-1 (0/2 hits) | CONFIRMED | CORE-011 |
| CORE-011 final verdict | `STANDALONE_BOOTSTRAP_DESIGN_READY = YES`; historical chain is NOT the post-boundary path | CONFIRMED | CORE-011 decision CSV |

CORE-011 Env A post-ordinal-1 exception: `0xC0000005:FIRST` at
`ntdll!RtlFreeHeap+0x15A` (EIP `0x7673015A`), ~24 ms after ordinal-1.

---

## 2. Confirmed EXE Native Structures

| Address | Role | Evidence grade | Source |
|---|---|---|---|
| `0x0849413B` | startup gate byte (`-q` flag); 1 write + 3 reads validated (`0x0016FF08`, `0x0017FF46`, `0x00239C68`, `0x0028E1A4`); runtime `[0x849413B]=1` during `-q`; consumers at `EXE+0x2213B9/0x2214C5` (STUN mode), `0x237772`, `0x355871`, `0x402423`, `0x402CD3`; write site `0x37F5F7/0x37F612` | CONFIRMED | CORE-010 (E-010-025), EX-031/041/042 |
| `0x0849B500` | `-qa` gate byte; 0 static operand sites in file image (NOT_FOUND); runtime observation `-qa` sets it to 1; read at `0x6213C2`/`0x6214D2` inside STUN function `0x6212C0` | NOT_FOUND (static) / RUNTIME_OBSERVED | CORE-010 (E-010-026), EX-035/042/045 |
| `0x0849B501` | `-src=tgp` gate byte; 1 validated read (`0x002835BA=cmp byte ptr [abs], imm8`); write NOT_FOUND; runtime `-src=tgp` sets it to 1 | CONFIRMED (read) / write RUNTIME_OBSERVED | CORE-010 (E-010-027), EX-035 |
| `0x08189FEC` | IIPS fatal status code slot / fatal code text `8189fec`; 0 static operand sites (NOT_FOUND); PACKED_OR_RUNTIME_GENERATED; not equatable with IFS2 failure | NOT_FOUND / UNKNOWN semantics | CORE-010 (E-010-030), EX-039/040/046/050/057 |
| `0x00CA827C` | argv provider dispatch slot; single validated call site `0x00561133=call dword ptr [abs]`; target runtime-bound, VIRTUAL_ONLY; NOT proven to be GetCommandLineW/A or CommandLineToArgvW; holds `0x00A1517E` at boundary entry (12/12) | CANDIDATE | CORE-010 (E-010-024), EX-032 |
| `0x0196928C` | argv count global; validated write `0x00561119=mov dword ptr [abs], eax`; = 0 at boundary entry | CONFIRMED (shape) | CORE-009/010 (E-010-023) |
| `0x01969290` | argv array global; validated `0x00239C2D` (read) + `0x0056111E` (write); = 0 at boundary entry | CONFIRMED (shape) | CORE-009/010 |
| Gate token cluster | `-qa` @ file `0x6C7F64`, `-src=tgp` @ `0x6C7F68`, `WIN_NO_TCLS` @ `0x6C7F80`; confirms gate is EXE-owned, not Tencent layer | CONFIRMED | CORE-010 |
| Fatal dispatcher | `EXE+0x37FA70` executed for WIN_NO_TCLS (EX-031); candidate common fatal dispatcher for IIPS errors (L2) | CONFIRMED for WIN_NO_TCLS / CANDIDATE for IIPS | EX-031/041 |
| Dispatcher state globals (in `0x4FCEE0` path) | `0xE59D20`, `0x82E13F8`, `0x82C4A78`, `0x82C4A68/6C`, `0x849B5CC`, `0x81AA110/114/118`, `0x849BA38`, `0x76595A4/A8/AC`, `0x766929C` | CANDIDATE (static L2) | EX-045 |
| Indirect IAT/thunk slots in bootstrap path | `0xCA812C`, `0xCA8190`, `0xCA819C`, `0xCA8170`, `0xCA8534`, `0xCA8114`, `0xCA818C`, `0xCA84C8` | CANDIDATE (API names unbound) | EX-045 |

---

## 3. Runtime Entry Candidates

All RVAs are EXE-image-relative (VA = `0x00400000` + RVA).

| # | RVA | Role | Evidence source | Grade | Call relation | Post-ordinal-1 execution | .tvm0 dep | Tencent dep | Standalone entry suitability |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `0x0E5DC690` | EXE Entry (single FF15 call to Base ord-1) | CORE-008/010 | CONFIRMED | Entry -> IAT slot -> Base ordinal 1 | YES (is the entry; boundary itself is external) | NO (plain FF15) | NO (only import is Base.dll) | NO (it IS the boundary call; falls through to zero padding) |
| 2 | `0x77F580` | gate/bootstrap function head (`0x77F580..0x77FA6F`); contains WIN_NO_TCLS gate + `0x77F8B3` call | EX-045/046; CORE-010 E-010-031/032 | CANDIDATE (static L2 chain); execution reached in independent-copy runs per EX-046 but NOT post-ordinal-1 in CORE-011 | head of historical chain; caller NOT recovered | NO (0 hits in CORE-011, both pre and post boundary) | NO in chain; possible .tvm0 above its caller | NO (chain itself plain .text) | MAYBE (chain head; upstream caller unknown; entry conditions unknown) |
| 3 | `0x77F8B3` | call site inside `0x77F580` -> `0x4FD9B0` | EX-045 | CANDIDATE | direct E8 `0x77F8B3 -> 0x4FD9B0` | NO (CORE-011 0 hits) | NO | NO | NO (mid-function call site, not an entry) |
| 4 | `0x4FD9B0` | bootstrap dispatcher candidate (`0x4FD9B0..0x4FDADB`) | EX-045/046 | CANDIDATE | called from `0x77F8B3`; calls `0x4FCEE0` at `0x4FDA03` | NO (CORE-011) | NO | NO | MAYBE (multi-call dispatcher; expects gate context) |
| 5 | `0x4FCEE0` | multi-subsystem init dispatcher (`0x4FCEE0..0x4FD8DF`) | EX-045/046 | CANDIDATE | called from `0x4FDA03`; calls `0x808650` at `0x4FD287` | NO (CORE-011) | NO | NO | MAYBE (large init sequence; internal state assumptions unknown) |
| 6 | `0x808650` | subsystem init wrapper (`0x808650..0x808932`) | EX-045/046 | CANDIDATE | called from `0x4FD287`; calls `0x7E98F0` at `0x808658` | NO (CORE-011) | NO | NO | MAYBE |
| 7 | `0x7E98F0` | network subsystem init (`0x7E98F0..0x7E9A35`) | EX-044/045/046 | CANDIDATE | called from `0x808658`; calls `0x6212C0` at `0x7E9913` | NO (CORE-011) | NO | NO | MAYBE (sub-stage, not a head) |
| 8 | `0x6212C0` | STUN/network mode init (`0x6212C0..0x621AF5`); reads `0x849413B`/`0x849B500`; selects stun1-tub.codol.qq.com vs stun.us.demonware.net | EX-042/043/044/045/046; CORE-010 E-010-033 | CANDIDATE (L2 static; strings confirmed EXE-side for demonware endpoint only) | called at `0x7E9913` and recursively at `0x621AC6` | NO (CORE-011) | NO | NO | NO (leaf-stage, depends on prior init) |
| 9 | `EXE+0x00561133` call via `0x00CA827C` | argv provider invocation | CORE-008/010 | CANDIDATE | single indirect call site; target runtime-bound | NOT_OBSERVED (argv globals still 0 at boundary) | UNKNOWN | UNKNOWN | NO (indirect slot, not a code entry) |
| 10 | `EXE+0x37FA70` | fatal error display dispatcher (WIN_NO_TCLS path) | EX-031/041 | CONFIRMED executed for WIN_NO_TCLS | called from gate region; -> #32770 dialog | NOT_OBSERVED post-ordinal-1 in CORE-011 (not in the 7-candidate set; executed in EX-031 independent runs) | UNKNOWN | NO | NO (error path, not bootstrap continuation) |
| 11 | `0x759F50` | structure builder fed by `0x849413B` consumer at `EXE+0x402423` | EX-041/042 | CANDIDATE | called with gate booleans | NOT_OBSERVED | UNKNOWN | UNKNOWN | NO |
| 12 | `0x1321A9` / `0x239B7D` / `0x7036DC` family | Engine/FS/Renderer string-ref anchors | EX-020 | UNKNOWN | no clean prologue/caller; data anchors only | NOT_OBSERVED | UNKNOWN | UNKNOWN | NO (not proven executable entries) |

Aggregate verdict per CORE-011: zero of the 7 historical candidates executed
after the ordinal-1 boundary in the CORE-009 reproduction environment; the
historical native bootstrap chain is NOT the current post-boundary execution
path. No candidate is a CONFIRMED standalone entry.

---

## 4. Standalone Minimum State

Minimum EXE-internal state needed to bypass the external ordinal-1 boundary and
reach existing EXE native runtime (per CORE-010 layers A/B and EX-046 minimal
context):

| Item | Address / form | required_for_standalone | Evidence grade | Source |
|---|---|---|---|---|
| EXE image loaded at ImageBase `0x00400000`, PE32/I386 | sample identity | YES | CONFIRMED | CORE-001/010 layer A |
| Command line present, containing `-q` or `-qa` (WIN_NO_TCLS bypass) | argv | YES (for observed gate path) | CONFIRMED (gate semantics) / CANDIDATE as requirement for observed path | EX-031/035/046; CORE-010 layer A |
| argv count/array globals populated | `0x0196928C` / `0x01969290` | YES (gate consumes them) | CONFIRMED shape; population mechanism CANDIDATE | CORE-009/010 |
| argv provider slot bound and invoked | `0x00CA827C` @ call site `0x00561133` | YES (for argv path) | CANDIDATE | CORE-008/010; EX-032 |
| Startup gate byte set to 1 (`-q` path) | `0x0849413B` | YES (to pass WIN_NO_TCLS) | CONFIRMED | CORE-010; EX-031/041/042 |
| `-qa` byte (only if `-qa` route) | `0x0849B500` | UNKNOWN (only RUNTIME_OBSERVED; no static writer found) | NOT_FOUND static / RUNTIME_OBSERVED | CORE-010; EX-035 |
| Working directory = game root; full local game tree | process context | CANDIDATE (no ablation performed) | CANDIDATE | EX-046 MINIMAL_CONTEXT_PARTIAL |
| System DLLs (kernel32/ntdll etc.) | C_RUNTIME | YES | CONFIRMED | CORE-010 layer C |
| EXE-tree project module set (Base/libcef loaded; others later) | C_RUNTIME | UNKNOWN minimum | module set CONFIRMED; minimum UNKNOWN | CORE-009/010; EX-026/040 |
| Base.dll ordinal-1 boundary | Base RVA `0x1D6582C` | UNKNOWN whether required at all if replaced | BOUNDARY; contract UNKNOWN | CORE-009/010 |
| Internal dispatch table minimum | B_EXE | UNKNOWN | CANDIDATE | CORE-010 GAP-P1-004 |
| IIPS / IFS2 / CNIFS | BOOT_07 | UNKNOWN (blocks progression past IIPS fatal, not bootstrap entry itself) | BOUNDARY | EX-047/048/057/060 |
| Tencent launcher components (WeGame/TCLS/Client.exe/tcls_core) | C_RUNTIME | NO | NOT_REQUIRED_CONFIRMED | EX-026/046; CORE-010 audit |
| Network / STUN config | BOOT_06 | UNKNOWN | CANDIDATE | EX-043/044/045 |

At the ordinal-1 boundary entry, argv globals and gate bytes are all still 0
(12/12, CORE-009), so a standalone bootstrap must establish argv + gate state
itself; the observed pipeline establishes them only post-boundary.

---

## 5. Boundary Replacement Models

### Model A — Minimal native bootstrap replacing ordinal-1
Replace the Entry's external transfer (IAT slot `0x0E9DC665` -> Base ordinal 1)
with a minimal EXE-side native bootstrap that performs the argv/provider/gate
sequence and then enters the historical chain head `0x77F580`.

Pros:
- All confirmed EXE-owned structures (argv globals `0x0196928C/90`, gate
  `0x0849413B`, token cluster, chain `0x77F580 -> ... -> 0x6212C0`) are plain
  `.text` with NO_TVM0_DEPENDENCY (EX-045).
- Reuses the known sufficient context (local tree + `-q`/`-qa`, EX-046).
- Keeps a single, well-defined controllable boundary at the Entry.

Cons:
- The chain's upstream caller is UNKNOWN (EX-045: caller above `0x77F580` not
  recovered, potential .tvm0 boundary); CORE-011 proved the chain does NOT
  execute after ordinal-1 in the observed environment, so its real entry
  conditions/calling convention are unproven.
- The argv provider slot `0x00CA827C` is runtime-bound and VIRTUAL_ONLY; who
  binds it and when is UNKNOWN (GAP-P1-003).
- Whatever Base ordinal-1 did before transferring (threading, allocator, module
  setup) is UNKNOWN; a replacement may skip required Base-side initialization.

### Model B — Establish argv/global/dispatch state, then jump directly to an EXE native runtime candidate
A launcher/stub populates the minimum state (Section 4: argv globals, gate byte
`0x0849413B=1`, dispatch prerequisites) and transfers control directly to a
post-gate candidate such as `0x4FD9B0` / `0x4FCEE0` (or chain head `0x77F580`
with the gate pre-satisfied), bypassing both ordinal-1 and the gate.

Pros:
- Avoids reproducing gate/argv logic; directly targets dispatcher-level entries
  with confirmed static structure (EX-045/046).
- Testable incrementally per candidate; each candidate has known downstream
  call graph.
- Independent of the unresolved argv-provider binding question if argv globals
  are written directly.

Cons:
- No candidate is proven executable post-ordinal-1 (CORE-011: 0/28 hits);
  none is proven as a cold entry (all evidence is L2 static).
- Internal state assumptions of `0x4FCEE0` (dispatcher state globals, indirect
  IAT slots `0xCA81xx/0xCA84xx` with unbound API names) are UNKNOWN.
- Skipping the gate function skips whatever else `0x77F580..0x77FA6F` sets up
  beyond the gate byte.
- Still UNKNOWN whether Base.dll ordinal-1 side effects (or its absence) matter
  to downstream runtime.

No winner declared.

---

## 6. Gaps / Unknowns

| Gap | Status | Source |
|---|---|---|
| GAP-P0-001 POST_BOUNDARY_CONTROL_TRANSFER: does EXE-image code execute at/after ordinal-1, and which module enters it? | UNKNOWN (CORE-011: NOT_OBSERVED for the 7 historical candidates; does not prove no other EXE code runs) | CORE-010/011 |
| GAP-P0-002 BASE_ORDINAL1_BOUNDARY_CONTRACT: input/return/side-effect/termination semantics of ordinal-1 | UNKNOWN | CORE-009/010 |
| GAP-P0-003 EXE_ENTRY_NATIVE_CONTINUATION: Entry-connected continuation | NOT_FOUND (structural absence CONFIRMED; blocking UNKNOWN) | CORE-005/006/010 |
| GAP-P0-004 OBSERVATION_ENVIRONMENT_DIVERGENCE: 0.67 s (debugger) vs 7.7 s (normal) timeline divergence; Env B exits before ordinal-1 | UNRESOLVED | CORE-010/011; EX-028 |
| GAP-P1-001 NATIVE_BOOTSTRAP_ENTRY_CONNECTION: caller of `0x77F580` chain head | UNKNOWN/CANDIDATE | CORE-010; EX-045 |
| GAP-P1-002 IIPS_INITIALIZATION: first failing prerequisite; `8189FEC` source (PACKED_OR_VM_GENERATED) | UNKNOWN/CANDIDATE | CORE-010; EX-039/040/057 |
| GAP-P1-003 ARGV_PROVIDER_SLOT: who binds `0x00CA827C`, when it runs | CANDIDATE | CORE-010; EX-032 |
| GAP-P1-004 RUNTIME_DISPATCH_MINIMUM: minimum dispatch-table slot set | CANDIDATE/UNKNOWN | CORE-010 |
| GAP-P2-001 GAME_INIT / GAP-P2-002 RENDERER_MAIN_LOOP | UNKNOWN | CORE-010 |
| Who loads TenProxy/GameRpcs/TenRpcs/tcj/GDPLoader/GameDataPlatformServer (no caller edges captured) | UNKNOWN | EX-026/027/040 |
| iips.dll loader/init/error caller (packed EXE/Base side) | UNCONFIRMED | EX-039/040 |
| `0x0849B500` static writer | NOT_FOUND | CORE-010 |
| Base-internal nodes `Base+0x2C96E/0x5F7000/0x5EB4E0/0x13A68/0x1D68B` responsibilities | UNKNOWN (thread starts observed only) | EX-026/027 |
| Environment variables relevance | UNKNOWN | CORE-010 layer A |
| EX-065 TCLS upstream protocol relevance to a normal `-q` launch (whether TCLS path is exercised outside repair/pre-download) | UNKNOWN (U11) | EX-065 |

---

## 7. P0 Experiment Recommendation

Exactly one next experiment:

| Field | Value |
|---|---|
| experiment_id | E-012-01 |
| purpose | Test whether a specific EXE-native control-transfer target can serve as a standalone bootstrap entry by determining whether ANY EXE-image `.text` execution occurs after the ordinal-1 boundary (post-boundary EXE execution census), closing GAP-P0-001 fully |
| single variable | `EXE_IMAGE_CODE_EXECUTED_AFTER_ORDINAL1` in {OBSERVED, NOT_OBSERVED} |
| target candidate | EXE `.text` section as a whole (image-base-relative execute coverage), with per-address attribution to the known candidates `0x77F580`, `0x4FD9B0`, `0x4FCEE0`, `0x808650`, `0x7E98F0`, `0x6212C0`, `0x00561133` (argv provider call site), `0x37FA70` (fatal dispatcher); ordinal-1 entry breakpoint retained as the phase marker |
| method | Reuse the CORE-009/CORE-011 observer (no file modification, no hooks, no Base internals): guard-page / execute-breakpoint coverage over the EXE image `.text` range armed AFTER the ordinal-1 entry breakpoint fires; record module, RVA, thread, timestamp for each first-hit; Environment A (CORE-009 reproduction) only, `-q` and no-arg cases |
| success criterion | A first post-ordinal-1 EXE `.text` hit with RVA + owning thread recorded (OBSERVED), naming the actual post-boundary EXE entry; or 0 hits across both cases with ordinal-1 hit confirmed (NOT_OBSERVED), which proves no EXE-image continuation exists in this environment and fixes the boundary replacement design point |
| stop condition | Stop when: (a) the first attributed EXE `.text` hit is recorded, or (b) process exit/timeout in both cases with ordinal-1 confirmed; in all cases stop before any Base-internal instrumentation, and stop immediately on the known post-ordinal-1 `0xC0000005` (RtlFreeHeap) exception |
| constraints | read-only observation; reversible (process-memory breakpoints only); no EXE/DLL modification, no patch/hook/stub; no Tencent/TCLS/WeGame interaction |

Rationale: CORE-011 answered the question only for the 7 historical candidates
(all NOT_HIT). The single remaining P0 blocker for a standalone bootstrap
design is whether ANY EXE-image code executes after ordinal-1; E-012-01 is the
minimal single-variable test of that, directly selecting between Model A and
Model B entry targets.

---

## 8. Deliverable Mapping

| Deliverable | Populated from |
|---|---|
| `exe_core012_entry_candidates.csv` | Section 3 table (12 rows): RVA, role, evidence source, grade, call relation, post-ordinal-1 status, .tvm0/Tencent dependency, standalone suitability |
| `exe_core012_minimum_state.csv` | Section 4 table: item, address, required_for_standalone, evidence grade, source artifact |
| `exe_core012_boundary_models.csv` | Section 5: Model A and Model B rows with pros/cons (no winner) |
| `exe_core012_gap_list.csv` | Section 6: all gaps with status and source (extends `exe_core010_gap_list.csv` with CORE-011 outcomes) |
| `exe_core012_next_experiment.csv` | Section 7: E-012-01 (ONE_ONLY) with purpose, target, success criterion, stop condition |
| `core012_bootstrap_design.py` | Generator encoding Sections 1-7 as data tables; constants available from `core010_bootstrap_contract.py` (IMAGE_BASE, ENTRY_RVA, IAT_SLOT_RVA, BASE_ORDINAL1_RVA, TRACKED_SITES) and `core011_post_boundary_execution.py` (candidate RVA list, decision values) |
| `CODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md` | Narrative assembled from Sections 1-7; key source facts: CORE-009 boundary contract, CORE-010 contract matrix/layers/gaps, CORE-011 NOT_OBSERVED verdict + STANDALONE_BOOTSTRAP_DESIGN_READY=YES, EX-045/046 chain and dependency classification, EX-057 IIPS boundary |

---

Completeness note: all 15 requested sources were read (CORE-009/010/011
reports + `core010_bootstrap_contract.py` + `core011_post_boundary_execution.py`
structure, core010/core011 CSVs, EX-020/026/027/039/040/041/042/045/046/057/065).
Where a section lacked evidence it is marked UNKNOWN / NOT_FOUND rather than
invented.