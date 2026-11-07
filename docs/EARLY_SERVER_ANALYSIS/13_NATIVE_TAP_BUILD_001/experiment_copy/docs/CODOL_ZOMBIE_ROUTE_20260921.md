# zm zombie routing on a connected graph -- 2026-09-21

Build de015044, zm_prototype_sh, bin/home/main/qconsole.log lines 271-290 and
440-520.  The map-built waypoint graph is sound (715 nodes, 5957 links, every
zombie_spawner and exterior_goal on the 710-node main component) and yet every
zombie printed

    CoDOL actor: ent 576 route FAILED (no path between nearest nodes) x1 in 0 ms: from (1964 -872 5) to goal (70 385 -16), 715 graph nodes

and never moved ("moved 0/s", "stuck ... -> repath/regoal" forever).

## The one reason

`ActorRouteEdge` (codol_actor_lifecycle.cpp) rejected every link touching a
CLIMB node, and the map build marked both ends of every
`node_negotiation_begin -> node_negotiation_end` pair CLIMB "so dogs/zombies
skip it".  On the zm maps those 12 window links are the ONLY links between
the spawner yards and the interior: with them removed the graph is not one
component but six, `[236, 200, 140, 110, 3, 2]`, and each spawner yard is
its own island.  The census said "connected" because it is an undirected
union over ALL links, filter included; the planner ran over the filtered
graph.  The same filter also made the entrance goal unreachable, because the
node nearest an `exterior_goal` struct IS its window's negotiation_begin
node (37 units away), and every link into a CLIMB node was refused.

## Measured node picks (tools/codol_path_link_census.py walk, obj/zm-mapents/route_probe.py)

Nearest-node selection is plain 3-D distance, no line-of-sight, no radius
cap (`CODOL_BotNavNearest`), and the dropped-to-floor z is used on both ends,
so the "nearest" picks are the right ones:

| actor / goal | nearest node | class | origin | dist | component |
|---|---|---|---|---|---|
| ent 576 spawner (1964 -872 5) | 616 | node_pathnode | (2038 -874 1) | 74 | main |
| ent 577 spawner (-1036 -205 7) | 260 | node_pathnode | (-1074 -172 -5) | 52 | main |
| ent 578 spawner (2045 60 3) | 669 | node_pathnode | (2035 6 1) | 55 | main |
| player (70 385 -16) | 584 | node_pathnode | (84 368 1) | 28 | main |
| exterior_goal (278 -257 33) | 684 | node_negotiation_begin | (258 -257 1) | 37 | main |
| exterior_goal (-268 487 25) | 686 | node_negotiation_begin | (-248 487 1) | 31 | main |

A* result, start 616 -> goal 584 (the logged failure):

- with the CLIMB filter: **no path; frontier exhausted after 236 expansions
  (the whole yard), 45 links rejected by the filter** -- all 45 are links
  into negotiation_begin nodes 684/712/680/... ;
- without it: path of 17 nodes
  `616 656 657 126 620 660 403 145 147 148 149 684 683 592 582 643 584`,
  through window pf1253 (684 -> 683), 112 expansions.

Start 616 -> entrance 684 (the goal the script set first): filtered **no
path** (same 236/45); unfiltered 12 nodes.  260 -> 584: filtered none
(140 expansions, 19 rejected); unfiltered 11 nodes via window pf1254
(686 -> 685).  669 -> 584: filtered none (236/45); unfiltered 15 nodes via
pf1267 (714 -> 713).

Negotiation links are one-way (begin -> end only), so the interior never
routes back out through a window; that is T5's semantics and stays.  Directed
reachability from a yard is 355-454 of 710 nodes: a yard reaches its own
windows and the whole interior, not the other yards, which is why
`pick_entrance_node` (closest 3 exterior_goals) matters -- an entrance in a
different yard is unreachable even unfiltered (616 -> 686: none).

## The second fault: the entrance goal was overridden by the chase

Line 443 `goal set x1 (278 -257 33) ... radius 128` is the script's entrance
goal; the FAILED line three lines later already carries the player's
position.  `spawn_zombie` called `zombie_setup_attack_properties()`
(`self.ignoreall = false`) at spawn, so the native perception pass (perfect
info for the zm species) acquired the player through the wall on the first
frame and `CODOL_ActorRunFrame` re-targeted the goal at the enemy every
frame.  T5 sets `self.ignoreall = true` / `self.ignoreme = true` in
`zombie_spawn_init` (:159-:160) and only calls `zombie_setup_attack_properties`
after the entrance and the tear (`zombie_goto_entrance` :620); `find_flesh`
clears ignoreme at :3934.  With the filter fix alone the first route would
have gone to the player directly, through boards that are still up.

## Changes

- `src/codol/player/codol_bot_nav.h/.c`
  - new stance `CODOL_BOT_NEGOTIATE` for map negotiation pairs; the CSV's
    `climb` (player mantle, bots only) keeps `CODOL_BOT_CLIMB`;
  - per-node undirected component label (`CODOL_BotNavComponent`), computed
    for CSV and map graphs;
  - `codol_bot_route_stats_t` / `CODOL_BotNavLastRouteStats()`: expansions,
    links the caller's filter rejected, and the stop reason of the last A*.
- `src/codol/player/codol_actor_lifecycle.cpp`
  - `ActorRouteEdge` accepts STAND, CROUCH and NEGOTIATE (T5 Path_CanLinkNodes
    links negotiation pairs for every actor; the traversal animation is the
    XAnim owner's work, the mover walks the 15-unit link meanwhile);
  - `ActorRouteFailedDetail`: once per actor, on "no path between nearest
    nodes", prints both node picks (index, origin, distance, stance,
    component) and the search's stop reason with its counters.
- `bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_spawner.gsc`
  - `spawn_zombie`: `ai.ignoreall = true; ai.ignoreme = true;` (T5 :159);
  - `zombie_think`: `zombie_setup_attack_properties()` + `ignoreme = false`
    after the entrance/tear step, before the find_flesh loop (T5 :620, :3934).

Objects-only build passes; `tools/codol_script_resolve.py --only zm` exits 0.
Not booted here (parent links and restarts).

## What the next boot should show

    CoDOL actor: ent N goal set x1 (278 -257 33) from (1964 -872 5) radius 128
    CoDOL actor: ent N route node 616 -> 684: 12 nodes
    CoDOL actor: ent N hp 150 org (...) moved 90/s goal (278 -257 33) route 3/12 enemy -1 ...

`enemy -1` until the boards are torn (ignoreall), then `goal set ... (player)`,
`route node 684 -> 584: ...` through the window and a non-zero `moved`.  If a
route still fails, the new line names why:

    CoDOL actor: ent N route detail: start node A (x y z) D away stance S component C -> goal node B (...) ... ; frontier exhausted after E expansions, K links rejected by the stance filter

`K > 0` with `stop = frontier exhausted` is a filter cut; `component` values
that differ are a real graph gap (the 3- and 2-node islands).

Open, not in this pass: the mover must physically clear the window sill on
the begin -> end link (physics step height), and `tear_into_building` must
actually remove the board collision before the interior leg starts.
