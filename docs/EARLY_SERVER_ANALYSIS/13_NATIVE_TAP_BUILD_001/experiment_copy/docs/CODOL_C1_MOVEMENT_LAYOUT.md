# C1-native movement contract

This is the implementation contract for movement between the 1.1.1.13 C1
client and sh1x. C1 movement state is authoritative on both ends. Retained IW3
types and routines may be temporary implementation material, but their bit
numbers, structure offsets and state transitions are not protocol truth.

Evidence labels used below:

- **C1 static**: read directly from `C1.exe`, SHA-256
  `d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`.
- **C1 live**: client memory, packet capture, or current sh1x/C1 logs.
- **Cross-check**: IW4, T5/OpenBLOPS, or retained IW3 behavior. It establishes
  lineage or intent, never a C1 offset.
- **Open**: evidence is insufficient. Do not turn it into a constant.

## Architecture requirement

The target path is:

```text
C1 wire usercmd -> C1 usercmd -> C1 Pmove -> C1 playerState
                                      |
                                      +-> C1 snapshot fields -> C1 client
```

Do not make `usercmd_t` or retained `playerState_t` the canonical state and
translate their flags on every command/snapshot. A correct native design owns a
C1 command structure and a C1 movement/player-state structure (or a semantic
structure whose constants are C1 constants), runs C1 transitions, and writes
the measured C1 netfields directly. Legacy IW3 game code may receive an
explicit mirror at its boundary. That mirror must not feed back into C1 Pmove.

`CODOL_ToEngineUsercmd` remains a boundary mirror for retained game and weapon
code. The active movement owner consumes `codol_usercmd_t`, produces C1
`pm_flags` directly, and `CODOL_OverlayEngineMovement` publishes that word
without translating it through IW3 movement state.

## C1 usercmd memory and wire layout

`usercmd_s` is exactly `0x28` bytes. `pmove_t` contains the current command at
`pm+0x04`; current `buttons` is therefore `pm+0x08`. The old command starts at
`pm+0x2c`, and its buttons are at `pm+0x30`. `PM_CheckJump` proves this arithmetic
at `0x00409674/0x0040967e`. **C1 static.**

| Offset | Memory type | Wire representation | Meaning/evidence |
|---:|---:|---|---|
| `0x00` | `u32` | delta byte when `<256`, otherwise absolute `u32` | `serverTime`, writer `0x0059fa40` |
| `0x04` | `u32` | bit 0 separately; bits 1..29 as a 29-bit changed field | `buttons`, `0x0059fc75`, `0x0059fd12` |
| `0x08` | `i32` | low 16 bits, delta-key short | pitch angle |
| `0x0c` | `i32` | low 16 bits, delta-key short | yaw angle |
| `0x10` | `i32` | low 16 bits, delta-key short | roll angle |
| `0x14` | `u16` | 10 bits | weapon |
| `0x16` | `u16` | 10 bits | primary weapon for alternate mode |
| `0x18` | `u16` | 10 bits | offhand |
| `0x1a` | `i8` | not sent directly | forward; reconstructed from direction bit 0/1 as `+127/-127` |
| `0x1b` | `i8` | not sent directly | right; direction bit 2/3 as `+127/-127` |
| `0x1c` | `float` | `ANGLE2SHORT`, only with button `0x4` | melee-charge yaw |
| `0x20` | `u8` | 8 bits, only with button `0x4` | melee-charge distance |
| `0x21..23` | `u8[3]` | delta bytes, only with `0x20000` | selected location x/y/angle |
| `0x24..25` | `i8[2]` | delta bytes, only with `0x200000` | remote-control angles |

The full-form wire order of the 10-bit identifiers is weapon (`+0x14`),
offhand (`+0x18`), alternate-mode weapon (`+0x16`). **C1 static:**
`MSG_WriteDeltaUsercmdKey` `0x0059fa30`, with fields at
`0x0059fd74..0x0059fe88`. The three path tags are unchanged `7`, short `2`,
full `5`.

