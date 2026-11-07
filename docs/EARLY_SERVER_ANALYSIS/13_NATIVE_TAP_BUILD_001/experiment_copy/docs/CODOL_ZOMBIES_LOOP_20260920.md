# CoDOL Zombies — the gameplay loop, ported from T5

2026-09-20. Owner of this change: `bin/home/codol_rawfiles/zm/**` only. No
`src/**` file and no shared-tree file was touched. Native and shared-tree
work that this port wants is handed back as §8, not applied.

Predecessors: `docs/CODOL_ZOMBIES_STARTUP_20260915.md` (what the zones and the
MapEnts declare, and the gap list this closes most of) and
`docs/CODOL_ACTOR_SPECIES_20260920.md` (the zombie actor species and the
animation wall).

---

## 1. What this is

Before this change `zm/maps/mp/gametypes/_zombiemode.gsc` was a boot chain:
load, publish a gamestate, accept a player, do not fatally error. Rounds, the
points economy, barricades, the power switch, the mystery box, perk machines,
downs and revives did not exist.

They exist now, as eight new modules plus a rewritten core, 4,875 lines of GSC
under `zm/`, ported from `D:\CoD\COD-GSC-Source\T5-STEAM-GSC\maps`.

| File | Lines | Ported from |
|---|---|---|
| `zm/maps/mp/gametypes/_zombiemode.gsc` (rewritten) | 723 | `_zombiemode.gsc` init_levelvars / round_start / round_think / round_wait / round_pause / player_damage_override |
| `zm/maps/mp/gametypes/_zombiemode_utility.gsc` | 615 | `_zombiemode_utility.gsc` + the `common_scripts\utility` helpers it needs |
| `zm/maps/mp/gametypes/_zombiemode_score.gsc` | 350 | `_zombiemode_score.gsc` |
| `zm/maps/mp/gametypes/_zombiemode_spawner.gsc` | 519 | `_zombiemode_spawner.gsc` (budget half) + `_zombiemode.gsc` round_spawning |
| `zm/maps/mp/gametypes/_zombiemode_blockers.gsc` | 742 | `_zombiemode_blockers.gsc` |
| `zm/maps/mp/gametypes/_zombiemode_weapons.gsc` | 690 | `_zombiemode_weapons.gsc` |
| `zm/maps/mp/gametypes/_zombiemode_perks.gsc` | 477 | `_zombiemode_perks.gsc` |
| `zm/maps/mp/gametypes/_zombiemode_laststand.gsc` | 468 | `_laststand.gsc` + `_zombiemode.gsc` player_laststand |
| `zm/maps/mp/gametypes/_zombiemode_power.gsc` | 124 | `zombie_theater.gsc:346-413` electric_switch / wait_for_power |

All LF, matching the existing zm set. Every file carries a header naming, by
T5 function and line, what was taken and what was left out and why; this
document does not repeat those lists, it summarises them.

---

## 2. T5 inventory, and what was taken

`D:\CoD\COD-GSC-Source\T5-STEAM-GSC\maps` carries 68 `_zombiemode*.gsc` files.
The ones that matter to the five priorities, with the disposition:

| T5 file | Lines | Disposition |
|---|---|---|
| `_zombiemode.gsc` | 6,571 | **Taken in part** — init_levelvars, round_start, round_think, round_wait, round_pause, ai_calculate_health, default_max_zombie_func, round_spawning, round_spawn_failsafe, award_grenades_for_survivors, player_laststand, checkForAllDead, end_game |
| `_zombiemode_score.gsc` | 728 | **Taken whole**, minus the team pot (dead in T5 itself since 2010-03-10) |
| `_zombiemode_blockers.gsc` | 3,431 | **Taken in part** — barriers, purchasable doors, debris, flag blockers |
| `_zombiemode_spawner.gsc` | 5,030 | **Taken in part** — the budget, the actor's data fields, the death event |
| `_zombiemode_weapons.gsc` | 3,106 | **Taken in part** — the weapon table, the mystery box, wall buys |
| `_zombiemode_perks.gsc` | 2,118 | **Taken in part** — perk machines and Pack-a-Punch |
| `_zombiemode_utility.gsc` | 3,941 | **Taken in part** — the ~40 helpers the above call |
| `_laststand.gsc` | 1,028 | **Taken in part** — down, bleedout, revive trigger |
| `zombie_theater.gsc` (power) | — | **Taken** — T5 has no shared power module; every level carries the same copy |
| `_zombiemode_powerups.gsc` | 3,048 | **Not taken** — see §6 |
| `_zombiemode_zone_manager.gsc` | 807 | **Not taken** — see §6 |
| `_zombiemode_audio.gsc`, `_zombiemode_money.gsc`, `_zombiemode_net.gsc`, `_zombiemode_timer.gsc`, `_zombiemode_load.gsc`, `_zombiemode_ffotd.gsc`, `_zombiemode_devgui.gsc`, `_zombiemode_server_throttle.gsc`, `_zombiemode_sidequests.gsc`, `_zombiemode_deathcard.gsc` | — | Not taken; support/telemetry/dev, or backends this server has none of |
| `_zombiemode_ai_{ape,astro,director,dogs,faller,monkey,napalm,quad,sonic,thief}.gsc`, `_waw_zombiemode_ai_japanese.gsc` | — | **Not taken — animation workstream.** Every one is an animscript species |
| `_zombiemode_weap_*.gsc` (13 files: tesla, thundergun, freezegun, crossbow, shrink_ray, microwavegun, humangun, black_hole_bomb, cymbal_monkey, nesting_dolls, quantum_bomb, sickle, sniper_explosive) | — | Not taken; the guns are in the box as ordinary weapons, their special behaviours are not |
| `_zombiemode_hackables_*.gsc` (7), `_zombiemode_equip_*.gsc`, `_zombiemode_traps.gsc`, `_zombiemode_auto_turret.gsc`, `_zombiemode_betty.gsc`, `_zombiemode_bowie.gsc`, `_zombiemode_claymore.gsc`, `_zombiemode_jump_pad.gsc`, `_zombiemode_player_zipline.gsc`, `_zombiemode_powercell.gsc`, `_zombiemode_spikemore.gsc` | — | Not taken; out of scope for the five priorities |

---

## 3. The five priorities

### 1. Round progression — **COMPLETE**

`_zombiemode.gsc::round_think` is T5's loop, in T5's order: raise the barricade
reward cap to `min(50 × round, 500)` (T5's own DT#36173 rule), publish the
round HUD, reset every player's per-round reward, top up grenades, start the
spawner, `notify("start_of_round")`, wait, `notify("end_of_round")`, decay the
spawn delay by 5% floored at 0.08 s, raise the move speed by
`round × zombie_move_speed_multiplier`, increment the round, wait
`zombie_between_round_time`, `notify("between_round_over")`.

T5's three override hooks (`level.round_spawn_func`, `level.round_wait_func`,
`level.round_think_func`) are kept so a per-map script can replace any one of
them.

The spawn budget is `_zombiemode_spawner::round_spawning`, arithmetic
unchanged from T5: `zombie_max_ai` plus `zombie_ai_per_player` scaled by
`round/5`, times an extra `round × 0.15` past round 10, then through
`default_max_zombie_func`'s round 1-6 ramp (25% / 30% / 50% / 70% / 90%).
Health is `ai_calculate_health`: `zombie_health_start`, plus
`zombie_health_increase` per round to round 9, compounding by
`zombie_health_increase_multiplier` from round 10.

**Round HUD**: C1's own. `setClientDvar("ui_hud_round", <n>)`, renderer
`0x00461A71`, MEASURED rendering live under the previous server
(`alpha0022/docs/zombies_gameplay_plan.md:312-321`). T5's chalk-mark HUD is
deliberately not ported — it `SetShader`s `hud_chalk_1`..`_5`, WaW materials
that no CoDOL zone carries.

All 33 `level.zombie_vars` rows T5's `init_levelvars` sets are set here, read
through `tableLookup("mp/zombiemode.csv", 0, <row>, 1)` first exactly as T5
reads them, defaulting to T5's own literals when the row is absent.

### 2. Points economy — **COMPLETE**

