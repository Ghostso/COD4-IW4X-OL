# CODOL_STANDALONE_CORE_010
# Standalone Bootstrap Contract with Explicit Unknowns

## 0. Task, scope and prohibitions

```text
ROUND        = EXE-CORE-010 (Bootstrap Contract with Explicit Unknowns)
PRIMARY      = COD OL/codoMP_client_shipRetail.exe
PRIMARY SHA  = 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
SAMPLE MATCH = True
BOUNDARY     = codoMP_client_shipRetailBase.dll (EF75220DE1D6973F...)
BASELINE     = CORE-001..CORE-009 plus targeted EX rounds; no new reverse targets
```

Prohibitions honoured this round:

```text
NO EXE modification / NO patch / NO hook / NO stub DLL      -> honoured
NO Base CFG / NO Base .text reverse / NO Base .tvm0         -> honoured
NO Base allocator / thread / IIPS / TenProxy internals      -> honoured
NO Tencent launcher reverse (TCLS / WeGame / Client.exe)    -> honoured
NO Procmon / NO Sandboxie / NO large-scale tracing          -> honoured
NO credential / session / token work                        -> honoured
STATIC FILE ACCESS                                          -> READ ONLY (SHA-256, PE header,
                                                               instruction bytes, ASCII tokens)
```

Method: the sample is re-verified statically at generation time, the CORE-009
observation artifacts are re-aggregated from their CSVs, and every contract row
carries an explicit status from the CORE-010 vocabulary
(`CONFIRMED / CANDIDATE / UNKNOWN / BOUNDARY / NOT_FOUND / UNRESOLVED`).
CORE-009 literal status words outside that vocabulary (for example
`NOT_CONFIRMED`) are preserved verbatim in the `core009_literal` column.

Conventions used by every artifact:

```text
blocking_level : CONFIRMED / CANDIDATE / UNKNOWN / NOT_BLOCKING
                 (how confident we are that the item blocks boot)
priority       : P0 / P1 / P2 / P3
                 P0 directly blocks the EXE native bootstrap
                 P1 blocks native bootstrap -> game init
                 P2 blocks game init -> main loop
                 P3 outside the boot core
                 => "ORDINAL1 = P0 UNKNOWN" is therefore encoded as
                    priority=P0 with blocking_level=UNKNOWN, never as P0 + CONFIRMED
required       : CONFIRMED / CANDIDATE / UNKNOWN / NOT_REQUIRED        (state machine)
required_status: REQUIRED_CONFIRMED / REQUIRED_CANDIDATE / UNKNOWN /
                 NOT_REQUIRED_CONFIRMED                                (dependency audit)
```
---

## 1. CORE-009 ingest (frozen, unchanged)

CORE-009 is adopted verbatim, including its final status block:

```text
ORDINAL1_INPUT_CONTRACT        = UNKNOWN
ORDINAL1_STACK_ARGUMENTS       = NOT_CONFIRMED
ORDINAL1_RETURNED              = NOT_CONFIRMED  (0/12 observed return)
ORDINAL1_RETURN_CONTRACT       = NOT_CONFIRMED
RETURN_VALUE_CONSUMER          = NOT_FOUND
SIDE_EFFECT_CONTRACT           = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_Q   = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_QA  = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_SRC = NOT_CONFIRMED
MODULE_THREAD_CALLER_CONTRACT  = NOT_CONFIRMED
FS_METADATA_DELTA              = 0
FINAL_MARKER                   = ORDINAL1_BOUNDARY_NO_RETURN_UNRESOLVED
```

`0/12` describes observation only, never Base behaviour:

```text
ORDINAL1_NONRETURN = UNKNOWN            (not NONRETURN_CONFIRMED)
```

Re-aggregated observation data (derived from the CORE-009 CSVs, not hand-copied):

```text
runs                        = 12 (cases A/B/C/D)
ordinal-1 entries           = 12/12
EXE return-site hits        = 0/12
per case                    = A: entries 3/3, returns 0; B: entries 3/3, returns 0; C: entries 3/3, returns 0; D: entries 3/3, returns 0
process states              = EXITED
exit codes                  = 0xC0000005, 0xC0000409
thread counts per run       = [8, 10]
last observer-relative time = 0.67s
modules in window           = 73 distinct ({'CREATE_PROCESS': 12, 'LOAD_DLL': 906})
project modules present     = NONE
project modules absent      = ['iips', 'ifs', 'tcls', 'tenproxy', 'gbspy', 'tenrpcs', 'tersafe', 'gdploader', 'tcj']
filesystem metadata delta   = 0 rows
```

Boundary input observations (values frozen, semantics deliberately unassigned):

```text
EAX    = 0x7AD4582C  (= Base runtime base + 0x1D6582C, the ordinal-1 code address)
EDX    = 0x78FE0110  (= Base runtime base + 0x110)
ESI    = 0x78FE0000  (= Base runtime base + 0)
EDI    = 0x00000020
EFLAGS = 0x00000202
ECX / ESP / EBP = variable per run (12 / 11 / 1 distinct values)

REGISTER_VALUE_STABILITY = CONFIRMED
REGISTER_SEMANTIC_ROLE   = UNKNOWN
```

Stable stack data exists but is not accepted as an argument list:

```text
[ESP] ['0x680C1F2F']   [ESP+4] ['0x38689866']   [ESP+18] ['0x6F646F63']
STACK_ARGUMENTS = NOT_CONFIRMED (CORE-009 literal)
```

`ESI` referencing `Base + 0` is **not** interpreted as a NULL context, and no
register is labelled `this` / `context` / `argument` / `flags` without new direct
evidence.

### 1.1 Observation-window coverage (new explicit limitation)

```text
CORE-009 window : process exits inside the observation window; last observer-relative
                  thread timestamp 0.67s, module set 73,
                  project modules iips/IFS2/TCLS/TenProxy absent
EX-046 baseline : independent-copy runs reach the IIPS fatal at about T+7.7s
=> OBSERVATION_WINDOW_COVERAGE = UNRESOLVED (root cause UNKNOWN)
```

