# zm: zombies through the windows -- 2026-09-21

Build 518b3190, zm_prototype_sh, `bin/home/main/qconsole.log` (one session,
6 zombies, ~4,400 `CoDOL actor:` lines).  User report: "the zombies get
stuck at the windows."  Every claim below is MEASURED (log, source, offline
trace, zone blob) unless marked INFERRED.

## 0. Headline

Three separate things were "stuck", and none of them was the 15-unit rise
the last pass worried about:

1. **At the window (ent 581, pf4):** the zombie stood on the negotiation
   begin node pushing into the boards with real root motion (`rm 0.32`,
   `moved 1-5/s`).  The boards and the clip brush were solid because **the
   tear never ran**: not one boardtear clip was played in the whole session
   (`grep boardtear qconsole.log` -> 0).  Two causes, both in the port:
   the entrance walk gave up after 20 s (a walk cycle needs 45-70 s to cover
   the 700-1100 units from a yard spawner to its window), and once in the
   chase the native perception pass re-targeted the goal at the player every
   frame, so the script's `setGoalPos( attacking_spot )` held for one frame
   and `wait_until_at_spot` timed out on every zombie.
2. **Even with the boards gone, the sill is a 42-unit world brush** (pf4:
   floor z 1 at y 1030, 13 at 1024, 42 at 1018, 34 at 1012, 2 at 1006) under
   a lintel leaving ~108 units of headroom at the begin node.  An 18-unit
   step never clears it; the map says so itself -- every begin node carries
   `animscript "zombie_mantle_over_40"` (12/12 on zm_prototype_sh, 20/20 on
   zm_asylum_sh, 4/4 on zm_zombie_training).  The mover needed T5's
   negotiation state, not a bigger step.
3. **In the yard (ent 576, the `stuck at (629 1999 1)` / `(773 1523 1)`
   lines):** clear, flat floor (offline capsule sweep to the next route node:
   fraction 1.000, floor z 1.1 the whole way) and `rm (0.00 0.00 0.00)`,
   always with `ai_zombie_walk_v7` at t 0.37-0.49.  The clip's own delta
   track is exactly zero from t 0.353 to 0.579 -- an authored one-second
   pause -- and the stuck detector read that as a wedge, repathed, then
   "regoal"-snapped the zombie back to the previous node every two seconds.
   That loop is what kept ent 576 oscillating between (814 1617) and
   (773 1523) for the whole match.

## 1. Measurements

### 1.1 The window (offline, `pmove.World('zm_prototype_sh')`, actor hull 30x30x72, mask 0x2820011)

Sweep begin node 360 (457 1047 1) -> end node 359 (457 983 1):

| lift | result |
|---|---|
| 0 | fraction 0.093, hit world brush 7922 (CONTENTS_SOLID), normal +y: the sill face |
| 18 / 30 | fraction 0.171, brush 11724 contents 0x8030200 (a clip on the sill) |
| 36 | startsolid (brush 2) |
| 40..48 | startsolid brush 6443 (CONTENTS_SOLID): the lintel/awning above the begin node |
| 56 | startsolid 0x8020000 |

Floor under x=457: y 1040 -> 1.1, 1030 -> 1.1, 1024 -> 13.2, **1018 -> 42.0**,
1012 -> 34.5, 1006 -> 2.3, 996 -> 2.0.  Both graph nodes are on the floor
(z 1), so the "15-unit rise" of the previous doc was the RAW node origins
(31 -> 31, not a rise either); the actual obstacle is the 42-unit sill
between them.

The barrier entities at that window (mapents, `pf4_auto1`): clip `*1` at
(458 1018 57) with `spawnflags 1`, six board chunks `*2..*7` (script_noteworthy
1..6, z 42..83), the attack-spot struct at (457 1018 23) radius 36 height 64,
and the `exterior_goal` at (457 1066 27) angles (0 270 0).

### 1.2 What ent 581 did (log)

