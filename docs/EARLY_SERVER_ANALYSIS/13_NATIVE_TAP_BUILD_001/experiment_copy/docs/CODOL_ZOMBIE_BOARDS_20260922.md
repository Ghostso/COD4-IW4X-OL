# zm: the torn board flies -- 2026-09-22

Build 35342873, zm_prototype_sh.  User report: "they tear down the windows
but the animation for the boards flying off isn't working."  Every claim
below is MEASURED (source, asm, map ents, zone listing) unless marked
INFERRED.  Nothing here was run live; see section 6 for the verify line.

## 0. Headline

**The board did not fly because our `remove_chunk` never launched it.**  On
the "board" notetrack the port did `update_states("destroyed") / hide() /
notSolid()` and returned -- its own header line said "state + Hide +
notSolid only".  T5's `remove_chunk` (`_zombiemode_blockers.gsc:1729`, the
"board" arm at :1900-:1990) does not hide the chunk on the note: it spawns a
`script_origin` launcher at the chunk, links the chunk to it, `MoveGravity`s
the launcher along a solved ballistic arc to a floor-traced landing point
100-124 units behind the barrier, spins it with `RotatePitch`, waits the
flight time, and only then hides the chunk.  The whole visual was dropped,
not stubbed by the engine: every builtin on that path is registered and has
a real body here (section 2).

## 1. T5 vs ours, the tear path line by line

T5 `maps\_zombiemode_spawner.gsc:1163-:1183` (the "board" notetrack) and
`maps\_zombiemode_blockers.gsc:1729` (`remove_chunk`, "board" arm).  Ours:
`bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_spawner.gsc`
`zombie_tear_notetracks` and `_zombiemode_blockers.gsc` `remove_chunk`.

| step | T5 | ours BEFORE | ours AFTER |
|---|---|---|---|
| note handler | `level thread remove_chunk( chunk, node, true, zomb ); chunk notify("destroyed")` (threaded off level; passes the barrier `node`) | `remove_chunk( chunk )` synchronous, no node | `remove_chunk( chunk, node, true, self )`; remove_chunk marks synchronously and threads the flight itself |
| audio | `chunk thread zombie_boardtear_audio_offset` (zmb_break_board, wait 0.3-0.6, zmb_board_slam) | same, already ported | unchanged |
| fx | `zombie_boardtear_offset_fx_horizontle/_verticle` (wood_chunk_destory = `impacts/fx_large_woodhit`, T5 `_zombiemode.gsc:1020`) | same, already ported (`level._effect["wood_chunk_destroy"] = loadfx("impacts/fx_large_woodhit")`) | unchanged |
| state | `update_states("mid_tear")` now, `"destroyed"` after the flight | `update_states("destroyed")`, `.destroyed = true` now | kept synchronous (see 1.1) |
| `chunk NotSolid()` | yes | yes | yes |
| launcher | `ent = Spawn("script_origin", chunk.origin); ent.angles = node.angles + (0,180,0)` | **dropped** | ported verbatim |
| distance | `dist = 100 + RandomInt(script_move_dist - 100)` (else `100 + RandomInt(100)`) | **dropped** | ported (guarded with `isDefined`/`int()`) |
| landing | `dest = origin + forward*dist; BulletTrace(dest+16z, dest-200z)`; fraction 1 -> `dest - 200z` else `trace["position"]` | **dropped** | ported verbatim |
| link | `chunk LinkTo( ent )` | **dropped** | ported |
| flight | `time = ent fake_physicslaunch( dest, 200 + RandomInt(100) )` -> `MoveGravity( velocity, time )` (`_zombiemode_utility.gsc:2381`) | **dropped, no fake_physicslaunch in the tree** | `fake_physicslaunch` ported into `_zombiemode_utility.gsc` (gravity 800, see 2.3) |
| spin | 60%: `ent RotatePitch(180, time*0.5)`; 40%: `ent RotatePitch(90, time, time*0.5)` | **dropped** | ported verbatim |
| end | `wait(time); chunk Hide(); wait(0.1); ent Delete(); update_states("destroyed"); notify("destroyed")` | `hide()` immediately | `wait(time); hide() (unless repaired meanwhile); wait(0.1); unlink; ent delete()` |
| repair | `replace_chunk`: show/solid/og origin+angles | same | plus: unlink from the launcher if repaired mid-flight |

