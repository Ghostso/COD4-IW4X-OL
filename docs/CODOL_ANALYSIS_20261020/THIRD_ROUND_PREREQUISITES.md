# Third Round Prerequisites

Date: 2026-10-21 (Asia/Shanghai)

Status: evidence-capture worklist before round-three cross-validation. This is a demand list, not an audit-complete declaration.

This list does not treat every historical gap as a round-three blocker. It answers three separate questions:
1. What must be captured before cross-validation starts?
2. What can the audit continue to derive from existing files?
3. What affects eventual playability but does not block an architectural comparison?

## A. P0: minimum evidence set before round three

| ID | Missing / incomplete evidence | Current evidence | Why it blocks round three | Minimal acquisition |
|---|---|---|---|---|
| R3-A01 | Full target runtime mapping of 3.19 client | `CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin`, 10,899,456 B, SHA `17cef6e0...fd045` | Current image covers only about 4.513% of SizeOfImage; IAT slots and runtime globals lie beyond EOF, so static xrefs cannot prove a complete dispatcher. | Dump the loaded image without patching it; record module base, SizeOfImage, SHA and section coverage. Minimum useful range covers `0x0CA8400..0x0CA8700` plus the missing read-path ranges and non-linear/late code regions; record exactly which pages are present. |
| R3-A02 | In-match receive -> netchan -> opcode -> parser edge | P5 loop `0x7A41D0`, recv wrapper `0x873A00`, but payload write point and in-match dispatcher are unproven | All opcode/gamestate/snapshot/reliable claims remain untestable. | Runtime read-only capture of the socket data pointer and the first consumer, or a full image plus pointer-table restoration that closes the same edge. Record caller, buffer, length and opcode read. |
| R3-A03 | Real 3.19 battle capture | No `.pcap/.pcapng` in inventory; one 259 B gamestate sample and one 284 B snapshot hex sample exist | Cannot validate framing, ACK, baseline, message boundaries or ordering against actual 3.19 bytes. | Isolated capture from one client PID: OOB challenge/connect, gamestate, first snapshot, usercmd phase, normal snapshot, reliable command, disconnect. Preserve raw bytes plus packet directions and timestamps. |
| R3-A04 | Complete target gamestate/configstring format | A 259 B sample exists; index/width/termination/table capacity remain unknown | Cannot map client parser to server writer or determine message boundary. | From the same capture and runtime image, extract full gamestate and configstring frames, all opcodes, index ranges and terminator, plus parser instruction evidence. |
| R3-A05 | Complete target snapshot boundaries, baseline and delta semantics | 284 B first snapshot sample; 314/136 tables and type dispatcher found | No reliable frame boundary, entity add/remove, baseline selection, EOF or field-width mapping. | Capture at least two consecutive snapshots and one baseline; dump entity/client/player-state values consumed by client at matching frame numbers. |
| R3-A06 | Target player/client/entity layout and field consumers | Several sizes/fields and parser families recovered; full consumer map is missing | Server cannot produce states that client will consume correctly. | Runtime record of struct sizes/offsets validated at the consumer, with field-by-field writer -> wire -> reader -> state mapping. |
| R3-A07 | Target `CLIPMAP_MP`, `MAP_ENTS`, ComWorld / physics collision data | FF containers are present, including `mp_firingrange.ff` (31,332,485 B, SHA `268EAD12...FAE53`), but no verified extracted structures | World geometry, spawn points, brush traces and authoritative movement cannot be implemented or compared. | Extract these four asset families from the exact matching FF version; record asset type, size, hash and references. |
| R3-A08 | Player collision/shape and Pmove constants | Generic movement physics notes exist; target values and runtime consumption remain open | The known no-floor / wall-clipping failure cannot be resolved from generic physics alone. | Runtime/static capture of player mins/maxs, eye offset, gravity, step size, friction, acceleration, ground trace and actual trace calls. |
| R3-A09 | Target server-side game rules | No playable damage/death/respawn/score/round chain exists | A complete-server comparison cannot distinguish a protocol skeleton from a playable server. | Recover the target client/game event consumers and the 2697 writer paths for spawn, weapon fire, hit/damage, death, respawn, scoring and round transition. |
| R3-A10 | 2697 original package and correspondence to 3.19 | Reports identify `codol_dedrun.exe` SHA `80816711...50ea1` and client paths; original `server2697` directory is not visible | 2697 is currently a derived evidence source, not a reproducible paired reference. | Provide original 2697 package, legal server/client binary pair, PE headers, section hashes and load test. |
| R3-A11 | Booking / external endpoint delivery trace | Control-plane evidence exists for ol-mod/REF kit, but no 3.19 same-build delivery chain | Cross-validation can compare architecture but cannot prove the 3.19 client can be routed to our battle server. | Capture lobby/booking response, chosen battle endpoint, client connect attempt and the exact endpoint field consumed. |

