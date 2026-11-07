# Multiplayer fix and test priority — 2026-09-29

## Evidence boundary

The attached screenshot reports player-visible symptoms. The client logs under
`E:/codol-classic/main/` span September 26–28 and several server revisions;
they do not establish that every symptom remains on the current build. The
reporter's additional `C:/Users/zz/Downloads/console_mp.log` records an active
match from September 28 17:30–17:45 with repeated RC-XD and Predator splashes,
but has no offhand input/state trace or timestamp for the failed throw. It
cannot identify the state that disabled equipment. The
September 29 local bot server proves Killhouse graph load, bot spawning and
server-side bot kills. A later isolated C1 process joined and played Killhouse
with 12 Recruit bots, left through the menu and rejoined, then completed a
timed round. This does not cover the separate level-5 player account or the
reported two-streak equipment failure. Use paired client `console_mp.log`, server `qconsole.log` and
`games_mp.log`, lobby log, build hashes, map/mode, and a short screen capture
for every reproduction below. Keep the original logs intact.

## Priority order

| Priority | Issue and evidence | First decisive test | Fix boundary / acceptance |
| --- | --- | --- | --- |
| P0, one producer gated, local repeated joins clean | **Client command overflow disconnects.** Four early `EXE_ERR_CLIENT_CMD_OVERFLOW` cases: `console_mp-006.log:5092` and `console_mp-009.log:4983,14702,19424`. A later paired VPS capture identified a separate `jr` join-request storm into an in-match host; the lobby now gates that relay. The four early cases have no paired command trace, so their producer remains unassigned. The existing C1 made repeated same-process Killhouse joins and manual exits with 12 bots during this pass; the latest 5,000 client-log lines have no overflow, `EXE_SERVERQUIT` or DObj error. | Rejoin the original failing map/loadout with a second human joiner; capture C1's sequence/ACK window and server receive/ACK trace. Include a no-bot control to isolate any remaining producer. | Confirm the in-match join-request gate live on the original contour, identify any remaining producer from a paired trace, then complete sustained multi-client play without overflow. |
| P0, original maps pass with owned M4A1; exact skins open | **M4 viewmodel `1073 tag_weapon` disconnect.** Archived Rust and Afghan failures both assembled two nameless arm models with only `trim_char_*` bones before a correctly named M4 gun. The old deferred `d` configstring pump reread values from the wrong overlapping table, blanking inherited arm slots; commit `1a11932` stores the original command value. A synthetic C1 mirror found 43–166 bad slots per reload before the fix and zero after four reloads. In one unchanged C1 process, owned custom-class M4A1 rendered in Killhouse, Rust and Afghan; Rust and Afghan both passed M4A1→M9→M4A1, controlled enemy death and F respawn with the rifle and arms visible. The current Afghan trace published named arm model `fja_tanktop_sc_m_vmchar_wht`, native 165/wire 141, 68 bones with `tag_weapon=1`; named hands model `han_tactical_ss_s_vmchar_15` was native 166/wire 96. The last 2,500 C1 console lines had zero `1073`, `tag_weapon`, `EXE_SERVERQUIT` or client-command overflow. | Equip the **archived exact** Rust `wea_m4_m4_blk_vmgun` and Afghan `wea_m4_m4_02_vmgun` recipes, including their attachments, and repeat the two-map cycle while logging C1 registration and arm tags. The current owned M4 skin was not separately identified as either archived recipe. | The owned M4A1 map, switch and respawn contours pass on both original maps; the original skin/attachment recipes remain the final gate before closing this disconnect. |
| P0, server path fixed | **Bot spectator/map restart script fatal in an older server log.** `bin/home/main/qconsole.log.old:2363-2404` records an RC spawn influencer team error on bot spectator spawn. The spawn selector now omits RC influence for a spectator, which has no combat team. | The retained script resolved against 973 builtins. A live same-process `map_restart` loaded the edited script; 12 training bots reached `CS_ACTIVE` with no script runtime/fatal error, and PID 10016 remained the sole UDP/17733 owner. | Repeat a human switch to spectator and back when C1 is available. The bot initialization/restart contour passes; the broader human transition remains open. |
| P0 resolved locally, reconnect gate | **A restarted C1 was offered a cached match descriptor with a stale security key.** At 02:58 the lobby marked its held key `SUSPECT` but still answered `findSessions` with one phantom session; C1 entered the room, and repeated Ready clicks produced no StartGame message. | Restart C1 against the patched lobby with a cached descriptor, then use the normal Multiplayer path. Check `findSessions`, `createSession`, key observation, StartGame and server admission in order. | On the September 29 local retest, the fresh client received zero stale results, created its own session/key, got StartGame automatically, and reached server `CS_ACTIVE` with one dedicated server on UDP/17733. Repeat after a later client restart before treating it as a broad regression pass. |
| P0, natural end reproduced | **Natural match end returns C1 to a broken room.** The earlier menu exit sent matchmaking 21/3 and room 11/2; the patched lobby retired the descriptor. A September 29 same-process C1 menu exit, queue, ready, class-select and spawn succeeded; a 60-second read-only capture on the second join peaked at three outstanding reliable commands. Three one-minute timed rounds ended normally, then C1 displayed an empty server panel, a wrong room card and a Ready button that emitted no new room task. The lobby recorded `ClientDisconnect` telemetry but no 21/3 or 11/2. Two isolated trials of a C1 type-4 `Clear Readys` lobby push, including the same sender ID as the working StartGame push, both left the room broken; the experiment was reverted. Native `codol_exitToLobby 0` rotated into a playable next round on the same server, but it bypasses the requested lobby return. Exact C1 room-state reads found the Ready-time synthetic type-5 map response zeroes its member count; the frontend requires at least one member before sending Ready on return. Omitting type 5 loaded the wrong map, and adding one member caused Com_Error 702; both tests were reverted. | Replace the Ready-time map update with a room protocol path that preserves a valid roster and correct map. Repeat timed and score-limit ends followed by immediate Ready, requeue and spawn in the same C1 process. See `CODOL_POSTMATCH_LOBBY_20260929.md`. | The lobby's 21/3 retirement fix passes the menu-exit contour. Natural end still fails and must reach a usable next match without restarting C1 or manual room recovery. |
| P1, controlled same-process C1 pass | **Newly earned class unlocks stay locked until C1 restarts.** The earlier lobby credited level 3→5 but task 30's one-shot copy left C1 with only flags 1..3. The rank script now sends `cg_unlockFlagSet` after XP sync. In the existing C1 PID 3384, a developer-only targeted XP hook drove the ordinary rank function: C1's flag count rose 26→27, ID 6 appeared while the copy guard stayed set, and the in-match menu gained custom class 3. After manual Leave, C1 showed level 6 and unlock notices; the lobby backpack opened and class 3 selected with its own loadout, without restarting C1, lobby or server. | Repeat with naturally earned XP and a normal match end after the post-match room repair; check both class and character customization, then repeat with a clean level-1 profile to rule out early unlocks. | The controlled promotion and class menu pass. Normal XP, natural match-end lobby return and all customization categories remain open. |
| P1, partial controlled C1 pass | **Lethal equipment and tactical input stop after more than one killstreak** (screenshot report; no paired failure trace yet). After two UAV uses, a controlled RC-XD death and a second RC-XD, C1 key G threw its frag; native offhand ammo changed `frag_grenade_mp:1` to `:0`, with `disabledOffhandWeapons=0`. This default class had no tactical offhand, so it cannot establish the tactical half. | Test a class with both lethal and tactical on the user's profile, with two different reward orders and a second life; capture offhand selection/ammo, hold counter, weapon flags and client input. | Both actions work after the same mixed-reward sequence; no stuck disabled-offhand counter. The tested lethal path passes, the reported full scenario remains open. |
| P1, controlled C1 pass | **RC-XD cannot be used again after use followed by death** (screenshot report). A controlled C1 ride showed remote control active, `disabledOffhandWeapons=1` and `rcRule=1/3`. Death during the ride restored the rifle, `usingRemote=0`, remote control off, RC claim released, `rcRule=0/3` and offhand hold 0. A new RC-XD was then granted; C1 key 8 opened the controller and a visible second RC camera. After that ride, the same cleanup fields were 0/released and a real frag throw worked. | Repeat with an ordinarily earned RC-XD and death just after the ride, plus tactical input. The first ride used a developer activation hook; the second used C1's bound key. | The tested death-during-ride then second-use sequence passes in C1; the broader timing and loadout cases remain open. |
| P1, controlled C1 pass | **Earned killstreaks stop cycling within one life** (September 29 human report). The award loop skipped rollover entries; its later fixed list also stopped after ten cycles. A developer-only hook drove the real award path on a bot from 3 through 102 kills, then death and 3 kills. In live C1, the hook awarded UAV at 3 and 6 in one life; key 5 consumed the oldest copy and left the next owned/selected, then another press consumed it. A bot kill occurred before the later synthetic jump to count 9, so its three new awards belong to a fresh life and do **not** extend that one-life observation. A controlled death then preserved those copies, and new count 3 added another. | Repeat with actual human kills and multiple configured reward types, then death during RC-XD; verify HUD and offhand behavior as well as the server inventory. | The native award path can extend beyond ten cycles and preserve queued rewards across death. The controlled C1 two-award/use path passes, but mixed rewards and ordinary kills remain open. |
| P1, controlled C1 pass | **Killstreak splash says key 8 while UAV works on key 5.** Exact C1 localize `MP_EARNED_UAV` contains `{ACTION_SLOT_HELP}`. C1 resolves it from a separate clientInfo byte at `cg+0x15ae80`; the UAV was in slot 2/key 5 while this byte selected slot 1/key 8. Merged source now publishes the earned reward's slot with `setActionSlotHelp`. On the deployed build, controlled C1 UAV awards at 6 and 9 showed key 5 in the splash, matching its HUD; pressing 5 used the reward. | Remap the key and repeat, then test each configured reward type and slot in C1. | The C1 splash and HUD agree for the tested UAV bind. Other rewards and remapped binds remain to verify. |
| P1, script fix deployed; human HUD retest pending | **Killstreak bar appears full with no reward.** The live class log selected UAV in slot 0 and no other reward. The server awards one UAV at the base threshold and repeats it at later rollover thresholds, but the HUD target stayed at the base cost while its published count kept increasing. The display could therefore remain full between awards. The GSC now publishes progress within the rollover span while preserving the unbounded award count; a live `map_restart` lowered the script, 12 Recruit bots became active, and a controlled bot award path ran without script error. The screenshot alone does not establish the player's exact current kill count. | In the same C1 process, earn and use the first UAV, then reach the next threshold without dying. At each kill compare the bar, server count, owned reward queue and key-5 activation. Repeat with three different equipped rewards. | The bar resets to the next cycle after a completed threshold and reaches full only when the next reward is earned; owned copies remain usable in earned order. |
| P1, measured C1 contour passes; reported bar unidentified | **Damage display carries across death** (September 29 human report). Native `ClientSpawn` clears playerState damage fields; C1's `0x00453EE0` health ratio reads wire stats `+0x190/+0x198`, and `0x0045D780` starts directional effects only on a new damage event at `+0x17C` with nonzero count at `+0x188`. In 1,192 read-only C1 samples at 50 ms intervals, natural bot damage drove health 45→15→0 and overlay intensity 0.55→0.85→0. The next spawn changed `spawnTime`, had health 100/100, damage timer/event/count 0 and overlay 0/inactive through the rest of the capture. A separate developer-triggered `downed 12` produced a real death; the immediate post-F screenshot showed no red tint. The reported visible bar was not identified, and immediate new-life bot fire caused one 75/100 sample after an earlier respawn. | Capture the exact bar on a reproducible prior-life hit, death and first spawn; pair screenshots with C1 health, damage timer/event/count and overlay values. Test with and without immediate new-life damage. | The measured health tint resets on the tested deaths. Do not change that path without a matched failing visual; the user's specific bar remains open. |
| P1, timed and score-limit reason verified, lobby gate | **Normal score-limit end shows a false partner-left popup.** In the September 29 human run, `exitLevel` sent `t EXE_MATCHEND_PARTNER_LEAVE`; C1 displayed the notice. Exact C1 disassembly proves `EXE_MATCHENDED` bypasses profile invalidation. The server now flushes C1's direct secure-record `K` updates before sending the normal `t EXE_MATCHENDED`. In controlled timed and score-limit C1 rounds, the result sequence completed, the server sent `t EXE_MATCHENDED`, and C1 returned without the false popup; both entered the broken room described above. The score-limit client was spectating at settlement and earned 0 XP, so XP refresh remains untested. | Repeat a human score-limit end with earned XP; capture ordered `K`/`t`, result summary, lobby XP and career page. The exact branch evidence is in `docs/CODOL_MATCH_END_REASON_CONSTRAINT_20260929.md`. | End a normal match without blaming another player, reach a usable lobby, and refresh career XP promptly. Preserve the result summary. |
| P1, backend accounting verified for three local reports | **XP shown after a match differs from credited XP** (screenshot report; its example text is cut off). The three saved human reports list 780, 4,460 and 4,960 XP; the lobby credited exactly those amounts to one profile, reaching 10,200 XP/level 5. Both `mpdata_s` copies decode to 10,200 XP and the stored service blob matches the per-user file. | Record the C1 post-match amount and cached rank/XP before leaving, after task 30, and after a clean reconnect; compare with the already reconciled server report and profile. Repeat one short FFA and one team match. | The displayed award and persistent account delta agree for each match, and new unlocks appear without stale same-process UI state. The three local backend credits do not establish C1 display correctness. |
| P1, bot killfeed visible in C1 | **Killfeed missing after latest update** (screenshot report). Obituaries use `EV_OBITUARY` snapshot entities. A shared overlay used to reject the event because its native type number differs from C1's wire type; merged commit `6a58e5e` corrected that comparison. The native regression carries an obituary seed with its C1 wire type. During the September 29 same-process M4A1 test, C1 visibly showed several Training-bot kills with weapon icons at lower left after late join and again after respawn. Received `Command: K` lines are secure-profile updates, not killfeed evidence. | Capture a human-involved kill with server obituary creation, snapshot publication, client handling and screen video; check names/icons after another late join. | Bot-vs-bot feed is visible through the tested late join and respawn. Human-involved entries and all icon mappings remain open. |
| P1, guard deployed; controlled replay matches | **Killcam sometimes follows another character** (new player report, September 29; no paired wrong-camera trace yet). `_damage.gsc` derives `attackerNum` from the killer and `_killcam.gsc` stores it as `forcespectatorclient`. Native `SpectatorClientEndFrame` can drop forced follow when an archive is unavailable and enter ordinary follow. A guard now ends the replay if the actual follow target changes to another client. Four controlled `downed` calls in the existing C1 process selected Training 2 as attacker in the server log; visible replay cards on Killhouse, Rust and Afghan named Training 2, including an Afghan first-person camera. These are positive controls, not reproduction of the intermittent wrong target. | Record one wrong replay with victim/killer client numbers, death and respawn times, the existing `codol_debugTrace` killcam tuple (`fsc`, `sc`, `psCl`, archive time), entity reuse, and screen video. Repeat with rapid bot kills, simultaneous deaths, and killer disconnect/respawn. | Each replay follows the killer for that death, or deliberately ends if that target is unavailable; its name/card and camera agree with the server death record. |
| P1, live server verified | **Rifle and SMG kills were classified as pistol bullets.** The pre-fix bot-only Killhouse log had 1,529 `MOD_PISTOL_BULLET` kills among 1,905 kills, including composed primary-weapon recipes. Retained `Bullet_Fire` selects pistol/rifle MOD and trace priority from `WeaponDef.bRifleBullet` at native `+0x4e0`, but the native C1 weapon loader never populated it. Exact C1 weapon data supplies the corresponding boolean at `+0xbc4`. | The full native test suite passed (84 `PASS` lines, exit 0), including both rifle/pistol mapping values and invalid input. On the newly deployed single server PID 4788, 60 bot kills included 38 `MOD_RIFLE_BULLET`, 11 `MOD_PISTOL_BULLET`, 7 `MOD_HEAD_SHOT`, and 3 `MOD_MELEE` (one other kill). Three distinct composed recipes produced rifle MOD; one distinct recipe produced pistol MOD. Compare human killfeed/killcam if needed. | Damage/kill classification and bullet trace priority follow the mounted weapon definition without changing its class or loadout. |
| P2 | **FFA score readout stays unchanged while the match score progresses** (screenshot report). Current source has `CODOL_PublishPlayerScores` called from `SV_Frame` before client messages; it sends the exact `E <client> <score>` command that C1 uses to patch its cached row. No human C1 score event was captured on this build. | With TAB closed, earn one score event; compare `sess.score`, outgoing `E <client> <score>`, full `b` board after TAB, and the bottom-corner readout. | The HUD updates promptly without TAB; full board and authoritative score agree after a late join and match end. |
| P2 | **Scoreboard sometimes does not appear after Alt-Tab during loading** (screenshot report). | Repeat the same join with and without Alt-Tab, in windowed and fullscreen modes. Record focus changes, scoreboard key/input, client `s`, server `b`, and screen behavior. | If `b` arrives, repair the client UI/focus state; if it does not, repair the request/reply path. HUD visibility returns correctly on key release in both cases. |
| P2 | **Alt-Tab/Windows key unavailable during matchmaking or a match** (older screenshot post). | Test matchmaking, map load, active play and pause menu separately in windowed/fullscreen mode; record focus/window style and input-grab transitions. | Windows focus switching works in each supported mode without changing gameplay input or causing the scoreboard regression. |
| P2 | **FOV and FOV scale reset on joining** (older screenshot post). Current MP GSC omits the inherited `cg_fov` spawn reset and `cg_fovScale` connect/match-end resets. The join path and C1 saved-setting behavior still need measurement. | Set distinct saved FOV/scale values, record them before queue, during map load, after spawn and after leaving. Trace any server `setClientDvar` and client profile reload at the first change. | User values persist through join, death, map rotation and return to lobby. |
| P2, intermittent and unconfirmed | **Some bots slide without a walking animation** (September 29 human report). Native bot command movement, pmove locomotion selection, entity animation publishing and the exact C1 animation consumer are connected. A prior 660-sample live probe found no fast-moving bot with an idle or missing legs animation; it cannot rule out the rare visible slide. | Record a short clip with map, bot name/slot and time, then pair native usercmd movement, server legs animation and client entity animation for that bot. The read-only `codol_hitprobe <botSlot>` reports origin and resolved legs/torso animation for a selected bot. | Movement and locomotion animation agree through route turns, combat, death and respawn without a stale pose. |
| P2, new log finding | **C1 repeatedly reports a missing bot muzzle tag or DObj.** The September 29 local `console_mp.log` contains 585 `No tag_flash or DObj in CalcMuzzlePoint on entity 0 (eType 1)` warnings. Entity 0 was Recruit bot Training 1; the human was slot 12. Exact C1 code checks the client-info `+0xAF4` vehicle/alternate entity selector before falling back to the player's DObj; zero is expected on foot and is unrelated to the separately linked world-gun child. A 90-second live sample found the player's DObj present in 1,721/1,782 samples but no `tag_flash` in its sampled models. The warning does not prove a missing first-person gun model or wrong server hit result. | During one controlled slot-0 shot, capture the C1 selected DObj/tag result and separate world-gun child/model, plus the server child, weapon selector and link state. | The bot world gun yields a valid muzzle transform and correct visible effects without repeated warnings. |
| P2, source fixed, client gate | **A queued model update from a different category can overwrite an inherited MP model after map transition.** The shipped Zombies table leaves index 1685 free while MP inherits `bar_spcsshotgun_tf_f_10` there. Reassertion previously checked only the override bank, so it could miss that MP value. This is a separate conditional defect, not an established cause of the archived same-category M4 failures. | Queue a Zombies runtime model at index 1685, transition the same C1 to MP while the command is pending, and capture the first snapshot/model registration. | The inherited MP model wins after the new gamestate; no wrong or empty model survives the first snapshot. |
| P2, tiers implemented | **Named bot difficulty tiers.** The exact 1.1.1.13 `mp/botdifficultytable.csv` and `mp/botclasstable.csv` provide Recruit, Regular, Hardened and Veteran data. | Sequential map restarts in one live server verified all four named values, class lineups, 12 bots, and no script errors. | The server uses authored response/fire/turn/ADS values plus class eligibility. Human balance and other authored AI fields remain open. |
| P3, promote if correlated | **Other log warnings.** The Sep 28 client log has a join-request burst (`WARNING! TOO MANY MESSAGES`, up to 824 queued), missing soundaliases and repeated model-mark transfer messages; the isolated Sep 29 client has HTTP/table misses. | Correlate each warning with a visible failure and its exact build. Isolate the join-request burst from the older command-overflow cases; temporal proximity is not causation. | Fix the specific user-visible effect or queue producer. Do not treat generic warnings as proof of any screenshot bug. |

