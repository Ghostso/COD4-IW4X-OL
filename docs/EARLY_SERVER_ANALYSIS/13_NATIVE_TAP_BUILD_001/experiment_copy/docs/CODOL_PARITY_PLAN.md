# CoDOL server parity plan (2026-09-09)

Goal: bring the native server at this repository to parity with vanilla
Call of Duty Online 1.1.1.13, so that a C1 client gets the same match a retail
server would give it.

Companion documents:

- [CODOL_PARITY_INVENTORY.md](CODOL_PARITY_INVENTORY.md) — the full gap
  inventory, seven sections, one row per feature with evidence pointers.
- [CODOL_SOURCE_LAYOUT.md](CODOL_SOURCE_LAYOUT.md) — where the code lives.
- [CODOL_PLAYER_ACTION_AUDIT.md](CODOL_PLAYER_ACTION_AUDIT.md) — per-action status.
- `CODOL_IMPLEMENTATION_PASS.md` — the running work log.

Nothing in this plan was built, run or tested. It is offline source and binary
inspection only, which is what the current writing pass allows. Every claim
carries a file and line or a measured address; where a claim could not be
settled offline it says so and names the run that would settle it.

## Executive summary

The server already gets a real C1 client through the lobby, into a map, onto a
team, through the class panel, and into a body that walks, sprints, crouches,
jumps, dives, aims, shoots, reloads, throws grenades and dies. What it does not
yet do is run a **match**.

The single largest cause is narrower than expected. C1 kept IW3's
server-to-client command format but renumbered the command letters, and five
senders in the retained code still use the old ones. Because every old letter
is also a *valid* new letter, they do not fail — they execute the wrong
command. Setting a client dvar opens a menu. Equipping a grenade overwrites a
team score. That is why the match scaffolding looks implemented and behaves as
if it is not.

Five things, in order, turn this into a playable match:

1. Answer the client's scoreboard request. It asks with `s`, which the server
   does not recognise, and the correct producer for the reply exists but is
   dead code (item 1.1).
2. Send team scores on the letters C1 actually reads (item 1.2).
3. Stop `setclientdvar` from opening menus. 89 script call sites depend on it,
   including the end-of-game summary (item 1.3).
4. Stop equipment gives from corrupting the scoreboard (item 1.4).
5. End the match, and publish the frozen bit so the end holds (items 1.5, 1.9).

Beyond that the work is ordinary implementation, sized in phases below. Two
items previously believed to need a live experiment were settled offline during
this pass: the identity of the `s` command, and the damage-indicator field
offsets.

## Implementation status (2026-09-10)

Phases 0, 1 and 3 are implemented. Phase 2 is implemented except for the two
items blocked on identification work. Phase 4's missing-builtin item is closed
and its killcam is unblocked; the rest of phase 4 and phase 5 need a live
client or are large subsystems. Phase 5's persistence item is implemented.

Everything below is verified as far as it can be without a client: the server
boots, loads every installed map, and runs every gametype that has a script,
with no script errors. Nothing has had a C1 client connect to it.

| item | state | note |
|---|---|---|
| 0.1 unhandled client command trace | done | developer only, prints the whole line |
| 0.2 reliable letter census | done | one line per distinct leading byte, at the single send choke point |
| 1.1 scoreboard | done | `s` accepted, `CODOL_SendScoreboard` wired, skill gate warns instead of aborting, rows clamped to 19 |
| 1.2 team scores | done | `setteamscore` sends `C`/`D`; configstrings 5 and 6 published every frame |
| 1.3 setclientdvar | done | singular and plural now send `s` |
| 1.4 offhand notice | done | both sites send `y` |
| 1.5 match end | done | `t "EXE_MATCHENDED"`, behind `codol_exitToLobby` |
| 1.6 fast restart | done | sends `k` |
| 1.7 client vocabulary | done | covered by 0.1 |
| 1.8 map restart leak | done | an unchanged map reuses its mounted archives |
| 1.9 frozen bit | done | native state now uses C1 `0x800` directly |
| 2.1 shellshock bit | done | native `0x10000` published as C1 `0x8000` |
| 2.2 rank and XP | done | client state `+0xA0` is the scoreboard rank column and `+0xA4` its neighbour; both are published from the progression store. `J`/`K` remain unsent: they make the client recompute from its own data |
| 2.3 damage feedback | done | `0x0d8`, `0x0dc`, `0x0e0`, `0x17c`-`0x188` |
| 2.4 HUD refresh and letters | done in part | `F 4`/`F 5` on weapon and offhand change; `setClientSubtitle` as C1's `]`. `L` playercard rows and `S` killcam FX remain |
| 2.5 named unpublished fields | done in part | `viewmodelIndex`, the view-angle clamps, the prone trio, `viewlocked`, `viewlocked_entNum`. The remote-camera fields have no retained counterpart and belong to phase 4 |
| 2.6 objectives | done | section 5 identified and written; seeded from the per-client array the engine already filters. The gate stays off while nothing is live |
| 2.7 admin chat | done | all seven broadcast sites use `SV_CHAT_CMD`, `V` under CoDOL |
| 3.1 map loading | done | all 15 installed multiplayer zones load; one script fix was needed, for `mp_bog_sh` |
| 3.3 zone asset dispatch | done | no zone hits the unhandled types; they need a documented skip, not a reader |
| 3.4 gametypes | done in part | all 14 with scripts load; `conf` and `infect` newly written; `combat` needs bots first |
| 3.5 entity truncation | assessed | a truncation, not an overflow, and it already warns; enlarging four assembly stack frames is a poor trade |
| 4 missing builtins | done | none are missing on the load path; the candidates all live in files that never compile |
| 4 killcam | unblocked | `forcespectatorclient` added; the script wrote a field the server did not define, so it errored on the first death and never ran |
| 5.1 profile persistence | done | IW4-only playerdata roots written to `<fs_homepath>/codol_progress/<uid>.txt` and restored on attach |
| hygiene | done | the three dead menu senders corrected so a re-registration cannot drop a client |

Two switches exist for bisecting a regression without a rebuild:

- `codol_publishExtendedPlayerState` (default on) withholds the damage block and
  the viewmodel/view-lock/prone block, the two families mapped from measured
  field names rather than from a live capture. Read every frame.
- `codol_exitToLobby` (default on) turns the match-end leave off, for a
  dedicated-server rotation instead of a lobby return.

What to watch for on the first live run, in order: the client spawns and moves
as before; the scoreboard key produces rows and the log shows an `s` arriving
about every two seconds; team scores track kills; no menu opens by itself; a
grenade give no longer moves a team score; a death starts a killcam; the
reliable letter census contains no letter outside appendix A.

