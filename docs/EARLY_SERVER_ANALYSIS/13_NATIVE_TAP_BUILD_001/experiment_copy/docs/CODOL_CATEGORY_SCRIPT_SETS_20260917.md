# Per-category script sets: the coop contract, the closure audit, and what landed

2026-09-17. Script half of the `fs_game` / category-handoff work item: *"unload
the mp zone and scripts for the appropriate coop or zm ones depending on
fs_game"*. Zones are another worker's half; this document is **scripts only**.

## Evidence class, up front

- **Read out of the shipped data (MEASURED).** Every coop fact in §2 was
  extracted offline from `D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\client_shipRetail\chinese\*.ff`
  with `alpha0022/zone_assets.py` (the measured RSA/AES/zlib container reader),
  plus the asset index already in `docs/zone_assets/`. Nothing about coop
  gametype or level names was invented.
- **Computed (MEASURED).** Every closure figure in §1 comes from
  `python tools/codol_script_resolve.py`, which walks `#include` and
  `file\path::function` references from the engine's entry points through the
  loader's own root precedence.
- **Written, NOT COMPILED BY THE VM.** The 21 GSC files in §3. They pass the
  static resolver and the `--binary bin/codol_dedrun_next.exe` builtin gate; no
  server, lobby or client was started, and no process was killed.
- **INFERRED** is marked inline wherever it appears.

---

## 0. How the mechanism resolves today (verified, not assumed)

`Scr_ReadFile` (`src/cscr_parser.cpp`) calls
`CODOL_ReadScriptSourceWithNativeOverlayForZone(codol_scriptPath,
codol_scriptOverlay, codol_scriptNativeOverlay, CODOL_ServerZoneType(),
extFilename, ...)`. `src/codol/script/codol_script_source.c:82-88` probes, in
order:

```
<nativeOverlay>/<zoneType>/<name>      only when zoneType is non-empty lowercase ASCII
<nativeOverlay>/<name>
<overlay>/<name>
<base>/mp/<name>
<base>/<name>
```

`bin/START-CODOL-SERVER.cmd:118-120` points **all three** dvars at the single
collated root `bin\home\codol_rawfiles`, so in practice there are exactly two
layers: `bin\home\codol_rawfiles\<zoneType>\` and `bin\home\codol_rawfiles\`.

**The category layer is live by the time scripts load (MEASURED ordering).**
`CODOL_SetServerMapIdentity(mapname, codol_zoneType->string)` is called at
`src/sv_main.c:5560`; `SV_InitGameProgs` at `src/sv_main.c:5643` is what
eventually reaches `GScr_LoadScripts` (`src/scr_vm_main.c:1415`) and
`GScr_LoadGameTypeScript` (`:1436`). The identity is therefore latched ~80 lines
of `SV_SpawnServer` before any `Scr_ReadFile` call, so `CODOL_ServerZoneType()`
is never NULL for a real map load.

`codol_gametype_policy` (`src/scr_vm_main.c`) is the other half:

| category | forced script | fallback | behaviour when the script is missing |
|---|---|---|---|
| `mp`   | — (`combat`/`tdm` → `war`) | `dm`   | falls back to `dm` |
| `coop` | — (honours `g_gametype`)    | `coop` | **`Com_Error(ERR_DROP)`** — fallback == what was tried |
| `zm`   | `zm`                       | `zm`   | **`Com_Error(ERR_DROP)`** |

---

## 1. Closure audit per category

Entry points walked: `maps/mp/gametypes/_callbacksetup`, the gametype script
named by `g_gametype`, the level script `maps/mp/<mapname>`,
`codescripts/delete`, `codescripts/struct`.

### 1.1 mp — 102 scripts, unchanged by this pass

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles \
  --seed maps/mp/gametypes/_callbacksetup.gsc --seed maps/mp/gametypes/war.gsc \
  --seed maps/mp/mp_killhouse_sh.gsc --seed codescripts/delete.gsc --seed codescripts/struct.gsc
```
→ `scripts the loader would lower: 100` (102 distinct `.gsc` paths counting the
two seed spellings of the fx module). The list was captured before and after
this pass's edits and **diffs empty**. No file outside `coop/` and `zm/` was
touched.

**Pre-existing defect found while auditing, NOT fixed (not my files):**

```
UNRESOLVED NAMES (each one is a fatal map-load compile error)
  maps/mp/mp_killhouse_sh_fx.gsc
    no such function: common_scripts/utility.gsc::shouldrunserversideeffects
```

`shouldRunServerSideEffects()` is **called by 15** `maps/mp/*_fx.gsc` files in
`bin/home/codol_rawfiles` and **defined by none** (MEASURED: `grep -rn` over the
whole tree finds only call sites). Whether that is actually fatal at runtime is
INFERRED from the tool's contract — the user's live mp matches do run on
killhouse, so either the VM tolerates an unresolved namespaced call or the fx
module is not reached. Either way it is worth a look, and it is the reason none
of the new coop/zm level scripts call an `*_fx::main()`.