## B. P1: existing artifacts that can still be worked locally

| ID | Work item | Existing input | Expected output |
|---|---|---|---|
| R3-B01 | Repair / compare the 124 B reference snapshot chain | `CODOL_MOVEMENT_PHYSICS_20261004` extracted package under 046; `CodolMotionSnapshot.cs`; 284 B hex sample | Reversible writer/reader, first-frame and subsequent-frame delta rules |
| R3-B02 | Trace the payload write into session object `[esi+0xB0]` | `CODOL-BATTLE-SERVER-RECEIVE-LINK-050`; P5 addresses | Recv buffer -> payload -> reader instruction chain |
| R3-B03 | Restore pointer tables / `.rimp` / `.tvm0` context from current image | 12 `image_best.bin` variants and existing disassembly scripts | Either recovered callbacks/opcode table or address-specific negative evidence |
| R3-B04 | Parse FF container structure without assuming game semantics | exact 3.19 `mp_firingrange*.ff` files | Asset index, compression/layout, candidate CLIPMAP/MAP_ENTS records |
| R3-B05 | Reconcile 2697 write chains against 3.19 parser families | 2697 E1-E6/F1-F6 and 3.19 parser traces | Side-by-side field/order/width matrix with unresolved cells marked UNKNOWN |
| R3-B06 | Establish deterministic trace / Pmove fixtures | 3.19 disassembly plus existing movement physics package | Input -> trace -> final position vectors and wall/floor test corpus |
| R3-B07 | Inventory raw/reverse material by hash and version | 375,294-path inventory and derived evidence | Relevance table; avoid rescanning duplicate material |

## C. P2: second-round gaps that do not block architectural comparison

- CoD4x build toolchain, built `cod4x18_dedrun`, Cod4 IWD/zone, plugin load tests and RCON/WebAdmin E2E: `M2-C4-01..10`.
- IW4X 16 submodules, build/version headers, exact MW2 host, host disassembly, format parser, RCon/HTTP E2E: `M2-IW-01..12`.
- These remain required for executable claims and cross-project replay, but they are not prerequisites for reading source architecture.

## D. Do not capture / do not treat as blocking

- Marketplace, TCLS update UI, pure UI text and cosmetic assets.
- Old 1.1.1.13 labels as if they were 3.19 facts.
- Hash-only duplicates as new evidence.
- A self-test count or a process staying alive as proof of client compatibility.
- Old 2697 writer fields promoted to 3.19 without consumer evidence.


## E. Known assets found in the existing workspace (not missing)

The following are present and should be reused rather than recollected blindly:

| Evidence | Path / hash | Use |
|---|---|---|
| 3.19 executable | `COD OL/codoMP_client_shipRetail.exe`, 7,841,344 B, SHA `36997674...b537` | target identity |
| 3.19 base DLL | `COD OL/codoMP_client_shipRetailBase.dll`, 60,327,992 B, SHA `EF75220D...6A20` | static analysis |
| loaded-image candidate | `CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin`, 10,899,456 B, SHA `17cef6e0...fd045` | current partial static map |
| firingrange fastfiles | `COD OL/main/mp_firingrange.ff`, 31,332,485 B, SHA `268EAD12...FAE53`; `mp_firingrange_load.ff`, 24,885 B | asset extraction input |
| gamestate sample | `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/_extracted/evidence/firingrange-gamestate.bin`, 259 B | limited parser check |
| first-snapshot sample | `FIRINGRANGE-BRINGUP-VERIFY-20261015/_src_backup/golden_first_snapshot.hex`, 284 B | limited KAT check |
| movement evidence package | extracted under 046 from `CODOL_MOVEMENT_PHYSICS_20261004` | Pmove/snapshot reference, not a target-runtime substitute |