### What is genuinely left

Everything below needs a C1 client in a match. There is no more of this plan
that can be written blind and known to be right.

- **Phase 4.** The killcam is unblocked and its whole server contract is in
  place, but no death has ever started one here. All thirteen killstreak
  scripts compile and initialise on every boot; what has never happened is a
  player earning and using one. The remote-camera player-state fields have no
  retained counterpart, so they need new server state, and there is no producer
  to drive that state until a remote streak actually runs. Vehicles still need
  their factory dispatch and snapshot seeding finished.
- **Phase 5's lobby.** Still the external Python process. Replacing it means
  implementing the Demonware session, party, playlist and store services
  natively, and it is the largest single piece in the project. The match-data
  upload is also a draft with no backend to talk to.
- **`combat`.** Blocked on bots, not on script authoring.
- **Proving the rest.** Every map and gametype result in this document is the
  server reaching a settled level. Team scores, the scoreboard, the match end,
  the damage indicators, rank on the board and objectives on the compass are
  all written and none has been seen on a screen.

## 0. Method, and what changed during this pass

The inventory was assembled from the server sources, this repository's docs,
and the alpha0022 Python prototype's reverse-engineering notes. Its highest
priority rows were then re-verified directly, and four of them changed:

1. **The unknown client command `s` is now identified.** It is the scoreboard
   request. C1 sends a bare `s` from four sites that all run the same idiom:
   `if (cg->scoresRequestTime + 2000 < cg->time) { cg->scoresRequestTime = cg->time; CL_AddReliableCommand("s"); }`
   — the IW3 `score` command, renamed to one letter. Measured by static export
   of `C1.exe` 1.1.1.13: string `0xc41e50`, sender `CL_AddReliableCommand`
   `0x493bb0`, call sites `0x436f4a` (scores-down key), `0x45fe42` and
   `0x4601fd` (HUD/prediction), `0x465a05` (inside `CG_SetSingleClientScore`
   `0x465990`, when the local client is missing from the board). The server
   handles `score` and not `s`, so it never answers.
2. **Most reliable-command letters were already corrected**, and my first scan
   said otherwise because it did not honour the `%ifdef CODOL_SERVER` branches
   in the assembly. Re-run with preprocessor state applied, only five senders
   are still wrong. That is a much smaller job than the inventory implies.
3. **Team scores have two routes, not one**, and both are measured: the
   reliable pair `C`/`D` and configstrings 5 and 6. They write the same two
   client fields.
4. **Vision sets are fully implemented** on both routes. The inventory row
   claiming otherwise was stale.

Two independent exports agree on the C1 command table — this repository's
`docs/CODOL_C1_COMMAND_DISPATCH.json` and alpha0022's appendix B — on every
handler address used below, so the letter map is treated as settled.

## 1. The headline: the server-to-client command contract

C1 kept IW3's dispatch shape (one letter, then arguments) but **renumbered the
table**. Argument shapes are unchanged; only the letters moved. A wrong letter
is therefore never a no-op: it silently executes a different, valid command.

Five senders are still on IW3 letters, and each one does real damage:

| retained sender | sends | C1 reads it as | consequence |
|---|---|---|---|
| `GScr_SetTeamScore` axis branch, `_g_scr_main_mp.asm:6524` | `G <score>` | nothing — C1 has no `G` | "Unknown client game command"; axis score never updates |
| `GScr_SetTeamScore` allies branch, `_g_scr_main_mp.asm:6542` | `H <score>` | hide scoreboard / close pause menu | allies score never updates, and the board is dismissed under the player |
| `PlayerCmd_SetClientDvar`, `_g_client_script_cmd_mp.asm:3484` | `v <name> <value>` | open a script menu by index | 67 script call sites push a menu open with a garbage index instead of setting a dvar |
| `PlayerCmd_SetClientDvars`, `_g_client_script_cmd_mp.asm:3558` | `v …` | same | 22 more call sites |
| `G_GivePlayerWeapon` and `G_SetEquippedOffHand`, `_g_weapon.asm:1017` and `:1137` | `C <offhandIndex>` | **team score 1 = offhandIndex** | every grenade or equipment give overwrites the axis score with a weapon index |

Two more, outside the assembly:

| sender | sends | C1 reads it as | consequence |
|---|---|---|---|
| `SV_MapRestart` fast path, `sv_main.c:3910` | `m` | stop music | a fast restart never restarts the client |
| admin broadcast, `sv_cmds.c:107`, `plugin_exports.c:463`, `plugin_internal.c:148`, `sv_main.c:2226` | `h "<text>"` | stop local sound, index `atoi("<text>")` | admin chat is invisible and stops a sound instead |

Everything else is already right: `a b c e f g h l m n o p q r u v w z A B D E H N O P Q R` are
either correct in the retained code or produced by CoDOL-native senders.

Three assembly senders are wrong but **dead** in this build, because
`scr_vm_main.c` registers CoDOL-native replacements for their builtins:
`PlayerCmd_OpenMenu`/`OpenMenuNoMouse` (`t`, which at CL level is a
**drop-with-reason**, not a cgame command), `PlayerCmd_CloseMenu` (`u`), and
`PlayerCmd_CloseInGameMenu` (`L`). Correct them anyway so a future
re-registration cannot reintroduce a client drop.

## 2. Phase 0 — instrumentation, before any behaviour change

Cheap, and it converts most remaining "unverified" rows into facts on the next
run the user makes.

| # | add | where | answers |
|---|---|---|---|
| 0.1 | log the full text of an unhandled client command | `g_cmds.c:1007`, before the `GAME_UNKNOWNCLIENTCOMMAND` reply | any further client command we do not implement |
| 0.2 | in developer builds, print each distinct outbound reliable letter once, with the first payload | `SV_SendServerCommand_IW`, `sv_main.c` | proves which letters actually leave the server, and catches any sender this audit missed |
| 0.3 | print the "never non-zero" player-field list on demand, not only every 30 s | `codol_frame_builder.c:55` | turns the unpublished-field guesswork in inventory §3 into a measured list |
| 0.4 | count and print retired archives and their bytes after each mount | `codol_asset_registry.c:300` | confirms the restart leak in item 1.8 |

Guard 0.2 behind `com_developer` and a per-letter latch so it cannot flood.

## 3. Phase 1 — P0: a match that starts, scores, and ends

This is the smallest set that turns the current "spawn and walk around" into a
match. Ordered by dependency.

### 1.1 Scoreboard, end to end