The CORE-009 window never reaches the IIPS phase, and its exit codes
(0xC0000005, 0xC0000409) are observer-conditional. They are recorded as
observations of the observation environment, not as Base behaviour and not as a
confirmed termination contract.

---

## 2. Evidence Ledger

Artifact: `exe_core010_evidence_ledger.csv` (39 rows)
Status distribution: CONFIRMED=15, CANDIDATE=4, UNKNOWN=12, BOUNDARY=2, NOT_FOUND=5, UNRESOLVED=1

```text
E-010-001  SAMPLE_IDENTITY_EXE                CONFIRMED  COD OL/codoMP_client_shipRetail.exe
E-010-002  ENTRY_INSTRUCTION                  CONFIRMED  RVA 0x0E5DC690 (VA 0x0E9DC690)
E-010-003  ENTRY_FALLTHROUGH                  CONFIRMED  RVA 0xE5DC696
E-010-004  IAT_SLOT_ORDINAL1                  CONFIRMED  slot VA 0xE9DC665 (RVA 0xE5DC665)
E-010-005  EXE_IMPORT_SET                     CONFIRMED  PE data directory[1]
E-010-006  BASE_ORDINAL1_TARGET               BOUNDARY   Base.dll ordinal 1 (RVA 0x1D6582C)
E-010-007  ORDINAL1_REACHABILITY              CONFIRMED  boundary RVA 0x1D6582C (Base-relative)
E-010-008  ORDINAL1_REGISTER_VALUE_STABILITY  CONFIRMED  boundary registers
E-010-009  ORDINAL1_REGISTER_SEMANTIC_ROLE    UNKNOWN    boundary registers
E-010-010  ORDINAL1_STACK_ARGUMENTS           UNKNOWN    boundary stack
E-010-011  ORDINAL1_RETURNED                  NOT_FOUND  EXE RVA 0xE5DC696
E-010-012  ORDINAL1_RETURN_CONTRACT           UNKNOWN    boundary return
E-010-013  RETURN_VALUE_CONSUMER              NOT_FOUND  EXE caller side
E-010-014  ORDINAL1_NON_RETURN                UNKNOWN    boundary
E-010-015  ORDINAL1_SIDE_EFFECT               UNKNOWN    boundary
E-010-016  ORDINAL1_TERMINATION_MODE          UNKNOWN    process
E-010-017  POST_BOUNDARY_THREAD_ACTIVITY      CONFIRMED  process
E-010-018  POST_BOUNDARY_MODULE_SET           CONFIRMED  process
E-010-019  FS_METADATA_DELTA                  CONFIRMED  process filesystem
E-010-020  COMMANDLINE_BOUNDARY_DELTA_Q       UNKNOWN    boundary input
E-010-021  COMMANDLINE_BOUNDARY_DELTA_QA      UNKNOWN    boundary input
E-010-022  COMMANDLINE_BOUNDARY_DELTA_SRC     UNKNOWN    boundary input
E-010-023  ARGV_DATA_SHAPE                    CONFIRMED  0x0196928C (count) / 0x01969290 (array)
E-010-024  ARGV_PROVIDER_SLOT                 CANDIDATE  0x00CA827C (call site 0x00561133)
E-010-025  STARTUP_GATE_Q                     CONFIRMED  0x0849413B
E-010-026  STARTUP_GATE_QA                    NOT_FOUND  0x0849B500
E-010-027  STARTUP_GATE_SRC_TGP               CONFIRMED  0x0849B501
E-010-028  STARTUP_CONTEXT_GATE_TOKENS        CONFIRMED  EXE file-image plain-text token cluster
E-010-029  WIN_NO_TCLS_SEMANTICS              CONFIRMED  argv gate (WIN_NO_TCLS)
E-010-030  IIPS_STATUS_CODE_SLOT              NOT_FOUND  0x08189FEC
E-010-031  HISTORICAL_BOOTSTRAP_CHAIN         CANDIDATE  0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> 0x6212C0
E-010-032  POST_BOUNDARY_EXE_ENTRY_INFERENCE  CANDIDATE  EXE image (0x77F580 head)
E-010-033  NETWORK_STUN_CONFIG                CANDIDATE  0x6212C0 / 0x7E98F0 / 0x808650
E-010-034  IIPS_BOUNDARY                      BOUNDARY   iips.dll / IFS2.dll / CNIFS
E-010-035  IIPS_INIT_RESULT                   UNKNOWN    post-gate node
E-010-036  EXE_SELF_BOOTSTRAP                 NOT_FOUND  EXE Entry-connected graph
E-010-037  GAME_INIT                          UNKNOWN    none
E-010-038  RENDERER_INPUT_AUDIO_MAIN_LOOP     UNKNOWN    none
E-010-039  OBSERVATION_WINDOW_COVERAGE        UNRESOLVED process (cross-round)
```

Only the six CORE-010 status values are used in the `status` column. Where
CORE-009 used a literal outside that set, the literal is preserved in the row's
`notes` and in the contract matrix `core009_literal` column.

---

## 3. Bootstrap State Machine

Artifact: `exe_core010_boot_state_machine.csv` (13 nodes, BOOT_00..BOOT_12)

```text
BOOT_00_PROCESS_START        CONFIRMED  required=CONFIRMED    blocking=NOT_BLOCKING
BOOT_01_EXE_ENTRY            CONFIRMED  required=CONFIRMED    blocking=NOT_BLOCKING
BOOT_02_ORDINAL1_BOUNDARY    BOUNDARY   required=UNKNOWN      blocking=UNKNOWN
BOOT_03_ARGV_PROVIDER        CANDIDATE  required=CANDIDATE    blocking=CANDIDATE
BOOT_04_STARTUP_CONTEXT_GATE CONFIRMED  required=CANDIDATE    blocking=CANDIDATE
BOOT_05_NATIVE_BOOTSTRAP     CANDIDATE  required=UNKNOWN      blocking=UNKNOWN
BOOT_06_NETWORK_INIT         CANDIDATE  required=UNKNOWN      blocking=CANDIDATE
BOOT_07_IIPS_BOUNDARY        BOUNDARY   required=UNKNOWN      blocking=CANDIDATE
BOOT_08_GAME_INIT            UNKNOWN    required=UNKNOWN      blocking=UNKNOWN
BOOT_09_RENDERER             UNKNOWN    required=UNKNOWN      blocking=UNKNOWN
BOOT_10_INPUT_AUDIO          UNKNOWN    required=UNKNOWN      blocking=UNKNOWN
BOOT_11_MAIN_LOOP            UNKNOWN    required=UNKNOWN      blocking=UNKNOWN
BOOT_12_SHUTDOWN             UNKNOWN    required=NOT_REQUIRED blocking=NOT_BLOCKING
```

