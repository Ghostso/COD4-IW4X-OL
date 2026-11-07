# The bottom-right score only updates while TAB is held -- 2026-09-21

Reported: "the player's score shown in the bottom right of the HUD does not
update as the player earns points. It only refreshes when the player opens the
scoreboard by holding TAB. After closing the scoreboard the displayed value is
correct, then goes stale again." Hit in zombies (`zm_prototype_sh`, the live
match in `bin/home/main/qconsole.log:190-192`).

Everything below labelled MEASURED comes from reading C1.exe
(`tools/codol_c1_disasm.py`) or this tree; nothing is inferred from IW4/T5.

## 1. The two transports

### The scoreboard path (TAB) -- works

* The client sends the one-letter command `s` when the scores key goes down
  (`0x436f4a`).
* `SV_ClientCommand` -> `ClientCommand` (`src/g_cmds.c:989`) -> `Cmd_Score_f`
  (`src/g_cmds.c:745`) -> `CODOL_SendScoreboard`
  (`src/codol/stats/codol_scoreboard_sender.c:18`).
* That emits C1's whole board: `b <count> <team1> <team2> <limit>` + ten ints
  per row in multiplayer, or `4 <count>` + seven ints per row in `zm`.
* C1 parses it at `0x465130` (normal) / `0x4655e0` (zm) into **the cached row
  table at `cg+0xBEB70`, stride `0x40`, 19 rows max** (the memset of `0x4C0`
  bytes at `0x465254` is 19 x 64). MEASURED field layout, both parsers:
  `row+0x00` client number, `row+0x04` **score**, `row+0x08` ping,
  `row+0x0c` deaths, `row+0x14` kills. The zm parser writes the same
  `row+0x00` / `row+0x04` pair (`0x4656fc` loads `ebx = cg+0xBEB74`, then
  `[ebx-4] = client`, `[ebx] = score`).

### The continuous HUD path (bottom-right readout) -- was dead

The HUD readout is **not** a playerstate field, **not** a configstring and
**not** a HUD element. MEASURED: C1's named HUD/menu value `score`
(string `0xc44478`) is resolved at `0x5dec2d` by taking the LOCAL client number
from `cg+0x35c0`, looking it up in that same cached row table with the helper
at `0x45fe50`, and returning **`row+0x04`**. The neighbouring names in the same
resolver come from the same row: `ping` (`0xc49678`) -> `row+0x08`, `deaths`
(`0xc44470`) -> `row+0x0c`, `kills` (`0xc44468`) -> `row+0x14`.

So the bottom-right number is the client's cached scoreboard row, and the only
two writers of that row are:

1. the whole-board replies `b` / `4` above, and
2. **the incremental reliable command `E <clientNum> <score>`**: dispatcher
   `0x469320`, byte map `0x46a118['E'] = 14`, jump table `0x46a024[14] =
   0x469a4f`. The handler reads argv[1] as the client number and argv[2] as the
   score and calls `0x465990`, which finds that client's row and writes
   `row+0x04`. If the client is not in the table it instead re-requests the
   whole board with `s`, rate-limited to one request per 2000 ms
   (`0x4659fa`, string `0xc41e50` = `"s"`).

The retained producer of `E` is `PlayerCmd_UpdateDMScores`
(`src/asmsource/_g_client_script_cmd_mp.asm:4464`), the GSC player method
`updateDMScores`. MEASURED shape: it sends the viewer **its own** row and then
**the leader's** row (`level.sortedClients[0]`, or the next sorted client when
the viewer is the leader), both `SV_GameSendServerCommand(self, 0, "E %i %i")`
-- svscmd_type 0, "can ignore", exactly what a retail server uses.

## 2. Root cause

**Nothing ever sends `E`.** `sess.score` is the authoritative value, the
scoreboard reply reads it (`codol_scoreboard_sender.c:42`) and gets it right,
but the carrier that keeps the client's cached row in step with it is never
emitted, so the cached row -- and therefore the HUD readout -- is frozen at
whatever the last whole board said. Pressing TAB sends `s`, the whole board
arrives, the row is rewritten and the readout is briefly correct again. That is
the reported symptom exactly.

