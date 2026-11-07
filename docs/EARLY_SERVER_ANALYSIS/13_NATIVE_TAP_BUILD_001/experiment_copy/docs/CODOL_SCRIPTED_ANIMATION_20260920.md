# T5's scripted-animation GSC surface: `%anim` and the builtins that consume it

Report date: 2026-09-20.
Scope: `CODOL_ACTOR_SPECIES_20260920.md` §5 option (1) — port the `%anim`
reference-variable system and the script commands that drive an entity's
XAnim tree from GSC, so a humanoid actor can be animated by its animscripts
instead of by a native clip table.

Every claim is labelled **MEASURED** (read out of source, the retained
assembly, `C1.exe`, the shipped data, or a tool/compiler run) or **INFERRED**.

---

## 1. Verdict up front

1. **`%anim` was already complete.** MEASURED. The compiler, the VM opcode, the
   value type and the resolution helper are all present and already exercised
   by two registered builtins. §2 gives the chain with addresses. Nothing in
   this task had to be built for it; it had to be *established*, and it was.
2. **Notetrack delivery was already complete too.** MEASURED. `G_RunFrame`
   already ticks every entity's server DObj with `bNotify = 1` and the retained
   `XAnimProcessServerNotify` already issues `Scr_NotifyNum(entnum, notifyName,
   <notetrack>)` plus the `"end"` marker. §3. T5's `DoNoteTracks` is pure GSC
   and stays pure GSC; it needed an engine producer for
   `self waittill (flagName, note)` and that producer exists.
3. **The gap was the builtins, and 20 of them now exist and are registered.**
   §4 lists them with their T5 provenance. They are implemented, not stubbed:
   there is no empty body and no "unsupported" arm in
   `src/codol/script/codol_script_anim.c`.
4. **The zombie species' three native function pointers are deliberately still
   NULL**, and §7 argues that filling them would be the fabrication the task
   forbids. The species' animation backend is now the scripted path; the only
   change on that side is that `setanimstate` says so.
5. **One measured defect found in code this task does not own**, §6:
   `codol_dog_animation.c`'s `apply_batch` reads the two wire fields
   `(type, arg2 bit 0)` with `type` meaning plain/complete and bit 0 meaning
   knob, while C1 1.1.1.13 reads `type` as plain/knob/knob-all and bit 0 as
   complete. They agree on two of the four combinations the dog emits and
   disagree on `(4, 0)`, which the dog does emit. An anchored patch is in §6.

---

## 2. `%anim` — what was already wired, and how it is known

A GSC `%name` resolves against the script's `#using_animtree` tree into a
`VAR_ANIMATION` value whose payload is a packed `scr_anim_s {uint16 index;
uint16 tree;}` (`src/scr_vm.h:646`). The whole chain is present:

| stage | where | MEASURED evidence |
|---|---|---|
| lex/parse `%name` | `src/asmsource/_scr_compiler.asm` | `EmitOrEvalPrimitiveExpression_410` (`:5711`) refuses with `"#using_animtree was not specified"` when `gScrAnimPub+0x414` is null — an arm only the `%anim` production reaches |
| emit | same, `_400` (`:5719`) | `mov eax, 0x13; call EmitOpcode` then `TempMallocAlign(4)`, `*p = 0xffffffff`, `Scr_EmitAnimation(p, name, pos)` |
| link | `_scr_animtree.asm:691 Scr_EmitAnimation` | chains the emitted 4-byte cell onto the animtree node variable so `Scr_LoadAnimTreeAtIndex` / `ConnectScriptToAnim` (`:150`) can patch the real `(tree,index)` into it when the tree is built |
| execute | `_scr_vm.asm` | opcode `0x13` → jump table `VM_ExecuteInternal_jumptab_0` entry 19 → `VM_ExecuteInternal_3260` (`:2464`) sets `top->type = 0xb` (`VAR_ANIMATION`) and falls into `_1110` (`:2288`), which copies the 4-byte link pointer out of the code stream |
| read back | `_scr_vm.asm:5706 Scr_GetAnim(unsigned paramIndex, XAnimTree_s *tree)` | validates `type == 0xb` (`"type %s is not an anim"`), and when `tree != NULL` requires `Scr_GetAnims(anim.tree) == XAnimGetAnims(tree)` (`"anim '%s' in animtree '%s' does not belong to the entity's animtree '%s'"`). Returns the packed value in `eax`; errors leave through `Scr_ErrorJumpOut` |
| already used | `src/scr_vm_main.c:150-152` | `getanimlength`, `animhasnotetrack`, `getnotetracktimes` are registered and their asm bodies (`_g_scr_main_mp.asm:1327/1365/1401`) all begin `Scr_GetAnim(0, NULL)` |

