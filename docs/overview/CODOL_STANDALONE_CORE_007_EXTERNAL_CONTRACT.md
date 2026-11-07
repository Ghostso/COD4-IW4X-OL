# CODOL_STANDALONE_CORE_007
# codoMP_client_shipRetail.exe — External-Boundary Contract Recovery

## 0. Scope and inherited baselines

```text
SAMPLE   = COD OL\codoMP_client_shipRetail.exe
SHA-256  = 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
PE       = PE32 / I386
ImageBase= 0x00400000
Entry RVA= 0x0E5DC690
SAMPLE_MATCH_CONFIRMED
```

Only `codoMP_client_shipRetail.exe` was analysed, and only as a **static file
image**. No WeGame, TCLS, TenProxy, Base.dll internals, CODOL-MP.exe,
Sandboxie, Procmon, patch, hook, or debugger-dependent conclusion was used.
Base ordinal-1 is referred to only as `EXTERNAL_BOUNDARY`.

Inherited from EXE-CORE-006 (not re-proven here):

```text
Entry -> EXE native fall-through  = NOT_FOUND
Entry -> EXE native continuation  = NOT_FOUND
TLS callback array                = empty
Entry -> historical bootstrap     = NOT_CONNECTED
.tvm0                            = not treated as ordinary code
Entry next verifiable node        = IAT slot 0x0E5DC665
```

This round asks a **different** question:

> What "startup contract traces" did the EXE itself leave behind that tell us
> what state `Base ordinal_1` historically had to prepare?

The answer is built only from EXE-internal evidence. It is **not** assumed that
Base hands execution back to a particular function.

---

## 1. Executive Summary (final six answers)

```text
1. EXE 内已经确认的启动状态有哪些？
   = 0x0849413B  (startup gate, EXISTS: 3 reads + 1 write)
     0x0849B501  (startup gate, read-only in file: 1 read)
     0x0849B500  = NO static access (0 occurrences)
     0x08189FEC  = NO static access (runtime-produced)

2. -q / -qa / -src=tgp 在 EXE 内形成了哪些可验证的数据流？
   = ONE partially confirmed chain:
       argv string compare -> mov byte [0x0849413B], 1  (WRITE, CONFIRMED)
     0x0849B500 / 0x0849B501 writes are NOT present in the file image.

3. EXE 内哪些 function-pointer / dispatch mechanism 可以确认？
   = a genuine dispatch slot array exists (0x00CA8xxx / 0x00E2Cxxx ...),
     BUT 100% of its confirmed targets live in the VIRTUAL_ONLY runtime
     region. CONFIRMED function pointers to file-backed code = NONE.

4. EXE 内哪些 filesystem / renderer / network / game runtime islands 可以确认？
   = network (STUN, 0x002212C0) and bootstrap-gate islands are RAW-BACKED.
     filesystem is only a string-referenced CANDIDATE.
     renderer / game islands = UNKNOWN.

5. IIPS 结果进入 EXE 后，EXE 自身如何消费？
   = UNKNOWN / BOUNDARY (the failure state 0x08189FEC is not referenced by
     any absolute operand in the file image)

6. Standalone Bootstrap 最小需要准备哪些 EXE-visible state？
   REQUIRED_CONFIRMED : 0 items strictly proven complete
   REQUIRED_CANDIDATE : 0x0849413B, 0x00CA827C provider, argv globals
   UNKNOWN            : 0x0849B500, 0x0849B501 write source, IIPS result path
```

**Stop condition reached: E.** The current file image yields only
`Entry -> Base ordinal_1 -> external boundary` plus several Entry-independent
runtime islands. Per the specification, EXE-wide blind scanning stops here.

---

## 2. Confirmed startup-state globals

All references were found by an absolute-memory-operand scan that requires the
instruction to be **alignment-validated** (reached by a `55 8B EC` linear
sweep from within the same section). Misaligned `FF/80/38 05 disp32` byte
patterns inside packed data are excluded.

```text
0x0849413B   (RVA 0x0809413B, VIRTUAL_ONLY, section 2 RW)
  WRITE 0x00239C68  C6 05 3B 41 49 08 01   mov byte ptr [0x0849413B], 1
  READ  0x0016FF08  80 3D 3B 41 49 08 00   cmp byte ptr [0x0849413B], 0
  READ  0x0017FF46  38 1D 3B 41 49 08      cmp byte ptr [0x0849413B], bl
  READ  0x0028E1A4  38 05 3B 41 49 08      cmp byte ptr [0x0849413B], al

0x0849B501   (RVA 0x0809B501, VIRTUAL_ONLY, section 2 RW)
  READ  0x002835BA  80 3D 01 B5 49 08 00   cmp byte ptr [0x0849B501], 0
  WRITE = NOT_FOUND in the file image

0x0849B500   (RVA 0x0809B500, VIRTUAL_ONLY, section 2 RW)
  occurrences of the 4-byte VA anywhere in the file = 0

0x08189FEC   (RVA 0x07D89FEC, VIRTUAL_ONLY, section 2 RW)
  occurrences of the 4-byte VA anywhere in the file = 0
```

