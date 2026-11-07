# Native PhysicsLaunchClient

`physicslaunchclient` now calls the retained native `ScriptEntCmd_PhysicsLaunch`
and then `SV_LinkEntity`. The wrapper rejects non-entity, reserved and unused
references; native launch retains its script-mover class and argument checks.
With exactly two arguments it reads linear/angular trajectory deltas; otherwise
the retained implementation initializes both deltas to zero. No Python runtime,
hook or external executable address is used by the implementation.

Evidence comes from the local `D:/CoD/shx/iw4x.exe`: the method registration at
0x73d8e8 associates `physicslaunchclient` with 0x407eb0. That method calls
SetupPhysicsLaunch at 0x5face0, clears contents/physicsObject, then calls 0x4e0880.
[IW4x Server.cpp](https://github.com/iw4x/iw4x-client/blob/main/src/Game/Server.cpp)
identifies the latter as `SV_LinkEntity`. The helper evaluates the current
trajectories, copies vector 0/1 to linear/angular deltas, and uses IW4 trajectory
type 9. The retained IW3 helper performs the same setup using native type 8.
The Python reference's point/force comment does not match these method semantics.
This implements the requested IW4 builtin; direct C1 server-method parity remains
unverified because that registration was not found in the client executable.

The isolated Bog VM fixture creates script models, calls the method with vectors
and with no arguments, checks the original position and deletes the models.
`SH1X_PHYSICS_LAUNCH_CLIENT_VM_PASS` appears alongside both node markers in
`%TEMP%/sh1x-physicslaunchclient-vm-probe/main/games_mp.log`. Probe PID 53656
exited through quit. This verifies native invocation, not client-side rigid-body
simulation or every error branch.

Full reference script compilation advances past this missing method and now
fails at `EnableOffhandWeapons` in `common_scripts/utility.gsc:2714`.
Reference probe PID 66396 terminated after fatal script compilation/network
shutdown; log: `%TEMP%/sh1x-physicslaunchclient-reference-probe/main/qconsole.log`.
No existing client or lobby was modified. Windows build passes
(`/tmp/sh1x-physicslaunchclient-win32.log`).
Full Linux `make -B -j6 all test-codol` passes
(`/tmp/sh1x-physicslaunchclient-linux.log`).

The CoDOL trajectory adapter now translates native client-physics type 8 to
CoDOL type 9 for both position and angular trajectories. It preserves launch
time, duration, base and delta; no ballistic approximation is substituted.
The native enum now names the already-used value as `TR_PHYSICS = 8`.

Local C1 evidence (SHA-256 rechecked for this analysis:
`d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`):

- `0x443325` selects the centity's previous position trajectory at +0x74;
  `0x443337` tests type 9 and dispatches a special handler, bypassing ordinary
  trajectory evaluation. The interpolation path also excludes next-state
  position type 9 at +0xf0 (`0x443359`).
- The ordinary path calls `BG_EvaluateTrajectory` (`0x40ca40`) for position
  at +0x74 and angles at +0x98 (`0x4433d9`, `0x4433ed`). Its jump table at
  `0x40cca8` sends type 9 to base-copy (`0x40ca5c`), rather than gravity.
- Centity cleanup tests position type 9 at `0x46b59c`, destroys the associated
  nonzero/non-sentinel handle through `0x6592c0`, then clears both trajectory
  types and the handle (`0x46b5de`). This supports identifying the special
  type as physics, consistent with IW4's named type 9 and the retained native
  launch setup. The special handler's protected body was not fully recovered.

The native integration fixture now composes a script mover with both physics
tracks, checks linear/angular delta preservation and the native maximum
duration, checks serializer reachability, and writes an entity section. Invalid
angular data or an unsupported mode preserves both entity output and event
clock. This verifies native conversion and encoding, not observed C1 rigid-body
simulation. Live snapshot producers, full script startup and match entry remain
incomplete. The earlier startup blocker above describes the historical probe;
the current unresolved script function is `weaponInheritsPerks`.

Validation for the trajectory change: Linux `make -j6 all test-codol` passes
(`/tmp/sh1x-physics-trajectory-linux.log`), including the new native entity
fixture. A subsequent forced Windows cross-build of `bin/codol_dedrun.exe`
passes (`/tmp/sh1x-physics-trajectory-win32.log`). Shared static libraries were
last rebuilt for Windows; force their rebuild before the next Linux link.