Why it is never sent:

* `updateDMScores` is called from exactly one place in the whole script tree:
  `maps/mp/gametypes/_gamescore.gsc:209` and `:352`, i.e. `sendUpdatedDMScores()`
  and `initialDMScoreUpdate()`. `givePlayerScore` only threads
  `sendUpdatedDMScores()` **when `!level.teamBased`** (`_gamescore.gsc:56-57`),
  which is IW4's own rule.
* The zm purse never goes near it. `zm/maps/mp/gametypes/_zombiemode_score.gsc`
  writes `self.score` in `add_to_player_score` / `minus_to_player_score` /
  `player_reduce_points` and then only calls `set_player_score_hud()`, which
  updates its own GSC hudelem. `self.score` does reach `sess.score`
  (`src/g_client_fields.cpp:511` -> `ClientScr_SetScore`, `:193-205`), so the
  scoreboard is right and only the HUD carrier is missing.
* `_setPlayerScore()` (the suicide path) sends nothing either.

This is precisely the "we update the authoritative value but never mark the
HUD-side carrier dirty" shape, with the carrier being a reliable command rather
than a snapshot field.

## 3. What the theory-under-test turned out to be -- HUD elements are innocent

The briefed hypothesis was a rejected HUD element (a `hud_bits` codec range
violation in `CODOL_WritePlayerArrays`). Checked and cleared:

* The zm purse hudelem's value goes into wire field offset `0x80`
  (`CODOL_OverlayEngineHudPresentation`, `codol_engine_state.c:50`,
  `HUD_FIELD(0x80,value,1)`), which is `hud_bits` index 9, **codec 0**.
* Codec 0 (`codol_delta.c:215`) writes a zero test bit and otherwise
  `trimmed(from,to,13,4096)`, and `trimmed` (`:51-61`) falls back to a full
  32-bit XOR whenever the value is outside +/-4096 or not integral. So a purse
  of any size is representable; there is no range failure and no
  `CODOL_ReachHudFailure()` for it. (The fontScale codec `-86` that bit this
  file before is a different field, index 16, and the zm tree is already
  inside its 0.0..6.3 range.)
* No `HUD not reachable` line appears in any captured log.

The GSC hudelem `self.score_hud` (`_zombiemode_score.gsc`, `score_hud_init`,
also bottom-right at x=-103 y=-71) therefore *should* be live. It cannot be
the element the user is watching, because a hudelem value has no relationship
to the scoreboard command and could not possibly refresh when TAB is pressed.
See "Open" below.

## 4. Is it score-specific, and is mp affected?

**It is the transport, not the value.** Everything the HUD reads out of that
cached row -- score, ping, kills, deaths, and the placement computed at
`0x460060` -- is stale between whole boards. Score is simply the only one C1
gives an incremental command for; `E` carries nothing else. So restoring `E`
restores exactly what retail restores, and kills/deaths on the HUD remain
whole-board-only in C1 by design.

Per category, before this change:

| category | personal score carrier | state |
|---|---|---|
| zm | none | **stale until TAB** (reported) |
| mp, team based (tdm/dom/sd/...) | none -- `givePlayerScore` skips `sendUpdatedDMScores` when `level.teamBased` | **stale until TAB** |
| mp, free-for-all | `sendUpdatedDMScores()` -> `updateDMScores` | worked |
| coop | none | stale until TAB |

So **multiplayer has the same bug in every team-based gametype**; only FFA was
ever correct.

Team scores are a separate pair (`cg+0xBEB20` / `cg+0xBEB24`, commands `C` and
`D`, and the same two fields are rewritten from the `b` header) and are already
published every frame by `CODOL_PublishTeamScores` (`codol_sv_assets.c:579`)
as configstrings 5/6. Not affected.

## 5. The change

`src/codol/stats/codol_scoreboard_sender.c`