### 2.1 Alignment correction of the prior rounds

The prior rounds recorded reads at `EXE+0x2213B9` / `EXE+0x2214C5` for
`0x849413B` from a **runtime memory scan**. Static re-derivation finds the same
global at four sites, but the exact addresses differ because the runtime image
contained unpacked bytes. The static sites above are the ones that exist in
the shipped file.

A separate and important correction: the instruction at RVA `0x0016FF11`
is

```asm
0056FF11  80 3D 00 B5 09 00 90   cmp byte ptr [0x0009B500], 0x90
```

which references VA **`0x0009B500`** (RVA `0x9B500`, raw-backed in section 0),
**not** `0x0849B500`. The two addresses share the low bytes `B500`, which is
why a byte-level search can conflate them. `0x0849B500` has no static access at
all.

---

## 3. Function-pointer / dispatch mechanism

### 3.1 The dispatch slot array

Every `FF 15 <abs32>` (`call dword ptr [abs]`) and `FF 25` (`jmp`) site in the
two raw-backed executable sections was enumerated and grouped by slot VA:

```text
total distinct indirect slots           = 1193
slots whose site is alignment-valid     = 88
slots whose slot value targets
    VIRTUAL_ONLY (runtime code)         = 229
slots whose slot value targets
    RAW_BACKED_EXECUTABLE               = 7 (unvalidated)
                                        = 0 (after alignment + table-shape check)
confirmed function pointers to
    file-backed executable code         = NONE
```

The genuine slots form a **contiguous pointer table** in section 1
(`RAW_BACKED_DATA`, VA `0x00CA8000` upward), for example:

```text
slot 0x00CA8114 -> 0x00A13726
slot 0x00CA8118 -> 0x00A1373E
slot 0x00CA811C -> 0x00A13748
slot 0x00CA812C -> 0x00A1378C
slot 0x00CA819C -> 0x00A139A0
```

Every target (`0x00A1378C` -> RVA `0x0061378C`) is **VIRTUAL_ONLY**: inside a
section's declared virtual size but beyond its raw backing. The table is
populated at runtime; the file only contains the slot addresses and the call
sites.

### 3.2 The two apparent file-backed pointers

Seven slots initially appeared to point at raw-backed code. Manual alignment
checks disproved all seven:

* slot `0x00E5C8F0` sits inside a repeated double-constant run
  (`0x00483390` repeated); its call site `0x0005DECE` is not an instruction
  boundary.
* slot `0x00008844` is a near-null address (`VA 0x8844`, unmapped); the site
  `0x00372040` sits in packed data.
* the remaining five (`0x00E5C294`, `0x00E4F49C`, `0x005B4B0C`, `0x000C862C`,
  `0x00E3CC54`) likewise have misaligned `FF 15` sites.

```text
CONFIRMED_FUNCTION_POINTER count = 0
```

This is the direct answer to question 3: the EXE **does** have a dispatch
mechanism, but it is a runtime-populated import-style table whose entries are
not recoverable from the file.

### 3.3 CORE-005's 17 suspects, reclassified

| Suspect | Kind | Classification |
|---|---|---|
| `0x0E9DC665` | IMPORT_IAT_SLOT | EXTERNAL_BOUNDARY |
| `0x00CA8000` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot); target VIRTUAL_ONLY |
| `0x00CA812C` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x00CA8190` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x00CA819C` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x00CA8170` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x00CA8534` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x00CA8114` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x00CA818C` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x00CA84C8` | FUNCTION_POINTER_SLOT | DATAFLOW_CONFIRMED (slot) |
| `0x0849413B` | RUNTIME_GENERATED | UNKNOWN (state byte, not a table) |
| `0x0849B500` | RUNTIME_GENERATED | UNKNOWN |
| `0x0849B501` | RUNTIME_GENERATED | UNKNOWN |
| `0x08426AEC` | RUNTIME_GENERATED | UNKNOWN |
| `0x0E9DC635` | (import descriptor) | UNKNOWN |
| `0x0E9DC641` | (import name) | UNKNOWN |
| `0x0E9DC645` | (import FirstThunk copy) | UNKNOWN |

No string table, jump table, or constructor table was confirmed.

---

## 4. argv / command-line dataflow

### 4.1 Statically visible links

```text
stage 1  COMMANDLINE_PROVIDER_CALL   DATAFLOW_CONFIRMED
   RVA 0x00561133   FF 15 7C 82 CA 00   call dword ptr [0x00CA827C]
   slot 0x00CA827C statically holds 0x00A1517E  -> VIRTUAL_ONLY