`_zombiemode_score.gsc` is T5's file minus the team pot. Award on damage
(`zombie_score_damage_normal`, ×1.25 while the attacker is aiming down sights),
award on kill (`zombie_score_kill_<n>player` plus T5's hit-location bonus:
head 50, neck 20, torso 10, melee 80, burn 10), `round_up_score(points, 5)`,
spend through `minus_to_player_score`, and T5's three penalties
(`penalty_downed`, `penalty_died`, `penalty_no_revive`).

Damage and kill awards are driven from the actor's `"damage"` and `"death"`
notifies (`_zombiemode_spawner::zombie_damage_watch` /
`zombie_death_event`) rather than T5's `level.callbackActorDamage`, which this
server does not expose to GSC. `src/codol/player/codol_actor_lifecycle.cpp:1568`
records that the generic `G_Damage` path already sends those notifies.

The score readout is a server hudelem, plus T5's floating `+50`
(`score_highlight`, `create_highlight_hud`). It has to be: MEASURED, an
exhaustive sweep of all 23,124 C1 strings found no zombies points widget at all
(`alpha0022/docs/zombies_mode.md:1088-1148`); `ZOMBIE_ROUND` is the only
zombies HUD element C1 has. A budget guard stops the floating deltas from
starving the hudelem pool.

**Team pot not ported, on purpose.** T5 disabled it itself on 2010-03-10:
`add_to_team_score`'s body is entirely commented out and `set_team_score_hud`
zeroes the pool. Every purchase path here takes T5's solo branch, which is the
only branch that ever moves points in T5 as shipped.

### 3. Barricades — **COMPLETE, with one flagged adaptation**

`_zombiemode_blockers.gsc` ports `blocker_init`, `blocker_attack_spots`,
`blocker_think` and the whole of `blocker_trigger_think` — the
repair-for-points loop: a `trigger_radius` at the barrier's
`trigger_location`, hold use, one board per second, `cost` (default 10) per
board, capped per round at `rebuild_barrier_cap_per_round`.

Purchasable doors (`door_init`, `door_classify`, `door_buy`, `door_think`
including `electric_door` / `electric_buyable_door`, `door_activate` for
rotate / move / slide_apart, `door_opened`'s `script_flag` fan-out) and
purchasable debris (`debris_init`, `debris_think`, `debris_move`) are ported
with them, as is `flag_blocker`.

**THE ADAPTATION.** In T5 a zombie tears a board off a window from an
ANIMATION NOTETRACK. With no notetracks nothing would ever remove a board and
the repair economy could never pay out, so
`blocker_zombie_tear_watch()` removes one chunk per `zombie_board_tear_delay`
seconds while a zombie stands in the barrier's attack spots. **The trigger is
invented; the effect is T5's** — `remove_chunk` is the ported function. When
the animation workstream lands notetracks: delete
`blocker_zombie_tear_watch` and call `remove_chunk` from the notetrack.
Nothing else in that file changes.

### 4. Mystery box and perk machines — **COMPLETE**

**Mystery box** (`_zombiemode_weapons.gsc`): `treasure_chest_init`,
`get_chest_pieces` (use trigger → `chest_lid` → `chest_origin` → `chest_box`,
the exact T5 chain, and the exact targetnames the CoDOL MapEnts author),
`treasure_chest_think` (pay 950, roll, grab-or-timeout at 12 s, close),
`treasure_chest_weapon_spawn` (T5's 40-cycle mario-kart roll with its
slowdown schedule, driving a floating `script_model` set to
`getWeaponModel()`), `treasure_chest_ChooseWeightedRandomWeapon` (filters to
in-box weapons the player does not already own), `treasure_chest_lid_open` /
`_close` (a `RotateRoll`, not an animation, so it ports verbatim), and
`treasure_chest_give_weapon`. A roll that resolves to nothing refunds the spend
without crediting the lifetime total, which is T5's own teddy-bear refund rule.

**The weapon table is CoDOL's content, T5's contract.** T5's `init_weapons`
names `ak74u_zm` / `mp40_zm` / `ray_gun_zm`. MEASURED from
`docs/zone_assets/ALL_weapon.txt`: CoDOL's zm zones carry a *different* 163-name
set in `common_gametype_zm` / `patch_common_gametype_zm`, using the same
`<base>_zm` / `<base>_upgraded_zm` pairing. So `add_zombie_weapon` is T5's,
the cost tiers are T5's, and the names are the ones the client can build —
39 weapons, each validated at init by `precacheItem` +
`getWeaponIndexFromName` so anything absent drops out of the pool instead of
producing a roll the client cannot render.

**Wall buys**: `init_weapon_upgrade` + `weapon_spawn_think`, keyed off the
map's own `weapon_upgrade` triggers and their `zombie_weapon_upgrade` key.
First purchase gives the gun and reveals the wall model; afterwards the same
trigger sells ammo, at 4500 for an upgraded weapon and the weapon's own
`ammo_cost` otherwise — T5's rule.

**Perk machines** (`_zombiemode_perks.gsc`): `vending_trigger_think` with
T5's per-perk cost ladder (Juggernog 2500, Quick Revive 1500 / 500 solo,
Speed Cola 3000, Double Tap 2000, Stamin-Up 2000, PhD 2000, Deadshot 1000,
Mule Kick 4000), the power gate, T5's four refusals (already have it, too
poor, four perks already, in a revive trigger), the perk bottle weapon
(`zombie_perk_bottle_*`, all present in `common_gametype_zm`),
`give_perk` (SetPerk + the Juggernog health bump + the solo quick-revive
life) and `perk_think` (perks are lost on down or death).

