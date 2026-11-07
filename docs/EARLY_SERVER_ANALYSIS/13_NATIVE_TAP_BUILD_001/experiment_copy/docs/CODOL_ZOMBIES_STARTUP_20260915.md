# zm handoff: the isSP crash, the sibling landmines, and what a zombies match actually needs

Status of this document, by evidence class:

- **Observed live**: one console transcript of a real `map zm_zombie_training`
  handoff from the Python lobby to this server, supplied by the user (quoted
  under §1). The lobby's dispatch is corroborated by a wiretap capture of the
  same day. Nothing else here was observed live *by this pass*; prior live
  results from earlier passes are cited as such and attributed.
- **Written, not built, not run**: one GSC edit in
  `scripts/codol/maps/mp/_load.gsc` (this worker) and one in
  `scripts/codol/maps/mp/gametypes/_gamelogic.gsc` (the parent). Neither has
  been compiled by the VM. This worker did not start the server, the lobby or
  the client, and killed no process.
- **Read off disk / extracted offline**: the script-closure audit, the zone
  rawfile inventory (fastfiles decrypted and inflated offline), the MapEnts
  harvest, and every file:line citation below.
- **Reasoned, not verified**: every "the next failure will be X" claim, marked
  as such where it appears and collected in §7.

---

## 1. The crash

### Transcript (user-supplied, live)

```
Notice: Could not find label 'CodeCallback_ScriptCommand' in script 'maps/mp/gametypes/_callbacksetup' - this part will be disabled
Error: Could not load rawfile "maps/mp/zm_zombie_training.gsc".
Notice: Could not find script 'maps/mp/zm_zombie_training' - this part will be disabled
Warning: CoDOL xmodel 'vehicle_mig29_desert' is not in any mounted zone; using void
Warning: CoDOL xmodel 'projectile_cbu97_clusterbomb' is not in any mounted zone; using void
******* script runtime error *******
type undefined is not an object: (file 'common_scripts/_dynamic_world.gsc', line 119)
  foreach player in level.players ...   (player_init)
called from common_scripts/_dynamic_world.gsc:87 player_init(); <- maps/mp/_load.gsc:55 thread common_scripts\_dynamic_world::init(); <- _gamelogic.gsc:1244 maps\mp\_load::main(); <- _callbacksetup.gsc:18 [[level.callbackStartGameType]](); <- CodeCallback_StartGameType()
Sys_Error: script runtime error ... Server fatal crashed
```

The three lines before the runtime error are **not** the cause and are not
regressions:

- `CodeCallback_ScriptCommand` is loaded with `errorIfMissing = 0`
  (`src/scr_vm_main.c:1312`); IW4's `_callbacksetup.gsc` genuinely has no such
  label. It prints on every map, MP included.
- `maps/mp/zm_zombie_training.gsc` is the *level script*. Its absence is
  non-fatal by construction (`GScr_LoadScripts` passes `qfalse`,
  `src/scr_vm_main.c:1344`) — but it is load-bearing for §3.3 and §4, and it is
  the accident that let this particular crash surface at all.
- The two xmodel warnings are MP killstreak models that live in the mp zones
  and are absent from the zm zone set; the killstreak precache runs regardless
  of zone type. Cosmetic.

### Root cause

`vendor/iw4/common_scripts/utility.gsc:2080-2086`:

```
isSP()
{
	if ( !isdefined( level.isSP ) )
		level.isSP = !( string_starts_with( getdvar( "mapname" ), "mp_" ) );

	return level.isSP;
}
```

IW4 shipped no multiplayer map whose name was not `mp_*`, so it could infer
"singleplayer" from the map name. CoDOL can not: `zm_zombie_training` is a
multiplayer map that is not `mp_*`, and neither are the `coop_*` zones. Under
zm, `isSP()` returned **true** for every caller in the vendor tree.

The first caller reached was `common_scripts/_dynamic_world.gsc:115-125`:

```
player_init()
{
	if ( isSP() )
	{
		foreach ( player in level.players )
```

`level.players` is created by `_spawnlogic::init()`
(`scripts/codol/maps/mp/gametypes/_spawnlogic.gsc:894`), which
`Callback_StartGameType` does not thread until
`scripts/codol/maps/mp/gametypes/_gamelogic.gsc:1479` — long after it calls
`maps\mp\_load::main()`. The foreach iterated an undefined value and
`Sys_Error`ed the server.

### The fix

Two edits, both "answer the question instead of letting it be inferred".
`isSP()` caches into `level.isSP` and only computes when that is undefined, so
assigning it is the mechanism the vendor function itself provides. A dedicated
match server is never singleplayer, whatever the map is called.

**(a) Parent-applied.** `scripts/codol/maps/mp/gametypes/_gamelogic.gsc:1259`,
first statement of `Callback_StartGameType()`:

```
	level.isSP = false;
```

This is what stopped the observed crash. It is correct, and it is sufficient
**for the exact configuration that crashed** — but only by accident.

**(b) This worker.** `scripts/codol/maps/mp/_load.gsc:9-31`, ahead of the
`level._loadStarted` guard, the same assignment plus its reasoning.

Why (b) is not redundant: **an IW4 level script's own `main()` calls
`maps\mp\_load::main()`, and the level script runs before
`CodeCallback_StartGameType`.** Both facts are on disk —

- `scripts/codol/maps/mp/mp_killhouse_sh.gsc:13` and
  `scripts/codol/maps/mp/mp_fav_tropical.gsc:23` both call
  `maps\mp\_load::main();` from the level script's `main()`;
- `vendor/iw4/maps/mp/gametypes/_callbacksetup.gsc:7-8` documents
  `CodeCallback_StartGameType` as *"Called by code after the level's main script
  function has run"*.

So on every map that **has** a level script, `_load::main()` runs first, from
the level script, before `Callback_StartGameType` reaches line 1259. zm reached
`_load` through the later path only because `maps/mp/zm_zombie_training.gsc`
does not exist yet. Supplying that level script — the immediate next step for
zm, §6 — routes `_load::main()` back through the earlier path and reinstates the
identical crash, with the parent's fix present and apparently correct.

`_load::main()` is the single choke point both entry orders pass through.
Reasoned from the call graph; not re-observed live.

---

## 2. Sibling-landmine audit

### Method

The vendor tree is 1479 `.gsc` files, most of which never load; grepping all of
them is noise (e.g. 50+ `maps/animated_models/*.gsc` test
`string_starts_with( mapname, "mp_" )` and never load on a dedicated server).
The audit was run against the **actual loaded closure**, computed by walking
`#include` and `file\path::function` references from the engine's entry points
(`maps/mp/gametypes/_callbacksetup`, `codescripts/delete`, `codescripts/struct`,
the gametype script) through the four roots in the order
`CODOL_ReadScriptSourceWithNativeOverlay` resolves them
(`src/codol/script/codol_script_source.c:62-65`: `scripts/codol`, then
`alpha0022/gsc_overlay`, then `<vendor>/mp/<name>`, then `<vendor>/<name>`).

Result: **274 files load** — 40 from `scripts/codol`, 0 from `gsc_overlay`,
234 from `vendor/iw4`. The only two unresolved references are the two filename
aliases handled explicitly at `codol_script_source.c:69-74`. This matches the
269-file figure at `docs/CODOL_IMPLEMENTATION_PASS.md:2362`.

### Findings

