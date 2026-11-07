# Zombies spawn but the player cannot see them — zm_prototype_sh, 2026-09-20

Every claim is labelled **MEASURED** (read out of the live log, the source, or
the shipped zone asset lists) or **INFERRED**.

Live log preserved as `/tmp/qconsole_zombievis_20260920.log` (22:49:55 session,
first 118,392 bytes) and `/tmp/qconsole_live2.log` (same session, 2,499 lines,
taken at 22:56 while the user was still testing).

---

## Verdict: (c) — published, with a model, with no pose

The zombie entity **does** reach the client, as `eType 18` (`ET_ACTOR`), inside
the PVS-filtered entity set, and its composition record (base model + parts)
**is** published in the actor section. What never reaches the client is any
**animation**, because the actor's *incarnation* is zero, and zero is the
"no incarnation" sentinel on the whole animation path.

Not (a): the entity is emitted.
Not (b): the actor record carries a resolved model.

### Evidence that it is emitted (rules out (a))

MEASURED, `qconsole.log:381`:

```
Warning: CoDOL dogs: actor animation delivery to client 0 dropped for sequence 210:
  no pose capture for sequence 210 (capture valid 0 seq 209):
  pose capture: bad source (ent 576 gen 0 time 16999 tree 130377de anims 249)
```

MEASURED, `src/codol/player/codol_actor_delivery.cpp:104-108` — that message can
only be produced from inside this loop:

```c
 if(!capture->valid || capture->sequence!=sequence) {
  for(unsigned i=0;i<count;++i)if(entities[i].type==18)
   return FAIL("no pose capture for sequence %u ...");
  CODOL_ActorDeliveryClear(client);*written=0;return 1;
 }
```

With no `type==18` entity in `entities[]` the function returns success and
writes nothing. The warning fired, therefore **at least one emitted entity had
`type == 18`** at sequence 210.

MEASURED, `src/codol/snapshot/codol_frame_builder.c:167-181`: the `entities`
array handed to `CODOL_ActorDeliveryPrepare` is `next->entities`, filled by
`CODOL_CollectServerEntitiesEmitted(source->first_entity, source->num_entities, …)`
— i.e. the entities of *this client's* `clientSnapshot_t`, already PVS filtered.
It is not the global entity table.

MEASURED, `src/codol/snapshot/codol_sv_gameframe.c:196-200`: the ET_ACTOR seed
arm exists and only rejects an out-of-range `actorSlot`/`treeSelector`; a
rejected entity is silently dropped from the emitted set, so the entity
surviving into `entities[]` also proves `actorSlot ∈ [0,32)` and
`treeSelector ∈ [0,5)` were valid.

### Evidence that it has a model (rules out (b))

MEASURED, `src/codol/snapshot/codol_actor_state.cpp:118-152`: `actor_from_entity`
resolves `entity->model` (falling back to `s.index`) through
`CODOL_ServerModelToWire` and **fails the whole capture** if it cannot.
`CODOL_ProduceActorStates` returns 0 on any such failure, which invalidates the
per-client capture, which makes `CODOL_CopyClientSnapshotActors` return 0,
which makes `codol_sv_gameframe.c:489` `return 0` — the frame is rejected and
the client receives no snapshot at all.

MEASURED: the client was live throughout (it kept firing wall-buy triggers —
`_zombiemode_weapons.gsc:313 self waittill("trigger", player)` produced dozens
of `zmb_no_purchase` runtime errors), and `qconsole.log` contains no
`CoDOL frame rejected` line. So the actor capture succeeded every frame, so
every registered actor had a publishable model.

MEASURED, `bin/home/codol_rawfiles/zm/character/character_zm_zombie.gsc:58-64`:
the zombie body is set with `self setModel( bodies[index] )` from
`c_zom_ger_body1` / `c_zom_garbageman_body` / `c_zom_worker_body` /
`c_zom_secunityguard_body`, and `CODOL_ActorPrepareAnimation`
(`codol_actor_lifecycle.cpp:1458`) refuses an actor with no `entity->model`
— the zombies passed it, and they own live XAnim trees (see below).

### What is actually missing

MEASURED, same log line: `tree 130377de anims 249`. The actor has a server DObj
with a real XAnimTree of 249 animations. Every other input to the pose capture
is healthy. The *only* failing term is `gen 0`.

MEASURED, `src/codol/player/codol_dog_animation.c:87-90`:

```c
 if(!out || !tree || !tree->anims || !tree->anims->size ||
    tree->anims->size>2048 || entity>=2046 || !generation || !time || …)
     return FAIL("pose capture: bad source (ent %u gen %u …)");
```

MEASURED, 41 copies in the live log of:

```
Warning: CoDOL anim: setflaggedanimknoball() on entity 576 with no incarnation; not published
```

from `src/codol/script/codol_script_anim.c:275-296`, which refuses to append the
animation to the journal when `event.generation` is 0. The warning is throttled
to one line a second globally, so the true rate is far higher.

---

