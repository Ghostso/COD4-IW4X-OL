# CoDOL multiplayer killstreak suite — audit and implementation, 2026-09-15

Scope: every killstreak CoDOL 1.1.1.13 ships, its earn/call-in wiring, the
native support it depends on, what the last live sessions actually prove, and
the work done in this pass. Evidence is cited by file and line so each claim
can be rechecked. A registered handler is not counted as a working reward.

---

## 1. The shipped catalogue

Authoritative source: `mp/coKillstreakStatsTable.csv`, recovered from the
mounted client zones and saved at
`obj/killstreak-activation-stage/c1-killstreak-table.json` (69 rows,
24 columns). MP rewards are IDs 1..43; IDs 44+ are zombie rewards belonging to
a different mode.

Column layout in use: 0 ID, 1 name, 2/3 title/description, 4 kill cost,
7 earned hint, 8 earned sound, 9 earned leader dialog, 10/11 allies/axis use
dialog, 12 inform enemy, 13 activation weapon, 14 XP, 15 icon, 16 crate icon,
**22 base reward**, 23 crate weight.

There is no `tank` row. `maps/mp/killstreaks/_tank.gsc` is IW4-only: it
compiles every map load but no catalogue row and no loadout item can ever
reach it. `double_uav`, `helicopter_blackbox`, `helicopter_mk19`,
`auto_shotgun`, `thumper`, `airstrike`, `super_airstrike` and
`airdrop_predator_missile` are likewise IW4 registrations with no C1 row.

---

## 2. Per-killstreak state

Evidence keys: **B** = `bin/home/main/qconsole.log.old` (session opened
19:07:52, mp_killhouse_sh, build 1229), **X** =
`obj/harrier-crash-20260915.log` (frozen Sep 14 capture, build 0),
**G** = `bin/home/main/games_mp.log`, **C** = the live `qconsole.log`.
An earlier session ("A") was rotated away mid-audit; two claims below are
marked as no longer citable from disk.

| ID | Reward | Cost | Activation weapon | Handler registered | Live evidence | Status before this pass |
|---|---|---|---|---|---|---|
| 1 | uav | 3 | killstreak_uav_mp | `_uav.gsc:29` | given 44x, activated 3x, no errors | **working** |
| 2 | airdrop | 5 | airdrop_marker_mp | `_airdrop.gsc:76` | never selected or used | registered, unexercised |
| 3 | counter_uav | 4 | killstreak_counter_uav_mp | `_uav.gsc:31` | given 5x, activated X:13841 | **working** |
| 4 | airdrop_sentry_minigun | 5 | airdrop_sentry_marker_mp | `_airdrop.gsc:79` | never selected or used | registered, unexercised |
| 5 | predator_missile | 5 | killstreak_predator_missile_mp | `_remotemissile.gsc:32` | 16 kills incl. G:19419 on build 1229 | **working** |
| 6 | precision_airstrike | 6 | killstreak_precision_airstrike_mp | `_airstrike.gsc:74` | 4 `artillery_mp` kills (G:3572, 16450-16453) | **working** |
| 7 | harrier_airstrike | 7 | killstreak_harrier_airstrike_mp | `_airstrike.gsc:76` | fatal X:18716; 23 `harrier_20mm_mp` kills on build 1228 | **fixed before this pass** (see 3.1) |
| 8 | helicopter | 7 | killstreak_helicopter_mp | `_helicopter.gsc:111` | activated once, 0 kills; both models `void` | **broken — no model** |
| 9 | airdrop_mega | 8 | airdrop_mega_marker_mp | `_airdrop.gsc:80` | never selected or used | registered, unexercised |
| 10 | helicopter_flares | 9 | killstreak_helicopter_flares_mp | `_helicopter.gsc:113` | never used; axis model `void` | **broken — no model** |
| 11 | stealth_airstrike | 9 | killstreak_stealth_airstrike_mp | `_airstrike.gsc:77` | never used | registered, unexercised |
| 12 | helicopter_minigun | 11 | killstreak_helicopter_minigun_mp | `_helicopter.gsc:114` | never used; allies model `void` | **broken — no model** |
| 13 | ac130 | 11 | killstreak_ac130_mp | `_ac130.gsc:102` | selected 4x, never given; model `void` | **broken — no model** |
| 14 | emp | 15 | killstreak_emp_mp | `_emp.gsc:18` | never used (all EMP hits are the grenade) | registered, unexercised |
| 15 | nuke | 25 | killstreak_nuke_mp | `_nuke.gsc:18` | never used | registered, unexercised |
| 16 | sentry | 5 | killstreak_sentry_mp | `_autosentry.gsc` (dynamic `sentryType`) | never used | registered, unexercised |
| 17 | mortar_mp | 6 | mortar_mp | `_mortar.gsc:11` | 7 kills, G:16641-16645 | **working** |
| 18 | rcbomb_mp | 3 | rcbomb_mp | none | given 9x, then `g "Killstreak not implemented: rcbomb_mp"` x9 | **unimplemented** |
| 19 | sr71_mp | 8 | radardirection_mp | `_sr71.gsc:7` | selected 2x, never executed | registered, unexercised |
| 20 | dogs_mp | 11 | dogs_mp | none | given 6x, then `"Killstreak not implemented: dogs_mp"` | **unimplemented** |
| 21 | sam_turret | 4 | auto_tow_mp | none | zero occurrences in any log | **unimplemented** |
| 22 | airdrop_sam_turret | 4 | airdrop_sam_marker_mp | none | zero occurrences | **unimplemented** |
| 23-43 | 21 `*_pro` rewards | — | `killstreak_pro_*` | none | selectable, would print "not implemented" | **unimplemented** |

Every one of the 22 base activation weapons resolves in the mounted C1 weapon
archive: `CoDOL native weapon lookup:` lines at B:701-702 and B:2266-2324 cover
`airdrop_marker_mp`, `mortar_mp`, `radardirection_mp`, `rcbomb_mp`, `dogs_mp`
and the sixteen `killstreak_*_mp` names. No killstreak weapon is skipped by
`precacheItem`; the ~660 skipped weapons are attachment permutations only.

### The generic earn/use path is sound

