# CoDOL asset-category teardown (mp -> coop / zm), 2026-09-17

Scope: `src/codol/assets/**` only. Everything else is reported as a cross-file patch in §7.
Every claim is labelled **MEASURED** (read out of code, a shipped file, a client log or a
build) or **INFERRED**.

---

## 1. Audit verdict, short form

1. **`CODOL_ReplaceRuntimeArchives(..., group 1, ...)` leaks a full second copy.** It does
   not free anything; it only unlinks. **MEASURED.**
2. **Four caches survive a group-1 replacement and can serve the old category** — weapon
   sound bindings, retired composed weapon cores, the loose-file CSV overlay cache, and the
   retired archives themselves. Several more are cleared correctly already. **MEASURED.**
3. **`CODOL_ForgetMountedMapArchives()` had zero call sites and no prototype** — dead code.
   **MEASURED.**
4. **Nothing in the startup group is mp-only.** The startup set is shared by all three
   categories; only group 1 changes. **MEASURED, three independent ways.**

---

## 2. Item 1 — what a group-1 replacement actually does

`mount_archives()` (`src/codol/assets/codol_asset_registry.c`, the `if(group)` block) walks
`archives`, unlinks every entry whose `group` matches, and pushes it onto the file-static
`retired_archives` list. Then `CODOL_RetireComposedWeapons()`. Then the new set is linked in.

**MEASURED:** nothing on that path calls `free_archive`/`CODOL_FreeLoadBlocks`/
`CODOL_CloseZone`. Before this change the *only* place `retired_archives` was drained was
`CODOL_UnmountArchives()`, whose sole call site is `src/common.c:1496` (`Com_Close`, process
exit). So every map change and every category change left one more complete resident copy of
`common_gametype_<t>` + `localized_common_gametype_<t>` + the map zone(s), **plus** every
cache built on top of them (models, materials, sounds, effects, physics maps and presets,
glass, worlds, rawfiles, string tables, xanim string handles, weapon hide tags, native
weapon cores) for the rest of the process.

Scale, **MEASURED** from the shipped `.ff` set
(`D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\client_shipRetail\chinese`):

| zone | bytes |
|---|---|
| `common_gametype_mp.ff` | 42,656,021 |
| `common_gametype_coop.ff` | 49,307,925 |
| `common_gametype_zm.ff` | 71,516,437 |
| `mp_killhouse_sh.ff` | 44,695,829 |
| `zm_zombie_training.ff` | 69,157,141 |
| `coop_training_mp_killhouse_sh.ff` | 41,861,397 |
| every `*_load.ff` and `patch_*.ff` sampled | 24,853 (stub) |

The comment at the old `codol_asset_commands.c:281-285` was accurate: "retired, not freed".

**Reachability of a retired archive (MEASURED).** Grepping `retired_archives` in
`codol_asset_registry.c` gives exactly four uses: the declaration, the retire push, the free
loop, and `CODOL_FindNativeWeaponQueryCore`, which walks `retired_archives` as generation 1
and matches by `struct WeaponDef *` **pointer**. That is deliberate — it is what keeps a
live composed weapon answerable after a remount — and it is also the one reason the retired
set cannot simply be freed without sequencing. All name-keyed lookups
(`CODOL_LoadEngineRawFile`, `CODOL_LoadEngineStringTable`, `find_dependency_definition`,
`CODOL_LoadMountedCollisionModels`, …) iterate `archives` only, so a retired archive is not
reachable *by name*.

> The coordinator asked specifically whether `CODOL_LoadEngineStringTable` /
> `CODOL_LoadEngineRawFile` can return a retired group-1 entry. **MEASURED: no.** Both
> start `for (archive = archives; ...)`, and a retired archive is no longer on `archives`.
> Their per-archive `tables`/`rawfiles` caches are owned by the `archive_t` and die with it.

---

## 3. Item 2 — caches holding pointers into the retired archives

Confirmed by reading the code and by a dedicated cross-tree sweep.

### 3.1 Survived a group-1 replacement (the bugs)

| cache | file | key | previously cleared by |
|---|---|---|---|
| `weapon_sounds` | `codol_sound_native.c:238` | weapon **name** only; holds `snd_alias_list_t*` into an `archive_t`'s sound cache | `CODOL_ResetNativeWeaponSounds`, called only from `CODOL_UnmountArchives` |
| `retired_composed` | `codol_weapon_compose.c` | `find_by_definition` walks live **and** retired lists | `CODOL_ResetComposedWeapons`, only from `CODOL_UnmountArchives` |
| `reference_tables` | `codol_asset_registry.c:41` | (script root, name); never generation | inline loop in `CODOL_UnmountArchives` |
| `retired_archives` | `codol_asset_registry.c:215` | — | `CODOL_UnmountArchives` |

