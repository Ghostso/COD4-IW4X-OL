# Dog killstreak: every spawn fails — `no server animtree named "dog"`

Report date: 2026-09-20.
User report: *"I also tried to call in the dog killstreak a little bit ago and it didn't work."*
Evidence: `bin/home/main/qconsole.dogs-20260920.log` (live, failing) vs
`bin/home/main/qconsole.nuked4.log` (2026-09-16, working).

Every claim below is labelled **MEASURED** (read out of the log, the source, the
retained disassembly or the shipped launcher) or **INFERRED**.

---

## 1. Verdict

**One defect, in native code.** `XAnim_s.debugName` is written **only in
developer builds**, and `CODOL_ServerAnimTreeName()` uses it as a tree's
identity. On the live server (`developer 0`) it therefore answers `NULL` for
*every* animtree, so `CODOL_ActorPrepareAnimation()` can never find the tree
named `"dog"` and refuses every `spawnactor`.

The dog animtree itself was registered, mounted, parsed and populated
correctly. Nothing about the scripts, the animlist mask, the spawner or the
model was wrong.

The three leads in the task brief are all **negative** — see §4.

---

## 2. Proof

### 2.1 The failing signature

MEASURED, `qconsole.dogs-20260920.log:317-330`, repeated for dogs 0..3:

```
CoDOL dogs: no map dog_spawner entity; building one with spawnactorspawner( "actor_enemy_dog_mp" )
Warning: CoDOL dogs: actor animation: no server animtree named "dog" is registered
         (3 registered; a loaded script must declare #using_animtree("dog") ...)
Warning: CoDOL dogs: spawnactor on 'actor_enemy_dog_mp': actor ent 376 initialization failed
CoDOL dogs: spawnactor produced no dog 0 for node at (3203, 1265, 32); skipping it
```

The warning's own advice is wrong: a loaded script **does** declare the tree.

### 2.2 The declaration is present and has been since 2026-09-16

MEASURED. `bin/home/codol_rawfiles/maps/mp/_dogs.gsc:97` contains a live
`#using_animtree("dog");`. `git log -S` dates it to commit `587568c5`
(2026-09-16 01:27), which predates both the running binary
(`bin/codol_dedrun_next.exe`, 09-17 16:02) and the failing run.

MEASURED. `_dogs.gsc` is in the compiled closure:
`tools/codol_script_resolve.py --list-reachable` lists it among the 108 files
the loader lowers for a `war` match. The log also shows it executing (it
printed the `no map dog_spawner entity` line).

MEASURED. Exactly three files in that 108-file closure declare an animtree —
`maps/mp/_animatedmodels.gsc:17` (`animated_props`), `maps/mp/_dogs.gsc:97`
(`dog`), `maps/mp/killstreaks/_ac130.gsc:1816` (`script_model`) — and the
warning reports exactly **3 registered**. The count is right; the *names* are
missing.

### 2.3 Why the names are missing

MEASURED, `src/asmsource/_xanim.asm:10883` (`XAnimCreateAnims`):

```asm
call dword [ebp+0x10]          ; alloc(count*8 + 0xc) -> esi = XAnim_s*
mov  eax, [ebp+0xc]
mov  [esi+0x4], eax            ; ->size  ... the ONLY field initialised
cmp  byte [g_anim_developer], 0x0
jnz  XAnimCreateAnims_10       ; <-- developer-only arm
XAnimCreateAnims_30:
...
XAnimCreateAnims_10:
  call Hunk_AllocDebugMem / strcpy
  mov  [esi], ebx              ; ->debugName       (offset 0)
  ...
  mov  [esi+0x8], eax          ; ->debugAnimNames  (offset 8)
```

MEASURED, `src/asmsource/_xanim.asm:13183` (`XAnimInit`):

```asm
mov  eax, com_developer
mov  eax, [eax]
mov  eax, [eax+0xc]
test eax, eax
setnz byte [g_anim_developer]      ; latched ONCE at startup
```

So with `developer 0`, `XAnim_s.debugName` is never written — the struct comes
straight from the allocator with only `size` set.

MEASURED, `src/codol/assets/codol_model_animation.c:190-203`:
`CODOL_ServerAnimTreeName()` returns `Scr_GetAnims(tree)->debugName`. With a
NULL `debugName` it returns NULL for **every** tree, so the `strcmp(name,"dog")`
scan in `CODOL_ActorPrepareAnimation` (`codol_actor_lifecycle.cpp`) matches
nothing.