```text
CONFIRMED nodes     : BOOT_00, BOOT_01, BOOT_04          (structure and gate)
BOUNDARY nodes      : BOOT_02 (Base ordinal-1), BOOT_07 (IIPS)
CANDIDATE nodes     : BOOT_03, BOOT_05, BOOT_06
UNKNOWN nodes       : BOOT_08..BOOT_12                   (game init, renderer,
                                                          input/audio, main loop, shutdown)
NO node was invented to make the machine look complete: BOOT_09/BOOT_10/BOOT_11
stay UNKNOWN because CORE-001..009 contain no direct evidence for them.
```

`BOOT_12_SHUTDOWN` is `required = NOT_REQUIRED` by definition (a shutdown phase
cannot be a prerequisite for reaching the runtime); its semantics remain
`UNKNOWN` because the observed exit codes are observer-conditional.

---

## 4. Entry contract (BOOT_01_EXE_ENTRY)

```asm
ImageBase = 0x00400000
Entry RVA = 0x0E5DC690
0x0E5DC690  FF 15 65 C6 9D 0E   call dword ptr [0xE9DC665]
0x0E5DC696  ..             zero padding (2410 bytes, re-verified)
```

```text
ENTRY                        = CONFIRMED
ENTRY_ACTION                 = EXTERNAL_CALL
IAT slot                     = 0xE9DC665 (RVA 0xE5DC665)
slot file value              = 0x80000001 -> Base.dll ordinal 1
FF15 sites for this slot     = 1
base relocation for the slot = 0 (none)
EXE import descriptors       = 1 (codoMP_client_shipRetailBase.dll)
ENTRY_TO_ORDINAL1            = CONFIRMED
ENTRY_NATIVE_CONTINUATION    = NOT_FOUND
```

The image has 7 sections (.tp3, .tp3, .tp3, .tp3, .tp3, .tvm0, .tp3); the
`.tvm0` section is present but was **not** decoded in this round.

---

## 5. Ordinal-1 boundary contract (BOOT_02)

```text
ORDINAL1_REACHABILITY   = CONFIRMED   (12/12 observed entries, cases A/B/C/D)
ORDINAL1_INPUT_CONTRACT = UNKNOWN     (no EXE-provided arguments; register roles unassigned)
ORDINAL1_STACK_ARGUMENTS= UNKNOWN     (CORE-009 literal: NOT_CONFIRMED)
ORDINAL1_RETURN_CONTRACT= UNKNOWN     (CORE-009 literal: NOT_CONFIRMED)
ORDINAL1_RETURNED       = NOT_FOUND   (return-site hits 0/12)
ORDINAL1_NON_RETURN     = UNKNOWN     (0/12 does not prove "never returns")
RETURN_VALUE_CONSUMER   = NOT_FOUND
ORDINAL1_SIDE_EFFECT    = UNKNOWN     (CORE-009 literal: NOT_CONFIRMED)
ORDINAL1_TERMINATION    = UNKNOWN     (observer-conditional exit codes)
```

What is known about ordinal-1:

```text
- the EXE Entry performs no push, no register setup, no stack preparation;
- the boundary is reached reliably (12/12) with and without -q / -qa / -src=tgp;
- the EXE return site is never reached within the observation window;
- process-internal activity continues (threads [8, 10], modules 73)
  after the boundary entry.
```

What is unknown about ordinal-1:

```text
- the calling convention and the role of each register;
- whether it returns at all, and with what value;
- whether it passes control back into EXE-image code;
- whether it creates or hands control to another runtime;
- why the process terminates inside the observation window.
```

Ordinal-1 is therefore recorded as:

```text
BOOT_02_STATUS = BOUNDARY
ORDINAL1       = P0 UNKNOWN        (priority P0, blocking_level UNKNOWN)
```

It is **not** written as `P0 CONFIRMED`, and it is **not** used as a known
standalone contract implementation. Distinguishing "no return observed" from
"terminates the boot thread" from "transfers execution" would require Base
internals and is explicitly out of scope; the minimal experiment in section 17
tests only the EXE-visible consequence.

---

## 6. ARGV contract (BOOT_03)

```text
ARGV_COUNT_GLOBAL   = 0x0196928C
ARGV_ARRAY_GLOBAL   = 0x01969290
static write pair   = 0x00561119 (count), 0x0056111E (array)   [re-verified]
ARGV_DATA_SHAPE     = CONFIRMED   (count + char** array)
ARGV_PROVIDER       = CANDIDATE   0x00CA827C (single call site 0x00561133)
ARGV_SOURCE         = CANDIDATE   process command line (UTF-16 source shape)
```

Static operand verification performed this round:

```text
0x0196928C : 1 validated of 2 candidates -> ['0x00561119=mov dword ptr [abs], eax']
0x01969290 : 2 validated of 3 candidates -> ['0x00239c2d=mov ecx, dword ptr [abs]', '0x0056111e=mov dword ptr [abs], esi']
0x00CA827C : 1 validated of 1 candidates -> ['0x00561133=call dword ptr [abs]']
unvalidated candidates are data-like byte coincidences and are not used as evidence
```

Runtime cross-check: at the ordinal-1 boundary entry both globals still hold
`['0x00000000']` / `['0x00000000']` in all 12 runs, even when a
command line was supplied. Therefore the provider had not run at that moment in
the observed environment - an observation, not a contract.

`0x00CA827C` is **not** claimed to be `GetCommandLineW`, `GetCommandLineA` or
`CommandLineToArgvW`; its target stays runtime-bound and VIRTUAL_ONLY.

---

## 7. Startup globals and context gate (BOOT_04)

