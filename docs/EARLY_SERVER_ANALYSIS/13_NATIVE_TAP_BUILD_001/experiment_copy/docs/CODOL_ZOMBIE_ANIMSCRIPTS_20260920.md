# CoDOL Zombies: the animation scripts, and the power-up module

2026-09-20. Owner of this change: `bin/home/codol_rawfiles/zm/**` only. No
`src/**` file and no shared-tree file was touched.

Predecessors, in the order they have to be read:
`docs/CODOL_SCRIPTED_ANIMATION_20260920.md` (the twenty animation builtins and
the notetrack producer), `docs/CODOL_ZOMBIES_LOOP_20260920.md` (the gameplay
loop, and §5's list of what it deferred to this task),
`docs/CODOL_ACTOR_SPECIES_20260920.md` (the zombie actor species).

Every claim is labelled **MEASURED** (read out of source, `C1.exe`, the
shipped zone data, or a tool run) or **INFERRED**.

---

## 1. Verdict up front

1. **The animation path is real and every deferred item in
   `CODOL_ZOMBIES_LOOP_20260920.md` §5 is now live**, except three that are
   named in §6 with the specific builtin or the specific shipped asset that
   blocks them. Nine parked animscript stubs became nine ported modules plus a
   new notetrack module.
2. **The invented barricade timer is gone.** `blocker_zombie_tear_watch()` is
   deleted. A board now comes off only when the tear animation's `"board"`
   notetrack fires, which is T5's own mechanism, and `remove_chunk` on the
   other side of it is still T5's.
3. **Melee is real.** T5's attack clips are played with
   `setflaggedanimknoballrestart` and the damage is landed on their `"fire"`
   notetrack through the registered `melee()` method, which is the exact
   mechanism T5 uses. No proximity timer was shipped.
4. **The biggest finding of this task is §2: the animtree the server parses is
   CoDOL's, not the vendor IW4 copy in our own tree**, and CoDOL's carries 386
   `ai_zombie_*` nodes. Without establishing that, every `%anim` in this batch
   would have been a guess; with it, all 108 distinct tokens are verified.
5. **Piece 2 landed.** `_zombiemode_powerups.gsc` (712 lines) drops and
   collects ten of the fifteen shipped pickups. The other five are excluded
   from the bag with the reason, not dropped as duds.
6. All three gates are clean; the mp gate is unchanged at 108 lowered (§8).

---

## 2. Which `generic_human.atr` is live — MEASURED, and it is not the obvious one

This had to be settled before a single `%anim` could be written.

* `bin/home/codol_rawfiles/animtrees/generic_human.atr` is the **vendor IW4**
  tree: 4,681 lines, **zero** `ai_zombie` nodes. It is also outside this
  task's file ownership.
* MEASURED, `src/cscr_parser.cpp:567`: `Scr_ReadFile` intercepts any path
  beginning `animtrees/` and returns the **mounted CoDOL archive's** copy,
  falling back to the script roots only when no archive defines the tree. Its
  own comment says why — "C1 ships its own `animtrees/*.atr` as rawfiles".
* MEASURED, `docs/zone_assets/ALL_animtree.txt`: `animtrees/generic_human.atr`
  ships in `common_mp` **and** `patch_common_mp`.
* Corroboration that this path is actually taken on this server: with
  `com_developer` set the same function dumps the mounted copy to
  `codol_animtrees/`, and `bin/home/codol_animtrees/dog.atr` exists (1,980
  bytes) while the vendor tree also has a `dog.atr`. The dump only happens on
  the mounted-archive branch.

So the tree was extracted from the fastfiles with the measured reader
(`tools/codol_zone_assets.py`'s `zone_assets.py --extract`, rawfile type 36):

| zone | bytes | lines | distinct `ai_zombie_*` nodes |
|---|---|---|---|
| `common_mp` | 123,522 | 5,341 | 386 |
| `patch_common_mp` (effective) | 123,640 | 5,345 | 386 |

The patch adds four leaves over the base (three `stand_and_crouch` entries and
one `zombie_test`) and is otherwise identical.

Two structural facts that change the port:

* **The single top-level node is `body`.** There is **no node named `root`**
  anywhere in the file. T5 writes `%root` as the knob-all root anim and as the
  `ClearAnim` target in `zombie_stop`, `zombie_death` and `zombie_melee`;
  `%root` would not compile here. **C1 wins: every `%root` became `%body`.**
  This is also the only legal knob-all root on this server, because
  `CODOL_SCRIPTED_ANIMATION_20260920.md` §4.2 refuses a root anim that has a
  parent, and `body` is the one node with none.
* The `ai_zombie_*` leaves are **not** confined to a `zombie` subtree. 186 sit
  under `body/scripted/zombie`, the rest are spread over seven other places
  under `body/scripted` (69 under `combatrun_forward`, 58 directly under
  `scripted`, 46 under `melee`, …). That does not affect GSC — `%name`
  resolves by name, not by path — but it is why a `zombie`-subtree-only search
  under-counts.

The extracted trees are at `%TEMP%\codol_generic_human_extract.atr` and
`…extract.patch.atr`.

---

## 3. The animation palette, and every place C1 beat T5

**A `%name` in the tree with no shipped xanim behind it compiles and then
animates nothing.** The script gate does not check `%anim` names at all, so
this is a class of failure no gate would have caught. The palette is therefore
the intersection of two measured sets:

1. the 386 `ai_zombie_*` nodes in the extracted `patch_common_mp` tree;
2. `docs/zone_assets/ALL_xanim.txt` restricted to the zones a zm match mounts
   — `common_mp`, `patch_common_mp`, `common_gametype_zm`,
   `patch_common_gametype_zm`, `zm_asylum_sh`, `zm_prototype_sh`,
   `zm_zombie_training`.

**225 of the 386 tree nodes have a shipped xanim in a zm match.** 209 of those
come from `common_gametype_zm`, 19 more only from `zm_prototype_sh`.

All 108 distinct `%` tokens used anywhere in `zm/**` were re-checked against
both sets after the last edit: **0 missing from the tree, 0 missing an xanim**
(the only two tokens with no xanim are `%body` and `%walk_and_run_loops`, which
are blend nodes and correctly have none).

### 3.1 C1-vs-T5 conflicts, and which side won

Recorded as the mandate requires. **C1 won all of them.**

| # | T5 says | CoDOL says | Resolution | Where |
|---|---|---|---|---|
| 1 | `%root` is the knob-all root and the `ClearAnim` target | no `root` node exists; the sole top-level node is `body` | use `%body` everywhere | `zombie_combat/_death/_stop/_move/_flashed/_jump`, spawner tear |
| 2 | `run5` = `%ai_zombie_run_v4` | node exists, **no xanim ships** | `%ai_zombie_run_v1`, which does ship — and which T5's own source has commented out one line above | `_zombiemode.gsc::init_standard_zombie_anims` |
| 3 | the idle set is `%ai_zombie_idle_v1_delta` (weighted `anim.idleAnimArray`) | node exists, **no xanim ships** | `%ai_zombie_idle_v1` | `zombie_stop.gsc`, tables |
| 4 | board taunts include `%ai_zombie_taunts_1/_3/_6/_8` | no xanim for any of the four | dropped; the remaining eight are T5's own board-taunt list | tables |
| 5 | the metal-bar barricade (`%ai_zombie_bartear_*`, `%ai_zombie_bar_bend_*`, the `"bar_bend"` notetrack) | all 36 bartear nodes declared, **none ships an xanim** | the bar variant does not exist in CoDOL; only the wood-board tear is ported, and the `"bar_bend"` notetrack arm is dropped | `_zombiemode_blockers.gsc`, spawner tear |
| 6 | eye glow is `self haseyes(1)`, a native toggle over `level._effect["eye_glow"]` | `haseyes` is **not a registered builtin**; the FX T5 toggles, `misc/fx_zombie_eye_single`, **is** shipped in `common_gametype_zm` under T5's own name | play the shipped FX on `tag_eye` with `playFxOnTag` | `_zombiemode_spawner::zombie_eye_glow` |
| 7 | the tear FX is `level._effect["wood_chunk_destory"]` | CoDOL ships **no** wood-chunk destruction effect at all | **substitution, flagged as such**: `impacts/fx_large_woodhit` (`common_gametype_zm`), the nearest shipped wood-debris burst. Every use is guarded, so deleting the line degrades the tear to silent geometry | `_zombiemode_blockers.gsc` |
| 8 | power-ups are `p_zom_*` **xmodels** passed to `add_zombie_powerup` | **no** `p_zom` power-up model in any zone; the pickups ship as fifteen `kis_*_zm` **weapons** | the model comes from `getWeaponModel( <kis name> )`; the registry keys on the kis name | `_zombiemode_powerups.gsc` (§7) |
| 9 | the player's lethal hit is vetoed in script (`player_damage_override` :4544) | `CODOL_LastStand_CanEnter` gates on C1 ability bit 23, which the engine now publishes at zm spawn | the script veto is **deleted**; the engine owns the down | `_zombiemode.gsc::Callback_PlayerDamage` (§5) |
| 10 | sound notetracks are handled by script | CoDOL ships the zombie audio as `zmb_zombie_nt_*` aliases, i.e. `sndnt#` notetracks the **client** plays | the server consumes `sndnt#…` and plays nothing; playing it too would double every footstep | `zombie_shared::HandleNoteTrack` |

Conflict 10 is worth its own line, because it is positive evidence rather than
an absence. MEASURED, `docs/zone_assets/ALL_sound.txt`, `common_gametype_zm`:
`zmb_zombie_nt_vocals_attack`, `_crawl`, `_land`, `_step`, `_swing`, `_taunt`
and `zmb_zombie_nt_traverse_v1/_v2`. T5's convention is a notetrack literally
named `sndnt#<alias>` (≈200 call sites, e.g. `maps\creek_1_anim.gsc:168`), and
the `nt_` in these alias names is that marker. So CoDOL's zombie clips
demonstrably carry notetracks, and demonstrably carry them for attack, swing,
step, land, crawl, taunt and traverse.

---

## 4. What was built, file by file

### 4.1 `zm/maps/mp/animscripts/` — nine ports and one new module

| file | lines | was | is |
|---|---|---|---|
| `zombie_shared.gsc` | 243 | **new** | `DoNoteTracks`, `DoNoteTracksForTime`, `HandleNoteTrack`, the notetrack registry |
| `zombie_init.gsc` | 158 | 54, data only | `firstInit`, the per-actor `self.a` block, the sound-alias registry |
| `zombie_move.gsc` | 139 | 37, parked | `MoveMainLoop` / `MoveRun` / the stand and crawl cycles |
| `zombie_stop.gsc` | 53 | 37, parked | the idle loop |
| `zombie_combat.gsc` | 278 | 37, parked | **`MeleeCombat` — the real melee** |
| `zombie_death.gsc` | 113 | 35, parked | `self.deathanim` + ragdoll fallback + the `deathanimscript` hook |
| `zombie_pain.gsc` | 107 | 37, parked | the flinch |
| `zombie_flashed.gsc` | 44 | 37, parked | the flash reaction |
| `zombie_turn.gsc` | 36 | 37, parked | see §6 — T5 has no humanoid zombie turn either |
| `zombie_jump.gsc` | 49 | 37, parked | see §6 — pose half only |

Two adaptations inside `zombie_shared.gsc` worth restating:

* **`DoNoteTracksForTime` is inverted.** T5 runs the pump on the calling
  thread and kills it with `ent endon("stop_notetracks")` on a helper struct.
  That relies on an `endon` registered inside a *called* function unwinding
  only that function. This VM's `endon` is thread-scoped, so T5's shape would
  kill `MoveMainLoop` instead of returning to it. Ported inverted: the pump is
  the thread and carries the `endon`, the caller waits out the interval. Same
  observable behaviour, unambiguous scoping. INFERRED that the T5 shape would
  misbehave; the inverted form is correct under either semantics, which is why
  it was chosen.
* **`anim.notetracks` became `level.zombie_notetracks`.** The dog animscripts
  (`maps/mp/animscripts/dog_*.gsc`), the only animscript set proven to run on
  this server, use `level.` throughout and never touch the `anim` global
  object. This file does not become the first thing to depend on it.

### 4.2 Melee, in detail — `zombie_combat.gsc`

The loop is T5's `MeleeCombat` (`animscripts/zombie_melee.gsc:13`):

1. face the enemy (`orientmode("face angle", …)`), `animmode("zonly_physics")`;
2. `pick_zombie_melee_anim()` — T5's walk / run / crawl / stumpy selection;
3. `self.safeToChangeScript = false` — MEASURED,
   `codol_actor_lifecycle.cpp:702` and `:1397` both read it, so the native
   frame will not switch scripts out from under a swing;
4. `setFlaggedAnimKnobAllRestart("meleeanim", clip, %body, 1, 0.2, rate)`;
5. wait on `"meleeanim"`; on `"fire"` call `melee()`; on `"end"` release;
6. T5's two randomised give-up windows (`resetGiveUpTime`), then
   `CanContinueToMelee()`.

Why `melee()` is the whole answer, MEASURED:

* it is registered — `Scr_AddMethod("melee", ActorMelee, qfalse)`,
  `src/codol/player/codol_actor_lifecycle.cpp:1295`;
* `ActorMelee` is complete, not a stub: it takes the eye tag matrix, aims at
  `CODOL_ActorEnemy`, and calls `CODOL_ActorMeleeTrace`
  (`src/asmsource/_codol_actor_melee.asm`), which tail-jumps to the retained
  `Weapon_Melee_internal` — the same trace-and-damage body player melee runs;
* it requires `self.aiweapon` to name a real WeaponDef, and
  `docs/zone_assets/ALL_weapon.txt` has **`zombie_melee` in
  `common_gametype_zm`** — T5's own zombie claw name, carried into CoDOL.
  `_zombiemode_spawner::resolve_melee_weapon()` precaches it and checks
  `getWeaponIndexFromName() > 0`, falling back to `dog_bite_zm`, and assigns
  `ai.aiweapon` on every spawn. The call site is guarded so a zone without
  either prints one line per actor instead of a script error per swing.

`pick_zombie_melee_anim` differs from T5 in one mechanical way, stated in the
file: T5 uses `array_combine` to merge the standing pool with the moving pool
and picks uniformly from the union. `array_combine` is not registered and
`_zombiemode_utility` has no counterpart, so the pool is picked first with the
same size weighting and then uniformly inside it — the identical distribution.

### 4.3 `_zombiemode_spawner.gsc` — 519 → 1,222 lines

Restored from `CODOL_ZOMBIES_LOOP_20260920.md` §5:
`zombie_setup_attack_properties`, the animscript handoff in `zombie_think`,
`set_zombie_run_cycle` / `set_run_speed` / `set_run_anim`, `zombie_eye_glow` /
`_stop` / `delayed_`, `zombie_death_animscript`, `do_zombies_playvocals` /
`play_ambient_zombie_vocals`, `make_crawler`.

Plus the whole tear path, which is where the deleted timer's job went:
`tear_into_building` (T5 :760), `get_attack_spot` / `reset_attack_spot`
(:1114, :1100), `get_tear_anim` (:1790), `zombie_tear_notetracks` (:1150),
`should_attack_player_thru_boards` (:917), `do_a_taunt` (:960).

Two honest gaps inside it, both named at their call sites:

* **`animscripted` is not available**, so the tear clip is not root-motion
  aligned onto the attack spot. Ported around: the native mover walks the
  zombie to the spot first (T5's own `goalradius` 2 and the node's angles) and
  the clip plays in place. What is lost is sub-inch alignment of the hands to
  the board, not the mechanic — the notetracks are identical.
* T5 waits on the engine's `"goal"` and `"orientdone"` notifies. This server's
  mover publishes neither, so arrival is polled with a hard timeout — which is
  the same safety T5 puts on its own `"orientdone"` wait, for the reason T5's
  comment gives ("Otherwise, zombies could get stuck waiting").

`get_tear_anim` is T5's 200-line switch collapsed: T5 crosses the chunk's
authored `script_noteworthy` slot with the side and the pose to land on one of
the 36 boardtear clips, and the slot number *is* the index into that side's
six clips. The side is derived from the chunk's offset along the barrier's
right vector. INFERRED that this reproduces T5's mapping; MEASURED that all 36
clips exist and that the six-per-side structure is what the names encode.

`move_speed_scale()` is new and is not in T5. T5's AI travels at the
animation's own root-motion speed, so the clip and the translation cannot
disagree; this server's mover is scalar, so the walk/run/sprint bucket now
picks the scalar (0.5 / 0.9 / 1.4) instead of the previous pass's formula over
the raw round dial. Without it the clip and the ground speed drift apart.

### 4.4 `_zombiemode_blockers.gsc` — the cleanup

* `blocker_zombie_tear_watch()` **deleted**. The header now records what it
  was and what replaced it.
* `blocker_attack_spots` gains `attack_spots_taken[]`, T5's per-spot
  reservation (:1327).
* `remove_chunk` keeps its T5 state half and gains the two halves T5 threads
  off the same note: `zombie_boardtear_audio_offset` (T5 :2105) and
  `zombie_boardtear_offset_fx` (T5 :1428 / :1493 merged — the two bodies
  differ only in the sign of the two FX offsets).
* The `"anim"` door style is **still out, with a sharper reason than before**:
  it is no longer "there are no animation builtins". MEASURED,
  `src/codol/script/codol_script_anim.c:143`: `anim_receiver` refuses any
  entity for which `CODOL_ActorOwnedTree` returns NULL, and its error text
  says so — *"only actors own one on this server"*. A `zombie_door` is a
  script brushmodel, so **none of the twenty new builtins can drive it**, and
  T5 additionally wants `animscripted`. Making this work is a native change
  (give a script model a server animtree), not a script one.

### 4.5 `_zombiemode_perks.gsc` — the Pack-a-Punch rig

`third_person_weapon_upgrade`, `do_knuckle_crack`,
`upgrade_knuckle_crack_begin` / `_end` are ported. The previous pass deferred
them as `animscripted()`; re-reading T5, **neither is**:

* `third_person_weapon_upgrade` is a `script_model` rig driven by `setModel` /
  `rotateto` / `moveto` / `delete` — all registered.
* the knuckle crack is a **weapon swap**: take the held gun, give
  `"zombie_knuckle_crack"`, switch to it. The animation is the weapon's own
  viewmodel anim, played by the client. MEASURED,
  `docs/zone_assets/ALL_weapon.txt`: `zombie_knuckle_crack` ships in
  `common_gametype_zm`, so the client has it.

Two T5 calls genuinely unavailable, named at their call sites and **not**
stubbed: `useweaponhidetags` (the world-gun tag cull — the world gun draws
with every tag visible for the four seconds it is shown) and four of T5's six
movement locks (only `AllowAds` and `AllowSprint` are registered;
`AllowLean` / `AllowCrouch` / `AllowProne` / `AllowMelee` are not). T5's
"if prone, stand to crouch" is done with the registered `getStance` /
`setStance`. `waittill_any` is not registered either, so the four-message wait
is a relay thread per message onto one struct — which is what `waittill_any`
is.

The FX is CoDOL's own: `maps/zombie/fx_zombie_packapunch`, `common_gametype_zm`.

---

## 5. The one paired edit — the last-stand veto is deleted

`CODOL_ZOMBIES_LOOP_20260920.md` §8a asked for exactly one script follow-up
once the engine publishes C1 ability bit 23 at zm spawn. Done:
`_zombiemode.gsc::Callback_PlayerDamage` no longer converts a lethal hit into
a down. The comment in its place records why — `Callback_PlayerLastStand`
already routes to the same `player_laststand()`, so keeping the veto would
down the player twice, once from the callback and once from the engine.

**The already-down guard above it stays**, deliberately: it is the one clause
the engine's own 500 ms grace window does not cover (a second attacker inside
the same frame). `revive_success` was already correct and is untouched.

---

## 6. Still out, by name, with the specific blocker

Nothing below is stubbed. Each is absent, and each says what would unblock it.

| item | blocker |
|---|---|
| `zombie_gib_on_damage` / `zombie_head_gib` (T5 :2800, :3050) | T5 detaches a tagged limb and attaches a stump. CoDOL ships 17 gib models per body family under **its own** suffixes (`_behead`, `_larmoff_1`, not T5's `_g_behead`), and **no shipped data names the tags they attach to**. Guessing the tags is the fabrication the mandate forbids. The hook `self.gib_func` is wired in `zombie_death.gsc`, so the module that learns the tags changes nothing else. `make_crawler` — the thing gibbing the legs would call — **is** ported and reachable. |
| `zombie_turn` (a real turn-in-place) | T5 has **no humanoid zombie turn module either** (only `zombie_dog_turn.gsc`), and MEASURED the shipped `ai_zombie` set contains no turn clip of any kind. The shipped data agrees with T5. The module keeps the running cycle and lets the native orient turn. |
| `zombie_jump` (traversals) | Two reasons. MEASURED, `codol_actor_lifecycle.cpp:866`: the native frame selects only pain/combat/move/stop/death — **nothing ever selects `_jump`**. And T5 drives the traversal set through `animscripted`. The pose half is implemented and reachable via `self.traverseAnim`; the alignment half is absent and named. |
| the `"anim"` door style | §4.4 — the builtins are actor-only by construction. |
| `zombify_player` and the playable-zombie state machine (T5 :4187) | Not attempted. It is a mode of its own, not an animation path. |
| `injured_walk` / `limp` / `stumble` (T5 :5314–:5380) | MEASURED: `PlayerSetGroundReferenceEnt` is **not** a registered builtin, and it is the whole mechanism — T5 tilts the player's ground reference entity to stumble the camera. `SetBlur` is absent too (T5 has it commented out anyway). This is a native handback, not a script gap. |
| the thundergun knockdown/getup set | The 19 `%ai_zombie_thundergun_*` clips **do** ship, but T5 plays the knockdown with `AnimScripted` onto a landing spot. Left for whoever ports the thundergun weapon script; `zombie_pain.gsc` exposes `self.pain_override` for it. |
| the tesla / freezegun / blackhole / microwave / humangun anim tables | Each belongs to a weapon script that is not ported. The clips exist; the tables can be pasted back the day their consumer does. |

---

## 7. Piece 2 — `_zombiemode_powerups.gsc`, 712 lines

### 7.1 The fifteen pickups, verified rather than assumed

MEASURED, `docs/zone_assets/ALL_weapon.txt` — exactly fifteen `kis_*_zm`, all
in `common_gametype_zm`:

```
kis_all_revive_zm            kis_insta_kill_zm
kis_bonus_points_player_zm   kis_minigun_zm
kis_bonus_points_team_zm     kis_nuke_zm
kis_carpenter_zm             kis_pandora_zm
kis_double_points_zm         kis_rcbomb_zm
kis_fire_sale_zm             kis_sentry_zm
kis_free_perk_zm             kis_tesla_zm
kis_full_ammo_zm
```

**`CODOL_ZOMBIES_LOOP_20260920.md` §6 was wrong about one name**: it lists
`kis_max_ammo`/`kis_full_ammo_zm`. There is no `kis_max_ammo`; the shipped
name is `kis_full_ammo_zm` only. It also does not mention
`kis_bonus_points_player_zm` / `_team_zm` / `kis_pandora_zm` /
`kis_rcbomb_zm` / `kis_sentry_zm` / `kis_minigun_zm`. That is conflict #8 in
§3.1 and the reason the task asked for the names to be re-verified.

### 7.2 Ported, and not

**Dropped and collected (10):** insta_kill, double_points, full_ammo, nuke,
carpenter, fire_sale, free_perk, all_revive, bonus_points_player,
bonus_points_team.

**Excluded from the bag with the reason (5)** — they are not dropped as duds:
`kis_minigun_zm` and `kis_tesla_zm` need their weapon scripts
(`_zombiemode_weap_tesla.gsc`, the minigun timer); `kis_rcbomb_zm` and
`kis_sentry_zm` need the RC-bomb and auto-turret modules; `kis_pandora_zm` is
T5's quantum bomb, which rolls a second power-up out of a table that includes
the other four.

T5 machinery taken: the shuffled draw-without-replacement bag
(`randomize_powerups` / `get_next_powerup` / `get_valid_powerup`, including
T5's legality filters — no second insta-kill while one is up, no all-revive
with nobody down, no carpenter with every board intact), `watch_for_drop`'s
score threshold, `powerup_drop`'s 2%-random / 98%-flagged split and per-round
cap, `powerup_setup`, `powerup_wobble`, `powerup_timeout`'s 25 s + 5 s blink,
`powerup_grab`'s 64-unit proximity test, and `powerup_vo`.

The announcer lines are CoDOL's own and are T5's names: `zmb_vox_ann_nuke`,
`_instakill`, `_doublepoints`, `_maxammo`, `_carpenter`, `_firesale`, all in
`common_gametype_zm`.

Not taken, and why: the power-up HUD overlay and its solo variant (they
`SetShader` T5 materials no CoDOL zone carries), bonfire_sale (no zm map
authors the trigger), random_weapon (needs
`treasure_chest_ChooseWeightedRandomWeapon` plus the unregistered
`useweaponhidetags`), the zombie-grabbable path (no CoDOL pickup is marked for
it), and `maps\_zombiemode_net::network_safe_spawn` (no net-throttle module
here, so the drop spawns directly).

### 7.3 Wiring into the existing modules

* `_zombiemode.gsc::Callback_StartGameType` calls
  `_zombiemode_powerups::init()` **last**, because `get_valid_powerup` asks
  the blockers module whether a barrier is damaged and the perks module which
  machines this map has.
* `_zombiemode_spawner::zombie_death_event` rolls the drop (T5 :3818).
  **Three kinds of kill are suppressed**: a nuke (T5 suppresses it so one
  power-up cannot carpet the map), and the two culls this server has that T5
  does not — `round_spawn_failsafe`'s stuck-actor kill and `clear_zombies`'
  between-round sweep. Both set `.no_powerup_drop`.
* `_zombiemode_perks::init` now records `level.zombie_perk_machines`, so
  `free_perk_powerup` can only hand out a perk this map has a machine for
  (T5 :2293's rule).
* `_zombiemode_weapons::treasure_chest_think` reads its price through the new
  `treasure_chest_cost()` (10 during a fire sale, T5 :2062) **per purchase**,
  and the hint follows the sale instead of advertising 950 during one.

---

## 8. Gate results

All three clean. MEASURED, run after the final edit.

```
# the mandated zm form
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles/zm --root bin/home/codol_rawfiles \
  --seed maps/mp/gametypes/zm.gsc --seed maps/mp/zm_prototype_sh.gsc \
  --seed maps/mp/zm_zombie_training.gsc --seed maps/mp/zm_asylum_sh.gsc
  builtins registered: 949
  scripts in effective tree: 1200
  scripts the loader would lower: 121
  every reachable script resolves against the registered builtin table

# the same PLUS the aitype and the nine animscripts -- which the mandated
# seeds do NOT reach, because the native path loads them, not a GSC call.
# CODOL_ActorScriptsLoadMapTypes is the loader; run this form too or the
# nine files this task rewrote are never gated at all.
  ... --seed aitype/enemy_zombie_zm.gsc --seed maps/mp/animscripts/zombie_{init,stop,move,combat,death,pain,flashed,turn,jump}.gsc
  scripts the loader would lower: 132
  every reachable script resolves against the registered builtin table

# multiplayer, unchanged
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --seed maps/mp/gametypes/war.gsc
  scripts the loader would lower: 108
  every reachable script resolves against the registered builtin table
```

`--binary` was omitted deliberately: with it the tool intersects the source
table with the deployed exe (`tools/codol_script_resolve.py:249`) and would
report the twenty new animation builtins as absent until someone links.

**A gate the tool does not provide, run by hand and worth automating:** the
`%anim` check of §3. All 108 distinct tokens under `zm/**` were verified
against the extracted animtree and the zm-mounted xanim set — 0 missing from
either. A bad `%anim` is a map-load compile error that `codol_script_resolve`
cannot see.

Line endings: every file under `zm/` is LF, verified with
`tr -cd '\r' < f | wc -c` == 0 after the last edit.

No `src/**` file and no shared-tree file was modified. No git command was run.
No server, lobby or client was started or stopped.

---

## 9. Live-verify checklist

In order; each step's failure points somewhere different.

1. **Boot `zm_asylum_sh` and read the init lines.** New ones to expect:
   `CoDOL zm: zombie melee weapon zombie_melee` and
   `CoDOL zm: N power-ups resolved out of the mounted zones`. If the first
   says `dog_bite_zm`, or says no WeaponDef is present, melee is off and
   nothing else in step 4 will happen.
2. **Watch for a weapon-count regression first.** This batch adds up to twelve
   `precacheItem` calls to zm (`zombie_melee`, `zombie_knuckle_crack`, ten
   `kis_*_zm`). `docs/.../weapon-count-cginit-crash` says 0x0047c1f7 is a NULL
   def from a blanked or unbuildable `*a` configstring, not a count cap, and
   every one of these ships in `common_gametype_zm` — but this is the change
   most likely to trip it, so check it before anything else.
3. **A zombie spawns and MOVES with its legs.** Previously it slid in the bind
   pose. Expect a walk/run/sprint cycle and the eye glow. A
   `"requires an entity with a server animtree"` error here means the
   bootstrap pose in `spawn_zombie` ran too early after all.
4. **Let a zombie reach you.** It should swing and you should take damage.
   This is the melee test and the headline of this batch. No damage but a
   visible swing = the clip has no `"fire"` notetrack (check against §3.1
   conflict 10). No swing at all = the native frame is not selecting
   `zombie_combat`; check `meleeAttackDist`.
5. **Let a zombie reach a window.** A board should come off *as the tear
   animation plays*, not on a 3-second beat. Then rebuild it for points. If
   boards come off with no animation, something still polls.
6. **Kill zombies until a power-up drops.** It should spin, blink for the last
   five seconds, and fire its announcer line on pickup. Nuke should clear the
   field; insta-kill and double-points should change the score readout.
7. **Pack-a-Punch.** Expect the knuckle-crack viewmodel for the duration and
   the world gun moving in and out of the machine.
8. **Go down.** With C1 ability bit 23 published this should now be the
   engine's last stand (`ps.pm_type 7`), not the script crawl. This is the
   step §5 changes and the one to watch for a double-down.
