# CODOL_STANDALONE_CORE_008
# codoMP_client_shipRetail.exe - External Boundary Contract Validation

## 0. Scope, method, prohibitions

```text
SAMPLE   = COD OL\codoMP_client_shipRetail.exe
SHA-256  = 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
ImageBase= 0x00400000
Entry RVA= 0x0E5DC690
SAMPLE_MATCH_CONFIRMED
```

This round analysed **only** `codoMP_client_shipRetail.exe`, only as a static
file image. No code was modified and no compatibility layer was written.

```text
NO PATCH / NO HOOK / NO DLL MODIFICATION / NO EXE MODIFICATION
Base.dll internals               = NOT ENTERED (ordinal-1 is EXTERNAL_BOUNDARY)
Tencent launcher / TCLS          = NOT RESEARCHED
Sandboxie / Procmon / debugger   = NOT USED
.tvm0                            = NOT decoded
```

Validation method: absolute-memory-operand scan with **two independent
validators** per site - a local-context alignment test and a semantic
control-flow test (the instruction must be followed by a coherent
`jcc`/`call`/`ret`/`mov`/`test` continuation). This is stricter than
CORE-007's prologue-only sweep, which could not see inside the obfuscated
section-0 stream.

---

## 1. Final answers (the eight required questions)

```text
1. EXE -> Base ordinal-1 known input contract
   = call dword ptr [0x0E9DC665] with NO push arguments, NO register setup,
     NO stack arguments prepared by the EXE.  Argument list / convention
     = UNKNOWN.  The EXE passes context only implicitly (the process context
     that Windows already established).

2. ordinal-1 confirmed return contract
   = NOT_CONFIRMED.  The instruction after the call is zero padding; no
     instruction consumes EAX.  Observable return use = NONE.

3. 0x00CA827C to argv provider relationship
   = CANDIDATE (file-provable, same function region)
       0x00561119  mov dword ptr [0x0196928C], eax   ; argv_count
       0x0056111E  mov dword ptr [0x01969290], esi   ; argv_array
       0x00561133  call dword ptr [0x00CA827C]       ; provider
     The historical 0x852724 argv-builder address is VIRTUAL_ONLY and is NOT
     file-linked:  ARGV_PROVIDER_TO_852724 = UNKNOWN.

4. 0x0849413B dataflow (only provable flow)
   = a startup gate byte set to 1 by an argv token comparison
       WRITE 0x00239C68  mov byte ptr [0x0849413B], 1
       READ  0x0016FF08  cmp byte ptr [0x0849413B], 0
       READ  0x0017FF46  cmp byte ptr [0x0849413B], bl
       READ  0x0028E1A4  cmp byte ptr [0x0849413B], al
     CONFIRMED (semantic + alignment validated).

5. 0x0849B500 / 0x0849B501 / 0x08189FEC evidence levels
       0x0849B500  = NOT_FOUND   (0 references anywhere in the file image)
       0x0849B501  = CONFIRMED read / NOT_FOUND write
       0x08189FEC  = NOT_FOUND   (0 references anywhere in the file image)

6. Of the five runtime islands, which states are provably required for
   Standalone startup
   = NONE can be proven REQUIRED.  Only bootstrap_gate has a confirmed
     writer for its state; the rest have no static activation evidence.

7. Standalone Bootstrap current minimal contract
   REQUIRED_CONFIRMED : ImageBase load, PE Entry executes, IAT slot 0x0E5DC665
                        bound, ordinal-1 boundary satisfied, 0x0849413B
                        writable
   REQUIRED_CANDIDATE : 0x00CA827C bound, argv globals 0x0196928C/0x01969290,
                        runtime dispatch pointer table populated, gate bytes
                        for -qa/-src=tgp
   UNKNOWN            : ordinal-1 convention/return, gate writers,
                        IIPS consumer, island activation

8. Is a next-round dynamic experiment required
   = NO_DYNAMIC_EXPERIMENT_REQUIRED for the EXE-internal contract.
     (Only the ordinal-1 input/output boundary remains unresolved, which is
      by definition outside the EXE file image.)
```

**Stop condition B is reached:**