The delta key is:

```text
checksumFeed ^ messageAcknowledge ^ MSG_HashKey(
  serverCommands[reliableAcknowledge & 0xff], 32)
```

The general key was recovered live: using only `messageAcknowledge` decoded
70.27% of 29,494 packets; adding the command hash decoded 29,486/29,494
(99.97%), with only real weapon IDs 0/25/51. The hash sanitizes `%` and high
bytes to `'.'`, weights up to 32 bytes by `119+i`, then folds with `h>>10` and
`h>>20`. **C1 live.**

Packets carry six commands. At the observed ~87 commands/s and ~30 packets/s,
about three are new and three are the `cl_packetdup` overlap. Execute only
commands with `cmd.serverTime > ps.commandTime`, in increasing time order.
Repeated commands are redundancy, not additional simulation time. Six-deep
overlap and one-command delivery produced the same endpoint within `1e-9`
units in alpha0022's replay evidence.

### Button bits

These are C1 values, recovered from `CL_CreateCmd 0x00490d50`,
`CL_CmdButtons 0x0048fb60`, the command/handler table at `0x00491f60`, and
Pmove consumers.

| Bit | C1 meaning | Principal evidence |
|---:|---|---|
| `0x00000001` | fire | producer `0x0049044e`; dedicated wire bit |
| `0x00000002` | sprint | `0x0048fc94/ba`; `PM_UpdateSprint` |
| `0x00000004` | melee | `0x004904dc`; gates charge payload |
| `0x00000008` | use | `0x004904f6` |
| `0x00000010` | reload | `0x00490510`, Pmove `0x00409b03` |
| `0x00000020` | use/reload | `0x0049052a` |
| `0x00000040/80` | default-command lean state; normal C1 command producer does not set them | Pmove clears with mask `0xfffffb3f` at `0x0041605b` |
| `0x00000100` | desired prone level | producer `0x00490544`, stance producer `0x0048fbc2` |
| `0x00000200` | desired crouch level | `0x00490561`, `0x0048fbdc` |
| `0x00000400` | jump | `0x0049057e`; edge consumer `0x00409674/7e` |
| `0x00000800` | ADS | `0x0048fc12`; Pmove `0x0041533f` |
| `0x00001000` | stance key held | set `0x0048fbcb`, cleared `0x0048fb3a` |
| `0x00002000` | hold breath | `0x00490468` |
| `0x00004000` | frag | `0x00490485` |
| `0x00008000` | smoke/secondary | `0x004904a2` |
| `0x00010000` | tactical | `0x004904bf` |
| `0x00020000` | selected-location payload | `0x00490ae4`, wire gate `0x0059fe8b` |
| `0x00040000` | second location-select mode | `0x00490b10` |
| `0x00080000` | action slot 3/call-in | `0x00481850` |
| `0x00100000` | ADS throw | `0x0049059b`; this is not normal ADS |
| `0x00200000` | remote control | alternate builder `0x00490b40`, wire gate `0x0059fedc` |
| `0x00400000` | fourth offhand slot | `0x00480fb6` |
| `0x00800000` | dolphin dive request | `0x0048fb21`; `PM_CanDive 0x00408ee7` |
| `0x01000000` | marker slot | `0x004905b8` |
| `0x10000000` | input lock/UI catcher | `0x004905e1`, `0x00490753` |
| `0x20000000` | ADS toggle latch | `0x0048fc27` |

Bits `0x40000000` and `0x80000000` cannot be transmitted by this writer: the
upper field is only 29 bits after shifting right once.

C1 filters input inside Pmove. Remote mode keeps `buttons & 0x80300` and zeros
movement (`0x00416c4c..55`). Input lock keeps `buttons & 0x10001b02` and zeros
movement (`0x0041608d..9c`). Raw usercmds must remain available for scripts and
remote/equipment consumers; filter the command copy Pmove executes.