These are inputs. Their presence does not discharge the missing full mapping, paired capture, decoded world assets or consumer maps.

## F. Release criteria for starting round three

Architectural/lineage pass may start once R3-A01 and R3-A07 are registered and at least one of R3-A02/R3-A03 is available.

Protocol or playability claims additionally require all of R3-A02..A06 and A08..A09. Endpoint integration additionally requires R3-A11.

The minimum useful capture set is:
1. full loaded 3.19 image or at least the specified missing ranges;
2. one bidirectionally paired 3.19 battle session, including at least two snapshots and acknowledgements;
3. extracted firingrange CLIPMAP_MP, MAP_ENTS and physics/ComWorld;
4. consumer-side field and snapshot evidence;
5. original 2697 package for reproducible comparison.

## G. Current execution boundary

- The requested scope is evidence collection before round three, not a new live game experiment.
- No client, battle server, Auth, Lobby, IIPS, CoD4x or IW4X process is started by this worklist.
- Any later runtime capture must use a fresh isolated run directory and record before/after hashes for protected assets.
- When launching is explicitly authorized, use the frozen one-shot runner or a fresh run-specific copy; one invocation may create only one client.

## H. Proposed capture package contract

Use one dated directory per capture. Every package should contain:

| File | Required contents |
|---|---|
| `capture_manifest.json` | source SHA/version, module base, SizeOfImage, time interval, PID, process command line, capture tool version |
| `sections.json` | every image section: VA, VirtualSize, RawSize, file offset, captured page ranges, missing ranges |
| `packets.pcapng` | raw bidirectional packets without payload rewriting |
| `stream_reassembly.bin` | TCP/UDP reassembly output keyed to packet ids, if transport is segmented |
| `acks.csv` | snapshot/gamestate/message sequence and client acknowledgement values |
| `packet_index.csv` | timestamp, direction, source, destination, length, framing, opcode, netchan sequence, ack, payload offset |
| `gamestate.bin` / `configstrings.bin` | exact bytes plus first/last sequence and decoded index/width table |
| `snapshot_N.bin` | at least two consecutive snapshots plus baseline reference and client acknowledgement |
| `consumer_trace.jsonl` | buffer pointer, length, read count, opcode, parser entry and resulting state delta |
| `objects.json` | target asset hashes: CLIPMAP_MP, MAP_ENTS, ComWorld, physics, XModel collision |
| `hashes.sha256` | hashes of every file in the package |

Do not put secrets, account cookies or unrelated client data into the package. Redact identity values where they are not needed for protocol semantics, but keep lengths and byte positions.

## I. Historical movement package missing members

The movement package itself is present, but 046 records that several cited runtime artifacts were never included. These do not invalidate the reference source, but they prevent promotion of its claims to a 3.19 runtime proof:

| Artifact | Present? | Evidence value | Required replacement |
|---|---|---|---|
| `load-assets-34680/camera-motion.json` | no | 1500-frame camera/input/snapshot correspondence | recapture or original runtime output |
| `gameplay-playerstate.bin` | no | playerstate offset validation | fresh target-player-state dump |
| `predicted.bin` / `pred_trace.txt` | no | per-tick predicted trace | regenerated deterministic trace |
| `battle.log` / `n10*.txt` | no | full launch/probe rounds | preserve full logs in a new run directory |

## J. Evidence completeness versus playability

The prerequisites below are not a promise that a complete authoritative server is implementable from one dump. They establish the minimum evidence needed to decide which layer must be reused, ported, or independently implemented.