Note the header contract at `codol_model_animation.h:163` already promises
*"the canonical name tree id was registered under"* — `debugName` is not that,
so the implementation never matched its own documented contract.

### 2.4 The controlled A/B that settles it

MEASURED. `CoDOL mounted animtree: …` (`src/cscr_parser.cpp:574`) is a
`Com_DPrintf`, i.e. it prints only under `developer`.

| | `qconsole.nuked4.log` (09-16, dogs worked) | `qconsole.dogs-20260920.log` (09-20, failed) |
|---|---|---|
| `CoDOL mounted animtree` lines | **4** → `developer 1` | **0** → `developer 0` |
| `no server animtree named "dog"` | **0** | **4** |
| dogs | spawned, pathed, animated (`ent 198 setanimstate 'move_run'`) | all four refused |

MEASURED, the launchers:
* `bin/START-CODOL-SERVER.cmd:64` — `if not defined CODOL_DEVELOPER set "CODOL_DEVELOPER=0"` ← the live server
* `bin/START-CRASH-TEST.cmd:16` — `if not defined CODOL_DEVELOPER set "CODOL_DEVELOPER=1"` ← the test harness

The 09-16 verification was run under the developer-1 harness. That is the whole
difference. Nothing regressed; the feature has never worked on a production
launch.

### 2.5 The pipeline around the bug is correct

MEASURED, retained disassembly, in execution order:

1. `G_InitGame` (`_g_main_mp.asm:713-714`) calls `GScr_LoadScripts` **then**
   `BG_LoadAnim`. `_g_main_mp.asm:574` sets the bgs anim realm to `1`.
2. `GScr_LoadScripts` compiles the tree; each `#using_animtree` reaches
   `Scr_UsingTree` (`_scr_animtree.asm:615`, realm hardcoded `ecx=1`) →
   `Scr_UsingTreeInternal` (`:445`), which increments `gScrAnimPub+0x410`
   (`xanim_num[1]`) and stores the tree's **variable id** into
   `gScrAnimGlob+0x008` (`using_xanim_lookup[realm*128 + idx]`).
3. `BG_LoadAnim` calls `CODOL_RegisterServerAnimListReferences`
   (`_bg_animation_mp.asm:2166`), which resolves each animlist reference's tree
   through that **variable-id table** (`codol_model_animation.c:437-440`) and
   `Scr_FindAnim`s every dog animation into the server dog tree.
4. `Scr_PrecacheAnimTrees(alloc, 1)` (`_bg_animation_mp.asm:2201`) loops
   `1..xanim_num[1]` through `Scr_LoadAnimTreeAtIndex`, which parses
   `animtrees/dog.atr` and writes the built `XAnim_s*` into
   `gScrAnimPub + 0xc + (realm*128+idx)*4` — exactly the slot `Scr_GetAnims`
   reads.

A tree that failed to load here would `Com_Error` with `unknown anim tree <n>`
(`_scr_animtree.asm:1022`). No such error appears in the log, so the dog tree
**did** load. Step 3 proves the correct name source works in production: the
same file, 240 lines below the broken accessor, already uses it.

---

## 3. The fix

Identity now comes from the variable-id table, not from `debugName`.

The table cannot simply be read on demand: `Scr_EndLoadAnimTrees`
(`_scr_main.asm:201`) `ClearObject()`s the container and calls
`SL_ShutdownSystem(2)`, recycling the ids. The names are therefore **snapshotted
once**, while the compiler's objects are still alive.

**`src/codol/player/codol_actor_lifecycle.cpp`**
* New `CODOL_ActorSnapshotServerAnimTrees()` — copies the canonical name of
  every realm-1 tree out of `gScrAnimGlob+0x008` via
  `GetVariableName` → `SL_ConvertToString`, the same two steps
  `Scr_LoadAnimTreeAtIndex` itself uses to find `<name>.atr`.
* New `CODOL_ActorServerAnimTreeName()` — the snapshot, falling back to the
  retained `CODOL_ServerAnimTreeName()` (so developer builds and any tree
  registered after the snapshot, such as `BG_LoadAnim`'s own `multiplayer`,
  still resolve).
