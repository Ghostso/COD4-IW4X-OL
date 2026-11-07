# C1 natural match-end lobby boundary, September 29

The isolated C1 executable was SHA-256
`086B2BCF109C8340A898606E5CAA2678242449452BCF62B2DDA22A6E37DDA91F`.
The same native server process stayed on UDP/17733 during these trials. The
patched lobby's earlier matchmaking 21/3 retirement change was active.

## Observed paths

1. Manual in-match menu exit sent matchmaking 21/3 and room 11/2. C1 returned
   to the multiplayer menu. It then started matchmaking, created a fresh room,
   pressed Ready, loaded Killhouse, selected a class and spawned. A 60-second
   passive reliable-command probe on this second join peaked at three pending
   commands and did not reproduce the old overflow.
2. Natural timed end sent `t "EXE_MATCHENDED"` and displayed the result board
   without the false partner-left notice. The lobby saw Tencent 71/7
   `ClientDisconnect` telemetry but **no** matchmaking 21/3 or room 11/2. C1
   returned to a room page with an empty DEV PANEL, wrong room card and a Ready
   button. Clicking Ready sent no room 11/4 message. The UI Leave control
   returned C1 to its normal home page, after which normal matchmaking worked.
3. A lobby experiment sent the exact C1 room type-4 `Clear Readys` bit record
   (`04 00 00 00 08 00 00 00`) after the disconnect telemetry. It was tested
   once with envelope sender 69421 and again with 69420, the sender used by the
   working StartGame push. Both pushes were queued and logged on the encrypted
   lobby connection; both returned to the same broken room, and Ready still
   sent no room task. This does not prove whether C1 handled the record, but
   it proves that this push alone does not restore the page. The experimental
   code was removed from the canonical and live lobby.
4. With `codol_exitToLobby 0`, a timed end rotated into another playable
   Killhouse round on the same server process. It avoided the broken page by
   staying in the match. The default was restored to `1` because natural
   return to a usable lobby remains the required behavior.
5. A separate score-limit round settled on the same native server, which sent
   `t "EXE_MATCHENDED"`. C1 returned without the false partner-left notice,
   but showed the same broken room. The observing client was a spectator at
   settlement and earned zero XP; this test does not validate profile refresh.
   Manual Leave again restored the normal multiplayer home page.

## Exact C1 lead

`dwRoom::OnChatChannelMessage` starts at `0x00711BF0`; its type-4 arm begins
at `0x00712105` and calls `0x0070D0D0` (`Clear Readys`). That routine clears
member readiness fields but is not a room create/join or page rebuild. The
natural end gap occurs before the next room task: C1 does not send a new
11/4 when Ready is clicked. Type 8 starts at `0x0071280F` but drops the
message if the room singleton has a record at `+0x10` or C1 is host
(`room+0x44F8`); both apply to this host-created room, so it cannot invoke
`LeaveRoom` here. Type 9 at `0x0070F640` serializes a targeted 64-bit member
ID; its receiver at `0x0071286F` only leaves if that ID matches the local
member, using reason 8 and an event callback that clears the roster and
schedules `cpp_refreshTask`. This is a targeted member-removal path; its
user-visible effect is unverified and it is not a safe normal-end signal.
Manual Leave reaches
`dwRoom::LeaveRoom` at `0x0070E1F0` and its channel-unsubscribe path,
consistent with the observed room 11/2. Its preceding matchmaking 21/3
caller still needs mapping.

## Frontend Leave versus natural end, exact C1 code