| # | Site (file:line) | Predicate | Breaks under zm? | Status |
|---|---|---|---|---|
| 1 | `vendor/iw4/common_scripts/_dynamic_world.gsc:117` | `isSP()` → `foreach player in level.players` | **YES — the fatal crash** | FIXED (a)+(b) |
| 2 | `vendor/iw4/common_scripts/_dynamic_world.gsc:260,662,726,1445,1462,1478` | `isSP()` | No, once (1) is answered; timer intervals and `level.gameEnded` guards | FIXED by the same assignment |
| 3 | `vendor/iw4/common_scripts/_elevator.gsc:68` | `isSP()` picks the `scr_elevator_motion_detection` default | No (dvar default), but was wrong-valued | FIXED by the same assignment |
| 4 | `vendor/iw4/common_scripts/_pipes.gsc:132,186` | `isSP()` gates steam-pipe damage | No (cosmetic), wrong-valued | FIXED by the same assignment |
| 5 | `vendor/iw4/common_scripts/utility.gsc:2008,3026,3155,3185,3215,3334,3611` | `isSP()` in shared helpers (exploders, spawnflags, trigger helpers) | No; wrong-valued only | FIXED by the same assignment |
| 6 | `vendor/iw4/codescripts/character.gsc:124` | `!common_scripts\utility::isSP()` gates MP character setup | **Would have skipped MP character setup for every zm player.** Runs at connect, i.e. after both fixes | FIXED by the same assignment |
| 7 | `vendor/iw4/common_scripts/utility.gsc:2083` | the `string_starts_with(…,"mp_")` itself | Root cause | Not edited. Shadowing a 3600-line vendor utility to change one line was rejected; pre-seeding `level.isSP` is the vendor's own mechanism |
| 8 | `vendor/iw4/maps/mp/gametypes/_globallogic.gsc:23-24` | `level.script = tolower(getDvar("mapname"))`; `level.gametype = tolower(getDvar("g_gametype"))` | No. `level.script` → `zm_zombie_training` (used by `_matchdata::init` and dev prints). `level.gametype` takes the **raw dvar**, not the translated script name — see §3.2 | OK / documented |
| 9 | `vendor/iw4/maps/mp/gametypes/_serversettings.gsc:15` → `constrainGameType("zm")` (:47-) | if/else over `dm`/`tdm`/… | No branch matches `zm`, so no entity is deleted — incidentally correct, it leaves the zm entities alone | OK |
| 10 | `vendor/iw4/maps/mp/_art.gsc:29-30` | `if(!isdefined(level.script)) level.script = tolower(getDvar("mapname"))` | No — whole body is inside `/# … #/`, and (8) already set it | OK |
| 11 | `scripts/codol/maps/mp/gametypes/_gamelogic.gsc:1455` | `printLn("  Map: " + level.script)` | No — also inside `/# … #/` | OK |
| 12 | `vendor/iw4/common_scripts/_painter.gsc:1099` | `return issubstr( level.script, "mp_" )` | Returns false under zm where MP returns true, but `_painter` is threaded only from the `/# … #/` block in `_load.gsc` | OK / dev-only |
| 13 | `vendor/iw4/common_scripts/_elevator.gsc:1174` | `level.script == "plaza" \|\| "highrise_test"` | No — false for zm, the intended MP answer | OK |
| 14 | `src/codol/script/codol_script_map.c:8-21` (`getMapCustom`) → `mp/basemaps.arena` | looks `mapname` up in the arena rawfile | The arena entry for `zm_zombie_training` **does exist** (§3.1) but carries only `map`, `longname`, `gametype`, `description`, `mapimage`. So `allieschar`/`axischar`/`environment`/`thermal` all return `""`, and `_gamelogic.gsc:1281-1298` falls back to `mp/factionTable.csv` rows 1 and 2 | No crash. Wrong factions for zombies — a §5 item, not a landmine |
| 15 | `scripts/codol/maps/mp/gametypes/war.gsc:33`, `conf.gsc:40`, `infect.gsc:33` | `getdvar("mapname") == "mp_background"` | No — equality against one menu-background map | OK |
| 16 | `vendor/iw4/maps/animated_models/*.gsc:12` (≈50 files) | `string_starts_with( mapname, "mp_" )` | Not in the loaded closure — per-model scripts loaded by the fastfile, not by the server's script set | Not applicable |
| 17 | `scripts/codol/maps/mp/gametypes/_spawnlogic.gsc:46-52, 89-95` | `AbortLevel()` when a required spawn classname yields zero entities | **No.** The MapEnts prove `zm_zombie_training` ships one each of `mp_tdm_spawn_allies_start`, `mp_tdm_spawn_axis_start`, `mp_tdm_spawn`, `mp_dm_spawn`, `mp_global_intermission`, `info_player_start` (§3.4) | OK — but one spawn point per team, so no spawn spreading |
| 18 | `scripts/codol/maps/mp/_load.gsc:70,74` | `VisionSetNaked( getDvar("mapname"), 0 )`, `VisionSetPain( getDvar("mapname") )` | **zm-specific risk, not yet observed.** `zm_zombie_training.ff` ships **no** `vision/zm_zombie_training.vision` and no `sun/…sun` rawfile, where every mp zone and the other two zm zones do (§3.5). The vision name being asked for does not exist in any mounted zone | OPEN — see §7 |

No other `isSP`, `string_starts_with`, `getdvar("mapname")`, `level.script`,
`isMP`, `level.multiplayer`, `matchMakingGame`, `is_specialop`, `co_`/`coop_`
prefix or gametype-whitelist site in the 274-file closure changes behaviour
under a `zm_*` or `coop_*` map name. `matchMakingGame()` and `level.splitscreen`
are numerous but read server state, not the map name.

### Files changed by this worker

- `scripts/codol/maps/mp/_load.gsc` — one statement (`level.isSP = false;`) plus
  the comment explaining why the `_gamelogic` copy alone is not sufficient.

Nothing else. `_gamelogic.gsc` is parent-owned and was not touched; **no edit to
it is requested** — line 1259 is correct and should stay.

---

## 3. What the client actually expects for a zm match

### 3.1 The client's gametype contract: `zm`, non-team-based

Extracted offline from `code_post_gfx_mp.ff` (not from a zm zone):

- `maps/mp/gametypes/_gametypes.txt` — 19 entries:
  `dm dom sd sab war koth oneflag arena dd vip ctf gtnw coop combat clanwars`
  **`zm`** `conf infect hp`. Four of those (`combat`, `clanwars`, `hp`, and `zm`
  itself) are CoDOL-only; IW4 had 13.
- `maps/mp/gametypes/zm.txt` — one line, `"MPUI_ZOMBIE"`, the same
  localized-name form as `war.txt` (`"MPUI_WAR"`) and `dm.txt`.
- `mp/basemaps.arena`:

```
{
	map			"zm_zombie_training"
	longname	"MPUI_ZM_ZOMBIE_TRAINING"
	gametype	"zm"
    description "MPUI_DESC_MAP_ZM_PROTOTYPE"
	mapimage    "blank"
}
```

  — same `gametype "zm"` for `zm_prototype_sh`, `zm_asylum_sh`, and three
  zone-less names (`zm_factory_sh`, `zm_sumpf`, `zm_sumpf_sh`).
- `mp_playlists.ff` → `playlists_allmaps.info`: `gametype zm` /
  `name english "Zombie Mode"` / **`script zm`**, with **no `teambased` line**
  (unlike `combat`/`tdm`), and `mp/gametypescptable.csv` places `zm` in the
  NONTEAM half. **zm is a non-team-based gametype whose script name is `zm`.**

So `maps/mp/gametypes/zm.gsc` is the client-contracted server-side counterpart.
It does not exist in any of the three script roots.

### 3.2 How the server picks the gametype script today

`GScr_LoadGameTypeScript`, `src/scr_vm_main.c:1270-1313`:

1. `script_gametype = sv_g_gametype->string` (:1279).
2. Under `CODOL_SERVER`, `combat` and `tdm` translate to `war` (:1284-1285) —
   the public dvar is deliberately left alone, only the script entry point is
   translated. `zm` is not in that translation.
3. `maps/mp/gametypes/<script_gametype>` loaded with `errorIfMissing = 0`
   (:1287, :1290).
4. On failure it prints `Could not find script: maps/mp/gametypes/zm` and
   *"The gametype zm is not available! Will load gametype dm"*, then loads
   `maps/mp/gametypes/dm` with `errorIfMissing = 1` (:1299-1301).
5. The `Cvar_SetString(sv_g_gametype, "dm")` that vanilla IW4OL does here is
   compiled out under `CODOL_SERVER` (:1296-1298).

**Consequence for `g_gametype zm`:** the server runs IW4 free-for-all
deathmatch while `g_gametype` serverinfo still reads `zm`. Because
`_globallogic.gsc:24` takes `level.gametype` from the **dvar**, every
gametype-scoped dvar the match registers is named `scr_zm_*` and the `dm`
script reads them back under the same names — internally consistent, so not a
crash, but "zm" today *is* deathmatch and only one error line says so. This is
the "gametype fallback silent" note already at
`docs/CODOL_PARITY_INVENTORY.md:296`.

There is no `maps/mp/gametypes/zm.gsc` anywhere: `scripts/codol` has
`war.gsc`, `conf.gsc`, `infect.gsc`; `gsc_overlay` has only `_codol_chat.gsc`
and `_codol_respawn.gsc`; `vendor/iw4` has the 13 IW4 gametypes.

### 3.3 How the server picks the level script

`GScr_LoadScripts`, `src/scr_vm_main.c:1320-1349`:

```
Com_sprintf(mappath, sizeof(mappath), "maps/mp/%s", mapname->string);       // :1342
g_scr_data.levelscript = GScr_LoadScriptAndLabel(mappath, "main", qfalse);  // :1344
```

The prefix is a hardcoded `maps/mp/` for every zone type. For
`mapname zm_zombie_training` the server looks for exactly one thing —
`maps/mp/zm_zombie_training` — and `qfalse` makes its absence non-fatal.
Resolved through `CODOL_ReadScriptSourceWithNativeOverlay`, so the **only**
place this server will ever find a zm level script is
`scripts/codol/maps/mp/zm_zombie_training.gsc`.

### 3.4 Zone rawfile inventory (extracted offline)

CoDOL fastfiles are **not** plain `IWffu100`+zlib. Per
`src/codol/assets/codol_fastfile.c:51-107`, an `IWff0100` archive is a
0x115-byte header, a 256-byte RSA-OAEP(SHA-256) blob at `+0x15` decrypted with
the private key embedded in `C1.exe` at file offset `0x83C248`
(`codol_client_crypto.c:17-43`), yielding an AES-192 key + IV; the body is
0x2000 blocks under AES-CTR with a little-endian counter, with `IWffs100` hash
tables interleaved, then zlib. That was re-implemented offline for this pass.
All **90** `.ff` files in `client_shipRetail/chinese` decrypted and inflated,
0 failures; every zm zone begins `49 57 66 66 30 31 30 30 4e 01 00 00`
(`IWff0100`). `bin/codol_archive` is a 32-bit Linux ELF and was not runnable
here.

