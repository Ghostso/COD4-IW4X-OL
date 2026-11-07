# Intermittent splash delivery audit — 2026-09-15

## Current result

No causal fix established yet. C1 PID90404 was live but outside a match: commandTime=0. Inactive retained slots were not interpreted. Capture: obj/splash-delivery-audit/initial-inactive.json. No game inputs, process writes, builds, restarts, or tests performed.

The actual inherited script is alpha0022/vendor/iw4/maps/mp/gametypes/_hud_message.gsc. There is no scripts/codol/maps/mp/gametypes/_hud_message.gsc overlay in this checkout. Creating one before tracing the failure would duplicate the entire inherited file unnecessarily.

## Verified independent failure boundaries

1. Sound and presentation are independent. actionNotifyMessage issues ShowHudSplash, then playLocalSound. Successful sound does not prove the w command was admitted, received, or presented.
2. Native SV_AddServerCommand prints `CoDOL reliable ->` BEFORE bot exclusion, canNotReliable, pressure/non-active dropping. A log of w is not proof of queue admission. Splash uses type0, as the original C1 builtin does. At >=64 outstanding commands or non-CS_ACTIVE, existing sub_5310E0 prunes unsent type0 commands and rejects new type0. Changing only splash to mandatory delivery is not justified yet: it could play stale notifications and increase overflow pressure.
3. C1 CG_ShowSplash 469144..46919B returns BEFORE writing a slot when decoded global16F8068 state's +80260 equals1 and global6C267DC state's +7F4140 equals1 or2. The previous probe omitted this gate. Updated private probe.py captures it using guarded read-only access. This is a state predicate, not yet named semantically.
4. Accepted slot write is at cg+174384+16*slot. Record: row,startMilliseconds,durationMilliseconds,optionalNumber. Native comments incorrectly call argument3 duration; it is optionalNumber. Duration comes from client table column4 at4691F8. This old comment error does not itself change current wire behavior.
5. After slot write, C1 refuses menu open if global16FC2E0 bit0x10 is set or the dvar at16D44D4+12 is false (469298..4692AB). Menu name comes from client table column11 (4692B1), then5F5740 opens it. Receipt alone therefore does not prove display.
6. Original IW4 actionNotify explicitly preempts ordinary medals with killstreaks/challenges in slot0. actionNotifyMessage sends the replacement then notifies actionNotifyMessage0, ending the previous worker. The previous sound may have played while its slot is immediately overwritten. This is reference behavior, not proof of a newly introduced bug. No arbitrary duration extension or blanket queuing policy change made.

## Next evidence needed

Capture an active affected notification, correlate admitted reliable sequence/ack with C1 slot write and both early/menu gates, then inspect matching client/server splashTable row including columns0/4/11. Prior audit sampled rows only; whole-table equality remains unproved. If several commands reach one slot in one snapshot, correlate script preemption order rather than treating them as transport loss.

No gameplay sources edited. No full splash support claim. Parent owns build/deployment and ledger.

## Staged admission diagnostics

obj/splash-delivery-audit/admission.patch targets only src/sv_main.c. Numeric-only, developer-gated, eight events/client/second with omitted-event count; bots excluded. Captures admitted (after actual buffer write), rejected-disabled, rejected-inactive, rejected-pressure, pruned-unsent (later discarded after initial admission), and replaced-overflow. Reports slot/row/optionalNumber, sequence/sent/ack/state/server time. No command text, names, addresses, or secret values. Delivery/priority/duration semantics unchanged. Parent must review/apply/build; patch applicability checked, no runtime validation yet.

Note sequence is a queue coordinate, not immutable event ID: existing unsent compaction/replacement can move commands. Follow row/slot/number/time and subsequent prune records as well as sequence. Rate-limited captures with omitted>0 are incomplete evidence, explicitly not proof no drop occurred.

Writer chain source: CODOL_Scr_ShowHudSplash -> SV_GameSendServerCommand -> SV_SendServerCommand_IW -> SV_SendServerCommandString -> SV_AddServerCommand. C1 original builtin uses type0. Native row-missing rejection occurs before this queue and already emits Unable to find; no sound suppression or policy change proposed.

## Full live table comparison (new evidence)

Native PID94424, executable E8B36DB840557F063380423AD8A91B9DDEF84C4BB1CB9F6271D8FC3E8F0D7059, and C1 PID90404 were read through guarded ReadProcessMemory. All 919 rows ×12 columns match exactly, including NULL versus string cells. This rules out a current server/client splashTable mismatch, not historical mismatches on other builds. Files: server-table.json, client-table.json, table-differences.json in obj/splash-delivery-audit.

Server reader uses exact executable COFF _archives plus ASLR adjustment, verifies 160 bytes of CODOL_LoadEngineStringTable against relocated image, and follows the native cached table list. Loader disassembly establishes tables+31C, cache engine+20, cache next+30; archive next+350 agrees current structure and executable. One matching cached table found. Client reader verifies image path and asset lookup code4CB350/4CB540, walks original DB hash bucket/type37, then reads original eight-byte cells. The C1 asset can be inspected while not in a match; this comparison does not depend on stale playerState.

Medals rows2..24 including revenge13/firstblood17 use1.5 seconds and menu splash. No missing duration/menu names found for named rows0..205. C1 menu-enable dvar registration44C5AC uses literal numeric name585, default1; calling it an invented cg_* variable would be unsupported. Third player-state capture remains inactive, hence no failed-notification gate correlation.

## Active receipt and normal lifetime observed

Bounded read-only watcher completed alongside natural gameplay. Headshot row2 was admitted as native sequence222, server time100450, sent/ack216. C1 command100492 had slot0 row2/start4608642/duration1500/optional50. Early rejection false, UIFlags0, HUD gates enabled and splash-menu dvar enabled. At command101984 the start field became0, approximately the authored1.5-second lifetime later. No early replacement or delivery failure in this instance. This establishes receipt/lifetime, not a screenshot proof of icon/text visibility.

