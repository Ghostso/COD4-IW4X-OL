# Chopper gunner unlink crash — 2026-09-14

Proven primary failure in supplied attachment: `G_VehUnlinkPlayer: Player is
not using a vehicle`. Snapshot overflow messages occur during shutdown after
this error and do not establish a snapshot root cause for this crash.

Effective IW4 `_helicopter.gsc::heliRide` starts VehicleTurretControlOn and
PlayerLinkWeaponviewToDelta to `tag_player`. Its `endRide` calls ordinary player
unlink before VehicleTurretControlOff. The native controller installs gunner
slot/control ownership without native boarding state; this is intentional for
scripted weapon-view links.

Retained `_g_utils_mp.asm::G_EntUnlink` unconditionally called native dismount
when a linked player's parent classname was script_vehicle. The dismount
requires ps.pm_flags0x100000 and a real occupied ride slot, so scripted chopper
cleanup fails that assertion. OpenBLOPS Game/Server/game_mp/g_utils_mp.cpp931
confirms generic tag unlink is independent of this occupied-seat operation.

Source fix: under CODOL_SERVER, require occupied bit and matching owner handle
before the existing classname check enters G_VehUnlinkPlayer. Otherwise retain
ordinary tag-chain removal, pose restoration and pm_type restoration. Native
G_VehEntHandler_Use establishes that bit and owner handle together after seat
link; G_VehUnlinkPlayer clears them together. All existing actual ride exits
remain on the same dismount path. No stack frame change and no call introduced.

Source ready for parent review/build. No tests/build/process edits by worker.
Stationary flight remains separate: helicopter creation schedules handler23;
Helicopter_Think invokes Scr_Vehicle_Think; setvehgoalpos sets script movement
flags and driving state, and Vehicle_SetSpeed fills the fields consumed by that
movement path. No recorded native vehicle state from the failing activation was
available to identify the precise stopped-flight gate; no speculative movement
change was made.

Passive probe: tools/codol_helicopter_probe.py --pid <native PID> --samples 40
--interval .5. Reads only process memory. Resolves live ASLR module base,
relocates the built image, verifies native function bytes and derives data
addresses from that binary's COFF symbols. Struct offsets are retained-native
fields, not assumed C1 offsets. Vehicle controller is resolved by actual native
pool pointer (level+2e68), never by entity allocation order. Samples are JSON
and include the executable hash, server clock and physical timestep.

Initial passive capture on deployed SHA2F7D50A8/PID40176 at server time210800:
vehicle timestep0.05s, helicopter think50ms, no active vehicles. This verifies
reader access and baseline timing only, not helicopter gameplay behavior.