```text
EXTERNAL_BOUNDARY_CONTRACT_UNRESOLVED
```

The only remaining gap is the ordinal-1 input/output contract, which cannot be
resolved from the EXE static image by construction.

---

## 2. Task 1 - ordinal-1 contract (EXE side)

### Input side

```text
Entry RVA                : 0x0E5DC690
Entry bytes              : FF 15 65 C6 9D 0E
Instruction              : call dword ptr [0x0E9DC665]
Encoding length          : 6
explicit push arguments  : 0
stack adjustment         : NONE
register setup           : NONE
implicit global state    : NONE OBSERVED before the call
call kind                : indirect through the IAT slot
calling convention       : UNKNOWN
argument count           : UNKNOWN
argument source          : UNKNOWN
```

The EXE performs **no** preparation of any kind before transferring control to
ordinal 1. There is no `push`, no `mov reg`, no stack frame setup. Whatever
context ordinal 1 consumes must therefore come from:

```text
- the Windows process context (PEB, command line block, environment)
- the EXE image contents
- Base.dll own state
```

The first two are EXE-side and Windows-side facts; the third is a boundary and
was not inspected.

### Output side

```text
return site               : 0x0E5DC696
return site mapping       : RAW_BACKED but zero padding
observable return use     : NONE
side effect after return  : UNKNOWN
exception / termination   : UNKNOWN
```

Because the byte after the call is `0x00` and the following 2410 bytes are all
zero, no return contract can be observed inside the EXE.

```text
ORDINAL1_INPUT_CONTRACT  = CONFIRMED (empty / no EXE-provided arguments)
ORDINAL1_OUTPUT_CONTRACT = UNKNOWN
```

---

## 3. Task 2 - IAT slot 0x0E5DC665

```text
RVA                      0x0E5DC665
VA                       0x0E9DC665
section                  .tp3 (index 6)
file offset              0x00776665
section flags            0xE0000020 (UNINIT_DATA | EXECUTE | READ | WRITE)
initial file value       0x80000001  = ordinal flag | ordinal 1
owning import descriptor FirstThunk of descriptor 0
DLL name                 codoMP_client_shipRetailBase.dll
```

| Required question | Answer | Evidence class |
|---|---|---|
| section | `.tp3` index 6 | CONFIRMED |
| initial file value | `0x80000001` (ordinal 1) | CONFIRMED |
| loader-time nature | IAT slot; the loader writes the resolved function address here | CONFIRMED (PE semantics) |
| other EXE references | 1 absolute VA dword + 1 RVA dword (the import descriptor) | CONFIRMED |
| base relocation | NO relocation entry references the slot RVA | CONFIRMED |
| second call site | NONE - exactly one `FF 15` site | CONFIRMED |
| sole Entry external call site | YES, but NOT the only slot use | CONFIRMED |

The single `FF 15` site is the Entry itself:

```text
0x0E5DC690  FF 15 65 C6 9D 0E   call dword ptr [0x0E9DC665]
```

The one other reference (`0x0E5DC645`, the `FirstThunk` field of the import
descriptor) is data, not a call site. So the specification warning holds:

```text
"sole Entry call site" == "sole use of the slot in the whole EXE"
```

For this slot the two statements happen to coincide, and this was verified
rather than assumed.

---

## 4. Task 3 - 0x00CA827C contract

```text
slot RVA                 0x008A827C
section                  .tp3 (index 1, RAW_BACKED_DATA)
initial file value       0x00A1517E
target RVA               0x0061517E  ->  VIRTUAL_ONLY
read sites               0x00561133  (call dword ptr [0x00CA827C])
write sites              NONE found
pointer-to-slot sites    0
classification           CANDIDATE_RUNTIME_POINTER
```

### The new file-provable relationship

The argv storage globals are written by **aligned instructions inside the same
code region** as the provider call:

```asm
00961119  A3 8C 92 96 01      mov dword ptr [0x0196928C], eax   ; argv_count
0096111E  89 35 90 92 96 01   mov dword ptr [0x01969290], esi   ; argv_array
00961124  33 C0               xor eax, eax
00961133  FF 15 7C 82 CA 00   call dword ptr [0x00CA827C]       ; provider
```

