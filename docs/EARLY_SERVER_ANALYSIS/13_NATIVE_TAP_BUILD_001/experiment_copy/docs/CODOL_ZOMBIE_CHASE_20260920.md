# zm zombies: enemy acquisition and chase (2026-09-20)

Task: zombies never move, so the player never sees them. Fix zombie enemy
acquisition so they chase the player.

Every claim below is labelled MEASURED (read out of the live log, the source
tree, the T5 GSC or the OpenBLOPS T5 native tree) or INFERRED.

Files changed, all under `src/codol/player/` (this worker's ownership):

* `codol_actor_scripts.h` - new species column `perfectInfo` + its provenance.
* `codol_actor_scripts.cpp` - dog 0, zombie 1.
* `codol_actor_lifecycle.cpp` - perception honours the column; straight-line
  fallback when the map ships no waypoint graph at all; a solid teleport
  destination is resolved instead of freezing the actor; `cand N` diagnostic.

Nothing in `bin/home/codol_rawfiles/**` or `src/codol/weapon/**` was touched;
two suggested GSC one-liners are quoted verbatim at the end for their owner.

---

## 1. Why the zombie never acquired an enemy - and why the dog does

MEASURED, `bin/home/main/qconsole.log` (preserved copy:
`/tmp/qconsole_zombiechase_preserved.log`): 360 of 360 per-second actor diag
samples read `enemy -1`. Not one zombie ever had an enemy.

The acquisition pass is `ActorUpdateVisibleEnemy`
(`codol_actor_lifecycle.cpp`). Its gates, checked one at a time against the
zombie:

| gate | zombie | verdict |
|---|---|---|
| `a->ignoreAll` | `_zombiemode_spawner.gsc:400` sets `self.ignoreall = false` (a real native field, 0x8009) | MEASURED pass |
| actor team | `zm/aitype/enemy_zombie_zm.gsc:34` `self.team = "axis"` -> sentient team AXIS(1) | MEASURED pass |
| target team (`ActorMayTarget`) | `_zombiemode.gsc:568` `self.sessionteam = "allies"` -> `ClientScr_SetSessionTeam` (`src/g_client_fields.cpp:65`) -> `TEAM_BLUE` -> `CODOL_Sentient_ClientTeamChanged` -> sentient ALLIES(2) != AXIS(1) | INFERRED pass (code path read end to end; not separately logged) |
| player registered as a sentient | `CODOL_Sentient_ClientSpawned` at `src/g_client_mp.cpp:277`, persistent class, survives death | MEASURED pass |
| `s->dontTarget` | never set for a zm player | MEASURED pass |
| **line of sight** (`G_TraceCapsule` eye->target, clipmask `0x2820015`) | **fails** | **MEASURED fail** |

MEASURED, same log: the zombies spawn at `(-1325 -551 -8)`, `(2013 -946 2)`,
`(135 2388 -6)`, `(1901 -1462 1)`, `(2045 60 3)` ... while the goal the zm
script keeps writing (`_zombiemode_spawner.gsc:745`
`self setGoalPos( player.origin )`) is around `(6 385 1)`, `(42 228 1)`,
`(-35 52 1)` - the player. That is 1,000-2,500 units of indoor map, so the
sight capsule hits a wall on every frame for every zombie.

**The dog A/B.** Both species run the *same* acquisition function; the dog is
not privileged anywhere in it. The dog works because of its circumstances, not
its code: it is spawned as a killstreak next to its owner, on an MP map, with
short open sight lines - and when it does lose the line, MP maps have a
waypoint graph, so the route planner still moves it. Neither is true in zm.

The consequence chain, all in `codol_actor_lifecycle.cpp` and all MEASURED
from the log:

1. no sight -> no enemy -> `enemy -1`;
2. `chaseRadius` is only ever written in the enemy branch (`:718`,
   `a->chaseRadius = attack.goalSet ? 24.0f : fmaxf(24.0f, a->meleeAttackDistance)`),
   so it stays 0;
3. `CODOL_ActorGoalDirection` hits `route FAILED (no waypoint graph) ... 0 graph
   nodes` and, with `chaseRadius == 0`, returns 0 - no direction at all;
4. `route != 1` -> the *stop* animscript -> no root motion -> `moved 0/s`;
5. the zombies stand on their spawn structs, far outside the player's PVS, so
   he never sees one, never shoots one, and nothing ever scores.

One missing enemy therefore explains invisibility, immobility and the dead
score counter together.

## 2. What T5 actually does - checked, not assumed

The brief said T5 zombies do not navigate by waypoint graph and beeline at the
nearest player. Confirmed, and the mechanism is stronger than "beeline":

* MEASURED, `D:\CoD\COD-GSC-Source\T5-STEAM-GSC\maps\_zombiemode_spawner.gsc:4013`
  (`find_flesh`): `player = get_closest_valid_player( self.origin, self.ignore_player );`
  and `_zombiemode_utility.gsc get_closest_valid_player` is
  `player = GetClosest( origin, players )` - **pure distance, no sight test,
  no FOV, no distance cap**. The result is pinned as `self.favoriteenemy`.
* MEASURED, OpenBLOPS `Game/Server/game/actor_threat.cpp:317-321`: a sentient
  equal to `pFavoriteEnemy` is scored `maxThreat = 2147483646`, i.e. it wins
  the threat contest outright.
* MEASURED, OpenBLOPS `actor_senses.cpp:303-307`: the same favourite gets
  `fovDotUse = 0.0f`, i.e. it is exempt from the view cone.
* MEASURED, OpenBLOPS `actor_spawner.cpp:199-203`: a spawner with the
  **ENEMYINFO** spawnflag (`spawnflags & 8`) runs
  `Actor_GetPerfectInfo(spawn->actor, pEnemy)` over **every** sentient at
  spawn, and `Actor_GetPerfectInfo` (`actor_senses.cpp:514`) writes
  `lastKnownPosTime = level.time` plus the position. That write is the *only*
  awareness gate in the threat pass (`actor_threat.cpp:241`,
  `lastKnownPosTime <= 0` -> "unaware"). So an ENEMYINFO actor targets through
  walls from the instant it spawns.
* MEASURED, our own `zm/aitype/enemy_zombie_zm.gsc` QUAKED block declares
  `ENEMYINFO` for `actor_enemy_zombie_zm`.

So "acquire the nearest hostile with no line-of-sight test" is not a
workaround for a missing nav graph - it is the reference behaviour for this
actor, arrived at by T5 twice over (the spawnflag and `find_flesh`).

T5's *path* to that enemy does use nodes (`zombie_pathing` ->
`zombie_follow_enemy`, with `exterior_goal`/barrier structs at the windows),
and falls back to its breadcrumb system on `bad_path`. CoDOL has neither:
MEASURED, no pathdata/nav asset class exists in the zone inventory, the zm
maps are plain `game_map_mp`, and the only graphs on this server are 15
hand-authored `bin/home/main/waypoints/mp_*_wp.csv`, all multiplayer. With
zero nodes there is nothing to plan over, so the straight line is the only
remaining path - and the capsule physics still slides the actor along walls.

