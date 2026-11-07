# Native fuse-preserving throwback audit and missing producer

Source complete, parent reviewed; worker performed no builds/tests/live interaction. Parent owns deployment. This increment implements vanilla C1 supported throwback, not generic inventory refund for all special grenades.

## Proven missing field and request

C1 41ca10 checks command0x4000, positive ps+3c remaining grenade time, cursor target ps+210 !=7ff, then requires ps+40 throwbackWeaponIndex nonzero at41ca32..37. It queues event51 with precisely that weapon at41ca4d, stores it to offhand328 at41ca6a and starts offhand initialization41c220. Native snapshot overlay previously wrote34/38/3c but never40, while native selection only considered owned equipped slots/rising edges.

Implemented:
- codol_usehint_capture.c captures native throwback weapon together with existing immutable wire hint binding. Validates live missile, captured item identity equality, native index range, remaining timer and original supported frag offhand class1; knife excluded.
- codol_playerstate_ext.h/.c stores throwback_weapon, clears it with hints and whole-client extension reset, archives a changed bit+7bits after use_hint_weapon and before viewhands. Writer/reader order matches; nonzero requires a valid existing captured wire hint binding. This is an internal same-executable archive format change; server restart replaces old in-memory archives.
- codol_engine_state.c publishes C1 ps40 using the captured state's use_hint_weapon binding only when throwback weapon/timer are present, otherwise zero. Archived snapshots never consult live entities or current weapon registry. Existing wire bound1..700 applies.
- codol_weapon_state.c honors C1 held0x4000/timer/cursor/exact captured weapon before ordinary selected-slot scan. No ownership/rising-edge requirement for the recovered grenade.

Exact downstream identity retained: assembly PM_Weapon_CheckForOffHand_190 emits EV_SWITCH_OFFHAND34 (C1 wire51) with selected index then stores ps.offHandIndex+e0. G_UseOffHand reads+e0 and passes it to Weapon_Throw_Grenade. No fallback class scan occurs after selection.

## Fuse/owner/removal lifecycle already present

HandleClientEvent_220 validates selected and target grenade class1, reads target owner's entity handle into ps.throwBackGrenadeOwner and copies current throwback time to grenadeTimeLeft. Target handler7 uses Touch_Item_Auto, which sets active then calls Touch_Item. Its successful missile path emits trigger/pickup/death and frees the original native missile.

Held grenade time continues through native offhand state. G_FireGrenade_130 sets the new missile's nextthink to level.time + remaining grenadeTimeLeft and clears held time; it does not use a fresh definition fuse when recovering a cooked grenade. Thus this path recovers the active grenade for throwback, not a fresh inventory stack. No script refund, new visual proxy, or live fuse reset added.

## Exact equipment limits and physics metadata

C1 server50baed and50b9f9 explicitly require offhandClass1. Common_gametype_mp original asset header evidence:

| Asset | Weapon | Offhand | Stickiness | Cook | Timed |
|---|---|---:|---:|---:|---:|
|4073|frag_grenade_mp|1|0|1|1|
|4082|semtex_mp|5|1|0|1|
|4094|flash_grenade_mp|3|0|0|1|
|4100|smoke_grenade_mp|2|0|0|1|
|4102|emp_grenade_mp|2|0|0|1|
|4104|concussion_grenade_mp|2|0|0|1|
|4109|white_phosphorus_grenade_mp|1|0|1|1|
|4134|c4_mp|5|2|0|0|
|4138|bouncingbetty_mp|5|3|0|0|

Fields source+354 offhand,+7c8 stickiness,+bcc cook,+be2 timed; source name verified inline at3068.

Frag and white phosphorus fit the C1 supported throwback path. Semtex/flash/smoke/EMP/concussion generic return remains unimplemented: normal stock increment would reset their live fuse, and their non-cook behavior differs. Extending this requires a new native held-item expiry representation with client-compatible production/consumption, not changing a class comparison alone. Parent's stun/flash work is separate.

C4 sticky2 means all surfaces except sentients; Betty sticky3 means ground only. Current native metadata policy already distinguishes these exact values. No additional physics source change made without a concrete contradictory collision trace. Full gameplay completion not claimed.


## Owned special-grenade inventory recovery (2026-09-15 source increment)

User explicitly requested inventory recovery before destruction/explosion. No C1 vanilla special-grenade stock recovery path was established: the verified C1 server throwback branches accept offhand class1. This increment is an authorized native extension, not a claim that vanilla C1 performs it.

`codol_missile_pickup.c/.h` identifies a real ET_MISSILE with registered original C1 weapon metadata, timedDetonation (source +be2), and offhand class2/3/5 (source +354). It covers shipped smoke/EMP/concussion, flash, and Semtex without weapon-name aliases. Source class9 keeps the existing knife semantics. Class1 frag/white phosphorus keep existing live-fuse throwback. Untimed C4/Betty/scrambler retain their established device paths.

Recovery requires a live player, original missile owner handle matching that player, fuse deadline strictly after current level.time, exact weapon still owned, and real ammo capacity. Native Add_Ammo requests one with fillClip=1; actual positive transfer is required. The helper then clears original nextthink, emits the existing item pickup event when predictItemPickup is enabled, notifies trigger(player,undefined), notifies death, and frees the original missile. useCount/inuse checks after each notification prevent deleting a replacement entity. Return2 tells Touch_Item to stop immediately. This cancels the deployed projectile; it never resets a still-live fuse or creates a replacement projectile. Subsequent deliberate deployment of the recovered inventory item follows its ordinary fuse rules.

`_player_use_mp.asm` uses the existing ordinary item-distance candidate and activation path, with a native ownership/capacity filter. No script_origin proxy or client modification is used. `_bg_misc.asm` gates inventory missiles before retained smoke/flash class branches. `_g_items.asm` passes the captured original missile as the fifth recovery argument; its existing frame has room for that argument.

Special pickups use HINT_NOICON and the native 32-entry hint configstring pool. Verified shipped `localized_code_post_gfx_mp.ff` asset2564 is `WEAPON_PICKUP_GENERIC` (localized activate prompt and &&1 weapon-name replacement). The second localized token is the actual registered weapon display key. C1 hint consumer456270 calls message localization5da400 at456307; parser5da49d/5da4a2/5da4a7 recognizes separators0x14/0x15/0x16. Two localized tokens use0x14, matching OpenBLOPS `Game/Server/game_mp/g_scr_main_mp.cpp::Scr_ConstructMessageString`. Missing name/full hint pool suppresses the hint instead of publishing an incorrect throwback prompt.

Source written and reviewed locally; no builds, tests, process changes, or gameplay verification performed by this worker. Parent review/build remains required. Frag inventory reclaim is not added: its existing C1 throwback semantics remain. This increment therefore does not claim every equipment request complete.
