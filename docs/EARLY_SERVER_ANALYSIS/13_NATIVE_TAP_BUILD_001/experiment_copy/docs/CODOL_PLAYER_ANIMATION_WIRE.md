# Player animation snapshot adapters

The native entity adapter now publishes remote-player legs/torso animation words
to CoDOL entity offsets `0xd8`/`0xdc`. The player-state adapter publishes the same
words to `0xc4`/`0xcc`. Both paths preserve the CoDOL-native 10-bit animation index
and `0x400` restart toggle. Values outside the 11-bit range fail atomically,
including preserving the composition's event generation and other outputs.

Static inspection of the local C1.exe confirms the producer at `0x40d079` and
`0x40d085` copies player offsets `0xc4`/`0xcc` to entity offsets `0xd8`/`0xdc`.
The client consumer at `0x45b84c` and `0x45b858` copies those entity fields to
client animation state `+0x9f4`/`+0x9f8`. The retained native
`BG_PlayerStateToEntityState` likewise copies named legsAnim/torsoAnim fields.
The CoDOL build of `_bg_animation_mp.asm` already uses 1024 animation records
and toggle `0x400`, so these adapters do not apply an IW3 `0x200` mask.
They assume the CoDOL-native animation namespace, not arbitrary upstream IW3 IDs.

The remote adapter runs only for player entities. Actors use their distinct
actor-record animation fields; these adapters do not redirect that path.
Animation timers and remaining pose fields still need their own producers.

The existing native composition fixtures now check indices above 511, highest
index with restart bit, restart changes, zero clearing, client-held quantization,
serialization and rejection preserving the whole output transaction.
Final Windows build passes (`/tmp/sh1x-player-animation-win32-final.log`).
Full Linux `make -B -j6 all test-codol` passes
(`/tmp/sh1x-player-animation-linux-final.log`). No live client was attached.

## Remaining live connection

`SV_WriteSnapshotToClient` still invokes the IW3 player/entity/client delta writers.
`CODOL_PrepareClientSnapshot` and the CoDOL serializer/history bridge exist, but
a complete live CoDOL frame producer remains to be connected. These changes add
required animation fields to the native adapters; they do not prove a live CoDOL
snapshot, full script startup or client match entry. Entity-type-specific state,
player bindings, actor records, animation commands and their lifecycle must be
assembled before replacing the live writer.