### 1.1 Two deliberate differences (state, not visual)

* **State stays synchronous.**  T5 gates `all_chunks_destroyed()` on the
  post-flight `"destroyed"` state and its spawner tolerates a `mid_tear`
  chunk in the loop.  This port's tear loop (`tear_into_building_inner`) and
  `open_barrier_paths` were verified live on the synchronous state
  (docs/CODOL_ZOMBIE_WINDOW_20260921.md), so `update_states("destroyed")` and
  `chunk.destroyed = true` are still set on the note and only the flight is
  threaded (`remove_chunk_fly`).  Net effect: the zombie mantles the moment
  the last note fires, with the last board still in the air -- which is
  what T5 looks like too, since T5 threads the flight off level as well.
* **`chunk.in_flight`.**  A repair that lands inside the ~1 s flight would,
  with T5's code, `show()` a board still linked to a moving launcher and the
  flight thread would then hide the repaired board.  `replace_chunk` now
  unlinks first, and `remove_chunk_fly` only hides a board whose
  `.destroyed` is still true.

### 1.2 Not taken

The bar arm (:1770-:1900), the grate arm (:1995-:2060) and
`remove_chunk_rotate_grate` (:2083): no chunk of zm_prototype_sh is a bar or
a grate (all 72 are `script_parameters "board"`).  T5's clientside FX flag
path (`setclientflag ZOMBIE_SCRIPTMOVER_FLAG_*`) stays out for the reason
already in the blockers header (no client-script flag bits on this server).
T5's `draw_line_ent_to_pos` debug thread in `fake_physicslaunch` is dropped.

## 2. Builtin audit for the T5 board path

Registration is `src/scr_vm_main.c`; "body" is where the implementation
lives and what was checked in it.

| builtin | registered | body | verdict |
|---|---|---|---|
| `spawn` (function) | :398 `GScr_Spawn` | native | real |
| `linkto` | :778 `ScrCmd_LinkTo` | `_g_scr_main_mp.asm:9389` -> `G_EntLinkTo` (`_g_utils_mp.asm:582`) -> `G_EntLinkToInternal` + `G_CalcTagAxis`; 1-arg form takes the parent-only branch | real |
| `unlink` / `islinked` | :782/:784, :953 | `G_EntUnlink` (asm), `CODOL_Scr_IsLinked` (`codol_script_entity.c:135`) | real |
| `movegravity` | :925 `ScriptEntCmd_GravityMove` | `_g_scr_mover.asm:1623`: classname gate script_model / script_origin / script_brushmodel / +0x52; reads vector+float; writes `pos.trTime = level.time`, `trDuration = time*1000`, `trBase = currentOrigin`, `trDelta = velocity`, **`trType = 5` (TR_GRAVITY)**; `BG_EvaluateTrajectory`; `SV_LinkEntity` | real |
| `rotatepitch` | :927 `ScriptEntCmd_RotatePitch` | `_g_scr_mover.asm` -> `ScriptEnt_RotateAxis(ref, 0)` -> `ScriptEntCmdGetCommandTimes`: (deg, time [, accel [, decel]]), errors only if accel+decel > time | real |
| `moveto` / `rotateto` / `rotateyaw` | :921/:926/:928 | `_g_scr_mover.asm` | real (not needed by the board arm) |
| `bullettrace` | :174 `Scr_BulletTrace` | native, 4-arg form | real |
| `notsolid` / `solid` | :941/:940 | `_g_scr_mover.asm` | real |
| `hide` / `show` | :829/:828 `CODOL_Scr_Hide/Show` | `codol_script_entity.c:32-39`: willNeverChange guard then retained `ScrCmd_Hide/Show` | real |
| `delete` | :820 `CODOL_Scr_Delete` | guard then `ScrCmd_Delete` | real |
| `playsound` | :793 `CODOL_Scr_PlaySound` | native | real |
| `playfx` | :238 `Scr_PlayFX` | native | real |
| `physicslaunch` | :943 `ScriptEntCmd_PhysicsLaunch` | `_g_scr_mover.asm:1806`: same classname gate, writes MOVER_PHYSICS (C1 mode 9) | real, **not used**: T5's board arm uses `fake_physicslaunch` (MoveGravity), and `PhysicsLaunch` needs a collmap a brushmodel does not have |
| `physicslaunchclient` / `physicslaunchserver` / `physicsjitter` | :945 / :1157 / :250 | CoDOL-native | not on the board path |
| `clonebrushmodeltoscriptmodel` | :1108 | `GScr_CloneBrushModelToScriptModel` | not on the board path (T5 launches the brushmodel itself via the linked origin) |
| `getdvarint` | :412 | `GScr_GetCvarInt` | real; deliberately not used for gravity (2.3) |
| `int`, `randomint`, `randomfloatrange`, `distance`, `anglestoforward` | :195/:185/:188/:205/:217 | native | real |
| `codolprintln` | :121 `GScr_CoDOLPrintLn` | `scr_vm_functions.c:1839`: `Com_Printf(CON_CHANNEL_SERVER)` with no developer gate | prints at developer 0 |

