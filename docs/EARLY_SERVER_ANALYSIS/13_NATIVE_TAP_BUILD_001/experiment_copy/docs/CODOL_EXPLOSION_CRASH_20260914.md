# Explosion crash investigation — 2026-09-14

## Available incident evidence

- `bin/home/main/qconsole.log.old` (last write14:17:38) ends during active
  gameplay, at server time102450 / command102366. Shortly before that it logs
  `unmapped primary event 63 parameter 0 dropped from the wire`. The file ends
  after pacing output for client0 at origin(4038,1198,4). No exception, fault
  address, backtrace, script error, or shutdown reason is present in its tail.
  This does not establish that event63 or a specific grenade caused the exit.
- The current `qconsole.log` records a different, explicit script failure:
  unknown weapon `white_phosphorus_grenade_mp` in `_class.gsc` line200's
  `setOffhandEquipment` call, followed by server shutdown. This is not evidence
  for the earlier explosion fault.
- The newest `codol_dedrun` dump in
  `C:/Users/Michael/AppData/Local/CrashDumps` is PID54208, Sept11 14:31:08.
  Windows Application event1000 corroborates that older fault at14:31:06,
  exceptionc0000005, module offset226972. It predates the fuse/projectile
  changes and must not be attributed to this incident. No newer matching
  Application1000 event was found in the inspected three-day interval.

## Source review

`CODOL_ApplyNativeWeaponProjectile` now supplies the verified speed/up/forward,
radius and inner/outer damage fields. Nonzero inner damage makes
`G_ExplodeMissile_190` take the radius-damage branch at `_g_missile.asm`'s
`G_ExplodeMissile_40`; previously zero inner damage skipped it. This identifies
a newly exercised path, not a fault location.

The new `CODOL_NativeMissileSupportsAttachment` call in
`G_ExplodeMissile_140` passes the native WeaponDef in the first cdecl argument.
The surrounding code depends on ESI/EDI, which are callee-preserved; there is
no demonstrated calling-convention defect in that addition. The existing
attached-origin path still requires a non-none ground entity before using the
stored normal. Stop/stick/orientation predicates were not broadly substituted.

A separate verified omission remains: native `damageConeAngle` is not loaded
from C1+788. Retained `G_ExplodeMissile_40` takes its cosine and sends it to
`G_RadiusDamage`. A zero-initialized angle produces cosine1; this changes damage
visibility filtering. The C1 angle mapping was documented in
`CODOL_PROJECTILE_LAUNCH_DAMAGE_MAPPING_20260911.md`. Correcting it is justified
for explosion semantics, but is not established as a crash fix.

## Outcome

No concrete crash instruction or failing object is available from these logs
and dumps. No speculative null guard, handler rewrite or damage suppression
was applied. Preserve a contemporary crash dump/exception stack on the next
failure before assigning the crash to radius damage, attachment placement or
the dropped event. This pass made documentation changes only; no builds, tests,
process writes, restarts or client/Python changes.