The jump-table index was derived by counting: entries run `3080, 3090, 1010,
3100, 3110, …` so entry *n* (n ≥ 3) is `3100 + (n-3)*10`; `3260` is n = 19 =
`0x13` = `OP_GetAnim­ation` (`src/scr_vm.h:59`). MEASURED.

So the only thing this task had to add on the `%anim` side was a range check:
`Scr_GetAnim` proves the reference belongs to the entity's tree but never
bounds `index` against `anims->size`, and every consumer (XAnim, the static
`entries[].parent` walk, the 11-bit wire field) indexes with it.
`anim_param()` does that check.

`CODOL_FindAnimInServerTree` / `CODOL_RegisterServerAnimListReferences`
(`src/codol/assets/codol_model_animation.c`) were **not** duplicated. They
answer a different question (name → index, for a native producer with no GSC
reference), and the two index domains are the same entry index inside the same
`XAnim_s`, so nothing needed reconciling. INFERRED, from both reading
`entries[]` of the tree `Scr_GetAnims(serverTree)` returns.

---

## 3. Notetrack delivery — already complete, MEASURED end to end

T5's `animscripts\shared::DoNoteTracks( flagName, … )`
(`D:\CoD\COD-GSC-Source\T5-STEAM-GSC\animscripts\shared.gsc:1221`) is ordinary
GSC:

```gsc
for (;;) {
    self waittill (flagName, note);
    ...
    val = self HandleNoteTrack( note, flagName, customFunction, var1 );
    if ( IsDefined( val ) ) return val;
}
```

It needs the engine to notify the entity with the *flag* as the notify name and
the *notetrack* as its first parameter. That producer is live:

* `_g_main_mp.asm:1284` — `G_RunFrame` walks every in-use entity and calls
  `G_DObjUpdateServerTime(ent, 1)`; when it returns nonzero it calls
  `Scr_RunCurrentThreads` and re-tests, which is the standard notetrack
  settle loop.
* `_g_utils_mp.asm:2390` → `src/sv_game.c:248 SV_DObjUpdateServerTime` →
  `DObjUpdateServerInfo` (`_xanim.asm:11857`) → `XAnimUpdateTimeAndNotetrack`
  (`:8558`) → `XAnimProcessServerNotify` (`:4483`).
* `XAnimProcessServerNotify(DObj_s const*, XAnimInfo*, float)`:
  * returns immediately when `DObj+0x6` (entnum) is 0 or when
    `XAnimInfo+0x4` (`notifyName`) is 0 — so an animation played with no flag
    never notifies, exactly as in T5;
  * for each notetrack crossed this tick: `Scr_AddConstString(<notetrack
    name>)` then `Scr_NotifyNum(dobj->entnum - 1, 0, notifyName, 1)`
    (`:4537` and `:4567`);
  * at `state.time == 1.0` it notifies `g_endNotetrackName` instead
    (`:4596`), which `XAnimInit` interns as `"end"` (`:13181`,
    `SL_GetString_("end", 0, 3)`).

`XAnimInfo+0x6` (`notifyType`) is read **only** by `XAnimProcessClientNotify`
(`:7570`), which a dedicated server never runs. MEASURED. So on this build the
value is inert; the new builtins still compute T5's value (2 when the goal
weight exceeds 0.001, else 0) because C1 recomputes its own from the wire goal
weight anyway (`C1 0x443f60`).

