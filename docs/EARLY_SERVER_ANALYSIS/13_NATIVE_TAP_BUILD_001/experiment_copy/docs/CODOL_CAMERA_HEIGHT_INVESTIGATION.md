# First-person camera investigation, 2026-09-10

Status: root cause found and native fix written; build/runtime verification is
pending the next authorized server restart. C1's normal camera path requires
playerState +0x1ec (`linkWeaponEnt`) to be `ENTITYNUM_NONE` (2047). The native
snapshot left this CoDOL-only field at zero, meaning a weapon-view link to entity
0, so C1 skipped the eye-height add and clamped the camera to origin.z + 8.

## Confirmed source and binary evidence

- `ClientSpawn` in `src/g_client_mp.cpp` sets native viewHeightTarget/current
  to 60 and clears the lerp start. Retained `PM_CheckDuck` evolves standing,
  crouch, prone and spectator heights. Its zero-height branch applies to native
  spectator pm_type 4; the wire adapter correctly maps this to C1 type 5.
- `CODOL_OverlayEngineMovement` publishes the captured native target at C1
  playerState +0x158 and the floating current height at +0x15c, along with all
  three transition fields +0x160/+0x164/+0x168.
- Independently disassembled the supplied C1.exe: 0x40df38 adds [ps+0x15c]
  to origin.z; 0x429082 loads the same offset from the predicted playerState.
  Thus adding 60 to the server origin would double the height when the normal
  camera path works and would break stance transitions.
- The native field table carries target as signed 8 bits and current as float
  XOR (-88), both hint 0, so read-origin/prediction suppression does not omit
  either height field. Existing native tests cover 59.5 current /60 target and
  transition capture. They were inspected, not rerun in this investigation.
- The previous ledger documents a separate floor-camera failure from omitted
  baseline origins. The current native snapshot preparation already forces
  read-origin when there is no base. That historical fix is not evidence that
  this newly reported symptom has been fixed.

## Native fix

- `CODOL_OverlayEngineMovement` now explicitly publishes 2047 at C1 +0x1ec for
  the normal player camera.
- Captured player-link state now carries `linkWeaponEntNum`; the later link
  overlay replaces +0x1ec only for `playerLinkWeaponViewToDelta` and restores
  2047 after unlink. Camera-link +0x54 and controls-link +0x5c remain separate.
- The extension archive uses 11 bits for all entity-number fields. Its previous
  10-bit camera/control encoding could not represent CoDOL `ENTITYNUM_NONE`.
- `test_codol_native.c` asserts the normal movement overlay publishes 2047.

Direct C1 evidence: `CG_OffsetFirstPersonView` compares `[ps+0x1ec]` with
`0x7ff` at 0x4711aa, branches around the height add at 0x4711ea when unequal,
then loads `[ps+0x15c]` at 0x4711ec. This was rechecked against the supplied
1.1.1.13 `C1.exe` with `objdump`, not inferred from IW3/IW4/T5 offsets.

## Read-only live observation

C1 PID 84144, using its actual camera pointer decode instructions:
commandTime 0, origin (0,0,0), view target/current 0, no current gameplay snapshot.
This is disconnected state and cannot establish the in-game camera defect.

`tools/codol_camera_probe.py --pid 84144 --samples 3` now reads predicted,
current snapshot and next snapshot camera fields. It requests only PROCESS_VM_READ,
checks the C1 camera-consumer instruction signature, and never writes process
memory or attaches a debugger. Executed successfully against the current client.

After the next build/restart, use this while reproducing the first-person view:

- Snapshot height 0 in normal play: trace native movement and captured frame.
- Snapshot height correct but predicted height 0: trace client movement mode,
  transition and camera-link flags.
- Both heights correct: compare origin/world floor and camera/viewmodel behavior;
  changing the height field would be an unsupported workaround.

No client/lobby/server restart, full server build, or gameplay mutation was made.
