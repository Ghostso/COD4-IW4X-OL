# CODOL STANDALONE CORE-006
# Entry-connected Native Bootstrap Recovery

## 0. Scope and prohibitions honoured

```text
SAMPLE   = COD OL\codoMP_client_shipRetail.exe
SHA-256  = 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
PE       = PE32 / I386
ImageBase= 0x00400000
Entry RVA= 0x0E5DC690
Entry VA = 0x0E9DC690
SAMPLE_MATCH_CONFIRMED
```

Only `codoMP_client_shipRetail.exe` was analysed. All other modules
(`Base.dll`, `TenProxy.dll`, TCLS, WeGame, IIPS) appear only as named
external boundaries. No `.tvm0` semantics were guessed, no EXE/DLL was
modified, no patch/hook/debugger was used, and no runtime emulation was
performed. Tools used: static PE parsing (`ManualPE`), RVA→file-offset
mapping, Capstone 5.0.7 x86-32 disassembly, direct CALL/JMP extraction,
indirect-slot analysis, pointer-table scanning, TLS import parsing.

This round did **not** re-run EXE-CORE-001…005; their conclusions were used
as input only.

---

## 1. Executive Conclusion

```text
1. Entry -> EXE native continuation
   = NOT_FOUND

2. Entry -> historical bootstrap chain
   = NOT_CONNECTED

3. EXE indirect initialization mechanism
   = CONFIRMED

4. EXE thread-start mechanism
   = UNKNOWN

5. Entry 后可验证的真正下一节点
   = IAT slot RVA 0x0E5DC665 (external boundary, Base.dll ordinal 1)

6. 是否已经找到 Standalone Bootstrap 的 EXE 内入口
   = NO
```

**Decisive machine-level evidence.** The PE Entry is exactly six bytes:

```asm
0x0E5DC690  FF 15 65 C6 9D 0E   call dword ptr [0x0E9DC665]
0x0E5DC696  00 00 00 00 ...     zero padding
```

The byte immediately following the Entry instruction is `0x00`, and the
remaining **2410 bytes (0x96A)** to the end of the section's raw data are all
zero. The section's virtual size extends further (0x0E5D7000 + 0x82000), but
no raw bytes exist there. There is therefore **no native instruction reachable
from Entry by fall-through**, and the only recovered transfer is the indirect
call through the IAT slot.

This satisfies **stop condition D** of the round specification: after
`Entry -> Base.dll ordinal_1 -> external boundary`, no recoverable EXE-native
continuation exists in this sample. Per the specification, the next round
should pivot to *Standalone Bootstrap external-boundary replacement* rather
than further scanning of the Tencent launcher chain.

The key distinction required by the specification is preserved:
**"没有找到" (NOT_FOUND) and "证明不存在" (proven absent) are not the same
conclusion.** The evidence proves absence *of a file-backed native
continuation in this static image*. It does not prove that no runtime path
exists, because a large part of the image is not file-backed (Section 8).

---

## 2. Evidence Matrix

| Question | Answer | Confidence | Basis |
|---|---|---|---|
| Entry instruction | `call dword ptr [0x0E9DC665]` | CONFIRMED | Section-table RVA decode |
| Entry length | 6 bytes | CONFIRMED | Capstone + raw bytes |
| Bytes after Entry | 2410 zero bytes to end of raw | CONFIRMED | Raw file inspection |
| Entry import | 1 import, `Base.dll` ordinal 1 | CONFIRMED | Import descriptor parse |
| IAT slot RVA | `0x0E5DC665` | CONFIRMED | FirstThunk of descriptor 0 |
| Entry→native edge | none | CONFIRMED (in file image) | Recursive-descent CFG |
| Historical chain from Entry | none | NOT_CONNECTED | No CALL/JMP/pointer evidence |
| Thread creation call sites | none found | UNKNOWN | No API symbol; no call site |
| Exported functions | 22, all section-0 | CONFIRMED | Export directory parse |
| TLS callbacks | empty | CONFIRMED | TLS directory parse |

---

## 3. Entry Analysis