stage 2  ARGV_STORAGE_GLOBAL         BOUNDARY
   0x0196928C  argv count        (VIRTUAL_ONLY)
   0x01969290  argv pointer array (VIRTUAL_ONLY)

stage 3  ARGV_PREDICATE_FUNCTION     CANDIDATE
   RVA 0x0037F580 (raw-backed .text; documented -q/-qa gate)

stage 4  GATE_STATE_WRITE            DATAFLOW_CONFIRMED
   RVA 0x00239C68   mov byte ptr [0x0849413B], 1
```

The slot `0x00CA827C` is the EXE's single argv-provider dispatch slot. Its call
site is unique and alignment-valid; the slot's *target* is runtime-only, so
the API identity behind it remains

```text
DATAFLOW_UNRESOLVED  (target)  /  DATAFLOW_CONFIRMED  (call site)
```

### 4.2 The `-q` gate write

The write site sits inside a `strcmp`-shaped loop:

```asm
00639C51  movsx edx, byte ptr [edi + ecx]
00639C55  movsx esi, byte ptr [ecx]
00639C58  mov   ebx, eax
00639C5A  inc   ecx
00639C5B  dec   eax
00639C5C  test  ebx, ebx
00639C5E  je    0x639c83
00639C60  cmp   edx, esi
00639C62  jne   0x639c74
00639C64  test  edx, edx
00639C66  jne   0x639c51
00639C68  mov   byte ptr [0x0849413B], 1     <-- gate set
00639C6F  jmp   0x639d42
```

This is the EXE-internal, statically recoverable half of the `-q` contract:
a command-line token comparison sets `0x0849413B`.

### 4.3 What is NOT recoverable

```text
[0x0849B500] = 1  (-qa)      -> write site NOT in the file image
[0x0849B501] = 1  (-src=tgp) -> write site NOT in the file image
```

Only reads remain (`0x002835BA` for `0x0849B501`). Their writers execute in the
virtual-only region and cannot be resolved statically. Reported as
`DATAFLOW_UNRESOLVED`, not as absent.

---

## 5. Resource / filesystem contract

Literal byte search plus aligned immediate/absolute xref search:

| Resource needle | Present | Immediate ref | Classification |
|---|---|---|---|
| `settings_c.zip.iw4` | yes (RVA 0x9B51F8) | 1 (`push 0x00DB51F8` at 0x00054C4F) | CANDIDATE |
| `settings_m.zip.iw4` | yes (RVA 0x9B520C) | 0 | CANDIDATE |
| `main\video\%s.bk2` | yes (RVA 0x9C0A33) | 0 | CANDIDATE |
| `main\%s` | yes (RVA 0x9DBF24) | 1 (`push 0x00DDBF24` at 0x00239B7C) | CANDIDATE |
| `main\demo` | NO | – | NOT_FOUND |
| `players/config_mp.cfg` | NO (full path absent) | – | NOT_FOUND |
| `players\` | NO | – | NOT_FOUND |
| `GameBabyConfig.dat` | NO | – | NOT_FOUND |
| `config_mp` | yes (RVA 0x9BCFE0) | 0 | CANDIDATE |

Two aligned immediate references were recovered:

```asm
00639B7C  68 24 BF DD 00   push 0x00DDBF24      ; "main\%s"
00639B81  E8 90 54 32 01   call 0x195F016       ; VIRTUAL_ONLY
```

```asm
00454C4F  68 F8 51 DB 00   push 0x00DB51F8      ; "settings_c.zip.iw4"
```

Both reference sites lie in streams that are only *locally* consistent
(`pushal`, `pop ss`, `dec eax` neighbours), so neither reaches
`ALIGNMENT_VALID` status under the strict prologue-anchored sweep.

The surrounding stream is partially obfuscated (`pushal`, `pop ss`, mixed
alignment), so a **complete** filesystem-initialization dataflow cannot be
claimed. Deliberately downgraded to `CANDIDATE`.

**Conclusion:** the shipped EXE contains the resource *names* of the engine
filesystem contract, but the code that consumes them is not statically
reachable. No `EXE-internal filesystem initialization candidate` is confirmed.

Answer to the required sub-questions:

```text
EXE 是否引用这些资源？            部分引用 (字符串存在)
引用位置在哪里？                  section 1 (RVA 0x9B5xxx-0x9DBxxx)
引用是否属于启动路径？            UNKNOWN (消费代码位于 virtual-only)
引用前是否存在条件判断？          UNKNOWN
是否存在 filesystem init candidate？ CANDIDATE (main\%s 单点引用)
```

---

## 6. IIPS boundary (EXE side only)

```text
WIN_IIPS_INIT_ERROR   1 hit   RVA 0x9C93A8   CANDIDATE
WIN_IIPS_INIT_FAILED  1 hit   CANDIDATE
WIN_IIPS_DLL_ERROR    1 hit   CANDIDATE
IIPS\iips.dll         1 hit   RVA 0x9C93F0   CANDIDATE
iips.dll              1 hit   CANDIDATE
iipsinit              1 hit   RVA 0xA6F90C   CANDIDATE
8189fec / 8189FEC     0 hits                 NOT_FOUND
0x0037FA70 (handler)  raw-backed             CANDIDATE
```

The literal error value string `8189fec` does **not** appear in the EXE file
image, and VA `0x08189FEC` has zero absolute-operand references. The failure
value is produced at runtime (inside the IIPS/loader path), and the EXE-side
consumer is not statically visible.

```text
IIPS result -> EXE state -> fatal/continue   = UNKNOWN / BOUNDARY
```

No guessing was performed; iips.dll internals were not entered.

---

## 7. Runtime islands (Entry-independent)

| Island | Functions (RVA) | Globals | Mapping | Activation |
|---|---|---|---|---|
| bootstrap_gate | 0x0037F580, 0x0037FA70 | 0x0849413B, 0x0849B501 | raw-backed .text | CANDIDATE_ARGV_GATE |
| argv_provider | 0x00561133 (call site) | 0x00CA827C | raw-backed .text / slot | CANDIDATE_EXTERNAL_PROVIDER |
| network_stun | 0x002212C0, 0x002213B9, 0x002214C5 | 0x0849413B, 0x0849B500 | raw-backed .text | CANDIDATE_GATE_CONSUMER |
| iips_boundary | 0x0037FA70 | 0x08189FEC | raw-backed .text | CANDIDATE_FAILURE_BOUNDARY |
| scaleform_exports | 0x000364F0, 0x000365E0, 0x00036520 | – | raw-backed .text | CANDIDATE_EXTERNAL_CALLER |

```text
Entry-reachable graph = 1 block (CORE-006)
All islands above are ENTRY_INDEPENDENT / RUNTIME_ISLAND
Activation relationship between islands = UNKNOWN
```

The islands are confirmed to **exist as code**, but nothing in the static image
proves how they are switched on. This is the definition of stop condition D.

---

## 8. Activation candidates

| Candidate | Kind | Mechanism | Entry-connected | Class |
|---|---|---|---|---|
| `0x0849413B` | STARTUP_STATE_GLOBAL | argv gate writes 1; consumers branch | NO | CANDIDATE |
| `0x00CA827C` | INDIRECT_SLOT | `call [slot]` at 0x00561133 provides argv | NO | CANDIDATE |
| `0x0849B501` | STARTUP_STATE_GLOBAL | single static read at 0x002835BA | NO | UNKNOWN |
| `0x0037F580` | PREDICATE_FUNCTION | documented -q/-qa gate predicate | NO | CANDIDATE |
| `0x0E5DC665` | EXTERNAL_BOUNDARY | PE Entry calls Base.dll ordinal 1 | YES | BOUNDARY |

---

## 9. Evidence levels

```text
CONFIRMED
  - Entry = 0x0E5DC690, call dword ptr [0x0E9DC665]
  - Entry -> external boundary (Base.dll ordinal 1)
  - 0x0849413B: 3 alignment-validated reads + 1 write
  - 0x0849B501: 1 alignment-validated read
  - 0x00CA827C: exactly one FF15 call site (0x00561133)
  - dispatch slot array exists with alignment-valid call sites