During the damage check, an uncommitted developer-only `chip` probe caused
`LOCAL_VAR_STACK_SIZE exceeded` on `map_restart`; source and runtime copies
were reverted to the previously tested script. The crashed server PID 18036
was stopped and its port verified free before one replacement PID 12324 was
started with the same configuration. The original C1 PID 3384 then rejoined
Killhouse, selected custom class 3 and played with 12 bots. This failed probe
did not enter a commit or remain in the running script. It also shows the
static script resolver alone does not catch this compiler limit.

The bot muzzle warning's exact client branch and paired capture plan are in
`docs/CODOL_BOT_MUZZLE_WARNING_20260929.md`.
The deployed read-only `codol_worldgunprobe` now reports the live child,
selector and captured link. Repeated local samples found a valid linked gun
for all 12 Recruit slots when alive. C1's selected centity/DObj remains the
unmeasured side of this warning.

## Execution sequence

1. Capture a clean, same-build baseline: one human C1 plus bots, exact map/mode,
   build identity, paired logs and video. Reproduce P0 cases before changing
   gameplay. Recheck the old spectator fatal on the current build.
2. Exercise the two killstreak/offhand state machines with a human client; bot
   kills alone cannot test C1 reward selection or equipment input. Run the XP
   accounting capture in the same controlled matches.
