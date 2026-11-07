# Grenade collision loses all velocity through unpopulated coefficients

2026-09-14. Source written and read back by worker; parent review/build pending.
No tests, builds, launches, process changes or UI input by this worker.

## Concrete defect

`build_weapon_core` zero-initializes `codol_native_weapon_core_t` and previously
never imported bounce coefficients. Retained `BounceMissile_110` read
WeaponDef5c0/634, its29-entry parallel/perpendicular arrays, interpolated them
against collision incidence and multiplied the reflected velocity by the
result. Both values were zero, so impact removed all velocity. The following
floor branch then saw speed<20 and stopped the grenade. This directly explains
why ordinary floor hits appeared to stick despite nonsticky definitions.

It also extracted a five-bit material index and used that index against the
29-entry arrays. Surface29/30 could therefore read unrelated native fields.

## Verified source data and C1 consumer

C1 `52e942..52e967` computes perpendicular850 minus parallel7d4, multiplies by
negative collision dot / incoming speed, then adds parallel7d4. It applies
the result to reflected XYZ. Array stride850-7d4=7c holds31 float entries.
The next source field is8cc, confirming the second31-entry array boundary.
This consumer belongs to the previously traced C1 trajectory prediction path;
it does not independently prove every authoritative rolling/stopping branch.

Integrity-verified `common_gametype_mp.ff` weapon records confirm frag,
flash, concussion and white-phosphorus mode0, semtex mode1. All sampled records
carry31 nonzero-or-meaningful-zero coefficient entries. Examples shared by
these records: surface0 parallel0.5/perpendicular0.25; surface1 approximately
0.6/0.25; surface29 and30 each0.5/0.5. Perpendicular23..25 are genuinely0,
and must remain0. No generic constant was substituted for archive values.

Collision material import preserves source `surfaceFlags` verbatim in
`codol_collision_materials.c` and `codol_collision_native.c`, so these indices
already refer to C1 surfaces. There is no justification for truncating or
mapping them onto IW3 surface IDs.

## Implemented data path

* `codol_weapon_native.h`: adds31-entry bounce metadata alongside the native
  core; leaves retained WeaponDef layout intact.
* `codol_weapon_native.c`: atomic finite-float import from7d4/850 during every
  core build, including composed weapon cores using that builder.
* `codol_asset_registry.c`: bounded getter resolves mounted/retired/composed
  core using the existing core resolver, then returns the exact indexed pair.
* `_g_missile.asm`: CoDOL BounceMissile_110 calls that getter and feeds the pair
  into the existing interpolation. Incoming speed survives the C call;
  scratch xmm3 is restored to zero before returning to the common branch.
  Non-CoDOL assembly retains its existing arrays.

Surface31 is outside the31-entry C1 data, and a missing core has no verified
coefficient. In either invalid-data case the helper fails without output and
the collision keeps the already reflected velocity without coefficient
damping. This is explicit defensive behavior, not claimed C1 parity; it avoids
an out-of-bounds read or silently substituting another material. Normal mapped
C1 surfaces0..30 always use their exact archived values.

## Rolling and stickiness limits

C1 `52e92e..52e940` also gates an alternate path52e98d through dvar24b9e28 and
WeaponDef bytebdb. All sampled grenade records have bdb=1. That separate
rolling response has not been implemented by this coefficient correction.
Do not report complete C1 rolling parity from bounce data alone.

Native stickiness enum values still differ from the complete C1 enum. The
existing helper metadata is retained; this patch does not newly wire the
earlier predictor-only stop predicate into authoritative collision. Semtex
and specialized adhesive equipment need their verified authoritative target,
orientation and attachment lifecycle, independently of this nonsticky bounce
fix. User-visible bounce/rolling behavior remains unverified until deployment.