| Layer | Evidence needed before implementation claim | Playability impact |
|---|---|---|
| transport | socket ownership, framing, sequence, ACK, fragmentation | can connect / stay connected |
| session | challenge, auth identity, primed/active transition | can enter world |
| world | CLIPMAP_MP, MAP_ENTS, ComWorld, physics, brush trace | can spawn / collide / shoot |
| entity | entity/client/player state layout and field consumers | can replicate state correctly |
| snapshot | baseline, delta, frame budget, reliable ordering | can keep world synchronized |
| game rules | spawn, weapon, hit, damage, death, respawn, score, round | can call it a playable match |

A successful capture that only proves startup or gamestate parsing does not discharge the whole server audit. Keep the evidence levels separate in the round-three report.

## K. Highest-value acquisition order

1. `image_best_full.bin` or a page list that fills the missing read-path and late-code ranges.
2. A single clean 3.19 session capture with raw packets, stream reassembly, first gamestate, at least two snapshots and ACKs.
3. Consumer-side trace from the same session: buffer, opcode, parser, state delta.
4. Extracted firingrange CLIPMAP_MP / MAP_ENTS / ComWorld / physics.
5. Original 2697 package and paired client/server identities.
6. Booking endpoint response and the client-side endpoint consumer.

Do not spend the first acquisition round on marketplace, cosmetic assets, plugin demos or old-version source unless a specific unresolved field requires them.

## L. Required negative / positive evidence ledger

Every round-three prerequisite submission should say one of:

| Result | Meaning |
|---|---|
| `CAPTURED` | artifact exists, hash fixed, byte range present |
| `BOUND` | caller/callee, writer/reader or asset/reference relationship proven |
| `NOT_PRESENT_IN_SCOPE` | exact checked addresses/pages and method recorded |
| `BLOCKED_BY_SCOPE` | artifact range is outside the supplied dump and the next range is named |
| `CONFLICT` | two sources disagree; retain both and do not promote either |

This prevents a missing page, an unresolved pointer table or a hashed duplicate from being mistaken for a proven negative result.

## M. Intake status after R3_EVIDENCE_20261021_122246

See `THIRD_ROUND_INTAKE_AUDIT.md` for full verification.

| Prerequisite | State |
|---|---|
| R3-A01 | PARTIAL; still blocked by image scope |
| R3-A02 | PARTIAL; payload copy and dispatcher still missing |
| R3-A03 | MISSING |
| R3-A04 | PARTIAL only; 259 B sample |
| R3-A05 | CONFLICT; reader KAT vs writer mismatch |
| R3-A06 | MISSING consumer map |
| R3-A07 | PARTIAL; layer 1 only |
| R3-A08 | PARTIAL; horizontal vectors only |
| R3-A09 | MISSING |
| R3-A10 | BLOCKED; original package absent |
| R3-A11 | MISSING |

P0 closure: 0 / 11. Architectural review may continue; wire compatibility and playability remain blocked.

## N2. Diagnostic addendum after 2026-10-21 booking run

Full audit: `DIAGNOSTIC_RUNS_20261021_144241_145654_CLOSURE_AUDIT.md`.

Two diagnostic runs were checked:

- `ONCE_20261021_144241`: dumpcap started before client, same PID 9964 reached Auth/Lobby, 445 TCP/3074 frames were captured, no UDP/28960, no gamestate/snapshot, image OpenProcess failed with error 5 and no full sweep was attempted. Its 414-entry hash list rehashed cleanly.
- `DIRECT_20261021_145654`: booking was later enabled, Lobby produced 20 `mmbook accepted` events, 0 `mmstart`, battle_server PID 15676 listened on UDP/28960 with 16 consecutive zero-receive statistics, and the raw pcap independently contains 66,120 packets, 1,980 TCP/3074 packets and 0 UDP/28960 packets. The chain records client PID 1764 while capture metadata records PID 14736, so this is not a same-PID session.

Neither run changes P0: `0/11`. `booking accepted` is a Lobby control event, not proof of endpoint consumption or battle entry.

### N2.1 cleanup conflict

