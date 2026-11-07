# Native player animation-script loader status

Latest (2026-09-08): native movement and condition parsing now pass
`idlelaststand` and `akimbo`; the Windows Bog probe next stops at unknown perk
value `meleehalberd` in `mp/playeranim.script:2533` in the condition-only build.
The subsequent command-storage build also passes `stunned` and the former
eight-command limit at line 3216. The empty-delta fix also clears the rejection
of `pb_prone_death_quickdeath`. The expanded record-table build clears the
animation-name table crash. Native model DB integration now passes
`me_electricbox4`, and native trigger installation clears `?0`. The newest
probe passes `com_cellphone_on` after native brush physics conversion, then
previously failed at `G_Spawn: no free entities`. Native path-node storage now
clears that failure and completes isolated Bog initialization. See
`CODOL_PATH_NODES.md`, `CODOL_PHYSICS_BRUSH.md`, `CODOL_MODEL_DATABASE.md`
and `CODOL_TRIGGER_MODELS.md`.
The isolated test uses `developer 1` so its GSC assertions are retained, but
both node assertion groups now execute successfully. Match entry remains unverified.

The isolated Windows mp_bog_sh probe reaches game initialization after native
cloud FX conversion fixes collision assembly. Its earlier failure was:

```
BG_IndexForString: unknown token 'idlelaststand'
(mp/playeranim.script, line 37)
```

The input here is the shipped animation script, not GSC. Adding a GSC builtin
cannot resolve this failure.

The upstream `animMoveTypesStr` in `src/asmsource/_bg_animation_mp.asm` contains
43 movement entries and does not include idlelaststand. Its parser uses the
table's returned index directly to address a 516-byte animation-script slot.
The canned movement array starts at +0x116b0, immediately after 43 slots
starting at +0xc004. The documented layout in `src/bg_public.h` describes the
two `[1][43]` arrays; the actual server reserves a fixed 0x9a9d0-byte script
data block with later state at fixed offsets.

Appending names without extending storage and updating its consumers would
overlap subsequent arrays. Mapping last-stand movement to idle would also lose
the requested state semantics. Native storage, parser and animation selection
must be adapted together. Existing gameplay paths use IW3 indices and need
explicit mappings wherever CoDOL's indices differ.

The broader GSC surface remains a separate requirement. The normal reference
GSC startup currently fails on PhysicsLaunchClient before reaching this later
animation stage. Neither path has demonstrated a playable match.

## Measured tables and movement support

`tools/codol_playeranim_catalog.py` checks the C1 SHA256 and extracts its actual
pointer/hash token tables into `CODOL_PLAYERANIM_TABLES.json`: one state, 55
movements, 24 events, and 18 conditions. It compares names with the retained
IW3 tables. C1's first 43 movements and first 21 events preserve the existing
indices. Conditions differ: CoDOL omits the IW3 `underhand` entry and adds nine
new names, so its condition IDs cannot be copied directly into native state.

Generated `src/codol_animation_moves.inc` adds movements 43..54: eight jump
dive directions, idlelaststand, crawllaststand, crawllaststandbk, and dtp_move.
`src/codol_animation_tables.c` provides separate normal/canned storage for the
12 new movements while preserving the original 43 slots at their native ABI
offsets. The assembly source's normal/canned parser writes and runtime
`BG_AnimScriptAnimation` lookup use the same checked accessor. Both parsing
passes reset the extension storage, and script shutdown releases its owner.
The existing 64-bit movement mask accommodates these 55 values.

This supplies native script storage and selection access for the new movement
IDs. It does not yet implement all gameplay transitions that select last-stand
or dive animations, extend the 512-entry native animation index table, or fix
the remaining condition/event differences.

Validation so far: focused 32-bit ASan/UBSan tests prove original ABI offsets,
unique normal/canned slots, no writes into adjacent old tables, rejected invalid
indices/owners and reset. The non-CoDOL assembly `.text` and `.data` bytes compare
identically with upstream. The Windows build and real shipped-script probe
pass the old line-37 failure and reach the new line-139 condition failure.

Full Linux `make -B -j6 all test-codol` also passes. The diagnostic Windows
process exited after shutdown; the existing client and lobby were untouched.
The catalog additionally captures each C1 condition's storage kind and static
value table at `0xcd8bc0`; playeranimtype values are marked runtime-filled.

## Native condition extensions

