# Brush-model entity snapshots

The gameplay frame producer now handles native brush-model ET_GENERAL and
ET_SCRIPTMOVER records. It publishes the map's inline-model index at CoDOL
entity+0x98 and SOLID_BMODEL (0xffffff) at entity+0xa8. It does not translate this
selector through CS_MODELS, which is for named models. Position, angles, scale
and supported events continue through the existing entity overlays.

## Client evidence

For the verified C1.exe build, the '*' model-prefix branch at 0x56ace4 parses the
numeric model suffix and writes entity+0x98 at 0x56acf9. At 0x56acff it sets the
server entity's model-kind byte (+0x115) to 4. This is distinct from the '?' arm
at 0x56ad17, which uses model-kind 3.

The entity link routine at 0x5d8806 checks model-kind 4 and writes 0xffffff to
entity+0xa8 at 0x5d881c. The client-side consumer at 0x43ebb0 compares
centity+0x18c with 0xffffff, then loads centity+0x17c at 0x43ebbc and calls the
brush-model lookup at 0xa804f0. With nextState at centity+0xe4, these are exactly
entity+0xa8 and entity+0x98. Client collision helpers at 0x485320 and 0x485374 use
the same marker and selector. The script-mover netfield table includes +0xa8 as
a 24-bit field; it can represent the complete sentinel.

## Native implementation and bounds

`CODOL_OverlayEngineBrushEntity` requires a brush solid marker, a matching
ET_GENERAL/ET_SCRIPTMOVER wire type, a nonzero inline-model selector below the
loaded map's model count, and a selector representable by the 11-bit model
field. It updates a staged copy, preserving output on failure. Model zero is the
world and is not accepted as a moving brush entity.

The live producer selects this adapter from the native entity's `r.bmodel` and
uses `CM_NumInlineModels()` for bounds. The loaded collision adapter preserves
the map's inline-model indexing. Named model entities retain their existing
adapter, including its rejection of brush markers. Unsupported entities still
reject the complete frame; no records are omitted to make serialization pass.

The focused asset/frame test checks the two serialized field values, zero and
out-of-map indices, wire-width limits, type/solid mismatches and atomic failure.
It also builds a brush mover through the native gameplay producer and serializes
the resulting complete snapshot, then verifies an invalid inline-model index
invalidates the frame. The collision model count is a fixture in this test;
live integration is separately exercised by the encrypted movement probe.

## Integration result, 2026-09-08

The full forced Linux build and `test-codol` passed in
`/tmp/sh1x-brush-linux.log`; the forced Windows build passed in
`/tmp/sh1x-brush-win32.log`. The isolated server on UDP 17749, home
`%TEMP%/sh1x-brush-20260908-070206`, completed the encrypted movement probe.
After stats, gamestate, reliable userinfo and 32 IWD checksum claims, the native
log recorded CS_PRIMED to CS_ACTIVE. The probe reassembled and decrypted a
3,082-byte gameplay snapshot, sequence 6, server time 6350. The gamestate's
checksum feed was 366294252. No frame rejection or message overflow appeared in
the log. This is the first successful live native gameplay snapshot in this
probe; its header is recognized, but its full payload has not yet been decoded
by an independent client-side parser or accepted by real C1.

Only the owned probe server PID 74284 was stopped after executable/home checks.
C1 and the Python lobby remained running and responsive. The fixture's callbacks
are minimal, so this does not validate vendor scripts, walking, combat or a match.

## Independent payload decoding

The subsequent UDP 17750 run at `%TEMP%/sh1x-snapshot-decode-20260908-070808`
completed the same native flow and produced sequence 4 at server time 6600.
`tools/codol_snapshot_decode.py` parsed its complete 3,078-byte snapshot section
(3,082 bytes including the reliable ACK) using alpha0022's independent player,
HUD, actor, entity and client readers. It found 140 type-6 entities, one client
(slot 0), zero actors, and all 35 brush models in inline-model order. Entity 72
decoded to model 1 with solid 0xffffff. The reader reached the exact EOF, with
no unconsumed trailing bytes or out-of-bounds reads.

The strict checker rejects delta baselines, nonempty animation commands and
reserved sections it cannot decode. This is structural and selected-field
validation, not a comparison of every reconstructed field with native state.
Thirteen truncated or malformed variants were rejected. The captured synthetic
payload and a repeatable check are in `tests/fixtures/codol_snapshot/` and
`tests/test_codol_snapshot_decode.py`. No native source changed in this verification
step, so the previously tested binary was reused. Real C1 acceptance, delta
snapshots, vendor scripts and gameplay remain unverified. Only owned probe PID
11672 was stopped; C1 and the Python lobby stayed responsive.