The Scaleform binding named `LeaveRoom` (`0x00C761E4`) is registered by
`0x006A7BD0` at `0x006A7C48`. Its native callback at `0x006AF140` handles the
separate party-room singleton when present, then **always** calls `0x0071C780`
at `0x006AF1EB`. That routine calls the game-room singleton's vtable `+0x10`
(`0x0070DEF0`, pending-task cleanup) and `+0x24` (`0x0070E4A0`) and destroys
the matchmaking-manager object at `0x06C44F0C` when present. The `+0x24`
method calls `dwRoom::LeaveRoom` (`0x0070E1F0`) only while a room record or
pending join exists and teardown is not already active. `LeaveRoom` takes the
channel-unsubscribe path through `0x006FDB20` and may queue
`disconnect leaving_party_or_room` while still in game. Its completion at
`0x00711570` clears the room record at `+0x10` and notifies listeners. After
`0x0071C780`, the `LeaveRoom` binding calls `InRoomEventHandler` (`0x00698290`)
if the room record is already absent. The exact ActionScript page navigation
and the caller that produces matchmaking 21/3 have not been established.

`CL_GetServerCommand` dispatches at `0x00487811` by the first command byte:
`d` goes to `0x00487869`, `k` and `x` to `0x00487892`, and `t` to
`0x0048782E`; other letters in its `d`-through-`x` table fall through. The
`t` arm calls `CL_HandleDisconnect` (`0x004960E0`). For `EXE_MATCHENDED`, its
equality branch at `0x00496114` calls protected `Com_Error(5, ...)` at
`0x00496157` and returns; it does not call `0x0071C780` or the room leave
routine. The protected error implementation prevents a complete static trace
of its frontend transition, but the live timed and score-limit outcomes above
show the resulting room page is unusable. This reliable-command dispatcher
offers no path to execute a local console command sent by the server.

The other `t` reason branches do not provide a supported replacement.
`EXE_MIGRATIONABORTED` and `EXE_MIGRATION_IN_PROGRESS` take
`Com_Error(3)`; `EXE_PLAYERKICKED`, `XBOXLIVE_SIGNINCHANGED` and generic
reasons take `Com_Error(4)`; `hostquit` and `roundsdone` return without
tearing down the room. None visibly calls `0x0071C780` or
`dwRoom::LeaveRoom`. The protected `Com_Error` implementation limits the
static UI trace, but changing the reason has no evidence of preserving the
results screen and returning to a valid room without a false notice.

C1 registers a local `room.match.cancel` console command (name `0x00C7DB40`,
registration `0x00719895..0x007198BE`). Its callback `0x00718FA0` directly
calls `0x0071C780` without `Com_Error`. This is an existing non-popup cleanup
path, **not a verified post-match repair**: whether it works after a completed
match, sends 21/3, or transitions the ActionScript page is untested. The
related `room.match.testend` callback at `0x00719610` also calls
`0x0071C780`, but is a test command. No inspected room push provided a safe
normal-end equivalent. Type 9 is targeted member removal and reports reason
8, so using it as a routine match-end shortcut would misrepresent the event;
type 8 is rejected for the host-created room; the tested type 4 did not help.

There is **no evidence-backed server/lobby-only fix** for the required
natural return to a usable room. The smallest credible next investigation is
the frontend's normal-end handling: establish where its results-page
transition should invoke the existing `LeaveRoom` cleanup and room-page
navigation. This repo has tools for asset extraction, font GFX rewriting and
FFOTD StringTable delivery, but no demonstrated patch path for the frontend
ActionScript in `codo.gfx`. Do not infer success from static calls, a delivered
lobby push or a visible Ready button. Acceptance requires the same C1 process
to leave a naturally ended match without a false notice, send the expected
room/session teardown, create or join a fresh room, send Ready as room 11/4,
receive StartGame, and spawn.

## Exact menu-movie evidence

The current `patch_ui_mp` rawfile `scaleform/default/codo.gfx` was extracted
from the 1.1.1.13 zone (4,498,073 bytes, `GFX` signature) and its ActionScript
exported with the installed FFDec 25.1.3. This is the in-game menu movie,
unlike the launcher's separate `CODClient.swf`. In its `LobbyController.as`,
`onChangeReadyStateHandle` returns before calling native `SetReadyState` when
`isRoomInfoReady()` is false. That predicate requires both a nonempty
`_roomObj.name` and at least one `_roomMembers` entry. The observed empty
post-match room panel and missing 11/4 Ready request are consistent with this
guard; a simultaneous read of those ActionScript fields is still needed to
prove which one is empty.