### First-command delta baseline: still needs a C1-native proof

This point must not be settled from retained IW3 alone.

- `CL_CreateCmd 0x00490d50` zeroes each new C1 command, then fills it. This is
  the command producer, not proof of the network writer's `from` pointer.
- `MSG_WriteDeltaUsercmdKey 0x0059fa30` is readable, but C1
  `CL_WritePacket 0x004910b0` jumps into virtualized `.tvm0`. Static direct-call
  xrefs therefore do not reveal its first-command setup.
- alpha0022 decoded 29,529 blocks with a zero first base and observed an
  absolute first `serverTime`. The absolute time proves the time baseline is
  far away/zero. It does not prove unchanged fields are zero: path A/B tags
  validate grammar while unchanged fields inherit whatever base the decoder
  supplied.
- Current sh1x live A/B evidence on 2026-09-10 found held crouch alternating
  between decoded `0x200` and `0` with a zero base; seeding from current state
  stopped that alternation. This is evidence for a state-derived first base,
  though the existing builder derives it through retained IW3 fields.
- T5/OpenBLOPS has `MSG_SetDefaultUserCmd` and builds stance, lean, ADS,
  sprint, angles, weapon and offhand from playerState. This supports the
  behavior family, but T5's `usercmd_s` is `0x34`, not C1's `0x28`.

Until the virtualized C1 call is observed dynamically, keep the successful
state-derived baseline but build it from canonical C1 state. Required C1
values are prone `0x100`, crouch `0x200`, ADS `0x800`, sprint `0x2`, C1 weapon
IDs, and C1 view/delta angles. Never use `0x100000` as ADS; that is ADS-throw.
Never test an IW3 sprint bit to infer C1 sprint; canonical C1 `PMF_SPRINTING`
is `0x4000`.

The decisive probe is read-only tracing of the two pointer arguments passed to
`0x0059fa30` for command 0, plus the 0x28 bytes at `from`. Capture stand,
crouch, prone, ADS, sprint, and a weapon switch. This resolves the baseline
without interpreting retained IW3 code.

## C1 playerState movement fields

The C1 player-state netfield table is at `.rdata:0x00c38ca8`; the repository's
verbatim ordered copy is `src/codol/snapshot/codol_player_fields.inc`. Offsets
below identify C1 state. They are not offsets into retained IW3 structures.

| C1 offset | Encoding | Meaning | C1 evidence |
|---:|---:|---|---|
| `0x000` | `-97` | commandTime | prediction gates `0x0045f59d/a5` |
| `0x004` | 8 | pm_type | comparisons in `PM_UpdateStance` |
| `0x008` | `-16` | pm_time | landing/stance timer |
| `0x00c` | 31 | pm_flags | all movement consumers |
| `0x018` | 8, hint 3 | bobCycle | Pmove/footsteps |
| `0x01c..24` | float, hint 3 | origin | Pmove and snapshots |
| `0x028..30` | float, hint 3 | velocity | Pmove and snapshots |
| `0x090` | 16 | gravity | dive launch and normal gravity |
| `0x094` | float | lean | `PM_CmdScale 0x004101a5` |
| `0x098` | 16 | speed | command scale |
| `0x09c..a4` | angle codec | delta angles | view prediction |
| `0x0a8` | 11 | groundEntityNum | world 2046, none 2047 |
| `0x0ac..b4` | float | ladder normal | `PM_CheckLadder 0x00415435/47/52` |
| `0x0b8` | 32 | jumpTime | jump/dive phase |
| `0x0bc` | float | jumpOriginZ | dive apex |
| `0x0e8` | signed 8, hint 3 | movementDir | animation/movement |
| `0x0ec` | engine flags | stance animation bits | crouch `4`, prone `8` |
| `0x140` | 8 | clientNum | trace handler/index |
| `0x14c..154` | angles | viewangles | view/Pmove; prediction-preserved when ROV=0 |
| `0x158` | signed 8 | viewHeightTarget | 60/40/11, dead 8, last stand 22 |
| `0x15c` | float | viewHeightCurrent | camera and stance scale |
| `0x160` | 32 | viewHeightLerpTime | start time |
| `0x164` | signed 8 | viewHeightLerpTarget | prior/curve target selector |
| `0x168` | 1, always-change hint | viewHeightLerpDown | curve direction |
| `0x1ec` | 11 | linkWeaponEnt | 2047 for normal first-person camera |
| `0x234` | `-97` | diveEndTime | 100 ms post-dive stance lock |
| `0x238` | 1, always-change hint | sprintButtonUpRequired | sprint release latch |
| `0x23c` | 1, always-change hint | sprintDelay/exhausted | sprint recharge gate |
| `0x240` | `-97` | lastSprintStart | sprint clock |
| `0x244` | `-97` | lastSprintEnd | sprint clock; dive must match cmd time |
| `0x248` | 16 | sprintStartMaxLength | stamina allowance |
| `0x254` | generic float | moveSpeedScaleMultiplier | final command-scale multiplier |
| `0x258` | float | mantle yaw | mantle state |
| `0x25c` | 32 | mantle timer ms | mantle progress/termination |
| `0x260` | 4 | mantle transition index | animation/root-motion table |
| `0x264` | 7 | mantle flags | checked/done/over/script request |