The `reference_tables` one matters for a *category* switch specifically: `src/cscr_parser.cpp:584`
passes `CODOL_ServerZoneType()` into the loose-file overlay lookup, so the script root is
chosen by category. A resident entry from the mp root would keep answering. **MEASURED.**

### 3.2 Already correct — do not touch

* Model animations: `CODOL_ResetModelAnimations()` is called from `SV_SpawnServer` on every
  spawn, after the mount. **MEASURED.**
* Script profiles, server configstrings, the server weapon registry, server asset names and
  the match-data schema: all reset from `SV_ClearServer`, which `SV_SpawnServer` calls
  before the mount. **MEASURED.**
* The compose market index and its model cache: `reset_lookup_indexes()` runs inside
  `CODOL_RetireComposedWeapons()`, i.e. on **every** mount. **MEASURED.**
* `installed_clip`/`installed_source` (`codol_sv_xmodel.c`): released by
  `CODOL_ShutdownEngineClipMap()` from `CM_Shutdown` (`src/cm_load.c:205`), which
  `Com_Restart()` calls inside `SV_SpawnServer` before the mount. **MEASURED.**
* `codol_dual_wield_*` (`codol_weapon_state.c`): invalidated both by
  `CODOL_SetWeaponDualWieldResolver` (re-installed every spawn) and by
  `CODOL_ResetWeaponStates` from `SV_ClearServer`. **MEASURED.**
* All `*_native.c` converters in `src/codol/assets` are stateless apart from `static const`
  tables and failure-line ints. **MEASURED.**

### 3.3 Cleared by nothing at all — NOT in my ownership, see §7

These were safe only because retired archives were never freed. Once they are, a recycled
heap address can make a pointer-identity key match the wrong weapon:

* `codol_sway_defs[]` — `src/codol/player/codol_sway_phase.c:148`. Keyed by weapon index
  **and `const struct WeaponDef *` identity**. `CODOL_SwayPhaseReset(int)` only clears the
  per-client phase, not this table, and has **zero call sites**. **MEASURED.**
* `cached_def[]`/`cached_scope[]` — `src/codol/player/codol_pmove_c1_breath.c:98-99`. Same
  pattern, no reset anywhere. **MEASURED.**

Values in both are copied scalars, so the failure mode is a wrong sway curve or a wrong
scope-overlay flag for one weapon, **not** a dangling dereference. **INFERRED** from the
struct contents. It is still a regression risk this change introduces and §7.1 is the fix.

Memory-safe but permanently stale (strings are copied), also outside my area:

* `copies` shock-rawfile list, `src/db_load.cpp:3595` — keyed by name only, "owned for the
  process lifetime". A category with different `shock/*.shock` keeps serving the first one.
* `channel_names`/`channel_count`, `src/codol/assets/codol_snd_channels.c:24-25` — latched
  by `if (channel_count >= 0) return;`. Mine by directory, but the latch is also how the
  hardcoded fallback gets pinned if the first call precedes the mount; changing it is a
  behaviour change outside this task and is listed in §7.3.

Engine globals that retain CODOL-owned pointers (**MEASURED**):

* `bg_weaponDefs[]` — holds `&composed_entry_t::core.definition` / `&native_weapon_cache_t::
  core.definition`. Guarded, see §5.
* `comWorld` (`src/db_load.cpp:3569`) — shallow copy of an `archive_t`-owned
  `common_world_cache_t`. Safe here because `Com_Restart()` runs `Com_ShutdownWorld()`
  before the mount and `Com_LoadWorld()` re-reads from the new archives after it, both in
  the same `SV_SpawnServer`. **INFERRED** from that ordering.
* `cached_models[512]` (asm BSS, written at `codol_player_appearance.c:126`) — `XModel*`
  from `archive_t::models`, cleared only by the retained asm game-init path. Listed in §7.2.
* `cm` — safe, see §3.2.

---

## 4. Item 3 — `CODOL_ForgetMountedMapArchives()`

**MEASURED, before this change:** grepping the whole tree for the symbol returned exactly
one line, its own definition. It had no prototype in `codol_assets.h` or anywhere else, and
no caller. The reuse fast path it exists to invalidate could therefore never be invalidated.
It is now declared in `codol_assets.h` and called from `CODOL_UnloadCategoryAssets`.

---

## 5. Item 4 — is anything in the startup group mp-only?

**No.** The startup group is category-agnostic and needs no change for coop or zm. Three
independent measurements:

1. **The shipped file set.** `client_shipRetail/chinese` contains `common_mp.ff` and
   `code_post_gfx_mp.ff` and **no** `common_coop.ff`, `common_zm.ff`, `code_post_gfx_zm.ff`
   or `code_post_gfx_coop.ff`. The only per-category zones are
   `common_gametype_{mp,coop,zm}.ff` plus their `localized_` and `patch_` variants.
2. **A real zm client load, MEASURED**, `main/console_mp-006.log:80796-80853`:
   ```
   zm_zombie_training_load
   patch_common_gametype_zm   common_gametype_zm
   patch_localized_common_gametype_zm   localized_common_gametype_zm
   patch_zm_zombie_training   zm_zombie_training
   ```
   No `common_zm`, no `code_post_gfx_zm`. The mp startup zones stayed mounted from boot.
   The same shape appears for `zm_prototype_sh` in `console_mp-003.log:35451-35486`.
3. **The per-category const tables live in the startup group.** MEASURED,
   `docs/zone_assets/ALL_stringtable.txt:166-168`:
   ```
   mp/constconfigstrings_coop.csv   code_post_gfx_mp
   mp/constconfigstrings_mp.csv     code_post_gfx_mp
   mp/constconfigstrings_zm.csv     code_post_gfx_mp
   ```
   So `CODOL_LoadEngineStringTable("mp/constConfigStrings_zm.csv", ...)` resolves out of
   group 0 and is unaffected by the group-1 swap — which is exactly why the teardown must
   **not** touch group 0.

`CODOL_RetireRuntimeArchiveGroup(0)` is refused for this reason.

---

## 6. The coop map-name defect and what changed

### 6.1 The defect

`CODOL_ZoneTypeForMapName()` returned `"mp"` for anything that was not `zm*`/`coop*`, and
the caller refused to mount when that disagreed with `codol_zoneType`. **MEASURED** from the
shipped data: a coop match's LEVEL zone is spelled `mp_killhouse_sh`, so the derived answer
was `"mp"`, the carrier said `"coop"`, and every coop match was refused at the first step.
The same guard is what turned a `zm_prototype_sh` spawn under category `mp` into
`Com_Error(ERR_DROP)` and a dead server (`bin/home/main/qconsole.prev-5f1c9db8.log:9303,
9367-9373`, reported by the coordinator).

### 6.2 New rule

`CODOL_ZoneTypeForMap()` now returns the category a name **proves**, or `NULL`:

* `zm*` proves `"zm"`.
* `coop*` proves `"coop"`.
* anything else (`mp_*`) proves **nothing** — it is a legitimate mp level *and* every coop
  level.

`CODOL_LoadMapArchivesEx` refuses only a real contradiction: a proven category that differs
from the carrier, or carrier `"zm"` with a map that is not `zm*` (every shipped zm level is
`zm_*`). `mp_killhouse_sh` + `coop` now mounts. The error text names the carrier and tells
the operator to fix it rather than implying the map is wrong.

### 6.3 Does a coop mount need the playlist zone as well as the level zone?

**YES — both. MEASURED, two ways.**

* The client's own telemetry, `CODOL/re/alpha0022/dw-capture.log:2232`:
  `ClientLoadTime ... | 2005 common_mp | 1324 common_gametype_coop | 1720
  coop_training_mp_killhouse_sh | 4956 mp_killhouse_sh | NONE`. Four zones.
* `coop_training_mp_killhouse_sh.ff` is 41,861,397 bytes and
  `docs/zone_assets/ALL_weapon.txt` credits it with 44 weapon assets of its own
  (`common_gametype_coop` has 78). It is mission content, not the 24,853-byte loadscreen
  stub its `_load` sibling is.
* Corroborated by the coordinator from C1 `0x004CD0FE`: on a `coop_` map string the client
  loads `patch_<full>` + `<full>`, then `strchr(map+5,'_')+1` as the base and
  `patch_<base>` + `<base>`.

The implementation accepts **either** spelling, so the still-open question of which spelling
the gamestate should carry cannot break the mount:

* `map` is the level spelling and `session_map` (from `codol_sessionMap`) is the playlist
  spelling — mounts both.
* `map` is the playlist spelling and `session_map` is empty — the retained `coop_` branch
  strips it to the level spelling and mounts both.
* mp / zm — the two are identical, `roots` stays 3, nothing changes.