**Nothing was added for notetracks.** The correct action was to measure that
the path exists and leave it alone.

---

## 4. The builtins

New file `src/codol/script/codol_script_anim.c` (+ `.h`), registered from
`src/scr_vm_main.c`. All are **methods** on an entity.

Reference: `D:\CoD\OpenBLOPS\Game\Server\game_mp\g_scr_main_mp.cpp`, which
carries T5's own `GScr_SetAnimInternal` / `GScr_SetAnimKnobInternal` /
`GScr_SetAnimKnobAllInternal` / `GScr_SetFlaggedAnim*Internal` /
`GScr_ClearAnim` / `GScr_GetAnimTime` / `GScr_SetAnimTime`, each annotated with
the retail SP address it was decompiled from, plus the method-table block at
`:21615-21648`. Parameter order, the defaults (weight 1, goal time 0.2, rate 1),
the range checks and the error strings are taken from there.

T5's flag byte, its own comment at `:21594`: **bit 0 = "complete"** (select the
`XAnimSetComplete*` entry point), **bit 1 = `bRestart`**; so `0 = Limited`,
`1 = plain`, `2 = LimitedRestart`, `3 = Restart`.

| # | builtin | T5 origin | cmd type | flags | state |
|---|---|---|---|---|---|
| 1 | `clearanim(%anim, blend)` | SP 0x00800660 | 1 | – | complete |
| 2 | `setanim(%anim[,w[,t[,r]]])` | SP 0x00801640 | 3 | 1 | complete |
| 3 | `setanimlimited` | SP 0x00801660 | 3 | 0 | complete |
| 4 | `setanimrestart` | SP 0x00801680 | 3 | 3 | complete |
| 5 | `setanimknob` | SP 0x00800CC0 | 4 | 1 | complete |
| 6 | `setanimknoblimited` | SP 0x00800CE0 | 4 | 0 | complete |
| 7 | `setanimknobrestart` | SP 0x00800D00 | 4 | 3 | complete |
| 8 | `setanimknoball(%anim,%root[,w[,t[,r]]])` | SP 0x00801170 | 5 | 1 | complete **with the §4.2 precondition** |
| 9 | `setanimknoballrestart` | SP 0x008011B0 | 5 | 3 | complete, same precondition |
| 10 | `setflaggedanim(flag,%anim[,w[,t[,r]]])` | SP 0x008026A0 | 3 | 1 | complete |
| 11 | `setflaggedanimlimited` | SP 0x008026C0 | 3 | 0 | complete |
| 12 | `setflaggedanimrestart` | SP 0x008026E0 | 3 | 3 | complete |
| 13 | `setflaggedanimknob` | SP 0x00801CF0 | 4 | 1 | complete |
| 14 | `setflaggedanimknobrestart` | SP 0x00801D30 | 4 | 3 | complete |
| 15 | `setflaggedanimknoblimited` | see below | 4 | 0 | complete |
| 16 | `setflaggedanimknoblimitedrestart` | SP 0x00801D50 | 4 | 2 | complete |
| 17 | `setflaggedanimknoball(flag,%anim,%root,…)` | SP 0x008021C0 | 5 | 1 | complete, §4.2 precondition |
| 18 | `setflaggedanimknoballrestart` | SP 0x008021F0 | 5 | 3 | complete, §4.2 precondition |
| 19 | `setanimtime(%anim, frac)` | SP 0x008027D0 | 6 | – | complete |
| 20 | `getanimtime(%anim)` | SP 0x008016C0 | – | – | complete |