`_killstreaks.gsc` `giveKillstreak` -> `giveKillstreakWeapon` -> `_giveWeapon`
plus `_setActionSlot`; native `G_RunFrame` emits `weapon_change`;
`killstreakUseWaiter` matches the selected reward and calls
`killstreakUsePressed`, which consumes the reward only if the handler returns
true. Five native action slots publish through `codol_action_slots.c`, and the
selected/earned HUD publishes through `codol_killstreak_hud.c`. The logs show
this working: every reward the player earned was given with `result 1 owned 1`
and the correct `mp_killstreak_*` HUD splash fired. **The generic machinery is
not the problem.** The problems are per-reward: absent handlers, and models
that are absent from every mounted zone.

### Static resolution: no missing builtins, no missing scripts

Every script reachable from `_killstreaks.gsc` (271 files) resolves: every
`#include` target exists, every `file::function` reference exists, and every
call name is either a script function in scope or one of the 898 builtins the
VM registers. So *no killstreak in the shipped suite is blocked on a missing
GSC builtin*, and nothing needed importing from the reference dumps for the
registered rewards. This is now enforced by a tool, see section 4.

### Missing vehicle models: the dominant real defect

`^3Warning: CoDOL xmodel '<name>' is not in any mounted zone; using void` for:

| Model | Reward | Evidence |
|---|---|---|
| `vehicle_ac130_coop` | ac130 | B:2190, X:2139/21140/24596 |
| `vehicle_cobra_helicopter_fly_low` | helicopter (allies) | B:2248, X:2198/21199/24655 |
| `vehicle_apache_mp` | helicopter_minigun (allies) | B:2249, X:2199/21200/24656 |
| `vehicle_pavelow_opfor` | helicopter_flares (axis) | B:2250, X:2200/21201/24657 |
| `vehicle_little_bird_bench` | helicopter_minigun | X:471 |
| `vehicle_av8b_harrier_jet_opfor_mp` | harrier | X:2191 (already fixed) |

`void` is not merely an invisible vehicle: it has no bones, so every
`playFxOnTag`, `linkTo(<tag>)` and `getTagOrigin` against it raises a script
error, and an uncaught script error at that point shuts the map down. That is
exactly the harrier failure at `_airstrike.gsc:674`/`:838`. The same class of
fault was latent in four more rewards.

---

## 3. What this pass changed

### 3.1 Harrier / precision / stealth strike — verified already fixed

`spawnplane`'s C1 contract (optional string minimap-icon names at arguments
3 and 4, optional int spawnflags at 5) is implemented in
`src/codol/script/codol_script_minimap.c:48` `CODOL_Scr_SpawnPlane`, reached
from `src/asmsource/_g_scr_main_mp.asm:922-923`, and
`scripts/codol/maps/mp/killstreaks/_airstrike.gsc:26-27` precaches both icons.
The `type string is not an int` shutdown at X:18716 cannot recur on the current
binary. No change made. **Needs live confirmation.**

### 3.2 Aerial killstreak models — replaced void models with shipped ones

Replacement models were chosen from actual bone coverage, not name similarity.
Bones were read out of the shipped zones with the same method as the harrier
audit (xmodel asset, bone count at +4, tag name ids after the model name);
results in `obj/harrier-model-audit/` style, reproduced here:

| Shipped model | Bones | Tags the killstreak scripts need |
|---|---|---|
| `vehicle_mi24p_hind_mp` | 36 | origin, ground, deathfx, engine_left, light_L_wing, light_R_wing, light_belly, light_tail, light_cockpit01, player, **store_r_2**, flash |
| `vehicle_mi-28_mp` | 54 | origin, ground, deathfx, engine_left, light_L_wing, light_R_wing, light_belly, light_tail, player, turret, barrel, flash |
| `vehicle_pavelow` | 46 | origin, ground, deathfx, engine_left, **gunner_left**, **gunner_right**, light_L_wing1, light_R_wing1, light_belly, light_tail, light_tail2, light_cockpit01 |
| `vehicle_ac130_low_mp` | 21 | origin, ground, **body**, 105mm/25mm/40mm, flash_flares, light_belly, light_tail, light_top (**no** deathfx, **no** player) |
| `vehicle_little_bird_armed` | 32 | has player/turret/barrel/flash but **no** engine_left and **no** light_L_wing — rejected for every branch |

**`scripts/codol/maps/mp/killstreaks/_helicopter.gsc:16-27`** — precache list
now contains only shipped models, each mapped to its own already-registered FX
type (`hind`, `mi28`, `pavelow`, `littlebird`). The three `void` names are gone.

**`_helicopter.gsc:700-726`** (`heli_think` model selection):

- attack helicopter (`cobra_mp`) -> `vehicle_mi24p_hind_mp` for both teams.
  It is the only shipped helicopter carrying `tag_store_r_2`, which
  `_helicopter.gsc:1395` uses as the FFAR launch tag, *and* the
  `defaultLightFX` wing lights at `:167-176`.
- chopper gunner (`cobra_minigun_mp`) -> `vehicle_mi-28_mp` for both teams.
  Carries `tag_player` for `PlayerLinkWeaponviewToDelta` at `:397`, plus
  `tag_flash` for `fireWeapon` at `:1643`.
- pave low (`pavelow_mp`) -> `vehicle_pavelow` for both teams. It is the only
  shipped model with `tag_gunner_left`/`tag_gunner_right`, which
  `makeGunShip` at `:812`/`:824` links the two miniguns to.

Both teams now share a model per reward. That is a deliberate, stated
limitation: no shipped second model covers the required bones, and a model with
a missing bone is a map shutdown, not a cosmetic defect. Team identity still
comes from the existing team icons and ownership.

**`scripts/codol/maps/mp/killstreaks/_ac130.gsc`** — new CoDOL override, copied
from the vendor IW4 script and adapted at four sites:
`:22-27` precaches `vehicle_ac130_low_mp`; `:634` and `:705` set it;
`:1716-1718` plays the crash effect on `tag_body` because the shipped gunship
has no `tag_deathfx`. `tag_body` is already the engine-effect tag at `:476`, so
this is the model's real hull bone, not a substitute guess. Every other tag the
script addresses (`tag_flash_flares` `:1777`/`:1853`, `tag_light_belly`
`:475`, `tag_light_tail` `:478`, `tag_light_top` `:479`) is present.
The `tag_player` links at `:413`/`:713`/`:721` target `level.ac130`, which is
the `c130_zoomrig` model — verified to carry `tag_origin`, `tag_angle` and
`tag_player` — so they are unaffected.

