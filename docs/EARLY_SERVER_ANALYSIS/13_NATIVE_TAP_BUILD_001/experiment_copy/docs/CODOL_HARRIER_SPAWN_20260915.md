# Harrier spawn shutdown — 2026-09-15

## Established failure

Latest qconsole line18716 reports `type string is not an int` at
maps/mp/killstreaks/_airstrike.gsc:674, in
spawnplane(owner, "script_model", pathStart, friendlyIconName, enemyIconName).
The exception shut down the map. Native process101456 remained alive; this was
a script-argument failure, not evidence of a new native access violation.
Parent preserved the full log at obj/harrier-crash-20260915.log.

Retained GScr_SpawnPlane reads argument3 as integer spawnflags. T5 OpenBLOPS
retains that older contract; this call needs the measured C1 contract instead.

## Exact C1 contract

54C7D1 reads origin argument2. 54C7DF..54C825 reads optional nonundefined string
arguments3/4. 54C825..54C841 reads optional integer spawnflags argument5.
54C841/54C84A resolves those names via54FFB0. This resolver searches15 precached
minimap icon entries, case insensitive, returning slot+1; null/empty returns0.
An absent nonempty name raises `Minimap icon '%s' was not precached`.
It is **not** the material index namespace.

After real entity spawn, 54C8C6 sets type13; 54C8EE sets owner client at state+58;
54C8F1 sets friendly icon+60; 54C8F4 sets enemy icon+5c. There is no older
team|owner*4 packing. Failed spawn frees the entity at54C913 before raising error.

## Source correction, awaiting parent build

`codol_script_minimap.c` now supplies CODOL_Scr_SpawnPlane through a native
source-level replacement in retained GScr_SpawnPlane. It uses the existing
6085..6099 minimap bank, validates owner, reads optional icon strings and flags
at their C1 positions, allocates/calls the real G_Spawn/G_CallSpawnEntity path,
and frees failed spawns. No proxy entity or hook.

Named native LerpEntityStatePlane stores ownerClient/enemyIcon/friendlyIcon in
the existing union. Existing planeStateFields already archives all three words
as anonymous.data[0..2], so delayed frames retain the values without new live
lookups. CODOL_OverlayEnginePlane publishes captured fields at+58/+5c/+60 and
the resolved model at+98, with range and type validation. Native gameframe
dispatch now invokes this overlay for ET_PLANE.

Files: src/asmsource/_g_scr_main_mp.asm, src/entity.h,
src/codol/script/codol_script_minimap.c/.h,
src/codol/snapshot/codol_engine_state.c/.h,
src/codol/snapshot/codol_sv_gameframe.c.

No worker tests, build, launcher, runtime writes or restarts. Parent review and
build pending. This fixes the evidenced spawn contract, not all Harrier behavior.
The log separately warns that vehicle_av8b_harrier_jet_opfor_mp is absent from
mounted zones; model availability and following helicopter lifecycle remain
under investigation. No alternate model or extra zone has been guessed.
