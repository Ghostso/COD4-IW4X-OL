# SPAS pump replay: captured cause

Passive C1 capture: `obj/spas-ui-capture-2.jsonl`, 1000 records. Weapon wire114,
`viewmodel_spas12_HB`, single hand. Reads capture both predicted and received
snapshot playerState; no process writes, hooks, or debugger breakpoints.

| Sample | State source | commandTime | Phase | Animation | Time | Delay |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 398 | predicted | 331820 | 7 (rechamber) | 4 | 443 | 425 |
| 399 | snapshot | 331820 | 7 (rechamber) | 4 | 443 | 425 |
| 407 | predicted | 332277 | 0 (ready) | 1024 (idle + restart) | 0 | 0 |
| 408 | snapshot | 332265 | 0 (ready) | 4 (old pump) | 0 | 0 |
| 408 | predicted | 332325 | 0 (ready) | 4 (old pump) | 0 | 0 |

At matched commandTime331820, pump phase and both timers agree. The client
finishes the pump and starts idle, then the received authoritative ready state
restores the pump animation. Inventory primary rechamber byte is zero in both
sample408 states. Subsequent captured ready states retain animation4.

## Native cause and correction

C1 `PM_Weapon_CheckForRechamber` at `418f40` clears the inventory latch when
the shorter bolt delay expires (`418fce`) and emits brass (`418fdc`). Its
separate no-latch path at `41911f..41913c` still checks state7 and both zero
timers, then calls `418f00`. That helper resets the animation to idle with the
correct restart toggle and sets ready state.

The retained primary assembly skipped directly to `PM_Weapon_560` whenever
the rechamber bitset was clear. Therefore it missed the animation-completion
path after the bolt delay had already cleared the latch. Later processing
could publish ready state while retaining pump animation4. The snapshot
publisher faithfully preserved that old animation; altering its duration
would not repair the authoritative producer.

`src/asmsource/_bg_weapons.asm` now routes the absent-latch branch through
`PM_Weapon_CoDOLRechamberFinished`: only native rechamber state6 with zero
weaponTime and weaponDelay goes to existing `PM_Weapon_590`, which performs
the idle-animation toggle and ready-state transition. All other cases retain
their original path. This reproduces C1's explicit no-latch completion branch.

Source inspected and changed; no worker build or tests performed. Post-fix
live capture remains necessary before claiming the reported replay is gone.

## Post-fix capture

Build `14A36F66C328F198DD0F98C124FA01B7AD31705509A90F7E36ACADF66E89E795`,
native PID91984, C1 PID74192. Rejoined Killhouse and fired class5 SPAS twice
(HUD8->7->6). `obj/spas-ui-postfix.jsonl` contains1000 passive samples.
Both predicted and received states return to animation0 after each pump;
neither contains a ready-state pump animation. First completion is predicted
commandTime166195 and received166148; second is predicted176231 and
received176196. This confirms the captured end-of-pump correction is removed
for these two shots. It does not establish all weapon timing or movement parity.