3. Verify the three independent UI transports: killfeed obituary snapshot
   entities, whole scoreboard `s`/`b`, and incremental score `E`. Compare
   killcam target identity through GSC, archived frame and C1 presentation.
   Then run the Alt-Tab, FOV and Windows focus
   comparisons.
4. After each fix, rerun its decisive contour and one ordinary match through
   death, respawn, map transition and reconnect. Keep a before/after log pair.

## Work completed on September 29

- The submitted `C:/Users/zz/Downloads/console_mp.log` contains repeated
  RC-XD and Predator reward splashes during three active rounds on the remote
  server. It has no offhand button, offhand hold, or thrown-grenade trace, so
  the exact reported failure time cannot be recovered from this log alone.
- Existing source commits `a9c34e5` and `c964660` address a death-interrupted
  RC-XD use and an unbalanced offhand hold. The isolated native two-bot probe
  `tests/probe_codol_mp_streaks.py` passed on the current deployed executable:
  a bot died during RC-XD control, the rule slot and offhand hold returned to
  zero, it activated a second RC-XD, and the real grenade-fire path threw a
  frag and a concussion grenade afterward. This is a server-side regression
  result; C1 human input and HUD still need a paired test.
- The September 27 `1073 tag_weapon` logs precede commit `1a11932`, which
  fixed deferred configstring values for loading clients. An opt-in trace now
  records the selected first-person arm/hand model names, native/wire indices,
  skeleton dimensions and `tag_weapon` presence. Current Rust/Afghan C1
  reproduction remains required before closing the issue.