**2026-09-28 correction:** The call is inside `/ # ... # /` developer-comment
syntax (written without spaces in the GSC). The server registers
`developer_script` as false by default, and passes that value to `Scr_Settings`.
The resolver previously scanned the inactive block and misreported a production
map-load error. The production Killhouse/war gate now passes; the explicit
`--developer-script` gate still reports the missing function. This is a
developer-mode gap, not evidence that normal Killhouse matches fail to load.

### 1.2 zm — 6 scripts, already clean; 2 level scripts were missing

Before this pass `zm/` held four files and the closure was 6 scripts with zero
multiplayer modules — the design is sound. The gap was **per-map**: only
`zm_zombie_training.gsc` existed, so `zm_prototype_sh` and `zm_asylum_sh` (both
of which ship zones: `zm_prototype_sh.ff`, `zm_asylum_sh.ff`, plus `_load`
siblings) got `no level script for <map>` and no vision at all. Per the
"fix maps, don't pin" rule those are the work item, so both were written (§3.2).

Closure after, for all three maps: **6 scripts**, all resolving.

```
codescripts/delete.gsc                    bin/home/codol_rawfiles
codescripts/struct.gsc                    bin/home/codol_rawfiles
maps/mp/gametypes/_callbacksetup.gsc      bin/home/codol_rawfiles/zm
maps/mp/gametypes/_zombiemode.gsc         bin/home/codol_rawfiles/zm
maps/mp/gametypes/zm.gsc                  bin/home/codol_rawfiles/zm
maps/mp/<zm map>.gsc                      bin/home/codol_rawfiles/zm
```

### 1.3 coop — the category did not exist; it would have compiled 100 multiplayer scripts, then dropped

