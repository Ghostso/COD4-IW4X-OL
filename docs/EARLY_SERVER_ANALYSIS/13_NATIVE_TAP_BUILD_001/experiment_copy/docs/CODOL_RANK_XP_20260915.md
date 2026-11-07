# Rank and XP persistence, end to end (2026-09-15)

Scope: ranking up inside a match on this server, and the XP surviving the match.
Plus the Zombies character selection that shares the same profile plumbing.

Status discipline used throughout: **WRITTEN** (source exists and was reviewed),
**BUILT/TESTED** (compiles, links, and a fixture or the lobby's own module
exercises it), **LIVE** (observed against the running C1 client). This work
started no server, lobby or client process; the user's C1 (PID 49428) and lobby
`dw-capture.py` (PID 4556) were left running and untouched. The user then
started the server themselves part-way through, which produced the partial live
evidence in section 9 - read that section before treating anything here as
proven.

---

## 1. The contract, and why this one

Three candidate sources for a connecting player's rank/XP were on the table:
read `players/<uid>.json` / `lobby.sqlite` directly, have the lobby stamp rank
into `startgame.txt`, or read the lobby's own `mpdata_s.<uid>` blob.

**The blob wins, and it is already what this server does.** Reasons, in order of
weight:

1. It is the *client's* format. Rank and experience live only in `mpdata_s`; the
   `mpdata` the client uploads to the match server (32768 B, the 27-chunk
   `stats` upload) has no rank member at all. The lobby re-renders `mpdata_s.<uid>` from
   `players/<uid>.json` at serve time (`player_profiles.ensure_blob`), so the
   blob is already a faithful projection of the JSON authority — reading the
   JSON would duplicate `rank_service`'s rankTable arithmetic in C for no gain.
2. It needs no new IPC. `codol_profilePath` already points the server at the
   lobby's `resources` directory (`bin/START-CODOL-SERVER.cmd`), and
   `CODOL_ReadSecureProfile` already walks the same `mpdata_s.<uid>` ->
   `mpdata_s` -> seed chain the lobby serves from.
3. `startgame.txt` is a single-line, single-player handoff
   (`alpha0022/map_handoff.py:1881-1919`). It cannot describe a second human,
   and the rank would be a copy that goes stale the moment the lobby credits
   anything.

The return leg is the same directory: `resources/match_report.json`, format 1,
consumed by `rank_writeback.maybe_apply()` on the next storage GETFILE. That was
already the retired Python server's channel; this server now writes it, with one
addition — **a per-row `uid`** — so a multi-human match credits each account.

```
lobby players/<uid>.json  --render-->  resources/mpdata_s.<uid>
                                            |  CODOL_ReadSecureProfile (connect)
                                            v
                                   session secure profile
                                            |  _rank.gsc giveRankXP -> setRankExperience
                                            v
                              resources/match_report.json (format 1, per-row uid)
                                            |  rank_writeback.maybe_apply (GETFILE)
                                            v
                               lobby players/<uid>.json  (authority)
```

---

## 2. (a) Rank/XP at connect — ALREADY PRESENT, verified by reading, not changed

This half was already implemented; the audit below is the evidence, and the only
code added for it is the baseline capture in §4.

| step | where | note |
|---|---|---|
| uid latched | `src/sv_client.c:197,208-210,504` -> `src/codol/net/codol_connect.c:15-34` | the 16-hex `xuid` argument of the `connect` OOB packet, validated against the userinfo copy; immutable for the connection. **Not** `client_t::playerid`/`steamid` (IW4OL Steam), and `getXuid()`/`getUid()` are stubs (`src/scr_vm_functions.c:3251`, `:65`). |
| profile read | `src/codol/assets/codol_asset_commands.c:867-887` `CODOL_AutoBindClientSecureProfile` | `codol_profilePath` + that uid, seed `mpdata_s.ranklevel31.proposed`. Invoked from `src/sv_client.c:505` (`SV_DirectConnect`) and re-attached at `src/sv_client.c:1386` (`SV_ClientEnterWorld`), which drops the client if it still fails. |
| decode | `src/codol/stats/codol_profile_storage.c:9-53` | zlib inflate to exactly 32768 bytes, crc32 over bytes 4.. |
| rank conversion | `src/codol/stats/codol_profile_experience.c:24-62` | `CODOL_RankForExperience` / `CODOL_ProfileExperience`. Stored `rank` is one-based, `experience` is XP *within* the rank; the stale-`rankVersion` clamp follows C1 `0x58efa7..0x58efd4`. Blob offsets measured by alpha0022: rank `@0x13EC`, experience `@0x1130`, rankVersion `@0x13F0`; `GetRank @0x0058EFE0` ends in `dec eax`, `LiveStorage_GetExperience @0x0058EEB0` adds minXP itself. |
| script sees it | `src/codol/script/codol_script_rank_experience.c:37-47` (`getRankExperience`), `:65-113` (`setRankExperience`) | registered at `src/scr_vm_main.c:585-586`. Reads/writes the **session** view, so a script edit is visible to every later reader. |
| `_rank.gsc` uses it | `scripts/codol/maps/mp/gametypes/_rank.gsc:692-705` | `codolGetTotalRankXP`/`codolSetTotalRankXP` are the C1 adapters: humans go through `get/setRankExperience`, bots through `_persistence::statGet/statSet` (bots own no account). |

`mp/rankTable.csv` is a type-37 StringTable read from the mounted zones by
`CODOL_LoadEngineStringTable` (`src/codol/assets/codol_asset_registry.c:2084-2130`),
with a loose-CSV fallback under `codol_scriptPath`
(`src/codol/assets/codol_asset_registry.c:43-67`, bridged for the retained engine
at `src/db_load.cpp:3592-3603`). Column semantics used: `[2]` = rank minimum XP,
`[7]` = next rank's minimum, row `maxrank` `[1]` = max rank, `[3]` = rankVersion.
This build's curve is not stock MW2 (first band 2000 XP; 484,072 XP is level 31;
70 ranks, maxrank 69) and nothing here hardcodes a band.

## 3. (b) In-match ranking up — ALREADY PRESENT, audited

`scripts/codol/maps/mp/gametypes/` shadows the vendor IW4 tree (resolution order
`src/codol/script/codol_script_source.c:43-76`: native overlay, then
`alpha0022/gsc_overlay`, then `alpha0022/vendor/iw4`), and the overlay carries
real `_rank.gsc` (705 lines) and `_persistence.gsc` (296 lines).

- `_persistence::init()` calls `_rank::init()` (`_persistence.gsc:8`).
- `_rank::onPlayerConnect` seeds `player.pers["rankxp"]` from the profile and
  calls `player setRank( rankId, prestige )` (`_rank.gsc:184-197`).