Mount order is unchanged from the previous `roots=4` code: `common_gametype_<t>`,
`localized_common_gametype_<t>`, level, session, each followed by its `patch_` when the file
exists. Lookup walks `archives` head-first, i.e. last path first, so precedence is
session > level > localized > gametype, with each `patch_` ahead of its base. **Open, not
changed here:** the client's own load order is the reverse (gametype first), and IW4 DB
semantics are first-wins, so C1's effective precedence may be gametype > session > level.
Flipping ours is a separate, testable change; it only matters for a name present in two of
the four roots.

---

## 7. Cross-file patches — I do not own these files

### 7.1 REQUIRED before this ships: two pointer-keyed caches with no invalidation

`CODOL_UnloadCategoryAssets` now frees composed weapon cores. Two caches key on a raw
`const struct WeaponDef *` and are cleared by nothing, so a recycled address can match the
wrong weapon. Give each a reset and call it from the teardown. `codol_weapon_state.c:1011-1013`
already documents this exact hazard and defends against it; these two missed it.

`src/codol/player/codol_sway_phase.c` — add:

```c
/* Composed definitions are freed on an asset-category change, so a recycled
 * address could make slot->def == def match a different weapon. */
void CODOL_SwayPhaseResetDefs(void)
{
    memset(codol_sway_defs, 0, sizeof(codol_sway_defs));
}
```
and declare it in `codol_sway_phase.h`.

`src/codol/player/codol_pmove_c1_breath.c` — lift the two function-local statics in
`weapon_has_scope_overlay` to file scope and add:

```c
void CODOL_ResetBreathScopeCache(void)
{
    memset(cached_def, 0, sizeof(cached_def));
    memset(cached_scope, 0, sizeof(cached_scope));
}
```
plus a declaration in the matching header.

I will then add both calls to `CODOL_UnloadCategoryAssets`. Until they exist, the
category-change path can serve one stale sway curve / scope flag per colliding address.
Not a crash. **INFERRED** severity; the mechanism is **MEASURED**.

### 7.2 Recommended: `cached_models[]`

`cached_models[512]` (asm BSS, written at `src/codol/player/codol_player_appearance.c:126`)
holds `XModel*` owned by an `archive_t`. It is not in the teardown's borrower list. It is
probably safe — `SV_ShutdownGameProgs` and `Com_Restart` both run before the mount — but it
should be zeroed explicitly from `CODOL_ResetClientCharacters` or the teardown. Owner of
`codol_player_appearance.c` should confirm.

### 7.3 Optional: two permanently-latched caches

* `src/db_load.cpp:3595` `copies` — the shock-rawfile translation list, keyed by name for
  the process lifetime. Add a free entry point and call it from the teardown.
* `src/codol/assets/codol_snd_channels.c` `channel_count` latch — this file *is* mine, but
  unlatching it changes when `soundaliases/channels.def` is read relative to the retained
  `BG_LoadShellShockDvars` path, which is a behaviour change beyond this task. Left alone
  deliberately; flagged here so it is not forgotten.

### 7.4 Already handled by the `sv_main.c` worker

Nothing further needed: the category is taken from `fs_game` -> `codol_zoneType`, the
playlist spelling arrives on `codol_sessionMap`, and `SV_SpawnServer` calls the teardown
hook before the mount. The two hooks are implemented and registered, §8.

---

## 8. What was implemented

All in `src/codol/assets/`.

**`codol_asset_registry.c`**

* `free_archive(archive_t *)` — the per-archive release body, factored out of
  `CODOL_UnmountArchives` so one generation can be released without touching group 0.
* `CODOL_ReleaseRetiredArchives(void)` -> `unsigned` — drains `retired_archives` through
  `free_archive`. Documents its precondition: every borrower listed on
  `CODOL_UnloadCategoryAssets` must be reset first.
* `CODOL_RetireRuntimeArchiveGroup(unsigned group)` -> `unsigned` — moves a live group aside
  **without** mounting a replacement, so the outgoing category can be unloaded *before* the
  next one is opened rather than both being resident. Refuses group 0. Runs
  `CODOL_RetireComposedWeapons()` when it retired anything.
* `CODOL_ResetReferenceStringTables(void)` — the loose-file CSV overlay cache, split out of
  `CODOL_UnmountArchives`.
* `CODOL_UnmountArchives` rewritten on top of those four; behaviour unchanged.

**`codol_asset_commands.c`**

* `CODOL_UnloadCategoryAssets(const char *from_type)` — the named entry point. Order:
  `CODOL_ResetNativeWeaponSounds` -> `CODOL_ResetModelAnimations` ->
  `CODOL_ResetScriptProfiles` -> `CODOL_ResetReferenceStringTables` ->
  `CODOL_ForgetMountedMapArchives` -> guard -> `CODOL_ResetComposedWeapons` ->
  `CODOL_ReleaseRetiredArchives` -> `CODOL_HeapCheck`. Borrowers first, providers last.
