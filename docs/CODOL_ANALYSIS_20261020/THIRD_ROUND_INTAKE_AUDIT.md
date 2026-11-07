# Third Round Intake Audit

Date: 2026-10-21 (Asia/Shanghai)

Input bundle: `run_codol_001/runs/R3_EVIDENCE_20261021_122246`

Source report: `run_codol_001/runs/R3_EVIDENCE_20261021_122246/THIRD_ROUND_INPUT_EVIDENCE.md`

Summary file under audit: `run_codol_001/runs/R3_EVIDENCE_20261021_122246/HASHES_SUMMARY.json`

Status: `ACCEPTED AS PARTIAL EVIDENCE`

This audit verifies the delivered bundle and maps it to `THIRD_ROUND_PREREQUISITES.md`. It does not promote partial artifacts into protocol compatibility.

## 1. Bundle integrity

| Check | Result |
|---|---|
| Run files | 60 |
| Actual total bytes | 74,090,386 |
| SHA-256 entries | 58 |
| Rehash result | 58 OK / 0 mismatch / 0 missing |
| Files excluded from hash list | `hashes.sha256`, `RESULT_MANIFEST.json` |
| Protected files before/after | 11 checked, unchanged |
| Claims about processes | 0 client, 0 battle server, 0 Auth/Lobby/IIPS |
| Declared status | `PARTIAL`, `p0_closed=false` |
| Bundle self-consistency | PASS after treating the 2 B summary variance as an accounting conflict |
| Bundle verdict | accepted, no integrity failure |

### 1.1 Byte-accounting discrepancy

`HASHES_SUMMARY.json` reports 74,090,384 B. The actual tree is 74,090,386 B, a 2 B difference. The 58 hashed files total 74,082,611 B; adding `hashes.sha256` and `RESULT_MANIFEST.json` gives the actual total. The summary byte field is therefore an accounting discrepancy; it is not a missing file or a hash failure. The exact cause of the 2 B difference is not established.

This does not invalidate the hash list or any evidence. It is recorded as an accounting discrepancy in the summary field, not repaired inside the delivered run.

### 1.2 Non-substantive artifact

The bundle contains a compiled Python cache file:

`snapshot124/scripts/__pycache__/demo_parse_snapshot_only.cpython-311.pyc`

It is hashed and harmless, but it is not evidence. Future bundles should exclude `__pycache__` before hashing to avoid environment-specific noise.

## 2. P0 mapping

| Prerequisite | Bundle result | Intake decision |
|---|---|---|
| R3-A01 full runtime image | `CAPTURED_PARTIAL` / `BLOCKED_BY_SCOPE`; 10,899,456 of 241,537,024 B, 4.51254% | P0 remains open. Full image or page list still required. |
| R3-A02 in-match receive edge | recv and reader allocation instructions captured; payload copy and final consumer absent | P0 remains open. |
| R3-A03 real battle capture | no pcapng; reported `NOT_PRESENT_IN_SCOPE` | P0 remains open. |
| R3-A04 gamestate/configstrings | only a 259 B historical sample; no full frame | P0 remains open. |
| R3-A05 snapshot | 124 B reader KAT passes; writer is 158 B; no live ACK | P0 remains open; conflict is now reproducible. |
| R3-A06 state/field consumers | still no target consumer map | P0 remains open. |
| R3-A07 world assets | layer-1 `IWffs100` only; no CLIPMAP_MP/MAP_ENTS/ComWorld | P0 remains open. |
| R3-A08 Pmove/trace | only four deterministic horizontal vectors; no target constants or brush trace | P0 remains open. |
| R3-A09 game rules | no playable rule state machine | P0 remains open. |
| R3-A10 2697 package | original package still invisible | P0 remains open. |
| R3-A11 booking | no same-build endpoint trace | P0 remains open. |

P0 closure count: 0 of 11. P0 state: A01, A02, A04, A07 and A08 have partial progress; A05 is a reproducible conflict; A03, A06, A09, A10 and A11 have no closed evidence. P1 state: B01/B02/B04/B05 are partial or conflicting; B03/B06 are partial; B07 is captured. B01 remains a reader/writer conflict, not a solved writer.

