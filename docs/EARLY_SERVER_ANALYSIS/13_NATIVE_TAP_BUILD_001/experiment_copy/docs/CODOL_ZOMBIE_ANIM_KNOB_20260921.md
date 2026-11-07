# Zombie walk clip "never lands": what the actor diagnostic really measured, and the instrumentation that decides it

Date: 2026-09-21. Scope: `zm_prototype_sh`, build 004269ba (regparm fix), the
per-second `CoDOL actor:` line reading `anim  w 1.00 t 0.00 delta -1` and
`rm (0.00 0.00 0.00)` for every zombie, every second.

Everything below is MEASURED from the retained source/asm, the zone data and
the logs on disk unless marked INFERRED. Nothing was run: this worker was not
allowed to link or start the server, so the live verdict is deferred to the
next boot, which the change makes decisive.

---

## 1. Verdict up front

**The per-second diagnostic could not see the tree.** Its `anim` field was
built from two calls that cannot answer the question at developer 0, so the
line `anim  w 1.00 t 0.00 delta -1` carries no information about what the
zombie is playing. It is therefore NOT evidence that the walk clip "never
landed". The one fact it does carry -- `w 1.00` for anim 0 -- proves the
opposite of the premise: `XAnimGetWeight(tree, 0)` reads the tree's root
info record, and a root record only exists once some `XAnimSetGoalWeight*`
call has succeeded on that tree (`XAnimGetWeight` returns `0.0` for a tree
with no records, `_xanim.asm:10723 .. _10: fldz`). So at least the spawn-time
`setAnimKnobAll(%ai_zombie_idle_v1, %body, ...)` DID land on the actor's own
tree.

The five hypotheses in the assignment were each checked against the retained
code and the data (section 3). None of them is a defect: the builtin knobs
the same tree the DObj animates and the diagnostic reads; the index space is
one `XAnim_s`; `%body` is the top-level node; the tree is ticked every frame
by the same `G_RunFrame -> G_DObjUpdateServerTime -> DObjUpdateServerInfo`
path that measurably moves dogs (`rm (16.88 0.00 0.00)`, 72 log lines); an
undefined rate keeps the default 1.0 and `zombie_init.gsc` sets 0.9..1.1.

What is left cannot be settled by reading and is now settled by the log:
the rewritten diagnostic walks the XAnim info pool directly and names the
clip, its goal weight, its blended weight, its time and its previous time;
the builtins print every accepted transaction (bounded) with the tree
pointers on both sides; and the one silent failure mode XAnim has --
returning 0 without leaving a record -- is a warning. Section 6 is the
decision table for the next boot's output.

One structural difference between the species that never worked and the one
that does was found and is the leading INFERRED candidate if the next boot
shows the walk clip present with `t` frozen: the zombie locomotion clips sit
two blend levels *below* a `loopsync` group (`walk_and_run_loops > combatrun
> combatrun_forward > ai_zombie_walk_v1`) while every dog clip that animates
is a *direct* child of its `loopsync` group (`german_shepherd_run_knob >
german_shepherd_run`). The retained sync-time propagation
(`XAnimUpdateInfoSync`, `_xanim.asm:8396`) has therefore never been
exercised through nested blend nodes on this server.

---

## 2. What the old diagnostic measured (MEASURED)

`src/codol/player/codol_actor_lifecycle.cpp` (before this change) built the
field as

```
top   = XAnimGetDescendantWithGreatestWeight(&a->tree, 0);
name  = XAnimGetAnimName(a->tree.anims, top);
leaf  = !entries[top].numAnims;
delta = leaf && parts ? parts->bDelta : -1;
"anim %s w %.2f t %.2f delta %d", name, XAnimGetWeight(&a->tree, top), XAnimGetTime(&a->tree, top), delta
```

### 2.1 `XAnimGetDescendantWithGreatestWeight` takes an INFO index

`src/asmsource/_xanim.asm:2037`:

```
XAnimGetDescendantWithGreatestWeight:
    ...
    mov  [ebp-0xa0], eax          ; tree
    lea  eax, [edx*8]
    shl  edx, 0x6
    sub  edx, eax                 ; edx * 56 = sizeof(XAnimInfo)
    lea  eax, [edx+g_xAnimInfo]   ; &g_xAnimInfo[edx]
    cmp  word [eax+0x12], 0x0     ; info->animToModel (leaf?)
    jz   _10
    movzx eax, word [eax+0x10]    ; return info->animIndex
```

