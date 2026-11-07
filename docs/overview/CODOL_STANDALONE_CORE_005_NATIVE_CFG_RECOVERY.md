# CODOL STANDALONE CORE-005
# Native Function / CFG Recovery

## 1. Sample identity

```text
Sample = COD OL\codoMP_client_shipRetail.exe
SHA-256 = 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
PE = PE32 / I386
ImageBase = 0x00400000
Entry RVA = 0x0E5DC690
Entry VA = 0x0E9DC690
SAMPLE_MATCH_CONFIRMED
```

## 2. PE / section mapping

The standard-library PE parser from CORE-004A was reused. RVA mapping always uses the section table. `RAW_BACKED`, `VIRTUAL_ONLY`, `DATA_UNKNOWN`, and `TVM0_BOUNDARY` are distinct states. No virtual-only RVA was read as file code.

## 3. Decoder validation

Capstone `5.0.7` runs as x86-32 with `detail=True`. Entry re-decodes as:

```asm
0x0E5DC690  FF 15 65 C6 9D 0E  call dword ptr [0x0E9DC665]
```

The slot VA maps to RVA `0x0E5DC665`. It is an `EXTERNAL_CALL_BOUNDARY`, not an EXE function.

## 4. Function recovery method

A bounded recursive-descent decoder starts only from PE Entry, the seven explicitly supplied historical candidates, three retained CORE-003 heuristic hits, and newly decoded direct CALL targets. CALL targets remain candidates; historical seeds do not become confirmed merely because Capstone returns instructions.

```text
FUNCTION_RECOVERY_METHOD = CFG_DERIVED + KNOWN_SEED
FUNCTION_RECOVERY_STATUS = PARTIAL
functions/seeds = 12
status counts = {'BASIC_BLOCK_ONLY': 3, 'UNRESOLVED': 8, 'CONFIRMED_FUNCTION': 1}
```

Function entry categories are kept separate: `PE_ENTRYPOINT`, direct-call target,
historical seed, legacy heuristic hit, and unresolved/virtual-only seed. The three
CORE-003 prologue hits are not promoted to functions merely because they begin with
`push ebp`.

## 5. Basic block recovery

Blocks terminate on CALL, JMP, conditional branch, RET, unresolved indirect transfer, decode failure, zero padding, or budget boundary. Instruction and block starts are globally deduplicated.

```text
basic blocks = 37
block confidence = {'LOW': 36, 'CONFIRMED': 1}
decoded nonempty starts before conflict filtering = 48
excluded instruction-range conflict starts = 11
reported block-range overlaps = 0
```

When two candidate paths produced overlapping instruction ranges, both conflicting starts were excluded from the report rather than selecting an arbitrary alignment.

## 6. Direct CFG

```text
CFG_STATUS = PARTIAL
edges = 60
edge types = {'CALL': 3, 'FALLTHROUGH': 10, 'INDIRECT_UNRESOLVED': 1, 'COND_FALLTHROUGH': 20, 'COND_TAKEN': 20, 'JMP': 2, 'EXTERNAL_BOUNDARY': 2, 'RET': 2}
```

Only decoded direct control transfers create target edges. Ordinary bytes and string proximity do not create edges.

The CORE-005-specific direct-edge table is `exe_core005_direct_edges.csv`. Relative
targets are independently checked from the signed displacement in the instruction
bytes using `instruction_end + displacement`; operand text is not treated as an RVA.

```text
instruction database rows = 282
direct edge rows = 57
decode-failure rows = 11
```

## 7. Call graph

The call graph contains 6 recovered call sites. Direct, indirect, and the Entry external boundary remain separate classifications.

## 8. Indirect calls

Unresolved indirect call/jump sites: 1. No register or memory target was guessed.

Static value propagation did not establish an executable target for the unresolved
site(s). The Entry memory operand is handled separately as the confirmed external
boundary. No `call eax`-style target is upgraded from syntax alone.

## 8A. Function-pointer tables

All 17 CORE-003 table suspects were re-read through PE mapping and DWORD extraction.

```text
table rows = 17
classification counts = {'CANDIDATE': 2, 'NOT_FUNCTION_TABLE': 10, 'STRONG_FUNCTION_TABLE': 1, 'UNKNOWN': 4}
```

The four mode/state addresses in the large virtual range are `VIRTUAL_ONLY` and
remain `UNKNOWN`. Executable-looking DWORDs are not treated as function pointers
without a confirmed use/xref sequence.

## 9. Loops/back-edges

Loop rows: 4. A row is emitted only when the destination dominates the source in a recovered per-function direct block graph. No loop receives a gameplay semantic name.

All loops outside the Entry cluster inherit the trust level of their originating candidate stream and remain `LOOP_CANDIDATE`; structural complexity does not raise a historical seed to confirmed code.

## 10. Entry reachability

Entry reaches 1 native block(s) and 1 recovered function/seed cluster(s) before the confirmed external boundary. The historical `0x0077F580 -> ... -> 0x006212C0` chain is `NOT_ENTRY_CONNECTED`; most addresses in that chain are also `VIRTUAL_ONLY` in the original file.

