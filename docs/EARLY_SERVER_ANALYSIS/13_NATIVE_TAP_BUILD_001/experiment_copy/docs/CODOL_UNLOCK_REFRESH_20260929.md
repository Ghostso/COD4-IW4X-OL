# Same-process rank unlock refresh

Target client: `C1.exe` SHA-256
`086B2BCF109C8340A898606E5CAA2678242449452BCF62B2DDA22A6E37DDA91F`.
Addresses below are virtual addresses in that exact build.

## Observed failure

The lobby credited the local profile from level 3 to level 5 and returned
rank flags 1 through 5. Read-only C1 memory after that task-30 reply still
contained only 1 through 3, with its one-shot copy guard at `0x06C3D2FF`
already set. C1 did not copy the new task-30 flags into the live array.
The frontend lock dictionary is also cached, so the server-side repair needs
a same-process menu retest.

## Exact client and server path

- C1's `s` server-command case at `0x00469891` passes name/value pairs to
  `CG_SetClientDvarFromServer` at `0x00468B01`. For literal
  `cg_unlockFlagSet`, it calls `CG_SetUnlockFlagsFromString` at `0x00468900`.
  That function splits on `|`, parses each numeric token, ignores duplicates,
  and appends new IDs to the live array (maximum 1000 entries).
- Retained `PlayerCmd_SetClientDvar` emits a reliable `s` command with a
  quoted value. `SV_AddServerCommand` preserves distinct commands; C1's
  `CG_ExecuteNewServerCommands` at `0x0046A1A0` consumes them in sequence.
- Script rank IDs are zero-based while lobby-visible level and unlock-flag
  IDs are one-based. The mounted rank table has contiguous thresholds. On a
  promotion, `_rank.gsc::giveRankXP` now sends the complete `1|2|...|N`
  prefix after `syncXPStat()`, where `N` is the new level. A multi-rank jump
  therefore supplies every earned flag, and duplicate IDs are harmless.

## Verification and remaining boundary

The MP script resolver passed against 973 registered builtins and the live
Windows binary. The single server compiled the edited `_rank.gsc` on
`map_restart`, returned 12 Recruit bots to `CS_ACTIVE`, and logged no script
error. The Windows cross build deployed later has SHA-256
`8C70370B08F0E7BEEE4150B3F89B6ED6250ACE6A3FF2F183F75C07E81FFF05B3`
and is the only server on UDP/17733.

There was no C1 process available for a rank promotion after this change.
Next test: earn a level in one C1 process; record `s cg_unlockFlagSet`, the
live C1 flag array, final XP sync, match exit, and reopened class and
customization menus. C1 destroys and recreates its frontend movie on match
exit, but visible unlock behavior has not yet been observed on this build.
