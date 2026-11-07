# zm: why there are no zombies anywhere (2026-09-21)

Task: the player spawns into a zombies match, is armed, the round HUD renders,
and there is never a zombie anywhere. The zm session log carries no round,
spawner or actor diagnostics at all.

Every claim below is labelled MEASURED (read out of a live log, this source
tree, the script tree or the retained asm) or INFERRED.

## 0. Headline

**The zombies spawn. They cannot reach the player because the waypoint graph
the actor mover plans over belongs to a different map.**

`CODOL_BotNavLoad` is the only writer of the node count, and its only caller
was the `loadbotwaypoints` builtin, called from
`maps/mp/gametypes/_codol_bots::init()`, which only
`maps/mp/gametypes/_gamelogic.gsc:1508` threads. The zm gametype deliberately
never runs `_gamelogic`. So on a zm map nothing ever wrote that file-static
count, and the zm map inherited whatever graph the previous map left behind.

A secondary, independent finding explains the silence: **every script
diagnostic and every script runtime error in this build is compiled out or
suppressed at `developer 0`, which is what production runs.**

## 1. The chain does NOT break at spawn - measured

MEASURED, `bin/home/main/qconsole.log.old` (zm session, build 1299,
`zm_asylum_sh` then `zm_prototype_sh`, asset category zm, animlist mask 0x8):

* `CoDOL animation classes: zm needs mask 0x8; using it in place of the
  default 0x0` - the zombie species row is reachable in a zm match and the
  mask derivation works.
* Six actors, entities 576-581, `hp 150`. 150 is
  `level.zombie_vars["zombie_health_start"]`, and six is T5's round-1 budget
  for one player. So `zm.gsc::main()` -> `_zombiemode::Callback_StartGameType`
  -> `_zombiemode_spawner::init` -> `round_think` -> `round_spawning` ->
  `spawn_zombie` all ran, and the native actor layer created live actors.
* Their origins are the map's spawn structs: `(-1325 -551 -8)`,
  `(2013 -946 2)`, `(135 2388 -6)`, `(1901 -1462 1)`, `(2045 60 3)`,
  `(-1226 930 15)`. The goal written every frame is the player, around
  `(6 385 1)` / `(42 228 1)` / `(-35 52 1)`.

So the premise "the gameplay loop never runs" is wrong; it runs and produces
zombies. The break is entirely in getting them to the player.

## 2. The break point: `CODOL_ActorGoalDirection` plans over another map

`src/codol/player/codol_actor_lifecycle.cpp`, the pathing branch:

```c
int from = CODOL_BotNavNearest(entity->r.currentOrigin);
int to   = CODOL_BotNavNearest(a->goal);
const float *start = CODOL_BotNavPoint(from), *end = CODOL_BotNavPoint(to);
if (!start || !end) { ActorRouteFailed(entity, a, "no waypoint graph");
                      if (!a->chaseRadius && CODOL_BotNavCount() > 0) return 0;
                      goto straight; }
a->routeCount = CODOL_BotNavRouteFiltered(from, to, ...);
```

Two failure modes, both MEASURED, both the same root:

**(a) zm booted as the first map - graph empty.** MEASURED, `qconsole.log.old`:
`ent 576 route FAILED (no waypoint graph): ... 0 graph nodes`, then
`animscript -> dog_stop (moveMode 0 animMode 1)`, then
`moved 0/s ... rm (0.00 0.00 0.00) vel (0 0 0)` for every sample. `route != 1`
selects the *stop* animscript, the stop animation has no root motion, and root
motion is the only thing that moves an actor. The zombies stood on their spawn
structs for the whole match. (Commit d1b089dc added the `goto straight`
fallback for exactly this; it was never exercised on a zm map - see 4.)

