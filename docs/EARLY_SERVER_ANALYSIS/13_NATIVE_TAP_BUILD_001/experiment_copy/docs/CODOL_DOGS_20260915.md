# Attack dogs killstreak, 2026-09-15

End-to-end integration of `dogs_mp` (catalogue row 20, 11 kills) and
`dogs_pro_mp` (row 41). Supersedes the staging notes in
`CODOL_DOGS_IMPLEMENTATION_20260914.md`, which described the same work while it
was still unintegrated under `obj/dogs-stage/`.

Status: source integrated, every object compiles, two offline gates pass
(`tests/test_codol_dog_animation.py`, `tools/codol_script_resolve.py` with the
dog scripts seeded). Nothing has been built as a whole binary, deployed or seen
in C1. The killstreak is still unregistered - the one-hunk hook diff for
`_killstreaks.gsc` is at the end of this file and belongs to the killstreak
worker.

## 1. State found in obj/dogs-stage

Codex's staged work was **not** GSC. It was ~4,400 lines of native C/C++ that
implement the actual VM builtins, plus eleven small patches wiring them into
shared files. Audit result:

| | |
|---|---|
| written | 25 sources + 2 retained-assembly files + 11 patches |
| compiles | yes, after 3 fixes - see below. Every staged `.c`/`.cpp` was otherwise clean under `-m32 -std=gnu11/gnu++11 -DCODOL_SERVER` |
| tested | **no**. No unit test, no build, no run, nothing in C1 |
| patches that still applied | 2 of 11 (`actor-fields-dispatch`, `actor-script-load-callsites`); `native-entity-types` and `actor-spawner-identity` had already been integrated; the rest had drifted and were reapplied by hand |

The three compile failures were all missing halves of unapplied patches:
`ENT_HANDLER_CODOL_ACTOR` (`g_shared.h`), `CONTENTS_CORPSE` (never defined in
this fork) and `G_ModelIndex` (which CoDOL replaces with
`CODOL_RegisterRuntimeModel`; `_g_items.asm:1523` makes the same substitution).

Three staged modules were **discarded** rather than integrated:
`codol_dog_locomotion.c`, `codol_dog_action_animation.c` and `codol_dog_look.c`
are earlier iterations superseded by `codol_dog_states.cpp`, which carries its
own `BG_Dog_Look_At`. Nothing referenced them, and two of them carried the same
broken clip names described in section 3. They remain in `obj/dogs-stage/`.

## 2. C1 evidence

### Assets (all measured in the shipped 1.1.1.13 zones)

| thing | C1 name | where |
|---|---|---|
| model | `german_sheperd_dog` | `common_gametype_mp.zone` xmodel #10079, 579,128 bytes. Also interned in `mp_nuked`, `code_post_gfx_mp`, `common_gametype_coop` |
| animation tree | `animtrees/dog.atr` | `common_mp.zone` rawfile #206, 1,980 bytes |
| animation list | `animlists/common_dog.animlist` | `common_gametype_mp.zone` rawfile #10002, 2,059 bytes, 70 entries (58 in the `=dog` group) |
| xanims | 68, `german_shepherd_*` #10004..#10074 | `common_gametype_mp.zone` |
| materials | `mc/mtl_german_shepherd`, `mc/mtl_german_shepherd_fur` | `common_gametype_mp.zone` |
| activation weapon | `dogs_mp` (melee 25, delay 250, time 699); pro row uses `killstreak_pro_dogs_mp` | type-28 defs in `common_gametype_mp` |
| bite weapon | `dog_bite` | real C1 WeaponDef |
| shellshock | `shock/dog_bite.shock` | `code_post_gfx_mp.zone` rawfile #376 |
| HUD | `hud_icon_dogs`, `dpad_dogs`, `specialty_dogs_crate`, `hud_dog_melee` | `common_gametype_mp.zone` |
| sounds | `anml_dog_*` (~30 aliases), `mp_killstreak_dogs`, `dog_whistle`, `dog_melee`, `dog_death`, `dog_early`, `dog_late`, `dog_lunge` | `common_gametype_mp.zone` |

Absent from every C1 zone, and therefore adapted away: `german_shepherd` and
`german_shepherd_black` (the T5 model names - C1 ships one dog model and no
black variant, so the friendly and enemy models are the same), `dog_bite_mp`,
`aml_dog_bark_close`, `aml_dog_neckbreak`, and any MP dog FX (the only `*dog*`
effects in the corpus are zombie-mode).