```text
0x0849413B  = CONFIRMED startup state        (1 write + 3 reads, re-verified)
              static sites: 4 validated of 5 candidates
              ['0x0016ff08=cmp byte ptr [abs], imm8', '0x0017ff46=cmp byte ptr [abs], bl', '0x00239c68=mov byte ptr [abs], imm8', '0x0028e1a4=cmp byte ptr [abs], al']
              rejected data-like candidate(s): 1
0x0849B500  = NOT_FOUND in the current EXE file image (0 operand sites)
              runtime observation: -qa sets it to 1  => RUNTIME_OBSERVED only
0x0849B501  = CONFIRMED read (1 site, ['0x002835ba=cmp byte ptr [abs], imm8'])
              write NOT_FOUND in the current EXE file image
              runtime observation: -src=tgp sets it to 1 => RUNTIME_OBSERVED only
0x08189FEC  = NOT_FOUND in the current EXE file image (0 operand sites), PACKED_OR_RUNTIME_GENERATED
```

Gate semantics (EX-031 / EX-035 / EX-046, unchanged):

```text
no args      -> WIN_NO_TCLS fatal                                  CONFIRMED
-q           -> bypass, then IIPS init error 8189fec               CONFIRMED
-qa          -> bypass, then IIPS init error 8189fec               CONFIRMED
-src=tgp     -> sets 0x0849B501, does not bypass WIN_NO_TCLS       CONFIRMED (sets) / NOT_CONFIRMED (standalone bypass)
```

New static verification this round: the gate tokens are inside the EXE file
image as one adjacent plain-text cluster:

```text
-qa        at file offset 0x6c7f64
-src=tgp   at file offset 0x6c7f68
WIN_NO_TCLS at file offset 0x6c7f80
region: ...+set....1436....console_mp.elog.main\%s.main\%s_%s..codoMP_client_ship.exe..Initializing....-q..-qa.-src=tgp....WIN_ERROR...WIN_NO_TCLS.ATVI_STUDIO_NA...
```

This confirms the startup-context gate belongs to the EXE itself
(`PROCESS`/`EXE` layer), not to a Tencent authentication layer.

At the ordinal-1 boundary entry the gate value is still
`['0x00000000']` and `['0x00000000']` (12/12), which is consistent
with the gate running after the boundary in the EXE-visible timeline.

---

## 8. Native bootstrap candidates (BOOT_05)

```text
HISTORICAL_CANDIDATES = 0x77F580, 0x77F8B3, 0x4FD9B0, 0x4FCEE0, 0x808650, 0x7E98F0, 0x6212C0
CORE-005 / CORE-006  = HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED
                     = ENTRY_CONNECTED_NATIVE_EDGES = 0
```

```text
NATIVE_BOOTSTRAP_CHAIN = CANDIDATE
ENTRY_CONNECTION       = UNKNOWN          (must not be upgraded to CONFIRMED)
```

Structural observation recorded this round (the only new inference):

```text
independent-copy runs reach the EXE-side chain head (0x77F580 family) while the static
Entry-connected graph is empty
=> POST_BOUNDARY_EXE_ENTRY_INFERENCE = CANDIDATE
   (the chain must be entered from outside the Entry-connected graph; a Base -> EXE
    transfer is one possible explanation, not a proven fact)
```

No Base internals were inspected to test that inference.

---

## 9. Network initialization (BOOT_06)

```text
NETWORK_INIT   = CANDIDATE
nodes          = 0x6212C0 (STUN/network mode init), 0x7E98F0, 0x808650
STUN endpoints = stun1-tub.codol.qq.com, stun.us.demonware.net
```

Static string verification this round:

```text
stun.us.demonware.net : present in the EXE file image at ['0x6b2610']
stun1-tub.codol.qq.com: 0 hits in the EXE file image (source unresolved)
Network Port          : present at ['0x6c7fb8']
```

```text
=> the demonware endpoint is EXE-side text; the codol.qq.com endpoint must come from
   another source (config file or another module) and is NOT proven EXE-side here.
```

The chain matches the IW4 lineage, but it is not promoted beyond `CANDIDATE` on
that basis: lineage similarity is not CODOL evidence.

---

## 10. IIPS boundary (BOOT_07)

```text
IIPS_BOUNDARY = CONFIRMED
IIPS_SUCCESS  = UNKNOWN
IIPS_FAILURE_ROOT = UNKNOWN
```

Confirmed boundary items (EX-047 / EX-048 / EX-060, unchanged):

```text
iips.dll
CNIFS::InitInGameApp
CNIFS::initIfsLib
LoadLibraryW
GetProcAddress(CreateIFSLibDll)
CreateIFSLibDll
GetProcAddress(DestoryIFSLibDll)
```

`8189FEC` stays `PACKED_OR_RUNTIME_GENERATED`:

```text
0x08189FEC = NOT_FOUND in the current EXE file image (1 iips.dll string hits exist)
=> it must not be equated with an IFS2 failure.
```

This round does **not** enter IIPS/IFS2 internals.

---

## 11. Game init, renderer, input/audio, main loop

```text
GAME_INIT  = UNKNOWN     (IW4_LINEAGE_HOMOLOGUE = CANDIDATE only)
RENDERER   = UNKNOWN
INPUT      = UNKNOWN
AUDIO      = UNKNOWN
MAIN_LOOP  = UNKNOWN
```

No node in these layers has an Entry-connected or otherwise direct CODOL
address/call/structure evidence in CORE-001..009. They are recorded as UNKNOWN
instead of being filled in from the lineage.

---

## 12. Four-layer standalone contract (every item rated)

Artifact: `exe_core010_dependency_layers.csv` (24 items)