### 3.3 The 21 pro rewards — implemented from the catalogue's own base column

A pro row is identical to its base row in every gameplay column. The complete
diff between, for example, row 1 `uav` and row 23 `uav_pro` is: ID, the
localized title/description, `MP_EARNED_UAV` -> `MP_EARNED_PRO_UAV`, the
activation weapon `killstreak_uav_mp` -> `killstreak_pro_uav_mp`, and column 22
going from empty to `uav`. Cost, sound, all three dialog columns, inform-enemy,
XP, both icons, all unlock columns and crate weight are byte-identical. All 21
pro rows resolve their column 22 to an existing base row.

Column 22 is therefore the catalogue's own statement of which reward's
behaviour a pro reward runs, and it is the only column that distinguishes the
pro rows at all.

- `_killstreaks.gsc:803-812` new `getKillstreakBaseRef()` reads column 22 and
  falls back to the name itself.
- `_killstreaks.gsc:99-129` `initKillstreakData` installs
  `level.killstreakFuncs[pro] = level.killstreakFuncs[base]` (and the setup
  func when the base has one). Two gates, neither waived: the base must have a
  real registered handler, so `dogs_pro_mp` and `rcbomb_pro_mp` stay
  unimplemented while their bases are; and the pro row's own
  `killstreak_pro_*` weapon must resolve. The existence test is
  `codol_weaponInventoryType( name ) == "unknown"`
  (`src/codol/script/codol_script_weapon_queries.c:188-212`), which resolves a
  mounted native weapon and answers without raising — so a pro weapon that is
  not in the archive skips the row instead of failing `precacheItem` and
  shutting the map down.
- `_killstreaks.gsc:254/270/284` `isRideKillstreak`, `isCarryKillstreak` and
  `deadlyKillstreak` now switch on the base ref, so a pro reward is gated by
  its base reward's airborne / turret / last-stand / round-grace rules instead
  of silently falling through to `default: return false`.

Each pro reward keeps its own metadata — its own earned hint, dialogs, XP
award, icons and activation weapon are registered by the existing loop; only
the use callback is shared. This does **not** claim CoDOL applies no extra
pro-only buff; no shipped column expresses one, so none was fabricated.

Expected effect: 21 rewards move from `iPrintLnBold("Killstreak not
implemented: <name>")` to running their base behaviour. This is the largest
coverage change in the pass and it is entirely data-derived.

### 3.4 RC-XD (`rcbomb_mp`) — scripts installed, builtin implemented, gated off

A previous agent left a complete adapted T5 RC-XD implementation staged at
`obj/rc-physics-stage/scripts/maps/mp/killstreaks/` and never shipped it into
the loaded tree — which is why `rcbomb_mp` was granted, HUD-announced, and then
answered with `g "Killstreak not implemented: rcbomb_mp"` nine times in X.
The supporting native work (owned ODE bodies, T5 wheel constraints, C1 remote
driver ownership, `usevehicle`/`getseatoccupant`/`isremotecontrolling`,
`setclientflag` family, RC placement trace and spawn influence) is already
built and deployed.

Installed into `scripts/codol/maps/mp/killstreaks/`: `_rcbomb.gsc`,
`_rcbomb_rules.gsc`, `_rcbomb_presentation.gsc`, `_rcbomb_watchers.gsc`.

Three names the staged script referenced did not exist. All three were resolved
without inventing behaviour:

1. **`spawnvehicle`** — the legacy IW4OL `GScr_SpawnVehicle` is commented out in
   `src/scr_vm_functions.c:2698` and used the wrong argument order
   (`origin, spawnflags, type, model`). `CODOL_Scr_SpawnVehicle`
   (`src/codol/vehicle/codol_vehicle_spawner.c:126-173`) already implements the
   real IW4/C1 contract — `model, targetname, vehicle definition, origin,
   angles` — loads the definition, selects the helicopter initializer for
   definition type 5 and the retained `SpawnVehicle` otherwise, and installs
   the per-spawn `script_vehicle_collmap` brush. It was written but never
   registered. **Registered at `src/scr_vm_main.c:389-399`** under
   `CODOL_SERVER`. Verified present in the built binary.
2. **`setEnemyModel` + `codol_setRCModelAudience`** — T5 shows each viewer a
   differently coloured car. C1's entity state publishes one model per entity
   and no measured C1 producer selects a second model per recipient, so
   implementing this would mean inventing a snapshot facility. Instead
   `_rcbomb.gsc:42-73` picks the car by the **owner's** team
   (`t5_veh_rcbomb_allies` / `t5_veh_rcbomb_axis`, both verified present in
   `common_gametype_mp`, 20 bones each, carrying `tag_origin`, `tag_body`,
   `tag_driver`, `tag_player` and the four wheel tags). Friend/enemy
   identification still comes from the already recipient-filtered green/red
   blink in `_rcbomb_presentation::blink`. Stated limitation, not parity.
3. **`vector_scale`** — has no counterpart in the mounted IW4
   `common_scripts/utility`. Replaced at `_rcbomb.gsc:353-357` with
   `vector_multiply` (`common_scripts/utility.gsc:1457`), the same scalar-times-
   vector operation, already in scope.

`isRideKillstreak` now includes `rcbomb_mp`, matching T5: RC requires being on
the ground, is refused while using a turret or in last stand, and does not
force a weapon switch back after use.

**RC-XD is currently gated off at `_killstreaks.gsc:35-44`** — see section 5.

### 3.5 The helicopter was never missing - the snapshot dropped it

Live call-in on mp_killhouse_sh, current build, `bin/home/main/qconsole.log`:

```
3952: CoDOL giveweapon: name killstreak_helicopter_mp engine 84 wire 106 ... result 1 owned 1
4024: CoDOL reliable -> Nucleur: d 3437 mp_killstreak_heli
4100: tableLookup miss: mp/statstable.csv column 4 value 'killstreak_helicopter'
4101: CoDOL reliable -> Nucleur: d 3972 019tag_light_l_wing
4102: CoDOL reliable -> Nucleur: d 3439 weap_c4detpack_trigger_plr
4104: CoDOL reliable -> Nucleur: d 3440 ab_1mc_use_str_heli
4109: CoDOL reliable -> Nucleur: d 3441 uk_1mc_enemy_str_heli
4117: ^3Warning: CoDOL entity type 12 cannot be seeded; dropping it from snapshots
4118: CoDOL reliable -> Nucleur: d 3973 015tag_light_r_wing
4119: CoDOL reliable -> Nucleur: d 3974 017tag_light_belly
4120: CoDOL reliable -> Nucleur: d 3975 016tag_light_tail
```

This disproves the path/early-out hypothesis outright, and it also **validates
the model fix in 3.2**:

- The four `d <cs> <tag>` registrations are `defaultLightFX`'s four
  `playFXOnTag` calls at `_helicopter.gsc:167-176` completing in order with the
  0.05 s waits between them. A `void` model would have raised on the first one.
  So `vehicle_mi24p_hind_mp` resolved and carries all four light bones.
- `d 3440 ab_1mc_use_str_heli` / `d 3441 uk_1mc_enemy_str_heli` are
  `usedKillstreak`'s leader dialogs, which run **only after** the use function
  returns true. `weap_c4detpack_trigger_plr` is its `playLocalSound` on the
  same path.
- Killhouse does ship the routes: `docs/CODOL_AERIAL_MAP_PATHS_20260915.md`
  resolves three `heli_start` chains, a seven-node `heli_loop_start` cycle, a
  `heli_crash_start` chain and five `heli_leave` records in the map entity
  text. `_helicopter::init` therefore does not take its no-nodes early return,
  which is also why `level.killstreakFuncs["helicopter"]` was registered at all.

**Root cause: `entity_seed` had no arm for `ET_HELICOPTER` (12) or
`ET_VEHICLE` (14).** The helicopter spawned, took a model, ran its light FX and
followed its path - and every client dropped it from every snapshot, so nothing
was ever drawn. `ET_PLANE` (13) and `ET_MG42` (11) on either side of it both
have arms; the vehicle pair did not.

All three overlays this needs already existed and were simply unreachable -
`CODOL_OverlayEngineVehicleIdentity`, `...VehicleAssets` and `...VehiclePose`
at `src/codol/snapshot/codol_engine_state.c:1614/1635/1669` - and the identity
producer is wired too: `CODOL_EntityStateVehicleCaptured` is called from the
retained `SpawnVehicle` (`src/asmsource/_g_vehicles_mp.asm:4487`) and
`CODOL_CaptureVehicleSpawnClient` from `_g_scr_helicopter.asm:283`.

**Fix — `src/codol/snapshot/codol_sv_gameframe.c:266-314`**, new
`case ET_HELICOPTER: case ET_VEHICLE:` arm: resolve the visual model from
`un2` (+0xd8; `index`/+0x88 is the collision brush), then apply identity,
assets and pose in that order. Model 0 is the legitimate "no visual model"
case and `CODOL_ServerModelToWire` maps it to 0, which is what the asset
overlay's both-or-neither test expects.

This one arm covers the attack helicopter, pave low and chopper gunner, and
any other script-spawned vehicle including RC-XD. **The AC-130 does not depend
on it**: its rig and plane model are `script_model` (`ET_SCRIPTMOVER`) and its
compass marker is `spawnPlane` (`ET_PLANE`), all of which already had arms -
its blocker was only the void model fixed in 3.2.

### 3.6 No more silent failures

Two changes so the next "I pressed it and nothing happened" is self-explanatory
from the console alone.

**The dropped-entity warning now states the reason.** It reported the type once
and nothing else, which is why a whole killstreak could vanish with one
unattributable line. `codol_entity_seed_reason`
(`src/codol/snapshot/codol_sv_entities.c:10-17`, cleared before each resolve,
printed with the warning at `:110-118`) carries a reason the resolver writes.
The vehicle arm fills it in for each of its four refusal points - no wire slot
for the visual model, identity not captured at spawn, assets rejected with the
model/weapon/brush values, pose out of range. The dependency direction is
deliberate: the resolver in `codol_sv_gameframe.c` writes a symbol owned by
`codol_sv_entities.c`, which already links standalone in the unit tests.

**Every silent refusal in `killstreakUsePressed` now prints one line.** Six
bare `return false` paths left the reward owned, nothing on screen and nothing
in the log. `killstreakRefused()` (`_killstreaks.gsc:303-313`) prints
`CoDOL killstreak: <name> refused: <reason>` and returns the same false the
callers already expect, so no control flow changed. Covered: not on the ground,
already using a remote killstreak, a location selection already open, weapon
disabled, the reward's own use function returned false, and ownership revoked
while the use function ran. The paths that already showed the player an
`iPrintLnBold` were left alone.

**`_helicopter.gsc:730-738`** additionally prints one positive line naming the
entity, vehicle type and model on spawn, and one on spawn failure.

### 3.7 Builtins the helicopter path needs - verified real, not stubs

`spawnhelicopter` is a full C implementation at `src/scr_vm_functions.c:2645`
(registered `src/scr_vm_main.c:390`). The flight-path methods the script uses -
`setvehgoalpos`, `setgoalyaw`, `setneargoalnotifydist`, `setyawspeed`,
`setmaxpitchroll`, `setairresistance`, `setturningability`, `sethoverparams`,
`vehicle_setspeed`, `setlookatent`, `setvehweapon`, `setturrettargetent`,
`setvehicleteam`, `freevehicle` - are all registered at
`src/scr_vm_main.c:1004-1028` against the retained `CMD_VEH_*` bodies in
`src/asmsource/_g_scr_vehicle.asm`. `missile_createattractorent` is registered
at `:159`. `getentitynumber` is a method at `:844`. None is a stub.

### 3.5 Not implemented in this pass

- **`dogs_mp` / `dogs_pro_mp`.** All the native work is staged and unintegrated
  (`obj/dogs-stage/`, `docs/CODOL_DOGS_IMPLEMENTATION_20260914.md`): actor
  composition, T5 attack-goal claiming, goal/route following, root-motion
  consumption and actor physics exist as source, but perception, orientation,
  the 47-state `bg_dog` animation mapping, the animation-tree constructor and
  the entity-state animation producer do not. There is no `_dogs.gsc` in the
  local `BO1-GSC` dump (it carries only the SP/zombie dog scripts). Completing
  dogs is a multi-subsystem job, not a script import.
