# Second Round Freeze

Freeze ID: `CODOL-SECOND-ROUND-20261021`

Date: 2026-10-21 (Asia/Shanghai)

## Frozen facts

- CoD4x 21.2 identity: `cod4x18_dedrun`, AGPL-3.0, 1,093 paths, 1,085 unique hashes, 110 asm files.
- IW4X identity: HEAD `675c4f1e0355c0f07e9d2679429f3d90d9ed175d`; 604 source paths; 16 uninitialized submodules.
- IW4X rawfiles identity: 7,439 paths, 1,033,997,734 B; asset/runtime tree, not server source.
- CoD4x is frozen as a standalone server tree with a substantial recovered-asm core.
- IW4X is frozen as an injected host extension whose full server behavior requires an exact host binary.
- WebAdmin implementation, startup, and reachability are distinct CoD4x facts.
- `DISABLE_SESSION` is frozen as the default IW4X configuration.
- No cross-project lineage, protocol, asset-format or reuse conclusion is admitted in this freeze.

## Evidence status

| Dimension | CoD4x | IW4X |
|---|---|---|
| Static inventory | complete for current tree | complete for current tree + rawfiles |
| Domain discovery | A-S populated | A-S populated |
| Readable source chain | substantial | substantial for extension layer |
| Recovered-assembly semantics | partial | not applicable in extension source |
| Host ABI resolution | not applicable | unresolved |
| Build | unverified | unverified |
| Run | unverified | unverified |
| Real packet/asset evidence | absent | absent |
| Full semantic audit | not complete | not complete |

## Integrity boundary

- This freeze captures evidence identity and the current degree of proof.
- It does not freeze a deployable server, a client-compatible protocol, or an implementation to copy.
- It does not modify protected launch assets or the CODOL first-round evidence.
- No game client, battle server, Auth, Lobby, IIPS, CoD4x process or IW4X process was started during round two.

## Entry condition for round three

Round three may compare architecture, algorithms, protocol structure, asset layout and lineage only after:

1. This second-round freeze is accepted.
2. Missing reverse-engineering material supplied by the user is registered against the missing-artifact IDs.
3. Every cross-project claim is labeled as direct code derivation, structural isomorphism, algorithm family, wire compatibility, asset compatibility, or merely name/value similarity.

Until then, `CROSS_VALIDATION.md` remains blocked.