```text
A_PROCESS  EXE identity (path + SHA-256)          CONFIRMED  required=CONFIRMED
A_PROCESS  architecture PE32/I386                 CONFIRMED  required=CONFIRMED
A_PROCESS  working directory = game root          CANDIDATE  required=CANDIDATE
A_PROCESS  command line present                   CONFIRMED  required=CONFIRMED
A_PROCESS  -q or -qa (WIN_NO_TCLS bypass)         CONFIRMED  required=CANDIDATE
A_PROCESS  environment variables                  UNKNOWN    required=UNKNOWN
B_EXE      Entry action                           CONFIRMED  required=CONFIRMED
B_EXE      IAT slot -> Base ordinal 1             CONFIRMED  required=CONFIRMED
B_EXE      argv storage                           CONFIRMED  required=CONFIRMED
B_EXE      argv provider slot                     CANDIDATE  required=CANDIDATE
B_EXE      startup globals                        CONFIRMED  required=CANDIDATE
B_EXE      internal dispatch table                CANDIDATE  required=UNKNOWN
B_EXE      native bootstrap chain                 CANDIDATE  required=UNKNOWN
C_RUNTIME  Base.dll ordinal-1 boundary            BOUNDARY   required=UNKNOWN
C_RUNTIME  system DLLs                            CONFIRMED  required=CONFIRMED
C_RUNTIME  EXE-tree project module set            CONFIRMED  required=UNKNOWN
C_RUNTIME  filesystem tree                        CONFIRMED  required=CANDIDATE
C_RUNTIME  network / STUN                         CANDIDATE  required=UNKNOWN
C_RUNTIME  IIPS / IFS2 / CNIFS                    BOUNDARY   required=UNKNOWN
C_RUNTIME  Tencent launcher components            NOT_FOUND  required=NOT_REQUIRED
D_GAME     game init                              UNKNOWN    required=UNKNOWN
D_GAME     renderer                               UNKNOWN    required=UNKNOWN
D_GAME     input / audio                          UNKNOWN    required=UNKNOWN
D_GAME     main loop                              UNKNOWN    required=UNKNOWN
```

Layer summary:

```text
Layer A (PROCESS) : identity/architecture CONFIRMED; working directory CANDIDATE;
                    command line CONFIRMED; -q/-qa CANDIDATE (gate path only);
                    environment UNKNOWN
Layer B (EXE)     : Entry + IAT + argv shape CONFIRMED; argv provider CANDIDATE;
                    startup globals mixed (0x0849413B CONFIRMED, 0x0849B500 NOT_FOUND);
                    dispatch table / native chain CANDIDATE with UNKNOWN Entry connection
Layer C (RUNTIME) : Base ordinal-1 BOUNDARY; system DLLs and module set CONFIRMED;
                    filesystem tree CANDIDATE; network CANDIDATE; IIPS BOUNDARY;
                    Tencent launcher components NOT_FOUND
Layer D (GAME)    : game init / renderer / input / audio / main loop all UNKNOWN
```

---

## 13. Tencent dependency audit (required vs optional)

Artifact: `exe_core010_required_vs_optional.csv` (17 components)

```text
WeGame                                         NOT_REQUIRED_CONFIRMED     confidence=CONFIRMED
TCLS                                           NOT_REQUIRED_CONFIRMED     confidence=CONFIRMED
Client.exe (TCLS folder)                       NOT_REQUIRED_CONFIRMED     confidence=CONFIRMED
tcls_core / TCLS.dll                           NOT_REQUIRED_CONFIRMED     confidence=CONFIRMED
TCLS shared memory / TPF_Share_Mem             NOT_REQUIRED_CONFIRMED     confidence=CANDIDATE
IIPSHostApp.exe                                UNKNOWN                    confidence=UNKNOWN
IFS2.dll                                       REQUIRED_CANDIDATE         confidence=CANDIDATE
TenProxy                                       UNKNOWN                    confidence=CANDIDATE
TenRpcs / TenSafe / GbSpy / GDPLoader / PolicyProbe UNKNOWN                    confidence=CANDIDATE
BugTrace.dll                                   UNKNOWN                    confidence=CANDIDATE
libcef.dll                                     UNKNOWN                    confidence=CANDIDATE
Base.dll ordinal-1                             REQUIRED_CANDIDATE         confidence=CANDIDATE
iips.dll                                       REQUIRED_CANDIDATE         confidence=CANDIDATE
local game tree (working dir = game root)      REQUIRED_CANDIDATE         confidence=CANDIDATE
-q or -qa                                      REQUIRED_CONFIRMED         confidence=CONFIRMED
network connectivity                           UNKNOWN                    confidence=UNKNOWN
renderer / audio / input                       UNKNOWN                    confidence=UNKNOWN
```

Rules applied:

```text
- REQUIRED_CONFIRMED is only used where a differential observation exists;
- static imports are checked first (EXE import descriptors = 1,
  codoMP_client_shipRetailBase.dll);
- load order is never treated as causality;
- no wording such as "definitely requires" / "definitely does not require" is used
  beyond the enumerated evidence levels.
```

Result: no Tencent component is proven to be a hard prerequisite of the EXE
native bootstrap. `WeGame`, `TCLS`, `Client.exe` and `tcls_core/TCLS.dll` are
`NOT_REQUIRED_CONFIRMED` for the observed path; `TenProxy`, `TenRpcs`,
`TenSafe`, `GbSpy`, `GDPLoader`, `PolicyProbe`, `BugTrace.dll` and `libcef.dll`
are loaded (or observed) but remain `UNKNOWN` as dependencies.

---

## 14. Standalone gap list

Artifact: `exe_core010_gap_list.csv` (12 gaps)

```text
GAP-P0-001   C_RUNTIME  POST_BOUNDARY_CONTROL_TRANSFER     UNKNOWN      blocking=UNKNOWN      priority=P0
GAP-P0-002   C_RUNTIME  BASE_ORDINAL1_BOUNDARY_CONTRACT    UNKNOWN      blocking=UNKNOWN      priority=P0
GAP-P0-003   B_EXE      EXE_ENTRY_NATIVE_CONTINUATION      NOT_FOUND    blocking=UNKNOWN      priority=P0
GAP-P0-004   C_RUNTIME  OBSERVATION_ENVIRONMENT_DIVERGENCE UNRESOLVED   blocking=UNKNOWN      priority=P0
GAP-P1-001   B_EXE      NATIVE_BOOTSTRAP_ENTRY_CONNECTION  UNKNOWN      blocking=CANDIDATE    priority=P1
GAP-P1-002   C_RUNTIME  IIPS_INITIALIZATION                UNKNOWN      blocking=CANDIDATE    priority=P1
GAP-P1-003   B_EXE      ARGV_PROVIDER_SLOT                 CANDIDATE    blocking=CANDIDATE    priority=P1
GAP-P1-004   B_EXE      RUNTIME_DISPATCH_MINIMUM           CANDIDATE    blocking=UNKNOWN      priority=P1
GAP-P2-001   D_GAME     GAME_INIT                          UNKNOWN      blocking=UNKNOWN      priority=P2
GAP-P2-002   D_GAME     RENDERER_MAIN_LOOP                 UNKNOWN      blocking=UNKNOWN      priority=P2
GAP-P3-001   C_RUNTIME  PLATFORM_SERVICES                  UNKNOWN      blocking=NOT_BLOCKING priority=P3
GAP-P3-002   A_PROCESS  ENVIRONMENT_VARIABLES              UNKNOWN      blocking=UNKNOWN      priority=P3
```