- **`sam_turret` / `airdrop_sam_turret`.** Need an anti-air target
  selection/lock/missile lifecycle. Aliasing them to the minigun sentry would
  hide that; not done.
- **Per-team RC car model**, and the pro-specific buff if CoDOL has one — both
  need evidence that does not exist in the shipped data.

---

## 4. New tool: `tools/codol_script_resolve.py`

A GSC call to a builtin the VM does not register is a **compile-time**
`unknown function`, and a script compile error at map load is `Sys_Error`: the
whole match dies. It is invisible to runtime testing and invisible to a partial
check. This pass caused exactly that failure once, by shipping the RC-XD
scripts before the binary that registers `spawnvehicle` was deployed.

The tool reproduces the loader's own behaviour offline:

1. Builds the VM's builtin table from every `Scr_AddFunction`/`Scr_AddMethod`
   in `src/`, **after stripping C comments**, so a commented-out registration
   (the exact `spawnvehicle` case) is correctly counted as absent.
2. Builds the effective script tree in loader precedence order, or reads the
   collated root directly.
3. Walks the reachable set from the entry scripts, following `#include` and
   `file::function`, and lowers nothing else — its reachable set reproduces the
   14 killstreak modules the boot log prints as `CoDOL lowering:` exactly.
4. Reports unresolved call names, missing includes and dangling namespaced
   calls, and exits nonzero.

It normalizes CR-only line endings (several shipped IW4 scripts use them, which
otherwise makes `//` swallow the file) and strips string literals (GSC assert
messages contain text that parses as calls).

Usage after every script batch, against the root the server loads:

```
python tools/collate_gsc.py
python tools/verify_gsc_collation.py
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only maps/mp/killstreaks
```

Pre-existing diagnostics outside the killstreak chain (unrelated to this pass,
all in vendor IW4 files): `xmodelalias/alias_*_heads_*.gsc` and two
`character/mp_character_us_army_*` scripts are decompiler artifacts with
newlines replaced by `.`; `common_scripts/_createfx.gsc` emits `#include` text
from string literals; `common_scripts/_artcommon.gsc` and `maps/mp/_art.gsc`
have an unbalanced quote that desynchronizes literal stripping. Use `--only` to
scope a gate to the batch under change.

---

## 5. Live-server incident and current gate

Shipping `_rcbomb::init()` while the deployed binary (build 1229) did not yet
register `spawnvehicle` produced
`Sys_Error: script compile error / unknown function` at map load and took the
server down. Fixed by commenting the single init line at
`_killstreaks.gsc:35-44`; only reachable scripts are lowered, so the four
`_rcbomb` files are now out of the compile set entirely while remaining
installed. Verified: the collated root's reachable set is the same 14
killstreak modules as before, `spawnvehicle` appears in reachable code only
inside `//` comments, and the gate exits 0.

**To enable RC-XD: deploy a binary built from the current source (it registers
`spawnvehicle`), then uncomment the one line at `_killstreaks.gsc:44`, re-run
`collate_gsc.py`, and re-run the resolver gate.**

---

## 6. Build and tests

- Cross-build clean and linked: `bin/codol_ks_audit.exe`, sha256
  `07906c66caa7ce97e3995b38dc59bcdaebda25a2172891a9a6afe8b51834ed9d`, log
  `obj/build-ks-audit-20260915.log`. Built into an isolated `OBJ_DIR` and
  target name so the concurrent deploy agent's `obj/codol` and
  `bin/codol_dedrun_next.exe` were not touched. `spawnvehicle` confirmed
  present in the binary and absent from the deployed one.
- `make test-codol`: 27 targets pass, then `test_codol_native` (makefile:445)
  fails to link. **Pre-existing and not from this pass** — that link names its
  sources explicitly and `codol_game.c` / `codol_sv_state.c` /
  `codol_sv_snapshot.c` / `codol_playerstate_ext.c` / `codol_radar_input.c`
  have grown calls into sources the link does not include:
  `CODOL_ResetClientActionSlotState`, `CODOL_ResetClientKillstreakHud`,
  `CODOL_PmoveC1ResetClient`, `CODOL_PmoveC1ResetAll`,
  `CODOL_RefreshMapSunSampleSize`, `CODOL_ResetMapSunSampleSize`,
  `CODOL_GlassWorldEnsureMap`, `CODOL_GlassWorldCapture`, `CODOL_WriteGlass`,
  `CODOL_ResetPerkRuntime`, `CODOL_ResetClientRadarTypes`,
  `CODOL_ResetAllRadarTypes`. This pass's only native change is one
  registration in `src/scr_vm_main.c`, which no test target links. The makefile
  is being edited concurrently, so it was left alone; the fix is to add
  `codol_action_slots.c`, `codol_killstreak_hud.c`, the pmove-C1 source, the
  glass world source, `codol_perk_effects.c` and `codol_radar_types.c` to that
  line. Log: `obj/test-ks-audit-20260915.log`.
- `tools/verify_gsc_collation.py`: OK — 1644 files, 0 missing, 0 hash
  mismatches, 0 unresolved lowering paths.

---

## 7. Open items and what to check live

Live checks, in impact order:

1. **Attack helicopter** — earn it and call it in. It should now spawn a Hind
   with lights, take damage smoke on `tag_engine_left` and fire FFAR from
   `tag_store_r_2`. Previously it spawned a void.
2. **Pave low** — the two door miniguns should appear and track. Previously
   the axis model was void.
3. **Chopper gunner** — the ride should link the player view to `tag_player`
   on an Mi-28 and fire from `tag_flash`.
4. **AC-130** — reaching 11 kills should now give and activate it; watch for
   the gunship model, the three gun tags and the crash effect on `tag_body`.
5. **Any pro reward** — select one in a class and earn it. It should run the
   base reward instead of printing "Killstreak not implemented".
6. **Harrier / precision / stealth strike** — confirm no repeat of the
   `_airstrike.gsc:674` shutdown.