Both writers are semantically valid (each is followed by a coherent
continuation), and they sit within 0x1A bytes of the provider call site:

```text
ARGV_PROVIDER_TO_CA827C = CANDIDATE
```

They are **not** CONFIRMED because:

* the region contains a decode desync (`jmp 0x96112b` lands in a misaligned
  byte run), so a complete function boundary cannot be established;
* the slot runtime target and the globals are both `VIRTUAL_ONLY`, so the
  data flow cannot be closed inside the file image.

```text
ARGV_PROVIDER_TO_852724 = UNKNOWN
```

The historical `0x852724` argv-builder RVA is `VIRTUAL_ONLY` and nothing in the
file image references it.

---

## 5. Task 4 - argv contract

```text
Stage                   Site          Level               Evidence
----------------------  ------------  ------------------  --------------------
GATE_WRITE_Q            0x00239C68    CONFIRMED           mov byte [0x0849413B],1
GATE_READ_Q             0x0016FF08    CONFIRMED           cmp [0x0849413B],0
GATE_READ_Q             0x0017FF46    CONFIRMED           cmp [0x0849413B],bl
GATE_READ_Q             0x0028E1A4    CONFIRMED           cmp [0x0849413B],al
GATE_READ_SRC_TGP       0x002835BA    CONFIRMED           cmp [0x0849B501],0
GATE_WRITE_-qa          (none)        STATIC_WRITE_NOT_FOUND
GATE_WRITE_-src=tgp     (none)        STATIC_WRITE_NOT_FOUND
ARGV_PROVIDER_CALL      0x00561133    CONFIRMED           call [0x00CA827C]
ARGV_COUNT_WRITE        0x00561119    CANDIDATE           mov [0x0196928C],eax
ARGV_ARRAY_WRITE        0x0056111E    CANDIDATE           mov [0x01969290],esi
HISTORICAL_RUNTIME      -             HISTORICAL_RUNTIME_OBSERVATION
```

### The confirmed -q chain

```asm
00639C51  movsx edx, byte ptr [edi + ecx]
00639C55  movsx esi, byte ptr [ecx]
00639C5A  inc   ecx
00639C5B  dec   eax
00639C5E  je    0x639c83
00639C60  cmp   edx, esi
00639C62  jne   0x639c74
00639C64  test  edx, edx
00639C66  jne   0x639c51
00639C68  mov   byte ptr [0x0849413B], 1
00639C6F  jmp   0x639d42
```

```text
argv token comparison
        |
        v
0x639C68  mov byte [0x0849413B], 1
        |
        v
gate consumers 0x0016FF08 / 0x0017FF46 / 0x0028E1A4
```

This is `STATIC_CONFIRMED`.

### -qa and -src=tgp

```text
STATIC_WRITE = NOT_FOUND   (both)
```

The only static access to `0x0849B501` is a read. `0x0849B500` has no access at
all. The dynamic observations from prior rounds are recorded separately:

```text
HISTORICAL_RUNTIME_OBSERVATION
    -q  -> [0x849413B] = 1
    -qa -> [0x849B500] = 1
    -src=tgp -> [0x849B501] = 1
```

These are **not** merged into `STATIC_CONFIRMED`.

---

## 6. Task 5 - minimal EXE-visible state table

| State | Address | Evidence | Writer | Reader | Purpose | Confidence |
|---|---|---|---|---|---|---|
| q_gate | `0x0849413B` | 4 aligned+semantic sites | `0x00239C68` | `0x0016FF08`;`0x0017FF46`;`0x0028E1A4` | STARTUP_STATE | **CONFIRMED** |
| qa_gate | `0x0849B500` | 0 references | NOT_FOUND | NOT_FOUND | STARTUP_STATE | **NOT_FOUND** |
| src_tgp_gate | `0x0849B501` | 1 aligned+semantic site | NOT_FOUND | `0x002835BA` | STARTUP_STATE | **CONFIRMED read** |
| iips_failure | `0x08189FEC` | 0 references | NOT_FOUND | NOT_FOUND | IIPS_STATE | **NOT_FOUND** |
| argv_count | `0x0196928C` | 2 sites | `0x00561119` | `0x00239C21` | COMMAND_LINE_STATE | **CANDIDATE** |
| argv_array | `0x01969290` | 1 site | `0x0056111E` | NOT_FOUND | COMMAND_LINE_STATE | **CANDIDATE** |

