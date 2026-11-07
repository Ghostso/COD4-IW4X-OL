# Native C1 movement integration

## Decision

The CoDOL server must run one movement state model:

```text
C1 usercmd -> native C1 ClientThink/Pmove -> native C1 playerState
           -> native C1 entityState -> C1 snapshot serializer
```

The current playing path is a round trip through IW3:

```text
C1 usercmd
  -> CODOL_ToEngineUsercmd (lossy C1-to-IW3 conversion)
  -> retained IW3 usercmd_t / ClientThink_real / Pmove
  -> retained IW3 playerState_t
  -> CODOL_OverlayEngineMovement and other overlays
  -> C1 player-state fields
```

That round trip cannot produce prediction parity. A matching flag number in two
games is insufficient: each movement function reads a set of fields, dvars,
weapon properties, traces and prior-frame state. The server must stop invoking
retained IW3 `Pmove` for a C1 client. Patching individual stance, dive or mantle
branches inside it leaves two state machines coupled together.

The live tower case is direct evidence. After the attempted mantle, retained
movement entered IW3 ladder state (`pm_flags 0x8`) and advanced about `+95 Z`;
the C1 client remained stuck in its mantle. A native C1 path must decide mantle
and ladder state before either result is published. Script notifications,
blockage entities and player linking remain post-move server work; they do not
require IW3 movement.

## Current flow and replacement points

| Stage | Current implementation | Problem | Native C1 replacement |
| --- | --- | --- | --- |
| Packet decode | `SV_UserMove` in `src/sv_client.c`; `CODOL_ReadUsermoveMSGFrom` | C1 decoding is correct, but its first-command default is rebuilt from IW3 `playerState_t` | Build the default from the authoritative C1 state and retain each decoded `codol_usercmd_t` unchanged |
| Accepted command | `CODOL_ToEngineUsercmd`; `client_t::lastUsercmd` | Masks C1 buttons, reduces movement direction to IW3 axis bytes, maps 10-bit weapon IDs into the 128-entry IW3 registry, drops alternate weapon and remote fields | Add `lastC1Usercmd` and `oldC1Usercmd` to CoDOL client storage; `SV_UserMove` accepts and dispatches those directly |
| Game dispatch | `SV_ClientThink` -> `G_SetLastServerTime` -> `ClientThink` in `src/g_active.cpp` | `ClientThink` copies the converted IW3 command through `SV_GetUsercmd` | Add `SV_GetC1Usercmd` and call `CODOL_ClientThink(clientNum, &c1cmd)` for CoDOL connections |
| Movement | retained `ClientThink_real` and `Pmove` in `src/asmsource/_g_active_mp.asm` / `_bg_pmove.asm` | IW3 owns command time, stance, hull, ladder, mantle, ground, view height and predicted events | Implement `CODOL_ClientThinkReal` and the complete native C1 pmove call graph in `src/codol/player/` |
| Weapon input | retained `PM_Weapon` plus `CODOL_WeaponStateUpdate` sidecar | Primary hand still runs the IW3 machine and uses translated weapon IDs/buttons | Native C1 pmove consumes the 10-bit C1 weapon IDs and both hands directly; script grants and ammo mutate this same state |
| Entity update | retained `G_UpdateEntityStateFromPlayerState` / `BG_PlayerStateToEntityState` | Converts the IW3 movement result into an IW3 entity state before C1 overlays | Native C1 `BG_PlayerStateToEntityState` authors a C1 entity state. Copy only runtime collision origin, angles, bounds and contents into `gentity_t::r` |
| Snapshot capture | `SV_BuildClientSnapshot` copies `SV_GameClientNum()` into `clientSnapshot_t::ps` | Snapshot history captures IW3 state plus extension sidecars | Capture the native C1 state and its C1 entity state together in sequence-keyed CoDOL frame storage |
| Snapshot output | `CODOL_BuildGameplayFrame` seeds zero fields then calls `CODOL_OverlayEngineMovement` and weapon overlays | Semantically translates IW3 fields back to C1 on every frame | Read the captured C1 structure directly through the measured 244-field netfield table; keep only asset-handle resolution and wire encoding |
| Prediction trailer | client-supplied predicted origin is stored on `client_t`; ROV compares it to an IW3 result | Diagnostic/correction decision compares different movement implementations | Compare it with the native C1 state produced for the same `commandTime`; never use it as authoritative position |
| Synchronous mode | retained `G_RunClient` rewrites `sess.cmd.serverTime` and invokes `ClientThink_real` | Re-enters IW3 movement | Call `CODOL_ClientThinkReal` with the stored C1 command retimed to `level.time` |

`CODOL_ToEngineUsercmd`, `CODOL_DefaultWireUsercmd(const playerState_t *)`, and
`CODOL_OverlayEngineMovement` may remain temporarily for non-C1 builds or offline
tools. They must not execute for a playing CoDOL client after cutover.