**`zm_zombie_training.ff`** (69,157,141 bytes → 152,295,867 inflated,
1189 assets) contains exactly **four** rawfiles:

```
animlists/zm_zombie_training.animlist          183 B
maps/mp/zm_zombie_training_fx.gsc            7,986 B   main(){ level._effect[...] = loadfx(...) }
maps/createfx/zm_zombie_training_fx.gsc     48,959 B   //_createfx generated
<pooled, unnamed>                              332 B   zone build log
```

The build log records the client's zone chain: `code_post_gfx_mp` →
`common_mp` → `common_gametype_zm` → map zone.

**Headline: `maps/mp/zm_zombie_training.gsc` does not exist in any zone.**
Neither does `maps/zm/...`, `maps/mp/gametypes/zm.gsc`, any `_zombiemode*.gsc`,
or any `.csc` file at all. A sweep of all 90 zones finds **55 distinct `.gsc`
rawfiles and every one is an fx pair** — `maps/mp/<map>_fx.gsc` +
`maps/createfx/<map>_fx.gsc`.

**Control:** `mp_killhouse_sh.ff` yields `animlists/…`, the same two `_fx.gsc`,
plus `vision/mp_killhouse_sh.vision`, `vision/…_tp.vision`,
`sun/mp_killhouse_sh.sun`. `common_gametype_mp.ff` likewise ships **no**
`maps/mp/gametypes/*.gsc`. So this is not a zm gap: CoDOL zones never ship
level or gametype GSC, and the server owns both files for every map. That is
already how `mp_killhouse_sh.gsc` and `mp_fav_tropical.gsc` came to live in
`scripts/codol`.

**`common_gametype_zm.ff`** (51 rawfiles, 46 StringTables) carries the zm-only
data, and one entry matters more than the rest:

- **`mp/zombiemode.csv`** — 5 columns × 106 rows,
  `NAME | EASY | MEDIUM | HARD | VETERAN`. The entire mode's tuning is already
  on disk and reachable by `tableLookup`: `zombie_health_start`,
  `zombie_health_increase(_multiplier)`, `zombie_spawn_delay`,
  `zombie_new_runner_interval`, `zombie_move_speed_multiplier`,
  `zombie_max_spawned`, `zombie_max_ai`, `zombie_ai_per_player`,
  `zombie_score_start_1p..4p` (+`_team`), `zombie_score_kill_1p..4p`
  (+`_team`), `zombie_score_damage_normal/light`,
  `zombie_score_bonus_melee/head/neck/torso/burn`, `starting_lives`,
  `penalty_no_revive/died/downed`, `zombie_perk_juggernaut_health`,
  `rebuild_barrier_cap_per_round`, `zombie_powerup_point_doubler_time`,
  `…insta_kill_time`, `…drop_increment`, `…drop_max_per_round`,
  `game_start_delay`, `zombie_intermission_time`, `zombify_player`,
  `spectators_respawn`, tesla/ape entries, plus a zm weapon list
  (`ray_gun_zm`, `tesla_gun_zm`, `thundergun_zm`, `freezegun_zm`,
  `m1911_zm`, `python_zm`, … , `ray_gun_upgraded`, `tesla_gun_upgraded`).
  `patch_common_gametype_zm.ff` ships a 6,352-byte override that wins.
- `mp/zmranktable.csv`, `mp/zmmatchbonus.csv`.
- `animlists/common_zombie.animlist` (7,874 B, patch version),
  `animtrees/zombie_dog.atr`, `animtrees/zm_magic_box.atr`
  (`codo_treasure_chest_box_open/close`), `shock/pain_zm.shock`,
  `shock/sonic.shock`, `shock/electrocution.shock`.

Localized UI strings live in `localized_code_post_gfx_mp.ff`:
`MPUI_ZM_ZOMBIE_TRAINING`, `MPUI_ZOMBIE`, `SF_UI_GAME_TYPE_ZOMBIE`,
`SF_UI_ZOMBIE_{BLACK_HOLE_BOMB,CYMBAL_MONKEY,NESTLING_DOLLS,QUANTUM_BOMB,STARBURST_BOMB}_{NAME,DESC}`.

### 3.5 Missing vision/sun for this one map

`zm_prototype_sh.ff` and `zm_asylum_sh.ff` both ship `sun/<map>.sun` and
`vision/<map>.vision`. **`zm_zombie_training.ff` ships neither.** Every mp zone
does. `scripts/codol/maps/mp/_load.gsc:70,74` calls
`VisionSetNaked( getDvar("mapname"), 0 )` and `VisionSetPain( getDvar("mapname") )`,
i.e. asks for `zm_zombie_training` by name. Audit row 18; risk, not observation
— see §7.

### 3.6 What the map itself declares (MapEnts)

Two independent extractions agree. `alpha0022/resources/map_spawns.proposed.json`
already carried a MapEnts harvest for all three zm maps (its provenance note
records the same `C1.exe` `0x83C248` RSA key and per-block SHA-256
verification); this pass re-extracted `zm_zombie_training`'s 114 KB entity text
from the clipmap stream directly. Classname histogram:

```
326 node_pathnode      185 script_struct     104 script_origin      94 script_model
 94 script_brushmodel   20 trigger_use        12 trigger_multiple   10 trigger_radius
  6 info_volume          4 node_negotiation_{begin,end}             4 info_intermission
  3 trigger_damage       2 trigger_use_touch   1 worldspawn
  1 mp_tdm_spawn_axis_start  1 mp_tdm_spawn_allies_start  1 mp_tdm_spawn  1 mp_dm_spawn
  1 mp_global_intermission   1 info_player_start
  1 actor_zombie_juggernaut  1 actor_zombie_ger  1 actor_zombie_dog
```

Notes that matter:

- There is **no `script_gametype` key on worldspawn**, and the spawn points are
  the ordinary MP ones. A zm gametype script must use DM/TDM spawns — which is
  also why `war`/`dm` do not `AbortLevel` here (audit row 17).
- Three `actor_zombie_*` classnames are present: `actor_zombie_ger`,
  `actor_zombie_juggernaut`, `actor_zombie_dog`. Those are actor-spawner
  entities with no actor subsystem behind them on this server (§4).
