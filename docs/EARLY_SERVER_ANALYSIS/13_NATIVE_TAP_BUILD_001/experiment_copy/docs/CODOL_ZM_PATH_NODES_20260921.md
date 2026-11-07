# zm/coop map-node path graph: why 620 of 715 nodes were isolated, and the fix

Date: 2026-09-21. Scope: `src/codol/player/codol_bot_nav.c`
(`CODOL_BotNavBuildFromMapNodesIfEmpty`, the port of T5 `Path_ConnectPaths` /
`Path_CanLinkNodes` that commit 454c188b introduced). Nothing in the mp CSV
path, `codol_engine_state.c` or `codol_actor_lifecycle.cpp` was touched.

State of this work: **source written, compiled (`tools\BUILD-CODOL.ps1
-ObjectsOnly`, `obj/codol/codol_bot_nav.o`, no new warnings), NOT linked and
NOT booted**. Every "after" number below is the offline oracle's prediction;
the native server prints its own census at load (section 6) so the first
boot verifies it.

## 1. The reason: the authored node origins float above the floor, and T5/C1 drop them before linking

First live result (454c188b, zm_prototype_sh):

    CoDOL waypoint graph: built from the map: 715 nodes, 122 links (12 negotiation), 620 nodes with no link leaving them
    ^5Hitch warning: 4219 msec frame time

Measured offline with `tools/codol_path_link_census.py` (alpha0022's
`pmove.World`, brushes + terrain, a POINT trace straight down from each
node), the node origin sits this far ABOVE the floor under it:

| map | nodes | node z minus floor z | nodes within 7 of their floor |
|---|---|---|---|
| zm_prototype_sh | 715 | 7 .. 78, mode 28 (156 nodes), median 28 | 1 |
| zm_asylum_sh | 1,641 | 2 .. 80+, mode 24 (357 nodes) | 1 |
| zm_zombie_training | 334 | 18 .. 46, mode 24 | 0 |

Not one node is on its floor. That is by design: T5 spawns nodes and then
runs `node_droptofloor` on every one (OpenBLOPS `pathnode.cpp:327`, called
from `G_SpawnPathnodes` `:513` for all nodes without PNF_CAN_PARENT, then
`:524` for the rest) BEFORE `Path_ConnectPaths`. C1.exe carries the same
pass: "is floating" at 0x8794fc and "has no connections leaving it" at
0x8794dc (plus "PATH_MAX_NODES (%i) exceeded" at 0x87969c), so CoDOL drops
and connects at load exactly like T5. The 454c188b port skipped the drop.

What the missing drop did to the walk (Python oracle, 40 sampled nodes, the
shipped geometry: 72-tall box, 18 lift, 8-unit steps, 32 drop, 18 arrival):

| rejection | pairs | share |
|---|---|---|
| no floor within drop | 177 | 38% |
| arrival dz > 18 | 171 | 37% |
| forward hit | 113 | 24% |
| **link** | **6** | **1.3%** |

35 of the 40 sampled nodes had no link leaving them, i.e. the 620/715 the
server printed. The two dominant reasons are both the floating origin:

- **no floor within drop (38%)**: the walker lifts the capsule 18 above the
  node and then looks for a floor within 32 below the node z. A node 33..78
  above its floor fails on the very first step.
- **arrival dz > 18 (37%)**: for nodes 18..32 up, the first step's drop test
  snaps the walker's z to the real floor, but the TARGET node's z is still
  the floating authored value, so `|z_end - z_to|` is ~28 > 18.
- **forward hit (24%)** is mostly the 72-tall PLAYER box (top at floor +
  118 after the 28 float and 18 lift) clipping lintels and stair ceilings.
  T5 links with the ACTOR hull, `actorMaxs.z = 48` (OpenBLOPS
  `actor.h:452`), widened by 0.5 in xy.

## 2. Trace-stack finding: nothing wrong with the mask or the stack

- `G_TraceCapsule` (sv_world.cpp:320) is a plain `SV_Trace`: `CM_BoxTrace`
  against world model 0 (which in this engine includes the terrain
  `CollisionAabbTree`, cm_mesh) then `CM_ClipMoveToEntities`. At
  `GScr_LoadScripts` time no entity exists, so the map's 15 `clip`
  brushmodels (`*N` submodels), the 72 barrier board chunks
  (`script_model`) and every other blocker are absent from the trace, which
  is exactly what T5 arranges by zeroing `Path_IsDynamicBlockingEntity`
  contents during the connect.