Killstreak table row, verbatim (`mp/coKillstreakStatsTable.csv`, stringtable
#433 of `code_post_gfx_mp.zone`):

```
"20","dogs_mp","KILLSTREAKS_DOGS","KILLSTREAKS_DOGS_DESC","11","","",
"MP_EARNED_DOGS","mp_killstreak_dogs","achieve_dogs","dogs","dogs","1",
"dogs_mp","100","hud_icon_dogs","specialty_dogs_crate","dpad_dogs","0","0",
"hud_icon_dogs","300","","3"
"41","dogs_pro_mp","KILLSTREAKS_DOGS_PRO","KILLSTREAKS_DOGS_PRO_DESC","11","","",
"MP_EARNED_DOGS_PRO","mp_killstreak_dogs","achieve_dogs","dogs","dogs","1",
"killstreak_pro_dogs_mp","100","hud_icon_dogs","specialty_dogs_crate","dpad_dogs","0","0",
"hud_icon_dogs","300","dogs_mp","3"
```

### Entity type and animation fields

A dog is **`ET_ACTOR` = 18 (0x12)** (`src/entity.h:238`). C1 has a dedicated
actor family: vehicle spawner 17, actor 18, actor spawner 19, actor corpse 20,
events 21.

Two separate channels draw and animate it, and neither is the player's
`legsAnim`/`torsoAnim`:

- **Identity/composition.** `entityState+0x58` packs the actor slot in its low
  byte and the five-way animation-tree selector in byte `+0x59`
  (`src/codol/snapshot/codol_engine_state.c:1797`). C1 `42A69E` reads `+58` as
  the slot into a 0x29c-byte composition record, `428BA6` reads `+59` as an
  index into five tree pointers at composition `+0x18`, `428C3C` resolves the
  base model from composition `+0x234`, and `428D1D` builds the DObj from the
  selected tree plus the assembled models. The composition record itself comes
  over the separate 24-field **actor channel** (`codol_actor_fields.inc`,
  C1 netfield table `0xc37158`), base model at record `+0x0c` and four
  part model/tag pairs. `es+0xd8`/`+0xdc` exist on eType 18 but are the player
  legs/torso words and are **not** actor animation selectors.
- **Animation.** Actor animation is delivered as snapshot **animation
  commands**, not entity fields. C1 `46AFF0` walks the command list
  (`snapshot+0x3380` count, first record `+0x3384`, stride `0x2c`), validates
  each command's `ref` against the selected DObj tree's entry count at
  `46B120`, and dispatches through `443E90`; table `444140` maps types 1..6.
  Record `+0x1c` is goal weight, `+0x20` playback rate, `+0x24` blend
  (`docs/CODOL_ANIMCMD_SEMANTICS_20260915.md`). Cap is 1,024 commands per
  snapshot (`487272`).

### The tree must be enabled before map load

Serverinfo key `2482` selects which actor trees C1 registers: `465C08` parses
it into `cgs+0x164`, `450AF8` copies it to `bgs+0x921F8`, and `408456` tests one
bit per tree while registering five. **Mask bit 2 selects tree selector 1,
`dog`.** `408377` clears a bit whose animlist fails to load, so an unsupported
class degrades rather than breaking.

`codol_animlistMask` (`src/sv_main.c:3357`) defaults to **0**, which registers
no actor tree at all - with that default a dog would be published, composed and
then never animate. The launcher now sets it:
`bin/START-CODOL-SERVER.cmd` gains `CODOL_ANIMLIST_MASK` (default `2`) and
passes `+set codol_animlistMask`. Changing the dvar's compiled default in
`sv_main.c` would be equivalent and is the better long-term home; that file is
owned by another worker.

## 3. The decisive correction: C1's dog is IW4's dog, not T5's

`animtrees/dog.atr` extracted from `common_mp.zone` is **byte-identical** to the
IW4 tree already collated at `bin/home/codol_rawfiles/animtrees/dog.atr` (only a
trailing newline differs). It declares 47 nodes: one death clip
(`german_shepherd_death_front`), one pain clip (`german_shepherd_run_pain`), no
turn-in-place clips, no `traverse_down_80`, no `run_attack_low`.

OpenBLOPS `bg_dog_animations_mp.cpp`, which the staged `codol_dog_states.cpp`
was ported from, names 19 clips that only exist in T5's tree - and spells the
breed `german_shepard`, one 'h', a string that appears in **no** C1 zone.
`CODOL_DogStateApply` bound the whole clip table before running any state, so
those 19 names would have made every single `setanimstate` return 0. Dogs would
have spawned, moved, bitten and died in a fixed T-pose with nothing in the log.

The fix (`src/codol/player/codol_dog_states.cpp:108`) rebinds the table to
clips the C1 tree actually declares, each substitution commented in place:

| T5 clip | C1 clip | why |
|---|---|---|
| `run_turn_90_left/right`, `turn_90_left/right` | `german_shepherd_run_start_L` / `_R` | C1 bakes turn-in-place into the run starts, as IW4's `dog_move` does |
| `run_turn_180_left/right` | `german_shepherd_run_start_180_L` / `_R` | same |
| `pain_hit_*`, `run_pain_hit_*` (8) | `german_shepherd_run_pain` | C1's only pain clip |
| `death_hit_back/left/right` | `german_shepherd_death_front` | C1's only death clip |
| `run_attack_low` | `german_shepherd_attack_player` | C1's in-place player bite |
| `traverse_down_80` | `german_shepherd_traverse_down_40` | C1 declares up_40/up_80/down_40 only |

Two further changes to the same file:

- Binding is now **cached per tree and diagnosable**
  (`CODOL_DogClipBindings`, `codol_dog_states.cpp:1780`): 59 name lookups no
  longer run on every transition, and an unbound clip prints one warning naming
  the clip instead of failing silently forever.
- Five states the ported `dog_combat.gsc` calls had **no row at all** in the
  47-entry T5 table: `combat_attack_player`, `combat_attack_player_early`,
  `combat_attack_player_lunge`, `combat_player_neck_snap`,
  `combat_player_neck_miss`. Codex judged them unreachable (T5 MP's
  `dog_cant_kill_in_one_hit` does return `true` unconditionally, which does gate
  that branch). They are implemented anyway - `codol_dog_states.cpp:74` extends
  the enum to `ACTOR_ANIMATION_COUNT = 52` and `:1763` adds the rows - because
  all four clips they need are declared by C1's tree and IW4's
  `animscripts\dog\dog_combat` drives exactly this set:
  `attack_player` + `attack_player_late` paired (dog_combat.gsc:475-478), the
  `dog_early` and `dog_lunge` notetrack variants (:318-319, :327), and the
  knob-restarted neck snap/miss (:860, :902).

## 4. What was built

### Native, now in the build (`src/codol/player/`)

| file | lines | what |
|---|---|---|
| `codol_actor_lifecycle.cpp` | 1330 | actor identity paired 1:1 with a sentient, actor script fields, perception, goal/route, orientation, animscript switching, pain/death, corpse handoff, and the GSC method surface |
| `codol_dog_states.cpp` | 1832 | the 52-state dog animation machine and its C1 clip binding |
| `codol_dog_animation.c` | 358 | XAnim goal/complete-goal/knob owner, pose capture, bootstrap, 1200-slot pose archive |
| `codol_actor_anim_journal.c` | 202 | immutable animation-command journal with per-recipient cut/ack |
| `codol_actor_delivery.cpp` | 132 | archive/capture/emit adapter between the journal and the snapshot |
| `codol_actor_scripts.cpp` | 176 | aitype + animscript preload, precache, spawner init |
| `codol_actor_spawn.cpp` | 133 | `spawnactor`, `setspawnerteam`, and the new `spawnactorspawner` |
| `codol_actor_spawn_fields.cpp` | 36 | VM-reference-correct duplication of a spawner's dynamic script fields |
| `codol_actor_physics.cpp` | 116 | capsule sweep, plane clipping, gravity, ground, step |
| `codol_dog_combat.c` | 127 | T5 attack-spot geometry and claim arbitration |
| `src/asmsource/_codol_actor_melee.asm` | - | cdecl adapter onto retained `Weapon_Melee_internal` |
| `src/asmsource/_codol_xanim_complete_knob.asm` | - | notification-free `XAnimSetCompleteGoalWeightKnob` |

### Shared-file wiring applied

- `src/g_shared.h` - `ENT_HANDLER_CODOL_ACTOR = 0x19`, count 0x1A.
- `src/g_main_mp.cpp` - actor/corpse arms in `G_RunFrameForEntity`; the
  `CODOL_ActorPain`/`CODOL_ActorDie` handler row.
- `src/game/surfaceflags.h` - `CONTENTS_CORPSE 0x4000000`, the bit
  `_g_combat_mp.asm:265` already writes into `gentity+0x120`.
- `src/codol/player/codol_sentient.cpp` - `CODOL_ActorLifetimeReset` at pool
  reset, `CODOL_ActorForget` on slot release and on `G_FreeEntity`, and the
  aitype `spawner()` run on a map-authored spawner template.
- `src/codol/snapshot/codol_actors.h` / `codol_actor_state.cpp` - per-recipient
  alternate model, archived with the actor rather than read live.
- `src/codol/script/codol_script_path_nodes.c` - `CODOL_PathNodeOrigin`.
- `src/codol/snapshot/codol_frame_builder.c`, `codol_sv_snapshot.c`,
  `src/sv_snapshot.c` - animation-command delivery, archive and ack.
- `src/asmsource/_g_utils_mp.asm` - `G_DObjUpdate` builds an actor's server
  DObj against the tree the actor owns instead of a null tree.
- `src/asmsource/_g_spawn_mp.asm` - class-0 field namespace `0x8000` routes to
  the actor field dispatch.
- `src/scr_vm_main.c`, `src/asmsource/_g_main_mp.asm` - method registration,
  script-load reset, map aitype load and aitype precache callsites.

### GSC (ported from the shipped T5 source, with attribution headers)

`scripts/codol/maps/mp/_dogs.gsc` (1649) plus
`scripts/codol/maps/mp/animscripts/dog_{combat,move,turn,stop,init,death,pain,flashed,jump}.gsc`
and a dog-local `dog_shared.gsc`, `scripts/codol/aitype/enemy_dog_mp.gsc`,
`scripts/codol/character/character_mp_german_shepherd.gsc`. T5 structure,
function names and `setanimstate` names are verbatim; the adaptations are the
IW4-shaped killstreak registration, the missing T5 subsystems
(`_hardpoints`, `_tweakables`, `_killstreakrules`, `_battlechatter_mp`,
`_globallogic_score`, `_spawning`, Blackbox), and the C1 asset names.

`tools/collate_gsc.py` gained a `!pattern` keep form so
`character/character_mp_german_shepherd.gsc` survives the `character/**`
exclusion - that exclusion's rationale was that only `aitype/*.gsc` referenced
those files and nothing loaded `aitype`, which stopped being true when
`codol_actor_scripts.cpp` started loading the aitype natively.

### Builtins added this pass

`spawnactorspawner( <classname>, <origin>, [<angles>], [<count>] )`
(`codol_actor_spawn.cpp:85`). T5's MP maps ship an `actor_enemy_dog_mp` entity
with spawnflag 1 and targetname `dog_spawner`; `_dogs.gsc` finds it with
`getent()`. No CoDOL map has one. Rather than synthesise map entity-string
data, script asks for the template: the classname is dispatched through the
same `CODOL_Sentient_SpawnActorEntity` path a map entity takes, so the aitype's
own `spawner()` still runs on it. It returns nothing when the aitype scripts
are not loaded. `codol_actor_scripts.cpp:118` therefore also loads
`actor_enemy_dog_mp` unconditionally (non-fatally; a map that really authors
dogs keeps the fatal gate), and `_dogs::dog_manager_spawn_dogs` asks for the
template when `getent("dog_spawner","targetname")` finds none - setting
`level.no_dogs` rather than proceeding when that also comes back undefined.

Six engine facilities the ported scripts call that this fork never had
(`codol_actor_lifecycle.cpp:1029-1034`): `isai`, `setflashbanged`,
`getflashbangedstrength`, `getshootatpos`, `cansee`, `teleport`. `cansee` and
`getshootatpos` deliberately use the same eye-to-centre trace the native actor
perception uses, so script and native enemy selection cannot disagree.

Together with the staged set, the VM now registers `spawnactor`,
`setspawnerteam`, `setgoalpos`, `setgoalnode`, `orientmode`, `animmode`,
`setanimstate`, `setaimanimweights`, `getdeltaturnyaw`, `geteye`, `getvelocity`,
`melee`, `forceteleport`, `setenemymodel`, `settalktospecies`,
`setengagementmindist/maxdist`, `setentityowner`, `clearentityowner`,
`clearentitytarget`, and the actor fields `team`, `aiteam`, `type`, `enemy`,
`goalradius`, `goalheight`, `safetochangescript`, `animplaybackrate`,
`meleeattackdist`, `damageyaw`, `ignoreall`, `script_owner`, `aiweapon`,
`stopanimdistsq`, `lookaheaddir`.

## 5. Verification

| gate | result |
|---|---|
| per-object compile, 49 objects (`gcc/g++ -m32 -DCODOL_SERVER`) | clean |
| `nasm -f elf -DCODOL_SERVER` on the five touched/added asm files | clean |
| undefined-symbol sweep (`nm -u` over the new objects) | every symbol has a definition in `src/` |
| `tests/test_codol_dog_animation.py` | PASS: 64 clips bind in dog.atr (63 nodes); 52 states; 20 computed script states; 5 animscript files checked |
| `tools/collate_gsc.py`, `tools/verify_gsc_collation.py` | exit 0, 0 mismatches, 0 lost resolutions |
| `tools/codol_script_resolve.py --root bin/home/codol_rawfiles` | exit 0, 924 builtins, 88 reachable scripts |
| same, with the 12 dog scripts seeded | exit 0, 100 reachable scripts, nothing unresolved |

`tests/test_codol_dog_animation.py` is the regression gate for the bug in
section 3. It parses `clipNames[]` and `stateRows[]` straight out of the source,
parses the node set out of the animation tree, and fails if any clip is not
declared or any `setanimstate` literal in the ported scripts has no row. It also
ties the row count to `ACTOR_ANIMATION_COUNT` so the table and the range check
in `CODOL_DogStateApply` cannot drift apart.

The full link is not part of this: another worker's in-flight assembly has the
whole-binary build broken, so objects were compiled individually.

## 6. What needs live C1 verification

Nothing here has been seen by a client. In rough order of risk:

1. **Does the client draw a dog at all** - the actor composition record, the
   `+0x58` slot/tree pack and `codol_animlistMask 2` have never been exercised
   together.
2. **Does it animate** - the command journal, its per-recipient cut/ack, and the
   substitutions in section 3. A dog that renders but T-poses means the clips
   bound (the new warning would say otherwise) but the command path did not.
3. **The clone/restart bootstrap** in `codol_dog_animation.c` - old child fade
   durations, nested restarted sync groups and phase quantization were never
   verified against C1's clone cases.
4. **Root motion and physics** - `AI_ANIM_MOVE_CODE` consumes `XAnimCalcDelta`
   on the real DObj; frames over 250 ms currently reject movement instead of
   substepping.
5. **Navigation** - the route consumer uses the existing bot waypoint graph,
   which must actually be loaded for the map. Crouch/prone/climb links are
   excluded until dog traversal exists.
6. **Perception** - nearest-visible acquisition is a deliberately limited
   policy, not full T5 threat scoring or avoidance.
7. **Late-join and killcam corpse pose.**
8. **Flashbangs do nothing to dogs yet** - `_dogs::flash_dogs` is ported and
   callable but unhooked; `maps\mp\_flashgrenades.gsc` needs
   `self thread maps\mp\_dogs::flash_dogs( area );`. That file is not owned by
   this worker.

## 7. Hook diff for the killstreak worker

One hunk in `init()` of `scripts/codol/maps/mp/killstreaks/_killstreaks.gsc`.
Indentation is a tab. Safe to apply now: with the dog scripts seeded, the
resolver reports no unresolved builtin.

OLD
```
	thread maps\mp\killstreaks\_mortar::init();
	// RC-XD (catalogue row18 rcbomb_mp). This reaches spawnVehicle, which the
```

NEW
```
	thread maps\mp\killstreaks\_mortar::init();
	// Attack dogs (catalogue row20 dogs_mp at 11 kills, pro row41 dogs_pro_mp;
	// activation weapon column13 "dogs_mp" is a real C1 WeaponDef). _dogs lives
	// at maps\mp\_dogs rather than under killstreaks\ because it is also the
	// level-wide dog subsystem (preexisting BSP "actor_enemy_dog_mp" spawners,
	// flash_dogs) and not only the reward handler. _dogs::init() precaches the
	// model/bite weapon/shellshock and builds the pathnode arrays; it never
	// waits before returning, so it completes synchronously here, before
	// initKillstreakData() below, and the dogs_pro_mp row inherits this handler
	// from its base the same way every other pro row does.
	thread maps\mp\_dogs::init();
	level.killStreakFuncs[ "dogs_mp" ] = maps\mp\_dogs::useKillstreakDogs;
	// RC-XD (catalogue row18 rcbomb_mp). This reaches spawnVehicle, which the
```

Nothing else is needed in `_killstreaks.gsc`: `initKillstreakData()` already
picks the `dogs_mp` catalogue row up (hint string, dialog,
`level.killstreakWeapons["dogs_mp"]`, pro inheritance), and `usedKillstreak()`
already handles XP, the award stat and the inbound leader dialog.