No stub or no-op was found on the path.  The only thing missing was the
script.

### 2.1 Per-frame follow of a linked brushmodel

`G_RunFrame` (`src/g_main_mp.cpp:284`) sends every `ET_SCRIPTMOVER` entity
-- both the `script_brushmodel` chunk and the `script_origin` launcher --
to `G_RunMover` (`_g_mover.asm:200`), which first checks `tagInfo`
(+0x218) and calls `G_GeneralLink` for a linked child, else `G_MoverTeam`.
So the chunk is repositioned from its parent every server frame while
linked.  On `ent delete()` / `unlink()`, `G_EntUnlink`
(`_g_utils_mp.asm`) copies `currentOrigin`/`currentAngles` back into
`trBase` and zeroes the trajectory types.

### 2.2 Chunk entities

`obj/zm-mapents/zm_prototype_sh-mapents.txt`: 72 chunks, all
`classname script_brushmodel`, `model *N`, `script_parameters board`,
`script_team classic_boards`, `script_move_dist 125`, `script_noteworthy`
1..6, six per `pfN_auto1` barrier.  Each barrier's `script_struct` and its
`exterior_goal` both carry `angles 0 270 0`, facing INTO the room (the
zombie's tear facing; `animscripted(..., node.angles, ...)` uses the same),
so T5's `node.angles + (0,180,0)` launches the board outward, past the
zombie, exactly as in T5.  Chunk origins are the brushes' origin keys
(e.g. `456 1018 42`), so a pitch spin about the launcher spins the board
about its own centre.

### 2.3 Gravity

T5 reads `GetDvarInt(#"bg_gravity")`.  MEASURED: the retained
`BG_EvaluateTrajectory` (`_bg_misc.asm:1476`, TR_GRAVITY arm) computes
`-400 * t^2`, i.e. gravity fixed at 800, and `codol_engine_state.c`
`trajectory()` records the same for C1's evaluator (0x40CA40).  A dvar read
would make the solved arc miss its landing point whenever `g_gravity`
(`g_sv_main.c:717`, default 800) differs from the evaluator's constant, so
`fake_physicslaunch` uses -800.

## 3. Wire side (what the client sees)

`src/codol/snapshot/codol_engine_state.c` `trajectory()` (:1657) encodes
`TR_GRAVITY` as C1 mode 5 with `trTime`, `trDuration`, `trBase`, `trDelta`
-- that is the launcher, which is a `script_origin` and is never drawn.  The
board itself is a linked child: `G_GeneralLink` writes its origin/angles
each frame, so it leaves the server as `TR_STATIONARY` (mode 0) with a new
`trBase` every snapshot; C1 places a mode-0 entity at the newest snapshot's
`trBase` (BG_EvaluateTrajectory 0x40ca40), which at this server's 60 Hz
snapshot rate is a 3-5 unit step per frame at 200-300 u/s -- the same
regime the actor fix documented, but over a one-second flight of a plank
rather than a walking zombie.  Its pitch (apos) is likewise re-based each
frame.  The `TR_INTERPOLATE` promotion at :1989 is `ET_ACTOR`-only, so it
does not apply.  Nothing on this path requires a change to
`codol_engine_state.c`.

Optional patch spec (NOT applied, not needed for the boards to fly): if the
flight reads as stepped in a screenshot sequence, promote linked
`ET_SCRIPTMOVER` children too --

    /* codol_engine_state.c, next to the ET_ACTOR promotion at :1989 */
    if(es->eType==ET_SCRIPTMOVER && g_entities[es->number].tagInfo) {
        if(es->lerp.pos.trType==TR_STATIONARY && !put_entity(&out,0x00c,1u)) return 0;
        if(es->lerp.apos.trType==TR_STATIONARY && !put_entity(&out,0x030,1u)) return 0;
    }

-- with the same caveat as the actor promotion (mode 1 interpolates between
the two held snapshots, so the board would render one snapshot late).

Hidden state after the tear: `hide()` is only issued at the END of the
flight (or immediately when no barrier node was passed), and `replace_chunk`
still issues `show()` + `solid()` + og origin/angles, so the state the
client keeps after a tear is "hidden, on the floor behind the barrier",
and after a repair "shown, back in the frame".

## 4. Assets (all from zm zones; nothing `_mp`)

| use | T5 name | CoDOL zm asset | where |
|---|---|---|---|
| break fx | `wood_chunk_destory` = `impacts/fx_large_woodhit` (T5 `_zombiemode.gsc:1020`) | `impacts/fx_large_woodhit` | `docs/zone_assets/ALL_fx.txt:864`, `common_gametype_zm` -- the identical asset |
| tear sound | `zmb_break_board` (via `break_barrier_piece`) | `zmb_break_board` | `ALL_sound.txt:15226`, `common_gametype_zm` |
| slam sound | `zmb_board_slam` (via `board_slam`) | `zmb_board_slam` | `ALL_sound.txt:15202`, `common_gametype_zm` |
| repair sound | `rebuild_barrier_piece` | unchanged from the previous pass | -- |

The alias map is `zm/maps/mp/animscripts/zombie_init.gsc:107-108`
(`add_sound`), consumed by `_zombiemode_utility::play_sound_on_ent`.

## 5. The change

* `bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_blockers.gsc`
  -- `remove_chunk( chunk, node, destroy_immediately, zomb )` takes T5's
  signature; marks state/flag/notSolid/notify synchronously, threads the
  audio and FX as before, then `level thread remove_chunk_fly( chunk, node )`
  (new): the T5 :1900-:1990 launcher / dist / trace / link /
  `fake_physicslaunch` / `RotatePitch` / wait / hide / unlink / delete
  sequence, with one `codolprintln` per board.  `replace_chunk` unlinks a
  board repaired mid-flight.  Header index line updated.
* `bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_utility.gsc`
  -- `fake_physicslaunch( target_pos, power )` ported from T5
  `_zombiemode_utility.gsc:2381` (gravity -800, stores
  `self.launch_velocity` for the log, debug line-draw dropped).
* `bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_spawner.gsc`
  -- both `remove_chunk` call sites in `zombie_tear_notetracks` now pass
  `( chunk, node, true, self )` as T5 :1183 does.

No C/C++ or registration change was needed.  All three files are LF and
stay LF (CR count 0 before and after).

Gates: `python tools/codol_script_resolve.py --root bin/home/codol_rawfiles
--only zm` -> exit 0, "every reachable script resolves against the
registered builtin table".  `tools\BUILD-CODOL.ps1 -ObjectsOnly` -> see the
worker report (no source changed, so it exercises nothing new).

## 6. What to look for live

One line per torn board, at developer 0, in `bin/home/main/qconsole.log`:

    CoDOL zm board: chunk 3 at (441, 1022, 56) linked to launcher, movegravity vel (0, 213.4, 117.9) for 0.52 s to (441, 1132, 1.1) (dist 110 along yaw 90), spin pitch 180 over 0.26, fx impacts/fx_large_woodhit, snd zmb_break_board + zmb_board_slam

immediately after the existing `CoDOL zm: ent N tearing board 3 at ...`
line.  On screen: the plank leaves the frame away from the room, tumbles,
drops onto the yard floor behind the zombie, and disappears about a second
later; the frame slot stays empty until a repair.  The fallback line
`hidden without a launch (no barrier node)` should never appear from the
notetrack path; if it does, the spawner passed no node.
