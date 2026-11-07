# HUD capture at the native snapshot boundary

`SV_BuildClientSnapshot` now resolves and captures the CoDOL HUD when it copies
the native player state. The live `ps->hud` still identifies the client HUD copy
and its separately stored font transition metadata at this point. The detached
`frame->ps.hud` no longer has that identity.

`codol_sv_frame.c` owns one current HUD capture per recipient. Its sequence must
match the requested outgoing snapshot exactly. The stored HUD contains resolved
CoDOL text/material indices and font transition state, not references back to
native HUD objects. Updating a string mapping or reusing a game HUD object
cannot change an existing capture. The existing serializer's history must own
the final quantized sent frame; this store is not a replacement for ACK history.

The frame builder invalidates the previous capture before early returns. A
failed replacement also invalidates it, preventing accidental reuse. Buffers
are reused between captures and freed when client snapshot history resets.
`CODOL_CopyClientSnapshotHud` copies only a matching valid capture and preserves
its caller's output on failure.

`CODOL_OverlayClientSnapshotPlayer` now retrieves that sequence-matched capture
and composes the native frame through `CODOL_OverlayEnginePlayerWithHud`. The
captured HUD replaces live HUD resolution in this path; `frame->ps.hud` is never
used to recover metadata. The original live-state composition API still resolves
its native HUD normally. Both paths stage player fields, arrays, HUD and event
clock and commit all four outputs together. Missing capture, invalid packed HUD
counts or any player conversion failure leave all four outputs unchanged.

The caller must still supply this exact frame's native player state, a complete
semantic seed and explicit weapon/ammo/event bindings. The bridge does not fill
unresolved fields with zero or invent asset indices. The HUD's numeric wire
representability remains validated by the existing serializer.

Capture occurs before `SV_BeginClientSnapshot` writes reliable commands, so HUD
name publication can precede the snapshot that refers to those names. Asset
publication itself remains governed by the existing configstring code.

The dedicated ASan/UBSan fixture covers client isolation, ownership, exact
sequence matching, overwrite, failed replacement, invalidation and teardown.
The asset-name integration fixture exercises the production HUD resolver and
captures index 1 before remapping the live text/material to index 2, then checks
that the earlier capture still contains index 1.

The native integration fixture also composes a copied player state after
deliberately invalidating its embedded native HUD and removing its live resolver.
The captured HUD remains unchanged; wrong sequences and late ammo-conversion
failure preserve all outputs. This checks the capture-to-composition path, not
connected-client rendering.

The existing snapshot/history integration case now uses this capture path too:
sequence 100 carries the resolved HUD into prepared serialization and owned
history; sequence 101 captures an empty HUD, attempts a rejected send, retries
and commits. The sequence-100 base remains unchanged, and the accepted
sequence-101 base has cleared HUD arrays. Detached native HUD contents and live
resolver pointers are deliberately unusable in both compositions.

Validation on 2026-09-08: Windows MinGW build and forced Linux
`make -B -j6 all test-codol` pass, including send rejection/rollback and
asset-name integration. The dedicated capture fixture passes ASan/UBSan.
The subsequent capture-to-player composition and serialized-history checks also
pass the full Linux suite and Windows server build on the same date.

The live writer still emits its retained IW3 body and does not yet consume this
capture. Its CoDOL replacement must require a matching capture, compose the
remaining player/entity/client/actor state and prepare it through the existing
ACK/history bridge. A missing capture must reject that CoDOL frame. No live
client match entry is established by these capture tests.