- `giveRankXP` (`_rank.gsc:308`) is called from `_damage.gsc:215,1137,2244`,
  `_gamelogic.gsc:759`, `_missions.gsc:2053`, `war.gsc:141`, `conf.gsc:215`,
  `infect.gsc:144`. It runs the ordinary IW4 flow: `incRankXP` ->
  `updateRank(oldxp)` -> `setRank(newRankId)` + `updateRankAnnounceHUD` ->
  `syncXPStat()` -> `setRankExperience(total)`.
- Splash: `updateRankAnnounceHUD` (`_rank.gsc:459`) threads
  `_hud_message::promotionSplashNotify()` and `iPrintLn(&"RANK_PLAYER_WAS_PROMOTED")`
  to teammates. `setClientDvar`/`openMenu` behind it are real
  (`src/scr_vm_main.c:631`, `:578` -> `src/codol/script/codol_script_menu.c:62`).
- Scoreboard rank reaches the client: `setRank` is the retained asm builtin
  (`src/asmsource/_g_client_script_cmd_mp.asm:4684-4757`) writing
  `gclient+0x305c` / `+0x3060`, i.e. `clientState_t.rank`/`.prestige`
  (`src/player.h:288-289`). Those are published as clientState `+0xA0` and
  `+0xA4`, 8 bits each, by `CODOL_OverlayEngineClient`
  (`src/codol/snapshot/codol_engine_state.c:1018-1019`) into
  `src/codol/snapshot/codol_client_fields.inc:27` — **index 25 of the measured
  table, `{0x0a0, 8, 0}`**, exactly as the brief states. C1 evidence: the rank
  byte is copied at `0x46c964` into `clientInfo+0x60`, and the playercard row
  builder `0x68e7d0` reads `clientInfo+0x60` into card row `+0x14`; `+0xA4`
  follows into `clientInfo+0x64` / card `+0x18`. C1's own rank writer is
  `0x51dd18 -> client+0x3508`.

Builtins checked for stub-ness while auditing this path (do not count these as
support): `matchEnd`, `setPlayerTeamRank`, `sendRanks` are empty asm bodies
(`src/asmsource/_g_scr_main_mp.asm:7639-7648`); `logString` is an empty C body
(`src/scr_vm_functions.c:3240,3245`); `SV_MatchEnd` is commented out
(`src/sv_game.c:751-764`); `isUsingOnlineDataOffline` returns a constant
(`src/codol/script/codol_script_player_builtins.c:271`). None of them is on the
XP path, and none was relied on.

`_rank.gsc:498 endGameUpdate()` is an empty body — that is the IW4 original, not
a local regression, so it was left alone. The end-of-match rollup lives in §4
instead, where it can see every row rather than one player.

## 4. (c) Persisting the match — NEW, WRITTEN + BUILT/TESTED

New: `src/codol/stats/codol_match_report.h` / `codol_match_report.c`.

**The XP a row reports is not accumulated separately.** It is
`CODOL_ProfileExperience(session secure blob)` now, minus the same conversion of
the same blob at attach time. Both halves go through the recovered C1 algorithm,
so the number the lobby is handed is the growth of the value `_rank.gsc` itself
committed through `setRankExperience` — there is no second notion of "XP earned"
to drift out of step.