## 3. Evidence that genuinely improved

### 3.1 Image scope is now precisely bounded

- image size: 10,899,456 B
- module SizeOfImage: 241,537,024 B
- coverage: 4.51254%
- usable window: RVA `0x0..0xA65000`
- required RVA `0xCA8400..0xCA8700` is outside EOF
- VA interpretation does not supply the missing IAT range either

This is a useful positive/negative boundary. It prevents more work from treating the current image as a complete module dump.

### 3.2 Pointer-slot census

The bundle records 995 slot mappings, with 183 in the requested VA range. Target bytes mostly lie in an unavailable high address region. This improves the slot map but does not make the host API semantics provable.

### 3.3 124-byte snapshot conflict is now concrete

- historical 124 B vector: reader consumes 984 bits / 42 fields
- current writer with the same semantics: 158 B / 1256 bits
- common prefix: 17 B
- current reader self-test: fails at unknown index 48

Decision: retain the reader KAT as historical evidence; reject truncation or padding to 124 B; writer/reader compatibility remains blocked.

### 3.4 Receive ledger is instruction-level but not end-to-end

Captured:

- recv wrapper and actual call
- one-byte receive
- length field
- reader allocation
- reader threshold
- first-byte opcode comparisons `0x81/0x83/0x84/0x85`

Missing:

- payload copy into the reader allocation
- whether P5 is the final in-match path
- opcode semantics
- same-frame consumer state change

The bundle explicitly avoids promoting these bytes to protocol opcodes.

### 3.5 FF layer-1 is confirmed

`mp_firingrange.ff` decrypted to a layer-1 file with header `IWffs100`, 31,332,208 B. Layer-2 parsing and all required asset families remain unresolved.

### 3.6 Pmove vectors are only a regression fixture

Four horizontal integration cases are deterministic. They contain no target gravity, player bounds, brush trace, step, friction or ground snap. Their verdict `playability_claim: NONE` is correct.

### 3.7 2697/3.19 matrix is a gap record

The five topics are gamestate, configstrings, snapshot, reliable command and EOF. Nine of 25 cells are explicitly `UNKNOWN`; every row remains `BLOCKED`. The matrix is useful as a checklist, not a compatibility proof.

## 4. Conflicts introduced or confirmed

| ID | Conflict | Handling |
|---|---|---|
| R3I-01 | Summary bytes 74,090,384 vs actual 74,090,386; formula is derived as 58 listed files + the two unlisted control files | Keep both values; hash list remains authoritative |
| R3I-02 | 124 B reader passes while writer emits 158 B | Preserve as a protocol conflict; do not pad/truncate |
| R3I-03 | Current snapshot reader self-test fails at index 48 | Writer/reader round-trip is not trusted |
| R3I-04 | P5 receive chain is not proven to be in-match final path | Keep as candidate; do not register opcode |
| R3I-05 | Pointer slots expose targets in unavailable high memory | Slot map is partial, not callable host map |
| R3I-06 | Layer-1 FF header does not imply layer-2 asset extraction | Keep asset families blocked |
| R3I-07 | Pmove vectors are internal only | Do not use as target physics evidence |
| R3I-08 | 2697 original package absent | Do not call matrix a paired cross-version proof |

## 5. What can be done now

Allowed:

- architectural comparison with explicit `PARTIAL` evidence;
- static continuation on the four Pmove fixture cases;
- receive-ledger refinement inside the present image;
- layer-2 FF research from the present layer-1 file;
- 2697/3.19 checklist reconciliation;
- inventory and hash-based deduplication.

Not allowed:

- claiming target protocol closure;
- claiming client compatibility;
- claiming playable combat;
- claiming the 124 B vector is the current server's correct output;
- claiming FF assets were extracted;
- treating P5 as the final in-match dispatcher without consumer evidence.

## 6. Exact next acquisition

1. Full loaded 3.19 image or page dump covering the missing IAT/read path and late code, with module base and SizeOfImage.
2. Same-PID battle capture with raw packets, reassembled stream, gamestate/configstrings, at least two snapshots and ACKs.
3. Same-session consumer trace: buffer, length, opcode, parser, state delta.
4. Layer-2 extraction of CLIPMAP_MP, MAP_ENTS, ComWorld and physics/XModel collision.
5. Target player bounds, Pmove constants and real ground trace.
6. Original 2697 package, then same-build booking/endpoint sample.

