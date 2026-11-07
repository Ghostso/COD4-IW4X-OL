# Zombie walk clip: why `info->time` never advanced, and the fix

Date: 2026-09-21. Scope: `zm_prototype_sh`, build de015044,
`bin/home/main/qconsole.log` lines ~440-490. Follows
`docs/CODOL_ZOMBIE_ANIM_KNOB_20260921.md`, whose decision table predicted
"clip present, weight 1, time frozen" and pointed at the sync-time
propagation. That prediction was the wrong layer: the sync propagation is
intact. The clip never received time because the record ABOVE the whole
knobbed branch -- `%body`'s own `XAnimInfo` -- was never given a goal weight.

Everything below is MEASURED from the log, the retained asm and the T5
source unless marked INFERRED. This worker did not link or start the
server; the live verdict is the next boot's actor lines (section 7).

---

## 1. The single reason

**`setanimknoball` / `setflaggedanimknoball` never raised the root anim's
own record to goal weight 1.** The retained `XAnimSetGoalWeightKnobAll`
(`_xanim.asm:12467`) walks from the clip's record up through its ancestors
and stops the moment the parent's `animIndex` equals the root anim
(`:12539 _200: cmp [ebp+0x10], eax` -> return). It sets goal 1 / rate 1 on
every ancestor BELOW the root anim and never touches the root anim's record.
T5 does exactly the same in `XAnimSetGoalWeightKnobAll` (OpenBLOPS
`xanim.cpp:3943`); the difference is that T5's script builtins call the
COMPLETE form, `XAnimSetCompleteGoalWeightKnobAll` (`:3989`), whose
per-ancestor setter `XAnimSetCompleteGoalWeightNode` (`:3906`) walks every
parent to the tree root and drives each one whose goal is exactly 0 or 1 to
goal 1, rate 1. Our port had no complete form for knob-all and rationalised
it away as "only the part above the root is missing, and `body` is
top-level, so nothing is above it" (old comment, `codol_script_anim.c:547`).

Two facts make that wrong on this tree:

* The script animtree's entry 0 is the tree root; `%body` is a child of it.
  MEASURED: the builtin printed `root 2 '#2(blend)'` and the old
  "root anim must be a top-level node" refusal did NOT fire, which required
  `entries[2].parent == 0`. So `body` = entry 2, parent = entry 0.
* The root anim's record is created by `XAnimEnsureGoalWeightParent`
  (`_xanim.asm:6212 _160`) with `rep stosd` over its whole `XAnimState`:
  **goal 0, weight 0, rate 0**. Only the entry-0 root record gets goal 1,
  weight 1, rate 1 (`:6104 _140`, `:6119-6123`). Nothing in KnobAll, Knob or
  `XAnimSetGoalWeightNode` ever revisits `body`'s record.

So every zombie tree looked like this (chain root -> leaf):

```
root(entry 0)  g 1.00 w 1.00 rate 1.00   <- XAnimEnsureGoalWeightParent root init
body(entry 2)  g 0.00 w 0.00 rate 0.00   <- created zeroed, never set   *** BUG ***
scripted       g 1.00 w 1.00 rate 1.00   <- KnobAll ancestor loop
stand_and_crouch          g 1 w 1 r 1
walk_and_run_loops (sync) g 1 w 1 r 1
combatrun                 g 1 w 1 r 1
combatrun_forward         g 1 w 1 r 1
ai_zombie_walk_v4 (leaf)  g 1.00 w 1.00 t 0.000 rate 0.53   <- what the log printed
```

The chain above is INFERRED from the code for the intermediate rows (the
old diagnostic printed only the leaf); the leaf row and the entry-2 fact are
MEASURED. The extended diagnostic (section 6) prints the whole chain next
boot so the row marked BUG is read straight off the log.

## 2. Why that one zero produces exactly the measured signature

### 2.1 `XAnimUpdateTimeAndNotetrack` stops at `body`