`setflaggedanimknoblimited` (#15) is the one name not in T5's table: T5's MP
port did not carry it and SP index 122 was left unidentified there. It is
registered because the **shipped** IW4 animscripts tree in
`bin/home/codol_rawfiles/animscripts` calls it, and the flags rule every other
member of the family is built from pins it exactly at `flags = 0`. MEASURED
(the call site), INFERRED (the flags value, by the rule).

Already registered before this task and untouched: `getanimlength`,
`animhasnotetrack`, `getnotetracktimes` (functions, `src/scr_vm_main.c:150-152`),
`animmode`, `orientmode`, `setanimstate`, `setaimanimweights`
(`codol_actor_lifecycle.cpp:1304-1310`).

### 4.1 Receiver, and why it is narrower than T5's

`anim_receiver()` requires `CODOL_ActorOwnedTree(ent)` to answer non-NULL,
i.e. a live actor or an actor corpse, and then requires
`Com_GetServerDObj(ent)` with `DObjGetTree(obj) == tree`. T5 accepts any
entity with an animtree. The narrowing is deliberate: on this server only an
actor owns a server animtree, and only an actor's commands are carried by the
snapshot's animation-command section (`CODOL_ActorCaptureSources`, which is
already species-independent). Animating anything else would mutate server
state that the client never hears about. The refusal names the reason.

### 4.2 Knob-all, and the one precondition

C1 dispatches wire type 5 to `0x63b9c0` (plain) or `0x63bad0` (complete). The
retained CoD4 XAnim exports `XAnimSetGoalWeightKnobAll(DObj_s*, unsigned,
unsigned, float, float, float, unsigned, int)` (`_xanim.asm:12466`) but **no**
`XAnimSetCompleteGoalWeightKnobAll`. What "complete" adds is raising the goal
weight of the ancestors *above the named root anim*; the knob-all walk itself
already drives the chain from the anim up to the root anim to weight 1
(MEASURED, `C1 0x63bb7a` pushes a literal `fld1` into the per-ancestor setter,
and `0x63bad0`/`0x63b9c0` both open by calling `0x63bbe0`, the Knob entry
point, exactly as the retained `XAnimSetGoalWeightKnobAll` opens by calling
`XAnimSetGoalWeightKnob`).

So rather than silently drop the missing half, the complete forms **refuse a
root anim that has a parent**:

```
setanimknoball: this server has no XAnimSetCompleteGoalWeightKnobAll;
the root anim of a knob-all must be a top-level node of the animtree
```

MEASURED: every knob-all in T5's zombie animscripts roots at `%body` or
`%root`, and `body` is the top-level node of
`bin/home/codol_rawfiles/animtrees/generic_human.atr` (line 1, column 0), so
the refusal never fires for the zombie set and the operation is exact there.
The remaining work, if a deeper root ever appears, is one more asm entry point
shaped like `src/asmsource/_codol_xanim_complete_knob.asm` — that file is the
existing precedent for "Knob plus the ancestor completion loop".

Both knob-all forms also reproduce T5's own two refusals: a root anim equal to
the anim, and a root anim that is not an ancestor (walked over
`anims->entries[].parent`). A root in a different tree is already refused one
level down by `Scr_GetAnim`.

### 4.3 `XAnimHasTime` and `XAnimGetParamValue`, both absent — and why that is correct

* T5's flagged forms and `getanimtime` call `XAnimHasTime`, which the retained
  CoD4 XAnim does not export. `anim_has_time()` reproduces the predicate from
  the data: a primitive (`entries[ref].numAnims == 0`) always has a time, and a
  blended parent only has one when it is a sync group
  (`u.animParent.flags & 3`, the `loopsync`/`nonloopsync` bits assigned by
  `GetAnimTreeParseProperties` in `src/cscr_animtree.cpp`). The same `flags & 3`
  is what `codol_dog_animation.c:notified_target_proven` already requires
  before hanging a notify on a non-leaf. INFERRED, but from two independent
  in-tree agreements.