**(b) zm booted after an mp map - graph STALE.** MEASURED,
`bin/home/main/qconsole.log`, 2026-09-21 00:00, build 1301: the server boots
`mp_rust` (`CoDOL bot: waypoint graph waypoints/mp_rust_wp.csv loaded, 192
nodes`), the lobby then rcons `set g_gametype zm` + `map zm_prototype_sh`, and
the zombies that follow report

```
CoDOL dogs: ent 576 route node 170 -> 48: 9 nodes
CoDOL dogs: ent 577 route node 24 -> 126: 18 nodes
CoDOL dogs: ent 576 hp 150 org (1929 -1573 1) moved 0/s ... route 0/13 enemy 0 cand 1 script move
CoDOL dogs: ent 576 stuck at (1929 -1573 1) for 1000 ms -> repath
CoDOL dogs: ent 576 stuck: no clear nav node within 256 to snap to
```

Nodes 170, 126, 48, 24 are **mp_rust** nodes (`bin/home/main/waypoints/
mp_rust_wp.csv`, 192 rows, extents x -440..1772, y -225..1805). The zombies are
in `zm_prototype_sh`. They walk at coordinates that mean nothing in the level
they are standing in, wedge on the first wall, re-path, wedge again, and never
arrive. And because `CODOL_BotNavCount()` is non-zero, `start`/`end` resolve,
so the straight-line fallback from (a) is never reached either.

Mode (b) is the normal case: the lobby starts the native server and then rcons
the map (memory "Native server launch order"), so a zm match nearly always
follows an mp map.

### Why the state was stale

MEASURED:

* `src/codol/player/codol_bot_nav.c` - `static int count;` is written **only**
  by `CODOL_BotNavLoad`.
* `grep -rn CODOL_BotNavLoad src/` - one caller,
  `src/codol/player/codol_bot.c:668`, the `loadbotwaypoints` builtin.
* `grep -rn loadBotWaypoints bin/home/codol_rawfiles/` - one caller,
  `maps/mp/gametypes/_codol_bots.gsc:12`.
* `grep -rn _codol_bots bin/home/codol_rawfiles/` - threaded only from
  `maps/mp/gametypes/_gamelogic.gsc:1508`.
* `bin/home/codol_rawfiles/zm/maps/mp/gametypes/zm.gsc` - `main()` is
  `_callbacksetup::SetupCallbacks()` + `_zombiemode::init()`. `_gamelogic` is
  deliberately not run (`_zombiemode.gsc:18` says why: it would compile and
  precache the whole multiplayer chain).

So map load never touched the graph outside mp. Per-map native state was being
loaded by one game mode's script.

## 3. Why the log was empty - the second finding

MEASURED, `src/scr_vm_main.c:115`: `Scr_AddFunction("println", println, 1)` -
the trailing `1` is the *developer* flag.

MEASURED, `src/asmsource/_scr_compiler.asm`, `EmitCall_290`:

```
cmp dword [ebp-0x20], 0x1      ; the builtin's developer flag
jnz EmitCall_80
mov dword [gScrCompilePub+0x20024], 0x0
mov eax, gScrVarPub
cmp byte [eax+0x7], 0x0        ; developer off?
jnz EmitCall_80
mov eax, [ebp-0x3c]
call TempMemorySetPos          ; rewind: the whole statement is discarded
```

A developer builtin called with developer 0 is **removed from the bytecode at
compile time** - argument evaluation and all. It is a clean no-op, not an
error, which is why the zm loop ran perfectly while printing nothing.

MEASURED, `src/scr_vm_main.c:1818`: `RuntimeError` returns immediately when
`!gScrVarPub.developer && !terminal_error`. Script runtime errors are silent
too.

MEASURED, `bin/START-CODOL-SERVER.cmd:64`: `CODOL_DEVELOPER` defaults to `0`.

MEASURED: the script tree has 791 `println` calls (33 of them in `zm/`), and
**not one** of their strings appears in any of the ~40 `bin/home/main/*.log*`
files - including `DOG PATHING: Could not find spawn nodes`, which must fire on
every map with no dog nodes. That is the empirical confirmation.