A read-only check at `2026-10-21T15:09:39.154+08:00` found residual Python processes:

- PID 15676 listening on UDP `0.0.0.0:28960`;
- PID 1624 listening on TCP `127.0.0.2:3074`;
- PID 17536 listening on TCP `127.0.0.1:3074`;
- PID 16472 with no matching listener.

Their start times align with the DIRECT run. Therefore the statement that no Auth/Lobby/Battle process or `3074/28960` endpoint remains was not true at audit time. A fresh run must not start until the user explicitly controls or clears these remnants. No process was stopped by this audit.

## N0. Third-round start boundary

Correction: P0 incompleteness and residual processes are not prerequisites for *starting* third-round analysis. They are prerequisites for promoting its results to protocol compatibility, playability or complete-server conclusions.

| Mode | Allowed now? | Meaning |
|---|---|---|
| Third-round evidence review | yes | Compare available evidence, build matrices, identify contradictions and test hypotheses |
| Third-round architectural reasoning | yes | Use partial captures, static code, historical traces and negative evidence with explicit confidence levels |
| Third-round protocol conclusion | not yet | Requires paired same-PID battle evidence and consumer mapping |
| Third-round playability conclusion | not yet | Requires world assets, movement/collision, game rules and a complete battle chain |
| Starting a new live capture run | operationally separate | Residual 3074/28960 services should be handled first, but offline third-round work may continue without them |

Therefore the round-three status is `STARTED_NON_CONCLUSIVE`, not `BLOCKED_FROM_STARTING`. Evidence quality should be represented as levels: confirmed, partial, conflict, hypothesis, unknown. Negative or incomplete gaps reduce confidence only; they do not stop analysis.

## N. Intake status after COLLECT_319_20261021_132905

Full audit: `COLLECT_319_20261021_132905_INTAKE_AUDIT.md`.

Machine-readable gate: `THIRD_ROUND_BLOCKER_STATUS_20261021.json`; its static verification is `THIRD_ROUND_BLOCKER_STATUS_AUDIT_20261021.md`.

This run was accepted as a negative/partial evidence package only:

| Prerequisite | Run result | State after intake |
|---|---|---|
| R3-A01 | 0 / 58,969 image pages readable; all `ERROR_ACCESS_DENIED` (299) after ACE | still open; `BLOCKED_AFTER_ACE` |
| R3-A02 | no payload -> dispatcher/consumer edge | still open; `NOT_BOUND` |
| R3-A03 | filtered capture has only 3 TCP/3074 frames, one 4 B payload, no UDP/28960 | still open; `NOT_CAPTURED` |
| R3-A04 | zero gamestate/configstring frames | still open |
| R3-A05 | zero consecutive snapshot frames and no ACK history | still open |
| R3-A06 | `consumer_trace.jsonl` is an explicit empty placeholder | still open |
| R3-A07 | `mp_firingrange` block-0 only; layer-2 layout mismatch | still open; `PARTIAL_BLOCK0_ONLY` |
| R3-A08 | no target Pmove/trace evidence | still open |
| R3-A09 | no authority/rule state evidence | still open |
| R3-A10 | no original 2697 package | still open |
| R3-A11 | no booking/endpoint delivery trace | still open |

P0 closure remains **0 / 11**.

Required next-run ordering is stricter than this run:

1. Start `dumpcap` and prove capture is live before invoking the frozen chain.
2. Invoke the original frozen chain once; record the same PID through Auth, Lobby and battle.
3. Enter an actual battle and retain raw bidirectional application traffic, gamestate/configstrings, at least two snapshots and ACKs.
4. Capture the same-PID consumer chain from buffer through parser to state delta.
5. Only then rerun protocol comparison; do not promote the retained 3-frame TCP/3074 placeholder.

The image reader must also demonstrate at least one live readable page before attempting a full page sweep. A 0/N result under error 299 is `BLOCKED`, not `PARTIAL`.

The unfiltered original pcap is intentionally absent because it contained unrelated host traffic and credentials. Therefore no later claim may reconstruct missing Auth/Lobby/battle frames from this package.