Notes required by the round:

* `0x0849413B` - reaches `CONFIRMED`.
* `0x0849B500` - `NOT_FOUND` in this file image.
* `0x0849B501` - a read relationship exists (`0x002835BA`); its writer is not
  in the file image.
* `0x08189FEC` - `FILE_REFERENCE_COUNT = 0`, so
  `EXE_STATIC_CONSUMER = UNKNOWN`.
* `0x00CA827C` - remains `CANDIDATE`; this round found no stronger evidence.

---

## 7. Task 6 - runtime islands to contract

The island set is **not expanded**; only the five from CORE-007 are evaluated.

| Island | Functions | Required state | State in file | Confirmed writer | Activation verdict |
|---|---|---|---|---|---|
| bootstrap_gate | 0x0037F580, 0x0037FA70 | 0x0849413B, 0x0849B501 | YES | YES (`0x00239C68`) | **ACTIVATION_CANDIDATE** |
| argv_provider | 0x00561133 | 0x00CA827C | YES | NO | **ENTRY_INDEPENDENT** |
| network_stun | 0x002212C0 ... | 0x0849413B, 0x0849B500 | PARTIAL | YES (shared gate) | **ACTIVATION_CANDIDATE** |
| iips_boundary | 0x0037FA70 | 0x08189FEC | PARTIAL (state absent) | NO | **BOUNDARY** |
| scaleform_exports | 0x000364F0 ... | (none) | YES | NO | **ENTRY_INDEPENDENT** |

```text
ACTIVE_CONFIRMED     : none
ACTIVATION_CANDIDATE : bootstrap_gate, network_stun
ENTRY_INDEPENDENT    : argv_provider, scaleform_exports
BOUNDARY             : iips_boundary
UNKNOWN              : the ordering/relation among the above
```

No island can be proven to be *required* for standalone startup, because none
has a static link from Entry.

---

## 8. Task 7 - Standalone minimal contract

### REQUIRED_CONFIRMED

```text
1. process image loaded at ImageBase 0x00400000
       evidence: PE OptionalHeader.ImageBase
2. PE Entry executes: call dword ptr [0x0E9DC665]
       evidence: FF 15 65 C6 9D 0E at RVA 0x0E5DC690
3. IAT slot 0x0E5DC665 is bound before Entry runs
       evidence: FirstThunk of the only import descriptor; value 0x80000001
4. the ordinal-1 EXTERNAL_BOUNDARY is satisfied
       evidence: the only Entry-connected transfer
5. byte 0x0849413B exists as writable process memory
       evidence: section 2 is RW; 1 confirmed write + 3 confirmed reads
```

### REQUIRED_CANDIDATE

```text
1. an implementation is bound at dispatch slot 0x00CA827C
2. argv storage globals 0x0196928C / 0x01969290 exist
       evidence: aligned writers at 0x00561119 / 0x0056111E
3. the runtime dispatch pointer table is populated
       evidence: 229 aligned FF15 targets are VIRTUAL_ONLY
4. writable memory exists for the -qa and -src=tgp gate bytes
       evidence: reads exist; writers are outside the file image
```

### UNKNOWN

```text
1. ordinal-1 calling convention and argument list
2. ordinal-1 return usage / side effects visible to the EXE
3. writer of 0x0849B500
4. writer of 0x0849B501
5. EXE consumer of the IIPS failure state 0x08189FEC
6. activation relationship between the five runtime islands
```

No candidate was silently upgraded. `REQUIRED_CONFIRMED` contains only items
that this round re-verified from the static image.

---

## 9. Task 8 - dynamic experiment decision

```text
NO_DYNAMIC_EXPERIMENT_REQUIRED
```

Rationale: every EXE-internal question that the file image can answer has been
answered. The single remaining unknown - the ordinal-1 input/output contract -
is **defined** as external to the EXE. Observing it would require either
entering Base.dll (prohibited) or observing the boundary, which the round
explicitly defers.