This is the inverse of the known "developer 1 masks real bugs" trap: at
developer 0 the whole GSC diagnostic layer does not exist.

## 4. What was already fixed and never tested

`docs/CODOL_ZOMBIE_CHASE_20260920.md` (commit d1b089dc, build 1301, binary
dated 2026-09-20 23:52) added `perfectInfo` enemy acquisition, the
straight-line fallback and the solid-teleport lift.

MEASURED, `bin/home/main/games_mp.log`: the last zm `InitGame` is build 1299
(23:12:04). Build 1301's only recorded `InitGame` is `mp_rust` / `dm`. The
acquisition fix is confirmed working in the 00:00 log (`enemy 0 cand 1`,
`script move` - both of which were `enemy -1` / `script stop` on 1299), but the
straight-line fallback has never run, because the stale graph suppresses it.

Also confirmed present and correct now: `self.meleeattackdist = 64` in
`zm/aitype/enemy_zombie_zm.gsc:61` (the d1b089dc handover item).

## 5. Changes

### 5.1 The waypoint graph is per-map native state (the fix)

* `src/codol/player/codol_bot_nav.c/.h` - new `CODOL_BotNavLoadForMap(mapname)`:
  builds `waypoints/<mapname>_wp.csv` and calls `CODOL_BotNavLoad`, which
  already zeroes `count` before doing anything. No CSV is a normal outcome
  (no zm or coop map ships one, and CoDOL ships no pathdata asset class at
  all - `docs/zone_assets`), and it yields an empty graph rather than the
  previous map's.
* `src/sv_main.c`, `SV_SpawnServer`, immediately after
  `CODOL_LoadClientAnimTrees` and well before the game scripts run - call it
  for the map being spawned and print the result:

  `CoDOL waypoint graph: %d nodes for %s (%s)`

  On mp this is the same graph `_codol_bots::init()` would load a moment later
  (that call stays: it also resets bot state and gates bot spawning), so mp is
  unchanged. On zm/coop the graph is now correctly empty, which is what the
  actor mover's straight-line fallback needs to engage - and a straight line
  at the nearest player is the T5 reference behaviour for this actor
  (`find_flesh` -> `get_closest_valid_player` -> `GetClosest`, no sight test,
  no cap; see `docs/CODOL_ZOMBIE_CHASE_20260920.md` section 2).

### 5.2 Diagnostics that survive `developer 0`

* `src/scr_vm_functions.c/.h` - `GScr_CoDOLPrintLn`, same argument handling as
  `println` (all parameters via `Scr_GetDebugString`, one newline), printed on
  `CON_CHANNEL_SERVER`.
* `src/scr_vm_main.c` - registered as `codolprintln` with developer flag **0**,
  next to `println` with a comment explaining why both exist. `println` itself
  is left alone: flipping its flag would turn on all 791 of them, including
  per-actor animscript spam.
* The zm chain's stage reporting now uses it. A production boot will print, in
  order:

```
CoDOL waypoint graph: 0 nodes for zm_prototype_sh (no CSV for this map; actors steer straight at their goal)
CoDOL zm: Callback_StartGameType entered on zm_prototype_sh
CoDOL zm: starting weapon <name>
CoDOL zm: zombie melee weapon <name>
CoDOL zm: spawn points found: N on zm_prototype_sh
CoDOL zm: zombie spawner ready
CoDOL zm: subsystems initialised; starting the round loop
CoDOL zm: round 1 begins with 1 player(s)
CoDOL zm: round 1 budget 6 zombies at 150 health
CoDOL zm: round 1 first zombie spawned at (x y z) (ent N, 150 hp)
```

  and, when a stage fails, the reason instead: `no usable spawn point on
  <map>`, `round N has no spawners; nothing to spawn`, `spawnactorspawner
  produced no zombie spawner`, or `round N spawn attempt FAILED: <reason>`
  where the reason is now recorded in `spawn_zombie` (`no zombie spawner` /
  `spawnactor returned nothing`). The native actor layer's own
  `CoDOL actor: actor init:` warnings were already always-on
  (`Com_PrintWarning`).

  Files: `zm/maps/mp/gametypes/_zombiemode.gsc`,
  `zm/maps/mp/gametypes/_zombiemode_spawner.gsc`. The two `CoDOL zm DIAG`
  per-damage/per-death printlns were left as `println` on purpose - those are
  per-event and belong under developer.

