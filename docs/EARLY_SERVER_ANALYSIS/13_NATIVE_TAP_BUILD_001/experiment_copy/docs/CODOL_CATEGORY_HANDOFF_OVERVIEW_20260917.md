# The mp -> coop/zm handoff: parent overview and evidence, 2026-09-17

User request, verbatim:

> start working on the fs_game handoff when going into coop or zombies for the
> game server. unload the mp zone and scripts for the appropriate coop or zm
> ones depending on fs_game

This is the parent's evidence file and integration index. The five worker
deliverables it indexes are listed in section 7. Every claim here is labelled
**MEASURED** (read out of a binary, a log, shipped data or source) or
**INFERRED**.

---

## 1. What a "category" is, and the three things that must switch

CoDOL has three asset categories: `mp`, `coop`, `zm`. They are *not* gametypes.
The category selects, on the client and therefore on the server:

1. the gametype zone chain — `common_gametype_<category>` (+ `localized_` and
   `patch_` variants);
2. the constant configstring namespace — `mp/constconfigstrings_<category>.csv`;
3. the `fs_crc` the client checksums the gamestate against.

MEASURED, from the user's own client log
(`D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\main\console_mp.log`,
`DB_LoadXFile:` lines), the client's load order is:

```
common_mp  ->  common_gametype_<category>  ->  <level zone>  [-> <playlist>_load]
```

MEASURED for mp (`common_mp` / `common_gametype_mp` / `mp_storm_spring`, one
`ClientLoadTime` line) and for zm (`common_gametype_zm` / `zm_zombie_training` /
`zm_zombie_training_load`, and `zm_prototype_sh` — console_mp-003/006/012.log).
MEASURED for coop from the 2026-08-19 capture quoted in
`alpha0022/map_handoff.py:60-120`: `common_gametype_coop` / `mp_killhouse_sh`.

**Consequence: the startup zone group is category-agnostic.** MEASURED from the
shipped fastfile set
(`...\Call of Duty Online 1.1.1.13\client_shipRetail\chinese`): there is
`common_mp.ff` and `code_post_gfx_mp.ff` and there is **no** `common_zm.ff`,
`common_coop.ff`, `code_post_gfx_zm.ff` or `code_post_gfx_coop.ff`. The only
per-category zones are `common_gametype_{mp,coop,zm}.ff` plus their `localized_`
and `patch_` variants. So "unload the mp zone" means **group 1 only** — the nine
archives `CODOL_LoadStartupArchives()` mounts at
`src/codol/assets/codol_asset_commands.c:227` stay, correctly, for all three
categories.

Corroborating MEASURED fact: all three constant tables
`mp/constconfigstrings_{mp,coop,zm}.csv` live in the startup archive
`code_post_gfx_mp` (`docs/zone_assets/ALL_stringtable.txt`). Every category's
const table is resident regardless of which gametype zone is mounted.

## 2. Why the map name cannot carry the category (the reason fs_game exists)

`CODOL_ZoneTypeForMapName()` (`codol_asset_commands.c:299`) derives the category
from the map name by prefix — `zm` (2 chars), then `coop` (4), else `mp` —
mirroring C1 `0x612850`. `CODOL_LoadMapArchives` then **refuses** to mount when
the derived category disagrees with `codol_zoneType`.

For zm that works: zm maps are `zm_*`.

For coop it structurally cannot. MEASURED (`map_handoff.py:60-120`, 2026-08-19
capture): a coop match has **two map spellings**. The lobby/room-info playlist
spelling is `coop_training_mp_killhouse_sh`; the **level zone the client
actually loads is `mp_killhouse_sh`**. `base_map()` strips the prefix at the
first `_mp_`, and the lobby's `match_server_control.plan()` sends
`selection["map"]` — the *base* spelling. So the server is handed
`map mp_killhouse_sh` with category `coop`, the derivation returns `mp`, and the
mount is refused.

**Coop is dead on arrival at the first step of the handoff.** The category is
not recoverable from the map name, so it needs an explicit carrier. That is the
whole justification for the user's framing.