## Authoritative data model

Create these native types under `src/codol/player/`:

- `codol_player_state_t`: typed C1 fields at measured C1 offsets. Use explicit
  padding and `_Static_assert(offsetof(...))` for every movement, weapon and
  snapshot field before adding consumers. Do not alias `playerState_t`.
- `codol_pmove_t` and `codol_pml_t`: C1 command, trace callbacks, hull, touch
  list, stance change, mantle result and per-substep values. Define them from C1
  evidence. Do not reuse `pmove_t` because its embedded command and field layout
  are IW3 ABI.
- `codol_client_runtime_t`: one per client. It owns live C1 player state, current
  and previous C1 commands, button edge state, weapon-hand state, appearance,
  and lifecycle generation.
- `codol_entity_state_t`: already exists as the wire-semantic entity state.
  Promote it to the authoritative C1 snapshot state for CoDOL entities rather
  than recreating it from `entityState_t` at send time.

The native C1 state is the only authority for `commandTime`, `pm_type`,
`pm_flags`, `weapFlags`, origin, velocity, ground entity, stance, view-height
transition, ladder vector, jump/dive/mantle blocks, view angles, current weapons,
weapon-hand phases, ammo and predictable events.

The retained `gclient_t::ps` can exist during migration because retained
assembly assumes `sess` begins at offset `0x2f64`. It is a compatibility cache
for code not yet ported. It must never feed C1 movement or C1 player-state
snapshots. Do not synchronize it back into native movement wholesale. Port each
script getter/setter to the native C1 accessor for its field; a temporary
one-way mirror may serve an unported read-only retained consumer.

## Native command acceptance

Keep the verified C1 delta decoder. Change ownership after decode:

1. Build the packet default command from `codol_client_runtime_t::ps` using a
   C1 `MSG_SetDefaultUserCmd` implementation. This is a C1-state read, with C1
   weapon IDs and C1 stance/ADS/sprint rules.
2. Validate all decoded fields without narrowing them. Weapons and offhands are
   `0..1023`; validate against the C1 weapon registry and ownership in the C1
   state.
3. Deduplicate by C1 `serverTime` and accept the command atomically into
   `lastC1Usercmd`. Keep `oldC1Usercmd` with it so edge checks use the exact
   prior executed command.
4. Dispatch the exact accepted structure to `CODOL_ClientThink`. Do not stage a
   raw command next to an IW3 command. The current `CODOL_ExecutedWeaponInput`
   association exists only because the translation loses fields.
5. Make bots and synthetic spawn thinks produce explicit C1 commands. Their
   provenance may remain recorded, but all gameplay consumers receive the same
   C1 type.

The current semantic `codol_usercmd_t` is a suitable starting point. Confirm its
in-memory field alignment independently from the wire bit order before embedding
it in `codol_pmove_t`.

## Native `ClientThink` and `Pmove`

Implement the whole C1 movement unit before routing live clients into it. The
minimum complete call graph is:

- command-time clamping and substep loop (`Pmove` at C1 `0x416C30`,
  `PmoveSingle` at `0x415FF0`);
- button sanitation and `PM_UpdateViewAngles`;
- trace setup, ground trace, walking/ground-plane classification and touch list;
- `PM_UpdateStance` (`0x412560`), hulls and view-height interpolation;
- friction, acceleration, clipping, slide move and step-slide move;
- walk, air, ladder, noclip, ufo, dead, linked and spectator movement modes;
- jump and landing state;
- C1 mantle detection, mantle trajectory and completion;
- C1 dolphin-dive eligibility, launch, apex, landing slide and completion;
- sprint state and move scaling;
- C1 weapon state for both hands, ADS, reload, offhand, melee, fire and event
  production;
- bob cycle, movement direction, animation selection and predictable events.

The alpha0022 Python pmove is useful as an indexed C1 disassembly notebook. It
is not an oracle. Use the recorded C1 addresses and constants to implement the
native functions, then use IW4 and OpenBLOPS/T5 source for control-flow names,
trace plumbing and server lifecycle where C1 evidence is incomplete. Never copy
their field offsets or flag values into C1 types.

Movement traces should call the existing native collision backend through C1
callbacks. This preserves loaded BSP collision and entity contact while
removing IW3 movement rules. Trace masks, contents, hulls and ground-number
semantics must be C1 values at the C1 API boundary.

## Preserving scripts and entities

`CODOL_ClientThinkReal` should keep the server-side consequences around pmove,
but replace their data source:

1. Compute button edges and location-selection notifications from C1 commands.
2. Select C1 `pm_type` from session, health, links, noclip/ufo and last stand.
3. Run native C1 pmove.
4. If C1 reports a new mantle, create the mantle-blockage entity with the C1
   end position and duration. Do not let retained ladder/mantle code run in the
   same command.