* T5's setters call `XAnimGetParamValue(tree, index, "rate"/"goaltime"/
  "goalweight", &out)` to let the animtree override the defaults. That is a T5
  animtree feature: MEASURED, `src/cscr_animtree.cpp`'s
  `GetAnimTreeParseProperties` knows only `loopsync nonloopsync complete
  additive client separate forceload`, and the shipped `.atr` files carry no
  per-anim rate/goaltime/goalweight. Omitting the call is therefore correct for
  this data, not a shortcut.

### 4.4 Publication, clamping and error handling

`anim_publish()` applies the operation to the server's own XAnim tree **first**
and appends to `CODOL_ActorAnimJournalAppend` only on success, so a refused
operation publishes nothing. A nonzero XAnim return becomes a script error with
T5's own texts (`GScr_HandleAnimError`): error 1 → `"root anim is not an
ancestor of the anim"`, error 2 → `"cannot flag anim since it has 0 effective
goal weight"`. It is never fatal.

Clamps: T5's `G_StoreAnimCommand` (SP 0x004E7D80) clamps the *snapshotted*
command to weight 0..1, goal time 0..1.5, rate 0..3 while XAnim still receives
the script's values. That is reproduced exactly, and it also happens to sit
inside the journal validator's own bounds (weight ≤ 5, rate ≤ 5, blend ≤ 1.7,
`codol_actor_anim_journal.c:valid_event`).

Command time is `level.time ? level.time : 50`, T5's own expression; the
journal rejects time 0.

Generation is `ent->useCount`, which MEASURED equals
`codol_actor_lifetime_t::generation` (`codol_actor_lifecycle.cpp:150`), so the
events key correctly against the capture/archive path.

A journal append that is refused anyway logs one rate-limited warning per
second rather than one per animation per actor per frame.

---

## 5. What is deliberately NOT here

Not registered, not stubbed. Derived by gating the shipped IW4 animscripts
tree against the new table (§8) and by grepping T5's `animscripts/` and
`maps/_zombiemode*`:

| name | why not |
|---|---|
| `animscripted`, `animscriptedskiprestart`, `stopanimscripted`, `startscriptedanim` | a separate subsystem: scripted root-motion alignment (T5 `GScr_AnimScripted_SP` 0x00808690 + `GScr_UpdateScriptedAnim_SP`), which needs origin/angle alignment, `getstartorigin`/`getstartangles`/`getmovedelta` and a per-frame updater. Not attempted. |
| `useanimtree` | T5 `GScr_UseAnimTree`; binds a *second* tree to an entity. The actor tree here is owned by `CODOL_ActorPrepareAnimation`, and rebinding it is an actor-lifecycle change, not a script one. |
| `setanimknoballlimited`, `setanimknoballlimitedrestart`, `setflaggedanimlimitedrestart`, `clearanimlimited`, `setanimknoblimitedrestart` | SP slots T5's own port skipped; no call site in either the shipped animscripts or T5's zombie set. Add them the moment a call site appears — the flags rule already determines all but `clearanimlimited`. |
| `animcustom`, `setproneanimnodes`, `setidleanimoverride`, `setaiminganims`, `updateprone` | AI pose/aim subsystems, not the `%anim` surface. |
| `getmotionangle`, `getstartorigin`, `getstartangles`, `getmovedelta` | root-motion queries; they belong with `animscripted`. |
| `DoNoteTracks` and its whole family | pure GSC in T5, §3. Porting it is the *other* worker's file tree. |

---

## 6. Defect found in `src/codol/player/codol_dog_animation.c` (not this task's file)

MEASURED. C1 1.1.1.13's animation-command executor is `0x443e90`; the type
dispatch is `jmp *0x444140(,%eax,4)` with `eax = type - 1`, and the table reads

```
444140  1d3f4400 353f4400 4d3f4400 ed3f4400 8f404400 26414400
        ^t1      ^t2      ^t3      ^t4      ^t5      ^t6
```

| type | arm | `arg2 & 1` clear | `arg2 & 1` set |
|---|---|---|---|
| 1 | 0x443f1d | `0x63b210(tree, ref, blend)` | — |
| 2 | 0x443f35 | `0x63b250(...)` | — |
| 3 | 0x443f4d | `0x63c520` | `0x63c730` |
| 4 | 0x443fed | `0x63bbe0` | `0x63b8b0` |
| 5 | 0x44408f | `0x63b9c0` | `0x63bad0` |
| 6 | 0x444126 | `0x63c310(ref, tree, value)` | — |