## 3. The changes

### 3.1 `perfectInfo`, a species perception column

`codol_actor_scripts.h` gains `unsigned char perfectInfo;` with the OpenBLOPS
and T5-GSC citations above. `codol_actor_scripts.cpp`: dog `0` (unchanged
sighted behaviour), zombie `1`.

### 3.2 Acquisition honours it

In `ActorUpdateVisibleEnemy`, the sight trace is skipped for a `perfectInfo`
species; every other gate (alive, team, `dontTarget`, `ignoreAll`, nearest
wins) is untouched. For the zombie that is exactly `find_flesh`'s
`GetClosest` over the hostile team, and it is also what ENEMYINFO gives a T5
actor natively.

Effect, INFERRED from the code path: a zombie now acquires the nearest player
on its first frame, `chaseRadius` becomes 24, `CODOL_ActorGoalDirection`
returns a direction, `route == 1` selects the *move* animscript, its root
motion drives `CODOL_ActorMoveDelta`, and the actor walks at the player.

### 3.3 Straight line when the map ships no graph at all

`if (!start || !end) { ... if (!a->chaseRadius && CODOL_BotNavCount() > 0) return 0; goto straight; }`

With a graph loaded the old `chaseRadius` gate stands (a scripted patrol goal
should use the nodes). With **zero** nodes - every zm map - refusing to move
is not caution, it is a permanent freeze, so the actor goes straight. This
also covers the zombie's *script* goals (the barrier goal that
`tear_into_building` sets), which carry no `chaseRadius`.

