# Native snapshot entity collection

`CODOL_CollectServerEntities` reads a retained engine snapshot's
`first_entity`/`num_entities` span from `svsHeader.snapshotEntities`. It preserves
the engine's selected visibility set and sorted entity order, rather than
scanning all game entities. It rejects expired spans, invalid IDs, duplicates,
undersized destinations and unavailable semantic bindings.

For each exact snapshot record, a resolver supplies a CoDOL type-specific seed,
resolved event parameters and (for players) the native primary weapon ID. The
collector applies the production entity adapters: trajectories, events, player
flags, animations and the mapped current/primary weapon pair. It does not cast
native structures to wire structures, infer event parameter semantics or replace
unresolved entities with empty records. The resolver must supply remaining
type-specific fields and must not mutate native gameplay state.

Temporary owned arrays stage both converted states and event clocks. Output
and clocks commit only after every entity succeeds. Clocks are indexed by native
entity number and belong to its generation, not a recipient's ACK history.
`CODOL_CollectCurrentServerEntities` uses a server-owned clock store. Native
`G_InitGentity` now clears the reused slot through a source-edited call, and
`SV_ClearServer`/quit clear the whole store. Recipient ACK resets do not clear
entity generations. Explicit-clock collection remains available for fixtures
and separately owned snapshots. Current-frame collection must use the current
generation, not replay a historical ring record after its entity slot was reused.
This collection transaction is separate from transport/history acceptance.

The focused fixture uses the actual production ring collector and entity adapters.
It verifies ring wraparound, retained seed metadata, mapped player weapons,
extended animation IDs, event sequence rollover, expired spans, duplicate IDs,
capacity checks and atomic failure on the second entity. The 32-bit
AddressSanitizer/UndefinedBehaviorSanitizer run passes. The fixture is included
in `make test-codol`.
Full Linux `make -j6 all test-codol` and the Windows server build pass
(`/tmp/sh1x-frame-entities-linux.log`, `/tmp/sh1x-frame-entities-win32.log`).

The generation-lifecycle extension additionally tests repeated sampling without
double advancement, independent slot resets, full-store resets and reserved-slot
handling. Its sanitizer fixture passes.
Full Linux `make -B -j6 all test-codol` passes for the lifecycle extension
(`/tmp/sh1x-entity-generation-linux.log`). Windows build log:
`/tmp/sh1x-entity-generation-win32.log`. Isolated Bog probe PID 45340 completed
initialization and quit; both node VM markers are present in
`%TEMP%/sh1x-entity-generation-probe/main/games_mp.log`. No existing client or
lobby was modified. This startup probe exercises native entity initialization,
not live CoDOL snapshot reception or all slot-reuse scenarios.

## Remaining frame work

The collector is an integration building block, not yet called by the live
`SV_WriteSnapshotToClient`. Native gameplay/asset resolvers still need to supply
complete type-specific seeds and event parameters.
Player state, clients, actors and animation commands must be assembled with this
entity span before sending through `CODOL_PrepareClientSnapshot`. The current
live writer still emits IW3 snapshot bodies. No client match entry is established
by these collector tests.