T5/OpenBLOPS independently has the same view-height trio and transition
formula, but at offsets `0x194/0x198/0x19c` (`msg_mp.cpp` and
`bg_pmove.cpp`). The different offsets are direct proof that matching names do
not license layout copying.

## Stance and view height

C1 `PM_UpdateStance` begins at `0x00412560`. Desired stance is level-based on
every command:

```text
buttons & 0x100 -> prone
else buttons & 0x200 -> crouch
else -> stand
```

The client owns the input latch and re-emits the selected level every command.
Server Pmove must not add an edge-triggered stance latch. C1 state is
`pm_flags & 3`: stand `0`, prone `1`, crouch `2`. The tail at
`0x00412efd..0x00413141` selects target height and rebuilds both hull and these
bits. Normal heights are stand `60`, crouch `40`, prone `11`; hull maxima are
70, 50, 30 respectively. Spectator pm_type 5 uses height 0; dead pm_type 8 uses
8; last stand uses 22.

The three high stance bits are deny flags, not current stance:

```text
0x00800000 deny stand
0x01000000 deny crouch
0x02000000 deny prone
```

All three is fatal error `93` at `0x00412897`; deny-stand plus deny-crouch is
fatal in the linked path (`92`, `0x00412e5f`). Normal unrestricted play keeps
all three clear.

View-height transitions require all five fields `+0x158..+0x168`. Sending only
current/target, or omitting the lerp start/direction because their field index
is late, restarts the client curve after each snapshot. `PM_GetMoveScale`
reads the trio at `0x0040ffc6..0x0040ffe9`; `PM_UpdateViewheight` starts and
finishes the curve at `0x00411d80`. Snapshot deltas must explicitly publish
zero when a transition ends.

Normal camera state also requires `linkWeaponEnt +0x1ec = 2047`.
`CG_OffsetFirstPersonView 0x004711aa` compares it to `0x7ff`; when unequal it
skips adding `viewHeightCurrent` at `0x004711ec`, producing the camera-at-feet
symptom.

## Sprint

C1 `PM_UpdateSprint` starts at `0x0040f8f0`.

- `BUTTON_SPRINT` is `0x2`.
- `PMF_SPRINTING` is C1 `0x4000`; set at `0x0040f73b`, cleared at
  `0x0040f783/0x0040f939`.
- Start records `lastSprintStart +0x240` and maximum allowance `+0x248`.
- End records `lastSprintEnd +0x244`, clears `+0x23c`, clears the sprint flag,
  and sets `sprintButtonUpRequired +0x238` when the button remains held
  (`0x0040f770..9a`).
