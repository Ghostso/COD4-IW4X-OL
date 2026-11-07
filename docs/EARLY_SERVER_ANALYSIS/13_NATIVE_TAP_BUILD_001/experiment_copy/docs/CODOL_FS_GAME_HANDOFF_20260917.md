# fs_game as the CoDOL asset-category carrier (mp | coop | zm)

2026-09-17. Scope: the server-side plumbing that makes `fs_game` select which gametype
zones mount and which script set compiles. Files changed: `src/sv_main.c`,
`src/filesystem.c`, `src/filesystem.h`. `src/sv_client.c` was audited and needs no change.

Every claim below is labelled **MEASURED** (read out of source, a build, or a log on
disk) or **INFERRED**.

---

## 1. Why an explicit carrier is required

**MEASURED** (`src/codol/assets/codol_asset_commands.c:299-325`): `CODOL_ZoneTypeForMapName()`
derives the category from the map name by prefix — `zm` (2 chars) → zm, `coop` (4) → coop,
else mp — mirroring C1 `0x612850`, and `CODOL_LoadMapArchives()` **refuses to mount** when
the derived category disagrees with `codol_zoneType`.

**MEASURED** (parent, from `alpha0022/map_handoff.py:60-120`, a 2026-08-19 client capture,
corroborated by the user's `main/console_mp-003/006/012.log`):

* A **zm** match's map name is category-bearing: `zm_zombie_training` loads
  `common_gametype_zm` + `zm_zombie_training` + `zm_zombie_training_load`.
* A **coop** match has *two* map spellings: the lobby/room-info playlist spelling
  `coop_training_mp_killhouse_sh`, and the **level zone the client actually loads**,
  `mp_killhouse_sh`, together with `common_gametype_coop`. `match_server_control.plan()`
  sends the *base* spelling, so the server receives `map mp_killhouse_sh`.

Consequence: `CODOL_ZoneTypeForMapName("mp_killhouse_sh")` returns `"mp"`, the guard refuses,
and `sv_main.c` turns the refusal into `Com_Error(ERR_DROP)`. **Coop is dead on arrival
today, at step one.** The category is therefore *not* derivable from the map name in
general, and an explicit carrier is required. `fs_game` is that carrier: the lobby already
sets it over rcon immediately before `map`.

## 2. Why the map name must be a FALLBACK, never a veto

**MEASURED** (parent, `bin/home/main/qconsole.prev-5f1c9db8.log`):

* Lines 3317-3324 — the only rcon dispatch in the log: `set fs_game ""` /
  `set codol_zoneType mp` / `set g_gametype war` / `map mp_rust`. Confirms fs_game carries
  nothing today and the lobby's four-command shape matches `match_server_control.plan()`.
* Line 9303 — `Server: zm_prototype_sh`: a map change to a **zm** map with **no** preceding
  rcon dispatch (console or GSC `exitLevel`), so `codol_zoneType` was still `mp` from the
  previous match.
* Lines 9367-9373 — `Error: CoDOL map archives: 'zm_prototype_sh' is a 'zm' map but
  codol_zoneType is 'mp'` → `ERROR: CoDOL map archive loading failed: zm_prototype_sh` →
  `----- Server Shutdown -----` / `Server crashed`.

**The previous match's category winning by default killed the server.** The map name knew
the right answer and was used only to veto. The fix is to let it *auto-select*.

---

## 3. Audit: every fs_game read/write on the server path, and what reaches C1

| Site | What it does | Reaches C1 (1.1.1.13)? |
|---|---|---|
| `filesystem.c` `FS_InitCvars` | `Cvar_RegisterString("fs_game", "", 28, ...)`. **MEASURED**: 28 = `CVAR_SERVERINFO`\|`CVAR_SYSTEMINFO`\|`CVAR_INIT` (`cvar.h:240-258`). | — |
| `filesystem.c` `FS_GameCheckDir` → `FS_GameDirDomainFunc:2745` | `Com_Error(ERR_DROP)` unless `""` or a `mods/` subdir. Reached from **every** `FS_Startup`, i.e. from every `SV_SpawnServer` via `FS_Restart` (`sv_main.c:5320`). | — (kills the server instead) |
| `filesystem.c` `FS_Startup:3061-3082` | Adds `<basepath>/<fs_game>` and `usermaps/<mapname>` to the search path when non-empty. | indirectly, via pure checksums |
| `filesystem.c:3778, 3825` (`DB_BuildOSPath`/`DB_BuildQPath`, ffdir 1) | Zone lookups become `<fs_game>/<zone>.ff`. | indirectly |
| `filesystem.c:4018, 4033-4041` | Pure-iwd checksum selection keyed on `fs_game`. | yes (pure lists) |
| `db_load.cpp:1417-1452` `DB_BuildZoneFilePath` | Non-empty `fs_game` redirects `common_mp` / `localized_common_mp` / `code_post_gfx_mp` lookups and adds a `usermaps` fallback. | indirectly |
| `db_load.cpp:2069` | Prefixes the pure **zone name list** with `<fs_game>/`. | yes |
| `sv_client.c:662` `connectResponse %s` | **MEASURED: dead code in this build.** It sits in the `#else` arm of `#ifdef CODOL_SERVER` at `sv_client.c:648`; the CoDOL arm sends `NET_SendPacket(..., codol_response, ...)`. fs_game never reaches C1 here. | **no** |
| `sv_main.c:1087-1101` `SVC_Info` | `mod`=0/1 and the `game` key in the **browser/masterserver** `infoResponse`. | no (not the C1 handshake) |
| `sv_main.c:1343-1347` `SVC_SourceEngineQuery_WriteInfo` | Writes `"main"` when empty, else `fs_game`. **Source-engine query**, not C1. | no |
| `sv_main.c:3971-3974` `SV_Map` | Non-CoDOL arm only (`#else`); the CoDOL arm uses `DB_FileExists(mapname, 0)` alone. | no |
| `sv_main.c:4344-4352` `SV_SetSystemInfoConfig` | Appends `\fs_game\\` to systeminfo, then `SV_SetConfigstring(1, buf)`. | **no** — **MEASURED**: `SV_WriteGameState` returns early under `CODOL_SERVER` into `CODOL_WriteServerGamestate` (`sv_main.c:3553-3559`), which builds its own bank and never sets index 1 (`grep` for `CODOL_SetConfigstring(..., 1, ...)` across `src/codol/` returns nothing; `src/codol/` contains **zero** references to `fs_game`). |
| `cscr_parser.cpp:506` | `if ( !fs_gameDirVar && fs_gameDirVar->string[0] )` — **MEASURED: inside a `/* */` comment block**, dead. No action needed; the scripts worker should not "fix" it into live behaviour. | no |

### Audit conclusions

1. **MEASURED: `set fs_game <x>` over rcon is a silent no-op today.** `Cvar_Set_f` calls
   `Cvar_Set2(..., qfalse)` (`cvar.c:1727`) and `Cvar_SetVariant` rejects a `CVAR_INIT` var
   when `force == qfalse` with *"fs_game is write protected."* (`cvar.c:817-822`). So the
   reported `ERR_DROP` blocker is real but is reached a step later: once `fs_game` *is*
   non-empty (e.g. `+set` on the command line), the next `FS_Startup` — inside every
   `SV_SpawnServer` — drops the server.
2. **MEASURED: in the CoDOL build, `fs_game` reaches C1 through nothing at all.** The one
   handshake site is dead code; the gamestate writer is CoDOL's own and ignores it. The
   only real consumers are internal: the FS search path, zone path building and the pure
   checksum/zone-name lists.
3. Therefore the safe and correct design is that `fs_game` is an **input-only** carrier
   whose token is **consumed** — recorded and then emptied — so `fs_gameDirVar->string`
   is `""` at every point any consumer can observe it. That makes "byte-identical wire for
   mp" true by construction, and true for coop and zm as well.

---

## 4. What was implemented

### 4.1 `src/filesystem.c` / `src/filesystem.h` — fs_game accepts and consumes a category

New, all under `#ifdef CODOL_SERVER` (prototypes added to `filesystem.h`):

```c
const char *FS_CoDOLCategoryToken(const char *value);   /* "mp"|"coop"|"zm", case-insensitive, else NULL */
void        FS_CoDOLNormalizeGameDir(void);             /* idempotent: record + empty fs_game */
const char *FS_CoDOLConsumeGameCategory(void);          /* one-shot read of the pending request */
const char *FS_CoDOLGameCategory(void);                 /* diagnostics */
```

* `FS_GameDirDomainFunc` now accepts `mp` / `coop` / `zm` in addition to `""` and `mods/*`.
* For an **invalid** value it no longer `Com_Error(ERR_DROP)`s under `CODOL_SERVER`: it
  prints a specific error naming the accepted values and returns `qfalse`, so the existing
  `FS_GameCheckDir` resets the dvar to `""`. Rationale: this is reached from every
  `SV_SpawnServer`, on a live server, from a value the lobby sets remotely — a typo must
  not end a running match and drop the connected client. The reset also neutralises path
  traversal, which is what the `..`/`::` test was protecting. The non-CoDOL arm is
  unchanged.
* `FS_InitCvars` now clears `CVAR_INIT` on the live var (`fs_gameDirVar->flags &= ~CVAR_INIT;`)
  so the lobby's rcon write lands. It must be done on the var, not by changing the
  registration literal: **MEASURED**, `Cvar_Register` only ever `Cvar_AddFlags`-ORs flags in.
* `FS_InitCvars` then calls `FS_CoDOLNormalizeGameDir()` **before** `FS_SetDirSep` /
  `FS_GameCheckDir`, so a token can never reach the search path or a zone path.

### 4.2 `src/sv_main.c` — resolution, ordering, teardown, session map

**Precedence, re-evaluated on every spawn** (`SV_CoDOLResolveAssetCategory`, called as the
first statement of the `CODOL_SERVER` block in `SV_SpawnServer`, immediately *before* the
`codol_zoneType` re-registration and well before `FS_Restart` and `CODOL_LoadMapArchives`):

1. **`fs_game`** — this match's explicit carrier. The only input that can say `coop` for an
   `mp_*` level zone.
2. **`codol_zoneType` written for this match** — detected as `latchedString != string`.
   **MEASURED**: a latched rcon write touches only `latchedString` (`cvar.c`, `CVAR_STRING`
   case), and a spawn's re-registration promotes it with `force=qtrue` making the two equal
   again — so a leftover from the *previous* match can never look explicit. This is exactly
   the discriminator the crash in §2 needed.
3. **The map name** — `zm*` proves zm, `coop*` proves coop. Auto-selects; does not veto.
4. **`"mp"`.**

The previous match's value never wins. `map zm_prototype_sh` with no rcon at all now
resolves to `zm` and loads, instead of crashing the server.

**Contradiction handling — correct and warn, never fatal:**

* map proves a category and the explicit request differs → warn naming both, load the
  map-name answer (which is what the client itself derives, so it is the only self-consistent
  choice for the zone chain, the constConfigStrings namespace and `fs_crc`).
* explicit `zm` on a non-`zm_*` map → warn, load `mp`.
* **`mp_*` level zone + category `coop` is explicitly NOT a contradiction** — that pairing is
  how every coop match ships.

Every spawn prints one line: `CoDOL asset category: <cat> (from <source>) for map <map>`.

**Latch promotion is made correct** via `SV_CoDOLForceZoneType()`. **MEASURED trap**:
`Cvar_SetVariant`'s `CVAR_STRING` case early-outs on `!Q_stricmp(var->string, value.string)`
*without looking at `latchedString`* — so force-setting `codol_zoneType` to a value it
already holds in `string` would leave a stale disagreeing `latchedString` for the
re-registration to promote. The helper writes `""` first when the latched value differs, so
the real set always lands and `string == latchedString == resolved` before registration.

**Teardown on category change** — installed, not called by name, mirroring the
`CODOL_SetWeapon*Resolver` pattern already in `SV_SpawnServer`:

```c
void SV_SetCoDOLCategoryTeardown(void (*fn)(const char *previous, const char *next));
```

`sv_main.c` tracks `codol_loadedZoneType` (the category the currently mounted archives
belong to) and, when the resolved category differs, prints
`CoDOL asset category change <prev> -> <next>: retiring the previous gametype zones and scripts`
and calls the installed hook **before** `CODOL_LoadMapArchives`. With no hook installed it
warns instead, so the build links and runs either way.

**Session/playlist map** — new dvar and a second install hook:

```c
codol_sessionMap = Cvar_RegisterString("codol_sessionMap", "", 0, ...);  /* NOT latched */
void        SV_SetCoDOLSessionMapInstaller(void (*fn)(const char *session_map));
const char *SV_CoDOLSessionMapName(void);      /* "" when the lobby sent none */
const char *SV_CoDOLAssetCategory(void);       /* resolved category, for the asset layer */
```

The installer is called with the session spelling just before the mount. The mount still
keys off `mapname` (the base level zone), which is what goes on the wire.

**Wire safety**: `FS_CoDOLNormalizeGameDir()` is also called at the top of
`SV_SetSystemInfoConfig` and `SVC_Info`, so a pending token can never become a systeminfo
`fs_game` key, a `mod` flag or a `game` key even if no map load follows the rcon write.

### 4.3 Build

**MEASURED**: `make obj/codol/filesystem.o obj/codol/sv_main.o obj/codol/sv_client.o`
(msys2 make + mingw32 gcc, `TMP` redirected into `obj/tmpbuild`) compiles all three clean —
only pre-existing warnings (`unused variable 'expanded'`, `'mapname_loadff'`,
`'zoneinfo' set but not used`, and the pre-existing `sv_client.c` ones). No full link was
attempted: `TARGETNAME=codol_dedrun` means `make` would write `bin/codol_dedrun.exe`, the
live binary, which is out of bounds.

### 4.4 No-regression argument for mp

* Today's lobby sends `set fs_game ""` (**MEASURED**, qconsole line 3317). `""` yields **no**
  category request, so precedence falls to rule 2 (`codol_zoneType mp`, latched this match)
  → `mp`. Identical to today.
* A zm match driven the old way (`set fs_game ""` + `set codol_zoneType zm`) still resolves
  to `zm` through rule 2. No lobby change is *required* for today's flows to keep working.
* `fs_gameDirVar->string` is `""` at every observation point in every category, so the FS
  search path, zone paths, pure lists, `SVC_Info`, `SV_SetSystemInfoConfig` and the
  (already fs_game-free) CoDOL gamestate are byte-for-byte what they are today.

---

## 5. What the LOBBY must now send  *(parent: apply to `match_server_control.py`; I edited no .py)*

Same four commands, same order, with two changes:

```
set fs_game "<mp|coop|zm>"          # was "" — now the authoritative category
set codol_sessionMap "<session_map>"  # NEW, only for coop; "" otherwise
set codol_zoneType "<mp|coop|zm>"   # keep sending it; it is now the fallback, not the authority
set g_gametype "<gt>"
map <base level map>
```

Concretely:

| category | `fs_game` | `codol_sessionMap` | `map` |
|---|---|---|---|
| mp | `mp` | `""` | `mp_rust` |
| zm | `zm` | `""` | `zm_zombie_training` |
| coop | `coop` | `coop_training_mp_killhouse_sh` | `mp_killhouse_sh` |

Notes:

* `_fs_game_for(zone_type)` should simply return the zone type (`mp`/`coop`/`zm`). The
  `CODOL_MATCH_FS_GAME[_<TYPE>]` env override can stay as an escape hatch; a `mods/...`
  value still behaves as a classic mod dir.
* `codol_sessionMap` comes from `startgame.txt`'s `session_map=`. Send `""` when there is
  none — it is read once per spawn and not latched.
* Case is not significant. An unrecognised value is rejected with a named error and treated
  as `""` (mp baseline); it will not drop the server.
* Keep sending `codol_zoneType`: it remains a valid carrier (precedence rule 2) and is the
  dvar the rest of the server reads.

---

## 6. Cross-file patches handed back (I do not own these files)

### 6.1 REQUIRED — `src/codol/assets/codol_asset_commands.c`: stop vetoing coop

Without this, `fs_game coop` + `map mp_killhouse_sh` still fails the mount and
`sv_main.c` still `ERR_DROP`s. The category is already resolved and cross-checked in
`SV_SpawnServer`; this guard should only catch a genuine contradiction.

Replace, in `CODOL_LoadMapArchives` (currently lines 319-327):

```c
    derived=CODOL_ZoneTypeForMapName(map);
    if(strcmp(derived,zone_type)) {
        Com_PrintError(CON_CHANNEL_SYSTEM,
            "CoDOL map archives: '%s' is a '%s' map but codol_zoneType is '%s'; "
            "mounting common_gametype_%s for it would give the client the wrong zones and fs_crc\n",
            map,derived,zone_type,zone_type);
        return 0;
    }
```

with:

```c
    /* The map name PROVES the category only for the zm_* and coop_* spellings.
     * A coop match loads an mp_* LEVEL zone with common_gametype_coop
     * (playlist coop_training_mp_killhouse_sh -> level mp_killhouse_sh), so an
     * mp_* name must NOT be read as proof of "mp".  Refuse only a real
     * contradiction; SV_SpawnServer has already resolved and corrected the
     * category before calling here. */
    derived=NULL;
    if(!Q_stricmpn(map,"zm",2))        derived="zm";
    else if(!Q_stricmpn(map,"coop",4)) derived="coop";
    else if(!strcmp(zone_type,"zm"))   derived="mp";   /* zm content is only ever zm_* */
    if(derived && strcmp(derived,zone_type)) {
        Com_PrintError(CON_CHANNEL_SYSTEM,
            "CoDOL map archives: '%s' is a '%s' map but the asset category is '%s'; "
            "mounting common_gametype_%s for it would give the client the wrong zones and fs_crc\n",
            map,derived,zone_type,zone_type);
        return 0;
    }
```

`CODOL_ZoneTypeForMapName()` itself stays (it still mirrors C1 `0x612850`); it just stops
being the sole authority. Its doc comment should note the coop exception.

### 6.2 REQUIRED — `src/codol/assets/**`: install the two hooks

The asset layer must call, from its init (or from wherever the other resolvers are
installed):

```c
extern void SV_SetCoDOLCategoryTeardown(void (*fn)(const char *previous, const char *next));
extern void SV_SetCoDOLSessionMapInstaller(void (*fn)(const char *session_map));

SV_SetCoDOLCategoryTeardown(CODOL_UnloadGametypeAssets);   /* assumed name */
SV_SetCoDOLSessionMapInstaller(CODOL_SetSessionMapName);   /* assumed name */
```

Assumed signatures (adjust the cast, not the call site, if they differ):

```c
void CODOL_UnloadGametypeAssets(const char *previous_category, const char *next_category);
void CODOL_SetSessionMapName(const char *session_map);   /* "" when none */
```

`CODOL_UnloadGametypeAssets` is called **before** `CODOL_LoadMapArchives`, only when the
category actually changes, and must retire `common_gametype_<previous>`,
`localized_common_gametype_<previous>`, the `<previous>` constConfigStrings table and the
`<previous>` script set. It should also call the existing
`CODOL_ForgetMountedMapArchives()` so the "unchanged map, reuse the mount" shortcut
(`codol_asset_commands.c:280-292`) cannot hand back a mount from the old category.

`CODOL_SetSessionMapName` receives the playlist spelling for this match (e.g.
`coop_training_mp_killhouse_sh`) or `""`. Whether the coop playlist zone
`coop_training_mp_killhouse_sh.ff` additionally needs mounting alongside the level zone is
the asset worker's call; the string is now plumbed either way.

### 6.3 Optional — `src/cscr_parser.cpp`

No change needed. Its `fs_gameDirVar` use (line 506) is inside a comment block, and
`fs_game` is now always `""` anyway. Do not "repair" the `!fs_gameDirVar &&` typo into live
behaviour.

---

## 7. Open items / not done

* **INFERRED, untested on a live match.** No server was started or stopped; verification is
  a compile only. The first live test should be: (a) an mp match — expect the log line
  `CoDOL asset category: mp (from fs_game) for map mp_rust` and no other change; (b)
  `map zm_prototype_sh` from the console with no rcon — expect
  `... zm (from map name) ...` and a successful mount where it previously crashed;
  (c) a coop match once §6.1 lands.
* The teardown itself is not implemented here by design (owned by the assets worker); until
  §6.2 lands a category change logs
  `CoDOL asset category change with no teardown installed: the <prev> gametype zones stay resident`.
* `FS_Restart` still runs with `fs_game == ""` for every category, so the pure-checksum and
  zone-name lists are unchanged across categories. **INFERRED** that this is correct for
  C1 (it has never seen a non-empty `fs_game` from this server); if a category ever needs
  its own pure list, that is a separate change.
