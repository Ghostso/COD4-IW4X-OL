# Native rolling collision increment

Source written by worker; parent review and assembly integration pending.
No builds, tests, process changes or UI actions were performed by this worker.

## References and evidence

C1 helper52e850 projects incoming velocity onto the collision plane when
dvar1194 and WeaponDef bytebdb are active; otherwise it performs the ordinary
reflection. Helper52e8d0/52e98d then applies sliding friction and restitution.
These functions' only direct callers, including an executable-section-wide
call search, are in52fc10. Its caller530171 lies inside52fd50, which copies
the missile trajectory onto its stack for prediction. The predictor alone
does not prove authoritative stopping semantics.

OpenBLOPS `Game/Server/game/g_missile.cpp::BounceMissile`2249..2524 supplies
the authoritative reference. It makes the same tangent projection and calls
`GrenadeBounceVelocity`, whose true result means **rolling contact**, not
stationary. It continues linear movement, updates angular rolling velocity,
and independently applies the surface/stickiness/rest-speed stop policy.
This explains why importing the predictor's stop action would prevent rolling.

Verified C1 registrations:

| Name | Storage | Type/default | Range/flags |
|---|---|---|---|
|1194|24b9e28|bool1|flagsC4|
|1195|24b9dec|float0.01|0..1, flags84|
|1196|24b9e04|float0.4|0..1, flags84|
|1197|24b99b8|float100|0..FLT_MAX, flags84|
|1206|24b9e38|float0.3|0..FLT_MAX, flags84|

The names are actual shipped numeric dvar names. T5 English names provide
context only: rolling enabled, low/high friction, speed threshold and maximum
restitution respectively.

## Implemented response

`CODOL_MissileApplyRollingResponse` resolves native metadata, projects
`v - dot(v,n)*n`, and measures tangential speed. It multiplies the tangent by
`1 - (speed<=1197 ?1195:1196)`. For `abs(dot)>=25`, it adds normal impulse
`-dot * min(1-(1-perpendicular[surface])*normal.z,
max(1206,perpendicular[surface]))`. Shallower contacts return1 for rolling.

The authoritative T5 angular relation uses radius5:
`pitchSpeed =360*linearSpeed/(2*pi*5)`, yaw follows velocity, roll is90.
The new native producer evaluates existing angular pitch before rebasing its
linear angular trajectory at level.time, so consecutive collisions preserve
rotation phase. This lifecycle choice makes the inherited native trajectory
produce actual model rotation; exact C1 authoritative phase producer was not
located and is not claimed.

The function leaves linear trajectory type/time/base, origin, fuse and
notifications under the collision caller's ownership. Return-1 means ordinary
bounce remains responsible; return0 means handled rolling-enabled bounce;
return1 means handled rolling contact. None means force-stationary.

## Required caller integration

Call from BounceMissile_40 before the old coefficient block, using the
already evaluated incoming velocity and collision normal/material index.
For nonnegative returns, skip the ordinary bounce coefficient multiplication
and continue into the authoritative stop/stick decision. Save the rolling
result in a dedicated frame local. On a continuing rolling contact, skip the
old MissileLandAngles block that would overwrite the new angular trajectory.
On a genuine stop, keep existing resting alignment and lifecycle.

Metadata extends the native core, not the retained WeaponDef layout.
`CODOL_ReadNativeWeaponBounce` now preserves validated C1 bytebdb, and the
existing core resolver exposes it for mounted/retired/composed weapons.

## Explicit limits

This is core friction, restitution and angular rolling, not complete T5/C1
missile parity. T5 authoritative rolling additionally implements random
bumps, wobble phase, lateral collision traces and curved rolling. Those need
verified per-entity state/lifecycle and careful source review: its displayed
decompilation even marks a suspicious sine-expression reconstruction.
No guessed wobble state, keep-rolling extension or predictor-stop shortcut
was added. Sticky equipment policy is a separate worker's implementation.
Real client behavior remains unverified until parent integration/deployment.