* The guard: it reads `bg_lastParsedWeaponIndex` and, if the native weapon table is not
  empty, warns and keeps the retired archives resident instead of freeing definitions the
  engine still holds. **MEASURED** that this is normally 0 at mount time: `SV_SpawnServer`
  calls `SV_ShutdownGameProgs` first, `G_ShutdownGame` calls `Com_FreeWeaponInfoMemory`
  (`src/asmsource/_g_main_mp.asm:1555`), and `BG_ShutdownWeaponDefFiles` ends by storing 0
  into `bg_lastParsedWeaponIndex` (`_bg_weapons.asm`, `BG_ShutdownWeaponDefFiles_20`).
* `CODOL_UnloadGametypeAssets(prev, next)` — the `SV_SetCoDOLCategoryTeardown` entry point.
  Retires group 1, then calls `CODOL_UnloadCategoryAssets(prev)`.
* `CODOL_SetSessionMapName(const char *)` / `CODOL_SessionMapName(void)` — the
  `SV_SetCoDOLSessionMapInstaller` entry point. Validates the string as a zone basename
  (`[a-z0-9_]`, bounded) and stores it; `""`/NULL clears it.
* Both installed from `CODOL_InitAssetCommands()` via `SV_SetCoDOLCategoryTeardown` /
  `SV_SetCoDOLSessionMapInstaller`, matching the existing `CODOL_SetWeapon*Resolver` pattern.
* `CODOL_ZoneTypeForMap(const char *)` — replaces the old static `CODOL_ZoneTypeForMapName`;
  returns the proven category or NULL. Exported so `sv_main` can auto-select instead of
  reaching `ERR_DROP`.
* `CODOL_LoadMapArchivesEx(map, session_map, zone_type)` — the real mount. Accepts either
  spelling, mounts level + session for coop, keeps the reuse fast path (now keyed on
  level + session + category).
* `CODOL_LoadMapArchives(map, zone_type)` unchanged as a wrapper that supplies the installed
  session name, so `sv_main` needs no signature change.
* Belt-and-braces: if a caller does **not** use the teardown hook,
  `CODOL_LoadMapArchivesEx` still detects the category change itself and runs
  `CODOL_UnloadCategoryAssets` after the mount. When the hook did run, the hook's
  `CODOL_ForgetMountedMapArchives()` has already cleared `mounted_zone`, so the post-mount
  path sees no change and does nothing.

**Cost when the category is unchanged: zero.** The reuse fast path is untouched, and a
same-category map change runs exactly the code it ran before. That also means the
same-category map-change leak in §2 is **still present** — deliberately, per the task's
"no-op cost when the category is unchanged". Making it disappear is one line: drop the
`if(category_changed)` guard on the post-mount `CODOL_UnloadCategoryAssets` call. It should
not be taken until §7.1 lands.

---

## 9. Build

**MEASURED.** msys2 `make` (`C:\msys64\usr\bin\make.exe`), mingw32 gcc 14.1.0,
`TMP`/`TEMP` redirected to `obj/_tmp` because gcc's default `C:\WINDOWS` temp is unwritable
here. Object-file targets only — a bare `make` links and writes `bin/codol_dedrun.exe`.

* `make obj/codol/codol_asset_commands.o obj/codol/codol_asset_registry.o
  obj/codol/sv_main.o obj/codol/common.o` — all four compile. The only warnings are
  pre-existing ones in `sv_main.c` (`mapname_loadff`, `expanded`, `zoneinfo` unused).
* `make` over every object in `src/codol/assets/` — exit 0, no errors, no new warnings from
  the two files changed here.

No server was started or stopped, no binary was copied over `bin/codol_dedrun.exe` or
`bin/codol_dedrun_next.exe`, and no git command was run.

**Incident to note.** Before the object-only rule reached me I ran one bare `make`. The link
step failed (pre-existing undefined references from `pluginexports.asm` and
`_gxx_personality_v0` from `codol_script_lower.o`, unrelated to these changes — this msys2
mingw32 toolchain is not the `i686-w64-mingw32` cross-build the project's own build logs
show under `obj/codol-win32/`). `bin/codol_dedrun.exe` does not exist now; I cannot prove
whether it existed beforehand, and `ld` removes its output on failure, so it may have been
removed by that run. The live server runs `bin/codol_dedrun_next.exe`
(`bin/START-CODOL-SERVER.cmd:109`), which is untouched (Sep 17 16:02), and `bin/rollback/`
holds several prior builds. Flagging it rather than guessing.