- Mask 0x2820011 = SOLID | GLASS | MONSTERCLIP | 0x800000 | 0x2000000 in
  C1's own infoParms table (codol_collision_flags.h). MONSTERCLIP is in it
  on purpose (T5 uses the same word); the two high bits are runtime entity
  bits no material can author, harmless here. The floor census hit
  `0x1` (world solid) for 555/715 nodes, `0x8000001` (detail solid) for 91,
  and terrain surfaces (sflags with type bits, e.g. 0x1600000) for 263, so
  the terrain IS traced and the floor is found.
- The remaining forward hits after the fix are real: contents
  `0x8030200` / `0x8020000` (monsterclip volumes, the window and doorway
  clips) and `0x1` / `0x8000001` (walls). Those pairs are not meant to
  link; the windows are traversed by the 12 authored negotiation links.

## 3. Authored-link finding: there are no authored chains

zm_prototype_sh's 691 `node_pathnode` carry ONLY `classname` and `origin`;
42 also carry a `targetname` (each is the node a `zombie_spawner`
script_struct targets). No `node_pathnode` has a `target`. The only
authored links are the 12 `node_negotiation_begin` -> `node_negotiation_end`
pairs (`target` -> `targetname`, plus `animscript`), which the builder
already honoured (T5 `Path_IsNegotiationLink`, dist 15, unconditional).
`exterior_goal` structs target the window's clip brushmodel
(`script_brushmodel "*1"`, noteworthy "clip"), not a node. So the geometric
walk IS the designer's intended connectivity, as in T5, and "honour authored
links first" reduces to the negotiation pairs, which now also take
geometric links like every other node (T5 loops all typed pairs; the old
`continue` after a begin node was a divergence).

## 4. What changed in `codol_bot_nav.c`

