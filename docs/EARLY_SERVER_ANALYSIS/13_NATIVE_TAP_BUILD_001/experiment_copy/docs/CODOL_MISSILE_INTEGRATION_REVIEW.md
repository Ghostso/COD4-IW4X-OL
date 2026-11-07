# Native missile integration source review

Scope: current codol_missile_collision.c, codol_missile_rolling.c,
codol_equipment_lifecycle.c and retained _g_missile.asm integration. Read-only
source review; no tests, builds, process mutation or gameplay claim.

## ABI / storage

BounceMissile frame0xbc retains its three callee-saved registers. Dedicated
locals-a4 (entry trajectory),-a8 (collision policy),-ac (rolling result) are
outside the rolling helper outgoing five-argument area. Cdecl EDI/ESI preserve
entity/trace across native helpers; assembly restores xmm3 to zero after rolling.
The coefficient helper uses a separate temporary32byte stack allocation and
restores it on success/failure. No overlapping local or unbalanced epilogue was
found in these branches.

G_RunMissile frame1fc has three matching epilogues. Its generation local-1c0 is
outside existing deepest local1b8 and the outgoing48byte area ending at-1d8.
The original ground entity index in ECX is restored across attachment helper
before G_RunMissile_20. Both direct BounceMissile calls handle internalreturn2.
The outer impact caller validates r.inuse/useCount/eType before continuing.

## Lifetime / trajectory

Stationary notification requires entry moving and exit stationary, so strong
airborne return1 and repeated settled collisions do not emit it. Notify helper
releases its string reference, checks generation/inuse/type, and returns failure
for deletion/reuse/conversion. Outer impact generation guard prevents continued
simulation against a replacement missile sharing the old slot.

Rolling helper changes velocity/angular trajectory only; existing caller owns
position/time/fuse and stop decisions. Rolling result1 is not used as a stop.
Continuation skips MissileLandAngles only for handled rolling. True stop calls
G_SetAngle, whose native implementation g_utils_mp.cpp86 explicitly sets angular
TR_STATIONARY, clears time/duration/delta, and updates current angles. Therefore
settling cancels previous rolling angular velocity.

No concrete introduced crash or stack corruption was identified in this review.
This is not a runtime safety guarantee.

## Known semantic limits

OpenBLOPS GrenadeBounceVelocity has an explicit isDud branch excluding rolling
response. Current rolling helper does not receive or check native dud state.
This is a source-level parity gap, not proof of a presently reachable crash.
Implement only after locating the corresponding native/C1 dud producer; do not
reinterpret a similarly named union field across layouts.

C1 flesh-mode wall embedding, extra T5 wobble/curve/bump behavior, and actual
Betty/scrambler activation remain outside this bounded integration. Registered
rest-threshold dvar integration is owned by parent/rolling worker and was pending
while this review began. The reviewed snapshot still used ordinary20constant;
parent is replacing it with the verified current dvar.