- In both archived failures, C1's assembled first-person DObj lists two
  `Model ''` entries with character trim bones before the named M4 gun model.
  Rust used `wea_m4_m4_blk_vmgun` and Afghan used
  `wea_m4_m4_02_vmgun`, so the failure recurred across two gun skins while
  both leading arm/hand model names were empty. The assembled DObj lacks
  `tag_weapon`. This narrows the next trace toward
  arm/hand model publication and registration as well as the weapon recipe;
  the old logs alone do not establish which producer omitted the tag.
- An additional archived failure class appears twice in
  `console_mp-005.log:3754,6585`: `EXE_ERR_SERVER_TIMEOUT` while C1 was still
  `CA_CONNECTING` to the September 27 remote endpoint. These are connection
  attempts, not mid-match drops, and have no paired server admission trace.
  Recheck only if the current server reproduces them; do not combine them with
  the reliable-command overflow or the M4 DObj error.
- A read-only live `codol_hitprobe` sample on Killhouse recorded 144 paired
  bot poses across all 12 slots; 136 pairs moved more than 12 units. Twenty
  coarse pairs ended on `pb_stand_alert`, but each pair spanned many RCON
  probes and could include a normal stop or respawn. A focused 65-sample
  sequence for each of slots 9, 2 and 1 found no consecutive movement over
  8 units within 0.4 seconds while both poses stayed idle/alert. This does
  not rule out the reported rare visible slide; a C1 clip and paired entity
  animation are still needed.