### 5.3 Not changed

`addon_map_ents` was checked and cleared: MEASURED,
`docs/zone_assets/ALL_addon_map_ents.txt` lists nine entries and every one is
`coop_*`. No zm map has an addon_map_ents lump, so the zm spawners are ordinary
`script_struct` records with `script_noteworthy "zombie_spawner"` in the base
`game_map_mp` mapents - which `init_spawn_points` reads, and which the log
proves are being found and used (the six spawn origins in section 1). The
addon loader is not implicated.

`src/codol/snapshot/codol_engine_state.c` was not touched (owned by the parent
session this iteration).

## 6. How to verify live

1. Boot the server, let the lobby rcon a zm map as it normally does.
2. `grep "CoDOL waypoint graph" qconsole.log` - expect `0 nodes` for the zm
   map. A non-zero count there is the bug returning.
3. `grep "CoDOL zm:" qconsole.log` - the stage list in 5.2 should appear with
   `developer 0`. Any missing line names the stage that failed.
4. `grep "CoDOL dogs: ent" qconsole.log` - expect `enemy 0 cand 1`,
   `route 0/0`, `script move`, a non-zero `moved N/s`, and `org` marching at
   the player. `route node A -> B: N nodes` on a zm map means the graph is
   stale again.
5. Zombies spawn outside the building on T5 maps, so also watch
   `nearest_blocking_barrier` / `tear_into_building` doing the window entry
   (`_zombiemode_spawner.gsc:1100`); the straight line gets them to the
   barrier, the tear gets them in.

## 7. Build

`tools\BUILD-CODOL.ps1 -ObjectsOnly` -> **build OK (exit 0)**, objects only,
no link, no promotion, server not started or stopped.
`python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm`
-> exit 0, `every reachable script resolves against the registered builtin
table` (952 builtins, 106 lowered scripts).

Line endings preserved per file: `codol_bot_nav.c/.h` and `scr_vm_main.c` are
CRLF and stayed CRLF; `sv_main.c`, `scr_vm_functions.c/.h` and the zm GSC files
are LF and stayed LF.

---

# Part 2 (2026-09-21, second pass): the chain reaches a live, enemy-locked, moving-script zombie that does not translate

Boot on the Part 1 fix (build 7d455f90, `zm_prototype_sh` as the first map),
MEASURED from `bin/home/main/qconsole.log`: every `CoDOL zm:` stage line
fires at developer 0; `CoDOL waypoint graph: 0 nodes`; six zombies spawn on
the map's structs with `enemy 0 cand 1`, `script move`, `mode 1/1/3`,
`orient 5`, `route 0/0` (the straight-line arm), and then, every second,
`moved 0/s ... rm (0.00 0.00 0.00) phys ok 60 rej 0 vel (0 0 0) grounded 1`.
5,804 `route FAILED` and 2,476 `goal set` lines in one session.

## 8. Q1 - why the straight leg does not translate

### 8.1 What actually moves an actor (MEASURED, `codol_actor_lifecycle.cpp`)

`CODOL_ActorAdvanceGoalAnimation`, called last in `CODOL_ActorRunFrame`:

```c
int route = mode==1 && a->moveMode ? CODOL_ActorGoalDirection(entity, direction) : 0;
XAnimCalcDelta(obj, 0, rotation, translation, useGoalWeight!=0);
if (mode==1 && route==1) { distance = |translation.xy|; delta = direction * distance; }
moved = CODOL_ActorPhysicsMoveMode(entity, &a->physics, delta, seconds, gravity, 18, ...);
memcpy(a->lastTranslation, translation, 12);   // <- the "rm" field
```

There is no mover velocity at all: the ONLY source of displacement is the
root-motion delta of the animtree, `XAnimCalcDelta`, scaled onto the goal
direction. `mode 1/1/3` (scriptAnimMode 1 / animMode 1 / moveMode 3) and
`route 0/0` with `script move` are all the right values, so the direction is
computed and the physics step is taken 60 times a second (`phys ok 60`) -- with
a zero-length delta, because `rm` (= `lastTranslation`) is exactly 0.

So the single reason is: **the server animtree reports a zero root-motion
delta for the zombie's move clip.**

The "12-16/s right after a regoal" is not locomotion. MEASURED: the stuck
detector's second strike (`stuckCount >= 2`, "regoal") applies
`CODOL_ActorMoveDelta(entity, nudge)` with a 12-unit sideways nudge when an
enemy exists, and `phys ok` includes the gravity settle from the spawn
teleport (z 17 -> 1 on the first sample). Every `org` change in the session is
one of those two.

### 8.2 What was ruled out (MEASURED)

* The clips carry delta tracks. Read straight out of the zone
  (`common_gametype_zm`, XAnimParts +84 = `deltaPart`, +16 = flags):
  `ai_zombie_walk_v1` 129 frames flags 0x03 deltaPart inline;
  `ai_zombie_walk_fast_v1`, `ai_zombie_run_v1`, `ai_zombie_sprint_v1`,
  `zombie_dog_run` likewise; `german_shepherd_run` (the dog that the delta
  path was built on) is the same shape. `ai_zombie_idle_v1` has none, as
  expected for an idle.
* `codol_xanim_native.cpp` builds the delta payload (`p->bDelta=delta`,
  `deltaPart->trans/quat`), so the server-side parts are not stripped.
* The clip is requested correctly: `zombie_move.gsc` -> `MoveStandRun` ->
  `setFlaggedAnimKnobAll("runanim", runAnim, %body, 1, 0.2, rate)`;
  `runAnim` is `self.run_combatanim`, written by `set_run_anim` from
  `level.scr_anim["zombie"]["walk1".."walk8" / "run1".."run6" /
  "sprint1".."sprint4"]`, all of which resolve in the live
  `animtrees/generic_human.atr` (MEASURED: the mounted CoDOL copy has `body`
  at line 1 column 0, `walk_and_run_loops` at 2723, `ai_zombie_walk_v1` at
  2932). `self.has_legs = true` and `self.a` are set in `zombie_init.gsc:117/126`
  before `spawn_zombie` calls `set_zombie_run_cycle`, so the crawl arm is not
  taken.
* The knob-all refusal in `codol_script_anim.c:545` ("no
  XAnimSetCompleteGoalWeightKnobAll; root must be top-level") cannot fire for
  `%body` because `body` IS the top-level node.
* The tree is the actor's own (`anim_receiver` checks
  `DObjGetTree(obj) == CODOL_ActorOwnedTree(ent)`).