| hook | where | why there |
|---|---|---|
| baseline | `src/codol/assets/codol_asset_commands.c:880` (`CODOL_MatchReportClientAttached`) | the instant the profile is attached and before any script can edit it |
| end of match | `src/codol/script/codol_script_matchdata.c:14-29` (`CODOL_Scr_SendClientMatchData`) | IW4's `_gamelogic::processLobbyData` ends every match by calling `sendClientMatchData()` (`_gamelogic.gsc:2338`) after awards and scoreboards, with everyone still connected. Its neighbour `sendMatchData()` is gated on `matchMakingGame()` (`_gamelogic.gsc:2208-2209`), so this is the one end-of-match signal the vendor scripts always reach. |
| disconnect | `src/sv_client.c:1000` (freeze before `CODOL_DetachClientSecureProfile`) and `src/sv_client.c:1087-1088` (write once the last human's state has left `CS_CONNECTED`); `src/sv_client.c:497` covers a slot reused without a drop | a mid-match leaver still gets paid, and an emptied server reports immediately — the player is already back in the lobby asking for their profile |
| map change | `src/sv_main.c:2982` (`CODOL_ResetMatchReport`, first statement of `SV_ClearServer`'s CoDOL block) | a match that ended by map change rather than by its own game-over; placed before the secure profiles and the mounted rank table are torn down |

Design points worth keeping:

- **Reports partition the match, never repeat it.** After a successful write,
  each live row's baseline moves to the reported total and its counter carry
  goes negative by whatever the engine currently reads, so the next report
  carries only what accrued since. Rows carry `applied_live: 0` because this
  server runs no live save pump — unlike the Python server, nothing is persisted
  behind the lobby's back.
- **An empty report never clobbers a full one.** The fixture caught this: before
  the carry was folded into the freeze, the map-change reset re-reported the
  engine's raw counters and overwrote a game-over report the lobby had not
  consumed yet. `settle()` now folds the carry when a row is frozen, so after an
  ordinary game-over everything settles to zero and the reset writes nothing.
- **A reconnect inside one match is one row.** A departed row is adopted by uid
  when the same account attaches again.
- **Bot rows carry no `uid` and no `xp` object**, matching what
  `rank_writeback` skips anyway.
- Atomicity: temp file, `rename`, and on Windows (where `rename` refuses an
  existing target) `remove` + `rename`. A reader sees the whole old file, the
  whole new file, or none — never a partial one.

### The one-line lobby change

`alpha0022/rank_writeback.py` credited every human row to the *connection's*
uid, because the retired Python server only ever had one human. With two humans
one profile got both totals and the other got nothing. Backed up as
`rank_writeback.py.pre-cod4x`; `_amounts()` and the no-uid fallback are
unchanged, and a new `_per_uid_amounts()` builds one target per distinct row
uid, each with its own counters and its own `applied` idempotence key.
`_validate()` accepts `uid` as optional so pre-existing reports still parse.
`python rank_writeback.py --selftest` → 56 passed, 0 failed (was 40 checks);
`python player_profiles.py --selftest` → 34 passed, 0 failed.

### Row shape actually emitted

```json
{
 "format": 1,
 "created": 1789500000,
 "reason": "gameended",
 "server_time_ms": 620000,
 "duration_s": 600,
 "team_scores": [750, 1000],
 "players": [
  {"slot": 0, "name": "Alpha", "bot": false, "uid": "11354582479263516619", "team": 2,
   "kills": 9, "deaths": 3, "assists": 2, "score": 1000, "outcome": "win",
   "xp": {"kill_xp": 1500, "match_bonus": 0, "total": 1500, "applied_live": 0}},
  {"slot": 2, "name": "bot0", "bot": true, "team": 1,
   "kills": 2, "deaths": 10, "assists": 0, "score": 200, "outcome": "loss"}
 ]
}
```

`uid` is the decimal string of the 64-bit Demonware uid (`player_profiles._uid_key`
wants bare digits, 1..24 of them). `kill_xp`/`match_bonus` are the retired
writer's split of one total; this server has no separate bonus stage because the
vendor scripts award the end-of-match bonus through `giveRankXP` like any other
event, so it is already inside the measured delta and is not re-derived.

## 5. (d) Match data — the existing wire path, finished

`src/codol/stats/codol_matchdata_server.c` already implemented C1's server match
record (`Scr_SetMatchDataDef 0x553bf0`, `Scr_SetMatchData 0x553600`,
`Scr_GetMatchData 0x551cd0`, `Scr_ClearMatchData 0x551e00`, the queued sender
`0x551d80 -> 0x5cf180 -> 0x58eba0 -> 0x707470`, and the readable dump at
`0x6205d0`), and `sendMatchData` wrote `matchdata/<def>_NNNN.mdr` plus a `.txt`
dump under `fs_homepath`. What it did not have was a delivery sink, so every
send logged "retained, no delivery sink" (`codol_matchdata_server.c:118-126`).

A sink is now installed once at startup
(`src/codol/assets/codol_asset_commands.c:243`, beside the `codol_profilePath`
registration) and writes the prepared record to
`<codol_profilePath>/match_data.mdr` with the same atomic write the rank report
uses — the lobby's resources directory being the only backend this server has.
**Nothing in the lobby consumes `match_data.mdr` today**; this closes the dead
end and gives the record a real destination, it is not a claim that the lobby
reads it.

## 6. Zombies (TASK 2)

### (a) Roster limited to the four Cyborgs — LOBBY-SIDE, already done, verified

`alpha0022/zm_characters.py` holds `mp/cyborgclasstable.csv` verbatim at
`:113-126` — four rows, `zm1 hea_zmlubushield / zm2 hea_zmcowboy /
zm3 hea_zmpunk / zm4 hea_zmgirl`, marketplace items 279 / 171 / 186 / 413
(`:130-135`) — and `filter_profile()` (`:282-357`) clears every non-core ZM
identity from the 48 `characterClasses` records, repoints `zmCharacterIndex` at
a survivor and re-seals the CRC. It runs on the **serve** path
(`dw-capture.py:825-843`), so the blob this server later reads is already
filtered. No server change was made or needed.

### (b) Zombies model in a `zm` zone — the server DID pick the MP soldier

Evidence that a native change was warranted:

- `scripts/codol/maps/mp/gametypes/_teams.gsc:610-620` `playerModelForWeapon()`
  is the only runtime caller of `codol_applyProfileCharacter`, and it produces
  `"tf"`, or `"sc"` for axis. Nothing in it consults the zone.
- `src/codol/stats/codol_profile_character.c:12-15`: `"tf"`/`"sc"` read
  `tfCharacterIndex`/`scCharacterIndex`; only `"zm"` reads `zmCharacterIndex`
  (C1 selector reader `0x68f890`, name pointers `0xccc93c`; alpha0022 measures
  `zmCharacterIndex` at blob `@0x17F1`, `characterClasses` at `@0x7E9`, stride
  40, 48 records).
- `codol_zoneType` (`src/sv_main.c:3341`) was consulted only in `SV_SpawnServer`
  (archives, `mp/constConfigStrings_<type>.csv`, weapon configstrings,
  gamestate) and in `scripts/codol/maps/mp/_load.gsc:349`. Never in the
  appearance path.
- `zm1`, `hea_zm` and `cyborg` had **zero** hits anywhere in `src/` or
  `scripts/`.

So a `zm` match composed `tfCharacterIndex`/`scCharacterIndex`, i.e. the
multiplayer soldier. The fix is native and profile-driven, in the appearance code
as required:

- `CODOL_ServerZoneType()` — new accessor for the category the mounted map was
  installed with, latched by `CODOL_SetServerMapIdentity`
  (`src/codol/snapshot/codol_sv_state.c`, `.h`). Deliberately the *mounted*
  category, not the dvar, which a later command could relatch.
- `zone_faction()` in `src/codol/player/codol_player_appearance.c` overrides the
  caller's faction to `"zm"` when that category is `zm`, right beside the
  profile read. The GSC is unchanged.
- `CODOL_ZombieCharacterGender()` in
  `src/codol/assets/codol_character_composition.c` reads the profile's zombies
  head item, resolves its name through `mp/coMarketplaceItems.csv` and looks it
  up in `mp/cyborgclasstable.csv` (column 3 is the head identity, column 2 the
  sex). `hea_zmgirl` ships only `*_zm_f_*` geometry, so without this the female
  Cyborg composes against male variant rows. An unresolved row keeps the
  caller's value rather than guessing.

Bots are deliberately out of scope here: `codol_applyBotCharacter` composes from
`mp/botclasstable.csv` through `CODOL_PublishCharacterComposition` directly
(`src/codol/player/codol_bot_loadout.c`), never through
`CODOL_SelectClientCharacter`, so a bot in a `zm` zone still wears an MP body.
Zombies enemies are a separate actor problem, not a bot-loadout one.

The rest of the `zm` composition path already existed: `"zm"` is faction index 2
in `codol_character_composition.c:39-40` and in the variant matcher
`src/codol/assets/codol_character_variant.c:12`, and under `zm` the const
configstring bank is `mp/constConfigStrings_zm.csv` (1625 rows), whose model
block already contains every part of all four Cyborgs — `register_inherited_name`
(`src/codol/snapshot/codol_configstrings.c:98-116`) hands back the existing const
index instead of allocating over it, which is structurally the thing
`zm_characters.py` section 2 warned about.

### The dangling `player_models_zm.txt` contract — retired

`match_server_control._prepare_zone_inputs` called
`zm_characters.write_player_models()`, whose target is
`zm_characters.SH1DED_RESOURCES = D:\CoD\sh1ded\resources` — a directory that
does not exist, for a server that was deleted, in a format
(`cf <clientState offset> <const CS_MODELS index>`) that this server has no
reader for. Every `zm` dispatch was paying a swallowed exception for a file with
no consumer. The call is removed (backup
`match_server_control.py.pre-cod4x`), with a comment recording that the native
server reads `zmCharacterIndex` from the profile itself.
`zm_characters.write_player_models` is left in place; it now has no caller
outside its own CLI and self-test.

## 7. Zombies startup crash (added mid-task from live evidence)

The lobby widened `CODOL_MAP_TYPES` to `mp,coop,zm` and dispatched
`map zm_zombie_training` with `codol_zoneType zm`. The server took a fatal script
runtime error before the map finished loading:

```
type undefined is not an object: (common_scripts/_dynamic_world.gsc, line 119)
  foreach player in level.players            (player_init)
 <- _dynamic_world.gsc:87 player_init();
 <- maps/mp/_load.gsc:55 thread common_scripts\_dynamic_world::init();
 <- _gamelogic.gsc:1244 maps\mp\_load::main();
 <- _callbacksetup.gsc:18 [[level.callbackStartGameType]]();
```

**Root cause.** `alpha0022/vendor/iw4/common_scripts/utility.gsc:2080-2086`:

```
isSP() { if ( !isdefined( level.isSP ) )
             level.isSP = !( string_starts_with( getdvar("mapname"), "mp_" ) );
         return level.isSP; }
```

IW4 had no multiplayer map that was not `mp_*`. CoDOL does: `zm_zombie_training`
is not, so `isSP()` returned **true** and `_dynamic_world::player_init()` took
its `if(isSP())` campaign branch, which walks `level.players` — an array
`_spawnlogic::init()` (`scripts/codol/maps/mp/gametypes/_spawnlogic.gsc:894`)
only creates later in the same `Callback_StartGameType`
(`_gamelogic.gsc:1479`). The ordering itself is vendor-faithful; the predicate
was the bug, and it mis-answers for every non-`mp_` zone, co-op included.

**Fix (WRITTEN, BUILT):** `level.isSP = false;` as the first statement of
`Callback_StartGameType()` in
`scripts/codol/maps/mp/gametypes/_gamelogic.gsc`. That is the mechanism `isSP()`
itself provides — it computes only when `level.isSP` is undefined — so this
answers the question rather than guarding the caller. A dedicated match server is
never singleplayer, whatever the map is called.

The same console also showed `Could not load rawfile "maps/mp/zm_zombie_training.gsc"`,
a missing `CodeCallback_ScriptCommand` label, and MP killstreak xmodels absent
from the zm zones — i.e. the MP gametype chain is being loaded for a `zm` match.
That, and what a real zombies gametype needs, is a separate workstream tracked in
`docs/CODOL_ZOMBIES_STARTUP_20260915.md`.

---

## 8. What was built and tested

- Windows cross-build from WSL, full rebuild
  (`make -B OS=Windows_NT CC=i686-w64-mingw32-gcc ... OBJ_DIR=obj/codol-win32 bin/codol_dedrun.exe`):
  clean, no warnings from the changed files.
  `bin/codol_dedrun.exe --codol-info` exits 0.
  - Deployed to **both** executable names at 17:47, SHA-256
    `3EC0E1CE7AC6F811D10C87FF489F1EF602348CA7FC690A163FF732CAB4C4CD0B`. No
    server was running at that point and none was started by this work.
  - The user then launched `codol_dedrun_next.exe` from that build (PID 106932)
    and played the 18:07 match of section 9b, then relaunched from
    `codol_dedrun.exe` (PID 90248).
  - **Current state of the two names.** Whichever one the user is running is
    locked, so each build goes to the free one and they drift apart. As of the
    last build here:
    - `bin/codol_dedrun_next.exe` = `8B1CDAA5AED477F9C749493E9C288E849417A0E3829D6F0056C3B9C32CECE5D0`
      — **this is the current build**, with the section 9b diagnostics. The
      launcher runs this name, so a plain relaunch picks it up.
    - `bin/codol_dedrun.exe` = `18EA64855A790BE8FB5335D85B3ADE695CED986C604F1F1FD2A017E12CA99691`,
      one build older (no report diagnostics), and locked by PID 90248.
    After stopping the server, copy `codol_dedrun_next.exe` over
    `codol_dedrun.exe` to bring the two names back together.
  - The GSC changes need no rebuild, but they do need a server restart: scripts
    are read at map load.
- Full Linux server build (`make -B`): exit 0, `Server done`,
  `bin/codol_dedrun` rebuilt as a 32-bit ELF. This build was **broken before
  this work**: `sv_main.c`'s boot-time heap checkpoint calls MSVCRT's
  `_heapchk` / `_HEAPOK` / `_HEAPEMPTY` unconditionally, so `sv_main.o` would
  not compile on Linux at all. Those three lines are now inside an
  `#ifdef _WIN32`, and the portable container-layout probe beside them still
  runs everywhere. Note that the first, failed Linux attempt unlinked the stale
  `bin/codol_dedrun` from 2026-09-08 before the compile error stopped it; the
  file there now is the fresh working rebuild, not that artifact.
- New fixture `tests/test_codol_match_report.c`, wired into `make test-codol`.
  32 checks, all passing: the XP delta equals the profile growth; per-row `uid`;
  bot rows carry neither; name escaping for `"` and `\`; win/loss/tie from the
  team score banks; consecutive reports partition rather than repeat; a departed
  player is still reported; a reconnect is one row; a map change cannot clobber
  an unconsumed report; an unset `codol_profilePath` writes nothing.
- End-to-end schema agreement, against the *live lobby module* in an isolated
  temp tree (`resources/` and `players/` were not touched): the bytes this
  emitter produced pass `json.loads`, `rank_writeback._validate` (returns None),
  and `_per_uid_amounts` routes each row to its own account;
  `maybe_apply` then credited `players/2758876527760990337.json` with exactly
  that row's 90 XP, 1 kill and 1 match, and created nothing for the row whose
  total was zero.
- `make test-codol`: every target up to and including the new one passes.
  Two long-standing breakages were repaired on the way, both unrelated to this
  work and both previously masked because the suite aborted before reaching
  them:
  - `test_codol_usability` could not link because the retained activation
    assembly now references the inventory-missile and corpse-damage services;
    five `unexpected` guards added to `tests/codol_usability_dependencies.asm`
    (the fixture never reaches those paths).
  - `test_codol_inherited` could not link because `codol_sv_state.c` calls the
    map sun-sample override unconditionally while the fixture links no game
    code; the two calls are now inside the file's `CODOL_SERVER` guard.
  - **Still broken, pre-existing, not touched:** `test_codol_native`
    (`makefile:443`) has drifted out of date with the modules it links — it now
    needs `codol_radar_types`, `codol_glass_snapshot`, `codol_glass_world`,
    `codol_action_slots`, `codol_killstreak_hud`, `codol_pmove_c1`,
    `codol_perk_runtime` and `codol_map_shadow`, several of which pull in the
    whole engine (`level`, `cm`, `Cvar_*`). Repairing it is its own job.
- Line endings: `src/codol/snapshot/codol_sv_state.c` was mixed (43 CRLF, 93 LF)
  and is now uniformly LF, matching the 337 pure-LF files under `src/codol`.
  Content unchanged apart from the edits described above.

## 9. Live evidence, and what is still NOT verified

### LIVE (observed, `bin/home/main/qconsole.log`, one run)

The user started `codol_dedrun_next.exe` (PID 106932, 17:51:16) from the build
deployed at 17:47, SHA-256 `3EC0E1CE...`, which carries every change in this
document except the Linux-only `_heapchk` guard of section 8. Map `mp_rust`
(launcher default; no lobby handoff, so this was an `mp` zone, not `zm`). One
human, `Nucleur`, connected and later disconnected cleanly. From that log:

- the connect packet carried `xuid 9d93949b116047cb`, and the next line is
  `CoDOL secure profile for client 0 (uid 11354582479263516619): attached` -
  that hex is exactly the decimal uid the lobby keys
  `players/11354582479263516619.json` by, and the lobby's `mpdata_s.<uid>` was
  found and accepted. `CODOL_MatchReportClientAttached` runs inside that same
  `if (ok)`, so the baseline capture executed.
- `CoDOL progress: restored 583 entries for client 0`, and on the way out
  `CoDOL progress: saved 583 entries for client 0 (uid 11354582479263516619)`.
- `CoDOL profile appearance: client 0 character 15 faction tf parts 9 arms
  fja_ghost_tf_s_vmchar_00` - `zone_faction()` passes an `mp` zone through
  unchanged, live. It does not exercise the `zm` branch.
- The disconnect ran to completion (`Going to CS_ZOMBIE` then
  `Going from CS_ZOMBIE to CS_FREE for client 0`), so the row freeze and the
  last-human `CODOL_WriteMatchReport("disconnect")` both executed without a
  crash and without a warning. No report was written, which is correct: the
  session had no XP and no kills/deaths/score, and the rule is not to overwrite
  a possibly-unconsumed report with an empty one.

So the read half of the contract and both new disconnect hooks are LIVE. The
write half is not - nothing was owed in that session.

### NOT verified

- The report has never actually been written by the running server. Everything
  about its contents is fixture- and lobby-module-tested only.
- The rank-up splash, the scoreboard rank column and a post-match credit landing
  in `players/<uid>.json` have not been observed.
- Multi-human crediting - the defect the per-row `uid` exists to fix - cannot be
  seen with one player and has not been seen.
- `match_data.mdr` has no consumer, and no `sendMatchData` fired in that run.
- The `zm` faction/gender selection has not been seen producing a Cyborg body.
  No `zm` match has reached spawn.

## 9b. First live match test, and what it proved (18:07 run)

The user played `mp_killhouse_sh`, gametype `war`, eight `Training` bots, got a
kill, and left. Result: no XP, no promotion, `players/<uid>.json` unchanged, no
`match_report.json`, and **no console line of any kind from the report**.

What the log does establish:

- The profile half is fine: `CoDOL secure profile for client 8 (uid
  11354582479263516619): attached` (twice, the second being a slot reuse), and
  progress restored/saved. The player took slot 8, the bots 0..7.
- The bots really are bots: `Going to CS_FREE for Bot Training 1..8`, so
  `client_is_bot()` excludes them and the last-human test should have fired.
- Kills were scoring at the gametype level: reliable `D 100` broadcast and
  `d 6 100` (CS_SCORES2), i.e. `_gamescore` ran and moved a team score.
- **No script runtime error anywhere in the run.** So `getRankExperience`
  resolved, and `rankingEnabled()` did not fault, which means
  `level.rankedMatch` is defined (`_globallogic.gsc:12-13` ran).
- `scr_xpscale` is registered natively with default 1 (`src/sv_main.c:3353`),
  so the "XP multiplied by an unset dvar" explanation is ruled out.

What the log cannot distinguish, and why: **`_rank::giveRankXP` has three silent
early returns** (vendor `_rank.gsc`: `rankingEnabled()`, and the two
`level.teamCount` gates), `syncXPStat()` has a fourth, and
`CODOL_WriteMatchReport` returned 0 without saying so. A server that awards no
XP and a server that correctly awards none looked identical from the console.
That is itself the defect this pass fixes.

### Fix 1 - the report now always says what it did

`src/codol/stats/codol_match_report.c` prints, for humans only:

- at profile attach: `CoDOL match report: client N uid U baseline X XP`
  (or `(UNREADABLE - this player's XP cannot be reported)`);
- when a player leaves: `CoDOL match report: client N uid U left with X XP,
  kK dD aA sS`;
- when a write is declined: `CoDOL match report: nothing owed (reason R):
  N row(s), H human, X XP, activity A - not written`, followed by one indented
  line per human row giving its uid, XP delta, baseline, current total and
  counters;
- when `codol_profilePath` is empty, a warning saying the result cannot reach
  the lobby.

Those four lines turn the next run into a decision:

| what you see | what it means |
|---|---|
| a `left with ... XP` line, then nothing | `CODOL_MatchReportHumansConnected()` is wrong - a client is still counting as human |
| `nothing owed ... 0 XP, activity 0` | the kill never reached `sess.kills/score`; the engine counters, not the report |
| `nothing owed ... 0 XP, activity 3` | the kill landed but no XP was committed - read the `rank:` lines below |
| `wrote N rows ...` | the report worked; check the lobby journal next |

### Fix 2 - the four silent XP gates now name themselves

`scripts/codol/maps/mp/gametypes/_rank.gsc` prints, for humans only (bots trade
kills continuously and would bury the console; `codolRankShouldTrace()` treats a
player whose `.isbot` is not yet set as human so nothing is hidden). This is the
same `println` idiom `updateRank()` already used for promotions:

- `rank: <name> kill NOT awarded - rankingEnabled false (level.rankedMatch ...,
  usingOnlineDataOffline ...)`
- `rank: <name> kill NOT awarded - a team is empty (allies A, axis B)`
- `rank: <name> kill NOT awarded - fewer than two players (A + B)`
- `rank: <name> kill +V XP (xpScale S, total OLD -> NEW)` on success
- `rank: <name> XP NOT committed - xpScale S, rankingEnabled R` from
  `syncXPStat`, which is the call the match report actually measures, so a
  silent skip there loses the whole match's XP.

`println` is gated by `g_no_script_spam`, which registers as 0
(`src/g_sv_main.c:744`), so these appear by default.

This is instrumentation of a path that was already unreadable, not a guess at
the cause. The cause is one of those five lines and the next run names it.

## 9c. Second live test named the bug: NA_BOT is zero (18:55 run)

The instrumentation of 9b paid for itself on its first run. The console said:

```
CoDOL match report: nothing owed (reason disconnect): 1 row(s), 0 human, 0 XP, activity 0 - not written
```

**One row, zero humans.** The player's own row was classified as a bot. Two
facts make that inevitable:

- `NA_BOT = 0` — and so is `NA_BAD` (`src/sys_net.h:53-54`). An un-set-up
  netchan therefore reads as a bot, not as "unknown".
- `SV_DirectConnect` attaches the secure profile at `src/sv_client.c:505` but
  does not call `Netchan_Setup` until `:569`. The report latched
  `client_is_bot()` at attach, i.e. 64 lines before the netchan existed.

So every human was recorded as a bot, `humans` stayed 0, the write was declined,
and — because the "nothing owed" branch also skipped bot rows — the per-row
detail lines printed nothing either. It also explains the 9b run's silence: the
same latch, the same slot.

That the row *existed at all* (`1 row(s)`) is itself evidence: a frozen row is
only kept when a counter is non-zero, so **the kill did reach `sess`**. The
engine counters were never the problem.

### The fix

A row exists only because a secure profile attached, and
`CODOL_AutoBindClientSecureProfile` refuses a zero uid while bots have none —
so **every stored row is a human by construction** and the question should never
have been asked:

- `src/codol/stats/codol_match_report.c` — the attach-time `client_is_bot()`
  latch is gone; `client_is_bot()` carries the NA_BOT/NA_BAD trap in a comment
  and is now only consulted where the netchan is real.
- Bot rows, which the lobby's format carries for scoreboard context, are
  synthesised at **write** time from connected slots that own no row.
- `CODOL_MatchReportHumansConnected()` counts a connected slot as human when it
  owns a row *or* is not NA_BOT, so it cannot be fooled by the same timing.
- Regression test in `tests/test_codol_match_report.c`: a client attached while
  its netchan still reads `NA_BOT` must count as human, be reported, and carry
  its own uid and XP. That test fails against the old code.

### Two more things from the same run, both resolved

- **`tableLookup miss: mp/statstable.csv column 4 value 'killstreak' ...` is
  benign.** `_utility.gsc:2152-2172 getWeaponClass()` probes the weapon table by
  name and *expects* the miss for non-weapons, falling through to
  `codol_getWeaponClass()` and `isKillstreakWeapon()`, which is what set the
  class to `killstreak`. The message is a `Com_DPrintf` diagnostic
  (`src/codol/script/codol_script_table.c:96`), not an error. Nothing to fix,
  and this build's 95-row table simply has no killstreak rows.
- **Kills were invisible in the console** because the vendor obituary goes to
  `games_mp.log` via `G_LogPrintf`, not to qconsole. `_damage.gsc`'s
  `Callback_PlayerKilled` now prints
  `kill: <killer> killed <victim> with <weapon> (<MOD>)` for any death a human
  took part in, immediately before the `rank:` line, so the two can be lined up.

### What "activity" means, and what it deliberately does not

A report is owed when a human row carries XP **or** kills/deaths/assists/score —
the things the lobby credits. Time played is deliberately *not* activity: a
report carrying nothing but a duration would still replace a report the lobby
has not consumed yet, which is exactly how a real match's XP would be thrown
away by an idle reconnect. Assists were missing from the sum and have been
added.

## 9d. Career counters for the client's stats page

XP now works end to end (two matches, +150 and +750, folded by the lobby, profile
at 484,972 XP / 6 kills / 2 matches). The client's 账户/战绩 page is still empty:
time played 0, points 0, hit percentage 0, longest win streak 0, K/D 0, longest
kill streak 0, last-15-minutes average score 0.

**The counters were never missing — nothing was reading them back out.** The
vendor scripts already maintain every one of them in the *session secure
profile*, through `_persistence::statAdd`/`statSet`/`statSetBuffered` ->
`setPlayerData`:

| member | written by |
|---|---|
| `totalShots`, `accuracy`, `misses`, `hits` | `_weapons.gsc:946-948`, `:1011-1012` (buffered; `_persistence::updateBufferedStats` flushes every 2 s) |
| `timePlayedTotal/Allies/Opfor/Other` | `_teams.gsc:201-216`, `:734` |
| `wins`, `losses`, `ties`, `winStreak` | `_gamelogic.gsc:497-531` |
| `killStreak` (best) | `_damage.gsc:295` |
| `kills`, `deaths`, `headshots` | `_damage.gsc` `incPersStat()` -> `_utility.gsc:648-652` -> `statAdd` |
| `score` | `_gamescore::givePlayerScore` -> `statAdd("score", delta)` |

So **no script counting was added**. `codol_match_report.c` measures them the
same way it already measures experience: value at profile attach, value at
report, difference. A row now carries a `"lifetime"` object:

```json
"lifetime": {"timePlayedTotal": 540, "kills": 9, "score": 1250,
             "hits": 31, "totalShots": 120, "killStreak": 4, "wins": 1}
```

Design points:

- **Resolved by name, never by offset.** `read_secure_stat()` walks
  `mp/playersecuredata.def` through `CODOL_ScriptProfileView` +
  `CODOL_ResolveStructuredField` + `CODOL_StructuredReadScalar`. A name this
  DDL does not declare is skipped and named once in the console
  (`mp/playersecuredata.def declares no scalar '<x>'`), so a wrong entry in the
  list is visible and harmless. A wrong *offset* would silently corrupt a
  career, which is why there are none.
- Integer-like kinds only (int32/byte/bool/short). A float or string member is
  refused rather than reinterpreted.
- Keys appear only when the delta is positive; an unchanged counter is omitted
  rather than sent as zero.
- **Derived members are deliberately absent.** `accuracy` and `kdRatio` are
  recomputed by `updatePersRatio` from the counters, and the delta of a ratio
  is meaningless. The lobby recomputes them from the lifetime totals.
- `killStreak`/`winStreak` are best-ever members, so their delta is a *rise*.
- The same partitioning as XP: after a successful report each member's baseline
  moves to the reported value, so consecutive reports never repeat a counter.

Fixture coverage (`tests/test_codol_match_report.c`): deltas rather than totals,
a member the DDL does not declare being absent, an unchanged counter omitted,
the best-streak rise, and partitioning across two reports. A `lifetime_has()`
helper scopes each assertion to one named row, because a row already carries
this-match `kills`/`deaths`/`score` keys with the same names.

**Open at the time of writing:** which members this DDL actually declares is
answered live by the `declares no scalar` warnings on the next connect; the
lobby half (crediting the deltas and writing them into the rendered
`mpdata_s.<uid>` DDL members) and the question of how the client refreshes that
page without a re-login are both in progress and are NOT claimed here.

## 9e. The DDL, decoded — and two bugs it exposed in 9d

`mp/playersecuredata.def` was decoded offline out of **`patch_code_post_gfx_mp.ff`**
(v11, checksum 158043991, 6665 bytes, 1680 leaves — the values recorded at
`docs/CODOL_ITEM_UNLOCKS.md:293`). The **base** zone ships a different def
(checksum 1491960907, 6664, 1679); the patch zone wins and is the live one.

The career page reads it **by name at runtime**: Scaleform
`CareerBaseController.getIntProp(prop, bSecureProfile)` ->
`GetPlayerData([prop], true)` -> C1 `GetSecurePlayerData` **0x00551EF0**
(`"mp/playersecuredata.def"` @ **0x00C46B24**, xrefs 0x00551F5C / 0x00551F85).
Every career call passes `true`, so the whole page comes out of `mpdata_s`.

### Two defects in the 9d implementation, both found by that decode

1. **Four of the names did not exist.** `misses`, `timePlayedAllies`,
   `timePlayedOpfor`, `timePlayedOther` are IW4 names CODOL does not declare;
   `setPlayerData` routes them to the legacy session store that is discarded at
   disconnect, so they could never have reported anything. Replaced with this
   client's actual members.
2. **`kills` and `wins` are float32 in this DDL** — the two headline numbers on
   the page — and `read_secure_stat()` accepted only integer kinds, so it was
   *silently refusing the most important stats it was written to collect*.
   Kind 8 is now read, reinterpreted and rounded, with NaN and out-of-range
   refused rather than truncated. The fixture models both as floats, so a
   reader that only handled integers now fails the test.

### What the page shows, and where it comes from

| field | member | kind |
|---|---|---|
| 游戏时间 | `timePlayedTotal` | total |
| 助攻数 | `assists` | total |
| 总得分 | `score` | total |
| 胜 / 败 / 平局场次 | `wins` (float) / `losses` / `ties` | total |
| 逃跑场次 | `escapes` | total |
| 最长连胜场次 | `winStreak` | max |
| 击杀 | `kills` (float) | total |
| 击中头部次数 | `headshots` | total |
| 最长连续歼敌数 | `killStreak` | max |
| 阵亡 | `deaths` | total |
| 胜率 | `winRatio` | stored x10 |
| 命中率 | `accuracy` | stored x10000 |
| 杀敌/阵亡比 | **none** | ActionScript divides `kills` by `max(deaths,1)`; the DDL's `kdRatio` is never read |

So the server reports counters and max-members only; `accuracy`, `winRatio` and
`kdRatio` are recomputed by the lobby from the totals, which is what 9d already
said and is now confirmed against the consumer rather than assumed.

### "Last 15 minutes average score" is 15 **matches**, and it is the other blob

`SF_UI_CAREER_RECENT_SCORE` is 最近15场比赛得分. `CareerController` keeps
`FIXED_RECENT_LENGTH = 15` and averages `score` over the last fifteen non-empty
entries of a **30-entry ring in the PUBLIC `mp/playerdata.def`** —
`recentMatches[30]` (stride 40) with head `recentMatch` — read by C1
`PlayerData_ReadRecentMatches` **0x00462B50** into **0x016DBDF8** and handed to
Flash by `AS_GetRecentMatchStats::Invoke` **0x005AC310**. An entry counts as
empty when `rounds == 0` (**0x0046308B**).

It reads zero because the live `resources/mpdata.<uid>` has `recentMatch = 0`
and all thirty records at their defaults. **This is not fixed here and must not
be faked:** `mpdata` is the blob the *client uploads*, the lobby deletes it at
boot, and the client clobbers anything seeded into it about 25 s after login.
Populating the ring is its own job — either seeding it or merging at upload
time. The separate lifetime `scorePerMinute` (`mpdata_s` @0x1504) *is* now
populated by the lobby from `score` and `timePlayedTotal`.

It is **not** a Demonware stats row: service 4 is leaderboards only (tasks 3/4)
and nothing on the career path touches it.

### Lobby half (done, verified offline)

`rank_writeback` passes each row's `lifetime` through per uid; `player_profiles`
accumulates it and `ensure_blob` renders it into the real DDL members, resolved
through `playerdata_editor`'s own `by_path` — **no offset is hardcoded**. Every
written member is proved by rendering a blob and decoding it back:
`score` 0x13F4, `kills` 0x114C (float), `deaths` 0x111C, `headshots` 0x1134,
`hits` 0x1138, `totalShots` 0x1534, `wins` 0x19FC (float), `losses` 0x1158,
`ties` 0x1518, `winStreak` 0x19F8, `killStreak` 0x1148,
`timePlayedTotal` 0x1530, plus recomputed `accuracy` 0x000C, `kdRatio` 0x113C,
`winRatio` 0x19E8 and `scorePerMinute` 0x1504. Self-tests: `rank_writeback`
67/67, `player_profiles` 50/50.

**The lobby must be restarted** for this: `dw-capture.py:24-25` imports both
modules at startup. The match server does not need one.

## 9f. Why the career page went stale — and it was us

**Correction first.** Earlier notes in this file, and
`alpha0022/docs/playerdata_audit.md:73` and `rank_persistence.md`, say
`0x00592FA6` is C1 refusing to refetch the secure profile while connected. It
is not: that guard belongs to the **public** `mpdata` task (callback
`0x00592F30`, requester `0x00592E50`, blob `0x0722D068`, flag `0x0723D095`).
Nothing on the `mpdata_s` path is gated by `cls.state` at all. The claim has
been removed from §1; it was never load-bearing for the contract, but it was
wrong.

### The real mechanism

C1 keeps the secure profile in one buffer, `0x0205C598`, behind two flags,
`0x06C3D3D9` and `0x06C3D3DC`. Its per-frame Demonware tick (`0x004D8EE0`, from
`0x006FF0A9`) re-fetches the profile — **DW 10/3 GETFILE `"mpdata_s"`** via
`0x004D9900` — whenever it finds *both* flags zero and the lobby connected
(`0x00723030`/`0x00A34DA0`); the completion `0x004D9200` -> `0x004D98E0` sets
them again. `GetRank` (`0x0058EFE0`, via `AS_GetPlayerRank 0x005AA970`) and the
whole Scaleform career view read `0x0205C59C` = that buffer + 4, synchronously,
on draw. So the page updates with no relogin and nothing for the server to push
— roughly 200 ms after those flags go to zero.

**`CL_HandleDisconnect` (`0x004960E0`) is the only thing that clears them**
(`0x00496283`/`0x0049628A`, when the `cls.state` captured at `0x004960F6` is
>= 8) — and only *after* comparing the disconnect reason against a bypass list.

**We were sending the one reason on that list.** `codol_script_exitlevel_trace.c`
sent `t "EXE_MATCHENDED"`, which matches at `0x00496114`, jumps to `0x00496116`
and raises the silent level-5 notice **without ever reaching the
invalidation**. The string chosen for a quiet exit was, by itself, the reason
the career page never updated. The rest of the bypass list is
`EXE_MIGRATIONABORTED`, `EXE_MIGRATION_IN_PROGRESS`, `hostquit`,
`EXE_PLAYERKICKED*`, `roundsdone`, `XBOXLIVE_SIGNINCHANGED`.

Corroboration: 195 of 828 wiretap leaves show a 10/3 `mpdata_s` at +0.13–0.42 s
(next-frame latency), and the rate collapsed after 09-10 — the mtime of the
exitlevel file.

### The fix, and what it costs

`CODOL_MATCH_END_REASON` in `codol_script_exitlevel_trace.c` is now
`EXE_MATCHEND_PARTNER_LEAVE` (`0x00C47E14`): the one non-bypassed string that
still carries dedicated match-end handling (`0x00496294..0x004962BC`). Any
non-bypassed reason works; this is the closest to a quiet leave.

**The cost is cosmetic and real:** a level-4 notice
(`Com_Error(4, loc("EXE_SERVERDISCONNECTREASON") + loc(reason))`) instead of
the silent level-5 one. That is a deliberate trade — a player who cannot see
the match they just played is the worse bug — and the `#define` is the whole
knob if the wording turns out to be unacceptable. The side effects of the
handler's `0x00624FC0(handler, 1)` call are **unverified**.

Ordering is race-free: `match_report.json` is written at `"gameended"`
(`codol_script_matchdata.c`) before `exitLevel` runs, and the lobby folds the
pending XP inside its own 10/3 handler, so the refetch always sees the updated
blob.

**Not done:** patching C1 at `0x00496114` to skip the bypass. A 17-byte code
cave would give perfect cosmetics; this server does not modify the client.

### The four candidates, closed with VAs

| candidate | verdict |
|---|---|
| in-match stat ingest | `statResponse 0x00496A6B` is `Cmd_Argv(1)` + `atoi` only; `svc_statscommands` unused |
| match-end blob push | the GETFILE completion is the **only** writer of `0x0205C598`/`0x9C` |
| Demonware push | all 29 cases of the map at `0x00A340F4`/`0x00A34080` (vtable `0x00C7B42C`) reach no storage path and never write those flags |
| Flash refresh task | the career view fires no task id; the account view is task 1027, wallet only |

Bare OOB `disconnect` is also dead: `CL_DisconnectPacket 0x00496300` ignores it
within 3000 ms of the last packet (`0x00496397`) and skips the handler on an
empty reason (`0x004963BA`).

## 9g. LIVE: the corrected member list is confirmed

Build `B7CCFC242B3A472CE00B3D00E247635172E842EA652D420A3C43855DAB9DF5AE`,
PID 21224, `mp_rust`, one human connecting:

```
CoDOL match report: client 0 uid 11354582479263516619 baseline 489662 XP
CoDOL secure profile for client 0 (uid 11354582479263516619): attached
```

Two things this proves that could not be settled offline:

- **Not one `declares no scalar` warning.** All 22 members of the corrected
  list resolve in the mounted `mp/playersecuredata.def`, by name, at runtime.
  The IW4 names removed in 9e were the only wrong ones.
- The baseline reads **489,662 XP**, up from the 484,972 recorded before this
  pass, so the XP fold really is landing in the profile the server then reads
  back — the loop is closed at both ends.

Still unproven live: a match's counters actually moving (no kill yet in this
session), and the career page refreshing after the `EXE_MATCHEND_PARTNER_LEAVE`
change of 9f.

## 10. How to verify live

0. Stop the running server, then relaunch it. The GSC changes above need a
   script reload, and the binary changed. The launcher runs
   `codol_dedrun_next.exe`; the diagnostics build is in that file (see
   section 8 for which name is current and why).
1. Confirm nothing is running on udp/17733 and that `dw-capture.py` is up.
   Start the server with `bin/START-CODOL-SERVER.cmd`.
2. In `bin/home/main/qconsole.log`, look for
   `CoDOL secure profile for client 0 (uid <decimal>): attached`. If it says
   `no mpdata_s in codol_profilePath`, the lobby has not served that uid yet.
3. Join from the lobby and read the rank badge on the scoreboard. It comes from
   clientState `+0xA0`, written by `setRank` at `_rank.gsc:196`; a wrong value
   there means the profile conversion, not the wire.
4. Get one kill and watch `bin/home/main/qconsole.log`. Exactly one of these
   must appear, and it is the answer:

   ```
   findstr /C:"rank: " bin\home\main\qconsole.log
   ```

   - `rank: <you> kill +50 XP (xpScale 1, total N -> M)` - XP works; keep
     killing until `promoted <name> from rank A to B` appears.
   - `rank: <you> kill NOT awarded - ...` - the gate named on that line is the
     blocker. `a team is empty` means `level.teamCount` is not counting the
     bots; `rankingEnabled false` means `level.rankedMatch` is false and the
     dvars it reads (`onlinegame`, `xblive_privatematch`) need defaults.
   - `rank: <you> XP NOT committed - ...` - XP was awarded but never written to
     the secure profile, so the report would have nothing to carry.
5. End the match, or just leave. Expect these, in order:

   ```
   findstr /C:"CoDOL match report" bin\home\main\qconsole.log
   ```

   - at connect: `CoDOL match report: client N uid <decimal> baseline X XP`
   - on leave:   `CoDOL match report: client N uid <decimal> left with X XP, kK dD aA sS`
   - then either `CoDOL match report: wrote N rows (M human, X XP, reason
     disconnect) to <alpha0022>/resources/match_report.json` **or**
     `CoDOL match report: nothing owed (reason disconnect): ...` plus one line
     per row. The second form tells you whether the XP delta or the counters
     were zero; see the table in section 9b.
   - If none of the three appear at all, the report module never ran - that is
     a different bug from "nothing was owed", and the absence is the evidence.
6. Return to the lobby. The next storage GETFILE consumes it: check
   `alpha0022/resources/match_report.journal.log` for a
   `rank_writeback: player_profiles: <uid> +X XP level A->B` line, and
   `alpha0022/players/<uid>.json` for the new `total_xp` and a new `history`
   entry. The report should now be `match_report.applied.<ts>.json`.
7. Multi-human: repeat with two accounts and confirm two distinct
   `players/<uid>.json` files each moved by their own row's total — that is the
   defect this change exists to fix, and it cannot be seen with one player.
8. Mid-match disconnect: leave before the game ends and confirm the report is
   written with `"reason": "disconnect"` once the last human is gone.
9. Zombies: dispatch a `zm` room. The `isSP` fix should carry startup past
   `_dynamic_world`; the next failures are catalogued in
   `docs/CODOL_ZOMBIES_STARTUP_20260915.md`. If a zm match does reach spawn,
   `CoDOL profile appearance: client 0 character N faction zm` in the console is
   the line that proves the Cyborg record was used instead of the MP soldier.