`bin\home\codol_rawfiles\coop\` **did not exist at all**. There is no
`maps/mp/gametypes/coop.gsc` anywhere in the tree (only `coop.txt`, the
localized name). So, MEASURED:

1. `GScr_LoadGameTypeScript` looks for `maps/mp/gametypes/coop`, misses, finds
   the coop fallback is `coop` itself, and raises
   `Com_Error(ERR_DROP, "CoDOL coop zone type has no gametype script ...")`.
   **A coop match does not start at all today.**
2. Everything reached before/around that point resolves to multiplayer files,
   because the `coop/` root did not exist to shadow them. Walking the same
   entry points without the gametype seed gives **100 multiplayer scripts a coop
   match would wrongly compile**. Named explicitly, these are the mp-only files
   a coop or zm match must never see:

   - `maps/mp/gametypes/_callbacksetup.gsc` — the multiplayer one. Its
     `SetDefaultCallbacks` names `_gamelogic`, `_playerlogic`, `_damage` and
     `_hostmigration` as function pointers, and **that reference alone drags in
     the other 96 files** (a GSC `file::function` reference is a compile-time
     dependency).
   - The whole gametype chain: `_gamelogic`, `_globallogic`, `_playerlogic`,
     `_damage`, `_class`, `_rank`, `_missions`, `_persistence`, `_spawnlogic`,
     `_teams`, `_scoreboard`, `_killcam`, `_spectating`, `_deathicons`,
     `_friendicons`, `_healthoverlay`, `_hud`, `_hud_message`, `_hud_util`,
     `_hardpoints`, `_gameobjects`, `_gamescore`, `_menus`, `_objpoints`,
     `_playercards`, `_quickmessages`, `_serversettings`, `_shellshock`,
     `_tweakables`, `_weapons`, `_damagefeedback`, `_battlechatter_mp`,
     `_clientids`, `_dev`, `_codol_bots`, `_globalentities`, `_hostmigration`.
   - **All 16 killstreak modules** (`maps/mp/killstreaks/_ac130`, `_airdrop`,
     `_airstrike`, `_autosentry`, `_emp`, `_harrier`, `_helicopter`,
     `_killstreaks`, `_mortar`, `_nuke`, `_rcbomb` ×4, `_remotemissile`,
     `_sr71`, `_tank`, `_uav`) — these are exactly the precaches that made C1
     report `vehicle_mig29_desert` / `projectile_cbu97_clusterbomb` *"not in any
     mounted zone"* under zm, because those xmodels live in
     `common_gametype_mp` and a coop match mounts `common_gametype_coop`.
   - `maps/mp/perks/_perks`, `_perkfunctions`; the five `maps/mp/equipment/*`
     modules; `maps/mp/_load` and the ten subsystems it threads
     (`_minefields`, `_radiation`, `_shutter`, `_destructables`, `_dogs`,
     `_javelin`, `_stinger`, `_empgrenade`, `_flashgrenades`,
     `_entityheadicons`), plus `common_scripts/_elevator`,
     `_dynamic_world`, `_destructible`, `_pipes`, `_fx`, `_painter`,
     `_artcommon`, `_createfx`, `_createfxmenu` and the 3856-line
     `common_scripts/utility.gsc`.
   - `maps/mp/mp_killhouse_sh.gsc` — the **multiplayer level script**, with its
     `maps\mp\_load::main()` call, minimap setup and `game["attackers"]` /
     `game["defenders"]` team assignment, none of which a non-team-based Spec
     Ops match wants.

   `common_scripts/utility.gsc` in that list is the `isSP()` landmine carrier:
   `isSP()` is `!string_starts_with( getdvar("mapname"), "mp_" )`, which for coop
   is **TRUE under the playlist spelling** (`coop_training_mp_killhouse_sh`) and
   **FALSE under the base spelling** (`mp_killhouse_sh`) — the same match
   behaving differently depending on which of its two names the lobby sent.

Closure after this pass, for every one of the 14 level-script spellings:
**6 scripts**, zero multiplayer modules, every name resolving.

---

## 2. The coop contract, extracted from the shipped data

Everything in this section is MEASURED out of the `.ff` files, with the exact
asset it came from.

### 2.1 The gametype script name is `coop`

`mp_playlists.ff` → rawfile `mp_playlists.info`, lines 380-384, verbatim:

```
// ****Spec Ops****
gametype coop
name english "Spec Ops"
name chinese "<special operations>"
script coop
```

**No `teambased` line**, unlike the `tdm`, `dom`, `ctf`, `kc` and `inf` blocks
immediately around it. So coop is a **non-team-based gametype whose script name
is `coop`** — the identical shape to `gametype zm / script zm` at lines 98-101.

Corroborating, all MEASURED:

- `code_post_gfx_mp.ff` → `maps/mp/gametypes/_gametypes.txt` lists 19 entries
  and `coop` is one of them (`dm dom sd sab war koth oneflag arena dd vip ctf
  gtnw` **`coop`** `combat clanwars zm conf infect hp`).
- `code_post_gfx_mp.ff` → `maps/mp/gametypes/coop.txt` is one line:
  `"MPUI_COOPERATIVE"` — the same localized-name form as `zm.txt`'s
  `"MPUI_ZOMBIE"` and `war.txt`'s `"MPUI_WAR"`.
- `common_gametype_coop.ff` → `mp/gametypescptable.csv` (28 cols × 15 rows)
  carries a `coop` row with `matchreward_scale_win 0.5`.
- `code_post_gfx_mp.ff` → `mp/basemaps.arena`: **every** `coop_*` entry carries
  `gametype "coop"`, `allieschar "us_army"`, `axischar "opforce_composite"`
  (e.g. `coop_training_mp_killhouse`, `coop_defense_mp_crash_tropical`,
  `coop_chopper_mp_suburbs`, `coop_suspension_mp_bridge`,
  `coop_takeover_mp_estate`, `coop_zac130_mp_derail`).
- `mp_playlists.info` playlist 27 (`On-boarding`, `tutorial`) rotates exactly
  two maps: `coop_prolog_mp_crash_intro,coop,1` and
  `coop_training_mp_killhouse_sh,coop,1`.

**This matches the native fallback table**, which already says
`{ "coop", NULL, "coop" }` — the engine has been waiting for
`maps/mp/gametypes/coop.gsc` to exist.

### 2.2 The level-script module names: the playlist spelling is canonical

This was the load-bearing question. A coop match has two names for the same
level (`coop_training_mp_killhouse_sh` and `mp_killhouse_sh`), C1 at `0x004CD0FE`
mounts both, and `GScr_LoadScripts` asks for `maps/mp/<mapname>` — so which one
`mapname` is decides the module name.

**MEASURED from the zones, four independent signals, all pointing at the
playlist spelling:**

| signal | mp control | zm control | coop |
|---|---|---|---|
| fx rawfile | `maps/mp/mp_killhouse_sh_fx.gsc` | `maps/mp/zm_zombie_training_fx.gsc` | `maps/mp/coop_training_mp_killhouse_sh_fx.gsc` |
| createfx rawfile | `maps/createfx/mp_killhouse_sh_fx.gsc` | `maps/createfx/zm_zombie_training_fx.gsc` | `maps/createfx/coop_training_mp_killhouse_sh_fx.gsc` |
| animlist | `animlists/mp_killhouse_sh.animlist` | `animlists/zm_zombie_training.animlist` | `animlists/coop_training_mp_killhouse_sh.animlist` |
| vision | `vision/mp_killhouse_sh.vision` | (absent for this one map) | `vision/coop_training_mp_killhouse_sh.vision` |

In the two controls the `<mapname>` in `maps/mp/<mapname>_fx.gsc` is
unambiguous and equals the level-script module name. The coop zones use the
**full playlist name** in that same slot, for all nine. The coop addon entities
are likewise named `maps/mp/<playlist>.mapents`.

**So the canonical coop level script is `maps/mp/coop_training_mp_killhouse_sh.gsc`
and its eight siblings.** Because the question of which spelling the server
announces is still open elsewhere, the base spellings are shipped too and do the
identical work (§3.1) — the coop root is correct either way, at the cost of five
extra three-line files.

The nine playlist zones and their base level zones (base = strip at the first
`_mp_`, which is C1's own rule at `0x004CD0FE`: `strchr(map+5,'_')+1`):

| playlist zone | base level zone | own vision rawfile? |
|---|---|---|
| `coop_defense_mp_crash_tropical` | `mp_crash_tropical` | yes |
| `coop_prolog_mp_crash_intro` | `mp_crash_intro` | yes |
| `coop_spec1_mp_killhouse_sh` | `mp_killhouse_sh` | yes |
| `coop_spec_mp_crash_tropical` | `mp_crash_tropical` | yes |
| `coop_spec_mp_estate_tropical` | `mp_estate_tropical` | yes |
| `coop_spec_mp_fav_tropical` | `mp_fav_tropical` | **NO — ships no vision at all** |
| `coop_take_mp_estate_tropical` | `mp_estate_tropical` | **NO — only `vision/slomo_breach.vision`** |
| `coop_take_mp_fav_tropical` | `mp_fav_tropical` | yes |
| `coop_training_mp_killhouse_sh` | `mp_killhouse_sh` | yes |

All five base zones (`mp_crash_intro.ff`, `mp_crash_tropical.ff`,
`mp_estate_tropical.ff`, `mp_fav_tropical.ff`, `mp_killhouse_sh.ff`) exist and
each ships its own `sun/` and `vision/`. That is why the two coop zones without
a vision of their own name their base map's instead.

### 2.3 The coop zones ship no world assets — they are addons

MEASURED: none of the nine carries `col_map_mp`, `com_map`, `game_map_mp`,
`gfx_map` or `map_ents`. Each carries exactly one **`addon_map_ents`**,
`maps/mp/<playlist>.mapents`. The geometry is the base `mp_*` zone's. This is
the mechanical reason coop and mp share level zones and the category root is the
only thing separating their script sets.

**Consequence the coop scripts have to live with (MEASURED):** this server has
no `addon_map_ents` loader. Its asset-name table
(`src/asmsource/_db_assetnames.asm`, `g_assetNames`) is the IW3 33-entry set
ending at `stringtable`; IW4's type 42 is not in it, and `grep -rni
"mapents|map_ents" src/` finds only those assembler symbols for the base
`map_ents` type. So **the entities a coop match sees today are the base
`mp_<map>` zone's multiplayer entities**, not the Spec Ops ones.

### 2.4 What the coop entities actually are

Decoded from seven of the nine addon MapEnts (the `coop_prolog` and
`coop_spec1` blobs did not extract by name this pass — noted as incomplete):

Player starts, MEASURED per zone:

```
info_player_start_so         coop_training_mp_killhouse_sh (2), coop_defense_mp_crash_tropical (6),
                             coop_spec_mp_crash_tropical (2),  coop_take_mp_estate_tropical (2)
info_player_start_pmc        coop_spec_mp_estate_tropical (2), coop_spec_mp_fav_tropical (2),
                             coop_take_mp_fav_tropical (4)
info_player_start_pmcDefend  coop_spec_mp_crash_tropical (2)
```

Those are IW4's **Spec Ops** classnames exactly — `maps/_specialops_code.gsc:21`
tries `info_player_start_so` then `info_player_start`, and `:53-58` uses
`info_player_start_pmcDefend` for defend missions and `info_player_start_pmc`
otherwise. Ported in §3.1.

The rest of the content is IW4 singleplayer: `actor_enemy_favela_*_so`,
`actor_enemy_desert_elite_*_so`, `actor_enemy_dog_so`,
`actor_enemy_juggernaut_russian_so`, `actor_ally_codo_tf_*_so`,
`actor_ally_hero_{price,soap,ghost,harker}_*_so`, `weapon_*_so` pickups,
`script_vehicle_{blackhawk,ch46e,littlebird_bench,mi-28_flying,zodiac,...}`,
`misc_turret`, `trigger_multiple_flag_set`, `info_volume_breachroom`,
`script_specialops 1` on worldspawn, and 26 distinct `script_flag` names on the
training map (`start_obstacle`, `obstacle_complete`, `start_frag_training`,
`sidearm_complete`, ...). **CoDOL coop is IW4 Spec Ops, authored in the SP
namespace.** None of it is reachable without an actor subsystem, a vehicle
subsystem, an animscript runtime and the addon-ents loader.

### 2.5 The coop data tables

`common_gametype_coop.ff` (overridden by `patch_common_gametype_coop.ff`) ships
46 stringtables; the two that matter here, both MEASURED by decoding the
StringTable asset directly:

- **`mp/cocoopclasstable.csv`** — 16 columns × 43 rows, oriented rows = property
  names in column 0, columns 1..15 = the fifteen coop loadouts whose
  `uniqueName` row reads `class0..class4`, `class0_up1..class4_up1`,
  `class0_up2..class4_up2`. Rows: `loadoutUpgradeNumber`,
  `loadoutUpgradeItemName` (`coop_class_<n>_upgrade<1|2>`), `loadoutName`
  (`COOP_CLASS1..5`, `_UPG1`, `_UPG2`), `loadoutDescription`, `uniqueName`,
  `loadoutPrimary` (`m16_basic`, `m16_grenadier_reddot`),
  `loadoutPrimaryAttachment1..7`, `loadoutPrimaryCamo`, `loadoutSecondary`
  (`barrett_zoom`, `usp_silencer_akimbo`, `tmp_silencer_reflex`),
  `loadoutSecondaryAttachment1..4`, `loadoutSecondaryCamo`, `loadoutPerk1..3`
  (`specialty_coop_lightweight`, `_quickrevive`, `_quickrevive_pro`,
  `_fastreload`, `_armorvest`, `_quickdraw`, `_fastsprintrecovery`, `_marathon`,
  `_stalker`, `_fastmantle`, `_rof`, `_holdbreath`, `_holdbreath2`,
  `_bulletaccuracy`, `_flakjacket_pro`), `loadoutKillstreak1..4` (`sentry`,
  `sr71_mp`, `uav`, `rcbomb_mp`, `sentry_pro`, `uav_pro`, `rcbomb_pro_mp`,
  `helicopter`), `loadoutDeathStreak`, `loadoutLethal`, `loadoutSpecial`,
  `loadoutTactical`, `loadoutMeleeWpn` (`coop_mel_karambit`, `coop_mel_knife`,
  `coop_mel_bonesaw`, `coop_mel_bowie`, `coop_mel_sog`), `charGender`,
  `charBOO/FJA/FPA/HAN/HEA/VES/HEG/ELP/KNP/PAT`.
  *Caveat:* some cells are de-duplicated string references this decode does not
  resolve and renders empty; the names listed above are cells that decoded to
  literal text. `_coopmode.gsc` therefore reads the table first and probes, so an
  unresolved cell costs nothing.
- **`mp/cocoopmapsettings.csv`** — 2 columns × 11 rows, column 0 being coop
  playlist map names: `coop_training_mp_killhouse`, `coop_take_mp_fav_tropical`,
  `coop_defense_mp_crash_tropical`, `coop_take_mp_estate_tropical`,
  `coop_evasion_mp_con_spring`, `coop_sniperfi_mp_con_spring`,
  `coop_suspension_mp_bridge`, `coop_chopper_mp_suburbs`,
  `coop_defense_mp_suburbs`, `coop_escape_mp_storm_spring`,
  `coop_ac_mp_hunted_spring`. Note several of those have **no zone on disk**,
  and the on-disk `coop_training_mp_killhouse_sh` is **not** a row (the table
  says `coop_training_mp_killhouse`, no `_sh`). Used as a membership probe only;
  what column 1 means is not established and nothing reads it.
- Also present and unread by this pass: `mp/coopranktable.csv`,
  `mp/cocharitems*.csv` (the coop character roster), `mp/coweapitems*.csv`.

---

## 3. What was created

21 files, all under the two directories this worker owns. LF line endings, to
match the existing `zm/` category files (the shared tree is mixed — `_load.gsc`
is CRLF, `war.gsc` and `common_scripts/utility.gsc` are LF, `mp_killhouse_sh.gsc`
is mixed — and the VM accepts both).

### 3.1 `bin\home\codol_rawfiles\coop\` — new, 17 files

| file | role |
|---|---|
| `maps/mp/gametypes/_callbacksetup.gsc` | The six labels the engine binds with `errorIfMissing=1`, plus `SetupCallbacks`/`SetDefaultCallbacks`/`SetupDamageFlags`. Points every callback at `_coopmode`. Host-migration callbacks dropped (this server has none); `CodeCallback_ScriptCommand` omitted exactly as IW4 omits it. |
| `maps/mp/gametypes/coop.gsc` | The client-contracted rules script (§2.1). Two statements: `SetupCallbacks()`, `_coopmode::init()`. |
| `maps/mp/gametypes/_coopmode.gsc` | Core: tables, init, level entry, loadout, spawning, callbacks. ~430 lines. |
| `maps/mp/coop_defense_mp_crash_tropical.gsc` … `coop_training_mp_killhouse_sh.gsc` (9) | Level scripts, **playlist spelling, canonical**. Each calls `_coopmode::levelMain( "<vision name>" )`. |
| `maps/mp/mp_crash_intro.gsc`, `mp_crash_tropical.gsc`, `mp_estate_tropical.gsc`, `mp_fav_tropical.gsc`, `mp_killhouse_sh.gsc` (5) | Level scripts, **base spelling**. Same call, naming their own zone's vision. These deliberately shadow the multiplayer level scripts of the same name *for coop matches only*; the shared `maps/mp/*.gsc` files are untouched and are what an mp match still compiles. |

Real behaviour in `_coopmode.gsc`, not stand-ins:

- **Spawning** is IW4 `maps/_specialops_code.gsc:10-81` ported by contract:
  `info_player_start_pmcDefend` (when the map ships any) → `info_player_start_so`
  → `info_player_start_pmc` → `info_player_start`, then the base zone's
  `mp_tdm_spawn_allies_start` / `mp_dm_spawn` / `mp_tdm_spawn` — because §2.3
  means those multiplayer points are the only ones the server can see today.
  IW4's `get_closest_exclude` spreading is reproduced with `distance()`
  (`getclosest` is not a builtin here): each successive player takes the
  candidate whose nearest already-used point is farthest away.
- **Loadout** is read from `mp/cocoopclasstable.csv` by row name
  (`loadoutPrimary`, `loadoutSecondary`, `loadoutMeleeWpn`) at the class column,
  then **probed** with `precacheItem` + `getWeaponIndexFromName` before use, so
  a name the mounted coop zones do not carry is never given to a player. Logs
  `CoDOL coop: primary <name>` or the explicit "not present" line.
- **Vision** is set from the level script, which is where IW4 sets it
  (`maps/mp/_load.gsc:93,97`), with the per-map name resolved from §2.2's table
  so the two zones without a vision of their own use their base map's.
- **Defend-mission detection** is derived from
  `getEntArray("info_player_start_pmcDefend","classname").size`, not declared.
- **`level.isSP = false`** at all three entry points the category can be entered
  through — `init()` (gametype-script load), `levelMain()` (the level script's
  `main()`, which runs *before* `CodeCallback_StartGameType`) and
  `Callback_StartGameType()`. This is the choke-point fix asked for: nothing in
  the coop closure calls `isSP()` today, but the assignment is the vendor
  function's own caching mechanism, and it is the only thing that makes the
  playlist and base map spellings behave identically.
- **`self.statusicon` is only ever cleared, never named** — the setter resolves
  against precached status-icon configstrings and `Scr_Error`s fatally on a name
  that was not precached, and that precaching belongs to the multiplayer chain
  this script set exists not to load.

### 3.2 `bin\home\codol_rawfiles\zm\` — 2 new files, 2 edited

| file | change |
|---|---|
| `maps/mp/gametypes/_zombiemode.gsc` | **Added `levelMain( visionName )`** — the shared level entry point: sets `level.isSP = false` and, when a vision name is given, calls `VisionSetNaked`/`VisionSetPain`. Nothing else in the file was touched. |
| `maps/mp/zm_zombie_training.gsc` | Routed through `levelMain( undefined )` instead of assigning `level.isSP` inline. `undefined` is deliberate: MEASURED, `zm_zombie_training.ff` ships neither `vision/` nor `sun/` (audit row 18 of `CODOL_ZOMBIES_STARTUP_20260915.md`). |
| `maps/mp/zm_prototype_sh.gsc` | **NEW.** `levelMain( "zm_prototype_sh" )`. MEASURED: that zone ships `sun/zm_prototype_sh.sun` and `vision/zm_prototype_sh.vision`. |
| `maps/mp/zm_asylum_sh.gsc` | **NEW.** `levelMain( "zm_asylum_sh" )`. Same, for `zm_asylum_sh.ff`. |

`mp/basemaps.arena` gives both of those maps `gametype "zm"`, so the existing
`zm.gsc` rules script plus these files is their whole per-map contract.

### 3.3 Gate results

```
python tools/codol_script_resolve.py --root bin/home/codol_rawfiles/<cat> \
       --root bin/home/codol_rawfiles --binary bin/codol_dedrun_next.exe \
       --seed maps/mp/gametypes/_callbacksetup.gsc --seed maps/mp/gametypes/<cat>.gsc \
       --seed maps/mp/<map>.gsc --seed codescripts/delete.gsc --seed codescripts/struct.gsc
```

- coop, all 14 level-script spellings: exit 0, closure **6**, *"every reachable
  script resolves against the registered builtin table"*.
- zm, all 3 maps: exit 0, closure **6**, same.
- `validated against binary: bin/codol_dedrun_next.exe (0 source registrations
  absent from it)`. (`bin/codol_dedrun.exe` does not exist in the tree; the
  running server's binary was not touched and no build was run — note the
  hazard that a bare `make` links over `codol_dedrun`.)
- mp closure diffed before/after: **identical**.

---

## 4. What is still stubbed or absent, by file and function

Nothing here is an empty body or an unsupported-error stub. These are systems
that are **absent**, with the reason:

| file | function | state |
|---|---|---|
| `coop/.../_coopmode.gsc` | `Callback_PlayerLastStand` | **Forwards to `Callback_PlayerKilled`.** The real behaviour is IW4 `maps/_coop.gsc:64-201`: `EnableDeathShield` turns a lethal hit into a `"deathshield"` notify, the player goes down and bleeds out over 120/90/60 s by difficulty, and a buddy inside the revive trigger brings him back. `EnableDeathShield` is not a builtin on this server and there is no revive trigger, so the state machine would be written against nothing. The label is registered because the engine binds it with `errorIfMissing=1`. It is also unreachable today — nothing grants last-stand eligibility. |
| `coop/.../_coopmode.gsc` | `giveStartingLoadout` | Perks, killstreaks, lethal/tactical and camo from `mp/cocoopclasstable.csv` are **not applied**. Those rows exist (§2.5) but every applier (`_perks`, `_killstreaks`, `_class`) is a multiplayer module, and naming one compiles all 100. A coop-side perk applier is follow-on work. |
| `coop/.../_coopmode.gsc` | `giveStartingLoadout` | The character faction is hardcoded `"tf"` — **INFERRED** from `mp/basemaps.arena`'s `allieschar "us_army"` plus the `actor_ally_codo_tf_*` models in the coop MapEnts. C1's own coop character selector index has not been read out of the profile. |
| `coop/.../_coopmode.gsc` | `init` | `level.coop_class_column = 1` (class0) is fixed. C1 sends the player's chosen coop class in his profile; reading it back is follow-on. |
| `coop/.../_coopmode.gsc` | `coop_map_table` usage | `mp/cocoopmapsettings.csv` is used **only** as a membership probe that prints a log line. Column 1's meaning is not established, so nothing reads it. |
| `coop/maps/mp/*.gsc` (all 14) | `main` | No `maps\mp\<map>_fx::main()` call. The fx module exists as a zone rawfile, but whether `Scr_ReadFile` can reach a CoDOL zone rawfile is unproven (its fastfile fallback goes through the retained `DB_FindXAssetHeader` path, not the CoDOL archive registry; only `animtrees/` is wired to the registry in `Scr_ReadFile`). A `file::function` call is a compile-time dependency, so being wrong is a fatal load error, not a missing effect. Same reasoning the zm level script already used. |
| `coop/maps/mp/*.gsc` (all 14) | `main` | No minimap (`_compass` is a multiplayer module). |
| everywhere | — | The Spec Ops **mission layer** is absent in full: objectives, challenge stars, the countdown/challenge HUD, `script_flag` sequencing, actors, vehicles, breaching, the `_specialops_battlechatter` dialog. That is `maps/_specialops.gsc` (1247 L) + `_specialops_code.gsc` (1621 L) + `_coop.gsc` (1117 L) + `_pmc.gsc` (1594 L) of IW4 **singleplayer-namespace** script standing on the SP engine (`flag_init`/`ent_flag`, `level.gameskill`, `level.player`/`level.player2`, the actor and vehicle subsystems). It is blocked behind native work, not behind GSC. |
| native, not mine | addon_map_ents loader | Until it exists, a coop match sees the base `mp_*` entities and none of the Spec Ops ones (§2.3). This is the single highest-value native item for coop. |

---

## 5. Does the resolver need a change? **No.** Two things for the parent instead.

### 5.1 `src/codol/script/codol_script_source.c` — no patch recommended

Both of the questions asked are already answered correctly by the existing code:

- **Can a category root ADD a file without shadowing a shared one?** Yes,
  already. `coop/maps/mp/gametypes/coop.gsc` has no counterpart in the shared
  tree and resolves from the category root; `codescripts/delete.gsc` and
  `codescripts/struct.gsc` have no counterpart in `coop/` and resolve from the
  shared tree. The probe order is *per file*, not per directory, so the two
  behaviours coexist with no change. Measured: the coop closure resolves 4 files
  from `bin/home/codol_rawfiles/coop` and 2 from `bin/home/codol_rawfiles`.
- **Should `mp` get its own root for symmetry?** Not worth it, and it is a
  migration, not a patch. It would mean **moving the whole 100-script
  multiplayer closure** — `maps/mp/_load.gsc`, the 37 `maps/mp/gametypes/*`
  modules, all 16 `maps/mp/killstreaks/*`, `maps/mp/perks/*`,
  `maps/mp/equipment/*`, the 10 `common_scripts/*` subsystems and the ~130
  `maps/mp/mp_*.gsc` level/fx scripts — from `bin/home/codol_rawfiles/` into
  `bin/home/codol_rawfiles/mp/`, while the rest of the tree (`character/`,
  `codescripts/`, `aitype/`, `animscripts/`, `xmodelalias/`, `mp/*.csv`) has to
  stay shared because all three categories use it. That tree is load-bearing for
  the user's live matches and **this worker moved nothing**. If the parent ever
  wants it, it is a scheduled migration with a full before/after closure diff,
  and the only thing it buys is removing one failed `fopen` per script under mp.

  The current shape is the better one anyway: `bin/home/codol_rawfiles/` is the
  *common* root, and `zm/` and `coop/` are category overlays over it. The
  comment at `codol_script_source.c:81` already says exactly this.

The only optional hardening, and it is cosmetic: `zone_type_prefix()` returns 0
silently for a malformed category, which makes the category layer vanish without
a word. A one-line `Com_PrintWarning` there would turn "mysteriously compiled
the multiplayer scripts" into a log line. Not recommended as urgent — the three
live categories are all valid lowercase ASCII, and
`CODOL_LoadMapArchives` already rejects anything that is not `mp`/`coop`/`zm`
before a map can spawn.

### 5.2 `src/codol/assets/codol_asset_commands.c` — a real coop blocker, hand-back patch

**Not my file** (another worker owns `src/codol/assets/**`), so here is the
finding and the patch rather than an edit.

`CODOL_ZoneTypeForMapName()` derives the category from the map name's prefix and
`CODOL_LoadMapArchives()` **refuses the mount** when it disagrees with
`codol_zoneType`:

```c
static const char *CODOL_ZoneTypeForMapName(const char *map)
{
    if(!Q_stricmpn(map,"zm",2)) return "zm";
    if(!Q_stricmpn(map,"coop",4)) return "coop";
    return "mp";
}
...
derived=CODOL_ZoneTypeForMapName(map);
if(strcmp(derived,zone_type)) { Com_PrintError(...); return 0; }   /* caller -> ERR_DROP */
```

That is correct for mp and zm, whose map names are category-distinct. For coop
it is **only** correct under the playlist spelling. If the server is ever handed
the base spelling with the coop category — which is exactly what
`alpha0022/match_server_control.py`'s own docstring describes (*"a coop room can
preload `coop_training_mp_killhouse_sh` while the native server loads the level
zone `mp_killhouse_sh` with `g_gametype coop` and common-gametype category
`coop`"*), and what the 2026-08-19 capture shows reaching `CA_LOADING`
(`map: mp_killhouse_sh  type: coop`) — the mount is refused and the server drops
before a single script loads.

Suggested patch (the map name stays the authority for mp/zm; coop gains the one
exception the shipped data justifies):

```diff
--- a/src/codol/assets/codol_asset_commands.c
+++ b/src/codol/assets/codol_asset_commands.c
@@
 static const char *CODOL_ZoneTypeForMapName(const char *map)
 {
     if(!Q_stricmpn(map,"zm",2)) return "zm";
     if(!Q_stricmpn(map,"coop",4)) return "coop";
     return "mp";
 }