7. After a new binary is deployed and the one line is uncommented: **RC-XD** —
   place, drive, detonate, 20+6+4s timer, scrambler stun.

Open, not addressed here:

- `Warning: CoDOL link: entity 470/471 unresolved tag tag_player` repeats at
  every boot, before any player exists (B:2332-2335/2342-2345, C:2305).
  `c130_zoomrig` does carry `tag_player`, so this is not a missing bone; the
  likely cause is a `linkTo` running before the parent's DObj is built. The two
  entities were not identified in this pass and no AC-130 `linkTo` site runs at
  init, so the producer is elsewhere. Needs a trace, not a guess.
- `mp/statstable.csv` has no killstreak rows, so every killstreak stat lookup
  logs `tableLookup miss: mp/statstable.csv column 4 value 'killstreak_*'` and
  falls back to column 2. Cosmetic today, but it silently drops per-killstreak
  stat attribution.
- `airdrop`, `airdrop_sentry_minigun`, `airdrop_mega`, `sentry`, `emp`, `nuke`,
  `stealth_airstrike` and `sr71_mp` have registered handlers and complete
  scripts but **zero** live exercise in any surviving log. They are unproven,
  not known-good. The fastest way to close that is one session that earns each
  one; without it, no stronger claim than "registered" is defensible.

---

## 8. Live defect batch, second pass (2026-09-15, later)

### 8.1 AC-130 crash: an optional field treated as mandatory

Live: `CoDOL giveweapon: name ac130_40mm_mp ... result 1 owned 1` then
`ERROR: CoDOL weapon reload perk metadata unavailable` and
`----- Server Shutdown -----`. Source
`src/codol/weapon/codol_weapon_state.c`, `weapon_frame_msec`.

That function computes nothing but a timing MULTIPLIER, and all of its inputs
are optional: IW4 treats a WeaponDef's reload-perk field as optional (absent
means the perk does not apply) and `coAbilityModifiersTable.csv` is a tuning
table. Three paths in it called `Com_Error(ERR_DROP)`. Killstreak-held weapons
- the three AC-130 guns, the chopper gunner minigun, the sentry and predator
weapons - are exactly the weapons with no reload metadata, because they never
reload.

All three now report once per weapon per cause and return the unmodified
duration: absent reload metadata, absent ability table or row, and a product
that is nonfinite or unrepresentable. `CODOL_ResetWeaponTimingReports()` is
called from `CODOL_ResetWeaponStates`, because a new zone renumbers weapons and
a stale flag would silence a genuinely new gap.

`tests/test_codol_weapon_timing_metadata.c` pins all of it, including that a
valid modifier is **still applied** (0.5 x 1000 = 500) so the degradation did
not quietly disable the feature. Added to the makefile test target.

Not changed, but noted: `src/codol/weapon/codol_item_ammo.c:20` still
`ERR_DROP`s when a selected weapon has no published C1 index. That one is
arguably load-bearing - an unpublishable weapon cannot be selected - but it is
the same shape and is the next candidate if a killstreak weapon trips it.

### 8.2 "The AC-130 started in first person" is the same defect

`setAC130Player` gives the three guns at `_ac130.gsc:445-448` and only then
threads `attachPlayer` at `:451`. The ERR_DROP above fired on the first weapon
frame after the give, so the camera link never ran and the player was left in
their own view holding gunship weapons.

The link itself is sound and was not rewritten on suspicion: `level.ac130` is
the `c130_zoomrig` script_model, whose shipped bone list is exactly
`tag_origin`, `tag_angle`, `tag_player` (3 bones, read out of
common_gametype_mp), and `playerlinkweaponviewtodelta` is a real registration
at `src/codol/script/codol_script_startup_extra.c:1081`. `attachPlayer`
(`_ac130.gsc:869-884`) now logs the link it made, or the missing rig, so the
next activation says which. Live confirmation is still required.

The boot-time `CoDOL link: entity 470/471 unresolved tag tag_player` warnings
are a **different** path: `capture_entity_links` explicitly skips `ent->client`
(`codol_player_worldweapon.c:108`), so they concern a linked non-player entity,
not the player's view. See 8.4.

### 8.3 Aerial route data: every installed map already ships it