5. Convert the native C1 state to native C1 entity state.
6. Copy C1 origin, yaw, mins/maxs and contents to `gentity_t::r`, then call
   `SV_LinkEntity`.
7. Dispatch C1 predictable events through a C1 event handler. That handler may
   call existing server actions such as `FireWeapon`, `G_UseOffHand`, damage,
   touch callbacks and `Scr_Notify` after their parameters are made C1-native.
8. Run `ClientImpacts`, trigger touching, use activation, player links, remote
   control and water/gameplay post-processing against the C1 result.

This keeps script and entity behavior without using IW3 player movement as an
intermediate representation. Any retained helper that accepts
`playerState_t *` must receive a native C1 overload or be rewritten before it is
called from this path.

GSC player fields need explicit ownership. Movement and weapon methods read and
write `codol_client_runtime_t::ps`. Session-only fields stay in `gclient_t`.
Entity methods stay on `gentity_t`. This also removes the current risk that a
script writes an IW3 field while C1 serialization reads a sidecar approximation.

## Snapshot and archive integration

Extend each CoDOL snapshot frame with a value copy of the authoritative C1
player state. Capture it at `SV_BuildClientSnapshot` time alongside the exact
C1 entity/client states selected for that recipient. Follow spectators and
killcams must select the captured C1 state from the same historical frame; they
must not copy an archived IW3 `playerState_t` and rebuild C1 fields later.

Change the C1 player serializer to read the measured `codol_player_fields.inc`
offsets directly from `codol_player_state_t`. The descriptor table still owns
field order, bit width and change hint. This is serialization, not semantic
translation. Array/HUD sections can remain separate until typed into the C1
state, provided the snapshot capture freezes them with the same sequence.

The normal ROV bit remains zero. Set it for initial state, teleport, movement
mode transitions and explicit correction policy. Its divergence check must use
the C1 origin produced immediately after the command matching
`predictedOriginServerTime`. Do not copy client predicted origin into server
state and do not compare it to the compatibility IW3 cache.

## Cutover order

1. Add exact C1 types, per-client ownership, reset/spawn/copy routines, and
   sequence-keyed snapshot storage. No live routing change yet.
2. Add native C1 weapon registry/state so the pmove uses 10-bit C1 IDs and
   composed definitions directly. Remove the 128-entry IW3 ID limit from the
   CoDOL gameplay path.
3. Port the complete C1 pmove call graph and its collision callbacks.
4. Add native `CODOL_ClientThinkReal`, C1 event dispatch, entity publication and
   synchronous-client routing.
5. Port movement/weapon GSC fields and methods to native C1 accessors.
6. Make snapshot, follow and archive paths consume captured C1 state directly.
7. Switch `SV_UserMove` atomically from the old route to the complete native
   route. Do not operate with C1 stance on one authority and IW3 origin or
   weapon state on another.
8. Delete CoDOL calls to `CODOL_ToEngineUsercmd`, retained `Pmove`,
   `CODOL_OverlayEngineMovement` and primary-hand IW3 `PM_Weapon`. Leave the
   retained route compiled only for ordinary CoD4 clients if that mode is still
   supported.

## First live proof after cutover

Use one command-time trace at the native boundary: command time, exact C1
buttons/direction/weapons, C1 pm flags, ground entity, origin, velocity,
view-height state, mantle/dive phase and weapon-hand states. Compare it with the
client predicted-origin trailer at the same command time.

The decisive checks are held crouch, held prone, repeated tower mantle, ladder
entry/exit, dolphin dive, semi-auto cadence, a primary/secondary switch with a
composed weapon, and a weapon with many attachments plus camo. Success means the
server state remains in the same C1 phase as client prediction; absence of a
crash alone is insufficient.

## Evidence used

- `src/sv_client.c`: current C1 decode, lossy `CODOL_ToEngineUsercmd` call,
  acceptance, predicted-origin trailer and dispatch.
- `src/g_active.cpp` and `src/asmsource/_g_active_mp.asm`: retained
  `ClientThink`, `ClientThink_real`, IW3 `Pmove`, entity publication and
  `G_RunClient` synchronous path.
- `src/codol/snapshot/codol_engine_state.c`: explicit IW3-to-C1 movement flag,
  mode, view-height, mantle and weapon overlays.
- `src/sv_snapshot.c` and `src/codol/snapshot/codol_frame_builder.c`: IW3
  player-state capture followed by C1 frame construction.
- C1 static evidence recorded under alpha0022: `docs/movement_stance_fix.md`,
  `docs/camera_mantle.md`, `docs/ground_entity_num.md`, `ps_offsets.py` and
  `pmove.py`.
- `D:\CoD\OpenBLOPS\Game\Server\game_mp\g_active_mp.cpp`: T5 server lifecycle
  around pmove, entity linking, impacts, events and synchronous clients. It is
  structural reference only.
