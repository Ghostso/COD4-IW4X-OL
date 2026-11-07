# Native damage-number candidate (2026-09-22)

Status: included in accepted AZ on parent `0d64246`; Factory and same-build
FFA passed. Current accounting: [AZ review](zm-scoreboard-accounting-20260923.md).
Includes published headless-wave and death-weighting fixes.
The first AW iteration adds neutral damage feedback and zombie-only weapon
location scaling, confirmed visible in play. The AY opt-in iteration (superseding unlaunched AX) adds blue
reward HUD and explicitly reconstructed orange selection. See
reconstructed-zm-score-feedback-20260923.md; its accounting is superseded by AZ.

## Exact-build evidence

IDA MCP instance `eeah`, settled at 35,783 functions; x86 out.exe SHA-256
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`.
The IDB and extracted native bytes remain local.

- `0x67406E..0x674112`: playerstate auxiliary T15 reads repeated present bit,
  slot5, sequence4, style4, amount12 and entity11, then a zero terminator.
  Thirty-two six-byte records start at playerstate `+0x3752`.
- `0x561776`: sequence zero is inactive. The following branch selects
  damageNumberTableZhunt/TD/default, looking up the transmitted style.
- `0x561D4E..0x561FD0`: fallback display handles styles 0 through 4;
  `0x561F15` selects RGB at `0xDA32C8` for styles 3/4, otherwise `0xDA3288`.
  Exact IDA data reads show white (1,1,1) and orange (1,0.51,0.16).
  Size and motion also differ by style. This proves client presentation,
  not whether the original server selected orange for lethal or critical hits.
- `0x6CBBF0` reads TD style-table columns into color/type/fontSize objects;
  that mode-specific consumer is not evidence of Factory reward criteria.

The original `C-2021-7-31[15-32-16]zm.demo` first 180 seconds decode exactly
through 1,669 snapshots. Deduplicating received per-slot record transitions gives
214 transitions: 109 style0, 74 style2 and 31 style3. These counts are not unique
kill counts or odds. Style0 is a demonstrated native damaging-hit presentation;
styles2/3 and reward correlation need actor-generation and event context.

The large containing render functions did not decompile through the current MCP
call. Findings above use bounded IDA disassembly/data reads, not a claimed full
renderer decompilation. A missing MCP py_eval backend was not used as evidence.

## Implementation boundary

Damage records belong to a separate per-world/client-life owner. SvPlayerState,
WorldClientState and native player/entity layouts remain unchanged. Committed
zombie weapon damage appends a neutral record; rejected commands, corpse hits,
ordinary multiplayer players and headless timer ticks do not create new records.
The displayed amount saturates at the native 12-bit maximum without changing
combat damage or battery. Battery rewards remain separate.

Successful endFrame copies records into the normal immutable snapshot history.
T15 compares with that same acknowledged frame used by the rest of playerstate.
It does not use the latest sent packet. Number-only updates bypass the empty
playerstate fast path. Disconnect, reset and spawn-life changes clear ownership.
The 1..15 sequence cycle avoids the client's inactive zero value; the exact
deleted server sequence producer is not recovered. Ring capacity is native.

## Verification and next test

Direct and penetrating entity bullets now opt into the weapon's native location
table only for authoritative zombie_actor damage views. Generic props preserve
their prior behavior. Range and penetration attenuation precede location scaling;
invalid scaling rejects the transaction. Focused production-path regressions
check26body/31head at1.2, and40body/48head after wall attenuation. These are
synthetic regression inputs, not a recovered original M4A1 server formula.
Seven integrated suites and Release compilation pass on this base.

Original Factory archival HUD decoding now identifies the blue Value popup:
x30/y-50, color0xD8FFA629, scale0.9->3 over100ms then200ms settling,
1000ms visibility and750ms fade. Label385 still needs localization verification.
In several samples blue60 accompanies raw battery+30 and blue80 accompanies+40;
the displayed reward must not blindly copy raw battery. No universal ratio or
complete kill classification has been established. Blue projection is not yet
implemented; earlier statements below about pending reward transport are historical.

Source regressions cover wire limits, sequence wrap, acknowledgement/loss,
immutable older state, recipient admission, actual damage transactions and a
number-only full-snapshot delta. Separate local Unicorn replay executes the
unchanged native T15 reader on production-writer output: first-hit 38 bits and
lost-intermediate-packet 75 bits both reproduce exact expected native stores.
Only the transport bit primitives are intercepted. This is protocol evidence,
not a visual game PASS.

Factory test: single body/head hits, short automatic bursts, misses and dead
bodies; check visible numbers correspond to damage, stop after firing and do
not replay on later frames. Confirm accepted audio, animation and death FX.
Native orange conditions and blue kill/reward transport remain a separate
research step before extending presentation rules.

## 中文摘要

使用原生 T15 伤害数字通道，独立保存每名玩家的环形记录，并随已确认快照
进行增量编码；不修改原生玩家布局。当前仅恢复普通伤害数字，不猜测橙色
暴击/致死条件，也不把伤害值当作电池奖励。客户端样式、协议与服务端
选择条件分别记录；实机 Factory 和同构建 FFA 仍待验证。
