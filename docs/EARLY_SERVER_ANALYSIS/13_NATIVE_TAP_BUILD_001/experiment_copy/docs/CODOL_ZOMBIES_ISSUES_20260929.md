# Zombies issue ledger — 2026-09-29

This records the user's Prototype screenshots and reports, the current source
changes, and the proof boundary for the live 1.1.1.13 server. A static GSC
resolver result does not prove a C1 gameplay result.

| Issue | Current state | Evidence and next check |
| --- | --- | --- |
| Esc needs two presses to resume | Open; first exact-build client patch failed live, revised patch prepared | User's three screenshots show pause menu, then a menu-free cursor state, then gameplay. A read-only 50 Hz C1 trace during the failed patch showed `cl_paused` changes 1 to 0 while `sf_pausemenu_minimap` remains visible with `KEYCATCH_UI=0x10`; the next Esc removes it. The first patch ran only when the legacy menu later closed. The revised patch acts at `UI_KeyEvent` immediately after the pause movie closes; it is built but awaits a client exit and live retest. |
| Mystery box shows an unrelated cabinet instead of the reward gun | Diagnosed, not fixed | All 40 mounted box weapon definitions have world models. The final-roll diagnostic previously used developer-only `println` and was absent from production logs; it now uses `codolprintln` and awaits a safe script reload. Capture one roll and compare the logged weapon/model with the displayed entity before changing the model path. |
| Zombie attack appears instant-lethal or absent | Source changed, C1 unverified | Respawn republishes Zombies' native down-state ability; the combat animscript retries after a missed or abandoned swing. Test successive hits, down state and animation with a human client. |
| Extra yellow points at the right edge | Source corrected and reloaded; C1 retest pending | The persistent score hudelem was removed, but the T5 floating delta remained. The user's latest screenshot shows the native `+60` beside the purse and a separate yellow `10` at the right. The floating delta path is now removed from the script loaded by the current server. |
| Zombie enters default/T pose | Source revised and reloaded; C1 visual retest pending | Exact C1 animtree/zone assets showed `ai_zombie_idle_v1` is an additive clip, so it cannot pose a zombie alone in the stop or spawn state. Both now use mounted full-body `zombie_stationary_idle_v7`. Hit reactions now complete the non-additive `zombie` branch using `setFlaggedAnimKnobAll`; the live server logs the selected reaction at weight 1 and advancing time. The user's visual confirmation is pending. |
| Incorrect number of zombies per round | Rounds 1 and 2 server counts verified with a human client; later rounds open | The current Prototype session logged round 1 budget 6, spawned 6, and round 2 budget 8, spawned 8. Round 3 budget is 13 and is in progress. Check C1-visible kills and later rounds; a failsafe despawn is not a kill. |
| Power-up pickups appear outside the playable map | Source changed, C1 unverified | Kills during a zombie's outside entrance phase no longer roll or consume a drop. Test entrance kills and ordinary in-room drops. |
| Zombies stall at spawn or route into steep collision | Further source fix built and reloaded; C1 visual retest pending | Human rounds 1 and 2 showed actors stopped at `(-875,50,-1)` by the car, with another at `(-1188,914,13)`. The bounded actor step passed a controlled choke test. A later trace showed damage targeting the player while an entrance's `ignoreall` phase was active, replacing the scripted barrier goal and exhausting paths behind `clip_ai`. `CODOL_ActorSetEnemy` now rejects a non-null enemy during `ignoreall`; the full Windows build succeeded and the revised server is live. Other obstacles remain unverified. |
| Double Points pickup does not double score | Source corrected and reloaded; C1 test pending | Pickup already set and cleared `zombie_powerup_point_doubler_on` for 30 seconds, but `get_points_multiplier()` never read it. The scoring path now doubles the multiplier while the flag is set. The former `println` award diagnostic was compiled out at developer 0; a bounded production-log ledger is prepared for the next safe script reload. Verify an ordinary hit award while active. |
| Spawns ignore room zones | Initial selection verified on three maps; one human door transition verified | Added C1 `info_volume` brush spawning and a zone manager that reads map-authored volumes and spawner groups. Prototype found 3 groups and selected 17 start-room spawners rather than all 42; Training found 4 groups with 1 initial spawner; Asylum found 9 groups and enabled 6 spawners in `west2_downstairs_zone` when a temporary test client entered it. In a human Prototype match, opening the box-zone door enabled five additional spawners. Other doors and zones remain unverified. |
| Damaged barrier can be repaired but shows no prompt | User confirmed fixed in C1 | User confirmed the repair prompt now appears. The repair trigger is `trigger_radius`, which C1's cursor-hint scan ignores; the script forces the registered hint while touching a damaged barrier and clears it on exit or completion. |
| Solo down leaves player in revive pistol view | Controlled no-perk death verified; C1 and Quick Revive unverified | The starting life had been counted as a spare and the solo player waited 45 seconds before an automatic revive. The script now gives zero spare lives at start; a solo down without Quick Revive ends promptly, while purchased Quick Revive grants one timed self-revive. A temporary solo bot was dead within a second of a scripted down; C1 view and the perk path still need a human check. |
| Health does not appear to regenerate after zombie hits | Source changed; C1 unverified | Zombies never starts multiplayer's health-regeneration thread. A Zombies-only thread now restores health after a five-second damage-free period. Check health and damage overlay through multiple hits and respawns. |

The single live server was restarted only after `sh1x_status` reported zero
human players and the previous sole owner of UDP/17733 was stopped. It is
running Prototype Zombies on UDP/17733 with bounded-step actor physics, the
entrance-targeting guard and the updated Zombies scripts. The Windows
cross-build passed; the GSC resolver validated all 107 reachable Zombies
scripts against its 973 registered builtins; five resolver tests passed earlier
in the pass. A temporary bot previously ran round one, triggered the bounded
step at the reproduced choke, then was removed. The score and animation visual
changes await C1 confirmation. The live startup logs for Prototype, Training
and Asylum had no script runtime error after the zone repair. The Training and
Asylum checks each used one server process at a time; the temporary Asylum test
client was removed before returning the sole server to Prototype.