- Cross-category reassertion now uses the effective configstring: a published
  override wins, including an explicit empty override, otherwise the inherited
  fastfile value is restored after a stale queued command. A compiled isolated
  check passed both precedence cases. The full Windows cross-build linked a
  PE32 executable at `obj/win-cross/codol_dedrun.exe` (SHA-256
  `8C70370B08F0E7BEEE4150B3F89B6ED6250ACE6A3FF2F183F75C07E81FFF05B3`).
  The live PID 10016 was not replaced; no Zombies-to-MP C1 transition was run,
  so this remains a built source fix with a client gate.
- A same-process trace restart on the current live build published 12 bot
  profiles with 12 available arm models, all with `tag_weapon` in their
  mounted skeletons and none with a missing tag. This checks the current
  server asset path for bots, not C1's resolved model names or the human M4
  recipe that failed in the archived logs. The trace was disabled afterward;
  PID 10016 remained the sole UDP/17733 owner with no script runtime error.
- Exact C1 disassembly identified `EXE_ERR_CLIENT_CMD_OVERFLOW` as the
  256-entry client-to-server reliable text-command window. A bounded opt-in
  native trace (`codol_traceClientReliable`) now records receive/ACK progress
  without command arguments. A paired C1 sequence/ACK capture is still needed
  before assigning a cause.