(Note the same function contains a contradictory assumption: its
`if(!strncmp(map,"coop_",5))` base-stripping branch and `roots=4` path only make
sense if it is handed the *playlist* spelling.)

## 3. The live crash this work fixes

MEASURED, `bin/home/main/qconsole.prev-5f1c9db8.log`:

- lines 3317-3324 — the **only** rcon dispatch in the entire log:
  ```
  Rcon from 127.0.0.1:57961: set fs_game ""
  Rcon from 127.0.0.1:57961: set codol_zoneType mp
  Rcon from 127.0.0.1:57961: set g_gametype war
  Rcon from 127.0.0.1:57961: map mp_rust
  ```
  confirming `fs_game` carries nothing today;
- line 9303 — `Server: zm_prototype_sh`, a map change to a **zm** map with no
  preceding category dispatch (it came from the console or a GSC `exitLevel`,
  not from the lobby);
- lines 9367-9373 —
  ```
  Error: CoDOL map archives: 'zm_prototype_sh' is a 'zm' map but codol_zoneType is 'mp'; ...
  ERROR: CoDOL map archive loading failed: zm_prototype_sh
  ----- Server Shutdown -----
  With the reason: Server crashed: CoDOL map archive loading failed: zm_prototype_sh
  ```

The guard's failure mode is a **dead server**, because
`src/sv_main.c:5344` turns the refusal into `Com_Error(ERR_DROP)`.

**Design conclusion.** The map name must AUTO-SELECT the category when no
carrier set one, instead of vetoing. Proposed precedence:

> explicit carrier for *this* match (`fs_game` -> `codol_zoneType`)
> **>** map-name derivation
> **>** the previous match's value (which must never win — that is exactly the
> crash above).

Refuse only a genuine contradiction (explicit `mp`/`coop` against a `zm_*` map,
or explicit `zm` against an `mp_*`/`coop_*` map), and prefer a loud correction
to an `ERR_DROP` that kills the server and drops the connected client.

## 4. The wall immediately past the handoff: the weapon window

MEASURED, `src/codol/weapon/codol_sv_weapons.c:404-446`:
`CODOL_InitializeServerWeaponConfigstrings(zone_type)` loads
`mp/coWeaponAttachmentTable.csv` **only** when the category is `mp`. For coop
and zm the published `CS_WEAPONS` window is exactly two entries (`none`,
`defaultweapon_mp`) and CS 6517 is published as the empty string.

MEASURED, the matching client behaviour (`map_handoff.py:93-95`, 2026-08-19):

```
map: mp_killhouse_sh  type: coop  -> CA_LOADING, weapon list stops at
                                    ' * 0 none / * 1 defaultweapon_mp', then
                                    ERROR: 181 beretta_so 0 2   (coop const table)
```

against the mp run, which enumerated 54 entries and failed much later and
differently. So the in-code claim at `codol_sv_weapons.c:427-432` — that coop/zm
"keep the empty value, which skips the loop as the client's own tables do" — is
contradicted by the one coop transcript we have. A category-correct weapon
window is required for the handoff to reach anything playable.

Hard invariant when fixing it: C1's `CG_Init` loop (`0x47d1d0`) walks
`1..count-1` over `bg_weaponDefs` and dereferences a NULL definition at
`0x47c1f7` for any index the published window does not back. CS 6517 must never
exceed the number of published, buildable definitions.

## 5. The script half

MEASURED, `src/cscr_parser.cpp:555-595` and
`src/codol/script/codol_script_source.c`: `Scr_ReadFile` resolves through
`CODOL_ReadScriptSourceWithNativeOverlayForZone(..., CODOL_ServerZoneType(), ...)`,
which probes `<nativeOverlay>/<category>/<name>` **first**, then the shared
roots. The launcher points all three script dvars at the single collated root
`bin/home/codol_rawfiles`, so the category root is
`bin/home/codol_rawfiles/<category>/`.

MEASURED: `bin/home/codol_rawfiles/zm/` holds exactly four files
(`maps/mp/gametypes/zm.gsc`, `maps/mp/gametypes/_callbacksetup.gsc`,
`maps/mp/gametypes/_zombiemode.gsc`, `maps/mp/zm_zombie_training.gsc`).
`bin/home/codol_rawfiles/coop/` **does not exist**.