The mapents entity lump of all 15 installed MP zones was dumped. The lump is
inline in the `col_map_mp` asset - `zone.by_type(19)` is empty in these zones -
so it is found by anchoring on `"classname" "worldspawn"`, backtracking to the
enclosing brace and reading to the first NUL. Validated byte-identical against
`obj/killhouse-mapents-shadow.bin` (227009 bytes, 1967 records; the existing
doc's end offset 5147037 is exclusive-off-by-one, it is 5147038).

**Every map ships the full stock IW node set. There is no CoDOL renaming of
helicopter routes.**

| map | heli_start | heli_loop_start | heli_leave | heli_crash_start | heli_dest | heli_attack_area | minimap_corner | airstrike height |
|---|---|---|---|---|---|---|---|---|
| mp_afghan | 3 | 1 | 4 | 3 | 1 | 17 | 2 | airstrikeheight |
| mp_bloc_sh | 3 | 1 | 4 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_bog_sh | 3 | 1 | 4 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_cargoship_sh | 3 | 1 | 5 | 1 | 1 | 0 | 2 | **none** |
| mp_crash_intro | 3 | 1 | 4 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_crash_tropical | 3 | 1 | 4 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_cross_fire | 2 | 1 | 3 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_estate_tropical | 2 | 1 | 3 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_fav_tropical | 3 | 1 | 5 | 1 | 1 | 10 | 2 | airstrikeheight |
| mp_killhouse_sh | 3 | 1 | 5 | 1 | 1 | 0 | 2 | **none** |
| mp_nuked | 4 | 1 | 4 | 1 | 2 | 0 | 2 | **air_support_height** |
| mp_overgrown | 3 | 1 | 4 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_rust | 3 | 1 | 4 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_storm_spring | 3 | 1 | 5 | 1 | 1 | 0 | 2 | airstrikeheight |
| mp_underpass | 3 | 1 | 5 | 3 | 1 | 0 | 2 | airstrikeheight |

Every `target` chain resolves; no dangling links in any map. Killhouse's three
`heli_start` chains terminate at `auto467`, its `heli_loop_start` is a closed
seven-node cycle and `heli_crash_start` runs `auto482 -> auto42 -> auto44`.
mp_rust shares the same authored template; mp_overgrown has its own `auto2..51`
numbering; mp_afghan has a 16-node loop; mp_nuked has two independent route
families (`pf13_*`, `pf832_*`) plus MW2-era `chopper_gunner_start`,
`heli_gunner_loop_start`, `heli_bound_min`/`max`, `no_fly_zone` and
`artillery_axis`/`artillery_allies` that no current script queries.

Two genuine gaps, both now handled:

- **`airstrikeheight` is absent on mp_killhouse_sh and mp_cargoship_sh, and
  renamed to `air_support_height` on mp_nuked** (`script_struct`, entity #1079).
  `_airstrike.gsc:852-861` and `_harrier.gsc:14-19` now try both names. Both
  already guarded the absent case and fall back to their scaled default height,
  so this was never a crash - but on nuked the authored height was ignored.
- `heli_attack_area` exists on only mp_afghan (17) and mp_fav_tropical (10).
  `_helicopter.gsc:782` reads it with `getEntArray`, which returns an empty
  array rather than failing.

`level.mapCenter` is produced per gametype from the spawnpoint bounding box
(`war.gsc:108`, and the same two lines in every other gametype) and published
with `setMapCenter`, which is registered. `getmapcenter` and `getmapsize` are
**not** builtins on this VM, and IW4's scripts do not call them, so nothing
needed adding. `_ac130.gsc:85-89` derives its own centre from the two
`minimap_corner` entities, which every map has.

New `aerialPathCensus()` (`_killstreaks.gsc:66-97`) prints all of the above
once per map after a frame yield, so `level.mapCenter`'s producer has run:

```
CoDOL killstreak paths: heli_start 3, heli_loop_start 1, heli_leave 5,
heli_crash_start 1, heli_dest 1, heli_attack_area 0, minimap_corner 2,
airstrike height none (scripts use their scaled default height),
mapCenter (x y z)
```

### 8.4 Diagnostics: the cap that hid everything after boot

`capture_entity_links` rate-limited itself with one `static unsigned failures`
counter capped at **eight messages for the lifetime of the process**. Boot
spends all eight on one repeating `tag_player` link, so every link failure for
the rest of the session was silent - precisely the state an unpublished
killstreak link would hide in.

It now limits per (cause, tag) with a 32-entry table, re-arms on map reset via
`CODOL_ResetEntityLinkReports()` from `CODOL_ResetPlayerWorldWeapons`, and
reports the **native tag index and the wire slot separately**:

```
CoDOL link: entity 470 parent 12 tag 'tag_player' unresolved
            (native index 37, wire slot -1); link not published
```

A native index of 0 means the tag was never registered as a server tag at all;
a nonzero native index with no wire slot means the C1 tag bank has not
published it. The two need different fixes and the old message could not tell
them apart.

### 8.5 Expected log on a successful call-in

Attack helicopter, after deploy:

```
CoDOL giveweapon: name killstreak_helicopter_mp ... result 1 owned 1
CoDOL reliable -> <player>: d <n> mp_killstreak_heli
CoDOL killstreak: helicopter  spawned entity <N> vehicle cobra_mp model vehicle_mi24p_hind_mp
CoDOL reliable -> <player>: d <n> 0##tag_light_l_wing     (and _r_wing, _belly, _tail)
CoDOL reliable -> <player>: d <n> ab_1mc_use_str_heli
```

and crucially **no** `CoDOL entity type 12 cannot be seeded` line. That warning
is now the single definitive signal: if it appears, the parenthesised reason
names which of the four seed steps refused.

AC-130:

```
CoDOL giveweapon: name ac130_105mm_mp / ac130_40mm_mp / ac130_25mm_mp ... result 1
CoDOL killstreak: ac130 linked player <N> weaponview to rig <M> tag_player
```

with no `CoDOL weapon reload perk metadata unavailable`. A line such as
`CoDOL weapon 61: no reload perk metadata (ability 1); using unmodified timing`
is expected and harmless - that is the degradation working.

Any refusal now names itself, for example
`CoDOL killstreak: helicopter refused: player is not on the ground`.

---

## 9. RC-XD lifecycle port and ODE dispatch fix (2026-09-15, later)

### 9.1 The ODE crash: the previous fix was necessary but not sufficient

The earlier root cause (`dxUserGeom::computeAABB` indexing `user_classes` by
the raw class id) was half right. The `-0x37` lea it added is correct, but
every user-class dispatch site in `src/asmsource/_collision_kernel.asm` still
read its table through `_ZZ9Phys_InitvE15Phys_Stop_f_VAR+0x30/+0x34/+0x38/
+0x3c`. That symbol is a disassembler artefact: the original binary folded
the `-11*0x14 = -0xdc` bias into the disp32 (`user_classes+field-0xdc`) and
the disassembler resolved that displacement against the nearest symbol below
it, phys_ode's static `Phys_Stop_f_VAR`. In the reassembled server the two
symbols live in different objects' `.bss` - measured in
`bin/codol_ks_audit.exe`: `Phys_Stop_f_VAR = 0x12569f5c`,
`user_classes = 0x11eee0d4` - so all five sites read zeroed phys_ode memory
and called or compared a NULL function pointer no matter how they were
indexed. Both owned-world near callbacks (`ownedNearCallback`, `pulseNear`)
call `dCollide`, which reaches the `+0x30` collider site for any user-class
pair, so the next crash after the earlier fix would have been there.

Fix: all five sites (`dCollideUserGeomWithGeom` x2, `computeAABB`,
`AABBTest`, `dGeomFree`) now use `lea r,[r+r*4-0x37]` and
`user_classes+0x4/0x8/0xc/0x10` directly - exactly ODE_CreateGeom's own
convention and arithmetically identical to the original biased-displacement
form. Full derivation is in the comment above `_ZN10dxUserGeom11computeAABBEv`.
Status: WRITTEN, BUILT (see 9.5), exercised at boot only if a car spawns
(bots cannot earn streaks), so the collide path itself is NOT yet LIVE.

### 9.2 `unlink` never released remote control

`Scr_AddMethod("unlink", ScrCmd_Unlink)` was the retained tag unlink only.
`CODOL_PlayerLinkUnlinkReceiver` (which exits remote control and notifies
`exit_vehicle` on player and vehicle, like T5 `VEH_UnlinkPlayer`) was written
for a registration wrapper that did not exist. `owner Unlink()` in the RC
script therefore never ended the ride, and the T5 `rcbomb_done` contract was
unreachable. Added `CODOL_Scr_Unlink` (`src/codol/vehicle/
codol_remote_vehicle.cpp`) and registered it under `CODOL_SERVER` at
`src/scr_vm_main.c:752`. Status: WRITTEN, BUILT.

### 9.3 `_rcbomb.gsc`: the eleven T5 functions and three helpers

`scripts/codol/maps/mp/killstreaks/_rcbomb.gsc` now follows the T5 structure
end to end. Ported from T5-STEAM-GSC `maps/mp/_rcbomb.gsc`:
`givePlayerControlOfRCBomb`, `updateRulesOnEnd`,
`updateKillstreakOnDisconnect`, `updateKillstreakOnDeletion`,
`carDeathWaiter` (kept unthreaded, as T5), `detonateIfTouchingSphere`,
`detonateAllIfTouchingSphere` (koth radio consumer), `RCCarAllowFriendlyFireDamage`,
`loadTreadFx` (six C1-shipped variants per surface; the bare
`fx_treadfx_rcbomb_<type>` is not in the C1 inventory and is not requested),
`rcbomb_debug_box` (drawn through the registered `line`; `box` is not a
builtin here), `rcbomb_debug_line`. Imported T5 script helpers with
attribution: `vector_scale`, `spread_array_thread`, `freeze_player_controls`.
The use function now blocks on `rcbomb_done` exactly like T5, so the
dispatcher's activation lock covers the whole ride.

Adapters re-pointed: `_killstreakrules` -> `_rcbomb_rules`;
`_weaponobjects` -> `_rcbomb_watchers` (now also carries T5's respawn hook:
`weapon_object_destroyed` + object deletion, and the
`allowFriendlyFireDamageOverride` consumer from `_globallogic_vehicle`);
`_hostmigration::waitLongDurationWithHostMigrationPause` is the mounted IW4
copy. Deliberate deviations, each commented in the script: a refused
`killstreakStart` deletes the freshly spawned car instead of leaving it for
respawn; `updateKillstreakOnDeletion` also notifies `rcbomb_done` because the
native remote link is released silently at respawn (no `exit_vehicle`), which
would otherwise hold the dispatcher lock for the match; the disconnect waiter
captures the rule claim before the entity is freed.

Not emulated (no counterpart on this server, none invented): `_treadfx` tag
consumer, `_hud::fadeToBlackForXSec`, per-viewer `setEnemyModel`, the T5
explosion sound alias (absent from the C1 inventory), `_medals`/`_properks`/
`_rank` destroyer credit (the single `destroyed_killstreak` notify carries it).
Status: WRITTEN; static gate `tools/codol_script_resolve.py --only
maps/mp/killstreaks` exits 0 against the isolated root with the init line
enabled (all four `_rcbomb` files reachable).

### 9.4 Enable steps for the live root

The live root's gate line at `_killstreaks.gsc:44` stays commented. To enable:

1. Deploy a binary built from this source (it carries the `_collision_kernel`
   fix, `CODOL_Scr_Unlink` and `spawnvehicle`).
2. Uncomment `thread maps\mp\killstreaks\_rcbomb::init();` at
   `scripts/codol/maps/mp/killstreaks/_killstreaks.gsc:44`.
3. `python tools/collate_gsc.py` then
   `python tools/codol_script_resolve.py --only maps/mp/killstreaks --binary bin/<deployed>.exe`
   (must exit 0).
4. Restart on the live port, earn or `scr_givekillstreak` an RC-XD from a C1
   client, and check `qconsole.log` for `RC physics construction failed`,
   `Native ground vehicle physical frame failed`, or a dump.

### 9.5 Isolated build and boot

Build `make -j12 -k OS=Windows_NT CC=i686-w64-mingw32-gcc CPP=i686-w64-mingw32-g++
AR=i686-w64-mingw32-ar OBJ_DIR=obj/rcxd-win32 TARGETNAME=codol_rcxd
bin/codol_rcxd.exe`, log `obj/build-rcxd-20260915.log`: every file this
pass touched compiles (`_collision_kernel.o`, `codol_remote_vehicle.o`,
`scr_vm_main.o`, `msg.o` after player.h was restored). **The link did NOT
complete** because of other workers' in-flight, untracked files:
`src/codol/weapon/codol_weapon_give.c` (undefined `CODOL_WeaponOwned`,
`CODOL_WeaponOwnedSet`) and `src/codol/player/codol_actor_{lifecycle,scripts,
spawn,spawn_fields}.cpp` (C++-mangled references to `G_Spawn`, `COM_Parse`,
`CopyArray`, `ScrCmd_GetEye`, `PlayerCmd_GetVelocity`: missing `extern "C"`).
So: NOT BUILT into a binary, and the isolated boot on udp/17743 did NOT run.
Everything for it is staged and ready: launcher
`<scratchpad>/START-RCXD-ISOLATED.cmd`, isolated home `<scratchpad>/rcxd-home`
(own `main/`, waypoints, collated root with the `_rcbomb::init()` line
enabled - resolver gate exit 0), reference copy `<scratchpad>/rcxd-ref`
(securitykey.bin + resources), `+set scr_codol_bots 4 +map mp_rust`. Once the
tree links, run that launcher, then re-run
`tools/codol_script_resolve.py --only maps/mp/killstreaks --binary bin/codol_rcxd.exe`
and watch `rcxd-home/main/qconsole.log` for several minutes for `Sys_Error`,
`RC physics construction failed`, `Native ground vehicle physical frame
failed` or a dump. Bots cannot earn killstreaks, so the RC-XD use itself
(spawn, drive, collide path of 9.1, detonate, cleanup) needs a C1 client.
Status summary: ODE fix WRITTEN, unlink wrapper WRITTEN, scripts WRITTEN +
statically gated; nothing BUILT-TESTED or LIVE.