**Wrong.** Three independent faults. `Cmd_Score_f` (`g_cmds.c:743`) calls the
retained IW3 `SendScoreboard`, which emits `b` with **seven** integers per
client; C1's `b` handler (`0x4693B5`) expects a count, three header integers,
then **ten** per client. The correct producer,
`CODOL_SendScoreboard` (`codol/stats/codol_scoreboard_sender.c:11`), is written,
correct, and **called by nothing** — it has no header and no caller. And the
client asks with `s`, which the dispatcher does not know.

**Evidence.** C1 `b` layout: alpha0022 appendix B and
`docs/CODOL_SCOREBOARD_CONTRACT.md:30`. Correct formatter:
`codol_scoreboard_wire.c:24-28`. `s` identification: §0 above.

**Fix.**
- Add `s` beside `score` in the dispatcher at `g_cmds.c:962`.
- Give `codol_scoreboard_sender.c` a header and call `CODOL_SendScoreboard`
  from `Cmd_Score_f` under `CODOL_SERVER`.
- Soften the skill gate. Today a single client without a `skills/<mode>`
  profile aborts the whole send (`codol_scoreboard_sender.c:46-50`), so one bad
  profile means nobody ever sees a board. Warn once per client and send that
  row with skill 0.
- Clamp to 19 rows, not 64 (`codol_scoreboard_wire.c:17`). C1 clamps its own
  row count to `0x13` at `cg+0xBEB18`.

**Done when.** Holding the scoreboard key shows populated rows, and the log
shows an `s` arriving about every two seconds while it is held.

### 1.2 Team scores

**Wrong.** `setteamscore` still sends IW3 `G`/`H`. `updatescores` and
`updatedmscores` were already corrected to `C`/`D`/`E`. Configstrings 5 and 6
are never published at all.

**Evidence.** `C` writes `cg+0xBEB20`, `D` writes `cg+0xBEB24`; configstrings
5 and 6 hold the same two values and feed the win/lose banner at `0x550960`
(alpha0022 `matchend_fix.md:90`, `matchflow_status.md:45-62`, settled live:
CS 6 is TEAM_ALLIES, blue, top of the HUD). The already-corrected
`PlayerCmd_UpdateScores` pins the sides: `level+0x200` → `C`, `level+0x204` →
`D` (`_g_client_script_cmd_mp.asm:4413-4434`). With `teamScores` at
`level+0x1fc` (`g_shared.h:132`) and `TEAM_RED = 1`, `TEAM_BLUE = 2`
(`q_shared.h:786-788`), that is axis → `C` → CS 5 and allies → `D` → CS 6.
`GScr_SetTeamScore`'s branch test is `scr_const.allies` at offset `0xc`
(`scr_vm.h:202`), so its `_20` branch is allies.

**Fix.**
- `_g_scr_main_mp.asm:6524`: `0x47` → `0x43` inside `%ifdef CODOL_SERVER`.
- `_g_scr_main_mp.asm:6542`: `0x48` → `0x44` inside `%ifdef CODOL_SERVER`.
- Add native `CS_SCORES1` (6) → CoDOL 5 and `CS_SCORES2` (7) → CoDOL 6 to the
  mapping table in `CODOL_RefreshServerMapConfigstrings`
  (`codol/assets/codol_sv_assets.c`, the table that already maps 9, 11, 12,
  821, 822, 823), so a late joiner gets the scores in its gamestate.

**Done when.** Both HUD scores track kills, and a late joiner sees them
immediately.

### 1.3 `setclientdvar` and `setclientdvars`

**Wrong.** Both send `v`, which C1 dispatches to a script-menu open.

**Evidence.** C1 `s` → `0x469891` → `CG_SetClientDvarFromServer` `0x468A00`,
with a whitelist (`cg_objectiveText`, `cg_objectiveIcon`, `hud_drawHud`,
`g_scriptMainMenu`, `ui_opensummary`, `cg_unlockFlagSet`, `cg_vo_prefix`) and
`Dvar_SetFromServer` otherwise. 89 call sites in the loaded script corpus.

**Fix.** `_g_client_script_cmd_mp.asm:3484` `0x76` → `0x73`, and `:3558`
`0x76` → `0x73`, both inside `%ifdef CODOL_SERVER`. The argument shape,
`%c <name> "<value>"`, already matches.

**Done when.** No spurious menus open during a spawn, and a dvar the scripts
set is observable on the client.

### 1.4 Offhand equip notice

**Wrong.** `C <offhandIndex>` is C1's "team score 1". Because IW3's letter for
this notice happens to equal a valid C1 letter, this fails silently and
corrupts the axis score on every equipment give.

**Evidence.** `_g_weapon.asm:1017` (inside `G_GivePlayerWeapon`, right after
`BG_AssertOffhandIndexOrNone`) and `:1137` (`G_SetEquippedOffHand`). C1's
equivalent is `y` → `CG_SetEquippedOffHand` `0x486DD0`, same `%c %i` shape.

**Fix.** Both sites `0x43` → `0x79` inside `%ifdef CODOL_SERVER`.

**Done when.** Throwing a grenade no longer changes a team score, and the
offhand icon matches the equipped item.

### 1.5 Match end

**Mostly already written, and blocked by items 1.1 and 1.3.** Reading IW4's
`endGame` (`vendor/iw4/maps/mp/gametypes/_gamelogic.gsc:2037-2215`) against
C1's accepted sequence shows the script already performs almost the whole
ritual, and every step of it is currently lost on the wire:

| script does | reaches C1 as | today |
|---|---|---|
| `player setClientDvar("ui_opensummary", 1)` (`:2093`) | `s ui_opensummary 1` — and `ui_opensummary` is one of the seven names on C1's `s` whitelist | sent as `v`, so it opens a menu by garbage index instead. **Fixed by item 1.3.** |
| `setDvar("scr_gameended", 1)` (`:2158`) | a replicated dvar the `.menu` layer reads to blank the HUD | works |
| final scoreboard | `b` | wrong sender. **Fixed by item 1.1.** |
| `freezePlayerForRoundEnd` (`:2101`) | `pm_flags` frozen bit | not published. **Item 1.9.** |
| `visionSetNaked("mpOutro", 0.5)` (`:2118`) | `N "mpOutro" 500` | sent correctly, but `mpOutro` is not a resident vision asset in C1 and an unknown name silently no-ops. `black_bw` is the only vision name hardcoded in the client. |
| `spawnIntermission` for every player (`:2189`) | intermission player state | partially |
| `exitLevel(false)` (`:2215`) | nothing | **the real gap** |

