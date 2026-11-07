# Predator remote missile closes immediately — 2026-09-14

Concrete source defect: converted WeaponDef.projLifetime remained zero because
CODOL_ApplyNativeWeaponProjectile imported launch speed/damage fields but not
lifetime. Retained G_FireRocket reads native+578, multiplies seconds by1000,
adds level.time, and schedules nextthink (maximum level.time+60000). Zero
therefore schedules the rocket's think immediately. This explains the observed
brief static-and-close lifecycle without requiring a camera visual fallback.
It is source evidence; this worker did not capture the user's exact dying entity.

Effective vendor maps/mp/killstreaks/_remotemissile.gsc creates MagicBullet,
links camera/controls, waits for rocket death, then runs staticEffect(0.5),
unlinks and clears remote state. Existing native controls/trajectory consumers
are present; this increment does not replace them or add a script overlay.

C1 producer evidence: 53169b reads WeaponDef+7a4 as float, multiplies by double
C842B8=-1000, converts to integer, subtracts from level.time at5316ac..5316b4,
and stores nextthink at entity+1cc. 5316ba..5316c8 caps to level.time+60000.
Thus the field is seconds, not milliseconds. 531749 reads adjacent+7a8 for
zero versus accelerated launch, matching retained timeToAccelerate selection.

Shipped common_gametype_mp remotemissile_projectile_mp has lifetime12.0 seconds,
timeToAccelerate0.0 and projectileSpeed10. No matching inline weapon definition
was found in the inspected patch_common_gametype_mp weapon records. The existing
bomb metadata reader independently reads+7a4 as lifetime but never filled the
retained rocket consumer's WeaponDef field.

Change restricted to CODOL_ApplyNativeWeaponProjectile in
src/codol/weapon/codol_weapon_native.c: copy+7a4 to projLifetime and+7a8 to
timeToAccelerate. Both floats are checked finite before output mutation, along
with the existing cone validation. Preserve source zero/negative semantics and
the existing producer's deadline conversion/cap; no invented duration/default,
no client asset changes, no timing delay to disguise the lifecycle error.
The same native conversion function serves composed source images too.

Status: source written and reviewed locally, parent build/runtime verification
pending. No automated tests, builds, process changes or UI actions by worker.