The second register argument is multiplied by 56 and used as an index into
`g_xAnimInfo` -- it is an XAnimInfo record index. Both retained callers agree:
`:2398-2410` and `:2577-2589` compute `ecx*56 + g_xAnimInfo` for the record
they are iterating and pass that same `ecx` in `edx`. The function returns
the *anim* index (`[+0x10]`) of the heaviest descendant record.

The diagnostic passed anim index `0`. Record 0 is the pool's null record
(`XAnimAllocInfoIndex` threads the free list through it, `:6315`), whose
`animToModel` and `children` are 0, so the call fell through to `_20`
(`:2432`), which returns 0. `top` was always 0 = the root entry, whose name is
empty. The `w 1.00` printed was then `XAnimGetWeight(tree, 0)` = the root
record's blended weight, and `t 0.00` the root's time (a blend node has
none). `delta -1` because the root is not a leaf.

### 2.2 `XAnimGetAnimName` is empty at developer 0

`XAnimGetAnimName(anims, i)` (`_xanim.asm:11020`) reads
`anims->debugAnimNames[i]`; `XAnim_s::debugAnimNames` is developer metadata
and NULL on a production boot (`codol_model_animation.c:
CODOL_FindAnimInServerTree` already guards `!anims->debugAnimNames`). Even
with the right index the field would have printed `anim `.

Both faults together are why the line was identical for the whole session and
why the regparm fix (004269ba) changed nothing visible: it stopped the crash,
it could not make the call meaningful.

---

## 3. The five hypotheses (MEASURED, with the retained code)

| # | hypothesis | finding |
|---|---|---|
| 1 | two trees | NOT the case. `anim_receiver()` (`codol_script_anim.c`) refuses unless `DObjGetTree(Com_GetServerDObj(entnum)) == CODOL_ActorOwnedTree(ent)`, and `CODOL_ActorOwnedTree` returns `&a->tree` -- the same storage the diagnostic reads and `CODOL_ActorAdvanceGoalAnimation` evaluates through `XAnimCalcDelta(obj, 0, ...)` (`_xanim.asm:10574` walks `obj->tree`). A mismatch would have raised `Scr_ObjectError` and printed at developer 0 (454c188b); no such line exists in the log. Both pointers are now printed (section 5). |
| 2 | index space | ONE `XAnim_s`. `Scr_GetAnim(i, tree)` (`_scr_vm.asm:5706`, `_20` arm) requires `Scr_GetAnims(anim.tree) == XAnimGetAnims(tree)` or errors "anim '%s' in animtree '%s' does not belong to the entity's animtree". The actor's tree is `Scr_GetAnims(serverTree)` for the tree named `generic_human` (`CODOL_ActorPrepareAnimation`). The script and the actor therefore share the very `entries[]` array. `anim_param()` bounds the index against `anims->size`. The server parses C1's own `animtrees/generic_human.atr` out of the mounted zone (`cscr_parser.cpp:567`, `CODOL_LoadEngineRawFile` first); the loose `bin/home/codol_rawfiles/animtrees/generic_human.atr` is IW4's and has **zero** `ai_zombie_*` nodes -- it is not what was parsed, or the map would have failed to compile. |
| 3 | `%body` root | Top-level. C1's `generic_human.atr` extracted from `common_mp` (123,522 bytes): `body` at line 1 column 0, and the ancestor chains are in section 4. The knob-all refusal at `codol_script_anim.c` ("root anim of a knob-all must be a top-level node") cannot fire, and had it fired it would have printed. `XAnimSetGoalWeightKnobAll` (`_xanim.asm:12467`) returns 1 only when the parent walk from the clip's record reaches record 0 before meeting `rootAnim`; `body`'s record is created by `XAnimSetGoalWeightNode`'s parent-ensure step, so the walk terminates at it. |
| 4 | goal weight vs weight | The tree IS ticked. `G_RunFrame` (`_g_main_mp.asm:1284`) calls `G_DObjUpdateServerTime(ent, 1)` for every in-use entity without the 0x2000 flag; that is `SV_DObjUpdateServerTime(ent, level.frameTime*0.001, 1)` (`_g_utils_mp.asm:2390`, `sv_game.c:250`) -> `DObjUpdateServerInfo` -> `XAnimUpdateTimeAndNotetrack(obj, tree->children, dtime, 1)` (`_xanim.asm:11858`). Dogs blend and move through exactly this (`CoDOL dogs: ... rm (16.88 0.00 0.00)`, 72 lines in `bin/home/main/qconsole.log*`), and dogs have no other update path: `codol_dog_animation.c:apply_batch` calls the same `XAnimSetGoalWeightKnob`/`XAnimSetGoalWeight` on the same server DObj. |
| 5 | rate | `optional_float(5, 1.0f)` keeps the default when the parameter is undefined (`Scr_GetType == 0`); `zombie_init.gsc:137-138` sets `self.animplaybackrate = 0.9 + randomFloat(0.2)` and `self.moveplaybackrate = self.animplaybackrate`; `apply_move_speed_scale` rescales it, never to 0. A rate of exactly 0 is now warned (section 5). |