```text
RVA              : 0x0E5DC690
File offset      : 0x00776690
Section          : .tp3 (index 6)
Section VA       : 0x0E5D7000
Section char     : 0xE0000020  (UNINIT_DATA | EXECUTE | READ | WRITE)
Instruction      : FF 15 65 C6 9D 0E  =  call dword ptr [0x0E9DC665]
Instruction size : 6
Fall-through     : 0x0E5DC696 -> zero padding (RAW_BACKED_NON_CODE)
```

The Entry is a single indirect call through an import thunk and nothing else.
The stub section is writable+executable (`0xE0000020`), which is characteristic
of a loader/packer tail rather than ordinary `.text`.

### Import table (complete)

```text
Import directory RVA : 0x0E5DC635
Descriptor 0         : codoMP_client_shipRetailBase.dll
  OriginalFirstThunk : 0x0E5DC65D = 0x80000001  (ordinal flag | ordinal 1)
  FirstThunk (IAT)   : 0x0E5DC665
  Name RVA           : 0x0E5DC66D
Descriptor 1         : NULL terminator
```

The DLL name string in the file is the literal byte run
`codoMP_client_shipRetailBase.dll`. The name RVA points one byte after the
end of the sibling string `codoMP_client_shipRetail`, i.e. the launcher's
executable base name is concatenated with `Base.dll`. **The EXE has exactly
one import: `Base.dll` ordinal 1.**

This is why Entry cannot reach any native bootstrap inside the EXE: the only
outgoing edge is into `Base.dll`, whose internals are out of scope.

### Entry neighbourhood (raw inspection)

```text
0x0E5DC635  import descriptor (20 bytes)
0x0E5DC649  import name string "codoMP_client_shipRetailBase.dll"
0x0E5DC66D  (name RVA target / thunk target byte)
0x0E5DC690  Entry: FF 15 65 C6 9D 0E
0x0E5DC696  00 00 ... (2410 zero bytes to end of raw)
```

The bytes *before* Entry are the import descriptor and the packed data tail;
the bytes *after* Entry are zero. There is no second instruction.

---

## 4. Indirect Call Analysis

`Entry`'s only transfer is an absolute-memory indirect call:

```asm
call dword ptr [0x0E9DC665]
```

The operand is a direct absolute VA (not a register), so the slot is fully
resolved:

```text
slot RVA        = 0x0E5DC665
slot section    = .tp3 (index 6), RAW_BACKED_DATA
slot raw value  = 0x80000001  (pre-snap: ordinal import thunk encoding)
role            = IAT slot for Base.dll ordinal 1
classification  = EXTERNAL_BOUNDARY
```

No other indirect call, indirect jump, or `mov reg,[table+idx]; call reg`
sequence is reachable from Entry, because no other block is reachable from
Entry. The single CORE-005 indirect site
(`0x004FD97A`, `lcall 0xbbE8,0x52514600`) is **not** Entry-connected and was
not promoted.

### CORE-005 internal `0xCAxxxx` slot reinvestigation

CORE-005 flagged four EXE-internal slots:

```text
0x00CA812C
0x00CA8190
0x00CA819C
0x00CA84C8
```

These are **not** a native dispatch table. Address `0x00CA812C` is RVA
`0x008A812C` in section 1 (`VA 0x008A8000`, non-executable, `RAW_BACKED_DATA`),
which is a **run of contiguous 4-byte pointers**, e.g.

```text
RVA 0x008A8114 -> 0x00A13726
RVA 0x008A8118 -> 0x00A1373E
RVA 0x008A811C -> 0x00A13758
RVA 0x008A812C -> 0x00A1378C
```

Every target (e.g. `0x00A1378C` → RVA `0x0061378C`) is **VIRTUAL_ONLY**: inside
section 0's virtual size but beyond its raw backing. The pointers therefore
point at addresses that do **not exist in the file image** and are produced at
runtime. Reclassifying them does not change any Entry-reachability conclusion.
They remain entries in a runtime-populated data region, not an Entry-connected
initialization mechanism.

`FF 15` memory-indirect call sites across the raw sections were counted by
target slot. The top slots are the `0x00CAxxxx`/`0x00DB7158` addresses above;
none of the corresponding call instructions is Entry-connected because
Entry reaches only one block.

---

## 5. Function Table Analysis

### 5.1 Pointer-table runs