Generated `src/codol_animation_conditions.inc` adds the nine new condition
names, their scalar/bitset descriptors and measured static value tables.
Native indices 0..9 remain unchanged, including IW3's `underhand`; the new
names occupy 10..18. The catalog records this mapping explicitly.

Parser define tables now cover all 19 native indices. A script item still
holds at most ten simultaneous conditions; its parser rejects overflow before
writing the next item field. New condition state lives separately from the
fixed native client layout. Native setters and both animation/event selection
paths use the same scalar or 64-bit bitset evaluator.

The new slots track whether a gameplay producer has supplied a value. An
unknown value raises a diagnostic if evaluated. The gameplay producers for
these slots are still missing; parsing `akimbo` does not establish dual-wield
animation behavior. Existing condition value tables also require review:
the observed next blocker is C1's extra `meleehalberd` perk value.

The focused 32-bit ASan/UBSan fixture passes scalar equality, low/high bitset
matching, unknown-state rejection, client/index bounds, unchanged legacy ABI
offsets, and reset. The Windows build passes. Its isolated shipped Bog probe
advances from line 139 to line 2533 and exits normally after shutdown; no
vehicle-node VM assertion or live animation selection has executed yet.
Probe log: `%TEMP%/sh1x-animconditions-vm-probe/main/qconsole.log`.
Non-CoDOL assembly text/data remains byte-identical to the upstream version.
Full Linux `make -B -j6 all test-codol` also passes for the condition changes
(`/tmp/sh1x-animconditions-linux-regression.log`).

## Perk value and event support

The native perk table now recognizes `meleehalberd` at index 3. IW3's
`laststand` and `grenadedeath` remain at 1 and 2; C1 has no `laststand` token
and uses index 2 for `meleehalberd`. Preserving native indices matters because
`player_die` explicitly supplies perk value 2 after firing the death grenade.
The halberd gameplay producer is not implemented yet.

Generated `src/codol_animation_events.inc` adds C1 events 21..23: `stunned`,
`dtp_takeoff`, and `dtp_land`. The catalog generator verifies that the first
21 C1 event names preserve IW3 indices before emitting this extension. The
native parser and `BG_AnimScriptEvent` use the same checked slot accessor.
Original slots remain at +0x16f60 with stride 0x204; the three extra slots
are separate owned storage, reset each parsing pass and at script shutdown.
Gameplay still needs to produce the new events at the appropriate transitions.

Windows build and the focused 32-bit ASan/UBSan fixture pass. The fixture
checks all legacy offsets, extension separation from both movement arrays,
invalid event/owner rejection and reset. Non-CoDOL assembly text/data compares
byte-identically with upstream. Real shipped Bog probes advance first to
`stunned` at line 3009, then to:

```
BG_ParseCommands: exceeded maximum number of animations (8)
(mp/playeranim.script, line 3216)
```

The native item contains only eight commands. Raising the parser limit alone
would overwrite adjacent fields/items; command storage and its consumers need
adaptation. This remains an animation-script loader failure before the planned
vehicle-node VM assertions. The probe exited normally after shutdown; C1 and
the Python lobby remain running and untouched. Logs are in
`%TEMP%/sh1x-animperk-vm-probe` and `%TEMP%/sh1x-animevents-vm-probe`.
Full Linux `make -B -j6 all test-codol` passes for the perk/event changes
(`/tmp/sh1x-animevents-linux-regression.log`).

## Variable-length native command lists

`CODOL_AppendAnimCommand` now grows a separate command list for each native
script item. Each command retains the existing 16-byte ABI, and the item keeps
its original command count at +0x7c. Item identity is checked against the
2048-slot native item array at +0x199b4 with stride 0x100. Appending does not
overwrite the eight inline command slots or the next item. Allocation growth
checks arithmetic limits, clears new commands and preserves previous entries.

`BG_ParseCommands`, both animation/event command selectors, and the post-load
animation scan use this storage. Reset frees all lists before each parsing
pass and on shutdown. Parser pointers may move on append; no command pointers
are retained across append operations by these consumers. Gameplay behavior
still depends on the separate movement/event/condition producers described above.

The 32-bit ASan/UBSan fixture passes 129-command growth, data preservation,
zeroed new records, native-array canaries, invalid item/count rejection and
reset. Windows build passes; non-CoDOL text/data still matches upstream bytes.
The real Bog probe now reaches animation asset loading and reports:

```
CoDOL rejected animation pb_prone_death_quickdeath: byte29 0, tracks 0/0/0, frames 30
```

The converter's specific failed validation has not yet been isolated. This
does not prove both animation parser passes or gameplay selection completed.
Vehicle-node VM assertions still have not executed, and match entry is
unverified. Probe log: `%TEMP%/sh1x-animcommands-vm-probe/main/qconsole.log`.
The probe exited after shutdown without touching the running client/lobby.
Full Linux `make -B -j6 all test-codol` passes for these command-storage
changes (`/tmp/sh1x-animcommands-linux-regression.log`).

## Empty delta containers and next table failure

The detail probe confirms `pb_prone_death_quickdeath` has delta reference
0xffffffff, no translation/quat2/quat4 tracks, 30 frames, 122 bones and one
notify. The converter incorrectly required every present delta container to
contain a track. It now preserves an empty native container; all existing
individual-track and unsupported-quat4 checks remain.

The retained `XAnim_CalcDeltaForTime` explicitly handles null rotation and
translation pointers. A 32-bit ASan/UBSan fixture executes that actual assembly
at five sample times and verifies raw identity rotation (0,32767) and zero
translation for the converted empty container. The Windows build passes.

The subsequent Bog probe no longer reports the rejected asset. It instead
terminates with Windows exception 0xc0000005 at module offset 0xf2307, mapped
in that build to `BG_AnimationIndexForString_130`, `cmp edi,[ebx+0x4c]`.
Windows Application event 1000 identifies probe PID 65964 and the server path;
report ID b29be7db-0bd3-4b5d-bc6b-7c4d6664055f. The probe is no longer running.

Source inspection shows `BG_LoadAnim` writes the tree size to +0xc000 and
fills 0x60-byte records starting at the script-data base without enforcing
the 512-record boundary. Record 512 begins at +0xc000, overlapping that count
and later script tables. This is a concrete overflow path for larger trees
and the next adaptation target; no crash dump/register values were available
to establish the exact overwritten count in this run. All animation record
consumers and CoDOL's wider animation index/toggle encoding need review.

Logs: `%TEMP%/sh1x-xanim-detail-probe/main/qconsole.log` and
`%TEMP%/sh1x-emptydelta-vm-probe/main/qconsole.log`. The latter exited by access
violation, not clean shutdown. Client/lobby were untouched. Match entry and
the planned vehicle-node VM assertions remain unverified.
Linux `all test-codol` passes after correcting the older fixture that expected
empty containers to fail. That fixture now verifies successful empty-container
conversion and still checks atomic rejection of malformed track metadata.
Logs: `/tmp/sh1x-emptydelta-linux-regression.log` (old expectation failure),
`/tmp/sh1x-emptydelta-linux-regression-rerun.log` (pass).

## Expanded animation record table

CoDOL now owns 1024 native 0x60-byte animation records and a separate count.
`CODOL_BeginAnimationRecords` validates the tree size before clearing and
initializing the table. The fixed native script/client data retains its ABI
offsets. Both parser passes share the record table; script shutdown clears it.
The loader, name lookup, command flag writes, command duration queries,
post-load scan, stance/ADS queries, player animation and lerp-frame consumers
use the new storage under `CODOL_SERVER`.

Animation index stripping and toggle generation in this module now use 0x400
instead of 0x200, allowing indices 512..1023. Animation flags that happen to
use bit 0x200 are unchanged. The weapon-animation and movement-flag bitmasks
in other modules are separate fields and have not been blindly replaced.
This does not yet establish end-to-end snapshot/client animation parity.

The focused 32-bit ASan/UBSan fixture checks all 1024 record slots, old-layout
canaries, count bounds, preservation between parser passes, new-tree clearing
and shutdown. Non-CoDOL assembly text/data remains byte-identical to upstream.
Windows build passes. The shipped Bog probe passes the prior animation-name
scan crash and reaches model loading:

```
Could not load xmodel "me_electricbox4".
Could not load default asset 'void' for asset type 'xmodel'.
```

Log: `%TEMP%/sh1x-animrecords-vm-probe/main/qconsole.log`. Probe PID 62608
exited after normal game shutdown. The planned vehicle-node VM assertions
still have no success marker; gameplay animation transitions and match entry
remain unverified. Client/lobby were untouched.
Full Linux `make -B -j6 all test-codol` passes for the expanded record table
(`/tmp/sh1x-animrecords-linux-regression.log`).