**The real gap is the exit.** The string `EXE_MATCHENDED` does not appear
anywhere in `src/`. On retail the client follows the server into the next map;
under CoDOL the client arrived from the lobby and expects to return there for
its after-action report. `t "EXE_MATCHENDED"` is the only server-sendable
leave, and the whole chain was re-verified against `C1.exe` during this pass:
`CL_GetServerCommand` indexes a table at `0x4878D8` with `firstChar - 'd'`, so
`t` (index 16) selects entry 2 of the jump table at `0x4878C8`, which is
`0x48782E`. That arm raises `Com_Error(4, "EXE_SERVER_DISCONNECTED")` when the
command has no argument, and otherwise passes `Cmd_Argv(1)` to `CL_Disconnect`
at `0x4960E0`, which string-compares it against `EXE_MATCHENDED` at `0xc47D30`
(reference at `0x4960FF`) and raises the benign front-end notice. The same
table shows `d` (index 0) going to the configstring handler and `k`/`x`
(indices 7 and 20) sharing the restart arm, so none of the three ever reach
cgame. `disconnect` and `disconnectforoutro` are client-only console commands
and cannot be reached from the server. Corroborates alpha0022
`matchend_fix.md` §A.2, §A.3.

**Fix.** Land items 1.1, 1.3 and 1.9 first; then most of the end sequence
starts working with no new code. Add only the exit: `CODOL_Scr_ExitLevel`
(`codol/script/codol_script_exitlevel_trace.c`) is already the single funnel
every gametype passes through, so send `t "EXE_MATCHENDED"` there, behind a
cvar so a dedicated-server rotation can be chosen instead of a lobby return.
Optionally send `q 14` (`mp_eog_summary`) as well; `q 13` is the scoreboard and
`q 8` the endgame-update panel. C1's `q` path has no intermission gate, so none
of this needs `pm_type = 6`, which alpha0022 measured as a one-way door that
freezes the reliable acknowledgement ring.

**Done when.** A `scr_dm_scorelimit` win shows the summary, holds it, and
returns every client to the lobby, and the server survives to host again.

### 1.6 Fast restart

**Wrong.** `sv_main.c:3910` sends `m` (stop music). The map-change path at
`:3833` already sends the correct `k`/`x`.

**Fix.** `'m'` → `'k'` under `CODOL_SERVER`, matching the comment already at
`:3828-3831`.

### 1.7 Handle, or deliberately ignore, the rest of the client vocabulary

With 0.1 in place, decide each unknown command rather than replying
`GAME_UNKNOWNCLIENTCOMMAND`. Known client senders so far: `mr`, `n`, `cp`,
`s`, `userinfo`, `disconnect`, `matchdatadone`. C1's own registration table at
`0xcd149c` holds only four entries (`userinfo`, `disconnect`,
`disconnectforoutro`, `matchdatadone`), so the rest are emitted directly by
game code, which is why enumerating them needs the trace rather than a table
walk.

### 1.8 Map restart must stop leaking the map

**Wrong.** A non-fast restart runs `SV_LoadLevel` → `SV_SpawnServer` →
`CODOL_LoadMapArchives`, which re-opens, decrypts and replays every zone.
`mount_archives` moves the previous group onto `retired_archives`
(`codol_asset_registry.c:295-303`) and nothing frees that list except a full
teardown at `:1997`. Every restart therefore holds a second complete copy of
the map. This is the most likely cause of both the remount failure and the
memory growth seen during long play.

**Fix.** Two parts.
- Free a retired archive once nothing references it, or reference-count the
  composed-weapon cores that `CODOL_RetireComposedWeapons` protects.
- Skip the remount when the map and zone type are unchanged. A restart of the
  same map cannot need different zone content, and this also removes the
  30 second first-frame precache from every restart.

**Done when.** Ten consecutive `map_restart` cycles leave resident memory flat
and no `CoDOL map mount failed` line appears.

### 1.9 Publish the frozen player-state bit

Promoted out of phase 2 because items 1.5 and the warmup both depend on it.
The retained engine sets `pm_flags` from the freeze-controls client field in
`ClientEndFrame`. Direct C1 `PmoveSingle` at `0x41602c` proves frozen is
`0x800`: movement and velocity stop while view angles remain available. C1
`0x80000` is remote controlling; outer `Pmove` and `PM_UpdateViewAngles` use it
to suppress movement and view updates. sh1x stores both C1 flags directly and
the snapshot writer forwards them unchanged.

**Done when.** `freezeControlsWrapper(true)` actually stops the client moving,
instead of only stopping the server simulating it.

## 4. Phase 2 — P1: the feedback the client draws but never receives

### 2.1 Publish the shellshock `pm_flags` bit

The frozen bit is item 1.9, promoted into phase 1. The other missing bit in the
same mask (`codol/snapshot/codol_engine_state.c:248-251`) is shellshock: native
`0x10000` → C1 `0x8000`, already documented at
`codol/script/codol_script_shellshock.c:30`.

Corroborated in the client: every site testing `pm_flags & 0x8000`
(`0x523890`, `0x538b1b`, `0x561c09`) immediately reads `ps+0x598`, the
shellshock block, and `ps+0x598` is already a field this server writes. Without
the bit, flashbangs and grenade concussion never render on the client even
though the server simulates them.

### 2.2 Rank and XP

`J` (update, no commit) and `K` (update, commit) are never sent, and the
per-client rank, prestige and head-icon fields of the client state are never
published (`codol_engine_state.c:851-866` says so in its own comment). The
progression the player earns is invisible. Pair this with item 5.1, since
sending an update for a value that is not persisted is worth little.

### 2.3 Damage indicators and flinch — now measured, no live run needed

The comment at `codol_engine_state.c:261-263` says these offsets are not in
alpha0022's `ps_offset_audit.md`, and that was the reason they were left
unpublished after the 2026-09-09 revert. They **are** in alpha0022's
`playerstate_fields.py`, which is the better source: it carries the C1 netfield
table verbatim from `.rdata:0x00C38CA8` with an IW4 name mapping checked four
independent ways.

Two independent derivations agree on the identification:

1. `playerstate_fields.py` names `0x017c damageEvent`, `0x0180 damageYaw`,
   `0x0184 damagePitch`, `0x0188 damageCount`, `0x018c damageFlags`.
2. The wire widths at `0x17c`–`0x188` are **8, 8, 8, 7**, and that run is
   **unique across all 244 fields**. The retained engine's own netfield table
   gives `damageEvent` 8, `damageYaw` 8, `damagePitch` 8, `damageCount` 7
   (`msg.c:2437-2462`), and `damageCount` is one of only three 7-bit fields in
   the whole IW3 table.