Separate graph artifacts are emitted:

```text
ALL_NATIVE_FUNCTION_GRAPH = 60 edge rows
ENTRY_REACHABLE_GRAPH = 1 edge rows
```

This separation prevents the small Entry-connected graph from being mistaken for
the size of all recoverable native candidates.

## 10A. Secondary roots and thread entries

Static thread API symbol search produced `1` row(s). No thread start
parameter was recovered, so no `THREAD_ENTRY_CONFIRMED` or secondary root was added.

Bootstrap candidate validation is in `exe_core005_bootstrap_validation.csv`; each
candidate is explicitly labeled `ENTRY_CONNECTED`, `NOT_ENTRY_CONNECTED`, or
`VIRTUAL_ONLY`/unresolved.

## 11. Known native candidate validation

- `0x004FD9B0`: RAW-backed and mechanically decodable, but starts with an implausible sequence including `aaa`; retained as `BASIC_BLOCK_ONLY`/candidate, not a confirmed function.
- `0x004FCEE0`: RAW-backed but direct-entry decode fails; see the special analysis below.
- `0x00808650`, `0x007E98F0`, `0x006212C0`, `0x0077F580`, `0x0077F8B3`: `VIRTUAL_ONLY`; no file code was synthesized.
- CORE-003 hit `0x00001098`: mechanically decodes but contains implausible/rare instructions and remains low-confidence block-only evidence.
- CORE-003 hits `0x000010AF` and `0x000010C6`: overlap the decoded stream rooted at `0x00001098`; they were excluded as independent blocks and remain unresolved.

## 12. 0x004FCEE0 special analysis

```text
section = .tp3
file offset = 0x004FCEE0
direct-entry decode = DIRECT_ENTRY_DECODE_UNRESOLVED
verified direct CALL/JMP xrefs = 0
absolute VA pointer occurrences = 0
recovered CFG edges into target = 0
possible predecessor-alignment paths within 15 bytes = 8
```

The predecessor-alignment paths are alignment possibilities only, not instruction-boundary proof. No recovered block establishes `0x004FCEE0` as a function entry.

## 13. .tvm0 boundaries

No `.tvm0` bytes were decoded. Any recovered edge landing there is labeled `TVM0_BOUNDARY` and traversal stops.

## 14. External boundaries

Entry's `call dword ptr [0x0E9DC665]` is confirmed as the established external boundary. Base.dll and all other DLL internals were not analyzed.

If a future recovered edge reaches `.tvm0`, it must be emitted as `TVM0_BOUNDARY`
and traversal must stop. No `.tvm0` instruction is present in the current graph.

## 15. Negative findings

- No trustworthy EXE-native continuation was recovered after the Entry external call.
- The historical candidate chain is not reachable from Entry through this EXE's recovered direct CFG.
- No `VIRTUAL_ONLY` address was decoded from the file.
- Mechanical decoding alone was not accepted as function proof.
- No Game Init, Main Loop, Renderer, Filesystem, IIPS, or state-machine semantics were assigned.

## 16. Confidence classification

```text
CONFIRMED = PE Entry and its external boundary
STRONG = direct CALL target with recovered structure and RET, when present
CANDIDATE = mechanically recovered direct block/edge with explicit provenance
LOW = decodable stream with implausible instruction mix or weak boundary evidence
UNKNOWN = unresolved indirect, virtual-only, or undecodable target
UNRESOLVED = a required boundary/target could not be established from current evidence
```

## 17. Remaining unknowns

The file contains very large virtual ranges with little raw backing, so static analysis of the original image cannot reconstruct runtime-produced bytes in those regions. A substantial EXE-wide CFG requires a trusted runtime memory image or a stronger native analysis environment, while preserving the no-patch and no-`.tvm0` boundaries.

## Artifact inventory

```text
exe_core005_instructions.csv
exe_core005_direct_edges.csv
exe_core005_basic_blocks.csv
exe_core005_functions.csv
exe_core005_indirect_calls.csv
exe_core005_function_tables.csv
exe_core005_loops.csv
exe_core005_entry_reachability.csv
exe_core005_all_native_graph.csv
exe_core005_entry_reachable_graph.csv
exe_core005_thread_seeds.csv
exe_core005_bootstrap_validation.csv
```

## Quality validation

```text
validation rows = 43
PASS = 42
FAIL = 0
INCONCLUSIVE = 1
sampled CFG edges = 20
sampled function/seed entries = 10
```

## Final status

```text
TOOLCHAIN_STATUS = LEVEL_5
FUNCTION_RECOVERY_STATUS = PARTIAL
CFG_STATUS = PARTIAL
ENTRY_NATIVE_CONTINUATION = EXTERNAL_BOUNDARY_ONLY
HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED
CFG_RECOVERY_USABLE = NO
FULL_CFG = NOT_CLAIMED
```