## Root cause: `useCount` is a FREE counter, so a first-use entity has incarnation 0

MEASURED, `src/g_main_mp.cpp:357,381` — the **only** writer of `useCount` in the
entire tree is `G_FreeEntity`:

```c
  int useCount = gEnt->useCount;
  …
  memset(gEnt, 0, sizeof(*gEnt));
  …
  gEnt->useCount = useCount + 1;
```

So `useCount` counts how many times a slot has been *released*. An entity
occupying a slot that has never been recycled carries `useCount == 0`.

MEASURED, the four places that consume it as a published "generation" all treat
0 as *absent*:

| site | test |
|---|---|
| `codol_script_anim.c:275` | `if (!event.generation) … return;` |
| `codol_actor_anim_journal.c:66` | `return event->generation && …` |
| `codol_dog_animation.c:88` | `… \|\| !generation \|\| …` → bad source |
| `codol_dog_animation.c:396` | `if(frame<0 \|\| !generation \|\| …)` → bad lookup |

And the producers were raw reads: `codol_script_anim.c:263`
(`event.generation = e->ent->useCount`) and `codol_actor_lifecycle.cpp:150`
(`a->generation = entity->useCount`, which `CODOL_ActorCaptureSources:1533`
then publishes as the pose source's generation).

### Why zm hits it and mp did not

MEASURED, the zm zombies take **ascending virgin entity slots**: 575, 576, 577,
578, 579, 580, 581, allocated in order within the first ~20 s of the match,
before anything had been freed. Nothing had incremented their `useCount`.

MEASURED, the working dog runs (`qconsole.nuked4.log`, `qconsole.log.quit2`)
show mp dogs at entity numbers 91, 121, 125, 129, 198, 230, 234, 241 — low and
non-contiguous, i.e. **recycled** slots — with **zero** `no incarnation`
warnings and **zero** `actor animation delivery … dropped` lines in either log.
An mp match churns entities (missiles, grenades, dropped world weapons) long
before a killstreak dog spawns, so the dog always lands on a slot with
`useCount ≥ 1`.

INFERRED: this is why the dog was believed to work and the zombie was not — the
two take the same code path, and the dog simply never presented a zero.

(MEASURED aside: `qconsole.dogs-20260920.log` shows the dog *also* failing, but
for an unrelated and already-known reason — `no server animtree named "dog" is
registered`, so `spawnactor` freed the actor at initialization. That log is not
evidence about incarnation either way.)

### Why one bad actor blanks the whole match

MEASURED, `codol_actor_delivery.cpp:74-78`: the live capture loop sets `ok=0` on
the **first** actor whose pose cannot be captured and then abandons the entire
recipient capture. One `gen 0` zombie therefore suppresses animation delivery
for *every* actor in the snapshot, including any zombie that did land on a
recycled slot. MEASURED, the live log also contains actors 167 and 176 (later
zm respawns, low recycled slots) coexisting with 576/577/578 — they got no
poses either.

---

## Fix

The incarnation published on the animation channel is now **1-based**:
`incarnation = useCount + 1`. Zero keeps meaning "absent", and a first-use
entity becomes addressable.

New in `src/codol/player/codol_actor_anim_journal.h` (the header every consumer
on this path already includes, directly or through `codol_dog_animation.h`):

```c
#define CODOL_ACTOR_INCARNATION(useCount) ((uint32_t)(useCount) + 1u)
```

Converted — producers and live-entity comparisons together, so both sides of
every equality move at once:

| file | line | change |
|---|---|---|
| `codol_actor_lifecycle.cpp` | 123 | `CODOL_ActorForEntity` identity check |
| `codol_actor_lifecycle.cpp` | 150 | `a->generation` (the published pose source) |
| `codol_actor_lifecycle.cpp` | 1448, 1597, 1622 | corpse record generation (a self-consistent trio; converted for uniformity, not because it was broken) |
| `codol_dog_animation.c` | 315, 340 | notified-batch guards comparing a **published** generation against a live `useCount` |
| `codol_script_anim.c` | 263 | `event.generation` for every GSC `setanim*` |

Deliberately **not** converted — these never reach the wire and only ever
compare one raw read against another, so 0 is harmless:
`a->enemyGeneration` (`codol_actor_lifecycle.cpp:312,329,333`),
`codol_actor_spawn.cpp`, `codol_actor_scripts.cpp:331`, `codol_bot.c`,
`codol_dog_combat.c`, `codol_player_worldweapon.c`,
`codol_equipment_lifecycle.c`, the vehicle/RC records,
`codol_script_combat_builtins.c`.

The four `!generation` sentinel tests are left in place; they are now genuine
invariants rather than a trap. `codol_script_anim.c:275`'s warning becomes
unreachable, which is the intended outcome.

Note on file ownership: `codol_dog_animation.c` and `codol_script_anim.c` sit
just outside this worker's glob (`codol_actor_*`, `codol_sentient.cpp`,
`snapshot/**`), but are owned by neither of the two other running workers
(zm GSC, `src/codol/weapon/**`). The change is atomic — splitting it would ship
a build where one side of an equality moved and the other did not.