- Rechecking the exact C1 executable (SHA-256
  `086B2BCF109C8340A898606E5CAA2678242449452BCF62B2DDA22A6E37DDA91F`)
  found both direct references to this error string at `0x00493BD3` and
  `0x00710775`. Each compares the client's reliable sequence minus its
  acknowledgement with `0x100` before raising the error. The first path then
  indexes a 256-entry ring with 1024 bytes per command. An older lobby note
  confused that entry size with the overflow condition; the four archived
  errors need a sequence/ACK trace, not a search for one oversized string.
- `tools/codol_client_reliable_probe.py` now reads only C1's sequence and
  acknowledgement from the verified executable's process memory, recording
  UTC time and outstanding count to CSV. It rejects a different process image;
  syntax/help and a wrong-process rejection passed. The live server still has
  `codol_traceClientReliable=1`, so the next human join can pair this client
  window with receive and outgoing-ACK events. No C1 process was running for a
  live capture when the tool was added.
- A later September 27 paired lobby/server capture, preserved in the lobby's
  `demonware/dw_rooms.py` rationale for commit `4cdc779`, identified one
  overflow producer: one room join batch contains 16 type-6 requests, and C1's
  in-match host forwards each as reliable `jr <uid> <n>` (inline producer at
  `0x00710743`). Repeated batches were observed at about 200 ms intervals,
  followed by the host's `EXE_ERR_CLIENT_CMD_OVERFLOW`. The current lobby gate
  does not relay such a batch to a host that `match_instances.locate` finds in
  a match. The canonical room self-test passed all 37 checks, including the
  measured 16-request batch and in-match suppression; the instance placement
  self-test also passed. The full canonical lobby self-test passed under its
  project virtual environment, with `pycryptodome` available. The isolated
  live lobby's `dw_rooms.py` hashes exactly
  to the canonical copy, whose default is to drop this relay. No current C1
  joiner was present to validate the gate end to end, and this later mechanism
  does not by itself attribute the four earlier overflow lines.
- The four early error-adjacent 15-second windows contain 416, 816, 576 and
  176 `JoinRequestHandler: Could not find senderID in chat channel` lines,
  respectively. Exact C1 code at `0x00711853..0x00711866` logs that warning
  on a missing-sender rejection and jumps to cleanup at `0x00711B41`;
  `jr` is enqueued by a separate room pump at `0x0071072E..0x007107AB`.
  Comparable warning bursts of 736, 717, 704 and 736 lines occurred without
  an overflow in the next ten seconds. Warning volume is therefore neither
  a reliable-command count nor sufficient to identify the old producer.
  Keep the four cases unassigned until a sequence/ACK and verb capture exists.
- Rechecking the four archived overflow times against the client's
  `WARNING! TOO MANY MESSAGES` lines found the nearest preceding warning
  525, 57, 348 and 41 seconds earlier, respectively. Those warnings describe
  a separate queue and are not a paired command/ACK trace. The live single
  server now has `codol_traceClientReliable=1` for the next human join; the
  bounded trace emits only recognized command verbs and sequence/ACK numbers,
  never command arguments. Do not infer a root cause until that capture exists.
- The first live login at 02:17 failed with C1 error 716 because the isolated
  lobby ran under the global Python installation and generated a zero auth
  ticket without `pycryptodome`. Restarting only the lobby under the project's
  virtual environment produced a real ticket; C1 then joined the 12-bot
  Killhouse Combat match. `tests/start_codol_local_stack.py` now checks crypto
  availability before launch instead of silently accepting a degraded lobby.
- In the human run, a developer grant gave client 12 `rcbomb_mp`; C1 activated
  it and the server spawned a remote-controlled RC vehicle. After the first
  ride, the claim was released and a second grant was owned and activated,
  according to the user. The score-limit end interrupted the planned death-
  during-control and post-respawn test, so the reported contour remains open.
- The match reached a normal score limit, wrote one human result row with
  4,460 earned XP, then sent `EXE_MATCHEND_PARTNER_LEAVE` at `qconsole.log` line
  65933. C1 showed that exact partner-left popup at 02:27:43. The match server
  remained up; the reported message is an incorrect normal-end reason, not
  evidence that a partner left. The isolated test round now has score and time
  limits disabled so the RC-XD contour can finish.
- The September 29 client restart exposed a separate lobby regression. A new
  connection inherited a cached descriptor even after the lobby marked its
  security key suspect. The canonical lobby and isolated live copy now answer
  zero results for that stale phantom session until this client supplies a
  fresh `createSession` descriptor. The lobby self-test passed, and a real C1
  restart at 03:05 followed the expected zero-result -> createSession -> live
  key -> StartGame -> server admission -> `CS_ACTIVE` sequence. Only one
  `codol_dedrun_next.exe` owned UDP/17733 throughout that successful join.
- A later match exit sent matchmaking `21/3` and the live lobby continued to
  advertise the departed room. The canonical lobby now retires the matching
  descriptor, its full self-test passes, and the patched isolated lobby is
  deployed on port 3074. The real C1 match-end/rejoin contour remains open.
- The native `make test-codol -j4` suite completed with exit code 0 after its
  send fixture was updated for the reliable-command trace. The one live
  server also completed all four bot-tier map restarts and a two-cycle
  killstreak award check; it was restored to 12 Recruit bots on UDP/17733.