* new `CODOL_ScoreLeaderFor(self)` -- C1's leader selection from
  `PlayerCmd_UpdateDMScores` (first `level.sortedClients[]` entry that is not
  the viewer, -1 when there is none).
* new `CODOL_PublishPlayerScores(void)` -- once per server frame, for every
  `CS_ACTIVE` non-bot client with `gamestateSent`, sends C1's
  `E <client> <score>` for the viewer's own row and then for the leader's row,
  with `svscmd_type 0`, but only when that viewer's own score, leader identity
  or leader score actually changed since the last send, and at most once per
  50 ms per client (IW4's `sendUpdatedDMScores` debounces with `wait .05` for
  the same reason: a zm purse moves on every bullet). Idle matches send
  nothing.

`src/codol/stats/codol_scoreboard_sender.h` -- declaration.

`src/sv_main.c` -- `#include "codol_scoreboard_sender.h"` and the call next to
`CODOL_PublishTeamScores()` / `CODOL_RefreshWeaponHud()` in the
`sv.state == SS_GAME` block that runs after `G_RunFrame` and before
`SV_SendClientMessages()`. This is the same hook and the same "C1 expects this
refresh command and the retained server never sent it" pattern as
`CODOL_RefreshWeaponHud`.

Driving it from the server frame off `sess.score` rather than from script means
it covers zm, coop and team-based multiplayer, and every writer of the score,
script or native, with no per-gametype script edits. Where the mp FFA script
still calls `updateDMScores`, the two agree: the publisher's "did it change"
guard means the duplicate is a no-op on the next frame, and a duplicate `E`
with the same numbers is idempotent on the client.

Build: `make objects` for the touched objects is clean (only the pre-existing
`-Waddress` warning already present in `CODOL_SendScoreboard`). Not linked, not
promoted, not committed, server untouched.

## 6. Open / handoffs

* **The `sv_main.c` half is already committed and the definition is not.**
  Commit `7d455f90` (another worker's zombies-waypoint commit, 00:17) swept the
  working-tree `sv_main.c` -- including this hook -- into HEAD. HEAD therefore
  calls `CODOL_PublishPlayerScores` while its definition is still an
  uncommitted change in `src/codol/stats/codol_scoreboard_sender.{c,h}`.
  **A link from HEAD alone fails with an undefined reference**; the two files
  must be committed before the next link. (While writing this,
  `src/codol/stats/codol_match_report.c` was also mid-edit by another worker
  and did not compile -- unrelated, and not touched here.)
* **Duplicate zm readout.** With `E` live, C1's own bottom-right readout and
  the GSC `self.score_hud` hudelem (same corner) both show the purse. Worth one
  live look at the next zm test: if two numbers overlap, the GSC element is the
  one to drop, because the C1 readout is the vanilla one and now tracks
  `sess.score` directly.
* **Intermission scoreboards are still the wrong format.** `G_RunFrame` calls
  the retained IW3 `SendScoreboard` for every intermission client
  (`src/asmsource/_g_main_mp.asm:1313`, gated on `level+0x210`, the flag
  `CalculateRanks` sets at `:1404`). That producer emits seven integers per row
  and C1's `b` parser reads ten (`docs/CODOL_SCOREBOARD_CONTRACT.md`). The fix
  is the same one-line swap already done in `Cmd_Score_f`: call
  `CODOL_SendScoreboard` there under `%ifdef CODOL_SERVER`. Not done here --
  `_g_main_mp.asm` is currently carrying 2015 CRs in the working tree against 0
  at HEAD (someone flipped its line endings), and an asm edit on top of that
  would be unreadable in the diff.
* **Line endings, unrelated to this work but worth someone's attention:**
  `src/server.h` (894 CR vs 0 at HEAD), `src/asmsource/_g_main_mp.asm` (2015 vs
  0) and `bin/home/codol_rawfiles/maps/mp/gametypes/_hud_message.gsc` have been
  wholesale-flipped in the working tree by earlier edits. Every file this doc
  touched is LF and stayed LF.