Also ruled out on the way:

* **The clips.** Read straight out of `common_gametype_zm` with the
  alpha0022 zone reader (`tools/codol_zone_assets.py`'s module):
  `ai_zombie_walk_v1` 129 frames, flags 0x03 (loop+delta), framerate 30,
  frequency 0.23256; `ai_zombie_walk_fast_v1` 82 / 0x03 / 30 / 0.36585;
  `ai_zombie_sprint_v1` 60 / 0x03 / 30 / 0.5; `ai_zombie_idle_v1` 58 / 0x01
  (no delta, as an idle should). `german_shepherd_run` (common_gametype_mp):
  12 / 0x03 / 30 / 2.5. The leaf time step is `state.rate * parts->frequency
  * dtime` (`_xanim.asm:8620-8623`, `parts+0x2c`), non-zero for all of them.
* **Asset resolution.** A clip absent from every mounted zone is replaced by
  `void`/`void_loop` with a `CoDOL xanim '%s' is not in any mounted zone`
  warning (`db_load.cpp:3559-3579`); no such warning exists in any log, so
  every leaf of the parsed tree is bound to its real XAnimParts.
* **Script errors.** `RuntimeError` prints at developer 0 since 454c188b
  (`scr_vm_main.c:1836`), the asm VM calls that C function
  (`_scr_vm.asm:925/3643/5650`), and every refusal in the builtins goes
  through `Scr_Error`/`Scr_ParamError`/`Scr_ObjectError`. The session log has
  no `script runtime error` line and no `CoDOL anim:` warning.
* **The script path to the knob-all.** `_zombiemode_spawner.gsc:356`
  `ai.animname = "zombie"` precedes `:387 set_zombie_run_cycle()`;
  `set_run_anim` indexes `level.scr_anim["zombie"]["walk1".."walk8"]`,
  `["run1".."run6"]`, `["sprint1".."sprint4"]`, all defined in
  `_zombiemode.gsc:936-957`; `randomIntRange(1,9)/(1,7)/(1,5)` stay inside
  those. `zombie_init.gsc:126` sets `has_legs = true`, so `MoveRun` takes
  `MoveStandRun`. `MoveStandRun`'s silent `wait(0.05); return` when
  `current_run_anim()` is undefined remains the one script-side way to reach
  "idle only, no error" -- the new diagnostic distinguishes it (section 6).

---

## 4. The structural difference (MEASURED, C1's own animtrees)

Extracted from `common_mp` with the zone reader (`z.rawfile("animtrees/
generic_human.atr")`, `z.rawfile("animtrees/dog.atr")`) and walked by brace
nesting:

```
generic_human.atr (C1, 123,522 bytes)
   1  body
2723  body > scripted > stand_and_crouch > walk_and_run_loops : loopsync
2932  ... > walk_and_run_loops : loopsync > combatrun > combatrun_forward > ai_zombie_walk_v1
2941  ... > walk_and_run_loops : loopsync > combatrun > combatrun_forward > ai_zombie_walk_fast_v1
2948  ... > walk_and_run_loops : loopsync > combatrun > combatrun_forward > ai_zombie_sprint_v1
3280  body > scripted > exposed_modern > exposed_aiming > add_idle : additive > ai_zombie_idle_v1

dog.atr (C1, 1,980 bytes)
  48  german_shepherd_run_knob : loopsync
  50  german_shepherd_run_knob : loopsync > german_shepherd_run
  39  german_shepherd_run_start_knob : nonloopsync > german_shepherd_run_start
```

Two things follow.

1. The spawn pose is under an **additive** node. `setAnimKnobAll(
   %ai_zombie_idle_v1, %body, ...)` therefore leaves the actor with the bind
   pose plus an additive idle -- and, correctly, `rm (0 0 0)` because the
   idle has no delta track. A session in which only the idle ever landed
   looks exactly like the reported one.
2. The locomotion clips are the only clips this server has ever been asked
   to play that are nested **inside** a sync group below further blend
   nodes. The time of a sync member is not advanced by the member itself
   (`XAnimUpdateTimeAndNotetrack`'s leaf arm requires a non-zero own weight,
   `_xanim.asm:8579-8583`); it is copied down from the group by
   `XAnimUpdateInfoSync` (`:8396`, copies `time/oldTime/cycleCount` from the
   group state into the member at `_100`, then `_110: test bl,bl` descends).
   Whether that descent reaches a grandchild leaf on this retained build is
   what the `t`/`ot` fields of the new diagnostic answer.

---

## 5. The change

### 5.1 `src/codol/player/codol_actor_lifecycle.cpp` (edited, as permitted)

* Removed the four `XAnimGet*` externs used only by the diagnostic (the
  `__regparm2 XAnimGetDescendantWithGreatestWeight` declaration among them)
  and added `extern "C" XAnimInfo g_xAnimInfo[4096];` (the same declaration
  `codol_dog_animation.c:19` already uses).
* New `static void ActorDescribeTree(const XAnimTree_s *, char *, size_t)`:
  starts at `tree->children` (the root record), counts every record
  reachable from it, follows the heaviest child (blended weight, goal weight
  as tie-break) to a leaf, and names that leaf by `entries[animIndex]
  .u.parts->name` -- real asset data, valid at developer 0.
* The per-second line now ends with
  `tree <ptr> anim <clip> w <weight> g <goal> t <time> ot <oldTime> rate <r> delta <0|1|-1> depth <n> infos <n>`,
  or `anim none (tree <ptr> has no infos)` when nothing has ever landed.
  The `tree` pointer is the same value the builtins print, so the two
  streams can be matched by eye.

### 5.2 `src/codol/script/codol_script_anim.c`

* `find_info()`, `count_infos()`, `anim_entry_name()`: bounded walks of the
  info pool from `tree->children`, and a developer-independent entry name.
* `anim_report()`, called from `anim_publish()` after XAnim accepted the
  transaction (a refusal still raises the T5 script error as before):
  * **Loud warning (once a second per actor)** when a setter with a positive
    goal weight returned 0 and the tree holds **no record** for the clip
    afterwards: `CoDOL anim: <method>() ent N: XAnim returned 0 for anim I
    '<clip>' (root R '<node>') but tree P holds NO record for it afterwards
    (root info K, M records) -- the clip did not land on the actor's tree`.
    This is the one failure the retained entry points never report.
  * **Loud warning (once a second per actor)** when the rate is exactly 0
    (legal in T5, but it freezes the clip at its current frame).
  * **Bounded report**: the first 6 transactions of each actor incarnation
    in full, then one per 10 s per actor. Each line carries the owned tree
    pointer, the DObj's tree pointer (proving hypothesis 1 on every line),
    the `XAnim_s` pointer and size, the root record index, the wire type,
    the anim and root indices with names, weight/blend/rate/flags, the XAnim
    result, and the clip's record after the call: `record K: g <goal> w
    <weight> t <time> rate <r>, M records in tree`.

  Bound arithmetic: the zombie move loop re-issues its knob-all every 0.4 s
  (`DoNoteTracksForTime(level.zombie_run_anim_update_time = 0.4)`), so six
  zombies unbounded would be 15 lines a second; with the bound it is 36
  lines at spawn and then 0.6 lines a second.

No GSC was touched; `tools/codol_script_resolve.py` was not required.
`src/codol/snapshot/codol_engine_state.c` and
`src/codol/player/codol_bot_nav.c` were not touched.

### 5.3 Build

`tools\BUILD-CODOL.ps1 -ObjectsOnly`: `build OK (exit 0)`;
`obj/codol/codol_script_anim.o` and `obj/codol/codol_actor_lifecycle.o`
rebuilt 2026-09-21 16:28 with no warnings in the new code. Line endings:
both files are LF in HEAD and LF after the edit (`tr -cd '\r' | wc -c` = 0
before and after).

---

## 6. Reading the next boot

Per zombie, within the first second after spawn, expect:

```
CoDOL anim: setanimknoball() ent 576 tree 0x... (DObj tree 0x..., anims 0x... size 5345, root info K) type 5 anim A 'ai_zombie_idle_v1' root B '#1(blend)' weight 1.00 blend 0.10 rate 1.00 complete -> xanim 0; record K2: g 1.00 w 0.00 t 0.000 rate 1.00, 6 records in tree
CoDOL anim: setflaggedanimknoball() ent 576 tree 0x... (...) type 5 anim W 'ai_zombie_walk_v3' root B '#1(blend)' weight 1.00 blend 0.20 rate 0.97 complete -> xanim 0; record K3: g 1.00 w 0.00 t 0.000 rate 0.97, 9 records in tree
```

and then the per-second actor line. The decision table:

| per-second `anim` field | meaning | where the defect is |
|---|---|---|
| `anim none (tree P has no infos)` | nothing ever landed | the builtins never ran for this actor; look for the missing `CoDOL anim:` lines and a `script runtime error` |
| `anim ai_zombie_idle_v1 ...` for the whole session, no `setflaggedanimknoball()` line | the move knob was never issued | GSC: `MoveStandRun` is looping on an undefined `current_run_anim()` (`self.run_combatanim` unset) |
| `anim ai_zombie_walk_vN w 1.00 g 1.00 t 0.000 ot 0.000 delta 1` | clip present and blended in, time frozen | sync-time propagation into the nested `loopsync` member (`XAnimUpdateInfoSync` descent), section 4 item 2 |
| `... w 0.00 g 1.00 ...` persisting | record present, weight never blends | the update never reaches this record: an ancestor with weight 0 (an additive/knobbed branch), or `DObjUpdateServerInfo` not ticking this entity |
| `... w 1.00 t 0.4xx ot 0.4yy delta 1` with `rm (0.00 0.00 0.00)` | the clip plays and advances, delta still 0 | `XAnimCalcDeltaTree`'s leaf arm (`_xanim.asm:2724`) against this clip's delta payload |
| `... w 1.00 t 0.4xx ... delta 1` with `rm (x y z)` non-zero and `moved N/s` | fixed | -- |
| any `-- the clip did not land on the actor's tree` warning | XAnim accepted and did nothing | `XAnimSetGoalWeightNode`/`XAnimAllocInfoIndex` (pool exhaustion or a refused sync member) |

The target line the user should see once locomotion works:

```
CoDOL actor: ent 576 hp 150 org (...) moved 90/s ... script move state ? mode 1/1/3 orient 5 rm (1.48 0.00 0.00) phys ok 60 rej 0 vel (...) grounded 1 tree 0x... anim ai_zombie_walk_v3 w 1.00 g 1.00 t 0.42 ot 0.41 rate 0.97 delta 1 depth 7 infos 9
```

---

## 7. Not done, and why

* No live run: linking, promoting and starting the server are the parent's.
  Everything in section 6 is the prediction the instrumentation was built to
  test, not a result.
* The sync-group descent (`XAnimUpdateInfoSync` `_110` onwards) was not
  transcribed in full; it is the leading candidate only by elimination and
  by the measured structural difference, and it is INFERRED until the
  `t`/`ot` fields say so.
* `MoveStandRun`'s silent wait is left as it is; the diagnostic identifies
  that case unambiguously (idle only, no `setflaggedanimknoball()` line), and
  a GSC edit would have needed the resolver gate and a script owner.
