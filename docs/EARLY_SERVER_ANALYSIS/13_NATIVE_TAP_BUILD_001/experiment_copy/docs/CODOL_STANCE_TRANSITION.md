# Player stance transition fields

The native movement adapter now publishes `viewHeightLerpTime`,
`viewHeightLerpTarget`, and `viewHeightLerpDown`. Sending current and target eye
height without these fields omitted the transition metadata used by client
stance-speed interpolation. The composed player-state adapter already calls
the movement adapter, so these fields no longer need a separate seed producer.

Evidence from C1.exe, SHA256
`d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`:

| CoDOL offset | Native member | Consumer evidence |
| --- | --- | --- |
| `0x160` | `viewHeightLerpTime` | `0x40ffc6` reads the start; `0x40ffe4..0x40ffe9` subtracts it from the current command time. |
| `0x164` | `viewHeightLerpTarget` | `0x40ffd2` selects the target-height-40 transition. |
| `0x168` | `viewHeightLerpDown` | `0x40ffdb` selects the upward transition when the flag is zero. |

These instructions belong to `PM_GetMoveScale` at `0x40ff70`, also documented in
alpha0022's `docs/ERRORS.md`. The retained `_bg_pmove.asm` implementation of
`PM_CmdScaleForStance` performs the corresponding time subtraction and target/
direction checks at native offsets `0x11c`, `0x120`, and `0x124`.

The actual CoDOL netfield table gives these fields 32-bit, signed 8-bit, and
one-bit encodings respectively. The adapter preserves the start-time bit pattern,
rejects out-of-range targets and non-boolean directions, and commits the complete
movement overlay only on success. Zero transition fields explicitly clear prior
state; they are not omitted as optional updates.

The native adapter test covers crouching, reversal, completion, boundary values,
and unchanged output after invalid input. This verifies snapshot translation;
it does not establish complete IW3/CoDOL movement-physics parity or live C1 match
behavior. Complete frame seeds and the gameplay frame-builder call remain open.

Validation on 2026-09-08: the Linux build and full `test-codol` suite passed
(`/tmp/sh1x-stance-transition-linux.log`), followed by the forced Windows build
(`/tmp/sh1x-stance-transition-win32.log`). The sequential command exited zero.
No running client or lobby process was modified for the static analysis or tests.