## 7. Intake verdict

The bundle is internally honest, hash-verifiable and useful for narrowing gaps. It does not close P0, does not prove third-round protocol compatibility, and does not alter the round-two freeze.

Recommended status for the overall project:

`ROUND 3 PRECONDITIONS: PARTIAL; ARCHITECTURAL REVIEW MAY CONTINUE; WIRE/PLAYABILITY BLOCKED.`

Do not label this bundle as a third-round completion. It is an accepted evidence supplement.

## 8. Verified evidence anchors

These are the concrete artifacts that a later reviewer should open first:

| Topic | Artifact | What it establishes |
|---|---|---|
| bundle identity | `capture_manifest.json` | run id, offline boundary, no processes |
| bundle integrity | `hashes.sha256` | 58-file hash coverage |
| summary/result | `HASHES_SUMMARY.json`, `RESULT_MANIFEST.json` | PARTIAL, p0_closed false, blocked list |
| protected baseline | `baseline/protected_compare.json` | 11 named files unchanged |
| image window | `image/image_coverage_v2.json` | 4.51254% coverage and address convention |
| pointer slots | `image/image_receive_va.json` | 995 mappings; 183 in requested VA range |
| receive chain | `receive_b0/receive_b0_ledger.json` | 11 instruction records and blocked payload edge |
| snapshot KAT | `snapshot124/verify_124_result.json` | 124 B reader pass, 158 B writer conflict |
| reader failure | `snapshot124/current_reader_selftest.log` | unknown index 48 |
| FF layer 1 | `fastfile/layer1_analysis.json` | `IWffs100`, layer 2 blocked |
| Pmove fixtures | `pmove/pmove_vectors.json` | four horizontal vectors, no playability claim |
| 2697/3.19 matrix | `matrix/2697_319_matrix.json` | five blocked topics, nine UNKNOWN cells |

These artifacts are accepted as inputs. None is a substitute for the missing full image, paired capture or layer-2 asset export.

## 9. What the 124-byte conflict does not decide

The 124 B reader pass does not establish that the historical byte string is the correct current CODOL snapshot. It establishes only that the snapshot-only reader can consume that vector under the historical semantics.

The 158 B writer result likewise does not establish that the current writer is wrong; it proves the writer and the historical reader are not on the same schema.

The correct next experiment is not to force a length. It is to pair:

- one real target snapshot message from the client's receive path;
- the fields the client actually consumes;
- the server's live player/entity state at that frame;
- the acknowledgement and next baseline.

Only that pairing can decide whether 124, 141 or 158 B is incidental to the input or a stable framing rule.

## 10. Deliverable quality for future rounds

Good:

- all work confined to a run-specific directory;
- manifests identify the evidence, not just the report;
- protected files hashed before and after;
- negative conclusions carry scope statements;
- conflicts are retained rather than silently patched;
- no client or service process was started.

Improve next time:

- make `files`, `bytes` and `hash_lines` arithmetic self-consistent;
- exclude `__pycache__`, temporary probes and generated caches from the evidence tree;
- include a machine-readable `prerequisite_status.json` keyed by R3-A01..A11;
- include a `sources_used.json` map from each artifact to its source file/SHA and analysis script;
- include a `reproduce.ps1` or `reproduce.py` with pinned interpreter and no implicit network access;
- run the hash verifier after the result manifest is finalized and record its output.

## 11. Cross-check against the second-round freeze

This intake does not alter `SECOND_ROUND_FREEZE.md`, `SECOND_ROUND_FREEZE_HASHES.json`, or any CoD4x/IW4X source/asset input.

It supplies CODOL-side prerequisites only. CoD4x and IW4X remain independently frozen as:

- CoD4x: standalone server tree with recovered-asm core, build/run unverified.
- IW4X: injected extension requiring an exact MW2 host, host/build unverified.

No lineage, wire-compatibility or asset-format conclusion is introduced by this intake.
