# C1 killstreak activation catalogue migration (2026-09-14)

Source staged only: `obj/killstreak-activation-stage/maps/mp/killstreaks/_killstreaks.gsc`.
Based on live000A script; deployed activation cleanup and reward-order changes
preserved. Parent review/build/deployment pending; no tests/process changes.

## Evidence and scope

Fresh verified inflation of shipped code_post_gfx_mp, common_gametype_mp,
patch_code_post_gfx_mp, patch_common_gametype_mp recovered the winning
`mp/coKillstreakStatsTable.csv`:69 rows,24 columns. Pooled cells resolved across
those zones; the recovered row data is saved beside the staged source as
`c1-killstreak-table.json`. This is asset evidence, not a generated replacement
asset. No extra zones, client edits or asset patches are proposed.

Exact zero-based columns consumed here:0ID,1name,4killcost,7earned hint,
8earned sound,9earned leader dialog,10allies use dialog,11axis use dialog,
12inform enemy,13activation weapon,14XP points,15icon,16crate icon. IW4's
activation columns6..15 were one column earlier. Existing class/HUD uses
columns0/4 already; shared metadata accessors now use the same C1 catalogue.

The initializer walks physical rows instead of stopping at the first missing
numeric ID. It runs after the existing init threads register actual handlers,
then processes only rows with a registered handler. Reviewed primary init
bodies register before their event waiters (e.g. _ac130:102, _helicopter:111,
_airdrop:76, _uav:27, _airstrike:73, _autosentry:17). Native thread invocation
runs those initial bodies before returning to this caller; no extra wait is
introduced. No unsupported weapon is precached merely because it appears in
the catalogue, and no pro reward is silently aliased to its base behavior.

Optional metadata policy: blank hint/shader/weapon is not precached, zero XP
is not registered as an award. Existing `_utility::playLeaderDialogOnPlayer`
asserts its dialog entry is defined, then explicitly skips any `null` value.
Therefore all five dialog keys are initially set to that existing silent
sentinel, and populated only by actual nonempty/non-null table values. C1
sentry's team dialogue cells are literally `null`; ZM rows have blank dialogue
and zero XP. These are real optional fields, not missing gameplay stubs.

## Matched existing callbacks (metadata integrated, gameplay not reverified)

uav, airdrop, counter_uav, airdrop_sentry_minigun, predator_missile, precision_airstrike, harrier_airstrike, helicopter, airdrop_mega, helicopter_flares, stealth_airstrike, helicopter_minigun, ac130, emp, nuke, sentry.

The runtime registry is the filter, not this list hardcoded into source. These
are the16 C1 base rows for which the existing initialized IW4 scripts provide
real callbacks. This increment corrects metadata consumption; it does not
certify every native vehicle/turret/remote effect used by those callbacks.

## Remaining unimplemented catalogue callbacks

New base MP reward callbacks missing from the current initialized suite:

mortar_mp, rcbomb_mp, sr71_mp, dogs_mp, sam_turret, airdrop_sam_turret.

Pro reward callbacks are not implemented just because column22 names a base:

uav_pro, counter_uav_pro, rcbomb_pro_mp, airdrop_pro, airdrop_mega_pro, airdrop_sam_turret_pro, sam_turret_pro, airdrop_sentry_minigun_pro, sentry_pro, mortar_pro_mp, precision_airstrike_pro, predator_missile_pro, helicopter_pro, harrier_airstrike_pro, sr71_pro_mp, helicopter_flares_pro, stealth_airstrike_pro, helicopter_minigun_pro, dogs_pro_mp, ac130_pro, emp_pro.

ZM catalogue entries belong to a separate mode implementation and have no
callbacks in this MP suite:

carpenter_zm, nuke_zm, double_points_zm, insta_kill_zm, minigun_zm, full_ammo_zm, fire_sale_zm, tesla_zm, free_perk_zm, all_revive_zm, sentry_zm, rcbomb_zm, pandora_zm, bonus_points_player_zm, bonus_points_team_zm, perkpop_deadshot_zm, perkpop_longersprint_zm, perkpop_disguise_zm, perkpop_carpenter_zm, perkpop_discount_zm, perkpop_flakjacket_zm, perkpop_electro_zm, perkpop_additionalprimary_zm, perkpop_scavenger_zm, perkpop_pandora_zm.

No handler stubs or constant-success return paths were added. Selecting an
unimplemented reward remains incomplete implementation work; metadata access
alone must not be counted as activation support. Legacy IW4-only registered
aliases absent from the C1 catalogue (e.g. double_uav, tank,
helicopter_blackbox/mk19) gain no invented C1 rows or fallback identities.
Default airdrop reward entries were checked: their killstreak rewards all
match C1 rows1..16; ammo uses its separate ammo crate function.