- Starting and continuing use distinct input/state veto masks
  (`0x1cc35` at `0x0040f7b1`, `0x1cf35` at `0x0040f822`).
- `PM_CmdScale 0x004101c7` directly consumes C1 `PMF_SPRINTING` and applies
  the sprint multiplier. Live C1 movement measured about 285 u/s from 190,
  matching 1.5.

All five sprint-state words and `pm_flags` are shared prediction state. They
must come from the same C1 Pmove step as `commandTime`, origin, and velocity.

## Dolphin dive

C1 dive is a Pmove state machine, not an IW3 action translated at the edge.

1. `PM_CanDive 0x00408eb0` requires the master dvar, a surface that permits
   dive, `lastSprintEnd == cmd.serverTime`, `buttons & 0x00800000`, horizontal
   speed squared above `3.16^2`, more than 1500 ms since `diveEndTime`, and
   more than 250 ms since `lastSprintStart`.
2. `PM_DiveStart 0x00408a90` sets ground to 2047, `jumpTime=now`, vertical
   speed `sqrt(gravity*39)*1.5`, C1 `PMF_DIVETOPRONE=0x40000000`, clears
   `0x2180`, sets `pm_time=0`, and stores `jumpOriginZ=origin.z`. Horizontal
   sprint velocity is retained; no forward impulse is added.
3. The apex arm `0x00408df0` starts above `jumpOriginZ+39`; it zeroes upward
   speed during the 400 ms apex interval and clamps it nonpositive afterward.
4. `PM_CheckDive 0x00408f30` first turns ground contact into
   `jumpTime=-now` and event 186 (`EV_DTP_LAND`, `0x00408f92/0x00409022`). Once
   horizontal speed falls to `<=3.16`, it clears bit 30, zeros velocity and
   jumpTime, writes `diveEndTime=now`, and clears sprint release state
   (`0x00408c65..0x00408c99`).
5. `PM_UpdateStance 0x004127ba/c8` forces prone while bit 30 is set and for
   100 ms after `diveEndTime`: rewrite current buttons to prone, zero movement,
   target height 11, and issue the force-prone event.

The server and client must run this identical transition from the identical
command. A server-only sidecar time used to approximate `+0x234` will drift;
the canonical C1 playerState field must be updated and snapshotted.

## Mantle and ladder transition

C1 Pmove ordering is measured directly in `PmoveSingle 0x00415ff0`:

```text
top of step: mantleFlags &= ~(0x08 | 0x10)       0x0041647a
if not already mantling:
    common pre-step                                      0x004167fc
    PM_UpdateSprint                                      0x00416805
    PM_CheckLadder                                       0x0041680c
    PM_UpdateStance                                      0x00416817
    PM_GroundTrace                                       0x00416824
PM_CheckMantle                                           0x0041682b
if PMF_MANTLE:
    if PMF_LADDER: clear 0x8, set PMF_LADDER_FALL 0x1000 0x00416837..43
    groundEntityNum = 2047
    pml.walking = pml.groundPlane = 0                    0x00416846..56
    common pre-step
    PM_UpdateSprint
    PM_CheckLadder
    PM_UpdateStance
    PM_MantleMove                                        0x00416881
    post-step and return
else:
    continue normal walk/air movement
```

Thus a mantle entered from a ladder atomically leaves C1 ladder bit `0x8` and
sets C1 ladder-fall bit `0x1000` before mantle motion. Feeding retained IW3
ladder/jump flags back through a mapping can reverse this transition and is a
credible cause of the live tower replay/stick.

`PM_CheckMantle 0x0040a740` requires a forward trace against
`CONTENTS_MANTLE=0x01000000`, then ledge checks at 60/40/20. Jump is
`0x400`; script-forced mantle uses mantle flag `0x20`. Start
`0x00409ff0` writes yaw, zero timer, transition index and flags, then sets
`PMF_MANTLE=0x4` at `0x0040a0cd`. Move `0x0040a7a0` advances `+0x25c` by
exact `pml.msec`, updates origin by animation root-motion delta, and clears
`PMF_MANTLE` only when the total duration is reached (`0x0040a933/3b`).