The retained playerState already holds every member: `damageEvent` at 312,
`damageYaw` 316, `damagePitch` 320, `damageCount` 324 (`player.h:162-165`), and
`damageTimer` 160, `damageDuration` 164 (`:125-126`).

Also unpublished and part of the same feature: `0x00d8 damageTimer` (10 bits),
`0x00dc damageDuration` (16 bits), `0x00e0 flinchYawAnim` (2 bits) — the flinch
and the screen overlay, as distinct from the directional arrow.

**Fix.** Publish all eight, with the range validation the surrounding code
already uses for every other field. The widths are hard limits: the codec
fails, and the whole frame is dropped, if a value exceeds its field
(`codol_delta.c:41-43`). `damageEvent` is an incrementing counter and must be
sent modulo 256; `damageCount` must be masked to 7 bits; `damageTimer` to 10
and `damageDuration` to 16.

**On the earlier revert.** These were reverted on 2026-09-09 as a suspected
cause of the spawn and camera regression. That regression has since been traced
to a different cause — baseline snapshots carrying no origin — and fixed. The
damage publication is not implicated and can be restored.

### 2.4 HUD element refresh, playercards, and the rest of the unproduced letters

- `F <elem 0..7>` refreshes one HUD element (0 health, 1 compass, 2 stance,
  3 sprint meter, 4 weapon info, 5 offhand info, 6 objective info, 7 RC bomb
  hints). Never sent. The retail server sends it after a weapon change; this is
  a candidate cause of the composed-weapon ammo reading `0|0`.
- `L <clientNum> <slot>` caches a player-card row. Never sent, so the card
  work already done never reaches the card UI.
- `S <weapon>` registers a killcam FX weapon. Needed by phase 4.
- `]` timed subtitle, `5`/`6`/`7` transported/burn/electrified, `9` in-game
  store, `[` anti-addiction notice, `|` force-load-on-demand: never sent.
  Individually small; list them so the choice to skip one is deliberate.

### 2.5 The rest of the named, unpublished player fields

Appendix C lists every C1 player field that has a measured name, can carry a
value, and has no writer anywhere in `src/codol`. There are 23. They cluster
into five features, and three of those features are blocked on nothing but the
publication itself.

### 2.6 Objective and waypoint arrays — implemented

The identification pass is done and the section is written.

The array is player-state section 5 at `ps+0x5D0`, and the wire is measured.
`MSG_ReadDeltaPlayerstate` gates it with one bit at `0x5a1f79`, then loops a
hard-coded 32 slots (`0x5a1f9c`) of stride `0x24` (`0x5a1fd6`). Each slot reads
a raw 3-bit `state` (`0x5a1fa6`) that sits outside the field table, then a
six-field delta struct through the generic reader `0x5a0a40` against the table
at `.rdata:0xc39818`. Its consumers are the compass drawer `0x4321b0` and the
on-screen drawer `0x432790`.

The field table is not sorted by offset, and its order is what the gap coder
counts in: origin x, y, z (floats), icon (12 bits at `0x20`), entNum (11 bits
at `0x10`), and a 4-bit field at `0x14` that neither drawer reads. `state` 0 is
the free slot and is how a deletion is expressed; only 1 and 4 draw. `entNum`
`0x7ff` means use the world origin, and any other value is read as a client
number rather than a general entity number. `icon` indexes `CS[4275 + icon]`,
the same material block hudelems use, and icon 0 falls back to the client's own
built-in material, so a smoke test needs no configstring at all.

The gap coder is a third one: plain unary, `delta-1` zero bits then a 1
(`0x5a09e2`). It is neither the player-field coder (4-bit, escape 15) nor the
HUD coder (3-bit, escape 7). Getting it wrong desynchronises everything after
section 5, which is the whole HUD.

Source: alpha0022 `objective_codec.py`, which carries the transcription, an
encoder and an independently written reader. The address the inventory pointed
at is the same table; what was wrong was its name, not its contents.

Seeding needed almost nothing. `G_RunFrame` already copies `level.objectives`
into `ps->objective` every frame, filtered by the client's team, zeroing the
state of anything that client must not see (`_g_main_mp.asm:1020-1060`, stride
`0x1c` on both sides). The two state enumerations agree exactly, `OBJST_EMPTY`
0, `OBJST_ACTIVE` 1, `OBJST_CURRENT` 4, so the translation is mechanical. The
retained array holds sixteen entries and C1 reads thirty-two; the tail stays
free.

The gate stays off while nothing is live, so the emitted bits are byte for byte
what they were before the section existed. That is deliberate: the reader costs
a flat 32 by 4 bits the moment the gate is on, because `state` is read for
every slot whether or not anything is in it.

Still unproven: whether the loaded HUD `.menu` declares the ownerDraw items
that instantiate the two drawers (145, 146, 152, 180). If it does not, the data
arrives correctly and nothing draws. That needs a client.

### 2.7 Admin chat letter

`h "<text>"` → `V "<text>"` (all chat) at the four sites in §1. `V` is
suppressed by `cg_teamChatsOnly`; `e` is the alternative if an unsuppressible
channel is wanted.

## 5. Phase 3 — modes and maps

### Map loading: done

Every installed multiplayer zone loads. Surveyed on 2026-09-10 by starting the
server once per map and waiting for either a fault or a settled level; each was
given up to six minutes, since the first-frame precache runs from twenty-six
seconds on killhouse to several minutes on the larger maps.

| map | zones mounted | collision leaves | result |
|---|---|---|---|
| `mp_killhouse_sh` | 6 | 4689 | loads |
| `mp_bog_sh` | 5 | 658 | loads |
| `mp_afghan` | 5 | 1651 | loads |
| `mp_rust` | 5 | 758 | loads |
| `mp_overgrown` | 5 | 10785 | loads |
| `mp_cross_fire` | 5 | 5095 | loads |
| `mp_bloc_sh` | 5 | 6188 | loads |
| `mp_estate_tropical` | 5 | 8846 | loads |
| `mp_storm_spring` | 5 | 3906 | loads |
| `mp_fav_tropical` | 5 | 3872 | loads |
| `mp_cargoship_sh` | 5 | 3278 | loads |
| `mp_crash_tropical` | 5 | 2943 | loads |
| `mp_crash_intro` | 5 | 2824 | loads |
| `mp_underpass` | 5 | not printed | loads |
| `mp_nuked` | 5 | not printed | loads |

