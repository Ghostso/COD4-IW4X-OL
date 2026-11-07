# Tactical insertion lifecycle repair stage

Written and source-reviewed only; no tests, builds, live edits, UI or process changes.

## Existing implementation, not missing wholesale

Active native overlay _class.gsc codol_giveEquipment maps marketplace1209 specialty_tacticalinsertion to givePerk plus flare_mp and selects it in native offhand equipment. _perks registers set/unset callbacks. _perkfunctions already grants flare, tracks safe standing ground, places a script_model beacon, adds owner/enemy use hints, damage listeners and friendly/enemy effects. Native override precedence is explicit in codol_script_source.c; effective vendor IW4 root is alpha0022/vendor/iw4 per launcher confirmed by parent.

Vendor maps/mp/gametypes/_playerlogic.gsc375 predicts setSpawnPoint and514..534 consumes its playerSpawnPos/angles on actual spawn, before class grant. Thus the earlier pickup audit's description of TI as missing lifecycle was too broad. These existing producers/consumers are retained.

## Staged changes

obj/tactical-insertion-stage/maps/mp/perks/_perkfunctions.gsc:

- Cancels previous placement/position monitors before initial grant; clears stale previous-life position.
- Cancels/replaces duplicate team/disconnect cleanup watchers.
- Deletes the native placement missile once the script beacon takes ownership; invalid placement returns exactly one flare and keeps prior valid beacon.
- Stores beacon.owner, supports repeated placement after reclaim without giveStartAmmo, and cleans active beacon on game end or perk removal.
- Owner use goes through shared _pickup::waitForPickup: actual owner/alive/ownership checks, literal hint, exact one-unit refund, no reset of starting ammo. Confirmed pickup sound retained.
- Undefined damage attacker cannot crash team checks or become an invalid method receiver.
- Enemy use explicitly checks owner/team/alive rather than trusting a stale client mask alone.
- deleteTI now dispatches independent level cleanup: clears matching owner reservation, closes use, emits death to child listeners, deletes enemy trigger and model. Existing loop-sound/friendly-dummy/FX cleanup listeners now receive their required death event. Retains the original2.5second spent-stick cosmetic after snapshotting position/angles before device deletion.

obj/tactical-insertion-stage/maps/mp/gametypes/_playerlogic.gsc is copied from the effective vendor IW4 file. It changes only successful beacon spawn consumption: after origin/angles copied, call shared deleteTI then explicitly clear setSpawnPoint. Existing normal spawn choice, care-package validation, timing, loadout and spawn method remain intact.

Parent must merge staged _perkfunctions with concurrent perk edits; do not blanket overwrite newer parent source. Shared _pickup module and native hint/use fixes must be deployed together (already present in active source at audit).

## C1 asset evidence

Read-only zone_assets traversal of installed client_shipRetail/chinese/common_gametype_mp.ff:

- weapon asset9568 type28 embeds flare_mp at blob3068.
- model9575 type4 embeds mil_emergency_flare_mp at360; two bones, shared serialized bone-name pointer0x314cb47f (not inline; names not decoded here).
- model9221 type4 weapon_light_stick_tactical_bombsquad at360 has two inline bone IDs24 tag_origin and742 tag_fire_fx.
- sound9535 chemlight_pu,9537 emt_road_flare_burn,9552 tactical_spawn.
- FX9595 misc/flare_ambient,9596 misc/flare_ambient_green.

No invented asset names or new zones. Actual regular-flare shared bone-name relocation remains unverified; retained script already requests tag_fire_fx. Parent can inspect native resolved skeleton if a tag failure appears. Gameplay/visual success not claimed until actual C1 observation.

## Final parent corrections

TI pickup now uses shipped &"MP_PICKUP_TI" and guards the nested helper return with isDefined before boolean use; also verifies self/owner remain defined before sound/cleanup. Detached deletion restores the original spent-stick cosmetic and its2.5second timer.

Monitor review: setTacticalInsertion first notifies old monitor/position updater, then clears the position; no yield separates these steps. New updater polls current valid grounded origin every0.05seconds and remains alive through pickup because the placement loop no longer returns after first beacon. Pickup never calls setTacticalInsertion, so no duplicate grant/reset. Cleanup watcher now has an explicit generation guard: replacing its nested wait can currently resume its caller in this VM, and the obsolete generation must not delete the new beacon. No retrieveTIPosition function exists in this effective module; actual updater is updateTISpawnPosition.

Localized C1 keys verified by inspecting every installed *localized*.ff type27 asset, not IW5 name assumptions:
- WEAPON_C4_PICKUP base localized_code_post_gfx_mp asset2198.
- WEAPON_CLAYMORE_PICKUP same asset2197.
- WEAPON_BOUNCING_BETTY_PICKUP same asset2199; patch_localized_code_post_gfx_mp asset168 overrides.
- WEAPON_PICKUP_SCRAMBLER same base asset2568.
- MP_PICKUP_TI same base asset987.

IW5 MP_PICKUP_C4/CLAYMORE/BOUNCING_BETTY and MP_PATCH_PICKUP_SCRAMBLER absent. Exact raw localization bytes and provenance saved in obj/tactical-insertion-stage/localized-pickup-evidence.json. Parent owns deployed shared hint changes.