### Build

`tools/BUILD-CODOL.ps1 -ObjectsOnly` → **exit 0, "Objects done"**, with
`codol_actor_lifecycle.o`, `codol_dog_animation.o`, `codol_script_anim.o` and
`codol_actor_anim_journal.o` all rebuilt after the edit (object mtimes verified
newer than source mtimes). No new warnings. Not linked, not promoted.

Line endings verified before and after: `codol_dog_animation.c` 407 CR in both
the working tree and `HEAD`; the other three 0 in both. `git diff --stat` is
35 insertions / 8 deletions across 4 files.

### What this does and does not promise

INFERRED: with the incarnation nonzero, pose capture succeeds, the journal
accepts the GSC animation transactions, and `CODOL_DogAnimBootstrap` emits a
current-pose bootstrap the first time the actor enters the recipient's roster.
That is the complete animation channel, identical to the dog's.

INFERRED: a skinned model whose client XAnimTree has received no animation at
all collapses to a degenerate pose, which reads as "nothing there" rather than
as a T-pose. That is the best explanation for *invisible* rather than *stuck in
bind pose*, but it is client-side and was not measured here. If the zombies now
appear but T-pose, that is a different defect (animation selection), not this
one.

MEASURED and unchanged by this fix: the zombies do not move (`moved 0/s`,
`route 0/0`, `enemy -1`). A stationary visible zombie was the stated goal.

---

## Second item: zm maps have no waypoint graph

MEASURED, `codol_actor_lifecycle.cpp:444-451`:

```c
 int from = CODOL_BotNavNearest(entity->r.currentOrigin);
 int to   = CODOL_BotNavNearest(a->goal);
 const float *start = CODOL_BotNavPoint(from), *end = CODOL_BotNavPoint(to);
 if (!start || !end) { ActorRouteFailed(entity,a,"no waypoint graph");
                       if (!a->chaseRadius) return 0; goto straight; }
```

MEASURED, the live log, every frame:
`route FAILED (no waypoint graph): … 0 graph nodes`.

### Does CoDOL ship pathnodes for zm maps? No — and not for any map.

MEASURED, `docs/zone_assets/COUNTS.tsv` header: the asset classes present across
**all** CoDOL zones are physpreset, phys_collmap, xanim, xmodelsurfs, xmodel,
material, pixelshader, vertexshader, vertexdecl, techset, image, sound,
sndcurve, loaded_sound, col_map_mp, com_map, game_map_mp, fx_map, gfx_map,
lightdef, font, menufile, menu, localize, weapon, snddriverglobals, fx,
impactfx, rawfile, stringtable, leaderboarddef, structureddatadef, tracer,
vehicle, addon_map_ents, weaponattach. There is **no** `pathdata`, no
`game_map_sp`, and no node/nav class of any kind.

MEASURED, `docs/zone_assets/ALL_game_map_mp.txt`: the three zm maps ship as
`game_map_mp` — `maps/mp/zm_asylum_sh.d3dbsp`,
`maps/mp/zm_prototype_sh.d3dbsp`, `maps/mp/zm_zombie_training.d3dbsp`.

MEASURED, `src/world.h:11-14`: `struct GameWorldMp { const char *name; }` — the
MP game world asset carries no path data in this fork at all. (In stock IW3 the
pathnode graph lives in the SP game world; MP maps have never had one, which is
exactly why CoD4 bot mods ship external waypoints.)

MEASURED, `docs/zone_assets/ALL_rawfile.txt` contains zero entries matching
node / path / waypoint / nav.

MEASURED, `bin/home/main/waypoints/` holds 15 CSVs, all `mp_*_wp.csv`
(afghan, bloc_sh, bog_sh, cargoship_sh, crash_intro, crash_tropical,
cross_fire, estate_tropical, fav_tropical, killhouse_sh, nuked, overgrown,
rust, storm_spring, underpass). None for zm.

### Options — no graph is invented here

1. **Make zombies chase directly instead of routing.** MEASURED,
   `codol_actor_lifecycle.cpp:718` is the only writer of `a->chaseRadius`, and
   it runs only once the actor has an enemy. The live zombies show `enemy -1`,
   so they never even reach the straight-line `goto straight` fallback that
   already exists two lines above. Wiring zm enemy acquisition (players are the
   only valid targets in zm) would give T5-shaped behaviour — beeline at the
   nearest player — with no graph at all. Cheapest route to moving zombies, and
   close to how T5 zombies behave between barrier and player.
2. **Author `waypoints/zm_<map>_wp.csv`** in the existing CSV format, generated
   from the map's own collision/BSP or recorded from player movement. Reuses
   the shipped loader unchanged, but is real per-map content work and is the
   option that amounts to building a graph.
3. **Import from the zone** — ruled out above; the data does not exist.

Recommendation: (1) first; (2) only if zm needs navigation around geometry a
direct chase cannot solve.
