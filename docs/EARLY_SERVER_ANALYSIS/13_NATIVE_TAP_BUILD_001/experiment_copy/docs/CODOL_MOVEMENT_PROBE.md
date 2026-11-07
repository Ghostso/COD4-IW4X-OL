# First encrypted native movement probe

`tools/codol_transport_probe.py --move` extends the stats/gamestate/checksum probe
with a CoDOL `clc_moveNoDelta` body built by alpha0022's independent usercmd test
writer. It uses the published checksum feed, message acknowledgement and reliable
server-command text for the usercmd key, then applies the netchan XOR and native
transport encryption. The command advances time to 100 with otherwise unchanged
input. It is an entry probe, not a test of walking or combat.

After the command, the probe reassembles encrypted outgoing fragments, decodes
the body with the acknowledged `cp` command as its XOR key string, skips reliable
server commands, and looks for CoDOL snapshot opcode 0. Finding that header alone
would not establish that a real C1 accepted the complete snapshot.

## Observed failure, 2026-09-08

The isolated native Windows server on UDP 17747 used home
`%TEMP%/sh1x-move-20260908-064447` and the existing native node VM fixture scripts.
Stats, gamestate, userinfo and the 32-checksum `cp` all succeeded. The next command
reached `SV_UserMove`, and the native log recorded:

`Going from CS_PRIMED to CS_ACTIVE for EncryptedProbe`

No gameplay snapshot was delivered. The server repeatedly reported message
overflow while trying to recover. The same running server reproduced the result
with new synthetic connections; the process remained responsive.

Read-only inspection of the owned server distinguished frame production from
transport failure. Addresses came from the built executable's symbols, adjusted
for its observed image base (0x450000 versus preferred 0x400000); structure offsets
came from a compiled helper using the project headers. `svs.clients` is an inline
array, not a pointer. The live snapshot flag was set, while the CoDOL frame-valid
flag was zero and its owned frame pointer was null. A current native snapshot
(sequence 461) had pm_type 4, client 0, weapon 0, 140 entities and one client.

This establishes that native entry and snapshot capture occurred, but the live
CoDOL frame conversion rejected the captured world state before a frame could be
published. The precise player/entity/client conversion that failed remains to
be isolated; the overflow message does not identify that cause. No records were
silently omitted to make the test pass. The `--move` probe currently fails its
expected-gameplay-snapshot assertion and should remain a regression target.

Only the owned probe server PID 72080 was stopped after executable and command
line checks. C1 and the Python lobby remained running and responsive. This was
not a real C1 connection, a successful gameplay snapshot, or a completed match.

## Frame diagnostics and first rejecting entity

Subsequent builds expose the last synchronous frame-building failure stage and
the failing entity's number/type/conversion stage. Developer output is emitted
when a client's failure reason changes, instead of adding a new message on every
retry. Existing atomic frame and event-clock publication is preserved.

The isolated diagnostic run at
`%TEMP%/sh1x-frame-diagnostic-20260908-065141` passed player/HUD conversion and
failed entity conversion. A second run at
`%TEMP%/sh1x-frame-entity-20260908-065321`, UDP 17748, reported:

`CoDOL frame rejected for client 0: entity conversion (entity 72 type 6, identity or seed)`

Read-only inspection of that owned server's `g_entities[72]` confirmed eType 6
(ET_SCRIPTMOVER), native model index 1, solid 0xffffff (SOLID_BMODEL), and
`r.bmodel=1`. Both the live gameplay seed and `CODOL_OverlayEngineModelEntity`
explicitly reject brush models. The first required missing mapping is therefore
a brush-model mover, not an oversized serialized message. Other unsupported
records may remain after that mapping is implemented; none were silently skipped.

Alpha0022 `g_entity.py:501-512` points to model index at CoDOL es+0x98. Static C1
inspection clarifies the cited address: 0x56ace4 compares the model prefix with
'*', 0x56acf9 stores the parsed unsigned-short model number at es+0x98, and
0x56acff sets entity+0x115 to 4. The reference's cited 0x56ad33 is instead on the
'?' arm (comparison at 0x56ad17), which sets +0x115 to 3. These model-kind values
still need tracing through link/snapshot construction and the client renderer
before extending the native brush-model adapter. Merely writing es+0x98 is not
enough evidence of a complete brush-model wire state.

That trace has subsequently identified entity+0xa8 as the brush-solid sentinel
and confirmed the client consumers. The native adapter now supports this pair;
see [brush-model entity snapshots](CODOL_BRUSH_ENTITIES.md) for the mapping and
subsequent validation.

The diagnostic server PIDs 71344 and 52536 were stopped after executable and
unique-home checks. C1 and the lobby were not modified. The full forced Linux
build and `test-codol` passed in `/tmp/sh1x-frame-diagnostic-linux.log`.
The forced Windows build passed in `/tmp/sh1x-frame-diagnostic-final-win32.log`.