In the same movie, `MatchController.as::onBackToRoomHandle(FIRST_PAGE)` checks
`isInRoom()` after an `EXE_MATCHENDED` return. Its in-room branch calls native
`RefreshInRoom()` and then `goRoom(true, "", true, true)`, which opens the room
page. `LobbyController` populates its local room object and roster from
`ROOM_INFO` and `ROOM_MEMBER_INFO` task results; its `bind_onRoomLeft` clears
both and navigates home. `initRoomMembers` first empties `_roomMembers`, then
rebuilds it from the delivered native array. The native `RefreshInRoom()` path
below has a zero member count to publish after Ready. A frontend change that
only bypasses `isRoomInfoReady()` would allow a Ready request but would not by
itself restore a real room roster. The decompiled `CFunctionContainer.as` body
is a stub for the native binding; the C++ path was inspected separately.

The scratch export lives under `%TEMP%/codol-11113-e2e-20260928/codo-as3`;
it is diagnostic output, not a deployed patch. No GFX/client modification was
made or claimed tested in this pass.

The `RefreshInRoom` native Scaleform binding registers at `0x006B0738` and
calls `0x006AF2C0`. In the live C1 process its room singleton vtable was
`0x00C7D66C`; `RefreshInRoom` dispatches virtual `+0x6c` (`0x0070ED50`) and
`+0x68` (`0x0070ECB0`) on that singleton. Those methods walk local room records
and listeners; no Demonware task dispatch appears in either method. A
controlled Combat score-limit-1 end on the same client/server processes again
showed the empty room panel. Read-only C1 memory at singleton `0x082D5470`
showed room record `+0x10 = 0x0810C520` before and after that natural end;
the `+0x15a70` count used by the `+0x6c` method was zero. Clicking the menu's Leave returned
home, after which `+0x10 = 0`. This proves natural end retained the native
room record while explicit Leave cleared it. It does not prove whether the
record was already incomplete before end or exactly why its ActionScript
room data was empty. The temporary score limit was restored to zero and the
single dedicated server was left running.

## Ready-time room roster loss and two controlled A/B tests

The canonical lobby's `dw_rooms.py` currently sends two map messages after
Ready: a type-5 `JoinResponse` with zero members, then a type-15 room-info
record. Exact C1 code ignores type 15 when the client is the room host; the
type-5 record is what updates its map. The type-5 handler also writes its
member count to `dwRoom+0x15a70`. Read-only C1 memory measured that count as
**1 on the usable room page** and **0 during the match** immediately after
Ready. This explains why the native `RefreshInRoom()` has no member records
to publish on return, and the menu's `isRoomInfoReady()` guard blocks Ready.

Two temporary isolated-lobby variants were run through the real C1:

1. With the type-5 map message omitted, the roster was preserved, but C1
   loaded its stale `mp_crash_tropical` while the server announced
   `mp_killhouse_sh`. `console_mp-004.log` records the wrong zone load and
   the missing-BSP disconnect. The host ignored the remaining type-15 map
   message, as the static guard predicted.
2. With one synthetic host member placed in the type-5 roster, C1 immediately
   raised `Com_Error[702]` while resolving `broadcastCharacterIndex`, before
   the match loaded (`console_mp-005.log`). The 314-bit member record does not
   carry the client-side structured-data fields required by the room card.

Both variants were removed from canonical and isolated lobby code; the
source tree was left clean and the prior playable join behavior restored.
The client and single lobby were restarted after each failed variant, never
duplicated. These tests establish a concrete dependency: the selected map
must reach the host without replacing its live roster, or a later valid room
member/profile refresh must restore that roster before the post-match page
opens. Neither has been verified yet. An empty roster is a gameplay blocker,
not merely a cosmetic missing character card.