- 548: `goal set x1 (457 1066 27) ... radius 128` -- the entrance goal; route
  `34 -> 360: 6 nodes` (360 = pf4's begin node).  The walk at 13-20 u/s.
- 1179 (about 20 s later, still 650 units out): `goal set x1 (-154 262 1)
  ... radius 4` -- `zombie_wait_goal( 20 )` timed out, `tear_into_building`
  set the spot and timed out 6 s later, `zombie_setup_attack_properties`
  ran, the chase began.
- 2633: `goal set x15 (457 1052 1)` -- the seek loop's
  `nearest_blocking_barrier` -> `tear_into_building` did set the attack spot
  (spot 0 = (457 1052)); 2843: the goal is the player again from
  (465 1068): the native chase overrode it.
- 3084-3653: at (463..469 1038 1), `moved 1-5/s`, `rm 0.32`, `orient 1`,
  route `360 -> 683` cursor 1 (the leg 360 -> 359 through the window),
  `anim ai_zombie_walk_v9 w 1.00`: walking into the boards.

### 1.3 What ent 576 did (log)

Every `stuck at` line of ent 576 after line 1249 is at (767..780 1521..1527)
or (801..812 1613..1622); the diag line at each carries `rm (0.00 0.00 0.00)`,
`vel (0 0 0)`, `phys ok 60 rej 0`, and `ai_zombie_walk_v7 ... t 0.367 /
0.370 / 0.374 / 0.414 / 0.416 / 0.421 / 0.457 / 0.481 / 0.483 / 0.488`.
Offline: the route leg it was on (node 550 (814 1617) -> 634 (714 1388))
sweeps clear at lift 0 and 18, the standing probe at (773 1523 1) is clear,
and no map entity is within 130 units.

### 1.4 The clips (zone blob, `obj/claude-workers/xanim_probe.py common_gametype_zm`)

| clip | frames | root motion frame 0 -> last (x fwd, y, z) | notetracks |
|---|---|---|---|
| ai_zombie_boardtear_m_1 / l_1 / r_1 | 94 / 69 / 85 | none (delta container present, all track pointers NULL) | **board** @0.596 / 0.551 / 0.576, end @1.0 |
| ai_zombie_traverse_v1 | 58 | (+64.6, +0.7, +10.9), z dips -2.7 @0.28, peaks +19.6 @0.86 | traverse_v1 @0.05, footsteps, **gravity on** @0.897, blend @0.948, end |
| ai_zombie_traverse_v2 | 44 | (+70.1, -6.3, +18.6) | traverse_v2, footstep, **gravity on** @0.932, blend, end |
| ai_zombie_traverse_v5 (run) | 47 | (+62.7, +4.2, 0) | sndnt#, footsteps, **gravity on** @0.894, blend, end |
| ai_zombie_traverse_v6 / v7 (sprint) | 34 / 42 | (+108.6, +5.7, 0) / (+71.4, +3.1, 0) | footsteps, **gravity on** @0.91 / 0.98, blend, end |
| ai_zombie_traverse_crawl_v1 / v4 | 230 / 103 | (+76.8, +2.6, 0) / (+68.8, +15.7, 0) | bodyfall, **gravity on** @0.85 / 0.95, blend, end |
| ai_zombie_walk_v7 (loop) | 133 | (+102.1, +1.3, 0), **|delta| = 0.000 for f47..f77 (t 0.353-0.579)** | sndnt# steps, end |

So: the tear clips DO carry the `board` note the port waits for; the traverse
clips carry exactly the 64-unit window link and hand physics back with
`gravity on`; and the yard stall is authored into walk_v7.  (Decoding note:
translation = mins + size * u16 raw, confirmed by v1 landing on 64.6 units.)

## 2. T5's sequence vs this port

| step | T5 (`_zombiemode_spawner.gsc`, `actor_negotiation.cpp`, `animscripts/traverse/*`) | before this pass | now |
|---|---|---|---|
| paths | the clip brush (spawnflag 1 = DISCONNECT_PATHS) cuts the window's negotiation link at spawn | the map build linked every begin -> end from the start; a chasing zombie could plan through untorn boards | `blocker_init`: `clip disconnectpaths()` (new native method, T5 `Path_DisconnectPaths` over the map graph); the repair loop cuts it again |
| entrance | `goalradius 128; SetGoalPos( node.origin ); waittill( "goal" )`; `zombie_assure_node` moves to the next closest entrance on `bad_path` | `zombie_wait_goal( 20 )` -- always timed out | `zombie_wait_entrance()`: waits for `goal`, on `bad_path` tries the rest of `entrance_nodes` then the 20 closest, each once |
| tear | `get_attack_spot`, `goalradius 2; SetGoalPos( spot ); waittill( "goal" )`, `AnimScripted` tear clip, `"board"` note -> `remove_chunk` | spot goal overridden by the native chase each frame; 6 s timeout; never reached the clip | `tear_into_building` runs with `ignoreall = true` (script owns the goal, which IS T5's contract -- T5 has no native chase), `wait_until_at_spot` accepts the native `goal` notify or 32 units, 15 s bound; `board` note removes the chunk, and a clip that ends without it removes the chunk anyway with a log line |
| open | `clip disable_trigger(); clip connectpaths()` (:601) | `disable_trigger` per board; no connectpaths (did not exist) | `open_barrier_paths( node )` after both tear sites: `disable_trigger` + `connectpaths` (native `Path_ConnectPaths`: restores the links THAT entity cut, wherever it now is) |
| traverse | `Actor_Negotiation_Start` at the begin node -> node animscript (`zombie_mantle_over_40::wall_hop_zombie`) in `AI_ANIM_USE_BOTH_DELTAS_NOCLIP`; cleanup: velocity 0, nearest node := end, recalc path | nothing: the mover walked the link with the walk clip and an 18-unit step into a 42-unit sill | native negotiation state (below) + `zombie_jump.gsc` = the T5 traverse script |
| after | `zombie_setup_attack_properties`, `find_flesh`; waits `zombie_start_traverse` / `zombie_end_traverse` | in place | in place; the jump script sends both notifies |

## 3. The change

### 3.1 `src/codol/player/codol_bot_nav.c/.h`

- `node_t` gains `record` (the map entity record behind the node, for its
  `animscript`/`angles`), `negotiationEnd` (a begin node's end node) and a
  per-link `blocker[]` (entity number + 1 of the cutter).
- `CODOL_BotNavNegotiationEnd`, `CODOL_BotNavRecord`, `CODOL_BotNavLinkBlocked`.
- `CODOL_BotNavDisconnectPaths( entnum, mins, maxs )`: every link whose
  segment, swept as the T5 actor hull (+-15 xy, 0..48 z -- the node points
  are on the floor, the clip's bottom is ~25 up), crosses the box is cut and
  tagged; `CODOL_BotNavConnectPaths( entnum )` restores that entity's cuts.
  The planner skips cut links.

### 3.2 `src/codol/player/codol_actor_lifecycle.cpp`

- **Route follower**: a begin node whose end node is the next leg is
  reached (24 units), never bypassed by the "behind me" rule; reaching it
  raises `negotiationPending`.
- **`ActorStartNegotiation`** (T5 `Actor_Negotiation_Start`): refuses if the
  link is cut; aligns the actor to the begin node (T5's `AnimScripted` lerp;
  the remainder is <= 24 units) facing the node's `angles`; zeroes momentum;
  enters the species' traversal animscript -- this port's `jump` slot --
  with `main( begin_origin, begin_angles, end_origin, animscript )`
  (parameters pushed last-first through `CODOL_ActorSwitchScript`); holds
  `safeToChangeScript = 0`.
- **`ActorNegotiationFrame`** (T5 `Actor_Negotiation_Think`): while the
  thread lives (8 s cap) the frame is facing + `CODOL_ActorAdvanceGoalAnimation`
  only -- no chase goal, no route, no stuck detector, no re-selection.
  The script's `animmode( "noclip" )` makes that root motion, z included,
  the actor's movement (mode 5 -> physics noclip), which is how the sill is
  crossed.
- **`ActorFinishNegotiation`** (T5 cleanup): if the actor did not end closer
  to the end node than the begin node, or ended in solid, it is snapped to
  the end node (lifts 1/20/44) and the line says `SHORT`; otherwise the
  crossing is logged with the distance to the end node.  Velocity zero,
  route dropped (re-planned from the end node), modes cleared.
- **Stuck detector**: accumulates the root motion the clip ASKED for
  (`stuckAttempt`).  No displacement with < 8 units asked for is a clip
  stall: one line per actor, no repath, no regoal.  A real wedge next to a
  negotiation node prints once, `window stuck detail:` -- the capsule sweep
  to the end node (fraction, hit kind, entity classname, contents/surface
  flags, material), begin/end node z, the link's cut state and cutter, the
  animscript, `rm` and the attempted motion.
- **`<entity> disconnectpaths()` / `connectpaths()`** registered as entity
  methods.

### 3.3 GSC (`bin/home/codol_rawfiles/zm/...`)

- `maps/mp/animscripts/zombie_jump.gsc` -- rewritten as T5
  `animscripts/traverse/zombie_mantle_over_40` + `shared::DoTraverse`: clip
  by `zombie_move_speed` (walk v1/v2, run v5, sprint v6/v7, crawler
  crawl_v1/v4), `zombie_start_traverse`, `orientmode( "face angle" )`,
  `animmode( "nogravity" )` + `animmode( "noclip" )`,
  `setFlaggedAnimKnobAllRestart( "traverseanim", ... )`, notetracks until
  `end` with `gravity on` -> `animmode( "gravity" )`, `zombie_end_traverse`.
- `maps/mp/gametypes/_zombiemode_spawner.gsc` -- `zombie_wait_entrance` /
  `next_entrance_node` (T5 `zombie_assure_node`), `open_barrier_paths`,
  `tear_into_building` wrapped with `ignoreall`, `wait_until_at_spot` on
  the native `goal`, the tear-clip-ended-without-note arm, and
  `codolprintln` lines at each stage (developer 0).
- `maps/mp/gametypes/_zombiemode_blockers.gsc` -- `disconnectpaths` at
  `blocker_init` and after each repair.

### 3.4 Which of the three options was implemented

**TEAR + TRAVERSE, the T5 sequence.**  The traverse is the real
`ai_zombie_traverse_*` clip playing through the window in T5's
noclip/nogravity mode, driven by the native negotiation state with the
pieces this server already had (`animmode`, `orientmode`, the flagged
knob-all, notetrack delivery).  T5's `AnimScripted` builtin itself is still
not registered; its one job here -- placing the actor on the begin node
facing the node's angles before the clip -- is done natively at negotiation
start.  The "step over" fallback was NOT used: the sill is 42 units, not 15,
and no step height that clears it would be honest.  The one fallback that
remains is inside `ActorFinishNegotiation`: a clip that ends short (or a
timeout) snaps the actor to the end node and says `SHORT` in the log.

## 4. What the user should see in the log as a zombie comes through

    CoDOL actor: ent 2xx disconnectpaths: 1 links cut inside (...)-(...)          <- x12 at init, one per window clip
    CoDOL actor: ent 576 goal set x1 (457 1066 27) from (...) radius 128
    CoDOL actor: ent 576 route node 34 -> 360: 6 nodes
    CoDOL actor: ent 576 not moving for 1000 ms but the animation asked for only 0.0 units of root motion (clip stall, not wedged; route kept): anim ai_zombie_walk_v7 ...   <- once, on walk_v7's pause
    CoDOL zm: ent 576 tearing board 6 at (456 1018 42) (barrier (457 1066 27))
    CoDOL anim: setflaggedanimknoballrestart() ent 576 ... 'ai_zombie_boardtear_m_6' ...
    ... x6 ...
    CoDOL zm: ent 576 barrier (457 1066 27) is open
    CoDOL zm: ent 576 opened the window at (457 1066 27) (clip dropped, paths connected)
    CoDOL actor: ent 2xx connectpaths: 1 links restored
    CoDOL actor: ent 576 goal set x1 (<player>) ... radius 4
    CoDOL actor: ent 576 route node 360 -> 5xx: N nodes
    CoDOL actor: ent 576 negotiation start: node 360 (457 1047 1) -> node 359 (457 983 1) animscript 'zombie_mantle_over_40' yaw 270; aligned from (46x 104x 1)
    CoDOL actor: ent 576 animscript -> traverse (jump) (moveMode 0 animMode 1)
    CoDOL anim: setflaggedanimknoballrestart() ent 576 ... 'ai_zombie_traverse_v1' ...
    CoDOL actor: ent 576 negotiation complete after ~2000 ms: (457 1047 1) -> (457 98x z), end node D away, dz Z
    CoDOL actor: ent 576 animscript -> dog_move (moveMode 3 animMode 1)
    CoDOL actor: ent 576 route node 359 -> 5xx: N nodes                             <- inside, on the interior graph

Failure signatures, each of which names its cause:

- `negotiation ... SHORT: ... snapped to end node` -- the traverse clip's
  root motion did not reach the server's mover (the delta path), or the 8 s
  cap hit; the zombie is inside anyway.
- `tear clip ended without its board notetrack` -- notetrack delivery
  dropped the `board` note (MEASURED present in the clip); board removed at
  the end.
- `did not reach attack spot ... in 15 s` -- the walk to the spot failed
  (a wedge at the window: look for the `window stuck detail:` line).
- `bad_path to entrance ... trying ...` / `found no reachable entrance` --
  the yard graph does not reach that window (component census).
- `negotiation start: the traversal animscript could not be entered` --
  a pain/death script held the actor at that frame.

## 5. Not in this pass

- Walk speed.  The zombies cover 13-20 u/s against T5's ~23 (walk_v7's own
  102 units / 4.43 s); the anim-smoothness owner has the delivery side.
  The entrance walk no longer times out, so this only costs time.
- `AnimScripted` as a builtin (the sidestep, taunt and window-attack clips
  that T5 plays with it still play in place).
- Dogs: no `_jump` change; the mp CSV graphs carry no negotiation pairs, so
  a dog never enters the state.  When a hellhound species row lands, its
  `dog_jump.gsc` needs the 4-parameter `main` and T5's
  `dog_wall_and_window_hop` (`german_shepherd_traverse_up_40` ships in
  common_gametype_mp/coop).

## 6. Gates

`tools\BUILD-CODOL.ps1 -ObjectsOnly` -> build OK (exit 0), objects only, no
link, no promotion, server untouched.
`python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm`
-> exit 0 (955 builtins incl. the two new methods).
Line endings: all six files LF and unchanged in kind (0 CR before and after).
`src/codol/snapshot/*`, the frame builder, animation delivery and
`ActorDescribeTree` untouched.  Not booted here.

---

# Part 2 -- build 6f2b8e29 log: "some get stalled, some rubberband, none broke a window"

`bin/home/main/qconsole.log` (2,336 lines, one session, 14 zombies, rounds
1-3), build 6f2b8e29.  Every number below is from that log, the offline graph
(`obj/zm-mapents/zm_prototype_sh-graph.json`, the census walk that reproduces
the native node numbering), the alpha0022 collision oracle, or the zone.

## 7. The entrance was reachable; the entrance LIST was being burned

### 7.1 The cuts are correct (offline, our rule vs T5's)

`nav_segment_crosses_box` re-run over the 5,911-link offline graph with the
twelve clip boxes the log printed (lines 414-425):

| clip ent | links cut |
|---|---|
| 168, 456, 463, 470, 477, 484, 491, 498, 505, 512, 554 | exactly one: the window's `begin -> end` |
| 526 (pf1260, box (130 -900 1)-(223 -892 118)) | `712 -> 711` (begin -> end) **plus** `188 <-> 712`: node 188 (400 -882 1) sits inside the box's x-span and its hull-inflated y-span |

Under T5's rule (`Path_DisconnectPathsForEntity`, OpenBLOPS pathnode.cpp
:3182: capsule `{-15,-15,18}..{15,15,48}` swept node-to-node against the
entity only) the cut set is **identical** (14 links, symmetric difference
empty).  No yard -> begin link is cut anywhere: 712 keeps in-links from 173,
178, 179, 180, 181; 680 keeps six; 684 keeps seven.  The nearest node to
every exterior_goal is its `node_negotiation_begin` (stance 4 = NEGOTIATE),
never the end node.  So the hypothesis "the hull cuts the yard off from the
begin node" is **refuted by measurement**; the cut rule stays as it is.

### 7.2 What the `route FAILED ... 143 expansions` really was

Directed reachability with the cuts applied:

| start | reaches | begin nodes reachable |
|---|---|---|
| 379 (-1357 -838), the west yard | 143 nodes | 680, 682, 686 |
| 405 / 417 / 30 / 191 (east + south yards) | 242 nodes | 684, 688, 690, 694, 712, 714 |
| 634 (714 1388), the north pocket | 11 nodes | 360 |

The frontier "exhausted after 143 expansions" is the whole west yard; window
pf1260 at (177 -943) is a south-yard window.  `pick_entrance_node` chooses
among the three straight-line-closest exterior_goals, and from (-1329 -907)
that set includes a window in another yard.  T5 does exactly this and moves
on with `bad_path` -> next entrance; so did we: line 467 tries (-266 -752)
and line 468 plans `379 -> 680: 9 nodes`.  **The first `bad_path` per
zombie is T5 behaviour, not a fault.**

The cycling through all twelve came from somewhere else.  Every later
`bad_path to entrance` of ents 576/577/581/580/578/583 is preceded by
`stuck ... -> regoal` / `stuck: snapped to nav node`: the stuck detector's
second strike **notified `bad_path`**, and `zombie_wait_entrance` took that
as "this entrance is unreachable" and advanced the list.  581 and 577,
wedged at (1400 -7xx 8) with a perfectly good route (`405 -> 712: 9 nodes`,
line 890), burned all twelve entrances in 220 s that way (lines 901-1112).
ent 586, which spawned in the right yard and hit nothing, walked `420 -> 712:
7 nodes` straight to the window and printed `tearing board 6` (line 1799).

### 7.3 Why no window was ever opened (the real blocker)

Four zombies reached a window and printed `tearing board 6` (580 line 1391,
579 1431, 586 1799, 589 2251).  Not one printed a second board, `barrier ...
is open`, or `tear clip ended without its board notetrack`, and there is no
`boardtear` anywhere in the log.  Their per-second diag after the tear line:
`anim ai_zombie_walk_fast_v3 w 1.00 g 1.00` (586), `ai_zombie_walk_v1 w 1.00`
(589), `ai_zombie_walk_v4 w 1.00` (580), records 11 -> 13 (the tear clip
entered the tree) but the walk cycle held weight 1 until death.

Cause: `tear_into_building_inner` published the tear with
`setFlaggedAnimKnobAllRestart` from the entity's own thread and set
`safeToChangeScript = false` to keep the NATIVE from switching animscripts.
That does nothing to the animscript that is already running:
`zombie_move::MoveStandRun` re-applies `setFlaggedAnimKnobAll("runanim",
walk, %body, 1, 0.2)` every `zombie_run_anim_update_time`, which knobs every
sibling -- the tear clip -- back to goal weight 0 within 0.2 s.  A clip at
weight 0 delivers no notetracks, so `zombie_tear_notetracks` waited for
`"board"` forever.  T5 avoids this by construction: `AnimScripted` pushes
`AIS_SCRIPTEDANIM` and calls `Actor_KillAnimScript` (OpenBLOPS
g_scr_main_mp.cpp:20578 `GScr_StartScriptedAnim_SP`), then runs
`animscripts/zombie_scripted.gsc`, which publishes the clip with the flagged
knob-all and simply waits.  There is no move loop left to fight it.

(The seven `script runtime error` blocks in the log are one bug:
`attacker.kills++` on a float field, `_zombiemode_spawner.gsc:1059`, thrown
on every zombie death before the drop roll.  Fixed with `+ 1`.)

## 8. The stalls and the rubberband

### 8.1 Clip stalls (`asked for only 1.5 / 6.0 / 7.2 units`) are real

`obj/claude-workers/xanim_probe.py common_gametype_zm ai_zombie_walk_v3
ai_zombie_walk_v9`:

- walk_v3 (107 frames, 133.7 units): per-frame steps fall to 0.04-0.35 from
  f62 to f80 (t 0.58-0.75) -- 1.9 units over 18 frames.  The line at 658 was
  at t 0.722, rate 0.55: 1.5 units asked in a second is exactly that.
- walk_v9 (132 frames, 114.9 units, only 5 delta keyframes): position is
  constant from f44 to f63 (t 0.333-0.477) and from f91 to f111 (t
  0.689-0.841).  Lines 689/714 were at t 0.434 / 0.408: inside the first
  plateau.  The detector reads the delta correctly; nothing to fix.

### 8.2 The wedge at (1400 -7xx 8) is a groove behind a slab lip -- and so is every other one

No map entity within 200 units (the only thing there is a `script_origin`
at z 664).  The oracle floor along the route leg 405 (1438 -777 17.6) ->
410 (1312 -759 1.1), point trace, x stepping west:

    1408 -> 9.4   1400 -> 7.1   1392 -> 8.5   1384 -> 1.0   1376 -> 1.0

A raised slab descending from 17.6 to 8.5 whose top has a **1.4-unit groove
right behind its western lip**, then a 7.5-unit drop to the yard floor.
The same shape at every wedge spot of the session (hull floor / point floor
under the actor / lip 8 units on):

| spot (log) | hull | point | lip | zombies |
|---|---|---|---|---|
| (1400 -755 8) | 8.5 | 7.1 | 8.5 | 581, 577 (lines 889-1104) |
| (1398 -774 8) | 8.6 | 6.5 | 8.5 | 581 (1271-1299) |
| (1414 -1098 8) / (1416 -1097 8) | 8.2 | 7.2 | 8.5 | 578 (1237), 582 (2089) |
| (844 -843 8) | 8.2 | 7.1 | 8.5 | 578 (1492) |

The capsule settles into the groove (origin z 7-8), its 30-unit footprint
overlaps the 8.5 lip, and from there every sweep starts solid: `phys ok 7
rej 53`, `grounded 0`, `vel (-11 0 0)`, frozen.  The map build's link walk
(census: step 8, lift 18) never sees it because it starts each step lifted.
Not an entity, so T5's DISCONNECT_PATHS is not the answer; it is a physics
seam.

### 8.3 The rubberband and the second false wedge

`stuck: snapped to nav node 405 (1438 -777 19)` fired 14 times for 581/577
alone -- a 40-unit teleport back onto the slab every second, then the walk
down into the groove again; with actor origins on TR_INTERPOLATE (63850367)
that is the slide the user saw.  ent 576's oscillation at spawn (lines
643-668) was the OTHER false verdict: at (-1327 -844) it was walking
walk_v3's slow section (6-8 u/s at rate 0.55) with `phys ok 60 rej 0`; the
old rule "asked >= 8, moved < 8 in a second" called that a wedge, repathed,
snapped it to node 379 and sent `bad_path` -- which is how the west-yard
zombie lost its good entrance (-266 -752) at line 668.

## 9. The change

### 9.1 `animscripted` / `stopanimscripted` (T5 AIS_SCRIPTEDANIM), native

- `src/codol/script/codol_script_anim.c`: `animscripted( notifyName, origin,
  angles, %anim [, mode [, %root [, rate [, goalTime]]]] )` with T5's
  4..8-parameter contract and dead-AI refusal; default root = %body (the top
  of the clip's ancestry below the tree root, as `zombie_scripted::init`
  defaults it); publishes the clip through the same `anim_publish` as
  `setflaggedanimknoballrestart` (complete + restart, weight 1, the notify
  name), so notetracks reach the script unchanged.  `stopanimscripted()`.
  Registered in `src/scr_vm_main.c` (957 builtins).
- `src/codol/player/codol_actor_lifecycle.cpp`: `CODOL_ActorScriptedAnimBegin`
  = `Actor_KillAnimScript` (the move loop dies, "killanimscript") + the state:
  `safeToChangeScript 0`, no goal/route/selection/stuck detector, face the
  given yaw, consume the origin offset at <= 120 u/s (T5
  `GScr_UpdateScriptedAnim` consumes it per tick rather than snapping), root
  motion by the given animmode with `moveMode 0`.  Popped by
  `stopanimscripted`, by the clip's length / rate + goalTime + 0.5 s, or by
  death.  Log: `animscripted: N ms at (...) yaw Y mode normal, from (...) D
  away` / `animscripted stopanimscripted|ran its length after N ms`.
- GSC: the tear (T5 :405 shape), the taunt (:437) and the window reach (:471)
  call `animscripted`; the loop exits call `stopanimscripted`; the two
  port-added `endon("killanimscript")` in `zombie_tear_notetracks` and
  `do_a_taunt` are removed (T5 has `endon("death")` only -- they attached to
  the calling `zombie_think` thread and the kill notify would have ended it);
  `zombie_shared::HandleNoteTrack` "stop anim" now calls `stopanimscripted`.

### 9.2 Physics: unstick and near-ground step (`codol_actor_physics.cpp`)

- A move whose start is in solid lifts the start by 2-unit steps up to the
  step height until the capsule stands clear, counts `unstuck`, and proceeds
  as grounded.  An actor clear nowhere within a step is still refused.
- The step-up branch also runs when the 0.25-unit ground trace hit a lip or a
  wall (normal below .7) but there is floor within one step below.
- `codol_actor_physics_t` gains `blocked` (the move achieved under half of
  its asked horizontal displacement) and `unstuck`.

### 9.3 Stuck detector: a wedge is what the physics refused

- Verdict: asked >= 8 and moved <= 8 in a second AND (`rejected > 0` or
  `blocked >= 15` frames).  Otherwise `moved under 8 units ... but physics
  accepted every move ...: a slow cycle, not a wedge; route kept` once, and
  the window resets.
- First strike: `stuck at (...) (asked A, physics rejected R, throttled T,
  unstuck U) -> repath` and the route is dropped.  Second: `-> unwedge`, a
  12-unit sidestep (`CODOL_ActorMoveDelta`, capsule-checked); only an actor
  that is startsolid where it stands is placed on the nearest clear node,
  and only within 64 units (`embedded in solid: placed on nav node ...`).
- **No `bad_path` from the stuck handler.**  That notify is the planner's
  (T5 Path_FindPath); `ActorRouteFailed` still sends it on a real route
  failure.  The entrance list is no longer consumed by wedges.
- `wedge detail` on every real wedge, once per actor per 48-unit spot:
  standing probe, floor 18 down (fraction / normal z / hit), 16 units ahead
  at floor level and at +18 (hit kind, entity classname, id, contents, surf,
  material, normal), nearest node and route leg, the physics counters, the
  velocity and the tree state; the `window stuck detail` line follows when a
  negotiation node is at hand.

### 9.4 Not changed, on purpose

- `CODOL_BotNavDisconnectPaths` / the cut rule (7.1).
- `pick_entrance_node` / `zombie_wait_entrance`: the first `bad_path` on a
  cross-yard pick is T5's own `zombie_assure_node` flow.
- The clip-stall branch (8.1).

## 10. What the user should see now, for one zombie

    CoDOL actor: ent 5xx goal set x1 (177 -944 30) from (361 -1611 2) radius 128
    CoDOL actor: ent 5xx route node 420 -> 712: 7 nodes
    CoDOL zm: ent 5xx tearing board 6 at (178 -895 45) (barrier (177 -943.5 30))
    CoDOL actor: ent 5xx animscripted: 3333 ms at (205 -929 26) yaw 90 mode normal, from (204 -932 1) 3 away
    CoDOL anim: animscripted() ent 5xx ... 'ai_zombie_boardtear_m_6' root 2 '#2(blend)' weight 1.00 ... restart
    CoDOL zm: ent 5xx tearing board 4 ...                                          <- x6, one per board
    CoDOL zm: ent 5xx barrier (177, -943.5, 30) is open
    CoDOL actor: ent 5xx animscripted stopanimscripted after N ms at (...)
    CoDOL zm: ent 5xx opened the window at (177, -943.5, 30) (clip dropped, paths connected)
    CoDOL actor: ent 526 connectpaths: 3 links restored
    CoDOL actor: ent 5xx animscript -> dog_move (moveMode 3 animMode 1)
    CoDOL actor: ent 5xx goal set x1 (<player>) ... radius 4
    CoDOL actor: ent 5xx route node 712 -> 5xx: N nodes
    CoDOL actor: ent 5xx negotiation start: node 712 (177 -925 1) -> node 711 (177 -861 1) animscript 'zombie_mantle_over_40' yaw 90; aligned from (...)
    CoDOL actor: ent 5xx animscript -> traverse (jump) (moveMode 0 animMode 1)
    CoDOL anim: setflaggedanimknoballrestart() ent 5xx ... 'ai_zombie_traverse_v1' ...
    CoDOL actor: ent 5xx negotiation complete after ~2000 ms: (177 -925 1) -> (177 -86x z), end node D away
    CoDOL actor: ent 5xx route node 711 -> 5xx: N nodes                             <- inside

And for the yard:

    CoDOL actor: ent 5xx moved under 8 units in 1000 ms with 9.4 asked for, but physics accepted every move ...: a slow cycle, not a wedge; route kept
    CoDOL actor: ent 5xx wedge detail at (1400.2 -755.1 7.9) heading (-0.99 0.05): standing IN SOLID; floor 18 down: ... ; ahead 16: fraction 0.00 startsolid 1 hit world ... material ...; physics rejected 53 throttled 60 unstuck 0 ...
    CoDOL actor: ent 5xx stuck at (1400 -755 8) for 1000 ms (asked 21.3, physics rejected 53, throttled 60, unstuck 0) -> repath

with `unstuck` climbing and the actor walking off the slab in the frames
after it, no `snapped to nav node`, no `bad_path to entrance` from a wedge.
If a wedge still holds, the `wedge detail` line names the surface.

## 11. Gates

`tools\BUILD-CODOL.ps1 -ObjectsOnly` -> build OK (exit 0); the only warnings
in the touched files are the three pre-existing ones (lines 880/1620/1788).
`python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm`
-> exit 0, 957 builtins.  Line endings: `codol_actor_physics.cpp/.h` and
`scr_vm_main.c` CRLF, edited byte-wise; the rest LF; each unchanged in kind.
`src/codol/snapshot/*`, the frame builder, `sv_main.c`, `sv_client.c`,
`engine_state`, `ActorDescribeTree` untouched.  Not booted here.