If a future round decides the boundary must be characterised, the *only*
permitted narrow experiment would be:

```text
NARROW DYNAMIC EXPERIMENT
    observe one variable: the register/stack state at the instant of transfer
    from EXE RVA 0x0E5DC690 to the ordinal-1 target
    (i.e. the EXE -> Base ordinal-1 boundary only)
```

Large-scale tracing is not proposed.

---

## 10. Evidence levels

```text
CONFIRMED
  - ImageBase, Entry instruction, IAT slot identity/value, import name
  - exactly one FF15 site for slot 0x0E5DC665
  - no base relocation for the slot
  - 0x0849413B: 1 write + 3 reads (semantic + alignment validated)
  - 0x0849B501: 1 read
  - 0x00561133: single provider call site
  - 0x00561119 / 0x0056111E: aligned mov writes to argv globals

CANDIDATE
  - 0x00CA827C as a runtime pointer slot
  - argv globals 0x0196928C / 0x01969290
  - the provider/argv same-region relationship
  - bootstrap_gate and network_stun activation

UNKNOWN
  - ordinal-1 calling convention, arguments, return use
  - writers of 0x0849B500 / 0x0849B501
  - island activation ordering

BOUNDARY
  - Base.dll ordinal 1 (EXTERNAL_BOUNDARY)
  - iips_boundary island / 0x08189FEC
  - .tvm0

NOT_FOUND
  - static write for -qa / -src=tgp
  - any EXE reference to 0x0849B500 or 0x08189FEC
  - a file-backed function pointer in the dispatch table
```

---

## 11. Negative findings

* The EXE provides no arguments and no register context to ordinal 1.
* No instruction in the EXE consumes ordinal 1 return value.
* `0x0849B500` and `0x08189FEC` have zero references in the file image.
* The `-qa` and `-src=tgp` gate writes are not in the file image.
* No runtime island has a static activation link from Entry.
* The `0x852724` argv builder is VIRTUAL_ONLY and unreferenced by the file.

---

## 12. Artifact inventory

```text
CODOL_STANDALONE_CORE_008_BOUNDARY_CONTRACT.md   (this report)
exe_core008_iat_contract.csv
exe_core008_entry_call_contract.csv
exe_core008_argv_provider_relation.csv
exe_core008_argv_contract.csv
exe_core008_global_state.csv
exe_core008_runtime_islands.csv
exe_core008_boundary_contract.csv
exe_core008_minimal_requirements.csv
exe_core008_evidence_matrix.csv
```

Reproducible tooling:

```text
core008_boundary_contract.py
```

## Quality validation

```text
sample SHA-256 match              = CONFIRMED
Entry bytes re-decoded            = FF 15 65 C6 9D 0E
IAT slot ownership                = descriptor 0 FirstThunk
slot reference count (VA dword)   = 1 (the Entry instruction)
slot FF15 site count              = 1
slot base relocation              = NONE
0x0849413B sites                  = 4 (validated)
0x0849B500 references             = 0
0x08189FEC references             = 0
argv-provider relation            = CANDIDATE (same region)
.tvm0 bytes decoded               = 0
code modified                     = NO
```

## Final status

```text
ORDINAL1_INPUT_CONTRACT        = CONFIRMED (no EXE-provided arguments)
ORDINAL1_OUTPUT_CONTRACT       = UNKNOWN
IAT_SLOT_0E5DC665              = CONFIRMED (unique FF15, no relocation)
CA827C_TO_ARGV_PROVIDER        = CANDIDATE
CA827C_TO_852724               = UNKNOWN
STATE_0849413B                 = CONFIRMED
STATE_0849B500                 = NOT_FOUND
STATE_0849B501                 = CONFIRMED read / NOT_FOUND write
STATE_08189FEC                 = NOT_FOUND
RUNTIME_ISLAND_ACTIVATION      = UNKNOWN (2 activation candidates)
DYNAMIC_EXPERIMENT             = NO_DYNAMIC_EXPERIMENT_REQUIRED
STOP_CONDITION                 = B
FINAL_MARKER                   = EXTERNAL_BOUNDARY_CONTRACT_UNRESOLVED
```