1. **Drop to floor** (`map_drop_to_floor`): T5 `node_droptofloor` verbatim in
   this engine's trace: from origin+1 down 256, box {-15,-15,0}..{15,15,30},
   mask 0x820011; start in solid or floating -> the node is a bad node
   (skipped, first 6 printed with T5's wording); otherwise the origin moves
   to the landing and a stationary {15,15,48} probe must be clear. The
   graph's node points are therefore at FEET height now, which is also what
   the actor mover wants (its origin is at the feet).
2. **Actor hull**: the walk uses {-15.5,-15.5,0}..{15.5,15.5,48} (T5
   `actorMins/Maxs` + 0.5) instead of the 72-tall player box.
3. **Flat-ground fast path**: when every floor sample 32 units along the line
   is within +-4 of a.z and b.z is too, the stepping walk's capsule would be
   the same constant-height capsule at every step, so one full-length sweep
   decides the pair (about 6 traces instead of ~64). Any slope, step or gap
   takes the full 8-unit stepping walk (18 step-up, 32 drop, 18 arrival),
   unchanged.
4. **Spatial grid**: nodes are bucketed into 256-unit cells (hash 4096); each
   node tests only the 3x3 neighbourhood, then the T5 dz/xy gates. The
   O(n^2) pair scan is gone. Note the 4.2 s hitch was mostly trace time,
   not the pair scan (511k cheap float compares is milliseconds), so the
   fast path is what buys the time; the build now prints its own wall time.
5. **Rejection histogram**: every exit of the link test is counted
   (`dz>128`, `xy>256`, `coincident`, `fwd startsolid`, `fwd hit solid`,
   `fwd hit monsterclip`, `fwd hit other`, `no floor within drop`, `down
   startsolid`, `step budget`, `arrival dz>18`, `link cap`, `link`) and
   printed once after the build.
6. **Component census**: union-find over the links (undirected), component
   count, main-component size, nodes off it, nodes with no link entering.
   Then the entity string is rescanned (`G_ResetEntityParsePoint` /
   `G_ParseSpawnVars`, reset again afterwards, the same thing
   `CODOL_InitPathNodes` does) for `script_struct` `zombie_spawner`
   (node by `target` -> node `targetname`, else nearest) and `exterior_goal`
   (nearest node); each one off the main component is printed (first 6).
7. `LINKS` 32 -> 48 (T5 has no per-node cap; overflow counts as `link cap`
   in the histogram instead of silently truncating). The former
   `MAP_LINKS_PER_NODE 16` cap is gone.

## 5. Predicted census after the fix (offline oracle, all nodes, all pairs)

`python tools/codol_path_link_census.py <map> --dropfloor --height 48 --sample 0`

| map | nodes kept | drop (bad) | candidate pairs | links | no link leaving | components (main / off) | spawners off main | exterior_goal off main |
|---|---|---|---|---|---|---|---|---|
| zm_prototype_sh | 715 | 0 in solid, 0 floating | 8,966 | 5,948 (5,936 walk + 12 negotiation) | **0** | 3 (710 / 5) | 0 of 42 | 0 of 12 |
| zm_zombie_training | 334 | 0 / 0 | 6,366 | 5,966 | 0 | 2 (191 / 143) | 20 of 51 (see below) | 1 of 4 |
| zm_asylum_sh | 1,641 | 0 / 0 | 47,422 | 34,901 (34,881 walk + 20 negotiation) | **0** | 5 (1,626 / 15) | 0 of 38 | 0 of 21 |

zm_prototype_sh after-fix histogram: link 5,936; forward hit 3,000
(monsterclip 0x8030200/0x8020000 and walls 0x1/0x8000001, i.e. real
barriers); arrival dz>18 21; no floor within drop 7; forward startsolid 2.
Every spawner (42) and every exterior_goal (12) sits on the 710-node main
component; the 5 nodes off it are two islands of 3 and 2.

zm_zombie_training is a map-data fact, not a link defect: its 334 nodes
form two areas (191 at z~450 spanning y 3600..4275, 143 at z~250 spanning
y 543..1700) with no nodes between them, and 45 of its 51 `zombie_spawner`
structs have no `target` at all and sit in regions with no nodes (e.g.
(2086,76,18) whose nearest node is 900+ units away at (1221,1483,241)).
The 6 spawners that DO target nodes (pf0_auto503/504/505) resolve and link.
The load-time census will print exactly these so they can be fixed as map
data (add nodes / targets) rather than masked.

### 5b. zm_asylum_sh

1,641 nodes all drop cleanly (0 in solid, 0 floating). 47,422 candidate
pairs (about 29 per node): link 34,881; forward hit 12,435 (monsterclip
0x8030200/0x8020000 and walls 0x1/0x8000001); arrival dz>18 78; no floor
13; forward startsolid 11; down startsolid 4. 5 components: 1,626 on the
main one and 15 off it in islands of 9, 2, 2, 2. All 38 spawners and all
21 exterior_goals are on the main component. The per-node average of ~21
links leaves headroom under the 48 cap; the native histogram's `link cap`
counter will say if any node exceeds it.

## 6. What the next boot prints (and how to read it)

    CoDOL waypoint graph: 715 map nodes dropped to the floor (0 in solid, 0 floating, 0 landing in solid skipped); connecting (T5 Path_ConnectPaths rule)...
    CoDOL waypoint graph: built from the map in N ms: 715 nodes, ~5950 links (12 negotiation, F flat fast-path), 0 nodes with no link leaving them, S with none entering, 3 components (main 710 nodes, 5 off it)
    CoDOL waypoint graph: link test census: fwd hit solid=... fwd hit monsterclip=... arrival dz>18=... no floor within drop=... link=...
    CoDOL waypoint graph: 42 zombie_spawner (0 off the main component), 12 exterior_goal (0 off)

Before those, up to 6 `ERROR: Pathnode (...) is floating / is in solid /
lands in solid` lines and up to 6 `has no connections leaving it` lines
(T5's wording), and up to 6 `... is off the main component` lines.

If the native census disagrees with the table above, the histogram says
which exit moved. The one known stack difference: the oracle is alpha0022's
Python (brushes + terrain); the server is the retained CoD4 `cm` (SSE), so
small counts (the 21 arrival and 7 no-floor pairs) may shift; the link
count and the 0 isolated should not.

## 7. Offline iteration

There is no native offline clipmap loader that reaches `G_TraceCapsule`
without a server (`tests/test_codol_collision_native.c` builds a synthetic
map; `tests/test_codol_assets.c --contents` loads a real zone's collision
staging but not into `cm`, and the crash harness `bin/START-CRASH-TEST.cmd`
is a full server on port 17799, which this worker may not start). The
oracle script `tools/codol_path_link_census.py` is the offline path: it
takes `--height/--lift/--arrive/--drop/--step/--mask/--dropfloor/--point`
so any rule change can be predicted before a boot, and the native build
prints the same histogram so one boot confirms it.

## 8. Not done / for the parent

- Link + boot + compare the native census with section 5.
- `codol_actor_lifecycle.cpp` (not mine): its "no clear nav node within 256
  to snap to" and goal-reach distances now compare against FEET-height
  node points instead of points ~28 above the floor. That is the correct
  frame for an actor origin, but if any of its checks assumed the old
  offset (e.g. a 3D distance with a tight z tolerance), it will now be
  looser in z by ~28, not tighter. No patch needed on the evidence seen;
  flagging it.
- zm_zombie_training's node coverage (section 5) is a map-data item.
