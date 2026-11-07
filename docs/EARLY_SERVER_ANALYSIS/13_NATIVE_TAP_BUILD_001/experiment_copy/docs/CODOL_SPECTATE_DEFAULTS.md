# setspectatedefaults reference and native integration requirements

Offline IW4 inspection, source only, 2026-09-09.

- Handler5df520 validates an entity with a player client. It directly reads
  vector argument0 into client337c at5df57a, then vector1 into3388 at5df58d.
  There is no argument-count guard or return value. First vector mutation occurs
  before reading the second; do not impose an atomic two-argument update.
- Consumer459e70 is the stop-following path. It clears spectator/follow fields,
  tests follow flag800 at459ea3, then calls4319a0(client,4).
- Helper4319a0 returns whether bit(1<<argument) is CLEAR in client31d0.
  When it returns nonzero,459ed7..459ef5 computes current player view origin
  and directions. When zero,459efa loads default position337c..3384 and calls
  AngleVectors-style4691a0 with default angles3388.
- Both branches join459f34, retaining a common collision-constrained camera
  placement path. Do not simply teleport to the default position or set the
  live view when the GSC setter runs.
- Retained src/g_cmds.c StopFollowing currently always calls
  G_GetPlayerViewOrigin/BG_GetPlayerViewDirection before its camera trace.
  Native sess.noSpectate is the permissions field to investigate via
  PlayerCmd_AllowSpectateTeam. IW4 permission bit4 must be mapped by team
  semantics, not copied into the IW3 bit positions.

Next: establish permission-bit meaning and native equivalent, C1 counterpart
where available, then implement storage/reset plus the setter and StopFollowing
branch. No placeholder method registered. Do not claim storing unused vectors
is method support. Worker checkpoint had no implementation; parent evidence
above comes from aligned handler5df520, consumer459e70 and helper4319a0.
Initial459e00 mid-function scan is not used as evidence of a function boundary.