- The level-5 profile and task-30 reply are current, but the running C1 had
  only rank 1..3 flags and a set one-shot copy guard. Exact C1 code accepts
  `cg_unlockFlagSet` as a reliable `s` command, parses pipe-separated IDs,
  and appends only missing flags. The rank script now sends the complete earned
  prefix after `syncXPStat()` on promotion. The same-process class menu result
  remains unverified; the client was closed for this follow-up. The active
  server's `map_restart` compiled the edited `_rank.gsc` and returned all 12
  Recruit bots to `CS_ACTIVE` without a script error.
  Exact command and client-cache evidence is in
  `docs/CODOL_UNLOCK_REFRESH_20260929.md`.
- The exact C1 disconnect handler makes a match-end reason change alone
  insufficient: `EXE_MATCHENDED` suppresses the popup but skips profile
  invalidation. The server now queues all final secure-profile `K` edits before
  the normal `t EXE_MATCHENDED` leave. The profile encoder test passed; the
  Windows cross build linked and was deployed as the sole server on UDP/17733,
  with 12 Recruit bots and no startup script or fatal error. A same-process C1
  match-end test must still verify the result summary, popup, XP and unlocks.
- Another branch supplied and tested the C1 action-slot splash fix before it
  was merged here. The merged script tree resolves against 973 builtins, the
  Windows cross build links, and the full native `make test-codol -j4` suite
  passes. The merged executable is live as the only server on UDP/17733 with
  12 Recruit bots; a current human C1 reward/remap retest remains open.
- The local server launcher now checks UDP/17733 before changing lobby state
  or staging a pack. The occupied-port test refused a second launch while
  PID 35020 kept running; a free-port check passed.
- An unattended current-build C1 retest reached the isolated launcher login
  screen, which required credentials. No authentication was automated or
  submitted; the launcher was closed. Consequently no new C1 gameplay,
  post-match rejoin, or HUD acceptance result came from that attempt.
- The merged live executable then passed a same-process two-bot RC-XD probe:
  first activation, death during remote control, remote/offhand release,
  respawn, second activation and release, then real frag and concussion
  grenade-fire events. It restored 12 bots on the same PID 10016 and UDP/17733.
  This does not prove the human C1 input/HUD path.
- The killcam follow-target guard passed static script resolution (973
  builtins, 1188 scripts, 107 reachable) and loaded on the live server without
  a script runtime error. A temporary watcher print established that bot
  deaths did not enter the player killcam path; it was removed. A human replay
  with a killer disappearing mid-archive is still required to verify the guard.
- The obituary regression exercises the same shared entity overlay that
  previously dropped native event type 87 after it had been translated to
  C1 type 128. The composed entity test passes with registered entity-state
  storage and an initialized event epoch. It establishes server publication,
  not C1 rendering. The full native suite passed before this test-only addition;
  the updated native integration target passed afterward.
- The single live server sampled 12 bots over 12 ticks with `codol_hitprobe`:
  144 state samples, 91 moving faster than 45 units/s, and none of those had
  an idle or missing leg animation in server playerState. The reported rare
  visible slide still needs a paired client clip and snapshot.
- All 15 supplied `mp_*_wp.csv` waypoint files were checked against the
  native loader's node, link, stance, annotation and file-size limits. Their
  declared row counts match, every link targets an existing node and has a
  reciprocal link, and each graph has one connected component; no structural
  rejection was found. Physical route traversal and maps without a supplied
  graph remain untested.
- A same-process `map mp_rust` test loaded the 192-node Rust graph and reached
  12 active bots. Ten `codol_hitprobe` cycles recorded 120 states and 66 moves
  faster than 45 units/s, with no moving sample in an idle or missing legs
  animation; the recent log had no script runtime or fatal error. The admin
  command omitted the normal `codol_sessionMap` handoff, so `sh1x_status`
  temporarily showed Rust as the level and Killhouse as the session map. The
  source's rotation and lobby handoff set both values. The same PID was
  returned to Killhouse, where both status fields again matched and 12 bots
  were active. A follow-up using the documented `set codol_sessionMap` then
  `map` sequence reached Rust with both map fields equal and 12 bots in four
  seconds, then restored Killhouse with matching fields and 12 bots in four
  seconds. A normal human post-match rotation still needs its own test.
- The remaining 13 supplied MP maps were loaded in the same dedicated-server
  process with the documented session-map handoff (five, then four, then four
  maps). Each `sh1x_status` reported the requested level and session map,
  `running=1`, and 12 bots. The server log confirms all 15 distinct waypoint
  CSVs loaded and contains no script runtime, script, or fatal error. PID
  10016 remained the only UDP/17733 owner and Killhouse was restored. This
  verifies map load and bot startup across the supplied maps, not physical
  traversal of every edge, human C1 presentation, or a real post-match lobby
  transition.
- A later same-process movement sweep revisited all 15 waypoint maps with 12
  bots each. Four bot slots were sampled seven times per map; 319 of 360
  consecutive position intervals changed by more than 12 units. Every map had
  movement: the per-map counts ranged from 6/24 on Storm Spring to 24/24 on
  several maps. A longer Storm Spring follow-up sampled all 12 slots eight
  times; every slot changed position, while several also showed death
  animations and stationary intervals between respawns. These coarse position
  samples include respawn displacement and cannot prove continuous waypoint
  traversal or resolve the intermittent C1-visible sliding report. The same
  server PID 10016 returned to Killhouse with 12 bots; its log still contains
  no script runtime/fatal error, frame rejection or snapshot overflow.
- The merged live build repeated the streak-award contour in the one existing
  server process: UAV at 3, airstrike at 6, stealth at 9, then a second UAV,
  airstrike and stealth at 12, 15 and 18. Repeating count 18 did not duplicate
  an award. After death, count 3 awarded the next UAV while prior rewards
  remained owned. PID 10016 stayed bound to UDP/17733, and 12 Recruit bots
  were restored. C1 display and inputs still need a human retest.