INFERRED from section 2: because coop and mp share level zones
(`mp_killhouse_sh`, `mp_crash_tropical`, `mp_estate_tropical`,
`mp_fav_tropical`, `mp_crash_intro`), a coop level script has the *same module
name* as the multiplayer one and the category root is the only thing that can
separate them. Getting the shadowing right is the whole job on the coop side.

Known landmine, already documented in `docs/CODOL_ZOMBIES_STARTUP_20260915.md`:
vendor IW4's `isSP()` infers singleplayer from a map name not starting with
`mp_`, which is true of every `zm_*` map — it must be neutralised at the choke
point for both non-mp categories.

## 6. What the lobby already does right

MEASURED, `alpha0022/map_handoff.py`: the lobby resolves coop and zm descriptors
correctly today, including the survival/spec-ops flow, carries
`type=<mp|coop|zm>` and both map spellings (`map=` and `session_map=`) in
`startgame.txt`, and holds per-category `fs_crc` values
(`mp 0xAD1E1713`, `coop 0xE8139F9B`, `zm 0x801CEF02`). zm descriptors are
MEASURED on the wire from the user's own client. So the lobby is not the
blocker; only `fs_game` is empty
(`match_server_control._fs_game_for()` returns `""` for every category unless
overridden by environment).

Parent-owned follow-through once the server contract lands:
`match_server_control.py` (`_fs_game_for`, and passing `session_map`),
`tools/codol_map_handoff.ps1` (currently emits only `map|gametype|type`), and
`bin/START-CODOL-SERVER.cmd`.

## 7. Worker deliverables

| Area | File ownership | Deliverable |
|---|---|---|
| C1 fs_game evidence (read-only) | none | `CODOL_FS_GAME_EVIDENCE_20260917.md` |
| Asset teardown on category change | `src/codol/assets/**` | `CODOL_CATEGORY_ASSET_TEARDOWN_20260917.md` |
| fs_game plumbing | `src/sv_main.c`, `src/filesystem.{c,h}`, `src/sv_client.c` | `CODOL_FS_GAME_HANDOFF_20260917.md` |
| coop/zm script sets | `bin/home/codol_rawfiles/{zm,coop}/**` | `CODOL_CATEGORY_SCRIPT_SETS_20260917.md` |
| coop/zm weapon window | `src/codol/weapon/**` | `CODOL_CATEGORY_WEAPON_WINDOW_20260917.md` |

## 8. What landed

### 8.1 The category carrier (`src/sv_main.c`, `src/filesystem.{c,h}`)

`fs_game` is now the category carrier, and it is **input-only**: the token is
recorded and `fs_game` is emptied again in the same breath, so
`fs_gameDirVar->string` is `""` at every point a consumer can observe it and
every byte this server puts on the wire stays what an mp match sends today.
That is not a stylistic choice — MEASURED from C1.exe, C1's own `fs_game`
(dvar 1006, registered at `0x00617A45`) has a domain callback at `0x00617810`
accepting only `""` or `mods/<name>`, all 15 of its references are
filesystem/search-path internals, and the `connectResponse` handler at
`0x004967EB` never reads the value. `src/codol/` contains zero `fs_game`
references. **fs_game cannot reach C1 at all**, which is exactly why consuming
it is safe.

Two retained blockers were removed: `fs_game` shipped as `CVAR_INIT`, so
`set fs_game X` over rcon was answered *"fs_game is write protected"* and did
nothing; and `FS_GameDirDomainFunc` `ERR_DROP`ed on any value not under
`mods/`, on a path reached from every `FS_Startup` — i.e. every
`SV_SpawnServer` — which would have ended a running match over a typo. It now
rejects loudly and resets to `""`.

Resolution order, re-evaluated on **every** spawn:

1. `fs_game` — this match's explicit carrier, the only input that can say
   "coop" for an `mp_*` level zone;
2. `codol_zoneType` written *for this match* — discriminated by
   `latchedString != string`, since a spawn's re-registration promotes the
   latch and makes them equal, so a leftover can never look explicit;