CANDIDATE
  - 0x0037F580 predicate function
  - resource strings (settings_*, main\*) with at most one immediate ref
  - the five runtime islands

UNKNOWN
  - activation relationship between islands
  - writers of 0x0849B500 / 0x0849B501
  - IIPS result consumer inside the EXE
  - thread-start mechanism

BOUNDARY
  - Base.dll ordinal 1 (EXTERNAL_BOUNDARY)
  - 0x0196928C / 0x01969290 argv globals (VIRTUAL_ONLY)
  - 0x08189FEC IIPS failure state (no static reference)
  - .tvm0

NOT_FOUND
  - Entry-connected EXE native continuation
  - confirmed function pointers to file-backed code
  - static writers for the -qa / -src=tgp gate bytes
  - filesystem initialization function
  - players\ and GameBabyConfig.dat in the file image
```

---

## 10. Negative findings

* The EXE dispatch table's entries are all virtual-only; the file image contains
  no confirmed function pointer into its own raw-backed code.
* `0x0849B500` and `0x08189FEC` have **zero** absolute-operand occurrences in
  the whole file image.
* The `0x0016FF11` instruction that appears near `0x0849413B` actually
  references `0x0009B500`; the two must not be conflated.
* The `-q` write is the only gate write recoverable from the file image.
* Resource names exist but their consumers are not statically reachable.
* The literal `8189fec` string is absent from the EXE file image.
* No game / renderer island was confirmed; only network (STUN) and gate code.

---

## 11. Required standalone Bootstrap state

Strict separation, as demanded by the round:

```text
REQUIRED_CONFIRMED
  (nothing is proven *complete*; only individual facts are CONFIRMED)
  - the EXE reads 0x0849413B at 3 sites and writes it at 1 site