`DObjUpdateServerInfo` (`_xanim.asm:11858`) -> `XAnimUpdateTimeAndNotetrack
(obj, tree->children, dtime, notify)` (`:8559`). Its first test is the
record's blended weight (`:8582 ucomiss xmm5, [eax+0x14]`; T5 `xanim.cpp:1546
if (info->state.weight == 0.0) { XAnimCheckFreeInfo(...); return; }`). The
entry-0 root has weight 1 and is a plain blend node, so it takes the
non-sync arm (`:8739 _130`: `dt = dtime * state.rate`, rate 1) and recurses
into its children (`:8936`). The first child is `body` with weight 0: the
call returns after `XAnimCheckFreeInfo` on its children and **never descends
further**. No record below `body` -- the loopsync group, the nested blend
nodes, the leaf -- is ever visited by the time update. `t` and `ot` stay
0.000 for the whole session, which is the log.

`XAnimCheckFreeInfo` does not free `body` because its children have weight
(next paragraph), and `body` keeps its children, so the record count stays
at 11 and the leaf record index (16 / 27 / 38) is stable across the session
-- also the log.

### 2.2 `XAnimUpdateOldTime` is what made the leaf read `w 1.00`

`DObjInitServerTime` (`:11563`) runs `XAnimUpdateOldTime(obj, root,
&zeroState, dtime, parentHasWeight = 1, &out)` (`:6857`) every frame before
the time update. That pass visits every record regardless of weight and
blends `weight` toward `goalWeight` -- but only lerps over `goalTime` when
`parentHasWeight` is true; otherwise it SNAPS `weight = goalWeight`
(`:6948 _10`; T5 `:1301-1312`). `parentHasWeight` for the subtree below
`body` is `body.weight != 0` = false, so every zombie record below `body`
snapped to its goal on the very next frame. That is why the leaf showed
`w 0.00` in the frame the knob landed and `w 1.00` ever after: a real
0.20 s blend and an instant snap are indistinguishable at one line a second,
and the "weight blends 0.00 -> 1.00" reading in the assignment was the snap.

The same pass also explains why the loopsync group could not have kept a
time even if something had advanced it: for a sync root (`flags & 4`) whose
`v6 && childHasTime` is false -- `v6 = parentHasWeight && weight != 0` is
false under `body` -- `XAnimUpdateOldTime` takes the reset arm
(`:7009 _60` -> `XAnimResetTime`; T5 `:1351 XAnimInitTime(tree, infoIndex,
0.0, -1)`) every frame.

### 2.3 Root motion

`CODOL_ActorAdvanceGoalAnimation` -> `XAnimCalcDelta(obj, 0, ...)`
(`:10574`) -> `XAnimCalcDeltaTree` (`:2641`) weights each subtree by the
record's blended weight. `body` at weight 0 contributes nothing:
`rm (0.00 0.00 0.00)`, every second, every zombie. Also the log.

## 3. The sync propagation was never the defect (retained update trace)

For the record, the retained update handles a leaf two blend levels below a
loopsync group correctly; it was simply never reached. Trace for a group
record G with children C (blend) -> CF (blend) -> L (leaf), all weight 1:

| step | where | what |
|---|---|---|
| G entered | `:8582` | weight != 0, continue |
| G is not a leaf | `:8629 cmp word [eax+0x12], 0` -> `_70` | `animToModel == 0` |
| G is a sync node | `:8682 _70: test byte [eax+0x14], 0x3` | `info->u.animParent.flags & 3`; the loopsync bit (1) is the parser's `GetAnimTreeParseProperties` value (`cscr_animtree.cpp`), bit 4 is added by `XAnimSetupSyncNodes_r` (`:1307 _90: or word [esi+0x4], 0x4`), and `XAnimFillInSyncNodes_r` copies bit 1 into the NESTED blend nodes (`:1197 _70: or [esi+0x4], ax` with ax = bLoop ? 1 : 2), so C and CF carry flags 1 (no bit 4). T5 `XAnimSetupSyncNodes_r` (`xanim.cpp:4299`) does the same with `childFlags = parFlags | flags & 0x63` |
| average frequency | `:8713 call XAnimGetAverageRateFrequency` per child of G | `XAnimGetAverageRateFrequency` (`:3134`) recurses through blend children (`_40`, `_100`, `_170`, ... inlined to several levels), weighting each level by `state.weight` and `state.rate`, and returns `parts->frequency` (`+0x2c`) at the leaf. T5 `:1752` is the same recursion. For L: 30 fps / 129 frames = 0.2326, times the leaf rate 0.53 |
| group dt | `:8786 _420` | `dt = avg * G.state.rate * dtime`; non-zero. (`:8784 _140` is the zero-avg path; only taken when every child has weight 0 or frequency 0) |
| G time advances | `:8842 _260` .. `:8873 _450` | `time = oldTime + dt`, loop wrap unless `flags & 2` (nonloopsync) |
| descend | `:8882 _440` -> `:8908 call XAnimUpdateInfoSync` per child | `XAnimUpdateInfoSync` (`:8396`) copies `time/cycleCount` (and `oldTime/oldCycleCount` when they differ) from G's state into the child (`_100`, `_160`) and then **recurses into the child's own children** (`_120` loop -> `XAnimUpdateInfoSync_130`), so C, CF and L all receive G's time. T5 `:2443` is line-for-line the same |

Direct children of the group (the dog's `german_shepherd_run` under
`german_shepherd_run_knob`) and grandchildren (the zombie's walk) go through
the identical `_120` recursion; depth is not a factor.

## 4. Dog vs zombie: the first field that differs on the path root -> leaf

Both species use the same `XAnimTree_s`, the same `g_xAnimInfo` pool and the
same per-frame path. The difference is the builtin that lands the clip:

| | dog (`codol_dog_animation.c:262`) | zombie (`codol_script_anim.c`, knob-all) |
|---|---|---|
| operation | `CODOL_XAnimSetCompleteGoalWeightKnobNotified` = `XAnimSetGoalWeightKnob` + `.parent` loop setting EVERY ancestor with goal 0 to goal 1 / rate 1 (`_codol_xanim_complete_knob.asm`) | `XAnimSetGoalWeightKnobAll`: ancestors below the root anim only |
| top-level node's record (`german_shepherd_run_knob` / `body`) | goal 1, weight 1, rate 1 | **goal 0, weight 0, rate 0** |
| entry-0 root record | goal 1 w 1 r 1 (root init) | goal 1 w 1 r 1 (root init) |
| time update reaches the group | yes | no, stops at `body` |
| actor line | `rm (16.88 0 0)`, t advancing | `rm (0 0 0)`, `t 0.00 ot 0.00` |

The first differing field walking down from the root is the goal weight of
the first record under the root: 1 for the dog, 0 for the zombie.

## 5. What C1 does

Not read: the C1 client's knob-all site is in `.tvm0` territory for the
script layer, and the assignment's own note that `tools/codol_c1_disasm.py
--xref` is unreliable stands. The prior doc cites C1 `0x63bb7a` (`fld1`
feeding the per-ancestor setter) as the KnobAll ancestor loop, which matches
the retained loop; the completion walk is a T5-source claim
(`XAnimSetCompleteGoalWeightKnobAll`, `xanim.cpp:3989`, reached from
`GScr_SetAnimKnobAllInternal`) and, per the C1-outranks rule, would yield to
a C1 measurement that contradicts it. None exists; the measured behaviour on
this build is fully explained by the missing walk.

## 6. The change

### 6.1 `src/asmsource/_codol_xanim_complete_knob.asm` (CRLF preserved, 154 -> 248 lines)

New `CODOL_XAnimSetCompleteGoalWeightKnobAll`, cdecl with the retained
argument order `(obj, anim, rootAnim, weight, blend, rate, notifyName,
restart)`, forwarded verbatim to `XAnimSetGoalWeightKnobAll`. When that
returns 0 it looks the clip's record up (`XAnimGetInfoIndex_r`, register
ABI) and walks `parent` to 0; for every ancestor whose `state.goalWeight` is
exactly 0.0 or 1.0 it calls `XAnimSetGoalWeightNode(tree, idx, 1.0, blend,
1.0, 0, 0)` -- the T5 `XAnimSetCompleteGoalWeightNode` condition and
arguments (`xanim.cpp:3906-3935`). A record mid-fade to any other goal is
left alone, as in T5. A non-zero `XAnimSetGoalWeightNode` return is
propagated; a missing record after a successful KnobAll returns 1 (the
existing "violated native invariant" convention of the file). Ancestors that
KnobAll already set to goal 1 are re-set with the same values, exactly as
T5's per-ancestor `XAnimSetCompleteGoalWeightNode` walk does; the entry-0
root goes through `XAnimSetGoalWeightNode`'s own `animIndex == 0` special
case (goal 1, blend 0, rate 1).

### 6.2 `src/codol/script/codol_script_anim.c` (LF)

* `anim_publish`: the KNOBALL case dispatches on the `complete` flag exactly
  like the KNOB and ANIM cases already do:
  `complete ? CODOL_XAnimSetCompleteGoalWeightKnobAll(...) :
  XAnimSetGoalWeightKnobAll(...)`. `setanimknoball`,
  `setanimknoballrestart`, `setflaggedanimknoball` and
  `setflaggedanimknoballrestart` all carry `ANIMFLAG_COMPLETE`
  (unchanged), so every zombie locomotion knob now completes the chain.
* The refusal "this server has no XAnimSetCompleteGoalWeightKnobAll; the root
  anim of a knob-all must be a top-level node of the animtree" is removed
  from both knob-all forms. T5 has no such refusal.
* The comment block above the knob-all forms now states the measured fact
  instead of the old rationalisation.

### 6.3 `src/codol/player/codol_actor_lifecycle.cpp` (LF; applied on top of f30189df, the routing agent's version)

`ActorDescribeTree` only: `t`/`ot` now print with three decimals (a 60 Hz
tick moves a 0.2326 Hz clip by 0.002 a frame, which `%.2f` rounded to
0.00), and the heaviest root->leaf path it already walks is dumped as a
`chain` suffix, one entry per record:

```
chain 5:0 f0 g1.00 w1.00 t0.000 ot0.000 r1.00 c0/0 6:2 f0 g0.00 w0.00 ... 16:237 L g1.00 w1.00 t0.000 ...
```

`info:anim`, then `f<flags>` (`XAnimInfo::u.animParent.flags`: 1 loopsync,
2 nonloopsync, 4 sync root) for a blend node or `L` for a leaf, then goal,
weight, time, oldTime, rate, cycleCount/oldCycleCount. Bounded to the first
24 actor lines of a boot plus the first 24 lines that show the frozen-clip
signature (leaf weight > 0 with time and oldTime both 0). The line buffer
grew from 160 to 1200 bytes (`MAXPRINTMSG` is 4096). Nothing else in the
file was touched; the routing code and `codol_bot_nav.*` were not opened for
editing.

### 6.4 Build

`tools\BUILD-CODOL.ps1 -ObjectsOnly`: `build OK (exit 0)`;
`obj/codol/_codol_xanim_complete_knob.o` exports
`_CODOL_XAnimSetCompleteGoalWeightKnobAll` (nm), `obj/codol/codol_script_anim.o`
imports it, `obj/codol/codol_actor_lifecycle.o` rebuilt. The only warnings
in the file are pre-existing (`ActorOrientToDirection`, `ActorDeltaTurnYaw`,
`ActorTalkSpecies`). Line endings: asm 248 CR for 248 lines (was 154/154),
C and C++ files 0 CR before and after. Not linked, not promoted, server not
touched.

## 7. What the next boot must show

Per zombie, one second after `animscript -> dog_move`:

```
CoDOL actor: ent 576 ... script move ... rm (x y 0) non-zero ... anim ai_zombie_walk_vN w 1.00 g 1.00 t 0.1xx ot 0.1xx rate 0.5x delta 1 depth 6 infos 11 chain 5:0 f0 g1.00 w1.00 ... 6:2 f0 g1.00 w1.00 t0.000 ... <group> f5 g1.00 w1.00 t0.1xx ot0.1xx ... 16:237 L g1.00 w1.00 t0.1xx ot0.1xx r0.5x
```

Checks, in order:

1. The second chain entry (`:2`, `body`) reads `g1.00 w1.00 r1.00`. If it
   still reads `g0.00`, the completion walk did not run: confirm the
   `CoDOL anim: setflaggedanimknoball()` line still prints (the builtin
   path) and that `bin/codol_dedrun_next.exe` is the new link.
2. The loopsync group entry (`f5` = loopsync 1 | sync root 4) has `t`
   advancing and equal to the leaf's `t`; the nested blend entries (`f1`)
   carry the same `t`. That is `XAnimUpdateInfoSync` doing its job.
3. `t` and `ot` differ by ~`rate * 0.2326 * frameTime` per frame and `rm`
   is non-zero while `t` moves. If `t` moves and `rm` stays `(0 0 0)`, the
   remaining defect is in `XAnimCalcDeltaTree`'s leaf arm against this
   clip's delta payload (section 6 of the previous doc, last-but-one row).
4. Dogs: unchanged path, unchanged output (`rm (16.88 0 0)`), and their
   chain shows `german_shepherd_run_knob` at `g1.00 w1.00` as before.

The walk clip's cycle at rate 0.53 is 129 frames / 30 fps / 0.53 = 8.1 s;
`t` grows by ~0.12 a second. That is the script's `moveplaybackrate`
(`zombie_init.gsc` 0.9-1.1 scaled by `apply_move_speed_scale`), not a
server choice, and is outside this change.

## 8. Not done

* No live run (not permitted for this worker). Section 7 is the prediction
  the instrumentation is built to confirm or refute in one boot.
* `XAnimCalcDeltaTree` was not re-traced; it was never reached and there is
  no measurement that implicates it.
* The `setanimknoballlimited`-style (non-complete) knob-all forms keep the
  retained semantics on purpose: T5's `XAnimSetGoalWeightKnobAll` also
  leaves the root anim's record alone, and a script that uses them relies on
  an earlier complete operation having lit the chain.