One fix was needed, and only one. `mp_bog_sh` died in
`maps/mp/_animatedmodels.gsc`: an entity tagged `animated_model` picks its
animation from `level.anim_prop_models[self.model]`, a table the level designer
populates from the map's own registration scripts, which ship inside the map's
zone rather than with the gametype library. IW4's code does not guard the
lookup, so a model we have no registration for raised a fatal error before the
match started. `scripts/codol/maps/mp/_animatedmodels.gsc` now leaves such a
prop static and names the model once in developer mode. A server cannot invent
an animation for data it does not have; the alternative is refusing the map.

**This also settles item 3.3.** No zone hit the unhandled asset types, so
types 17, 23, 32, 33, 34 and 35 do not appear in multiplayer zones, which is
what the IW4 enum alignment predicted (`gameworld_sp`, `ui_map`, `aitype`,
`mptype`, `character`, `xmodelalias`). They need a documented skip rather than
a reader, and only if a coop or zombie zone is ever attempted.

`mp_underpass` and `mp_nuked` settle without printing a collision line. They
stay up, so it is a reporting gap rather than a load failure, but it is worth
a look before either is played.

### Gametypes: every one loads, and two were written

Surveyed the same way, on `mp_killhouse_sh`.

| gametype | result |
|---|---|
| `war` `dm` `sd` `dom` `ctf` `dd` | loads |
| `sab` `koth` `arena` `oneflag` `vip` `gtnw` | loads |
| `conf` | loads, newly written |
| `infect` | loads, newly written |
| `combat` | falls back to `dm` |

`conf` (Kill Confirmed) and `infect` (Infected) had no script anywhere in the
library, so the loader fell back to `dm`. Both are now written as native
adaptations in `scripts/codol/maps/mp/gametypes/`, built on the same helpers
`war.gsc` uses so they inherit the team spawn logic, the score and round dvars
and the callback wiring rather than reimplementing them. Both compile and reach
a settled level with no script errors and no fallback.

Two notes on those two. Kill Confirmed polls proximity for tag pickup rather
than creating a trigger, because nothing in this corpus creates a trigger from
script and a tag is short lived and few in number. Its tag model is a
placeholder: CoDOL ships its own dog tag asset and its name is not measured
yet, so a model the gametype library already precaches is used, which cannot
warn or fault. Infected converts players through `_menus::addToTeam`, the one
place that keeps `team`, `pers["team"]` and `sessionteam` in step.

`combat` is deliberately not written. It is the bot and novice training mode
from playlists 1 and 3, and without bots any script here would be team
deathmatch wearing its name. The existing fallback is more honest: it logs the
substitution and switches `g_gametype` to `dm`, so the server info reports what
it is actually running.

### What is left in this phase

1. **Prove a match, not just a load.** Every result above is the server
   reaching a settled level. None has had a client connect. `war` in
   particular needs the phase 1 team-score and scoreboard work exercised
   against a real client.
2. **Bots, then `combat`.** The mode is blocked on the bot work, not on script
   authoring.
3. **The 2048-entity truncation.** Four call sites pass a 1024-entry stack
   buffer and a matching capacity to `CM_AreaEntities`
   (`_g_active_mp.asm:1231`, `_g_combat_mp.asm:635` and `:847`,
   `_g_mover.asm:422`), so an area query that finds more than 1024 entities
   is truncated. It is a truncation and not an overflow, the capacity is
   passed correctly, and `CM_AreaEntities_r` already reports it in developer
   builds (`sv_world.cpp:94`). Enlarging the buffers means growing four
   assembly stack frames and reindexing every local in those functions, which
   is a poor trade against a warning that already fires; do it only if that
   warning is ever seen.

## 6. Phase 4 — killstreaks, vehicles, killcam

These are the largest remaining blocks and they share prerequisites, so they
come after phases 1 and 2.

- **Killcam.** The measured contract is: `pm_flags |= PMF_FROZEN` (item 2.1),
  `pm_type < 8`, `otherFlags` `POF_FOLLOW 0x800` and `POF_PLAYER 0x1000`,
  `clientNum` set to the killer, the `pm_flags` field forced on every frame
  with the read-origin bit set, and the replay ended when the victim's use
  button (`buttons & 0x8`) is pressed. `ps` `0xa50`–`0xa5c` (delta time, kill
  cam entity) are unpublished. Note alpha0022 could not settle whether a
  following client enters the locked-follow or free-look path, because that
  code is virtualised in C1; retail uses `PM_SPECTATOR` (5), which is the
  fallback if a first-person killcam leaks input.
- **Killstreaks.** Further along than this plan assumed. All thirteen scripts
  compile and initialise on every boot, `_codol.gsc` among them, and the level
  settles with no script error, so the system's `init()` runs. What has never
  happened is a player earning and using one, which needs a client in a match.
  The view-lock fields `0x1ac` and `0x1b0` are now published (item 2.5). The
  remote-camera fields `0x44`, `0x48` and `0x4c` are not: they have no retained
  counterpart, so they need new server state, and there is no producer to drive
  that state until a remote streak actually runs. Enable in dependency order
  when a client is available: UAV first, since the radar bits are already
  implemented, then airstrike, then the sentry, then the remote-controlled
  streaks.
- **Vehicles.** Conversion, pose, collision and precache are written; the
  factory dispatch and snapshot seeding are not, and the gameplay frame builder
  still rejects vehicle state outright (`CODOL_GAMEPLAY_FRAME.md:23`).
- **Missing script builtins: closed.** Every function called across the 246
  script files on the match load path was checked against the 837 registered
  builtins and against every script-defined function, and then against what a
  real boot actually compiles. Nothing is missing.

  The names that looked missing all live in files that never load:
  `_deathstreaks.gsc` (`magicgrenade`, `setclientsubtitle`, `nativesplash`,
  `givedeathstreakhealth`, `setcopycatloadout`) is an alpha0022 overlay written
  against their Python host and is referenced by nothing; `_sentry.gsc`
  (`setsuppressiontime`, `setaispread`), `_loot.gsc` and `mp_strike.gsc` do not
  compile either. Confirmed by counting each in the lowering trace of a full
  boot. `waittillmatch` and `using_animtree` are not builtins at all: the first
  is VM opcode 0x77 and a keyword in the lowering pass, the second a compiler
  directive.

  Deathstreaks in particular need no bridges here. The vendor `_damage.gsc`
  already implements all four from the perk alone: copycat at :234, :737 and
  :888, combat high at :1414, final stand at :1617 and :1640, with the health
  boost in `_perkfunctions.gsc:183-193`. alpha0022 rebuilt them as host calls
  because their server could not run those callbacks; this one can.

  `setclientsubtitle` was implemented anyway, since C1's `]` is measured and a
  timed subtitle is generally useful, but it unblocks nothing on its own.