REQUIRED_CANDIDATE
  - 0x0849413B   : set to 1 when the -q token is present
  - 0x00CA827C   : dispatch slot that supplies the argv/command-line handle
  - 0x0196928C / 0x01969290 : argv count / argv pointer array
  - a filesystem root providing main\ and settings_*.zip.iw4
  - the Base.dll ordinal-1 external boundary being satisfied

UNKNOWN
  - 0x0849B500 and 0x0849B501 write sources
  - how the IIPS result reaches EXE state
  - which island activation sequence the engine expects
  - thread-start address
```

No "possibly needed" item was placed in `REQUIRED_CONFIRMED`.

---

## 12. Next step

Stop condition E is met. Blind EXE scanning should not continue.

Recommended next phase:

```text
Standalone Bootstrap external-boundary replacement
```

Concretely, the next round should define the **compatibility layer** that
satisfies `Base.dll` ordinal 1 and provides the argv/command-line handle to the
`0x00CA827C` slot, then verify whether the EXE's own raw-backed islands
(`0x0037F580`, `0x002212C0`, …) can be reached from there. That work must
remain at the boundary and must not reverse the Tencent components.

---

## 13. Artifact inventory

```text
CODOL_STANDALONE_CORE_007_EXTERNAL_CONTRACT.md   (this report)
exe_core007_global_contract.csv
exe_core007_global_sites.csv
exe_core007_indirect_slots.csv
exe_core007_dispatch_slots.csv
exe_core007_function_tables.csv
exe_core007_argv_dataflow.csv
exe_core007_runtime_states.csv
exe_core007_resource_refs.csv
exe_core007_iips_boundary.csv
exe_core007_runtime_islands.csv
exe_core007_activation_candidates.csv
exe_core007_evidence_matrix.csv
exe_core007_prior_round_corrections.csv
```

Reproducible tooling:

```text
core007_contract_recovery.py
```

## Quality validation

```text
sample SHA-256 match                 = CONFIRMED
global operand scan                  = alignment-validated
0x0849413B sites                     = 4 (3 read, 1 write)
0x0849B500 static occurrences        = 0
0x08189FEC static occurrences        = 0
argv provider call sites             = 1 (0x00561133)
confirmed function pointers          = 0
alignment-valid indirect slots       = 88 of 1193
.tvm0 bytes decoded                  = 0
```

## Final status

```text
ENTRY_NATIVE_CONTINUATION      = NOT_FOUND           (inherited, CORE-006)
STARTUP_STATE_GLOBALS          = 0x0849413B (CONFIRMED), 0x0849B501 (CONFIRMED read)
                            0x0849B500 (NO STATIC ACCESS), 0x08189FEC (NO STATIC ACCESS)
ARGV_DATAFLOW                  = DATAFLOW_CONFIRMED (call site + gate write)
                             DATAFLOW_UNRESOLVED (provider target, gates write source)
DISPATCH_MECHANISM             = CONFIRMED (slot array) / targets VIRTUAL_ONLY
CONFIRMED_FUNCTION_POINTERS    = 0
RUNTIME_ISLANDS                = 5 identified, activation UNKNOWN
IIPS_RESULT_CONSUMPTION        = UNKNOWN / BOUNDARY
STANDALONE_REQUIRED_STATE      = REQUIRED_CONFIRMED: none complete
                             REQUIRED_CANDIDATE: 0x0849413B, 0x00CA827C, argv globals
STOP_CONDITION                 = E
NEXT                           = external-boundary compatibility layer
```