3. the map name, which now **auto-selects** instead of vetoing;
4. `"mp"`.

The previous match's value never wins. Contradictions are corrected and
announced, never fatal. An `mp_*` level zone with category `coop` is
explicitly **not** a contradiction.

### 8.2 The asset teardown (`src/codol/assets/**`)

MEASURED: `CODOL_ReplaceRuntimeArchives(group 1)` only *unlinked* the previous
group onto `retired_archives` and nothing on that path freed — the sole drain
was `CODOL_UnmountArchives` at process exit. **Every map or category change
leaked a full resident copy** (`common_gametype_zm.ff` is 71.5 MB,
`zm_zombie_training.ff` 69.2 MB). `CODOL_ForgetMountedMapArchives()` was dead
code with zero call sites and no prototype.

`CODOL_UnloadCategoryAssets()` now sequences borrowers first, providers last,
and the mount guard was relaxed so only a *proven* category can contradict the
carrier. Four caches survived a group-1 swap and are now reset; two more, both
keyed on a raw `WeaponDef *` and cleared by nothing, were handed to the parent
and wired in this pass (`CODOL_SwayPhaseResetDefs`,
`CODOL_ResetBreathScopeCache`). Those two would not have crashed — the cached
values are copied scalars — they would have served the previous category's
sway curve and scope flag from a recycled address, which is the kind of bug
that survives a whole session unnoticed.

### 8.3 The script sets (`bin/home/codol_rawfiles/{coop,zm}/`)

MEASURED out of the zones: the coop gametype script is **`coop`**
(`mp_playlists.info` lines 380-384: `gametype coop` / `name english "Spec Ops"`
/ `script coop`, with no `teambased` line), corroborated by
`maps/mp/gametypes/_gametypes.txt`, `mp/gametypescptable.csv` and
`mp/basemaps.arena`. The coop **level script module name is the playlist
spelling**, established by four independent zone signals with unambiguous mp
and zm controls (fx rawfile, createfx, animlist, vision — e.g.
`maps/mp/coop_training_mp_killhouse_sh_fx.gsc` against
`maps/mp/mp_killhouse_sh_fx.gsc` and `maps/mp/zm_zombie_training_fx.gsc`).
Both spellings were shipped, so the root is correct either way.

Before this pass a coop match had **no `maps/mp/gametypes/coop.gsc` anywhere**,
so `GScr_LoadGameTypeScript` would `Com_Error(ERR_DROP)` — and before reaching
that it would have compiled **100 multiplayer scripts**, including all 16
killstreak modules (the source of the "not in any mounted zone" warnings), the
whole `_gamelogic`/`_globallogic`/`_damage`/`_class`/`_rank`/`_spawnlogic`
chain, and the multiplayer `maps/mp/mp_killhouse_sh.gsc`.

Verified independently by the parent with the loader's own precedence
(`--root <category> --root <shared>`):

| closure | scripts lowered |
|---|---|
| mp | 93 |
| coop | 4 |
| zm | 4 |

"every reachable script resolves against the registered builtin table", and
`--binary bin/codol_dedrun_next.exe` reports 0 source registrations absent from
the deployed exe. **That is the "unload the mp scripts" half of the request,
measured.**

### 8.4 The weapon window (`src/codol/weapon/`)

The in-code claim that coop/zm "keep the empty value, which skips the loop as
the client's own tables do" (§4) is **REFUTED**. MEASURED by decoding the three
type-37 stringtables out of `code_post_gfx_mp`: each category's constant table
*is* a complete weapon window.

| table | rows | weapon block (CS) | slots | CS 6517 |
|---|---|---|---|---|
| `constconfigstrings_mp.csv` | 2053 | 5363..5537 | 152, 22 holes | `176` |
| `constconfigstrings_coop.csv` | 1803 | 5363..5425 | 63, hole-free | `64` |
| `constconfigstrings_zm.csv` | 1625 | 5363..5492 | 130, hole-free | `131` |

CS 5363 is `defaultweapon_mp` in all three; coop index 2 is `beretta_so`, zm
index 2 is `frag_grenade_zm`. There is no coop/zm analogue of
`coWeaponAttachmentTable.csv` anywhere in the shipped set — the constants are
the only source, which is why the mp-only table load left coop and zm with a
two-entry window.