+/* A coop match has two names for the same level and C1 mounts both: the
+ * playlist name (coop_training_mp_killhouse_sh) and the base level name it
+ * derives from it by stripping at the first '_' after "coop_" (mp_killhouse_sh,
+ * C1 0x004CD0FE).  The coop zones ship no world assets at all -- only an
+ * addon_map_ents -- so the level zone really is the shared mp_* one, and a
+ * server handed the BASE spelling with codol_zoneType=coop is not disagreeing
+ * with the client, it is naming the same match by its other name.  The map name
+ * therefore stays the authority for mp and zm, whose names are
+ * category-distinct, and coop is allowed to arrive as mp_*.
+ *
+ * The reverse is still refused: an mp_* map with an unrequested coop category
+ * cannot happen, because zone_type comes from codol_zoneType, which the lobby
+ * sets deliberately per room. */
+static int CODOL_ZoneTypeAcceptable(const char *derived,const char *zone_type,const char *map)
+{
+    if(!strcmp(derived,zone_type)) return 1;
+    if(!strcmp(zone_type,"coop") && !strcmp(derived,"mp") && !Q_stricmpn(map,"mp_",3)) return 1;
+    return 0;
+}
@@
     derived=CODOL_ZoneTypeForMapName(map);
-    if(strcmp(derived,zone_type)) {
+    if(!CODOL_ZoneTypeAcceptable(derived,zone_type,map)) {
         Com_PrintError(CON_CHANNEL_SYSTEM,
             "CoDOL map archives: '%s' is a '%s' map but codol_zoneType is '%s'; "
             "mounting common_gametype_%s for it would give the client the wrong zones and fs_crc\n",
             map,derived,zone_type,zone_type);
         return 0;
     }
```

Note the `if(!strncmp(map,"coop_",5)) { base=strchr(map+5,'_'); ... }` block just
below already handles the playlist spelling correctly and needs no change; under
the base spelling `base == map` and only three zones are mounted
(`common_gametype_coop`, `localized_common_gametype_coop`, `mp_<map>`), which
means the **playlist-specific addon zone would not be mounted at all**. That is
the second reason to prefer the playlist spelling as the announced map name
(§2.2) and to treat this patch as the safety net rather than the plan.

### 5.3 Other findings handed back

1. `shouldRunServerSideEffects()` is called by 15 `maps/mp/*_fx.gsc` and defined
   nowhere in `bin/home/codol_rawfiles` (§1.1). Owner: whoever owns the shared
   mp tree.
2. No `addon_map_ents` (IW4 asset type 42) loader exists (§2.3). Owner:
   `src/codol/assets/**`. Without it, coop's Spec Ops entities — including its
   own player starts — are invisible to the server.
3. `mp/cocoopmapsettings.csv` names `coop_training_mp_killhouse` while the zone
   on disk is `coop_training_mp_killhouse_sh`, and names six coop maps for which
   no zone ships. Informational; `_coopmode` treats a miss as a log line, not an
   error.
4. Two coop zones ship no vision of their own (`coop_spec_mp_fav_tropical`,
   `coop_take_mp_estate_tropical`). Handled in data by naming the base map's
   vision; worth knowing if either map renders oddly.
5. `coop_prolog_mp_crash_intro` and `coop_spec1_mp_killhouse_sh` addon MapEnts
   did not extract by name this pass, so their player-start classnames are
   unconfirmed. The spawn order in `_coopmode` covers every classname the other
   seven use, so this is a completeness gap, not a risk.