- The retained `_healthoverlay.gsc` starts a new regeneration worker on each
  `spawned_player` notification and ends it at death. Native `ClientSpawn`
  zeroes `gclient_s`, including the playerState damage timer, event and count.
  The snapshot overlay copies these zeroed fields into C1's damage netfields;
  the live `codol_publishExtendedPlayerState` cvar is `1`. These checks do not
  identify which on-screen bar persisted in the human report. A paired
  screenshot and state capture are needed before changing client-facing damage
  behavior.
- A second live bot animation sample ran 60 cycles of `codol_hitprobe` for
  slots 1–11 on the same dedicated server: 660 state samples, 492 movements
  faster than 45 units/s, and no moving sample with an idle or missing legs
  animation. Slot 0 was not included and slot 12 was not in use. This narrows
  the rare sliding report to a client-visible or unsampled transition, but
  does not prove either cause; a paired clip and entity snapshot remain needed.
- The long-running server log has no script runtime or fatal error. Its one
  `Error:` line is the optional Steam DLL load at startup. The repeated
  `defaultweapon_mp` warnings end at map-load line 53,307 and originate in
  `db_load.cpp`'s missing-zone fallback for map assets (including documented
  co-op pickups). The authored `botclasstable.csv` instead lists MP loadout
  names such as `usp`, not `usp_so`. This log alone does not show a bot holding
  a fallback weapon, so it is not counted as a new bot defect.
- The full WSL `make test-codol -j4` suite completed with exit code 0 after
  the obituary regression was integrated. It includes the native obituary,
  snapshot send/rollback, asset-name publication, profile XP and character
  composition targets; it does not exercise C1 rendering or account menus.
- The old bot fatal was in `_spawnlogic.gsc`: spectator spawn selection called
  `codol_rcSpawnWeight` with `self.team`, even though a spectator has no combat
  team to weight. Both spawn-weight call sites now skip RC influence when
  `self.sessionstate == "spectator"`. Static resolution passed (973 builtins,
  1188 scripts, 107 reachable). The live stack's loose override matched the
  edited file (53,259 bytes); the single server compiled it on `map_restart`,
  and all 12 bots entered `CS_ACTIVE` without a script runtime or fatal error.
- The isolated lobby's three archived human reports and SQLite
  `match_report_players` rows agree on 780, 4,460 and 4,960 XP credited, with
  `applied_live=0` each time. `profile_history` shows cumulative totals 780,
  5,240 and 10,200; the current profile is level 5/10,200 XP. The per-user and
  shared `mpdata_s` blobs each decode to 10,200, and the `storage_files`
  service blob hashes identically to the per-user file. Canonical
  `python -m career.rank_writeback --selftest` passed 66 checks. The reported
  XP discrepancy still needs the C1 post-match display captured beside these
  values; it is not demonstrated in this backend accounting chain.
- In the current MP GSC, `giveRankXP` calls `incRankXP` and adds the same
  post-gate award value to `pers["summary"]["xp"]`;
  `_scoreboard::processLobbyScoreboards`
  then sends `player_summary_xp` and its score/challenge/match parts to C1 at
  match end. The rank function's `rankingEnabled` and player-count gates run
  before both operations. The remaining C1 test should compare that summary
  command, the displayed match amount and the later `mpdata_s` refetch in one
  trace. The client display and its stale same-process cache are not proved
  correct by the source path or backend totals alone.
- A later Windows cross build linked from the current native source and was
  deployed through the guarded one-server handoff. Its SHA-256 is
  `8C70370B08F0E7BEEE4150B3F89B6ED6250ACE6A3FF2F183F75C07E81FFF05B3`.
  PID 20900 alone owns UDP/17733, loaded Killhouse/Combat and the edited rank
  script, and admitted 12 Recruit bots without a script error. This puts the
  effective configstring reassertion fix on the live server; the C1
  cross-category model test and real promotion/menu test are still open.
- The September 29 full WSL `make test-codol` rerun completed with exit code 0
  after the controlled C1 streak, RC-XD, match-end and post-match investigations.
  The offhand-control, frame-entity, snapshot-send, model, weapon, profile and
  animation fixtures passed. This is a source regression gate; it does not
  certify the remaining C1-visible cases. The live stack was left at one
  UDP/17733 server (PID 18036), one TCP/3074 lobby (PID 31012), and the
  existing C1 process (PID 3384), with unlimited score/time and the normal
  `codol_exitToLobby 1` restored.
- A developer-only `xp <clientnum> <amount>` action in the existing
  `scr_codol_usekillstreak` test hook now calls the normal human `giveRankXP`
  function and reports stored XP before and after. Static GSC resolution
  passed (973 builtins, 1188 scripts, 107 reachable), the updated hook and
  rank script matched the loose copies in the isolated server home, and a
  same-process map restart admitted all 12 Recruit bots without a script
  error. With C1 slot 12 connected, controlled awards showed stored XP
  11,150→11,250→11,350→14,350. A read-only C1 monitor observed unlock flag
  ID 6 append while its task-30 copy guard remained set. The in-match class
  menu gained custom class 3; manual Leave returned to the lobby with a level
  6 badge, unlock notices, and a backpack in which class 3 was selectable.
  This did not exercise naturally earned XP or the broken natural-end room.