A DWORD-level scan for runs of ≥8 consecutive values that resolve into an
executable section found **685 candidate runs** (`exe_core006_function_tables.csv`).
These are overwhelmingly **false positives**: section 0 is a dense, packed x86
stream, and unaligned DWORD windows frequently decode to in-image addresses by
chance. Representative first entries are aligned to arbitrary byte offsets and
are not preceded by a table-length or type signature.

Classification per the required vocabulary:

```text
STRONG_FUNCTION_TABLE = 0
CONFIRMED             = 0
CANDIDATE             = 0 (none is used by any Entry-connected call)
UNKNOWN               = 685 (structurally unproven runs)
NOT_FUNCTION_TABLE    = all 4x/2x-alignment noise
```

No genuine initializer/constructor table was confirmed.

### 5.2 Required answers

```text
1. 是否存在真正的初始化函数表？        = NOT_FOUND
2. 是否存在启动阶段 dispatcher？        = UNKNOWN (no Entry-connected dispatcher)
3. 是否有表项最终指向 EXE .text？       = YES at byte level, but NONE is
                                           Entry-connected or code-confirmed
4. 是否能从 Entry 后的外部边界重新进入？ = NO (no recovered edge)
5. 是否存在 constructor/initializer 结构？= NOT_FOUND
```

Single DWORDs that merely "look like code addresses" were **not** treated as
function pointers. No table entry was promoted without a confirmed use/xref.

---

## 6. Thread Seed Analysis

```text
CreateThread         occurrences = 0
_beginthread         occurrences = 0
_beginthreadex       occurrences = 0
NtCreateThreadEx     occurrences = 0
RtlUserThreadStart   occurrences = 0
CreateRemoteThread   occurrences = 0
RtlCreateUserThread  occurrences = 0
```

No thread-creation API name exists anywhere in the raw file, and the EXE
imports nothing from `kernel32` (its only import is `Base.dll` ordinal 1).
No `StartAddress` can therefore be recovered from imports. No recovered
instruction is Entry-connected beyond the single call, so no in-image thread
seed call site exists either.

```text
EXE thread-start mechanism = UNKNOWN
```

`NtCreateThreadEx` was **not** treated as a start function; no start address
was inferred from symbol shape.

---

## 7. Historical Bootstrap Revalidation

For each historical candidate, both strict evidence checks were run
(`exe_core006_historical_revalidation.csv`):

* direct `CALL rel32` / `JMP rel32` to the candidate RVA (byte-level scan), and
* absolute 4-byte pointer equal to the candidate VA or RVA.

| Candidate | Mapping | Direct CALL | Direct JMP | Abs VA ptr | Classification |
|---|---|---|---|---|---|
| `0x0077F580` | VIRTUAL_ONLY | 0 | 0 | 0 | HISTORICAL_ONLY |
| `0x0077F8B3` | VIRTUAL_ONLY | 0 | 0 | 0 | HISTORICAL_ONLY |
| `0x004FD9B0` | RAW_BACKED_EXECUTABLE | 0 | 0 | 0 | NOT_FOUND |
| `0x004FCEE0` | RAW_BACKED_EXECUTABLE | 0 | 0 | 0 | NOT_FOUND |
| `0x00808650` | VIRTUAL_ONLY | 0 | 0 | 0 | HISTORICAL_ONLY |
| `0x007E98F0` | VIRTUAL_ONLY | 0 | 0 | 0 | HISTORICAL_ONLY |
| `0x006212C0` | VIRTUAL_ONLY | 0 | 0 | 0 | HISTORICAL_ONLY |

Five of the seven candidates are **VIRTUAL_ONLY** — they do not exist as file
bytes at all. The two raw-backed candidates (`0x004FD9B0`, `0x004FCEE0`) have
zero incoming direct transfers and zero absolute pointer references.

```text
HISTORICAL_CHAIN_STATUS = NOT_CONNECTED
```

No string similarity, address proximity, "looks like a function", or IW4X
homology was accepted as evidence.

### 7.1 Section-0 calls into the section-6 virtual range

A byte-level scan found 16 `E8/E9` encodings in section 0 whose computed target
falls inside section 6's virtual range. Only two targets are raw-backed
(`0x0E5D8529`, `0x0E5DA712`), and both land **inside the high-entropy packed
blob**. Disassembling them yields implausible/rare instructions
(`salc`, `aam 0x85`, `bound edi, ...`) that are not valid function prologues.
The remaining 14 targets are VIRTUAL_ONLY.

