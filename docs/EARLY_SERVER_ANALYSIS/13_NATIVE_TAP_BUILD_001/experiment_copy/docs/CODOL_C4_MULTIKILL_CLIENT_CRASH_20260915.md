# C1 crash after C4 triple kill, 2026-09-15 22:31:27

Status: WRITTEN, objects BUILT (gcc -m32, both touched files compile clean);
NOT LIVE (server PID 6648 still runs the old build).

## Crash site (client)

`LOGF1D0.tmp` / `DMPF1E1.tmp` (C1.exe 1.1.1.13, map mp_killhouse_sh, war, bots):

- Exception c0000005 at `0x00aea51c` (CRT `strlen`), read of address 1.
  EAX=0 ECX=1 ESI=1 EDI=0x016ec978.
- Stack: `0xaea51c strlen <- 0x621f9c (sscanf "%f %f %f %f" fmt 0xc6f360)
  <- 0x43e214 (dvar->color conversion) <- 0x488a99 (HUD draw using the
  team colour of clientInfo[n], `imul 0xb50`, team read at +0x35c0)
  <- 0x497960 (CG draw) <- 0x599f4e (frame loop) <- 0x631505 <- 0xadfaa7`.
- Minidump stack slot 0x14fba0 (saved ESI of the 0x43e1f0 frame) = **7**:
  the colour-dvar array at `0x02373000` has entries 0..6; index 7 reaches a
  boolean dvar (value 1) that `0x43e208` passes as a string -> `strlen(1)`.
- This is byte-for-byte the "C1 team-color crash" of
  `docs/CODOL_LIVE_CRASHES_20260911.md` (DMP9B39): an **invalid decoded team
  7 = baseline team 6 XOR 1** for one client. It is NOT the 14:13 crash
  (LOGBD5D: `0x0060ea8e`, different stack), and it is not the killfeed,
  splash, configstring or ragdoll code. The client itself reported the same
  frames: `clientCommand: Nucleur : 718 : disconnect EXE_CRASH
  62c530,aea51c,86f7201,621f9c,43e214,488a99,497960,599f4e,631505,adfaa7`.

## Server side (bin/home/main/qconsole.log 4870..4936, games_mp.log 21085..21087)

games_mp: `8:35 K;...;Training 1|2|4;...;Nucleur;c4_mp;159;MOD_GRENADE_SPLASH`
(server start 22:22:48 + 8:35 = 22:31:23). Reliable traffic to Nucleur for
the three kills was ordinary and small: `L 1 8 / q 7 / C 1300 / p 24`,
`L 2 8 / q 7 / C 1400 / p 24`, `L 4 8 / q 7 / C 1500 / p 24 / d 5 1500`,
then later `w 0 15 75` (splash row 15) and the broadcast `L 0 5 / w 1 163 0
/ p 29`. No command exceeded the per-command size, no unterminated
argument, no `d <cs>` weapon registration, no `giveweapon dogs_mp`, no dogs
splash (dogs was only *selected*, line 4075; the earn path never ran).
Reliable window: sequence 367 vs ack 363, far below the 64-entry ring.

The causal lines, immediately after the third kill:

```
^2CoDOL frame rejected for client 0: player or HUD conversion (CODOL_OverlayEnginePrimaryWeapon(&fields,ps) [weaponstate 20 weapAnim 0x1b weapon 94 offhand 10 pm_type 0 pm_flags 0x0])
^3Warning: WARNING: msg overflowed for Nucleur, trying to recover (no native frame for sequence 2544 (ready 1, ready sequence 2544, builder: player or HUD conversion); cursize 5 of 131072)
^2CoDOL snapshot clock: client 0 seq 2551 ack 2544 delta -1 gap 2552 ...
```

1. After the C4 detonation the retained weapon machine sits in weaponstate
   20 (offhand end) with weapAnim 27 (the detonation animation left in
   place). `CODOL_OverlayEngineOffhandPhase` only accepted animation 20 in
   state 20 and returned 0, so `CODOL_BuildGameplayFrame` rejected the
   entire frame 2544.
2. `SV_EndClientSnapshot` sent the overflow-recovery message (reliable
   commands only, no snapshot) as sequence 2544. Q3/C1 `CL_WritePacket`
   then reports `deltaMessage = -1` because `serverMessageSequence !=
   snap.messageNum`.
3. `CODOL_PrepareServerSnapshot` with acknowledged 0 found no ack base but
   had a pinned baseline, so it encoded 2545.. as **deltaNum 0 / flag 0
   against the pinned baseline** (the 09-11 "noDeltaSnapshot" branch).
   C1 (`0x49d9ce`) decodes such a frame against its saved copy at
   `0x06d33710`, which it refreshes **only on flag 8** (`0x49dd7e`). The
   two copies did not agree -> client team decoded as 7 -> HUD team colour
   -> `strlen(1)`. The client never acked past 2544 (crashed while drawing
   the first post-recovery frame), matching the stuck `ack 2544`.

So: yes, a server message caused it. Not a reliable command, but the
non-delta snapshot the server sent after rejecting frame 2544.

## Fix (WRITTEN, BUILT)

- `src/codol/snapshot/codol_engine_state.c` `CODOL_OverlayEngineOffhandPhase`
  case 20: accept animation 27 and publish C1 detonation animation 32
  (20 -> 22 unchanged). Removes the trigger.
- `src/codol/snapshot/codol_sv_snapshot.c` `CODOL_PrepareServerSnapshot`:
  `baseline_frame = flags&8 || latest==0 || !ack_base`. Any non-delta
  request is now answered with a flag-8 frame (null base, rov 1) that C1
  copies into its saved baseline; the pinned-baseline/flag-0 branch is no
  longer reachable. Removes the crash for every future overflow recovery.

Both compiled individually with `gcc -m32 -msse2 -mfpmath=sse -Wall
-std=gnu11 -DCODOL_SERVER -Isrc -Isrc/codol/<areas>`; no errors, only the
pre-existing misleading-indentation warning at the detonate case.

## Reproduce / confirm on next launch

1. Rebuild and relaunch; join killhouse with bots, plant C4, kill with it.
2. qconsole.log must NOT show `frame rejected ... weaponstate 20 weapAnim
   0x1b` nor `msg overflowed for <name>`.
3. Force the recovery path deliberately (e.g. any other frame rejection or
   `cl_nodelta 1` on the client) and confirm the following `snapshot clock`
   line shows `delta -1` with `flags 0x8` set and the client keeps acking
   (ack advances past that sequence) with no EXE_CRASH disconnect.