```text
P0 gaps : 4  -> GAP-P0-001, GAP-P0-002, GAP-P0-003, GAP-P0-004
P1 gaps : 4  -> GAP-P1-001, GAP-P1-002, GAP-P1-003, GAP-P1-004
P2 gaps : 2  -> GAP-P2-001, GAP-P2-002
P3 gaps : 2  -> GAP-P3-001, GAP-P3-002

P0 with blocking_level=CONFIRMED : 0
P0 with blocking_level=UNKNOWN   : 4
```

This is the formal encoding of the round rule: the observed
`ordinal1 -> no return point` proves only
`BOUNDARY_NO_RETURN_OBSERVED`. It does **not** prove `P0 = Base ordinal-1`.
Ordinal-1 may enter a long-lived runtime, create threads, transfer execution, or
terminate the boot thread - none of those alternatives has been separated by
caller-side evidence yet. Hence `ORDINAL1 = P0 UNKNOWN`.

`GAP-P0-003` is the only P0 item with a CONFIRMED `current_status`
(`NOT_FOUND`: the EXE has no Entry-connected native continuation), yet its
`blocking_level` is still `UNKNOWN`: a confirmed structural absence does not by
itself prove that boot is blocked, because the continuation may be entered from
outside the Entry-connected graph. No P0 item in this round reaches
`blocking_level = CONFIRMED`.

---

## 15. Required answers

### Q1. EXE 自身已经确认的启动条件是什么？

```text
CONFIRMED:
  PE32 / I386 image, ImageBase 0x00400000, Entry RVA 0x0E5DC690
  Entry = single FF15 indirect call through IAT slot 0xE9DC665 -> Base.dll ordinal 1
  exactly one import descriptor (codoMP_client_shipRetailBase.dll), no base relocations
  fall-through after the call is zero padding (2410 bytes)
  argv storage 0x0196928C / 0x01969290 with confirmed static write pair
  0x0849413B startup gate byte (1 write + 3 reads), 0x0849B501 read
  startup-context gate tokens (-q / -qa / -src=tgp / WIN_NO_TCLS) exist inside the EXE image
  WIN_NO_TCLS semantics: no args -> fatal, -q or -qa -> bypass (CANDIDATE as a requirement for
  the observed path only)
  boundary entry is reached 12/12 with any tested command line
```

### Q2. 哪些条件只是历史候选？

```text
CANDIDATE:
  argv provider slot 0x00CA827C (target VIRTUAL_ONLY, not a proven Windows API)
  argv source = process command line (API name unbound)
  native bootstrap chain 0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> 0x6212C0
    (ENTRY_CONNECTION = UNKNOWN, HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED)
  network / STUN initialization (0x6212C0 family)
  runtime dispatch table minimum
  IW4 lineage homology for game init
  working directory = game root, full local game tree (observation-derived, no ablation)
```

### Q3. 哪些 Tencent 组件目前没有被证明为 EXE native bootstrap 的硬前置？

```text
NOT_REQUIRED_CONFIRMED for the observed path:
  WeGame, TCLS, Client.exe (TCLS folder), tcls_core / TCLS.dll
  (direct launch entered native bootstrap and reached the post-gate IIPS fatal)
NOT_REQUIRED_CONFIRMED (weaker observation, single source):
  TCLS shared memory / TPF_Share_Mem
UNKNOWN - loaded but never proven required:
  TenProxy, TenRpcs, TenSafe, GbSpy, GDPLoader, PolicyProbe, BugTrace.dll, libcef.dll
NOTE:
  none of these components appears in the EXE import table, and none of them could be
  shown to be a hard prerequisite before IIPS.
```

### Q4. ordinal-1 当前到底知道什么、不知道什么？

```text
KNOWN:
  reached 12/12; stable input register values
  (EAX/EDX/ESI/EDI/EFLAGS); stable stack data in this environment; no EXE-provided arguments;
  no EXE-side return-value consumer; process-internal threads and modules appear afterwards
UNKNOWN:
  input contract, calling convention, register roles, stack argument contract,
  return contract, non-return, side effects, termination semantics,
  whether control transfers back into EXE-image code
FORBIDDEN UPGRADES:
  0/12 return -> NONRETURN_CONFIRMED            (NO)
  12/12 reachability -> closed contract         (NO)
  ESI = Base+0 -> NULL context                  (NO)
```

### Q5. 真正的 P0 gap 是什么？

```text
P0 is NOT "Base ordinal-1" as a confirmed blocker.
The primary P0 unknown is:
  GAP-P0-001 POST_BOUNDARY_CONTROL_TRANSFER
    does EXE-image code execute at/after the Base ordinal-1 boundary, and which module enters it?
supported by:
  GAP-P0-003 EXE_ENTRY_NATIVE_CONTINUATION = NOT_FOUND   (confirmed structural fact, blocking UNKNOWN)
  GAP-P0-004 OBSERVATION_ENVIRONMENT_DIVERGENCE = UNRESOLVED
  GAP-P0-002 BASE_ORDINAL1_BOUNDARY_CONTRACT = UNKNOWN
=> ORDINAL1 = P0 UNKNOWN, never P0 CONFIRMED.
=> no P0 item reaches blocking_level = CONFIRMED in this round.
```

### Q6. 真正的 P1 gap 是什么？