## 7. Phase 5 — session, persistence, lobby

- **Profile persistence.** Twelve IW4-only playerdata roots (rank, experience,
  prestige, challenge progress) are answered from a per-client session store
  that is discarded on disconnect (`codol_script_profile_vm.c`). Nothing is
  persisted or uploaded, so no progression survives a match. This is the
  prerequisite for item 2.2.
- **Match data upload.** `sendmatchdata` is a draft; the queue, session and
  backend are incomplete.
- **The lobby.** C1 reaches the game server only through the Demonware lobby,
  which is still alpha0022's `dw-capture.py` on port 3074. Nothing under `src/`
  implements session create, find, join, party, ready, playlists, chat, store
  or the rank push. This is the single largest remaining piece of work and the
  only one that is P0 for a standalone server; it is P1 while the Python lobby
  is kept, and the user's standing instruction is to preserve that process.
- **Reconnect and association reuse.** Associations persist across restarts;
  alpha0022 found that restoring them on startup revives stale sessions. The
  native behaviour is unverified.

## 8. What is genuinely unknown, and the run that would settle it

| question | the run |
|---|---|
| Which player-state fields never carry a value | one match with 0.3 armed; diff the printed offsets against inventory §3 |
| Whether the retained mantle ever starts | one run at a real ledge with `mantle_debug` forced on, which developer builds already do |
| Whether a following killcam client leaks input | the A/B in phase 4; static analysis cannot answer it, the path is virtualised |
| What else the client sends | 0.1, then one full match including a death and a match end |
| Whether the composed-weapon ammo HUD needs `F` | send `F 4` after a weapon change and watch the counter |
| Whether the unnamed CoDOL-only fields in appendix C matter | trace a C1 reader for each offset, or leave them zero |

## 9. Recommended order

Dependencies first, then value per unit of risk. Each row is one reviewable
change; the assembly edits are single-byte constants inside `%ifdef` guards and
carry almost no risk of collateral damage.

| order | items | why here | risk |
|---|---|---|---|
| 1 | 0.1, 0.2 | the two traces cost nothing and make every later step verifiable | none |
| 2 | 1.3, 1.4, 1.6, 2.7 | pure letter corrections; they stop the server actively corrupting client state, and 1.3 unblocks a large amount of existing script | very low |
| 3 | 1.1, 1.2 | the scoreboard and the scores; both are wiring, not new logic | low |
| 4 | 1.9 | one mask change; needed before the match end can hold a player still | low |
| 5 | 1.5 | after 1.1, 1.3 and 1.9 most of it already works; only the exit is new | medium, it is the first behaviour the server drives on its own |
| 6 | 1.8 | the restart leak; do it before long test sessions, not after | medium |
| 7 | 2.3, 2.1 | damage indicators and shellshock; both now fully measured | low |
| 8 | 3.1, 3.2 | second map and `war`; the first real breadth test | medium |
| 9 | 2.2, 2.4, 2.5, 2.6 | progression, HUD refresh, playercards, objectives | medium |
| 10 | phase 3 remainder | zone dispatch, missing gametypes, entity limit | medium |
| 11 | phase 4 | killcam, killstreaks, vehicles | high, and it is the bulk of the remaining work |
| 12 | phase 5 | persistence, then the lobby | high; the lobby is the largest single piece in the project |

Two sequencing warnings.

- **Do not start phase 4 before phase 2.** Killstreaks, killcam and turrets all
  depend on player-state fields that phase 2 publishes. Building them first
  means debugging two layers at once.
- **Do not restore the damage fields and change the `pm_flags` mask in the same
  change.** Both touch the same overlay, and the last regression in that file
  cost a full debugging session to attribute.

## Appendix A — C1 server-to-client commands, and whether the server produces them

C1 implements 60 letters. `G I X Y Z 0` and the punctuation outside this set
fall through to "Unknown client game command"; `d`, `k`, `x` and `t` are
handled at the client layer before cgame ever sees them.

| C1 | meaning | server |
|---|---|---|
| `a` | select weapon | yes |
| `b` | scoreboard, 10 ints per row | wrong sender wired — item 1.1 |
| `c` | announcement | yes |
| `d` | configstring | yes, CoDOL-native publisher |
| `e` `f` | game message | yes |
| `g` | bold game message | yes |
| `h` | stop local sound | yes |
| `i` `j` | screen blur start and reset | never sent; shellshock travels in the player state instead — item 2.1 |
| `k` `x` | map restart, preserve 1 or 0 | map change yes; fast restart wrong — item 1.6 |
| `l` `m` `n` `o` `p` | music play, music stop, sound fade, reverb, local sound | yes |
| `q` `r` `u` `v` | open menu, close menu, popup variants | yes, CoDOL-native |
| `s` | set client dvar | wrong letter — item 1.3 |
| `w` | HUD splash | yes |
| `y` | set equipped offhand | wrong letter — item 1.4 |
| `z` `A` `B` | deactivate reverb, channel volumes, deactivate | yes |
| `C` `D` | team score 1 and 2 | `updatescores` yes; `setteamscore` wrong — item 1.2 |
| `E` | single client score | yes |
| `F` | refresh one HUD element | never sent — item 2.4 |
| `H` | hide scoreboard, close pause menu | yes |
| `J` `K` | rank and XP update | never sent — item 2.2 |
| `L` | cache a playercard row | never sent — item 2.4 |
| `M` | client-side upload error print | not applicable |
| `N` `O` `P` `Q` `R` `3` | vision sets 0 to 5 | yes, five of six |
| `S` | register a killcam FX weapon | never sent — phase 4 |
| `T` | water sheeting | never sent |
| `U` | no-op in the client | not applicable |
| `V` `W` | all chat, team chat | yes for game chat; admin broadcast wrong — item 2.6 |
| `1` `2` `8` `}` | client flag writes, semantics unknown | never sent |
| `4` | zm scoreboard, 7 ints per row | formatter yes, zm not loadable |
| `5` `6` `7` | transported, burn, electrified | never sent |
| `9` | in-game store | never sent |
| `[` | anti-addiction notice | never sent |
| `]` | timed subtitle | never sent |
| `{` | ambient play | configstring route used instead |
| `\|` | force load on demand | never sent |
| `t` | client-layer drop with reason | never sent — item 1.5 |

## Appendix B — the exact edit sites