* `CODOL_ActorPrepareAnimation` scans with the new accessor, and its failure
  warning now **dumps every registered slot** (`1='dog' 2='script_model' …`,
  marking `<unnamed>` and `(no xanim)`), so a future failure names its own
  stage instead of repeating advice that is already satisfied.

**`src/codol/player/codol_actor_scripts.cpp`**
* The body of `CODOL_ActorScriptsLoadMapTypes` became `static
  ActorScriptsLoadMapTypes()`; the public function is now a wrapper that calls
  it and then takes the snapshot. A wrapper rather than a call at each
  `return` because the function has three non-fatal exits.
* Chosen site because it is the **last** script-loading step of
  `GScr_LoadScripts` (`scr_vm_main.c:1467`) — every `#using_animtree` has run,
  and `BG_LoadAnim`'s `Scr_EndLoadAnimTrees` is still far away.

Both files are within this task's ownership. No GSC changed.

---

## 4. The three leads, answered

### LEAD 1 — `//#using_animtree ("dog")` in `maps/mp/animscripts/dog_*.gsc`: **not a defect, do not uncomment**

MEASURED. The comment is in the **shipped T5 source itself** —
`D:\CoD\COD-GSC-Source\T5-STEAM-GSC\maps\mp\animscripts\dog_init.gsc:1` and
`dog_move.gsc:4` carry the identical `//#using_animtree ("dog");`. It is not a
CoDOL debugging leftover, which is why `dog_init.gsc`'s "nothing else changed"
header does not mention it.

MEASURED. Those ten files contain **zero** `%anim` references
(`grep -c '%' … = 0` for all of them), so they have nothing to declare a tree
*for*. T5 drives dog animation by name through `dog_shared`, not by `%token`.
`maps/mp/_dogs.gsc:97` is the correct and sufficient single declaration, and its
own comment block already explains exactly this.

Uncommenting would be inert (`Scr_UsingTreeInternal` dedupes by name, so no new
slot) and would diverge from the vendor source for no gain.

The second tree at `bin/home/codol_rawfiles/animscripts/dog/*.gsc` is the
**IW4/T5 single-player** set. MEASURED: none of its files is in the 108-file
compiled closure — the engine never loads it. It is inert reference material;
leaving it costs nothing and deleting it is not required by this bug.

### LEAD 2 — the `german_sheperd_dog` xmodel warning: **a reporting artifact, not a second defect**

MEASURED, ordering in the log:

```
:147  CoDOL native map archives mounted: 5 (zm_asylum_sh, zm)
:161  Warning: CoDOL xmodel 'german_sheperd_dog' is not in any mounted zone; using void (reported once)
:172  Rcon from 127.0.0.1:56599: map mp_killhouse_sh
```

The warning fired during the **zm startup map**, eleven lines *before* the mp
map was ever loaded.

MEASURED, `docs/zone_assets/ALL_xmodel.txt:2774-2777`: `german_sheperd_dog`
ships in `common_gametype_coop`, `common_gametype_mp`,
`coop_spec_mp_fav_tropical` and `mp_nuked` — **no zm zone**. So the warning was
*correct for the moment it was printed*.

MEASURED, `src/db_load.cpp:3445`: the suppression table is a function-local
`static char reported[32][64]` with a `static unsigned reported_count`, never
cleared between maps — **once per process, not once per map**. The later,
successful lookup on `mp_killhouse_sh` was silently suppressed.

MEASURED, direct proof the model is fine on an mp map —
`qconsole.nuked4.log:3949`:
`CoDOL dogs: ent 198 setenemymodel 'german_sheperd_dog' -> model 89`.

INFERRED: the zm-side request came from the dog preload, which the running
09-17 binary still performed on every category. Today's commit gating that
preload to `mp` already removes the trigger.

*Latent issue worth a separate fix (file not owned here):* the process-global
`reported[]` table means a genuine missing model on map N is silenced if map 1
happened to lack it. Making it per-`SV_SpawnServer` would restore the
diagnostic. See §5.

### LEAD 3 — `CODOL_ANIMLIST_MASK=2`: **plumbed and working, bit 2 not cleared**

MEASURED. `bin/START-CODOL-SERVER.cmd:76,128` pass `+set codol_animlistMask 2`.
`src/sv_main.c:3398` registers it (`Cvar_RegisterInt`, range 0..15) and
`:5583-5591` consumes it:

```c
if(!CODOL_SetServerAnimListFlags((unsigned)codol_animlistMask->integer))
    Com_Error(ERR_DROP,"CoDOL invalid animation class mask");
if(CODOL_LoadClientAnimTrees(mapname,CODOL_ServerAnimListFlags(),NULL)<0)
    Com_Error(ERR_DROP,"CoDOL animation list rawfile could not be loaded");
```

Both failures are hard `Com_Error`s. Neither appears in the log, so the mask was
accepted and the dog animlist loaded. `CODOL_RegisterServerAnimListReferences`
then matched the `dog` tree through the authoritative name table and registered
its animations (§2.5 step 3). No clearing of bit 2.

---

## 5. Open items (not fixed here — outside this task's file ownership)

1. **`src/codol/assets/codol_model_animation.c:190`** — `CODOL_ServerAnimTreeName()`
   still reads the developer-only `debugName`. The snapshot added here bypasses
   it for the actor path, but the accessor remains wrong for any future caller.
   Recommended: move the snapshot into `codol_model_animation.c` (where the
   `CODOL_ANIM_TREE_NAMES` layout already lives, line 41) and have
   `CODOL_ServerAnimTreeName` serve it, then delete the duplicate in
   `codol_actor_lifecycle.cpp`.
2. **`src/codol/assets/codol_model_animation.c:499`** —
   `CODOL_ClientAnimTreeForServerTree()` has the same latent bug. MEASURED: it
   currently has **no callers outside its own file**, and `CODOL_ResolveMpAnim`
   deliberately bypasses it via the animlist refs, so it is not live. Item 1
   fixes it for free.
3. **`src/db_load.cpp:3445`** — make the "reported once" xmodel table per-map
   (see LEAD 2) so a real missing model on a later map is not masked.
4. **`tools/BUILD-CODOL.ps1:64`** — `-ObjectsOnly` invokes
   `make … print-objects`, and the makefile has no such target, so the script
   aborts with `No rule to make target 'print-objects'`. Pre-existing; unrelated
   to this bug, but it blocks the documented build path.

---

## 6. Gate and build

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles \
    --seed maps/mp/gametypes/war.gsc --binary bin/codol_dedrun_next.exe
  builtins registered: 929
  validated against binary: bin/codol_dedrun_next.exe (0 source registrations absent from it)
  scripts in effective tree: 1153
  scripts the loader would lower: 108
  every reachable script resolves against the registered builtin table
```

(unchanged from the pre-change baseline — no GSC was modified)

```
make obj/codol/codol_actor_lifecycle.o obj/codol/codol_actor_scripts.o   -> OK
```

No new warnings from the changed regions; the warnings emitted are pre-existing
ones elsewhere in `codol_actor_lifecycle.cpp`
(`-Wmisleading-indentation` at :709/:1001, `-Wsign-compare` at :1120).

Linkage verified with `nm`: `_CODOL_ActorScriptsLoadMapTypes` (T),
`_CODOL_ActorSnapshotServerAnimTrees` (U in `codol_actor_scripts.o`,
T in `codol_actor_lifecycle.o`), `_CODOL_ActorServerAnimTreeName` (T).

Line endings: both changed files are LF in HEAD and LF in the working tree
(`tr -cd '\r' | wc -c` = 0 before and after).

No binary was copied into `bin/`. No server, lobby or client was started or
stopped.

---

## 7. Live verification checklist

The fix is in object files only — it needs a link and a redeploy of
`codol_dedrun_next.exe` before it can be tested.

1. Launch normally via `bin/START-CODOL-SERVER.cmd` — **with `developer 0`**.
   Testing under `START-CRASH-TEST.cmd` (`developer 1`) would pass even with
   the bug present; that is exactly how this defect survived since 09-16.
2. Call in the dogs killstreak on an mp map.
3. Expect **no** `no server animtree named "dog"` warning, and `CoDOL dogs: ent
   <n> setenemymodel 'german_sheperd_dog' -> model <n>` followed by
   `animscript -> dog_move` / `setanimstate 'move_run'`, as in
   `qconsole.nuked4.log:3949-4026`.
4. If it still fails, the new warning now prints every registered slot and
   whether each has an XAnim, which distinguishes "not declared" from
   "declared but unnamed" from "named but not built".
