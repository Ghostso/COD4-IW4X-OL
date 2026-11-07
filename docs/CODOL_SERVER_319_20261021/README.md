# CODOL 3.19 Battle Server

**Target**: CODOL 3.19.26.22 / Build 1649370
**Status**: Stage 0 Skeleton — architecture, layering, evidence gate operational

## Design Basis

This server is designed from the audit corpus in `CODOL_ANALYSIS_20261020`:
- `SERVER_RECONSTRUCTION_SPEC.md` — module boundaries, data ownership, interface contracts
- `THIRD_ROUND_CAPABILITY_MATRIX.md` — A-S domain status (C/P/X/U)
- `THIRD_ROUND_VERSION_MATRIX.md` — version lineage and reuse rules
- `THIRD_ROUND_EVIDENCE_LEDGER.md` — evidence registry for the gate
- `FIRST_ROUND_MATRIX.md` — first-round capability matrix

## Architecture

```
diagnostics   evidence registry, capture, replay, fixture labels
control       Auth/Lobby/booking contract, endpoint mapping
rules         spawn, weapon, damage, death, score, round
replication   snapshot, baseline, delta, ACK history
movement      usercmd, pmove, ground trace
entity        entity pool, client/player state, lifecycle
world_assets  FF/Zone read-only assets, CLIPMAP_MP, MAP_ENTS
wire_codec    opcode table, bit-byte cursor, fragmentation, reliable commands
session       state machine, challenge, slots, reconnect window
transport     UDP socket, OOB, bdDTLS, NAT
platform      clock, threads, single instance, config, graceful exit
```

### Data Ownership

| Data | Owner | Access |
|------|-------|--------|
| socket / server address | platform / transport | transport exclusive; others receive copies |
| session table | session | explicit session handle |
| receive buffer / fragments | session / wire_codec | read-only cursor + commit |
| immutable assets | world_assets | read-only references |
| world entities | entity | world commands only |
| snapshot history | replication | advance only after ACK |
| control plane session | control | separate from battle session |
| evidence labels | evidence_registry | compile/startup registration |

## Evidence Gate

The wire table is the critical safety mechanism. Every opcode entry must bind to a 3.19 evidence ID:

```c
typedef struct codol_wire_entry {
    uint16_t                opcode;
    const char             *name;
    const char             *version;        // must be "3.19"
    codol_evidence_level_t  evidence_level; // E0 or E1 for ACTIVE
    const char             *evidence_id;    // must exist in registry
    codol_handler_status_t  status;         // ACTIVE / REFERENCE / DISABLED
    int (*handler)(codol_session_t *, const uint8_t *, size_t);
} codol_wire_entry_t;
```

Startup validation rules:
1. `version` must equal `"3.19"` for ACTIVE handlers
2. `evidence_id` must exist in the target evidence registry
3. `evidence_level` must be E0 (target runtime) or E1 (target static) for ACTIVE
4. REFERENCE handlers are rejected in release mode
5. DISABLED entries are skipped entirely
6. NULL handlers are rejected for non-DISABLED entries

## What Is Implemented (Stage 0)

- [x] Platform layer: clock, config, single-instance, logging, graceful shutdown
- [x] Transport layer: UDP socket, non-blocking I/O, poll loop, address handling
- [x] Session layer: state machine (FREE→COOKIE→HANDSHAKE→CONNECTED→PRIMING→ACTIVE), slot allocation, timeout
- [x] Wire codec: bitstream reader (bit/byte/short/long), message header decode/encode
- [x] World/entity: entity pool, player state, spawn, lifecycle
- [x] Movement: pmove constants, friction, acceleration, gravity, jump, integrate
- [x] Replication: snapshot history, frame commit, baseline tracking
- [x] Evidence gate: registry, validation, lookup, release-mode rejection
- [x] Tests: evidence_gate, session, wire_codec (3/3 passing)

## What Is NOT Implemented (P0 Blockers)

These are **evidence-gated placeholders** — they cannot be filled until the corresponding P0 items close:

| P0 ID | What is missing | Where it plugs in |
|-------|----------------|-------------------|
| R3-A01 | Full 3.19 runtime image | session handshake, wire opcode table |
| R3-A02 | Receive → netchan → opcode → parser edge | wire_codec decode path |
| R3-A03 | Real 3.19 battle capture | wire_codec framing, ACK, snapshot boundary |
| R3-A04 | Gamestate/configstring format | replication baseline, configstring table |
| R3-A05 | Snapshot boundaries, baseline, delta | replication build/ack |
| R3-A06 | Entity/player field layout | entity state, player state |
| R3-A07 | CLIPMAP_MP, MAP_ENTS, ComWorld | world_assets, movement trace |
| R3-A08 | Pmove constants | movement constants init |
| R3-A09 | Game rules | rules module |
| R3-A10 | 2697 original package | cross-validation reference |
| R3-A11 | Booking/endpoint delivery | control module |

## Build

```powershell
# Requires MSVC Build Tools (E:\BuildTools)
$env:PATH = "E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;" + $env:PATH
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Debug
```

## Test

```powershell
cd build
ctest -C Debug --output-on-failure
```

## Run

```powershell
.\build\Debug\codol_battle_server.exe --map mp_firingrange --port 28960 --tick 20
```

## Version Rules (from THIRD_ROUND_VERSION_MATRIX.md)

| Version | Role in this project | Prohibited use |
|---------|---------------------|----------------|
| 3.19.26.22 / 1649370 | **Target** — sole arbiter of protocol & behavior | — |
| 2.6.9.7 / 2697 | Family write-side reference | Not 3.19 wire golden |
| 3.3.3.3 ol-mod | Family engineering reference | Not field or asset source |
| 1.1.1.13 | Historical appendix | Not in field tables |
| CoD4x 21.2 | External skeleton/algorithm reference | Not CODOL wire/asset |
| IW4X | External boundary reference | Not wire/struct |

## Evidence Sources

- 3.19 client: `COD OL/codoMP_client_shipRetail.exe` SHA `36997674...b537`
- 3.19 base DLL: `COD OL/codoMP_client_shipRetailBase.dll` SHA `EF75220D...6A20`
- Partial image: `CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin`
- Gamestate sample: `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/_extracted/evidence/firingrange-gamestate.bin`
- First snapshot: `FIRINGRANGE-BRINGUP-VERIFY-20261015/_src_backup/golden_first_snapshot.hex`
- FastFile: `COD OL/main/mp_firingrange.ff` SHA `268EAD12...FAE53`

## References (Architecture Only)

- CoD4x 21.2: server skeleton, socket/OOB/RCON/plugin ABI
- IW4X: host extension boundary, auth envelope, demo sink
- ol-mod 3.3.3.3: module layering, ownership model
- 2697 dedrun: family write-side structure