The four mantle fields and C1 `pm_flags`, origin, velocity, ground state,
stance and sprint fields must be one coherent state. The live 2026-09-10 tower
run reached retained ladder state `0x8` with roughly +95 Z after mantle and
stuck. Treat this as evidence of a mixed-state boundary until a C1-native
Pmove owns the mantle-to-ladder transition above.

## Command and snapshot clock contract

- `CL_FinishMove 0x0049069b` stamps commands from `cl.serverTime`.
- `CG_PredictPlayerState 0x0045f3a0` replays commands only when
  `cmd.serverTime >= ps.commandTime` and not beyond the latest command
  (`0x0045f59d/a5`). Pmove runs a command completely; C1's internal maximum
  substep is 66 ms.
- `CL_AdjustTimeDelta 0x00488380` targets newest snapshot serverTime minus one
  snapshot interval minus 16 ms (`0x004883f8..0x0048840a`). C1 therefore does
  not use stock IW3 timing unchanged.
- The movement trailer is three predicted-origin floats plus a time. Frame
  order is `CG_PredictPlayerState`, save predicted origin/time, then create the
  next command (`0x0047871f`, `0x0047894d`, `0x00487380`, `0x00478fa6`). The
  trailer time equals the newest transmitted command time, while its origin is
  normally the result through the preceding command. Do not integrate the
  trailer as another command or compare it to the wrong history sample.
- A snapshot must publish `commandTime` and every movement field from the same
  completed C1 Pmove state. Snapshot serverTime may be newer; it must not be
  substituted for player `commandTime`.
- With `readOriginAndVelocity=0`, the C1 delta path preserves locally predicted
  origin/velocity and view angles. With it set, it accepts the server values.
  Use it for spawn/teleport or a proven correction, not as a periodic movement
  mechanism. Repeated corrections create visible replay.
- Preserve snapshot history by acknowledged message sequence. Delta against
  the frame the client acknowledged; do not confuse reliable-command sequence,
  usercmd `serverTime`, snapshot serverTime, and netchan packet sequence.

## Immediate implementation consequences

1. Create/finish canonical `codol_playerstate_t` and C1 Pmove ownership for
   stance, view-height, sprint, jump, ladder, mantle and dive.
2. Decode into `codol_usercmd_t` and execute it directly. Remove movement
   dependence on `CODOL_ToEngineUsercmd`; mirror to retained types only for
   legacy consumers after C1 simulation.
3. Serialize canonical C1 fields directly. Remove bit remapping from
   `CODOL_OverlayEngineMovement` as each producer moves to C1 state.
4. Keep stance level-based. Preserve full view-height lerp metadata and all
   sprint/mantle/dive clocks.
5. Fix the first-command baseline in the C1 domain. Current live evidence
   favors a state-derived base, but its exact C1 writer setup remains open.
6. For the current tower failure, compare one command on both sides across:
   C1 `pm_flags` `0x4/0x8/0x1000`, ground 2047, mantle timer/index/flags,
   origin/velocity, stance, sprint times, and snapshot `commandTime`.

## Sources

- Supplied `C1.exe` and addresses listed above.
- alpha0022: `docs/usercmd_wire.md`, `docs/usercmd_button_decode.md`,
  `docs/movement_stance_fix.md`, `docs/movement_fix.md`,
  `docs/camera_mantle.md`, `docs/mantle_mount.md`, `docs/usercmd_time.md`.
- Native measured table: `src/codol/snapshot/codol_player_fields.inc`.
- T5 cross-check: `D:/CoD/OpenBLOPS/Engine/Core/qcommon/msg_mp.h`,
  `msg_mp.cpp`; `D:/CoD/OpenBLOPS/Game/Shared/bgame/bg_pmove.cpp`.