And the `181 aa12_mp 0 2` that dropped the 17:51 coop client is **our bug**:
`aa12_mp` appears nowhere in the coop window (its coop analogue is `aa12_so` at
index 16), but it is verbatim **mp constant index 2**, and verbatim the first
entry the old Python server published
(`alpha0022/weapon_configstrings.py:229-230`). The `0 2` is the not-found
shape, not the `N+1 N` partner shape. So `181 beretta_so 0 2` and
`181 aa12_mp 0 2` are one defect seen from both sides: the published window was
not the category's window — nothing published, or the wrong category's.

The window is now collected per category (mp keeps its row-ordered attachment
walk byte for byte; coop/zm walk their constants by slot), and CS 6517 is
published for every category as the server's own contiguous registered prefix
— never a hard-coded 64/131, so it cannot exceed buildable definitions and
cannot trip the `0x47c1f7` NULL deref.

Still open on this axis: mp remains on the attachment table (its 22 constant
holes are a live-path change); the `ps.weaponsEquipped[15]` ring at `ps+0x2A0`
is a second NULL-deref sink owned by loadout code; and there is no coop/zm
starting loadout yet.

### 8.5 The lobby contract (`alpha0022/`, `tools/`, `bin/`)

Five commands now go out at the Ready press, `map` last because it starts the
load:

```
set fs_game "<mp|coop|zm>"
set codol_sessionMap "<playlist spelling>"
set codol_zoneType <mp|coop|zm>
set g_gametype <gt>
map <base level map>
```

`tools/codol_map_handoff.ps1` emits a fourth `session_map` field (falling back
to `map` for a legacy stamp, verified), and `START-CODOL-SERVER.cmd` passes
`+set codol_sessionMap` for a cold start.

## 9. The one decision deliberately NOT taken

**Should the gamestate `mapname` be the coop playlist spelling?** Two
independent MEASURED lines say C1 wants it:

- the zone set is a pure function of the map string inside C1's single
  zone-list builder `0x004CCDF0` — the `coop_` expansion at `0x004CD0FE` is
  *inside* it, shared by `preloadmap`, `CL_MapLoading` and the gamestate path,
  with no caller special-cased;
- the coop level script, animlist, vision and createfx assets are all named for
  the playlist spelling (§8.3).

It was **not** done, because the native server cannot consume it yet: collision
and world lookups key on `sv_mapname` to build `maps/mp/<mapname>.d3dbsp`
(`codol_sv_xmodel.c:203`, `codol_glass_world.c:69`), and MEASURED, the coop
zones ship **no world assets at all** — no `col_map_mp`, `com_map`,
`game_map_mp`, `gfx_map` or `map_ents`, only one `addon_map_ents` each, for
which this server has no loader (IW4 asset type 42 is absent from the IW3
33-type `g_assetNames` set in `src/asmsource/_db_assetnames.asm`).

So the base spelling is what the server can actually load today. Making the
switch means teaching the collision/world lookups to resolve the base name for
themselves, and building an `addon_map_ents` loader — without which a coop
match sees only the base `mp_*` entities and its Spec Ops
`info_player_start_so`/`_pmc`/`_pmcDefend` points are invisible. That is the
highest-value next coop item, and it is now fully specified rather than
guessed at.

Also retracted along the way, and worth recording so nobody re-derives it: the
prefix test at `0x004CCDF0` reads the gamestate **`type` field**, not
`g_gametype` (the `loadingnewmap` OOB handler does two adjacent
`MSG_ReadString`s — #1 map, #2 category — which is field-for-field the
gamestate layout at `codol_configstrings.c:291-294`; CS[0] is parsed at
`CG_Init`, after zones mount, so it cannot select them). `g_gametype` must
**not** be renamed. `codol_zoneType` already sends the right thing.

---

Status of this file: evidence gathered by the parent before, during and after
the workers' passes. **Nothing here was live-verified** — no server, lobby or
client was started or stopped in this pass, and no coop session has reached
`CA_ACTIVE` in any capture on record.
