# Actor species table, and the zm humanoid zombie

Report date: 2026-09-20.
Scope: generalise the actor subsystem off the hardcoded `"dog"` (stage 1), and
bind a humanoid zombie species to `generic_human` (stage 2). Not in scope: the
zombies gameplay loop (rounds, points, box, perks).

Every claim below is labelled **MEASURED** (read out of the source, the shipped
zones, `C1.exe` or a tool run) or **INFERRED**.

---

## 1. Verdict up front

1. **Stage 1 is done.** Four `"dog"` literals and one dog-only script loader are
   now columns of one table in `src/codol/player/codol_actor_scripts.h/.cpp`.
   The dog row reproduces today's behaviour exactly, including the asset
   category gate added this morning.
2. **The enemy zombie body ships, and it is `c_zom_ger_body1`** (+ three
   siblings and a boss). MEASURED. It is a **per-map** asset, present in all
   three zm map zones and in no `common_*` zone.
3. **Stage 2's animation binding is settled and the server side is wired.**
   C1's serverinfo-2482 bit `0x08` does the whole job: it loads
   `animlists/common_zombie.animlist` (which binds every `ai_zombie_*` name
   into `generic_human`) **and** registers `generic_human` as the client's
   actor composition tree 3. The only thing outside this task's file ownership
   is the mask *value* the launcher passes — one number, §6.
4. **A humanoid zombie will still T-pose after that patch**, and §5 says why
   with evidence: T5 animates humanoid AI from GSC `%anim` references, and this
   server registers none of the builtins that path needs. The dog's native clip
   machine has no humanoid counterpart to port — not in OpenBLOPS, not anywhere.
   That is the remaining work item, and it is a workstream, not a line.

---

## 2. Stage 1 — the species table

### 2.1 Shape

`src/codol/player/codol_actor_scripts.h`:

```c
typedef struct {
    const char *name;        /* aitype main()'s self.type, and getType()      */
    const char *animtree;    /* #using_animtree name; animtrees/<x>.atr       */
    unsigned treeSelector;   /* C1 actor composition tree index, 0..4         */
    unsigned animlistMask;   /* serverinfo 2482 bits this species needs       */
    unsigned talkBit;        /* setTalkToSpecies() bit for this species       */
    const char *category;    /* asset category that preloads the aitype       */
    const char *classname;   /* spawner classname, "actor_<aitype file>"      */
    const char *animscript;  /* animscript module prefix, "<dir>/<species>"   */
    codol_actor_state_index_t stateIndex;   /* native animation-state backend */
    codol_actor_state_name_t  stateName;    /*  ... NULL when there is none   */
    codol_actor_state_apply_t stateApply;
} codol_actor_species_t;
```

Accessors: `CODOL_ActorSpeciesCount/…Species(index)/…ByName/…ByClassname`, plus
`CODOL_ActorSpeciesAnimListMask(category)` for §6.

### 2.2 The two rows

| column | dog | zombie |
|---|---|---|
| `name` (`self.type`) | `dog` | `zombie` |
| `animtree` | `dog` | `generic_human` |
| `treeSelector` | 1 | 3 |
| `animlistMask` | `0x02` | `0x08` |
| `talkBit` | `0x01` | `0x02` |
| `category` | `mp` | `zm` |
| `classname` | `actor_enemy_dog_mp` | `actor_enemy_zombie_zm` |
| `animscript` | `maps/mp/animscripts/dog` | `maps/mp/animscripts/zombie` |
| state backend | `CODOL_DogState{Index,Name,Apply}` | NULL |

### 2.3 What each former literal became