**Pack-a-Punch**: `vending_weapon_upgrade`. Real, not a stand-in — it resolves
the held weapon's `_upgraded_zm` variant through the same table, refuses
without charging when the held weapon has no upgrade in any mounted zone,
otherwise charges 5000, takes the gun, waits `packapunch_timeout` and hands
back the upgrade with full ammo.

**Power switch** (`_zombiemode_power.gsc`): `use_elec_switch` trigger,
`elec_switch` lever (a `RotateRoll`), flag `power_on`, and the one-network-frame
notify fan-out that releases the perk machines and the electric doors. A map
with no switch opens power immediately rather than locking every machine
behind an entity that does not exist.

### 5. Downs and revive — **COMPLETE as script; the native path is a handback**

`_zombiemode_laststand.gsc` ports T5's down: `downs++`, health clamped to 1,
the offhand disable, `penalty_downed`, the weapon strip, the last-stand
pistol, the linked `trigger_radius`, the bleedout timer, and
`revive_trigger_think` — another player in the trigger, facing the downed
player (T5's `is_facing`, dot > 0.4), holding use for `zombie_revive_time`,
cancellable. A revive restores health, weapons, movement and the offhand, and
pays the reviver T5's `"reviver"` points event.

**This is a script-side down, and it did not have to be.** This server *has* a
native last stand — `src/codol/script/codol_script_laststand.c` documents the
whole thing: the retained damage path enters last stand on a lethal hit, sets
`gclient.lastStand` plus a 500 ms grace deadline, calls
`CodeCallback_PlayerLastStand`, forces `ps.pm_type 7`, and `laststandrevive()`
clears it. But `CODOL_LastStand_CanEnter` (that file, :100-110) gates entry on
`state->abilities.masks[0] & 0x00800000` — C1 ability bit 23, `modPistolDeath`,
in the playerState extension — and nothing in GSC sets that bit. So the down is
entered from `Callback_PlayerDamage`, which vetoes the lethal hit.
`Callback_PlayerLastStand` is wired to the **same function**, and
`revive_success` calls `laststandrevive()` unconditionally, so publishing that
ability bit natively (§8) moves the down into the engine with zero script
change.

---

## 4. Builtins this port needs that the server does not register

MEASURED 2026-09-20 against the 929 names `tools/codol_script_resolve.py`
extracts from `src/`, cross-checked against `bin/codol_dedrun_next.exe`.
**None of these is called by any shipped file** — a GSC call to an
unregistered builtin is a compile-time error that kills the match at map load,
so each one is worked around and the workaround is named in the owning file's
header. This is the list for the parent to reconcile with the animation
workstream.

### 4a. Animation — the other workstream's, and the reason for §5

`%anim` tokens, `setanim`, `setanimknob`, `setflaggedanimknoball`,
`animscripted`, `useanimtree`, `animcustom`, `DoNoteTracks`.

### 4b. AI / actor

| Name | Wanted by | Worked around by |
|---|---|---|
| `GetAiSpeciesArray` / `GetAiArray` | `get_enemy_count` | the spawner keeps `level.zombies` and counts it |
| `ConnectPaths` / `DisconnectPaths` | doors, debris, barrier clips | not called; `setGoalPos` is recomputed every second instead |
| `setGoalRadius`, `setGoalEntity`, `allowedStances`, `setTeamForEntity`, `PushPlayer`, `setThreatBiasGroup`, `findpath` | `zombie_spawn_init`, `find_flesh` | omitted; the fields that do exist natively are set |

### 4c. Player / HUD

| Name | Wanted by | Worked around by |
|---|---|---|
| `SetMaxHealth` | Juggernog, zombie health | `self.maxhealth` / `self.health` written directly |
| `VisionSetLastStand` | the downed vision blend | absent |
| `setClientSysState` | the client `"lsm"` last-stand state | absent |
| `AllowLean`, `AllowMelee`, `AllowCrouch`, `AllowProne` | the drink clamp and the downed clamp | `AllowAds` / `AllowSprint` / `AllowJump` / `setStance` / `setMoveSpeedScale`, which are registered |
| `setblur` | `give_perk`'s drink flash | absent |
| `SetInvisibleToPlayer` / `setVisibleToPlayer` / `setVisibleToAll` | per-player machine and box visibility | absent; triggers are global |
| `useweaponhidetags` | the floating box weapon model | plain `setModel(getWeaponModel(name))` |
| `clientnotify` | power-on client FX (`"ZPO"`) | absent; there is no CSC VM |
| `isThrowingGrenade`, `isSwitchingWeapons`, `isnotarget`, `depthinwater`, `iscarrying` | purchase-path guards | those guards are dropped |
| `setClientField` / `setOmnvar` | T5 client fields | absent |

### 4d. Script helpers that are engine builtins in T5 but not here

`getstruct` / `getstructarray`, `getClosest`, `vector_scale`,
`array_randomize`, `waittill_any` / `waittill_any_return`,
`wait_network_frame`, `TriggerEnable`, `random`. All reimplemented in
`_zombiemode_utility.gsc`, each with its provenance noted. `TriggerEnable` in
particular: T5 does not have it either and disables a trigger by dropping it
10,000 units, which is what is done here.

---

## 5. What was deliberately left out for the animation workstream

By file and function, so the other worker can find them:

**`_zombiemode_spawner.gsc`** — `zombie_setup_attack_properties` (:3899), the
animscript handoff inside `zombie_think` (:415), `set_zombie_run_cycle`,
`zombie_gib_on_damage`, `zombie_head_gib`, `zombie_eye_glow` /
`delayed_zombie_eye_glow`, `zombie_death_animscript`, `make_crawler`,
`do_zombies_playvocals` / `play_ambient_zombie_vocals`.

**`_zombiemode.gsc`** — `init_standard_zombie_anims` (:1057), `init_anims`
(:1366), `init_animscripts` (:1372), `zombify_player` (:4187) and the whole
playable-zombie state machine, `injured_walk` / `limp` / `stumble`
(:5314-:5380).

**`_zombiemode_blockers.gsc`** — the `"anim"` door style
(`door_classify` :195, `door_activate` case `"anim"`,
`door_solid_thread_anim` :890, `level.blocker_anim_func`); every
`zombie_boardtear_*` / `zombie_bartear_*` / `zombie_gratetear_*` audio-plus-FX
offset function (:2105, :2155, :2605, :2642, :2680, :2737, :2792), which are
exactly the functions T5 drives from notetracks.

**`_zombiemode_perks.gsc`** — `third_person_weapon_upgrade` (:283),
`do_knuckle_crack` / `upgrade_knuckle_crack_begin` / `_end`
(:611, :624, :663): the Pack-a-Punch presentation rig.

**`_laststand.gsc` / `_zombiemode.gsc`** — the revive syrette's third-person
animation and the downed pose (T5 gets the pose from `ps.pm_type 7`, not from
an animation, so that half is a native handback rather than an animation one).

**MELEE IS A HOLE.** T5 zombies damage players from an animscript notetrack.
No notetracks means a zombie that reaches a player does nothing. No fake
proximity-damage timer was shipped in its place, because that would be
invented gameplay rather than a port. The barricade tear (§3.3) is the one
place where a notetrack was replaced, and only because the repair economy
is unreachable without it.

---

## 6. Other things not ported, and why

- **Power-ups** (`_zombiemode_powerups.gsc`, 3,048 lines). The pickups exist
  as content — `kis_insta_kill_zm`, `kis_nuke_zm`, `kis_double_points_zm`,
  `kis_carpenter_zm`, `kis_max_ammo`/`kis_full_ammo_zm`, `kis_fire_sale_zm`
  and nine more are all in `common_gametype_zm` — and
  `_zombiemode_score.gsc` already honours
  `zombie_vars["zombie_powerup_insta_kill_on"]` and the
  `"bonus_points_powerup"` / `"nuke_powerup"` events. What is missing is the
  drop-and-collect module. This is the single highest-value follow-on that
  needs no animation work at all.
- **Zone manager** (`_zombiemode_zone_manager.gsc`). It gates which spawners a
  round may use by which zones the players have opened. Without it every
  authored spawn point is live from round 1. The maps author the zones
  (`start_zone`, `upstairs_zone`, `box_zone`, `final_zone` and their
  `*_spawners` groups), so this is a clean follow-on.
- **Mystery box relocation** (the teddy bear). Needs the `zombie_teddybear`
  model and a fly-away; the box stays where the map put it.
- **Spectators / between-round respawn of dead players.** A dead player waits
  on the round boundary (`level waittill("between_round_over")`) instead of
  T5's spectator path.
- **Stats, leaderboards, `bbPrint`, the intermission screen.** No backend.
- **The zm scoreboard.** Still the gap `CODOL_ZOMBIES_STARTUP_20260915.md`
  records: C1 uses a different format under `zm` (command `4`, seven
  ints/row). `self.downs` and `self.revives` are now maintained by this port,
  so the writer has something to send.

---

## 7. Gate results

Both gates clean, run with the deployed binary:

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles/zm --root bin/home/codol_rawfiles \
  --seed maps/mp/gametypes/zm.gsc --seed maps/mp/zm_prototype_sh.gsc \
  --seed maps/mp/zm_zombie_training.gsc --seed maps/mp/zm_asylum_sh.gsc \
  --binary bin/codol_dedrun_next.exe

  builtins registered: 929
  validated against binary: bin/codol_dedrun_next.exe (0 source registrations absent from it)
  scripts in effective tree: 1196
  scripts the loader would lower: 119
  every reachable script resolves against the registered builtin table
```

`119` lowered, up from `111` before this change: the eight new modules. No
file outside `zm/` entered the closure — in particular `common_scripts/utility`
is *not* pulled in by anything written here (its four-file closure was measured
and then deliberately not used, because the shared tree is load-bearing for the
user's live multiplayer matches).

Multiplayer unchanged:

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --seed maps/mp/gametypes/war.gsc \
  --binary bin/codol_dedrun_next.exe

  scripts the loader would lower: 108
  every reachable script resolves against the registered builtin table
```

The gate's sensitivity was verified rather than assumed: a deliberate
`this_builtin_does_not_exist()` / `this_local_fn_does_not_exist()` pair was
appended to `_zombiemode_power.gsc`, the gate reported both as
`unknown function` with their call-site counts, and the probe was removed.

Also checked mechanically: no module defines a function name that collides
with one in `_zombiemode_utility.gsc` (which every module `#include`s), and no
module defines the same function twice — either would be a duplicate-symbol
compile error the gate does not model.

**NOTHING HERE HAS RUN LIVE.** No server was started or stopped for this
change. Everything above is source-level and gate-level; the live-verify list
is §9.

---

## 8. Handbacks — native and shared-tree changes this port wants

Neither is applied. Both are outside this workstream's file ownership.

### 8a. Publish C1 ability bit 23 for a zm player (native, `src/`)

`CODOL_LastStand_CanEnter` (`src/codol/script/codol_script_laststand.c:100-110`)
gates the engine's own last stand on
`state->abilities.masks[0] & UINT32_C(0x00800000)`. If a zm player's
playerState extension carried that bit at spawn, the ENGINE would own the
down: the correct `ps.pm_type 7` movement mode, the correct 500 ms damage
grace window, and the correct wire state — all three of which the script
approximation in `_zombiemode_laststand.gsc` cannot reproduce
(`setStance("prone")` + `setMoveSpeedScale(0.15)` reads as a crawl, not a
last stand).

The script side needs no change when this lands: `Callback_PlayerLastStand`
already routes to the same `player_laststand()`, and `revive_success` already
calls `laststandrevive()`.

The one thing to decide with it: `Callback_PlayerDamage` in
`zm/maps/mp/gametypes/_zombiemode.gsc` currently vetoes the lethal hit itself.
Once the engine enters last stand on its own, that veto becomes a duplicate
and should be reduced to the already-down guard above it.

### 8b. Nothing else

No shared-tree (`bin/home/codol_rawfiles/` outside `zm/`) change is needed.
The zm tree is self-contained by construction: it has no `#include` and no
`file::function` reference outside `zm/maps/mp/gametypes/`.

---

## 9. Live-verify checklist

In order; each step's failure points somewhere different.

1. **Boot `zm_asylum_sh`.** It reached Game Initialization with a player
   connected on 2026-09-20; it must still. Expect these lines, in this order:
   `CoDOL zm: starting weapon <name>`, `CoDOL zm: <n> zombie weapons resolved
   out of the mounted zones`, `CoDOL zm: <n> barriers, <n> doors, <n> debris`,
   `CoDOL zm: <n> perk machines, <n> pack-a-punch`, `CoDOL zm: <n> mystery box
   location(s)`, `CoDOL zm: <n> wall buys`, then either `CoDOL zm: zombie
   spawner ready` or `CoDOL zm: spawnactorspawner produced no zombie spawner`.
   Those six counts are the whole answer to "does the MapEnts vocabulary this
   port assumes actually match this map".
2. **Round 1 starts.** `CoDOL zm: round 1 begins with 1 player(s)` then
   `CoDOL zm: round 1 budget <n> zombies at 150 health`. The client's round
   counter should read 回合1.
3. **Points.** The score readout should start at 500 (or whatever
   `zombie_score_start_1p` says in `mp/zombiemode.csv`) and a floating `+10`
   should appear per hit landed on a zombie.
4. **Barricade.** Let a zombie reach a window; a board should disappear within
   ~4 s, and holding use at the window should replace it one board per second
   at +10 each, stopping at the round's cap.
5. **Round advances.** Kill the round's budget; expect `round 2 begins`,
   the HUD to read 2, and the budget line to show more zombies at 250 health.
6. **Power, then a perk machine and the box.** Buy the machine's perk and
   confirm `hasPerk` behaviour (Speed Cola visibly faster reload, Double Tap
   visibly faster fire); buy a box roll and confirm the model cycles for ~5 s
   before settling.
7. **Go down.** Expect the crawl clamp, the last-stand pistol, and a 45 s
   bleedout that ends the match solo. This is the step most likely to look
   wrong, because of §8a.

The riskiest unknowns, ranked: (a) whether the CoDOL zm MapEnts really carry
`exterior_goal` structs — the doc records `zombie_barrier` by targetname and
the T5 vocabulary generally, but not `exterior_goal` specifically, and step 1's
barrier count is the test; (b) whether `spawnActor` on the zombie species works
at all, which is itself unverified in
`docs/CODOL_ACTOR_SPECIES_20260920.md` §8; (c) whether the actor `"damage"` /
`"death"` notifies carry the parameters this port reads (INFERRED from
`codol_actor_lifecycle.cpp:1568` and from the dog's own
`waittill("death", attacker)`, not measured).