### 3.4 A solid teleport destination no longer freezes the actor

MEASURED, the same log: 116 of 360 samples read `phys ok 0 rej 60 grounded 0`
with zero velocity - roughly a third of the zombies had *every* physics move
rejected. That is the documented "wedged in solid" signature:
`codol_actor_physics.cpp slide()` returns 0 on `startsolid`, so the origin can
never change again. MEASURED, `_zombiemode_spawner.gsc:329` places zombies
with `ai forceTeleport( origin, angles )` onto `zombie_spawner` map structs,
and `ActorForceTeleport` did no validity test at all. (T5's own zm spawn
structs include riser points that are *meant* to be underground, and T5 plays
a rise animation out of them; our port has no riser handling.)

T5 refuses such a spawn outright - `SpotWouldTelefrag` in
`actor_spawner.cpp:141-157`. Refusing is wrong for this caller (those structs
are all the map offers), so the new `ActorResolveSolidOrigin` runs the same
capsule test and, when it starts solid, lifts one step height at a time up to
the capsule's own height, then settles back onto the floor the lift cleared.
Actors are made passable for the test exactly as the physics move does, so
one zombie overlapping another is never mistaken for solid. An unresolvable
destination is left where script asked and named in the log.

### 3.5 Diagnostic

The per-second actor line gains `cand N` - hostile sentients the last
perception pass considered. Read it as:

* `enemy -1 cand 0` - a *targeting* failure: no hostile sentient exists (team
  mapping, registration, `dontTarget`).
* `enemy -1 cand 1+` on a sighted species - the target is occluded.
* `enemy 0 cand 1` - the expected zm steady state, player on client slot 0.

## 4. How to verify live

1. Boot zm, join, let a round spawn.
2. `grep "CoDOL dogs: ent" qconsole.log` - expect `enemy 0 cand 1`, `route 0/0`,
   `script move`, a non-zero `moved N/s`, and `org` marching toward the
   player's position each second.
3. `grep "route FAILED"` still appears once per goal (there is genuinely no
   graph) - that is now informational, not fatal.
4. `grep "teleport destination"` - how many spawn structs sit in solid, and
   whether the lift cleared them.
5. `grep "phys ok 0 rej"` should be far rarer than 116/360.
6. The player should now see zombies converge on him; kills should start
   incrementing the score the other worker found stuck at zero.

## 5. Handover: two GSC one-liners (not this worker's tree)

**(a) Zombies will chase but not swing.** MEASURED: `CODOL_DogCombatGoal`
(`codol_dog_combat.c:104`) returns all-zero when `attackDistance <= 0`, so
`inAttackRange` is never true, so the native frame never switches to
`a->scripts.combat` and `zombie_combat.gsc` never runs. MEASURED: nothing in
the zm tree sets `meleeattackdist`, so it is 0 - and the GSC melee port itself
reads it (`zombie_combat.gsc:205` and `:221`). One line in
`bin/home/codol_rawfiles/zm/aitype/enemy_zombie_zm.gsc`, in `main()`, next to
the engagement distances already authored there:

```
	self.meleeattackdist = 64;
```

(64 is the engagement max distance that same file already authors two lines
below - it is the file's own number, not an invented one. The GSC owner should
confirm it against the swing animations' reach.)

**(b) Downed players.** MEASURED: T5 `find_flesh` filters with
`is_player_valid( player, true )`, which drops last-stand players.
`_zombiemode_laststand.gsc` sets `self.ignoreme`, which is a plain script
variable here - no native field reads it - so zombies will keep mobbing a
downed player. `setdonttarget` is already a registered sentient method
(`codol_sentient.cpp:845`) and `dontTarget` is already honoured by the
acquisition pass, so the fix is to pair it with the existing writes:
`self setDontTarget( true );` beside `_zombiemode_laststand.gsc:156`, and
`self setDontTarget( false );` beside `:284` and `:425`.

## 6. Build

`tools/BUILD-CODOL.ps1 -ObjectsOnly` -> **build OK (exit 0)**, objects only, no
link, no promotion. Line endings verified unchanged (all three files are LF in
the working tree and at HEAD, 0 CR before and after).