- 326 `node_pathnode` entities, but see §5: the compiled `pathData` payload is
  recorded as absent (`alpha0022/docs/actors_zombies.md:499`, which puts
  `zm_zombie_training`'s `nodeCount` at 1641).

The zombies content, by `script_noteworthy`: `zombie_spawner` ×51 (sample row:
`classname script_struct`, `model char_ger_honorgd_fullbody`, `count 9999`,
`script_forcespawn 1`, `spawnflags 3`, `script_disable_bleeder 1`,
`targetname start_zone_spawners`), `zombie_dog_spawner` ×1, `electric` ×1 (the
power switch), `chest`/`chest_rubble` (mystery box), `specialty_fastreload` and
`specialty_rof` (perk machines), `weapon` ×2 (wall-buys), `door` ×2,
`door2_tutorial`…`door5_tutorial`, `navigation_arrows` ×16, `player_volume` ×7.

By `targetname` (252 distinct keys):

- **Zones/spawners**: `start_zone`, `upstairs_zone`, `box_zone`, `final_zone`;
  `start_zone_spawners` (1), `start_zone_spawners_dog` (7),
  `upstairs_zone_spawners` (19), `upstairs_zone_spawners_dog` (10),
  `box_zone_spawners` (5), `box_zone_spawners_dog` (5), `window_spawners` (2),
  `main_zombie_spawner`, `main_juggernaut_spawner`, `zombie_spawner_door`,
  `zombie_spawner_upstairs`, `zombie_spawner_dog_init`.
- **Barriers**: `zombie_barrier`, `zombie_debris` (4), `zombie_clip` (3),
  `zombie_door` (5), `zombie_trap`, `first_door_blocker`.
- **Power**: `elec_switch`, `use_elec_switch`, `elec_switch_fx`,
  `power_switch_fx`, `power_off_fx` (2), `arrows_to_power`,
  `elec_door_01`…`_05`, `elec_point_01`…`_03`, `zapper_door_down`.
- **Mystery box**: `treasure_chest_use`, `treasure_chest_floor`, `chest_box`,
  `chest_lid`, `chest_origin`, `box_point`.
- **Perks / Pack-a-Punch**: `zombie_vending` (2, models
  `zombie_vending_doubletap` / `zombie_vending_speedcola`),
  `vending_doubletap`, `vending_sleight`, `speed_drink`, `weapon_upgrade` (8).
- **Progression**: `zm_door_01`…`_03` (+`_left`/`_right`), `zm_main_gate`,
  `door1_opening`…`door4_back`, `final_door` + `_trigger`/`_hint`/`_up`/`_down`,
  `left_lift_door`/`right_lift_door`, `power_room_tele`, `power_stairs_tele`.
- Also `zombie_care_package`, `script_string "zombie_chaser"`,
  `animscript "zombie_mantle_over_40"`, skybox `skybox_zombie_cod5_prototype`.

`zm_asylum_sh` uses the same vocabulary plus `magic_box_hallway`,
`magic_box_bathroom`, `start_chest`, `zap_machine_north/south`. CoDOL's zombies
maps are authored against T5/WaW `_zombiemode` conventions, which is what makes
the T5 corpus the correct behavioural reference (§5).

### 3.7 Zone mounting, and what the lobby dispatches

`CODOL_LoadMapArchives`, `src/codol/assets/codol_asset_commands.c:275-302`,
accepts exactly three zone types — `mp`, `coop`, `zm` (:280) — and for
`zone_type=zm`, `map=zm_zombie_training` mounts `common_gametype_zm`,
`localized_common_gametype_zm`, `zm_zombie_training`, each plus its `patch_*`
sibling when present. All six exist under `client_shipRetail/chinese/`.
`fs_crc(zm) = 0x801CEF02` is cited from earlier harvested work, not re-derived.

The lobby's plan is built at `alpha0022/match_server_control.py:96-119` and sent
to loopback `127.0.0.1:17733` (:130-140) as, verbatim:

```
set fs_game ""
set codol_zoneType zm
set g_gametype zm
map zm_zombie_training
```

`g_gametype` is the plain string `zm`, from the room descriptor's
`desc[23] = crc32("zm")`. `common_gametype_zm` is derived at :110 but is **not**
sent — the server derives it from `codol_zoneType`. `dispatch()`'s docstring
(:154-163) warns never to set `mapname` first; the `set mapname <level>` line in
the `1-START-LOBBY.cmd:224` comment is stale and is not sent.

Corroborated live by `alpha0022/captures/wiretap-20260915.jsonl:5519`
(`map=zm_zombie_training gametype=zm type=zm zone=common_gametype_zm fs_game=''`),
the room latch at `:1302` (`ROOM INFO zm_zombie_training/zm maxp=1`), and the
client's own load telemetry at `:5534`
(`2485 common_mp | 2926 common_gametype_zm | 5673 zm_zombie_training`).

Classification tables: gametype → zone type at `alpha0022/map_handoff.py:205`
(`ZONE_CATEGORY = {"coop":"coop","zm":"zm"}`, default `mp`, consumed by
`zone_category()` :382-386); map/gametype prefix → zone type at
`alpha0022/zone_crc.py:381-405` (`zone_type_for()`, documented as reproducing
C1's `0x612850` prefix test); `FS_CRC_BY_TYPE` at `map_handoff.py:891-895`.
The widening itself is one hunk: `1-START-LOBBY.cmd:219`,
`set CODOL_MAP_TYPES=mp` → `mp,coop,zm`.

### 3.8 Prior recorded work — cite, do not re-derive

`docs\` is thin on zombies and contains one stale line worth
correcting:

- `docs/CODOL_PORT.md:3270-3277` — the native checksum selector already uses the
  measured zm constant table; **`fs_crc(zm) = 0x801CEF02`**; `codol_zoneType` is
  separate from `g_gametype`.
- `docs/CODOL_PARITY_INVENTORY.md:271` — *"zm fs_crc never harvested"*. **Stale**;
  superseded by `CODOL_PORT.md:3273`.
- `docs/CODOL_PARITY_INVENTORY.md:286,296` — three zm zones, "no gametype",
  gametype fallback silent.
- `docs/CODOL_SCOREBOARD_CONTRACT.md:8,36` — C1 selects a **different scoreboard
  format** for gametype `zm` (command `4`, **seven** ints per row, vs MP's `b`
  with ten). A real zm gametype must feed that, not the MP scoreboard.
- `docs/CODOL_PLAYER_APPEARANCE.md:73,101,123,136-142` — faction token `zm`,
  `zmCharacterIndex`, `boo_zmcowboy_zm_m_00`.
- `docs/CODOL_SERVER_WEAPON_CONFIGSTRINGS.md:9` — coop/zm skip the MP pre-pass.
- `src/sv_main.c:3349-3350` — **`codol_animlistMask` already carries a zombie
  bit** ("human=1 dog=2 civilian=4 zombie=8"), feeding serverinfo key `2482`
  (`src/codol/snapshot/codol_sv_state.c:107`). The animtree wiring is present
  natively and untested under a real zm zone.

The substantive archive is in `alpha0022/docs/`, and it should be read before
any zombies work rather than re-derived:

- **`zombies_gameplay_plan.md`** — `:18-19` the fs_crc; `:20-21` the client
  *holds* `CA_ACTIVE` on `zm_asylum_sh` (35 s / 954 snapshots, 0 crash);
  `:36-68` the three xanim walls and the reframe that the animations are
  resident and what is missing is the server-side driver; `:76-93` records that
  there is **no vendor zombies source in this tree** and recommends pulling T5
  as reference; `:104-123` a 9-stage plan; **`:312-321` STAGE 1 VERIFIED LIVE
  2026-09-02** — player spawned holding `coltanaconda_zm` (ammo 8|32), round HUD
  回合1 rendered, no `0x0047C1F7` fatal, enemy zombies T-posing.
- **`zombies_mode.md`** — `:593-595` const-configstring row counts (mp 2053 /
  coop 1803 / zm 1625); `:690-774` the zm table is self-consistent and mp
  model/weapon names are unusable under it; **`:1088-1148`** an exhaustive sweep
  of all 23,124 C1 strings finding **none** of magic box / pack-a-punch /
  juggernog / round manager, and the verdict *"'walk around a zombie map alive,
  alone, with a zm weapon' is a plumbing job. 'Zombies' is a from-scratch game
  mode."*; what *is* client-side: `ZOMBIE_ROUND` HUD fed by dvar `ui_hud_round`
  (drawn `0x00461A71`), `MPUI_REVIVES` replacing the deaths column
  (`0x00461666`/`0x004626AE`), and four stat fields
  (`laststand +0x3A38`, `downs +0x3394`, `revives +0x3398`, `headshots +0x339C`).
- **`zombies_lobby_handoff.md`**, **`actors_zombies.md`** (`:499` — no compiled
  `pathData` for `zm_zombie_training`), and **`server_functions_treyarch.md`**,
  which already maps T5 zombies onto this project section by section
  (`§2.1`-`§2.8` at `:123,133,142,152,166,173,188,196`; the required-builtin
  list at `:274-275`).

---

## 4. Behavioural reference: the T5 zombies script set

`D:\CoD\COD-GSC-Source\BO1-GSC` (mirrored at
`obj/reference/COD-GSC-Source/BO1-GSC`) is a zombies-focused BO1 rawfile dump:
**55 `_zombiemode*.gsc`, 33,189 lines.** Largest: `_zombiemode.gsc` 3837,
`_zombiemode_spawner.gsc` 2371, `_zombiemode_blockers.gsc` 1818,
`_zombiemode_weapons.gsc` 1778, `_zombiemode_utility.gsc` 1612.

| Concern | T5 owner | Notes |
|---|---|---|
| gametype entry / callbacks | `maps/_callbacksetup.gsc:9-130`, `maps/_callbackglobal.gsc` | T5 has **no `zm.gsc`-style gametype file** — `Callback_StartGameType` (`_callbackglobal.gsc:78`) is empty and the mode is entered from the *level* script calling `maps\_zombiemode::main()`. CoDOL's engine demands a gametype script (§3.2), so this repo needs both. |
| core init | `maps/_zombiemode.gsc:14-120` | `level.zombiemode = true`, `SetAILimit(24)` (:65-68), then 18 subsystem `init()`s (:70-88). `init_function_overrides():532-554` re-points shared callbacks at zombie versions. |
| utility | `maps/_zombiemode_utility.gsc` | `spawn_zombie():40-58` is the actual actor spawn (`StalingradSpawn()` / `DoSpawn()`); `get_enemy_count():29-39` via `GetAiSpeciesArray`. |
| spawner / AI | `maps/_zombiemode_spawner.gsc` | `zombie_spawn_init():41-96`, `zombie_think():180` → `tear_into_building():349` → `find_flesh():1838`; pathing `:246,287,325,1924`; gibs/death `:1279,1513,1593`. |
| round logic | `maps/_zombiemode.gsc:1827-2361` | `round_spawning():1827-1963` with `ai_calculate_health():1838` and the ×round×0.15 scaling past round 10; `round_think():2257`, `round_wait():2361`, chalk HUD `:2104-2110`. |
| points | `maps/_zombiemode_score.gsc` (373 L) | Single entry `player_add_points():13-119`; bonuses `:120`; debits `:187`; penalties `:206,214`. |
| power-ups | `maps/_zombiemode_powerups.gsc` (1080 L) | `watch_for_drop():244` is the drop rule; nuke/insta-kill/double-points at `:743,833,858`. |
| mystery box | `maps/_zombiemode_weapons.gsc:470-1180` | `treasure_chest_init():470-503` reads `getEntArray("treasure_chest_use","targetname")` — the exact targetname the CODOL map ships (§3.6). |
| perk machines / PaP | `maps/_zombiemode_perks.gsc` (1334 L) | Generic `vending_trigger_think():668`; per-perk `turn_*_on()` `:471-620`; Pack-a-Punch `:250-398`. |
| doors / debris / boards | `maps/_zombiemode_blockers.gsc` (1818 L) + `_zombiemode_zone_manager.gsc` (377 L) | `door_buy():120`, `debris_think():492`, `blocker_trigger_think():730`. `disconnect_paths_when_done():476` edits the AI graph — a no-op without AI. |
| downs / revive | `maps/_laststand.gsc` | State machine `PlayerLastStand():55`, `Laststand_Bleedout():191`, `revive_trigger_think():233`, `revive_do_revive():333`, `auto_revive():405`. |
| animation | `animscripts/zombie_*.gsc` (22 files) + `_zombiemode.gsc:668-886` | Clip tables are GSC; the state machine is engine-driven per actor per frame (`setanimknob*`, `animmode`, `orientmode`, root motion), all `#using_animtree("generic_human")`. |

Native side, `D:\CoD\OpenBLOPS\Game\Server\game\`: `actor_*.cpp` (state, senses,
threat, pain, death, corpse, physics, orientation), **`actor_spawner.cpp:107
SpawnActor()`** and `:317 SP_actor_spawner()`, `pathnode.cpp` (4149 L) +
`actor_navigation.cpp` (6628 L), `actor_animapi.cpp` +
`Engine/Animation/xanim/`. GSC exposure in `game_mp/g_scr_main_mp.cpp`
(`ScrCmd_SpawnActor:9886`, registered `:21707`; `dospawn`/`StalingradSpawn`
`:21056`). Note `findpath` is an unimplemented stub even in OpenBLOPS
(`:17889`).

**Portability verdict.** Pure GSC, landing on a IW4OL-derived server as-is
modulo a handful of builtins (`setmaxhealth`, `getstruct(array)`, `getclosest`,
`dodamage`, `startrevive`/`stoprevive`/`reviveplayer`, `setstance`,
`connectpaths`/`disconnectpaths` as no-ops): round logic, points, power-ups,
mystery box, perk machines, doors/debris/board repair, and the downed/bleed-out
*state*. Native-dependent, and not portable without an actor subsystem: the
spawner itself (IW4OL has no actor entity type), pathing (`setgoalnode`,
engine A*, and CODOL ships no compiled `pathData` — only the 326
`node_pathnode` entities of §3.6), the animscript state machine (the T-pose
ceiling), melee/gibs/ragdoll, the revive *interaction* builtins, and the entire
client-FX `.csc` channel (CODOL has no CSC VM; there are zero `.csc` files in
any zone).

---

## 5. Gap list

"Owner" is the file that would hold the work in this repo.

| Concern | State | Owner |
|---|---|---|
| zm gametype script | **MISSING** — server silently falls back to `dm` (§3.2) | `scripts/codol/maps/mp/gametypes/zm.gsc` |
| zm level script | **MISSING** in every zone and every script root (§3.4) | `scripts/codol/maps/mp/zm_zombie_training.gsc` |
| map fx modules | **PRESENT** in the zone as rawfiles (`maps/mp/zm_zombie_training_fx.gsc`, `maps/createfx/zm_zombie_training_fx.gsc`) | zone; called from the level script |
| `.vision` / `.sun` for this map | **MISSING from the zone** — unlike every mp zone and the other two zm zones (§3.5) | risk, §7 |
| `isSP()` / MP-predicate correctness on a non-`mp_` map | **PRESENT** (this pass) | `scripts/codol/maps/mp/_load.gsc:9-31` + `_gamelogic.gsc:1259` |
| Spawn points | **PRESENT** in the zone; MP classnames, one per team, no spreading | zone MapEnts → `_spawnlogic.gsc` |
| Mode tuning data | **PRESENT and unused** — `mp/zombiemode.csv`, 106 rows, health/spawn/score/penalty/power-up timings (§3.4) | reachable now via `tableLookup` |
| zm rank/bonus tables | **PRESENT** — `mp/zmranktable.csv`, `mp/zmmatchbonus.csv` | zone |
| Callbacks | **PARTIAL** — the MP chain runs and is correct in shape; `PlayerKilled`/`PlayerLastStand` need zombies semantics | `zm.gsc` + `_gamelogic.gsc` (parent-owned) |
| `_zombiemode.gsc` equivalent (init, zones, round loop) | **MISSING** | `scripts/codol/maps/mp/gametypes/_zombiemode.gsc` |
| `_zombiemode_utility.gsc` equivalent | **MISSING** | `…/_zombiemode_utility.gsc` |
| Round logic + round HUD | **MISSING** server-side. The client half exists: `ZOMBIE_ROUND` HUD fed by dvar `ui_hud_round`, drawn at `0x00461A71`, and it **rendered live** under the old Python server | `…/_zombiemode.gsc` |
| Points economy | **MISSING**; all constants already in `mp/zombiemode.csv` | `…/_zombiemode.gsc` |
| Barricade repair, purchasable doors/debris | **MISSING**; entities present (`zombie_barrier`, `zombie_debris`, `zm_door_*`, `elec_door_*`) | `…/_zombiemode.gsc` |
| Power switch | **MISSING**; entities present (`elec_switch`, `use_elec_switch`, `power_*_fx`) | `…/_zombiemode.gsc` |
| Mystery box | **MISSING**; entities present under the exact T5 targetnames (`treasure_chest_use`, `chest_lid`, `chest_origin`), and `animtrees/zm_magic_box.atr` ships in the zone | `…/_zombiemode_weapons.gsc` |
| Perk machines / Pack-a-Punch | **MISSING**; entities present (`vending_doubletap`, `vending_sleight`, `speed_drink`, `weapon_upgrade` ×8) | `…/_zombiemode_perks.gsc` |
| Power-ups | **MISSING**; `zombie_care_package` present | `…/_zombiemode_powerups.gsc` |
| Downed / last stand / revive | **MISSING**. `CodeCallback_PlayerLastStand` is already wired (`src/scr_vm_main.c:1308`), and the client already replaces the deaths column with `MPUI_REVIVES` under zm | `zm.gsc` / `_laststand` port |
| zm scoreboard | **MISSING** — C1 uses a different format under `zm` (command `4`, seven ints/row; `docs/CODOL_SCOREBOARD_CONTRACT.md:8,36`) | `src/codol/…` scoreboard writer |
| Zombie spawners / AI | **MISSING**, and the hard item. 51 `zombie_spawner` structs and three `actor_zombie_*` classnames exist in the map; a IW4OL-derived server has no actor entity, no AI pathing, no animscript runtime | native `src/codol/…` (new) + a GSC façade |
| Zombie animation | **MISSING / known wall.** Prior work reached armed play with zombies T-posing. `animlists/common_zombie.animlist` and `animtrees/zombie_dog.atr` ship in the zone, and `codol_animlistMask` already has a zombie bit (`src/sv_main.c:3349-3350`) feeding serverinfo `2482` | native |
| Pathing data | **MISSING** — 326 `node_pathnode` entities, but the compiled `pathData` payload is recorded absent (`alpha0022/docs/actors_zombies.md:499`) | native |
| zm factions / teams | **PARTIAL / wrong** — the `basemaps.arena` entry has no `allieschar`/`axischar`, so `_gamelogic.gsc:1281-1298` falls back to default MP factions | `zm.gsc` |
| zm weapons | **PARTIAL** — `coltanaconda_zm` published and equipped live under the old server; `mp/zombiemode.csv` names the full intended set | `src/codol/…` weapon publication |

---

## 6. Recommended order

1. **Confirm the two `level.isSP` edits compile and that a zm handoff gets past
   `_load`.** Nothing below is testable until a zm map boots. This step is
   verification of work already written, not new work.
2. **`scripts/codol/maps/mp/zm_zombie_training.gsc`** — the minimal IW4
   level-script shape, modelled on `scripts/codol/maps/mp/mp_killhouse_sh.gsc`:
   call the zone's own `maps\mp\zm_zombie_training_fx::main()` (it exists,
   §3.4), then `maps\mp\_load::main()`, then compass/ambience/team sides. Do
   this *second*, not first, because it is the edit that would have reinstated
   the §1 crash without §1(b). Watch for the missing `.vision` (§3.5, §7).
3. **`scripts/codol/maps/mp/gametypes/zm.gsc`** — so `GScr_LoadGameTypeScript`
   stops silently substituting `dm` and `level.gametype`/`scr_zm_*` stop being a
   coincidence. Non-team-based (the playlist has no `teambased` line, §3.1),
   using the map's existing DM/TDM spawns, registering the dvar set, setting
   `level.onStartGameType` / `getSpawnPoint`.
4. **Round + points loop**, driven from `mp/zombiemode.csv` rather than
   hardcoded numbers. Pure GSC, needs no AI, and independently observable: a
   round counter that advances and points that accrue prove the loop with zero
   zombies in the world. The client's `ui_hud_round` HUD is already known to
   render.
5. **Static interactables** — power switch, doors/debris, wall-buys, mystery
   box, perk machines, Pack-a-Punch. All are `use` triggers over entities the
   map already ships under the exact T5 targetnames (§3.6), all pure GSC, all
   observable without AI.
6. **Zombie spawners and AI.** The native cliff: actor entities, pathing (with
   no compiled `pathData` to path over) and animscripts. Scope against
   `OpenBLOPS/Game/Server/game/actor_*.cpp`, `pathnode.cpp` and
   `actor_navigation.cpp` before writing anything, and expect the T-pose wall to
   be the first thing hit even once spawning works.
7. **Downs/revive**, then power-ups, last — both only mean something once
   zombies can kill a player.

The ordering principle: steps 3-5 are GSC-only and each produces a visible
change in the client with no engine work; step 6 is the one that needs new
native subsystems. Do not reorder 6 earlier on the theory that "zombies are the
point" — every other item is blocked behind a booting zm match, not behind AI.

---

## 7. What is still only reasoned

- **That §1(b) is necessary.** The call-ordering argument is read off
  `_callbacksetup.gsc:7-8` and the two level scripts that call
  `maps\mp\_load::main()` from their own `main()`. It has not been demonstrated
  by adding a zm level script and watching the crash return.
- **That the server now survives a zm handoff past `_load`.** Neither edit has
  been compiled by the VM. The audit found no further fatal predicate in the
  274-file closure and `_spawnlogic`'s `AbortLevel` paths are satisfied by the
  MapEnts — but "no further crash" is a prediction.
- **Audit row 18 (missing `.vision`/`.sun` for `zm_zombie_training`).** That the
  rawfiles are absent from the zone is extracted fact; that
  `VisionSetNaked("zm_zombie_training", 0)` will misbehave is inference. It was
  not reached in the observed transcript — the crash happened at
  `_load.gsc:55`, and the vision calls are at `:70,74`, fifteen lines later. If
  a zm boot produces a black or unlit world rather than a script error, check
  this first.
- **The most likely next failure**, in order: (i) the vision/sun gap above;
  (ii) nothing at all, with the match running as silent deathmatch on a zombies
  map, because §3.2's fallback is quiet by design.
- Every §5 entry marked PARTIAL. The MISSING entries are verified absences (the
  files are not on disk, or the rawfile is not in any zone); the PARTIAL ones
  are judgements about behaviour that was not exercised this pass.

---

# APPENDED 2026-09-15 (second pass): per-type zones, per-type scripts, fs_game

Everything from §1 to §7 above is unchanged and still stands. This appendix
adds three things that pass did not cover — per-asset-category zone mounting,
per-asset-category script sets, and the `fs_game` question — and closes §5's
first two MISSING rows (`zm gametype script`, `zm level script`).

**Evidence class for this appendix, up front:**

- **Built and tested**: the native changes compile clean into
  `bin/codol_dedrun_next.exe` (SHA-256
  `a95cae94d1dfb9625016ca4a107f81694cff67f598c85548789cdf33c7a3d91e`, 6,489,468
  bytes; `--codol-info` exits 0), and `make -j12 test-codol` reaches its known
  pre-existing `test_codol_native` link failure at `makefile:445` with 27 PASS
  lines and nothing else failing before it. `tests/test_codol_script_source.c`
  gained coverage for the new per-category root and passes standalone (the make
  target never reaches line 476 because 445 stops it — that is pre-existing).
- **Read off disk / extracted offline**: the zone-file inventory of
  `client_shipRetail/chinese` (90 `.ff`), the registry analysis in §8, the
  `fs_game` evidence in §10, and every file:line citation.
- **Written, not run by the VM**: the four new GSC files in §9.3. No GSC in this
  appendix has been compiled by the script VM.
- **NOT LIVE-VERIFIED.** This pass started no server, no lobby and no client,
  and killed no process. The user's `bin\codol_dedrun.exe` (PID 90248 at the
  time of writing) and the Python lobby were left running and untouched; the
  build went to the *other* executable name for exactly that reason. Every
  "this now does X" below is a claim about source, not an observation. §11 is
  the checklist for turning them into observations.

---

## 8. Zone mounting per asset category

### 8.1 What was already correct

`CODOL_LoadMapArchives` (`src/codol/assets/codol_asset_commands.c`) was already
genuinely per-category and no change to its zone *list* was needed:

- It builds `common_gametype_<type>`, `localized_common_gametype_<type>`, the
  map zone, and for a `coop_<mode>_mp_<map>` name also the underlying
  `mp_<map>` zone, each followed by its `patch_*` sibling when the file exists.
  All six zm files and all six coop files exist on disk — the full inventory is
  `common_gametype_{mp,coop,zm}.ff`, `patch_common_gametype_{mp,coop,zm}.ff`,
  `localized_common_gametype_{mp,coop,zm}.ff`,
  `patch_localized_common_gametype_{mp,coop,zm}.ff` out of the 90 `.ff` files in
  `client_shipRetail/chinese`. No zone name was invented.
- **The startup set is not multiplayer-gametype content and does not leak.**
  `CODOL_LoadStartupArchives` mounts a hardcoded nine —
  `code_post_gfx_default_mp`, `code_post_gfx_mp`, `patch_code_post_gfx_mp`,
  `localized_code_post_gfx_mp`, `patch_localized_code_post_gfx_mp`,
  `common_mp`, `patch_common_mp`, `localized_common_mp`,
  `patch_localized_common_mp`. The `_mp` suffix there names the multiplayer
  *executable's* base zones, shared by all three categories: the zone build log
  inside `zm_zombie_training.ff` itself records the client's chain as
  `code_post_gfx_mp` → `common_mp` → `common_gametype_zm` → map zone (§3.4),
  and the client's live load telemetry agrees
  (`alpha0022/captures/wiretap-20260915.jsonl:5534`,
  `2485 common_mp | 2926 common_gametype_zm | 5673 zm_zombie_training`).
- **Retired archives are not a leak path.** Mounting a new map replaces logical
  group 1 wholesale: `mount_archives` splices *every* group-1 entry out of the
  `archives` list onto `retired_archives`
  (`src/codol/assets/codol_asset_registry.c:311-319`), and every by-name
  resolver walks `archives` only — `find_dependency_definition` (`:612-640`),
  `CODOL_LoadEngineStringTable` (`:2088`), `CODOL_LoadEngineRawFile` (`:2047`),
  the model/material/effect walks at `:1726,:1759,:1820`. The two functions that
  read `retired_archives` (`:899` and `codol_weapon_compose.c:639-647`) match on
  pointer identity, never on a name — they are use-after-free guards for objects
  that already hold a `WeaponDef*`. `codol_load_blocks.h:167-169` states the
  rule: *"Old group assets stop participating in lookup."* So `map
  mp_killhouse_sh` followed by `map zm_zombie_training` cannot resolve an MP
  asset by name during the zm match, and both gametype zones can never be live
  at once (both are group 1; only the `codol_loadzones` console command can
  mount at group 0).
- The reuse fast path compares map **and** category
  (`codol_asset_commands.c`, `mounted_map`/`mounted_zone`), so it cannot serve
  mp zones to a zm reload of the same map name.

### 8.2 What was broken, and the fix

**`codol_zoneType` never took effect on a running server.** It is registered
`CVAR_LATCH` exactly once, in `SV_InitCvarsOnce` (`src/sv_main.c:3341`). The
lobby sets it over rcon, and `Cvar_Set_f` calls `Cvar_Set2(..., qfalse)`
(`src/cvar.c:1727`); for an unforced set of a latched var `Cvar_SetVariant`
prints *"will be changed upon restarting"* and writes only `latchedString`,
leaving `var->string` alone (`src/cvar.c:825-829`). Nothing promoted it. The
engine's promotion point is *re-registration* — `Cvar_Register` captures the
latched value and re-applies it with `force=qtrue` (`src/cvar.c:686`) — which is
precisely why `g_gametype`, latched at the same `SV_InitCvarsOnce` site, does
work: `GScr_LoadGameTypeScript` re-registers it once per map
(`src/scr_vm_main.c`). `codol_zoneType` never was.

Consequence: a live server handed `set codol_zoneType zm` / `map
zm_zombie_training` would mount `common_gametype_mp` and install
`mp/constConfigStrings_mp.csv` (2053 rows) against a zm map, and say so only in
an informational `CoDOL native map archives mounted: N (zm_zombie_training, mp)`
line. That is also a gamestate the client cannot agree with: `CODOL_WriteGamestate`
puts the category and its `const_crc` on the wire
(`src/codol/snapshot/codol_configstrings.c`), and the client derives its own from
the map name.

Reachability caveat, stated as such: the §1 transcript's
`vehicle_mig29_desert is not in any mounted zone` warning suggests *that*
particular run did have the zm zones mounted (those MP killstreak models do not
warn under `mp_killhouse_sh`), so that session probably set the category before
registration, at startup. The defect is in the code either way and a rcon
handoff on a warm server hits it.

Two changes, belt and braces:

1. **`src/sv_main.c`, top of `SV_SpawnServer`** (just after
   `Sys_BeginLoadThreadPriorities()`, ~`:5195`): re-register `codol_zoneType`
   with its original default and flags, so the latched value is promoted before
   any of `:5325` (map mount), `:5329` (`constConfigStrings_<type>.csv`),
   `:5330`/`:5332`/`:5337` and `:3554` (gamestate) read it. This is the engine's
   own idiom, the same one `g_gametype` gets, and a map spawn *is* the restart
   the latch is waiting for. `CVAR_LATCH` is kept: the value must not move under
   a connected client, and it does not — only a map spawn can move it.

2. **`src/codol/assets/codol_asset_commands.c`, head of
   `CODOL_LoadMapArchives` (`:283` and `:296-310`)**: a new
   `CODOL_ZoneTypeForMapName()` reproduces C1's own prefix test at `0x612850` —
   case-insensitive `"zm"` (2 chars), then `"coop"` (4), default `"mp"`, as
   documented and reproduced at `alpha0022/zone_crc.py:381-405` — and the mount
   is **refused** with a `Com_PrintError` when `codol_zoneType` contradicts the
   map name. The caller already turns a `0` return into
   `Com_Error(ERR_DROP, "CoDOL map archive loading failed: %s")`
   (`src/sv_main.c:5325-5326`). The map name is the authority because it is what
   the *client* uses to pick its zone chain, its constant-configstring namespace
   and its fs_crc; a server that disagrees is wrong on all three, and a loud
   refusal beats a quiet wrong mount.

Neither change alters which zones a correctly-dispatched match mounts. Together
they make it impossible for a zm map to mount the mp gametype zones.

---

## 9. Script sets per asset category

### 9.1 The resolution rule (`src/codol/script/codol_script_source.c`)

The resolver gained one layer, above the existing native overlay:

```
<native_overlay>/<category>/<name>        <-- NEW
<native_overlay>/<name>
<overlay>/<name>
<base>/mp/<name>
<base>/<name>
```

`CODOL_ReadScriptSourceWithNativeOverlayForZone()` is the new entry point;
`CODOL_ReadScriptSourceWithNativeOverlay()` and `CODOL_ReadScriptSource()` are
now thin wrappers that pass a NULL category, so every existing caller and every
unit fixture keeps its exact behaviour. The category prefix is accepted only as
plain lowercase ASCII short enough that it cannot push a legal script name past
the path buffer, so the traversal rules that already guard `name` still hold.

`src/cscr_parser.cpp` (`Scr_ReadFile`, ~`:581`) passes `CODOL_ServerZoneType()`
— the mounted map's category, latched by `CODOL_SetServerMapIdentity` during map
setup, not a dvar a later command could relatch. Before a map identity exists it
is NULL and the layer is skipped.

**Why this and not per-category module names.** The engine asks for the same
module names for every category and always will:
`maps/mp/gametypes/_callbacksetup` is hardcoded six times in
`GScr_LoadGameTypeScript` (`src/scr_vm_main.c:1303-1312` in the pre-change
numbering) and `maps/mp/<mapname>` once in `GScr_LoadScripts`. The CoDOL zones
use that same `maps/mp/` namespace for their own rawfiles even under zm
(`maps/mp/zm_zombie_training_fx.gsc`, §3.4). So the module name is the wrong
place to encode the category, and the *file* is the right one. The cost is one
`fopen` miss per script under `mp` (there is no `scripts/codol/mp/` directory);
the multiplayer resolution order is otherwise byte-for-byte what it was.

Covered by `tests/test_codol_script_source.c`: the category root wins when the
file exists, misses cleanly when it does not, is invisible to another category
and to the no-category callers, and rejects `""`, `".."`, `"zm/"`, `"ZM"` and
`"zm1"`.

### 9.2 Gating the gametype chain (`src/scr_vm_main.c`)

`GScr_LoadGameTypeScript` now consults a table keyed on
`CODOL_ServerZoneType()`:

| category | forced script | fallback |
|---|---|---|
| `mp`   | — (honours `g_gametype`; `combat`/`tdm` → `war`) | `dm` |
| `coop` | — (honours `g_gametype`) | `coop` |
| `zm`   | `zm` | `zm` |

Three behaviour changes, all confined to `CODOL_SERVER`:

- **The `combat`/`tdm` → `war` translation is now multiplayer-only.** No other
  category ships either playlist name.
- **`zm` pins the script name.** C1's `mp_playlists.ff` maps every `zm_*` map to
  `gametype zm` with `script zm`, `mp/gametypescptable.csv` lists `zm` once and
  non-team-based, and `mp/basemaps.arena` gives every `zm_*` map
  `gametype "zm"` (§3.1). A mismatching `g_gametype` is printed, not obeyed.
- **The `dm` fallback is refused outside `mp`.** When the fallback equals what
  was already tried, the loader raises `Com_Error(ERR_DROP)` naming the missing
  script and the directory it belongs in, instead of loading a multiplayer
  gametype. This kills the failure mode §3.2 documented and
  `docs/CODOL_PARITY_INVENTORY.md:296` recorded: `g_gametype zm` silently
  running IW4 free-for-all deathmatch on a zombies map.

`GScr_LoadScripts` keeps `maps/mp/<mapname>` as the level-script module name —
the per-category *root* is what makes the file per-category, per §9.1 — and adds
a diagnostic naming the exact path a missing level script should live at
(`scripts/codol/<category>/maps/mp/<map>.gsc`). Absence stays non-fatal, which
is IW4's contract.

The retained non-CODOL build is unchanged: it keeps its single `dm` fallback and
its `Cvar_SetString(sv_g_gametype, "dm")`.

### 9.3 The zm script set (written, never compiled by the VM)

Four new files under `scripts/codol/zm/`. Their whole-closure module graph is
`zm → {_callbacksetup, _zombiemode}` and `_callbacksetup → _zombiemode`:
**zero references to any multiplayer module, and no `#include` at all.** That is
the point — a GSC `file::function` reference is a compile-time dependency, so
the multiplayer `_callbacksetup`'s `SetDefaultCallbacks` naming `_gamelogic`,
`_playerlogic`, `_damage` and `_hostmigration` is what drags the entire
multiplayer chain in, and with it the killstreak precaches C1 reported as *"not
in any mounted zone"* under zm.

| File | Role |
|---|---|
| `zm/maps/mp/gametypes/_callbacksetup.gsc` | The six labels the engine binds with `errorIfMissing=1`, plus `SetupCallbacks`/`SetDefaultCallbacks`/`SetupDamageFlags`. Shape from `vendor/iw4/maps/mp/gametypes/_callbacksetup.gsc`; host-migration callbacks dropped (this server has none). |
| `zm/maps/mp/gametypes/zm.gsc` | The client-contracted rules script (§3.1). Two lines: `SetupCallbacks()`, `_zombiemode::init()`. |
| `zm/maps/mp/gametypes/_zombiemode.gsc` | Tuning, callbacks, spawn. The zm counterpart of `_gamelogic`/`_playerlogic`/`_damage`, reduced to the boot chain. |
| `zm/maps/mp/zm_zombie_training.gsc` | Level script. Sets `level.isSP = false` and documents, per item, what is deliberately absent. |

**Tuning is read, not hardcoded.** `_zombiemode::set_zombie_var()` is T5's
`_zombiemode_utility.gsc:1331-1347` contract verbatim — `tableLookup(
"mp/zombiemode.csv", 0, <row>, 1 )`, table value wins when the row exists and is
non-empty, otherwise the supplied default stands — and `mp/zombiemode.csv` is
the 106-row table that already ships in `common_gametype_zm.ff` (§3.4). Column 1
(`EASY`) is T5's own default for `set_zombie_var`; the difficulty selector is not
part of the boot chain. `CODOL_Scr_TableLookup` returns `""` for a missing table
or row and never errors
(`src/codol/script/codol_script_table.c:77-98`), so an absent table degrades to
the defaults instead of failing the boot. Rows consumed today:
`game_start_delay`, `starting_lives`, `zombie_score_start_1p`,
`zombie_starting_weapon`, and `player_starting_health` (default 100 —
deliberately **not** `zombie_health_start`, which is the AI's health).

**The starting weapon is probed, not guessed.** `resolveStartWeapon()` tries
`zombie_starting_weapon` from the table, then `coltanaconda_zm` (the one zm
weapon this client is recorded as having accepted live, ammo 8|32,
`alpha0022/docs/zombies_gameplay_plan.md:312-321`), then T5's `m1911_zm`.
`precacheItem()` is the probe: it is a silent no-op for a weapon in no mounted
zone (`src/codol/script/codol_script_precache.c:24-27`) and it is what registers
the definition, so `getWeaponIndexFromName()` only answers non-zero afterwards
for a name the zm zones really carry. It runs in `Callback_StartGameType`, the
precache window the multiplayer `_class::init()` demonstrably uses today.

**Spawning** uses the map's own multiplayer spawn classnames —
`mp_tdm_spawn_allies_start`, `mp_dm_spawn`, `mp_tdm_spawn`, `info_player_start`,
in that order — because that is what `zm_zombie_training` actually ships (§3.6),
one of each, with no `script_gametype` key on worldspawn. One point per
classname means no spawn spreading; picking randomly among whatever exists is
honest about that and works unchanged on `zm_prototype_sh` and `zm_asylum_sh`.
Character selection goes through `self codol_applyProfileCharacter("zm", weapon)`,
and the native selector already forces the zm faction whenever a zm zone is
mounted (`src/codol/player/codol_player_appearance.c:184-188`).

**`level.isSP = false` is set in three places** — `_zombiemode::init()`,
`_zombiemode::Callback_StartGameType()` and the level script's `main()` — for
exactly the reason §1 established. The zm chain does not go through
`maps\mp\_load` or `_gamelogic`, so neither of the existing assignments is on
its path, and the level script runs before `CodeCallback_StartGameType`.

**Three deliberate omissions, each a trap avoided rather than an oversight:**

- **`self.statusicon` is only ever cleared, never named.** The setter resolves
  the string against the precached status-icon configstrings and `Scr_Error`s —
  fatally — on a name that was not precached
  (`GScr_GetStatusIconIndex`, `src/g_scr_main_mp.cpp:165-183`), and the
  precaching is done by the multiplayer chain this script set exists not to
  load. The empty string is the documented zero index.
- **No `VisionSetNaked` / `VisionSetPain` anywhere.** `zm_zombie_training.ff`
  ships neither `vision/zm_zombie_training.vision` nor
  `sun/zm_zombie_training.sun`, where `zm_prototype_sh.ff`, `zm_asylum_sh.ff`
  and every mp zone ship both. This is audit row 18 / §7, and the multiplayer
  `_load.gsc:70,74` is where it would have been asked. The zm chain never asks.
- **No `maps\mp\zm_zombie_training_fx::main()`.** The effects module *does*
  exist, as a rawfile inside the map zone. Whether `Scr_ReadFile` can reach a
  CoDOL zone rawfile is unproven: its fastfile fallback goes through the
  retained `DB_FindXAssetHeader` path, not the CoDOL archive registry, and the
  only rawfile category wired to the registry in `Scr_ReadFile` is `animtrees/`
  (`src/cscr_parser.cpp`). A `file::function` call is a compile-time dependency,
  so being wrong about it is a fatal load error, not a missing effect. Effects
  are cosmetic; this is left for a pass that can test the rawfile path live.

### 9.4 Deliberately left for the follow-on workstream

Rounds, the points economy, barricades and purchasable doors/debris, the power
switch, the mystery box, perk machines and Pack-a-Punch, power-ups, the
downed/bleed-out/revive state machine, the zm scoreboard format (C1 command `4`,
seven ints per row), zombie spawners, AI, pathing and animation. All of §5's
remaining MISSING rows, in §6's order. `Callback_PlayerLastStand` is registered
because the engine binds it with `errorIfMissing=1`
(`src/scr_vm_main.c`), and forwards to the killed path; nothing in this script
set grants last-stand eligibility, so it is unreachable today.

---

## 10. `fs_game` per asset category: empty is correct, nothing changed

**Verdict: `fs_game` must stay empty for `mp`, `coop` and `zm`. No lobby file
was modified, and no `.pre-cod4x` backup was needed.**

The strongest evidence is a **measured capture** — a real decrypted C1 connect
packet, `alpha0022/_scratch/gs-20260902-0222.out.log:90`:

```
connect 79a6c4813004f32e "\cl_paused\0\name\Chud\xuid\...\natType\3\rank\30\clan\0000000000000000\2490\-1157214325\checksum\-58589618\challenge\1337\statver\220 3841806872\quickmatched\1\invited\0\csi\1\session\69421\partyid\0\qport\-27166\onlineStats\0"
```

There is no `fs_game` key and no `1006` key in the client's userinfo. The client
has nothing to compare a server `fs_game` against and the server has nothing to
echo back.

Corroborating, by class:

- **Source.** The CoDOL connect response carries no `fs_game`:
  `src/codol/net/codol_connect.c:91` sends
  `"connectResponse \\mapname\\%s\\gametype\\%s\\sv_maxclients\\%u\\protocol\\1\\shortversion\\1.1.1.13"`,
  and stock CoD4's `NET_OutOfBandPrint(..., "connectResponse %s", fs_gameDirVar->string)`
  (`src/sv_client.c:654`) is compiled out under `CODOL_SERVER` (`:640-641`).
  `CODOL_WriteGamestate` (`src/codol/snapshot/codol_configstrings.c:281-308`)
  writes map, **zone_type** and **const_crc** — category and integrity are
  carried by those two, both of which the lobby already sets correctly — and has
  no `fs_game` slot. `CODOL_ReadConnectUserinfo` (`codol_connect.c:35-64`)
  inspects only `xuid`. CS[1], the systeminfo string that would carry
  `\fs_game\`, is never sent on this build.
- **Source.** Asset mounting is driven by `codol_zoneType` and `codol_zonePath`,
  never by `fs_game` (`CODOL_BuildZonePath`, §8.1).
- **C1 image scan.** `alpha0022/docs/rebuild_step4_dvars.md:1055-1057`: the
  strings `fs_game`, `sv_pure`, `sv_referencedIwds`, `sv_referencedFFNames`,
  `FS_Restart`, `FS_ConditionalRestart` *"do not exist anywhere in the image"*;
  the filesystem restart on this build is driven by the gamestate's
  `checksumFeed`. The measured dvar table `alpha0022/docs/BASE.md:49` records
  numeric dvar 1006's default as `""` (registration `0x00617990`).
- **A non-empty value would break the server.** `FS_GameDirDomainFunc`
  (`src/filesystem.c:2745-2761`) accepts only the empty string or
  `mods/<something>` and `Com_Error(ERR_DROP)`s on anything else — so
  `set fs_game "zm"` over rcon would drop the server at that line. A legal
  `mods/x` value would redirect zone lookup away from
  `client_shipRetail/chinese`, where the archives actually are.
- **Live, per category.** mp: many times with `fs_game=''` (e.g.
  `alpha0022/captures/wiretap-20260915.jsonl:144`). zm: §3.7 above, corroborated
  at `:5519` and by the client's own load telemetry at `:5534`. coop: never
  started live, so coop is **inference** — identical code path, same empty
  connect.

Current configuration, unchanged: `CODOL_MATCH_FS_GAME_MP`, `_COOP` and `_ZM`
are all commented out at `1-START-LOBBY.cmd:234-236`, under a comment at `:227`
that already records the measured empty default, so
`match_server_control.py:48-49` falls through to `""` and `plan()` emits
`set fs_game ""` at `:114`. That is right, and the right change is none.

Unrelated staleness noticed and **not** touched: `1-START-LOBBY.cmd:223-224`
still documents a `set mapname <level>` rcon line that `plan()` does not send —
the same staleness §3.7 already records.

---

## 11. How to verify this live (the user must do this; this pass could not)

The server the user is running is `bin\codol_dedrun.exe`. The new build is
`bin\codol_dedrun_next.exe`
(`a95cae94d1dfb9625016ca4a107f81694cff67f598c85548789cdf33c7a3d91e`). Switching
to it requires a server restart, which deafens any connected client — batch it
with anything else pending.

**1. Boot an mp match first and confirm nothing regressed.** Nothing in this
appendix should change a multiplayer match at all.

```
Select-String -Path bin\home\main\qconsole.log -Pattern 'map archives (mounted|reused)|inherited configstrings installed' | Select-Object -Last 4
```

Expect `... (mp_killhouse_sh, mp)` and `installed: 2053 (mp)` exactly as before.

**2. Dispatch a zm match from the lobby** (unchanged — `set fs_game ""` /
`set codol_zoneType zm` / `set g_gametype zm` / `map zm_zombie_training`), then:

```
Select-String -Path bin\home\main\qconsole.log -Pattern 'map archives mounted|inherited configstrings installed|is a .* map but codol_zoneType'
```

- **Pass:** `CoDOL native map archives mounted: 6 (zm_zombie_training, zm)` and
  `CoDOL inherited configstrings installed: 1625 (zm)`. The row count is the
  cheapest discriminator there is: mp is 2053, coop 1803, zm 1625
  (`alpha0022/docs/zombies_mode.md:593-595`).
- **Fail, loudly:** a `... is a 'zm' map but codol_zoneType is 'mp' ...` line
  followed by `CoDOL map archive loading failed`. That means §8.2's promotion
  did not take; report it rather than working around it.

**3. Confirm the multiplayer chain did not load.**

```
Select-String -Path bin\home\main\qconsole.log -Pattern 'not in any mounted zone|maps/mp/gametypes/dm|gametype zm is not available|Could not find label'
```

Expect **no** `vehicle_mig29_desert` / `projectile_cbu97_clusterbomb` warnings
(they came from the multiplayer killstreak precache), **no** `dm` fallback, and
**no** `Could not find label 'CodeCallback_ScriptCommand'` (the zm
`_callbacksetup` is loaded instead of IW4's, and that label is optional anyway).

**4. Confirm the zm scripts compiled and ran.**

```
Select-String -Path bin\home\main\qconsole.log -Pattern 'CoDOL zm:|no level script for'
```

Expect `CoDOL zm: starting weapon <name>` and **no** `no level script for
zm_zombie_training`. `CoDOL zm: no starting weapon is present in the mounted zm
zones` is a real finding, not a crash — report the line.

**5. Connect the client.** The bar for this pass is: gamestate published,
`CA_ACTIVE` held, no `Sys_Error`, player spawned somewhere in the level. The
round HUD should read 回合1 (`ui_hud_round` is set to 1 on spawn and never
advances yet — the round manager is the follow-on workstream). Zombies will not
exist. The world may be unlit or oddly lit, per audit row 18 — check §9.3's
vision note first if so.

**6. If it crashes**, `bin\sys_error.txt` plus the last 60 lines of
`qconsole.log` are the whole story; the script-runtime-error backtrace names the
file and line, and every file in the zm chain is under
`scripts\codol\zm\maps\mp\`.