Manual alignment checks of the call sites showed several are themselves
misaligned false positives (for example at `0x0065E731` the byte `0xE8` is an
operand of `adc al, 0xE8`, not an opcode). The single genuinely aligned call
(`0x0044901E -> 0x0E9D8529`) targets packed data, not code. **No genuine
native edge exists from section 0 into the section-6 stub.**

---

## 8. Entry Reachability

Recursive-descent from the PE Entry only (`exe_core006_entry_reachable_graph.csv`):

```text
reachable_blocks           = 1
reachable_functions        = 1
total_edges                = 2
native_continuation_edges  = 0
external_boundary_edges    = 1
tvm0_edges                 = 0
unresolved_indirect_edges  = 0
```

Edges:

```text
0x0E5DC690 @0x0E5DC690  CALL               -> 0x0E5DC665 [INDIRECT_SLOT]      CONFIRMED
0x0E5DC690 @0x0E5DC690  CALL_RETURN_TARGET -> 0x0E5DC696 [RAW_BACKED_NON_CODE] CONFIRMED
```

### Why the whole image is not statically reachable

| Section | Name | VA | Virtual size | Raw size | Virtual-only bytes | Flags |
|---|---|---|---|---|---|---|
| 0 | .tp3 | 0x00001000 | 0x008A689A | 0x00593000 | 0x0031389A | RX |
| 1 | .tp3 | 0x008A8000 | 0x0016DA70 | 0x0016E000 | 0x0000DA70 | R |
| 2 | .tp3 | 0x00A16000 | 0x0DBB1CC0 | 0x00062000 | 0x0DB4FCC0 | RW |
| 3 | .tp3 | 0x0E5C8000 | 0x00000031 | 0x00001000 | 0 | RW |
| 4 | .tp3 | 0x0E5C9000 | 0x00009228 | 0x0000A000 | 0 | R |
| 5 | .tvm0 | 0x0E5D3000 | 0x00004000 | 0x00002000 | 0x00002000 | RX |
| 6 | .tp3 | 0x0E5D7000 | 0x00082000 | 0x00006000 | 0x0007C000 | RWX |

Section 2 alone declares 0x0DB4FCC0 (~229 MB) of virtual space with only
0x62000 raw bytes. Section 0 declares 0x31389A of virtual-only space.
Section 6's Entry is RWX. The image therefore contains a very large
**runtime-produced region that cannot be reconstructed from the file**. Static
recovery is bounded by this: an address in a virtual-only range is
`VIRTUAL_ONLY`, not a code address, and was never decoded.

This is the concrete reason the answer to "does Entry connect to a native
bootstrap" is `NOT_FOUND` (no file-backed path) rather than a false
"proven absent".

---

## 9. Confirmed / Candidate / Unknown / Boundary

```text
CONFIRMED
  - PE Entry = 0x0E5DC690, instruction FF 15 65 C6 9D 0E
  - Entry external boundary = IAT slot 0x0E5DC665 -> Base.dll ordinal 1
  - Entry fall-through = zero padding at 0x0E5DC696 (RAW_BACKED_NON_CODE)
  - Import table = exactly one descriptor (Base.dll)
  - TLS callbacks = empty
  - Exports = 22 entries, all in section 0
  - Section-6 is RWX (0xE0000020)

CANDIDATE
  - 685 unproven DWORD pointer runs (structural, none Entry-connected)

UNKNOWN
  - EXE thread-start mechanism (no symbol, no recovered call site)
  - Any bootstrap that may exist only in virtual-only runtime memory
  - The four CORE-005 0xCAxxxx "slots" as a dispatch mechanism

BOUNDARY
  - Base.dll ordinal 1 call target (DLL internals out of scope)
  - 22 exported functions (reachable only from an external caller)
  - .tvm0 section (no bytes decoded; any landing edge is TVM0_BOUNDARY)

NOT_FOUND
  - Entry-connected EXE native continuation
  - Entry-connected function/initializer/dispatcher table
  - Entry-connected thread start address
  - Constructor/initializer table in the file image
```

---

## 10. Negative Findings

* The Entry instruction is followed by 2410 zero bytes; there is no second
  native instruction on the Entry path.