| item | file | line | change |
|---|---|---|---|
| 1.1 | `src/g_cmds.c` | 962 | accept `s` alongside `score` |
| 1.1 | `src/g_cmds.c` | 743 | call `CODOL_SendScoreboard` under `CODOL_SERVER` |
| 1.1 | `src/codol/stats/codol_scoreboard_sender.c` | 46-50 | warn once instead of aborting the send |
| 1.1 | `src/codol/stats/codol_scoreboard_wire.c` | 17 | clamp rows to 19 |
| 1.2 | `src/asmsource/_g_scr_main_mp.asm` | 6524 | `0x47` → `0x43` |
| 1.2 | `src/asmsource/_g_scr_main_mp.asm` | 6542 | `0x48` → `0x44` |
| 1.2 | `src/codol/assets/codol_sv_assets.c` | mapping table in `CODOL_RefreshServerMapConfigstrings` | add 6 → 5 and 7 → 6 |
| 1.3 | `src/asmsource/_g_client_script_cmd_mp.asm` | 3484 | `0x76` → `0x73` |
| 1.3 | `src/asmsource/_g_client_script_cmd_mp.asm` | 3558 | `0x76` → `0x73` |
| 1.4 | `src/asmsource/_g_weapon.asm` | 1017, 1137 | `0x43` → `0x79` |
| 1.5 | `src/codol/script/codol_script_exitlevel_trace.c` | `CODOL_Scr_ExitLevel` | send `t "EXE_MATCHENDED"`, behind a cvar |
| 1.6 | `src/sv_main.c` | 3910 | `'m'` → `'k'` |
| 1.7 | `src/g_cmds.c` | 1007 | log the unhandled command text |
| 1.8 | `src/codol/assets/codol_asset_registry.c` | 295-303 | free retired archives; skip an unchanged remount |
| 1.9 | `src/asmsource/_g_active_mp.asm` | `ClientEndFrame` | set C1 `0x800` directly for frozen controls |
| 2.1 | `src/codol/snapshot/codol_engine_state.c` | 248-251 | add native `0x10000` → C1 `0x8000` (shellshock) |
| 2.3 | `src/codol/snapshot/codol_engine_state.c` | 261-263 | publish `0x0d8`, `0x0dc`, `0x0e0`, `0x17c`, `0x180`, `0x184`, `0x188`, `0x18c` with range validation |
| 2.7 | `src/sv_cmds.c`, `src/plugin_exports.c`, `src/plugin_internal.c`, `src/sv_main.c` | 107, 463, 148, 2226 | `h` → `V` |

Every assembly edit belongs inside `%ifdef CODOL_SERVER` with the `%else`
branch keeping the IW3 value, matching the convention already used at
`_g_client_script_cmd_mp.asm:4406-4412`.

## Appendix C — named player fields the server never publishes

Derived by intersecting the measured C1 netfield table (244 entries,
`.rdata:0x00C38CA8`, carried verbatim in
`src/codol/snapshot/codol_player_fields.inc` and named in alpha0022's
`playerstate_fields.py`) with every offset written anywhere under `src/codol`.
Fields written through array or overlay loops (events, event parameters,
perks, links, radar, sprint, use hint, loop sound, recoil) were excluded by
hand, as were the two the code deliberately withholds (`0x114`
`oldEventSequence`, per `codol_engine_state.c:1040`).

A width of 0 is **not** "cannot be sent": `codol_delta.c` `case 0` is a float
encoding (zero flag plus sign, else a 13-bit trimmed mantissa at scale 4096),
the same one that already carries `leanf`, `vLadderVec`, `jumpOriginZ` and the
mantle yaw. Positive widths are hard limits — exceeding one fails the write and
drops the entire frame (`codol_delta.c:41-43`), so every publication needs the
range validation the surrounding code already uses.

| offset | width | name | feature | plan item |
|---|---|---|---|---|
| `0x0040` | 10 | `throwbackWeaponIndex` | grenade throwback prompt | 2.5 |
| `0x0044` | 11 | `remoteEyesEnt` | remote killstreak camera | phase 4 |
| `0x0048` | 11 | `remoteEyesTagname` | remote killstreak camera | phase 4 |
| `0x004c` | 11 | `remoteControlEnt` | remote killstreak control | phase 4 |
| `0x0050` | 11 | `foliageSoundTime` | foliage movement sound | 2.5 |
| `0x00d8` | 10 | `damageTimer` | damage flinch and overlay | 2.3 |
| `0x00dc` | 16 | `damageDuration` | damage flinch and overlay | 2.3 |
| `0x00e0` | 2 | `flinchYawAnim` | damage flinch and overlay | 2.3 |
| `0x00e4` | 3 | `corpseIndex` | corpse hand-off on death | 2.5 |
| `0x0144` | 11 | `viewmodelIndex` | first-person hands model | 2.5 |
| `0x016c` | float | `viewAngleClampBase[0]` | turret and vehicle look limits | phase 4 |
| `0x0170` | float | `viewAngleClampBase[1]` | turret and vehicle look limits | phase 4 |
| `0x0174` | float | `viewAngleClampRange[0]` | turret and vehicle look limits | phase 4 |
| `0x0178` | float | `viewAngleClampRange[1]` | turret and vehicle look limits | phase 4 |
| `0x017c` | 8 | `damageEvent` | directional damage indicator | 2.3 |
| `0x0180` | 8 | `damageYaw` | directional damage indicator | 2.3 |
| `0x0184` | 8 | `damagePitch` | directional damage indicator | 2.3 |
| `0x0188` | 7 | `damageCount` | directional damage indicator | 2.3 |
| `0x018c` | 1 | `damageFlags` | directional damage indicator | 2.3 |
| `0x01a0` | float | `proneDirection` | prone body orientation | 2.5 |
| `0x01a4` | float | `proneDirectionPitch` | prone body orientation | 2.5 |
| `0x01a8` | float | `proneTorsoPitch` | prone body orientation | 2.5 |
| `0x01ac` | 2 | `viewlocked` | turret view lock | phase 4 |
| `0x01b0` | 16 | `viewlocked_entNum` | turret view lock | phase 4 |
| `0x01ec` | 11 | `linkWeaponEnt` | linked weapon entity | phase 4 |

The retained playerState already carries every one of these members, so each is
a bounded `put()` in `CODOL_OverlayEnginePlayerState`, not new state.

A further 148 of the 244 fields are CoDOL-only slots with no IW4 counterpart
and no name. They are not listed as gaps: without a traced consumer in C1 there
is nothing to publish into them, and leaving them zero is correct.
