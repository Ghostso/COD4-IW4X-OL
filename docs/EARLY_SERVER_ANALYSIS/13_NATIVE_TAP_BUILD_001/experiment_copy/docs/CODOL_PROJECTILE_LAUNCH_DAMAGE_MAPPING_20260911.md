# C1 projectile launch and explosion fields

## Consumer-verified mappings

These are C1 WeaponDef offsets, not presumed IW3 layout matches. Native field
names below refer to `src/xassets/weapondef.h`. No source changes were made in
this audit.

| C1 offset | Serialized type | Native destination | Consumer |
| --- | --- | --- | --- |
| 794 | signed int32 | iProjectileSpeed | 573f21 converts to float, multiplies forward x/y/z at573f30..573f49. |
| 798 | signed int32 | iProjectileSpeedUp | 573f52 adds to launch velocity z. |
| 79c | signed int32 | iProjectileSpeedForward | 573f27 reads; when nonzero,573f5f..573f8c adds this scalar times normalized horizontal forward to velocity x/y. |
| 778 | signed int32 | iExplosionRadius | 52f13c passes radius to522950;5229af uses it for query bounds,522bea divides distance by it. |
| 780 | signed int32 | iExplosionInnerDamage | 52f150 passes inner damage;522c08..522c18 interpolates inner/outer with distance/radius. Zero skips radius damage at52efdd. |
| 784 | signed int32 | iExplosionOuterDamage | 52f146 passes outer damage into the same interpolation. |
| 788 | float32 | damageConeAngle | 52efea..52f030 compares against180 degrees; otherwise converts degrees to radians and takes cosine for radius-damage cone. |

Actual grenade launch function573f10 passes the computed velocity to entity
producer5309d0 at573fb6. This is distinct from the AI prediction routines studied
in the stickiness audit. The alternate launch helper574030 also multiplies by
+794 and adds+798 to z (57403d..574070).

Horizontal normalization573350 uses the inverse-square-root estimate constant
0x5f3759df and one refinement. It is not an exact sqrt normalization. This detail
matters to a later native launch-path rewrite; copying the three scalar fields
does not establish full launch parity. Parent integration should preserve signed
up/forward values and zero values, not silently clamp or synthesize defaults.

Explosion producer52eb90 loads the definition using the actual entity weapon.
At52f11f..52f15b, stack arguments are origin, inflictor, inner damage, outer
damage, radius, cone cosine, cone direction, ignored entity, damage type, and
the final sentinel. The callee's522be5..522c18 computes
`outer + (inner - outer) * (1 - distance/radius)`, confirming damage semantics
independently of field ordering.

## Radius-min field needs separate treatment

+77c is passed alongside+778 only in explosion mode2's extra path
52f169..52f1b2. Routine522870 clamps its second float to at least1 and the first
to at least the second, gathers entities using the first, then dispatches both.
This is consistent with the existing flash-radius pair, but should not be
claimed as a general damage minimum radius without tracing522580 and verifying
native flash consumers. It is not passed to ordinary radius damage522950.

## Validation state

Offsets/types above are verified through actual C1 consumers. Shipped-definition
value corroboration remains pending. A passive lookup in preserved C1 PID74192
(module base400000) did not resolve coherent names through previously recorded
weapon indices; no values from that stale/unloaded lookup were accepted. No
runtime writes, UI actions, tests, builds, or process changes were performed.