* The EXE imports exactly one symbol (`Base.dll` ordinal 1) and no Win32 API.
* No thread-creation API string or call site exists in the file image.
* The TLS callback array is empty; TLS is not an init path.
* Five of seven historical bootstrap candidates do not exist as file bytes
  (`VIRTUAL_ONLY`); the other two have no incoming reference.
* The 16 section-0 "calls into section 6" are alignment artefacts or land in
  packed data; none is a genuine native edge.
* The `0xCAxxxx` slots are entries of runtime-populated pointer runs whose
  targets are all virtual-only; they are not an Entry-connected dispatcher.
* No `VIRTUAL_ONLY` address was decoded as code; no `.tvm0` byte was decoded.
* No gameplay/bootstrap semantics were assigned to any address by shape.

---

## 11. Next-Step Recommendation

Stop condition D is satisfied. Do **not** continue scanning the Tencent
launcher chain, `Base.dll`, `TenProxy.dll`, or `.tvm0`.

Recommended next round:

```text
Standalone Bootstrap external-boundary replacement
```

Concretely, the file image shows a clean structural seam that supports a
standalone design **without touching Tencent components**:

1. The EXE's own native code (section 0) is intact and includes a normal CRT
   startup stub and 22 exports. It is simply not reached from the shipped
   Entry.
2. The shipped Entry calls `Base.dll` ordinal 1 — a single, well-defined
   external boundary that a replacement loader could satisfy or bypass.
3. A standalone bootstrap must therefore **supply** the initialization that
   the Tencent shell provided (process args, subsystem init, then entry into
   the EXE's real native code), rather than recover it from the Entry chain.

Recommended evidence needed for the next round:

* A trusted runtime memory image of the loaded EXE, so virtual-only ranges can
  be classified as code or data (still without reverse-engineering Tencent
  internals).
* Identification of the EXE's real native entry among the section-0 CRT code.
* Definition of the `Base.dll` ordinal-1 contract at the *boundary* only
  (arguments and return), which is permitted as external-boundary analysis.

---

## 12. Artifact Inventory

```text
CODOL_STANDALONE_CORE_006_ENTRY_NATIVE_CONNECTION.md   (this report)
exe_core006_entry_edges.csv
exe_core006_indirect_slots.csv
exe_core006_function_tables.csv
exe_core006_thread_seeds.csv
exe_core006_initialization_candidates.csv
exe_core006_connection_matrix.csv
exe_core006_entry_reachability.csv
exe_core006_entry_reachable_graph.csv
exe_core006_historical_revalidation.csv
exe_core006_imports.csv
exe_core006_exports.csv
exe_core006_sections.csv
exe_core006_cross_section_transfers.csv
```

Tooling:

```text
core006_entry_native_connection.py   (Entry/import/export/TLS + Entry-connected CFG)
core006_stage2_analysis.py           (historical revalidation, tables, thread seeds, matrix)
core006_stage3_init_candidates.py    (init candidates, reachability closure, verdicts)
```

## Quality validation

```text
sample SHA-256 match        = CONFIRMED
Entry RVA match             = CONFIRMED
Entry instruction re-decode = CONFIRMED (FF 15 65 C6 9D 0E)
fall-through zero span      = CONFIRMED (2410 bytes)
import descriptors          = 1 + NULL terminator (CONFIRMED)
export entries parsed       = 22 (CONFIRMED)
TLS callback count          = 0 (CONFIRMED)
Entry-connected blocks      = 1 (CONFIRMED)
Entry-connected native edges= 0 (CONFIRMED)
virtual-only addresses used = not decoded (boundary respected)
.tvm0 bytes decoded         = 0 (boundary respected)
```

## Final status

```text
ENTRY_NATIVE_CONTINUATION     = NOT_FOUND
HISTORICAL_CHAIN_STATUS       = NOT_CONNECTED
EXE_INDIRECT_INIT_MECHANISM   = CONFIRMED (single Base.dll ordinal-1 boundary)
EXE_THREAD_START_MECHANISM    = UNKNOWN
ENTRY_NEXT_VERIFIABLE_NODE    = IAT slot 0x0E5DC665 (external boundary)
STANDALONE_EXE_ENTRY_FOUND    = NO
STOP_CONDITION                = D
NEXT_ROUND                    = Standalone Bootstrap external-boundary replacement
```