```text
P1-001 NATIVE_BOOTSTRAP_ENTRY_CONNECTION = UNKNOWN/CANDIDATE  (caller of the 0x77F580 chain head)
P1-002 IIPS_INITIALIZATION               = UNKNOWN/CANDIDATE  (first failing prerequisite, 8189FEC source)
P1-003 ARGV_PROVIDER_SLOT                = CANDIDATE          (who binds 0x00CA827C, when it runs)
P1-004 RUNTIME_DISPATCH_MINIMUM          = CANDIDATE/UNKNOWN  (minimum slot set)
```

### Q7. 如果要继续，只能设计哪一个最小实验？

```text
E-010-01 POST_BOUNDARY_EXECUTION_OWNER_CENSUS  (decision = ONE_ONLY)
single variable: EXE_IMAGE_EXECUTION_AFTER_BOUNDARY in {OBSERVED, NOT_OBSERVED}
```

See section 17. No other experiment is selected this round.

---

## 16. Standalone boot contract (evidence-consistent)

```text
PROCESS
  |
  v
EXE ENTRY                         CONFIRMED
  |                               Entry RVA 0x0E5DC690, FF 15 -> slot 0xE9DC665
  v
BASE ORDINAL-1                    BOUNDARY
  |                               reached 12/12
  |                               EXE return site 0xE5DC696 hit 0/12
  |
  +-- input contract             UNKNOWN      (no EXE-provided arguments; register roles unassigned)
  +-- stack argument contract    UNKNOWN      (CORE-009 literal NOT_CONFIRMED)
  +-- return contract            UNKNOWN      (CORE-009 literal NOT_CONFIRMED)
  +-- non-return                 UNKNOWN      (0/12 observed return only)
  +-- side effects               UNKNOWN      (CORE-009 literal NOT_CONFIRMED)
  +-- termination semantics      UNKNOWN      (observer-conditional exit codes 0xC0000005, 0xC0000409)
  +-- control transfer to EXE    UNKNOWN      (POST_BOUNDARY_EXE_ENTRY_INFERENCE = CANDIDATE)
  |
  v   (EXE-visible timeline continues; the following nodes are NOT Entry-connected statically)
ARGV                             CONFIRMED data shape / CANDIDATE provider
  |                               0x0196928C + 0x01969290; provider slot 0x00CA827C
  |                               at boundary entry both globals = 0 (12/12)
  v
STARTUP CONTEXT GATE             CONFIRMED (WIN_NO_TCLS, -q / -qa bypass)
  |                               gate tokens verified inside the EXE file image
  v
NATIVE BOOTSTRAP                 CANDIDATE
  |                               0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0
  |                               ENTRY_CONNECTION = UNKNOWN
  +-- NETWORK                    CANDIDATE    (0x808650 / 0x7E98F0 / 0x6212C0, STUN)
  +-- IIPS                       BOUNDARY     (iips.dll / IFS2.dll / CNIFS; SUCCESS = UNKNOWN)
  +-- GAME INIT                  UNKNOWN
  |
  v
RENDERER                         UNKNOWN
  |
  v
INPUT / AUDIO                    UNKNOWN
  |
  v
MAIN LOOP                        UNKNOWN
  |
  v
SHUTDOWN                         UNKNOWN (not a boot prerequisite by definition)
```

The diagram above is the only form consistent with the evidence ledger: every
node that has no direct evidence is labelled `UNKNOWN`, and the single external
boundary is labelled `BOUNDARY` with its contract explicitly open.

---

## 17. Next experiment (ONE_ONLY)

Artifact: `exe_core010_next_experiment.csv` (1 row, decision = ONE_ONLY)

```text
experiment_id            : E-010-01
gap_ids                  : GAP-P0-001; GAP-P0-002; GAP-P0-003; GAP-P0-004
decision                 : ONE_ONLY
single_variable          : EXE_IMAGE_EXECUTION_AFTER_BOUNDARY in {OBSERVED, NOT_OBSERVED}
method                   : Reuse the CORE-009 temporary-breakpoint observer (no file modification). Keep the ordinal-1 entry breakpoint, add a BOUNDED set of execute breakpoints at the EXE-side chain heads (VA = 0x00400000 + {0x77F580, 0x77F8B3, 0x4FD9B0, 0x4FCEE0, 0x808650, 0x7E98F0, 0x6212C0}) and record the owning module of every hit.
measures                 : whether EXE-image code executes after the Base ordinal-1 boundary and which module enters it; plus whether the ordinal-1 termination stays identical without extra breakpoints
exe_side_only            : YES
base_internals_required  : NO (address ownership only; no Base disassembly / CFG / .tvm0)
cost                     : 1 observation session; <= 8 breakpoints; <= 300s wall clock; bounded event log
expected_uncertainty     : collapses GAP-P0-001 and GAP-P0-003 from UNKNOWN to one bit; if OBSERVED it also names the entering module and moves P0 from 'does a native path exist' to 'how to reach that path standalone'
fallback_if_negative     : if EXE-image execution is NOT_OBSERVED in both the observer and the normal-copy environment, stop reverse engineering and switch to Standalone Bootstrap Design (boundary replacement track)
notes                    : No -q/-qa matrix extension, no Base internals, no credential / session / token work.
```

Why this one and only this one:

```text
- it is a single variable with two outcomes (OBSERVED / NOT_OBSERVED);
- it is EXE-side only and needs no Base internals, no patch, no stub DLL;
- it resolves the P0 item that actually blocks a standalone bootstrap design
  ("does any EXE-native continuation exist after the boundary?");
- either outcome is usable: OBSERVED names the entering module and the native path,
  NOT_OBSERVED justifies switching from reverse engineering to design.
```

No second experiment is scheduled. CORE-009 already reported
`NO_SINGLE_NARROW_VARIABLE_CONFIRMED` for further boundary-input experiments, so
repeating the `-q/-qa/-src=tgp` matrix is explicitly not selected.

---

## 18. Artifact inventory