`0x63b9c0` and `0x63bad0` (the type-5 pair) both **open by calling
`0x63bbe0`**, which is what the retained `XAnimSetGoalWeightKnobAll`
(`_xanim.asm:12466`) does with `XAnimSetGoalWeightKnob`. `0x63bbe0` and
`0x63c520` have byte-identical prologues apart from the animIndex arriving on
the stack rather than in `edi`. So `0x63bbe0` is Knob, `0x63c520` is the plain
setter, and the fields mean

* **type** = plain (3) / knob (4) / knob-all (5)
* **arg2 bit 0** = complete
* **arg2 bit 1** = restart

which is exactly T5's own `(type, flags)` split. `apply_batch`
(`codol_dog_animation.c:215`) instead reads:

```c
else if(c->type==4 && (c->arg2&1)) CODOL_XAnimSetCompleteGoalWeightKnobNotified(...)
else if(c->arg2&1)                 XAnimSetGoalWeightKnob(...)        /* type 3, bit0 */
else if(c->type==4)                XAnimSetCompleteGoalWeight(...)    /* type 4, no bit0 */
else                               XAnimSetGoalWeight(...)
```

i.e. `type` = plain/complete and `arg2 bit 0` = knob. The two readings agree on
`(3,0)` and `(4,1)` and disagree on `(3,1)` and `(4,0)`.
`codol_dog_states.cpp` emits `(3,0)` via `setGoal`, `(4,1)` via `completeKnob`
and **`(4,0)` via `completeGoal`** — so on every `completeGoal` the server sets
a *complete goal weight* while C1 performs a *knob*. INFERRED consequence: a
server/client divergence in sibling fading on exactly those transitions; it has
never been isolated live because both operations do raise the named animation.

Suggested patch, for the owner of that file (not applied here):

```c
/* OLD */
        else if(c->type==4 && (c->arg2&1))result=CODOL_XAnimSetCompleteGoalWeightKnobNotified(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,c->arg2>>1,channel);
        else if(c->arg2&1)result=XAnimSetGoalWeightKnob(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,c->arg2>>1);
        else if(c->type==4)result=XAnimSetCompleteGoalWeight(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,0,c->arg2>>1);
        else result=XAnimSetGoalWeight(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,0,c->arg2>>1);
/* NEW -- C1 0x443e90: type is plain/knob, arg2 bit 0 is "complete". */
        else if(c->type==4 && (c->arg2&1))result=CODOL_XAnimSetCompleteGoalWeightKnobNotified(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,c->arg2>>1,channel);
        else if(c->type==4)result=XAnimSetGoalWeightKnob(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,c->arg2>>1);
        else if(c->arg2&1)result=XAnimSetCompleteGoalWeight(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,0,c->arg2>>1);
        else result=XAnimSetGoalWeight(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,0,c->arg2>>1);
```

plus, in `codol_dog_states.cpp`, `completeGoal` becoming `goal(...,3,1)` and
`completeKnob` becoming `goal(...,4,1)` (already correct), and `setGoal`
staying `(3,0)`. **Not applied**: it changes the dog, the only actor whose
animation has ever been seen working, and it belongs with a live dog test.
`codol_script_anim.c` does not route through `apply_batch` precisely so that
the new builtins can be C1-correct without touching the dog.

One loose end, flagged rather than resolved: for command type 6 the writer
`codol_animcmd.c` emits a 5-bit `fraction`, while C1's type-6 arm reads
`cmd+0x24`, the slot `CODOL_ANIMCMD_SEMANTICS_20260915.md` identifies as
*blend*. That is consistent only if the decoder deposits the 5-bit value at
`+0x24`; the existing writer was measured against the decoder and is taken as
correct here, but no one has restated it since the field rename.

---

## 7. The zombie species' three function pointers — not wired, on purpose

