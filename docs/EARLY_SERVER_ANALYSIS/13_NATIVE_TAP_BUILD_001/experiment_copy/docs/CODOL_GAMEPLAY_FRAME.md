# Native gameplay frame producer

The native send loop now calls `CODOL_BuildGameplayFrame` for a current active
client snapshot. `SV_BuildClientSnapshot` records eligibility and outgoing
sequence only after copying the live entity/client spans. The cached/archive
branch leaves eligibility clear. `SV_BeginClientSnapshot` builds the CoDOL frame
after `SV_SetServerStaticHeader` has published those spans and asset/weapon maps
have been refreshed, before reliable commands and the snapshot body are written.

The producer uses the zero baseline documented by alpha0022's
`spawn_player.build_spawn_player_fields`, then applies the existing native player
overlays, resolved ammo/event inputs, and sequence-matched HUD. It supplies
ordinary weapon selection from the current native weapon when there is no
alternate mode. Native client records supply team, models, attachments and
vehicle identity; CoDOL progression metadata currently defaults to zero because
this gameplay implementation does not own it.

Current entity support is players, missiles, base-variant weapon items, general entities and script movers
using unbrushed models. Existing converters own trajectories, events, player
animation/weapon fields and model selectors. The producer rejects other types,
brush models, unresolved assets and alternate-mode weapon definitions. Item
selectors use the dedicated [weapon namespace adapter](CODOL_ITEM_SNAPSHOTS.md).
The producer does not invent vehicle state or silently remove unsupported visible entities.
Failure leaves the recipient frame invalid, so the existing send recovery path
handles it instead of sending an incomplete world.

Predictable-player and entity event clocks are server-owned, separate from ACK
history, and reset on entity-slot reuse and map reset. Full-frame composition
still stages both clock sets and commits only after every section succeeds.

This is an initial live producer, not complete state parity. Remaining work
includes the rejected entity/weapon modes, historical metadata for archived
frames, CoDOL progression/perk state, first-raise history, actor/animation-command
production and other player fields currently left at their baseline values.
The full gametype compile and authenticated client match-entry test remain open.

The production collector fixture now invokes this gameplay producer with a
native snapshot, real entity/client rings and captured HUD. It verifies owned
frame creation, baseline metadata, generation clocks, rejection of unsupported
vehicle/item-variant states and alternate weapons, and slot-reuse resets. Its native weapon/ammo
services are controlled; their real registry implementation is tested separately.
No connected-client result is inferred from this fixture.

Validation on 2026-09-08: Linux build and full suite passed in
`/tmp/sh1x-gameplay-frame-linux.log`, followed by the forced Windows build in
`/tmp/sh1x-gameplay-frame-win32.log` (sequential exit zero). The focused collector
fixture then also serialized its generated gameplay frame, including entity and
client records, through `CODOL_WriteSnapshot` under ASan/UBSan and passed.
Compiler output is in `/tmp/sh1x-gameframe-sanitizer.log`. This final fixture
extension changes tests only; production code matches the successful builds.