Earlier accepted rows67(uav),77(predator_missile),456(ch_predator_missile) had low pending-command counts. Capture active-state.json found latest456 in C1 slot0, also proving receipt. No pruned/rejected record was found in the sampled admission tail. Evidence files live-watch.jsonl and admission-live.txt. Intermittent failure still requires an affected occurrence; no unsupported gameplay fix applied.

## Actual C1 widget consumers and loaded menu

Captured live menu asset type26 named splash at187C6D4 (PID90404), using original asset hash lookup plus the menu/item/statement layout verified by C1 load routines4C12B0/4C0C90/4C0260 (also documented by native replay parser). File live-menu.json contains all five widgets and event trees; read-menu.py reads only. This is the actual loaded C1 menu, not copied IW4 UI source.

- Main splash_title and splash_description have no explicit visible expression. Each alpha expression clamps `(milliseconds - localvarint(timer_mark) - 150) / 150` to0..1: first150ms intentionally transparent, next150ms fade-in.
- onOpen sets timer_mark to milliseconds, menu scale/alpha lerp in50ms, and closes challenge, defcon, killstreak_pickup, killstreak, perk_challenge, promotion_weapon, killstreak_minisplash, daily_challenge, weekly_challenge, playercard_splash, promotion. Closing another reward menu is authored client behavior.
- splash_icon visible expression is only splashhasicon(0); material expression getsplashmaterial(0). Headshot/revenge/doublekill/firstblood/semtex rows carry real hud_medals_* column3 names, so table data satisfies this predicate.
- Two bonus widgets are separately gated by ui_splash_bonus_title_vis and use ui_splash_bonus_title. These do not gate the main title/description/icon. No proposal to enable them indiscriminately.
- C1 expression opcode150 dispatches5E3370: when UIinitialized16FC2DA is false return empty; otherwise look up col1, localize via5F49E0, substitute slot.optionalNumber via5F4B40. Null format result becomes empty string. Description opcode151->5E3450 analogous col2 with special distance conversion for two named descriptions. optionalNumber does not choose visibility or duration.
- Opcode152->5E3580 returns column3 material string. Opcode153->5E3640 returns whether column3's first byte is positive. Both have UIinitialized guard. Neither resolves a server material configstring or script hudelem. Full disassembly widget-consumers.txt.

This narrows an affected occurrence to slot/menu lifecycle, localization/material availability, or upstream delivery; merely adding native hudelems or forcing HUD icon overrides would implement the wrong path. The observed headshot passed delivery/timing/UIinitialized; visual success was not independently captured. No field mismatch or required gameplay patch established in this pass.

## Firstblood/card reciprocal-closure hypothesis checked

Parent identified firstblood slot0 row17 and callout_firstblood slot1 row170 in one server frame57500, sequences70/74. Live C1 playercard_splash event tree was decoded independently (live-playercard-menu.json): onOpen only closes announcer_line and conditionally slides in under !ui_hide_playercards. It does not close splash. Therefore reverse closure cannot explain the row17→row170 sequence.

Generic native menu-open6014D0 calls5F9800 on earlier stack menus; that function clears focus bit2, preserving visible bit4. It does not implicitly close splash. This candidate does not justify replacing original independent slot queues with a global queue. Explicit C1 splash/killstreak/challenge onOpen closure remains directional and can affect an earlier playercard, not the opposite order seen here.

Added private probe-menus.py to capture actual UI stack menu names and dynamic flags together with splash slots/gates. Latest invocation found client outside match again, so no retained stack was interpreted. No indefinite polling or user input mutation. Still no supported delivery-policy fix for the reported missing medal.

## 2026-09-15: same-slot preemption presentation fix staged

User clarified that failures occur with several notifications from one kill and
later notifications more often appear. The inherited IW4 actionNotify explicitly
starts killstreak/challenge over an active ordinary splash, then kills the older
worker. Actual C1 main medal text alpha is zero for its first 150 ms. Therefore a
later priority notification inside that window can erase the first notification
before its text ever becomes visible, while the first sound already played. This
is a concrete mechanism matching the reported pattern; the failed visual has not
been captured frame-by-frame. Firstblood slot 0 plus playercard slot 1 alone does
not demonstrate this mechanism (reciprocal menu close was excluded above).

Staged files: obj/splash-delivery-audit/queue-stage/_hud_message.gsc and queue.patch.
The full file overlays the existing inherited IW4 script; the Python vendor file
and live native overlay were not edited by this worker.

Changes:
- Reserve each slot synchronously before launching its notification worker.
- Finish the active notification before dispatching another for that slot.
- Preserve priority for pending challenge/killstreak entries, FIFO within that
  priority class. Do not remove previously earned killstreak entries.
- Use the complete client splashTable column 4 duration, replacing duration-.05.
- Keep legacy anonymous HUD notices in the same queue and preserve sound at the
  actual dispatch, not at queue insertion.
- Reset cancels both kinds of waiting workers before clearing owners, preventing
  an old completion from clearing a new owner. Pending entries resume in a fresh
  thread after wait(0), so the previous resetOnCancel watcher can return first.
- Keep existing active-notification death policy and disconnect cancellation.
  Preserve rank/challenge postgame conversion; release ownership on that path.

This is an intentional non-preemptive presentation policy for C1, not a claim
that the original C1 server used this queue. No invented duration or mandatory
menu override. Cross-slot menu conflicts and rendering gates remain separate.
Source inspection completed; parent review/build/live gameplay confirmation pending.
No worker tests, build, process mutation, or restart performed.