`codol_actor_species_t` carries `stateIndex` / `stateName` / `stateApply`, the
interface to a **native** clip machine, and `setanimstate` is the CoDOL-authored
bridge from a CoDOL-authored animscript into it. T5 has exactly one such
machine, for the dog (`bg_dog_animations_mp.cpp`), and animates every other
species from GSC. A T5-ported zombie animscript never calls `setanimstate`; it
calls `setflaggedanimknoballrestart` and friends.

Filling those three pointers for the zombie would therefore mean inventing
state names, transitions, blends and rates with no vendor source — the option
`CODOL_ACTOR_SPECIES_20260920.md` §5 rejected. MEASURED, nothing native blocks
a GSC-animated actor:

* `CODOL_ActorRunFrame` only calls `stateApply` when the pointer is non-NULL
  (`codol_actor_lifecycle.cpp:871`), so a NULL backend simply means the native
  path publishes nothing and the animscript owns the tree.
* `CODOL_ActorCaptureSources` / `CODOL_ActorArchivePose` /
  `CODOL_ActorDeliveryArchive` / `CODOL_DogAnimCapture` are already
  species-independent: they walk whatever the actor's DObj tree currently is.
  The per-client bootstrap (`CODOL_DogAnimBootstrap`) is likewise a pure
  function of a captured pose. So a zombie animated purely by GSC is captured,
  bootstrapped and delivered by the same machinery the dog uses.
* `CODOL_ActorPrepareAnimation` / `CODOL_ActorFinishInitialization` gate on the
  species' `animtree` and `treeSelector` columns, both already correct for the
  zombie row (commit `9b0ec4a8`).

**So the zombie's animation backend is now the scripted path, and it is
reached without a species-table change.** The only edit made on that side is
`codol_actor_lifecycle.cpp`'s `setanimstate` refusal, which now names the
builtins to use instead of only saying that a native machine is absent.

What the zombie still needs is on the other side of the file boundary: the nine
`zm/maps/mp/animscripts/zombie_*.gsc` modules currently park on
`"killanimscript"`, and T5's real ones (`animscripts/zombie_{init,move,stop,
combat,death,pain,melee,run,shared,utility}.gsc`) have to be ported into them.
That tree belongs to the concurrent zombies-GSC worker.

---

## 8. Builtin list, for reconciliation with the zombies-GSC worker

Registered by this task, all methods, all in `src/scr_vm_main.c`:

```
clearanim                         setflaggedanim
setanim                           setflaggedanimlimited
setanimlimited                    setflaggedanimrestart
setanimrestart                    setflaggedanimknob
setanimknob                       setflaggedanimknobrestart
setanimknoblimited                setflaggedanimknoblimited
setanimknobrestart                setflaggedanimknoblimitedrestart
setanimknoball                    setflaggedanimknoball
setanimknoballrestart             setflaggedanimknoballrestart
setanimtime                       getanimtime
```

Evidence that this covers the surface: gating the **shipped IW4 animscripts
tree** (`bin/home/codol_rawfiles/animscripts`, 80+ files, reached with
`--seed animscripts/move.gsc --seed animscripts/init.gsc --only animscripts`)
reports **no** unresolved name from the `%anim` family except the AI/pose and
scripted-alignment names listed in §5. Before this task every one of the twenty
above was unresolved there.

---

## 9. Gate and build results

Script gate, the two forms in the brief, after the zombies-GSC commit
`fe816479` landed:

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles \
    --seed maps/mp/gametypes/war.gsc --binary bin/codol_dedrun_next.exe
  builtins registered: 929
  validated against binary: bin/codol_dedrun_next.exe (20 source registrations absent from it)
  scripts in effective tree: 1172
  scripts the loader would lower: 108
  every reachable script resolves against the registered builtin table

python tools/codol_script_resolve.py --root bin/home/codol_rawfiles/zm \
    --root bin/home/codol_rawfiles --seed maps/mp/gametypes/zm.gsc \
    --seed maps/mp/zm_prototype_sh.gsc --binary bin/codol_dedrun_next.exe
  builtins registered: 929
  validated against binary: bin/codol_dedrun_next.exe (20 source registrations absent from it)
  scripts in effective tree: 1196
  scripts the loader would lower: 117
  every reachable script resolves against the registered builtin table
```