What is left is inside the VM/XAnim runtime and cannot be settled by reading:
either the knob command never reaches the tree (a silent script error
upstream - and script errors WERE silent, see 8.3), or the tree holds the
clip at weight 1 and `XAnimCalcDelta` still evaluates 0 (a time/oldTime or
info-walk problem in the retained CoD4 XAnim against CoDOL's clip layout).
No log on disk can distinguish the two, and no log on disk shows a non-zero
`rm` for ANY species, dog included (the dog logs predate the `rm` field).

### 8.3 What was changed so the next boot decides it

1. **Script runtime errors now print at developer 0** (`scr_vm_main.c`
   `RuntimeError`): the early `return` used to swallow them. It now prints
   `^1script runtime error (N/64 shown at developer 0): <message>` for the
   first 64 per process, then one cap line. `Scr_PrintPrevCodePos` asserts
   developer, so only the message is printed. No abort/Com_Error behaviour
   changed.
2. **The per-second actor line carries the animtree state**: `anim <name>
   w <weight> t <time> delta <0|1|-1>` for the heaviest leaf under the root
   (`XAnimGetDescendantWithGreatestWeight` / `XAnimGetWeight` /
   `XAnimGetTime` / `XAnimGetAnimName`, all retained cdecl exports of
   `_xanim.asm`; `delta` is the leaf's `XAnimParts::bDelta`, -1 when the
   heaviest node is not a leaf). Read it as:
   * `anim ai_zombie_walk_vN w 1.00 t 0.xx delta 1` with `rm (0 0 0)`:
     the clip plays, the delta evaluation is what is broken -> next target is
     `XAnimCalcDelta`/`XAnimCalcDeltaTree` against the converted delta parts.
   * `anim ai_zombie_idle_v1 w 1.00` or `w 0.00` or `anim none`: the move
     clip never reached the tree -> the script runtime error printed just
     before it names the failing builtin.

## 9. The map's own navigation (user direction: "use the map's spawns, they should be in the BSP")

### 9.1 Measured

Entity lump dumped from the `col_map_mp` asset of each zm zone
(`obj/zm-mapents/dump_zm_mapents.py`, same lump locator as alpha0022's
`harvest_mapents.py`; dumps in `obj/zm-mapents/<map>-mapents.txt`):

| map | entities | node_pathnode | node_negotiation begin/end | exterior_goal | zombie_spawner (noteworthy) | other |
|---|---|---|---|---|---|---|
| zm_prototype_sh | 1,491 | 691 | 12 / 12 | 12 | 42 | 15 `clip`, 72 board chunks (`script_noteworthy` 1..6 x 12), 3 zombie_debris, 2 zombie_vending, 16 player_volume, 5 teleport_location, 1 each actor_zombie_ger / actor_zombie_dog / actor_zombie_juggernaut |
| zm_asylum_sh | 2,987 | 1,601 | 20 / 20 | 21 | 40 (+main_zombie_spawner) | 13 nodes with a `stairs` key |
| zm_zombie_training | 878 | 326 | 4 / 4 | 4 | 51 (+main_zombie_spawner, zombie_spawner_door) | |
| mp_killhouse_sh (for comparison) | | 660 | 15 / 15 | - | - | 34 node_guard, 6 node_cover_crouch |

Node keys: `classname`, `origin` on every node; `targetname` / `target` /
`animscript` / `angles` only on the negotiation pairs (begin -> `target` =
end's `targetname`). No `spawnflags` on any zm node. The exterior_goal
structs carry `target` -> their chunk set, exactly what
`_zombiemode_blockers::blocker_init` reads.

So: the spawn points ARE from the BSP (unchanged), and the map DOES ship its
AI node set in the same entity string. The zm spawns sit outside; the
entrance windows and the node graph are the only way in.

**The compiled link table is empty in every CoDOL zone.** MEASURED,
`codol_load_blocks.c:replay_game_world_mp`: the 84-byte GameWorldMp is
replayed as name + `memset(+4, 0, 68)` + vehicle track (+72) + glass (+80),
consuming no stream bytes for the 68-byte PathData slot -- which can only be
correct if `nodeCount`/`nodes` are zero in every shipped map (a non-null
pointer there would desync the stream). And that IS the engine's design:
C1.exe carries `PATH_MAX_NODES (%i) exceeded.  Nodecount: %d` and
`Pathnode (%s) at (%g %g %g) has no connections leaving it`, the strings of
T5's runtime `Path_ConnectPaths` (OpenBLOPS
`Game/Server/game/pathnode_load_obj.cpp:1517`). CoDOL connects its nodes at
map load from the entity string, like T5 with `g_connectpaths`.

This server already parsed those nodes (`codol_script_path_nodes.c`,
`CODOL_InitPathNodes` in `GScr_LoadScripts`, for `getnode`/`getnodearray`)
but, by design, built no connectivity - and the actor mover only ever looked
at the CSV graph.

### 9.2 Changed

* `src/codol/script/codol_script_path_nodes.c` - `CODOL_PathNodeCount()` and
  `CODOL_PathNodeValue(index, key)` read-only accessors.
* `src/codol/player/codol_bot_nav.c` - `CODOL_BotNavBuildFromMapNodesIfEmpty()`:
  when the CSV load left the graph empty, take every `node_*` record
  (skipping T5's DONT_LINK spawnflag 1), and link ordered pairs by the
  T5 `Path_CanLinkNodes` rule: |dz| <= 128, horizontal <= 256, an actor
  capsule (+-15.5 xy, 0..72 z, trace mask 0x2820011 = T5's
  `phys.iTraceMask`) walked from A toward B in 8-unit steps with an 18-unit
  step-up and a 32-unit drop test each step, at most 96 steps, and
  |z - z_B| <= 18 on arrival; at most 16 links per node (T5 PATH_MAX_LINKS).
  A `node_negotiation_begin` links only to its targeted end (T5
  `Path_IsNegotiationLink`), marked CLIMB so `ActorRouteEdge` keeps dogs and
  zombies off it (neither has a traversal animscript wired natively).
  Cover-crouch/prone nodes are CROUCH, the rest STAND. It runs from
  `GScr_LoadScripts` right after `CODOL_InitPathNodes()`, i.e. after the
  clipmap is loaded and before any entity spawns (T5 zeroes dynamic blockers'
  contents for the same reason).
* `src/scr_vm_main.c` - that call; `src/scr_vm_functions.h` - the
  declarations.
* mp maps are untouched: the CSV (`waypoints/<map>_wp.csv`) still loads
  first and, when present, the map build is skipped.
* Log lines: `CoDOL waypoint graph: connecting N map nodes (T5
  Path_ConnectPaths rule)...` then `CoDOL waypoint graph: built from the map:
  N nodes, L links (K negotiation), I nodes with no link leaving them`. `I`
  is T5's own "has no connections leaving it" census; a large `I` means the
  walk rule is too strict for this geometry.

With a graph loaded the mover plans A* over it (`CODOL_BotNavRouteFiltered`),
the straight-line arm is only used for the final leg, and the stuck
detector's "snap to nav node" now has real nodes to snap to.

## 10. Q2 - the barrier entry

### 10.1 T5 reference (MEASURED, `T5-STEAM-GSC/maps/_zombiemode_spawner.gsc`)

* `zombie_think` :415 - picks the entrance: `get_array_of_closest(origin,
  level.exterior_goals, undefined, 3)`, drops any candidate more than
  `max_dist` (500, `level.max_barrier_search_dist_override`) farther than the
  previous one, random among the rest; `self.first_node = node`; threads
  `zombie_assure_node` (:611, retries the next closest on `zombie_bad_path`,
  then 20 more, then gives up after 20 s and kills the actor); calls
  `zombie_goto_entrance(node)`.
* `zombie_goto_entrance` :572 - `self.goalradius = 128; self SetGoalPos(
  node.origin ); self waittill("goal")`, then `tear_into_building()`, then
  `clip disable_trigger()` + `connectpaths()`, `zombie_setup_attack_properties`,
  `find_flesh`, and waits `zombie_start_traverse`/`zombie_end_traverse`
  before `zombie_complete_emerging_into_playable_area`.
* `tear_into_building` :746 - loop on `self.first_node`: return on
  `no_blocker`/no target/all chunks gone; `get_attack_spot` or taunt;
  `goalradius 2; SetGoalPos(self.attacking_spot, node.angles)`; the tear
  animation with the `"board"` notetrack removing a chunk.
* `find_flesh` :3922 -> `zombie_pathing` :4082 -> `zombie_follow_enemy`
  :4295, breadcrumbs on `bad_path`.

### 10.2 Ours, before this pass

`_zombiemode_spawner.gsc`: `tear_into_building(node)` (:1100), the attack
spots, the `"board"` notetrack, `get_attack_spot`, `do_a_taunt` and
`all_chunks_destroyed` are all ported and driven by the map's `exterior_goal`
structs and their targeted chunks (`_zombiemode_blockers::blocker_init`,
`blocker_attack_spots`). **What was dropped was the approach:**
`zombie_think` went straight to `nearest_blocking_barrier()`, which only
returns a barrier within 256 units of where the zombie already stands, and
otherwise `setGoalPos(player.origin)`. A zombie spawned 100+ units to the
side of its window therefore never "saw" the barrier and drove at the player
through the outer wall - exactly the measured stuck pattern.

### 10.3 Changed (`bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_spawner.gsc`)

`zombie_think` now does T5's entrance first: `pick_entrance_node()` (the
3-closest / max_dist / random rule, `self.entrance_nodes`), `self.first_node`,
`goalradius 128`, `setGoalPos(node.origin)`, `zombie_wait_goal(20)` (returns
on `"goal"`, on the native `"bad_path"`, or after T5's 20 s give-up),
`goalradius 64`, `tear_into_building(node)` - and only then the existing
seek loop. `closest_exterior_goals(origin, n)` is `get_array_of_closest`
over the exterior_goal structs. With the map graph of section 9, the route
to the entrance node is planned over the map's own nodes.

Not taken (named, not invented): the `clip connectpaths()` after the tear
(no dynamic node-link toggling exists natively yet - the map build ignores
entity clips, so window links exist from the start), the
`zombie_start_traverse`/`zombie_end_traverse` window-climb (needs the
`animscripted` root-motion alignment named in
`docs/CODOL_SCRIPTED_ANIMATION_20260920.md`), and `zombie_assure_node`'s
kill-after-20-s.

## 11. Log flood

`ActorRouteFailed` and the goal-set line are rate-limited to one line per 5 s
per actor and now carry the count since the last one (`route FAILED (why)
xN in M ms: ...`, `goal set xN (...)`). The `bad_path` notify per goal is
unchanged.

## 12. What the next boot should show

```
CoDOL waypoint graph: 0 nodes for zm_prototype_sh (no CSV ...)          <- Part 1 line, CSV absent
CoDOL waypoint graph: connecting 715 map nodes (T5 Path_ConnectPaths rule)...
CoDOL waypoint graph: built from the map: 715 nodes, L links (12 negotiation), I nodes with no link leaving them
CoDOL zm: ... (the Part 1 stage list) ...
CoDOL dogs: ent 576 goal set x1 (<exterior_goal origin>) from (<spawn>) radius 128
CoDOL dogs: ent 576 route node A -> B: N nodes
CoDOL dogs: ent 576 hp 150 org (...) moved N/s ... script move ... rm (x y 0) ... anim ai_zombie_walk_vN w 1.00 t 0.xx delta 1
```

If `moved` stays 0 and `rm (0.00 0.00 0.00)`, the new `anim ... w ... delta`
field and any `^1script runtime error` line just before it name the half of
8.2 that is broken; that is the next work item, and it is now measurable.

## 13. Build / gates

`tools\BUILD-CODOL.ps1 -ObjectsOnly` -> build OK (exit 0), objects only.
`python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm`
-> exit 0. Line endings: `scr_vm_main.c` CRLF (1922 -> 1940 CR for +18
lines), everything else LF and unchanged in kind. No link, no promotion, no
commit, server untouched. `src/codol/snapshot/codol_engine_state.c` untouched.