```text
CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md   (this report)
exe_core010_evidence_ledger.csv                   (39 rows)
exe_core010_boot_state_machine.csv                (13 nodes)
exe_core010_contract_matrix.csv                   (38 contracts)
exe_core010_dependency_layers.csv                 (24 items)
exe_core010_required_vs_optional.csv              (17 components)
exe_core010_gap_list.csv                          (12 gaps)
exe_core010_next_experiment.csv                   (1 row)
core010_bootstrap_contract.py                     (generator)
```

Inputs consumed: `exe_core009_runs.csv`, `exe_core009_registers.csv`,
`exe_core009_stack.csv`, `exe_core009_state_delta.csv`,
`exe_core009_thread_delta.csv`, `exe_core009_module_delta.csv`,
`exe_core009_fs_delta.csv`, `exe_core009_contract_matrix.csv`,
`CODOL_STANDALONE_CORE_009_BOUNDARY_OBSERVATION.md`, CORE-005/006/007/008 final
status blocks, EX-031/035/043/044/045/046/047/048/060.

---

## 19. Quality validation

```text
PASS  EXE SHA-256 match                      36997674B18F2896DE5E9D75...
PASS  Entry bytes re-decode                  FF 15 65 C6 9D 0E
PASS  IAT slot = Base ordinal 1              0x80000001
PASS  import descriptors = 1 (Base only)     codoMP_client_shipRetailBase.dll
PASS  base relocations absent                reloc dir size 0
PASS  0x0849413B sites = 4 validated         0x0016ff08=cmp byte ptr [abs], imm8; 0x0017ff46=cmp byte ptr [abs], bl; 0x00239c68=mov byte ptr [abs], imm8; 0x0028e1a4=cmp byte ptr [abs], al
PASS  0x0849B500 static sites = 0            NOT_FOUND
PASS  0x0849B501 sites = 1 validated read    0x002835ba=cmp byte ptr [abs], imm8
PASS  0x08189FEC static sites = 0            NOT_FOUND
PASS  argv count write site validated        0x00561119=mov dword ptr [abs], eax
PASS  argv array write site validated        0x00239c2d=mov ecx, dword ptr [abs]; 0x0056111e=mov dword ptr [abs], esi
PASS  provider call site validated           0x00561133=call dword ptr [abs]
PASS  gate tokens present in EXE image       token cluster verified
PASS  CORE-009 runs re-aggregated            12/12 entries, 0/12 returns
PASS  CORE-009 register stability            EAX/EDX/ESI/EDI/EFLAGS stable
PASS  FS metadata delta is zero              0 rows
PASS  P0 blocking level not upgraded         no P0 row reaches CONFIRMED blocking
PASS  13 boot nodes present                  BOOT_00..BOOT_12
PASS  CORE-009 literals preserved            NOT_CONFIRMED rows retained in core009_literal
PASS  no EXE/DLL byte written                read-only access
```

Reproduce with:

```text
python core010_bootstrap_contract.py
```

---

## 20. Final status

```text
STANDALONE_BOOTSTRAP_STATUS = BLOCKED_BY_UNKNOWN
RATIONALE                   = P0 gaps exist but none reaches CONFIRMED blocking level; the primary unknown is whether EXE-image code executes at/after the boundary
PRIMARY_UNKNOWN             = ORDINAL1_CONTROL_TRANSFER_VS_TERMINATION
SECONDARY_UNKNOWN           = IIPS_FIRST_FAILING_PREREQUISITE
NEXT_EXPERIMENT             = E-010-01 (ONE_ONLY)
FINAL_MARKER                = BOOTSTRAP_CONTRACT_WITH_EXPLICIT_UNKNOWNS
```

The status enumeration is resolved from the evidence rather than presupposed:

```text
READY_FOR_IMPLEMENTATION -> rejected: Layer C and Layer D still contain open BOUNDARY / UNKNOWN items
BLOCKED_BY_P0            -> rejected: no P0 item reaches blocking_level = CONFIRMED for the
                            ordinal-1 transfer/termination question (only the structural
                            absence of an Entry-connected continuation is CONFIRMED)
BLOCKED_BY_P1            -> rejected: P1 items exist but sit behind the P0 unknown
BLOCKED_BY_UNKNOWN       -> selected
```

The project is not ready for implementation, and it is not proven that Base
ordinal-1 is the blocker either. What is proven is that the first Entry-connected
external transfer has an open contract and that the EXE has no static
Entry-connected continuation.

---

## 21. Corrections applied to the earlier CORE-010 draft

A CORE-010 draft was written before the final CORE-009 report existed; it was
regenerated because it still contained pre-CORE-009 wording:

```text
ORDINAL1_RETURN            : UNKNOWN -> NOT_FOUND (0/12 observed) plus ORDINAL1_NON_RETURN = UNKNOWN
ORDINAL1_STACK             : UNKNOWN -> UNKNOWN with the CORE-009 literal NOT_CONFIRMED preserved
ORDINAL1_SIDE_EFFECT       : UNKNOWN -> UNKNOWN with the CORE-009 literal NOT_CONFIRMED preserved
-qa -> 0x0849B500 = 1      : CONFIRMED -> NOT_FOUND (static) plus RUNTIME_OBSERVED (dynamic only)
argv at the boundary       : implicit "available" -> recorded as 0x0 at boundary entry (12/12)
P0-001 wording             : "BASE_ORDINAL1_BOUNDARY = P0" -> P0 UNKNOWN (priority P0, blocking UNKNOWN)
draft status               : BLOCKED_BY_P0 -> BLOCKED_BY_UNKNOWN (evidence-consistent)
evidence ledger schema     : missing id/address -> id + address columns added
state machine schema       : 11 nodes without required/blocking_level -> 13 nodes with both
gap list schema            : missing layer -> layer column added
next experiment artifact   : absent -> exe_core010_next_experiment.csv (ONE_ONLY)
```

Newly added evidence this round (all read-only static verification): the EXE
import set, the gate-token cluster offsets, the STUN endpoint string location,
and the observation-window coverage limitation.

---

## 22. Core principle

> **Do not try to eliminate the UNKNOWN; place the UNKNOWN precisely inside the Bootstrap Contract.**

The target of this work remains the EXE's own startup architecture:

```text
codoMP_client_shipRetail.exe -> standalone native bootstrap -> game runtime
```

not the reconstruction of WeGame / TCLS / Client.exe.