**Read the "20 source registrations absent from it" line correctly.** With
`--binary`, the tool *intersects* the source table with the shipped
executable's table (`tools/codol_script_resolve.py:249`, `registered =
present`), so the twenty new names are excluded until someone links a new
`bin/codol_dedrun_next.exe`. Until then, a script that calls one of them will
be reported as an unknown function by the `--binary` form and resolve cleanly
without it:

```
... (same zm command, no --binary)
  builtins registered: 948
  every reachable script resolves against the registered builtin table
```

The zm form with the ten actor seeds (`aitype/enemy_zombie_zm.gsc` plus the
nine `maps/mp/animscripts/zombie_*.gsc`) is also clean: 128 lowered, no
unresolved name.

Build — never a bare `make`:

```
make obj/codol/codol_script_anim.o   -> OK
make objects                         -> OK, "Objects done"
```

No warnings from the new file. The only warnings in the changed region of
`codol_actor_lifecycle.cpp` are the three pre-existing ones already recorded in
`CODOL_ACTOR_SPECIES_20260920.md` §2.4 (`-Wmisleading-indentation` at `:655`
and `:966`, `-Wsign-compare` at `:1085`).

`nm obj/codol/codol_script_anim.o` shows all twenty `CODOL_Scr_*` entry points
as `T`, and every one of its undefined symbols — `Scr_GetAnim`,
`XAnimSetGoalWeight`, `XAnimSetCompleteGoalWeight`, `XAnimSetGoalWeightKnob`,
`XAnimSetGoalWeightKnobAll`, `XAnimClearTreeGoalWeights`, `XAnimSetTime`,
`XAnimGetTime`, `CODOL_XAnimSetCompleteGoalWeightKnobNotified`,
`CODOL_ActorAnimJournalAppend`, `CODOL_ActorOwnedTree`,
`codol_actor_delivery_failure` — is defined `T`/`B` elsewhere in the object
tree. No executable was linked and nothing was copied into `bin/`. No server,
lobby or client was started or stopped. No git write command was run.

Line endings, `tr -cd '\r' | wc -c` against `git show HEAD:<f>`:

| file | HEAD CR | after CR | HEAD lines | after lines |
|---|---|---|---|---|
| `src/scr_vm_main.c` | 1871 | 1896 | 1874 | 1899 |
| `src/codol/player/codol_actor_lifecycle.cpp` | 0 | 0 | 1662 | 1672 |

`scr_vm_main.c` is CRLF, and the 25 added lines are all CRLF (ΔCR = Δlines).
`codol_actor_lifecycle.cpp` is LF at HEAD and stays LF. The two new files are
LF.

---

## 10. Live verification checklist

Nothing here has run live. In order:

1. **Link and redeploy** `bin/codol_dedrun_next.exe`, then re-run both gate
   forms *with* `--binary` and confirm `0 source registrations absent`.
2. **Dog regression first.** An mp map, dogs killstreak, `developer 0`. The dog
   does not use any new builtin; the only change on its path is the
   `setanimstate` error text, which it should never reach. Any change in dog
   animation is a regression from something else in this batch.
3. **Smallest scripted-animation test.** In a zm match, on a spawned zombie:
   `self setflaggedanimknoballrestart("testanim", %ai_zombie_walk_v1, %body, 1, 0.2, 1);`
   then `self waittill("testanim", note);`. Expect the thread to wake with
   `note == "end"` after the clip's length, and the client to show the clip.
   A `"blended nonsynchronized animation has no concept of time"` here means
   the animation resolved to a non-sync parent node, not a failure of the
   builtin.
4. **Watch for** `CoDOL anim: <method>() on entity N applied but could not be
   published (...)`. One line per second means the journal is refusing — most
   likely a cut already taken at this server time, which would be a frame
   ordering problem, not a script one.
5. Only then port T5's zombie animscripts wholesale.