| was | file:line (pre-change) | now |
|---|---|---|
| animtree scan for `"dog"` | `codol_actor_lifecycle.cpp:1429` | `strcmp(name, row->animtree)` |
| `treeSelector = 1 // common_dog` | `:1456` | `(int)row->treeSelector` |
| `treeSelector != 1` in FinishInitialization | `:1470` | `!= a->species->treeSelector` |
| corpse `treeSelector = 1` | `:1562` | species selector captured before `CODOL_ActorRelease` |
| `if (strcmp(value,"dog")) Scr_Error(...)` setter | `:257` | `CODOL_ActorSpeciesByName(value)`; unknown name errors |
| `Scr_AddString("dog")` getter | `:282` | `Scr_AddString(a->species->name)` |
| `if(!strcmp(species,"dog"))mask\|=1` | `:1056` | `mask \|= row->talkBit` |
| `sender->talkMask & 1` (×2) | `:617`, `:630` | `sender->talkMask & ActorTalkBit(a)` (receiver's row) |
| `unsigned char dogSpecies` | struct `:50` | `const codol_actor_species_t *species` |
| `CODOL_DogStateIndex/Apply/Name` calls (×5) | `:859 :898 :901 :690` | `a->species->state*` |
| `CODOL_ActorScriptsLoadDogType`, `dogScripts`, `dogLoaded` | `codol_actor_scripts.cpp` | `CODOL_ActorScriptsLoadType`, `speciesScripts[]`, `speciesLoaded[]` |
| hardcoded `maps/mp/animscripts/dog_*` ×9 | `codol_actor_scripts.cpp` | `LoadSpeciesScripts()` over `row->animscript` + nine suffixes |
| `if (!strcmp(classname,"actor_enemy_dog_mp"))` map scan | `codol_actor_scripts.cpp` | `CODOL_ActorSpeciesByClassname(classname)` |
| `if (zone && strcmp(zone,"mp")) return;` | `codol_actor_scripts.cpp` | per-row `strcmp(zone, row->category)` — **gate kept, expressed as a column** |

`CODOL_ActorScriptsLoadType` still refuses any classname without a table row, so
an unknown `actor_*` in a BSP is left alone rather than handed another species'
animscripts — the same refusal the old comment promised.

### 2.4 What the dog row proves still works

* MEASURED: `make obj/codol/codol_actor_scripts.o obj/codol/codol_actor_lifecycle.o`
  and a full `make objects` both succeed; the only warnings in the changed files
  are the three pre-existing ones (`-Wmisleading-indentation` at `:655`/`:956`,
  `-Wsign-compare` at `:1075`) that `CODOL_DOG_KILLSTREAK_20260920.md` §6
  already recorded.
* MEASURED, mp script gate unchanged:
  `python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --seed maps/mp/gametypes/war.gsc --binary bin/codol_dedrun_next.exe`
  → `scripts the loader would lower: 108`, identical to the dog-fix baseline.
* MEASURED, symbol table (`nm`): `_CODOL_ActorScriptsLoadType`,
  `_CODOL_ActorSpecies{,Count,ByName,ByClassname,AnimListMask}` are `T` in
  `codol_actor_scripts.o`; `_CODOL_ActorSpeciesByName` is `U` in
  `codol_actor_lifecycle.o`.
* By construction: with one row whose columns are the old constants, every code
  path for `self.type = "dog"` evaluates to the same values it did before —
  animtree `"dog"`, selector 1, talk bit 1, category `mp`, the same nine
  `maps/mp/animscripts/dog_*` modules, the same `CODOL_DogState*` backend, the
  same fatal/warning text positions. INFERRED (no live dog spawn was run; the
  fix from this morning is still object-only and needs a link + redeploy, per
  `CODOL_DOG_KILLSTREAK_20260920.md` §7).

---

## 3. C1's actor composition trees — the measurement the rest depends on

MEASURED 2026-09-20 by disassembling the shipped client,
`D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\C1.exe`
(`objdump -d --start-address=0x4083f0`):

```asm
40840b: mov  $0xc3f080,%eax           ; "generic_human"
408410: lea  -0x18(%ebp),%ecx         ; the walking name pointer
408416: mov  %eax,-0x18(%ebp)         ; [0] generic_human
408419: movl $0xc3f090,-0x14(%ebp)    ; [1] "dog"
408420: mov  %eax,-0x10(%ebp)         ; [2] generic_human
408423: mov  %eax,-0xc(%ebp)          ; [3] generic_human
408426: movl $0xc3f094,-0x8(%ebp)     ; [4] "zombie_dog"
40842d: mov  $0x1,%ebx                ; mask bit, rol'd each iteration
408432: xor  %edi,%edi                ; byte offset into bgs+0x90174
408434: mov  %ecx,-0x4(%ebp)
408437: ...
40843f: lea  0x90174(%edi,%edx,1),%esi ; the 5 x 0x14 record array
408446: ...                            ; zero the 0x14-byte record
408456: test %ebx,0x921f8(%eax)        ; serverinfo key 2482 bits
40845c: je   0x40846e                  ; bit clear -> leave this entry NULL
408461: mov  (%ecx),%edx               ; the name at this slot
408464: call 0x5c9a10                  ; register tree by name
40846c: mov  %eax,(%esi)
40846e: addl $0x4,-0x4(%ebp)           ; next name
408472: add  $0x14,%edi                ; next record
408475: rol  $1,%ebx                   ; next bit
408477: cmp  $0x64,%edi
40847a: jl   0x408437                  ; 0x64/0x14 = 5 iterations
```

Read the strings (`objdump -s --start-address=0xc3f010`):

```
 c3f020  common .. common_actor_shared .. common_human .. common_dog ..
 c3f060  common_civilian .. common_zombie
 c3f080  "generic_human"
 c3f090  "dog"
 c3f094  "zombie_dog"
```

so the five client actor composition trees are:

| selector | 2482 bit | animtree | animlist loaded by that bit (C1 0x408310) |
|---|---|---|---|
| 0 | `0x01` | `generic_human` | `animlists/common_human` |
| 1 | `0x02` | `dog` | `animlists/common_dog` |
| 2 | `0x04` | `generic_human` | `animlists/common_civilian` |
| 3 | `0x08` | **`generic_human`** | `animlists/common_zombie` |
| 4 | `0x10` | `zombie_dog` | **none — no animlist is tied to this bit** |

Three of the five are the same tree; C1 registers it three times so that the
human, civilian and zombie classes can be enabled independently while sharing
one skeleton. The hellhound tree sits at selector 4 with no animlist of its
own, because its 60 clips travel inside `common_zombie.animlist`.

MEASURED, C1 `0x408354/0x408377/0x40839a/0x4083bd`: each of bits 0x01/0x02/0x04/
0x08 calls `BG_TryLoadAnimList` (`0x408040`) and, when it returns false,
**clears its own bit** (`andl $0xfffffffe/fd/fb/f7`). MEASURED, `0x408040`: when
`DB_IsXAssetDefault(rawfile, "animlists/<x>.animlist")` is true — i.e. the
rawfile is absent — every exit is `xor %al,%al` (`0x408112` and `0x408130`), so
an absent animlist returns **false** and the class bit is cleared.

Consequence, MEASURED against `docs/zone_assets/ALL_rawfile.txt`:

```
animlists/common.animlist                code_post_gfx_mp
animlists/common_actor_shared.animlist   common_gametype_coop, common_gametype_zm, coop_spec_mp_fav_tropical
animlists/common_civilian.animlist       coop_* only
animlists/common_dog.animlist            common_gametype_coop, common_gametype_mp, coop_spec_mp_fav_tropical
animlists/common_human.animlist          common_gametype_coop only
animlists/common_zombie.animlist         common_gametype_zm, patch_common_gametype_zm
```

A zm match mounts `code_post_gfx_mp`, `common_mp(+patch)`,
`common_gametype_zm(+patch)` and the zm map zone. It therefore ships **no
`common_human` and no `common_civilian` animlist**, so bits `0x01` and `0x04`
are cleared by the client and selectors 0 and 2 are unreachable in zm no matter
what the mask says. `common_zombie.animlist` **does** ship there, so **bit
`0x08` is the one and only way to get `generic_human` onto a zm actor** — and
it is also the bit that supplies the `ai_zombie_*` → `generic_human` name
bindings. One bit, both halves. This is the single non-obvious constant in the
whole task, and it is the one I got backwards on the first read of the
disassembly before re-measuring.

MEASURED: `src/codol/assets/codol_model_animation.c:433-434` already lists
exactly these six animlists against exactly these masks, so the server's mirror
of C1's loader is correct and needs no change.

---

## 4. Stage 2 — the zombie species

### 4.1 Which xmodel is the enemy zombie body

**`c_zom_ger_body1`**, plus `c_zom_garbageman_body`, `c_zom_worker_body`,
`c_zom_secunityguard_body`, and the boss `c_zom_juggernaut_body1`.
MEASURED, `docs/zone_assets/ALL_xmodel.txt` (lines 768-948) and the per-zone
lists: each of the first four families is body + head + 17 gib/dismember
variants (`_behead`, `_larmoff_1/2`, `_larmspawn`, `_legsoff_1`, `_llegoff_1/2`,
`_llegspawn`, `_lowclean`, `_rarmoff_1/2`, `_rarmspawn`, `_rlegoff_1/2`,
`_rlegspawn`, `_torso_1`, `_upclean`) = 19 models, 78 `c_zom_*` xmodels per zone.

They ship in **`zm_asylum_sh`, `zm_prototype_sh`, `zm_zombie_training`** — the
zm *map* zones — and in **no** `common_*` zone. The only `c_zom_*` asset in
`common_gametype_zm` is `c_zom_head_human`, a head. INFERRED consequence: an
enemy zombie can only be spawned on a zm map; there is no shared enemy body.

`c_zom_juggernaut_body1` has **no** gib set (2 models only), which is how the
art marks a boss rather than a round zombie — it is left out of the rotation.

Negative results, all MEASURED:
* `fja_zm*/han_zm*/hea_zm*/boo_zm*/fpa_zm*/heg_zm*` are PLAYER customization
  slot parts (`<slot>_<outfit>_zm_<gender>_<variant>`, with `_vmchar` viewmodel
  variants, 7 zm outfits), also present in `ui_viewer_mp`. Never an enemy.
* `zombie_wolf` (all three zm map zones) is the hellhound — T5
  `character/character_sp_zombie_dog.gsc:4` `setModel("zombie_wolf")`.
* Every other `zombie_*` xmodel is a prop (perk machines, teddybear, power
  levers, icons…). No `zmb`/`undead`/`ai_zom*` xmodel exists.
* Of the 1,112 model names quoted by T5/BO1 `character/` + `xmodelalias/`
  scripts, exactly four exist in CoDOL (`c_usa_pent_ciaagent_body`,
  `c_usa_rebirth_hazmat_mask`, `german_sheperd_dog`, `zombie_wolf`) and **none**
  is a humanoid zombie body. CoDOL's `c_zom_*` families are CoDOL-original
  assets that merely follow Treyarch's naming scheme (their gib suffixes differ
  from T5's `_g_behead`/`_g_rarmspawn`).
* CoDOL ships **no** `character`, `aitype`, `mptype` or `xmodelalias` xasset
  type (`docs/zone_assets/COUNTS.tsv` has no such column), so nothing
  engine-side binds body+head+gibs; a script must name the raw xmodels. That is
  what `zm/character/character_zm_zombie.gsc` does.

### 4.2 The animation content, and that it lives in `generic_human`

* MEASURED: `animtrees/generic_human.atr` ships in `common_mp` and
  `patch_common_mp` — **mounted for every asset category**, including zm. The
  patch copy is 123,640 bytes / 5,345 lines and **389 of those lines name
  `ai_zombie_*` nodes** (`ai_zombie_attack_crawl`, `ai_zombie_attack_forward_v1`,
  `ai_zombie_bartear_*`, `ai_zombie_traverse_*`, …).
  Extracted with `zone_assets.py` out of the shipped `.ff`.
* MEASURED: `animlists/common_zombie.animlist` (7,874 bytes in
  `patch_common_gametype_zm`) groups its entries as
  `=player_3rd_person` 16, **`=generic_human` 220**, `=zm_magic_box` 2,
  `=zombie_cymbal_monkey` 1, `=zombie_dog` 60. The whole `ai_zombie_*` set is
  in the `generic_human` group. This is the animation→tree binding
  `CODOL_RegisterServerAnimListReferences` replays server-side, so loading that
  animlist (2482 bit `0x08`) is what makes `CODOL_FindAnimInServerTree` able to
  resolve `ai_zombie_*` into the server's `generic_human` tree.
* MEASURED: `animtrees/zombie_dog.atr` (`common_gametype_zm`, 2,278 bytes) is
  pure hellhound — `zombie_dog_run_knob`, `zombie_dog_attackidle`,
  `zd_attack_player_late`, `zombie_dog_turn_knob` — and C1 registers it at
  selector **4**, not at the zombie class bit. So the hellhound and the
  humanoid zombie are two different species rows sharing one animlist, which
  is exactly how the shipped data is organised.
* MEASURED, xanim counts (correcting the brief): `common_gametype_zm` holds
  **209** `ai_zombie_*` xanims, plus 19 `ai_zombie_thundergun_*` in
  `zm_prototype_sh` = **228** total. The often-quoted **338** is the count of
  xanims in `common_gametype_zm` whose name merely *contains* "zom", which also
  sweeps in ~90 `zombie_dog_*`, ~60 `viewmodel_zombie_*`, 16 `zombie_exfil_*`,
  20 `zombie_celebration_p*` and `p_zombie_perkacola_drink`.

### 4.3 What landed, server side

Native (`bin/home/codol_rawfiles/zm/**` + the species row):

* `zm/aitype/enemy_zombie_zm.gsc` — QUAKED block, `main()` (`self.type =
  "zombie"`, `self.team = "axis"`, health 150, engagement 64/128),
  `spawner()`, `precache()`.
* `zm/character/character_zm_zombie.gsc` — the four-body/four-head rotation
  from §4.1, `setModel` + `precacheModel`. (`array()` is **not** a registered
  builtin here — the gate caught it — so the lists are built element by element.)
* `zm/maps/mp/animscripts/zombie_{init,stop,move,combat,death,pain,flashed,turn,jump}.gsc`
  — the nine modules `LoadSpeciesScripts` requires. `zombie_init.gsc` carries
  `#using_animtree ("generic_human");`, which is the **only** thing that
  registers that tree in the server registry (`maps/mp/_dogs.gsc:97` plays the
  identical role for `"dog"`, and its absence is exactly how the dog spawn
  failed before this morning). The other eight orient the actor and park on
  `"killanimscript"`; §5 says why they do not animate.

Because the species row's `category` is `zm`, none of this is compiled into an
mp or coop match, and the dog chain is still not compiled into a zm one.

---

## 5. Why a zombie will still T-pose, and what the real remaining work is

MEASURED: T5 does **not** have a native animation-state machine for humanoid AI.
`D:\CoD\OpenBLOPS` contains exactly one such file,
`Game/Shared/bgame/bg_dog_animations_mp.cpp` (the dog), and its only
zombie-named symbol is `Actor_Zombie_ExposedCombat_SP` in
`Game/Server/game/actor_exposed.cpp:21`, which carries no asset names.
Humanoid AI animation in T5 lives in GSC: `#using_animtree("generic_human")`
plus `%anim` references handed to `setflaggedanimknoball` / `animscripted` /
`DoNoteTracks`.

MEASURED: this server registers **none** of that surface — there is no
`"setanim"`, `"setanimknob"` or `"animscripted"` `Scr_AddMethod`/`Scr_AddFunction`
anywhere in `src/` (the only hits for `animscripted` are a string in
`cscr_memorytree.cpp` and the `VAR_ANIMATION` type in `cscr_variable.cpp`).

So the zombie row's state backend is `NULL` on purpose:

* `setanimstate()` now refuses by name for such a species
  (*"this actor species has no native animation state machine"*) instead of
  silently accepting dog state names against a `generic_human` tree;
* `CODOL_ActorRunFrame` skips the per-frame `stateApply` for it;
* everything else — allocation, sentient, team, perception, pathing, physics,
  damage, corpse conversion, the DObj and its `generic_human` tree, and the
  client's selector-4 composition tree — is live.

That is: **the actor exists, moves and can be shot; it holds its bind pose.**
This is the honest state, and it matches the "enemy zombies T-pose" symptom
already on record. Closing it is one of two workstreams, and the choice should
be deliberate:

1. **Port T5 faithfully** — add the scripted-animation builtins (`%anim`
   reference variables through `Scr_UsingTree`, `setanim`/`setanimknob`/
   `animscripted`, `DoNoteTracks` notetrack delivery) and then port T5's
   `maps/_zombiemode*` + `animscripts/*` GSC. Large, but it is the reference
   behaviour and it unlocks every humanoid actor, not just zombies.
2. **Write a native zombie clip table** shaped like `codol_dog_states.cpp`,
   binding a dozen `ai_zombie_*` names through `CODOL_FindAnimInServerTree`.
   Small (a new `src/codol/player/codol_actor_zombie_states.cpp` plugs straight
   into the row's three function pointers), but it has **no vendor source** —
   its state transitions, blends and rates would be invented, which is exactly
   what the "source from vendor GSC" rule exists to prevent.

INFERRED recommendation: (1). (2) is a legitimate stopgap only if the user wants
something visibly shambling before the builtin work lands, and should be labelled
as invented if it is taken.

---

## 6. Hand-back patch — the one file this worker does not own

Only **one** thing is missing, and it is a number: `codol_animlistMask` must
carry bit `0x08` in a zm match. It currently defaults to `2` (dog) for every
category, so a zm client registers **no** actor composition tree at all and
would compose a zombie against a NULL tree. No range widening is needed — bit
`0x08` is inside the dvar's existing `0..15` (`src/sv_main.c:3398`) and inside
`CODOL_SetServerAnimListFlags`'s `~15u` check
(`src/codol/snapshot/codol_sv_state.c:23`).

Two equivalent ways; the second is better because it cannot drift from the
table:

**(a) launcher only** — `bin/START-CODOL-SERVER.cmd`, `CODOL_ANIMLIST_MASK`
default `2` → `10` (`0x0A` = dog | zombie). Safe for every category: in mp,
`common_zombie.animlist` is absent so C1 clears bit `0x08`; in zm,
`common_dog.animlist` is absent so C1 clears bit `0x02`. The server-side mirror
(`CODOL_LoadClientAnimTrees`) skips an absent list without registering a client
tree id, so the two registries stay in step either way.

**(b) derive it from the species table** — in `src/sv_main.c`, immediately
before `CODOL_SetServerAnimListFlags` (`:5583`):

```c
/* OLD */
        if(!CODOL_SetServerAnimListFlags((unsigned)codol_animlistMask->integer)) {
/* NEW */
        {
            /* An explicit dvar still wins; 0 means "whatever this category's
             * actor species need" (codol_actor_scripts.h: mp -> 0x02 dog,
             * zm -> 0x08 zombie/generic_human). */
            unsigned animlistMask = (unsigned)codol_animlistMask->integer;
            if(!animlistMask)
                animlistMask = CODOL_ActorSpeciesAnimListMask(CODOL_ServerZoneType());
            if(!CODOL_SetServerAnimListFlags(animlistMask)) {
```

(plus the matching brace, `#include "codol/player/codol_actor_scripts.h"`, and
dropping `+set codol_animlistMask 2` from the launcher so the derivation is
reached). `CODOL_ActorSpeciesAnimListMask` was added by this task for exactly
this call.

**Also recommended, not required:** `tools/codol_script_resolve.py`'s
`DEFAULT_SEEDS` still lists only the dog preload. A zm gate now needs
`aitype/enemy_zombie_zm.gsc` and the nine `maps/mp/animscripts/zombie_*.gsc`
seeds; they were passed explicitly for the gate run in §7. Making the defaults
category-aware (dog seeds for mp, zombie seeds for zm) would stop the same
class of miss the 2026-09-20 correction was made for.

**A note for whoever adds the hellhound later:** selector 4 / bit `0x10` is
`zombie_dog`, and `0x10` *is* outside both the dvar range and the `~15u` check,
so that species — and only that species — needs those two widened to `0..31` /
`~31u`.

---

## 7. Gate and build results

Script gate, **exactly the command in the brief** (defaults + the two seeds):

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles/zm \
    --root bin/home/codol_rawfiles --seed maps/mp/gametypes/zm.gsc \
    --seed maps/mp/zm_prototype_sh.gsc --binary bin/codol_dedrun_next.exe
  builtins registered: 929
  validated against binary: bin/codol_dedrun_next.exe (0 source registrations absent from it)
  scripts in effective tree: 1180
  scripts the loader would lower: 109
  every reachable script resolves against the registered builtin table
```

Same command **plus the ten new zm actor seeds** (the set the engine will
actually preload once §6 lands):

```
  ... --seed aitype/enemy_zombie_zm.gsc
      --seed maps/mp/animscripts/zombie_{init,stop,move,combat,death,pain,flashed,turn,jump}.gsc
  scripts the loader would lower: 120
  every reachable script resolves against the registered builtin table
```

(The first run of that command failed on `unknown function: array (2 call
sites)` in `character/character_zm_zombie.gsc`; `array()` is not a registered
builtin on this server and the lists were rewritten element by element.)

mp regression, unchanged from the dog-fix baseline:

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles \
    --seed maps/mp/gametypes/war.gsc --binary bin/codol_dedrun_next.exe
  scripts the loader would lower: 108
```

Build (never a bare `make`):

```
make obj/codol/codol_actor_scripts.o obj/codol/codol_actor_lifecycle.o   -> OK
make objects                                                            -> OK, no errors
```

No new warnings from the changed regions; the three emitted are the pre-existing
ones named in §2.4. No binary was copied into `bin/`. No server, lobby or client
was started or stopped. No git write command was run.

Line endings, before and after (`tr -cd '\r' | wc -c` vs `git show HEAD:<f>`):

| file | HEAD | before | after |
|---|---|---|---|
| `src/codol/player/codol_actor_lifecycle.cpp` | 0 | 0 | 0 |
| `src/codol/player/codol_actor_scripts.cpp` | 0 | 0 | 0 |
| `src/codol/player/codol_actor_scripts.h` | 0 | 25 (all CRLF) | 107 (all CRLF) |

`.gitattributes` is `* text=lf`, so git normalises on diff and commit; the header
keeps the all-CRLF convention it had in the working tree, as the other `.h`
files in that directory do.

New files are all LF.

---

## 8. Live verification checklist

Nothing here has run live; the object files need a link and a redeploy of
`bin/codol_dedrun_next.exe`.

1. **Dog, first.** On an mp map with `developer 0`, call in the dogs killstreak.
   Expect the `CODOL_DOG_KILLSTREAK_20260920.md` §7 signature unchanged:
   `setenemymodel 'german_sheperd_dog' -> model <n>` then
   `animscript -> dog_move` / `setanimstate 'move_run'`. Any regression here is
   a species-table bug, not a zombie one.
2. **zm boots.** Load `zm_prototype_sh` **before** applying §6. Expect
   `CoDOL actor: aitype/enemy_zombie_zm or the maps/mp/animscripts/zombie_*
   animscripts did not load` **not** to appear (they do exist now), and the zm
   match to reach a playable state exactly as it does today. Watch specifically
   for the cost of `#using_animtree("generic_human")`: the server now parses a
   5,345-line tree and resolves ~1,900 xanim references during zm script load.
   INFERRED that this is a few hundred ms and that missing anims resolve to the
   default (the client does the same work in mp), but it is the one thing in
   this change that is untested and could plausibly stall or fail a zm boot.
   If it does, the declaration is a single line in `zombie_init.gsc`.
3. **Apply §6** (mask `0x0A`, or the derivation), relaunch, and confirm the
   `2482` key in the serverinfo carries it (`codol_sv_state.c:115` builds the
   string). Without this the zm client registers no actor tree at all.
4. **Spawn one.** `spawnactorspawner("actor_enemy_zombie_zm")` then
   `spawnactor`. Expect no
   `no server animtree named "generic_human" is registered for species 'zombie'`
   warning, a `c_zom_*_body` model on a zm map, and an actor that walks toward
   the player. Expect it to hold its bind pose — see §5. If `setanimstate` is
   ever called on it, it now refuses by name
   (*"this actor species has no native animation state machine"*) instead of
   playing a dog clip out of a human tree.
