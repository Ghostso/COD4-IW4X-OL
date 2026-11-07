# Grenade fuse and stickiness evidence

## Live failure

Passive ReadProcessMemory inspection of native PID91984 found entity105 still
alive at level.time398500, more than a minute after the reported throw:

- Valid inuse entity, number105, type4 (missile), handler7.
- Weapon7 resolves to `semtex_mp`.
- Origin `(4107, -922.8, 5.625)`, nextthink0.
- Native WeaponDef.timedDetonation (`+5ac`) was0.

The retained `BounceMissile` clears nextthink when this field is0. Handler7
correctly points to G_ExplodeMissile; the think callback table is not the fault.
The CoDOL loader currently copies fuseTime but not timedDetonation.

## Verified serialized fields

| C1 WeaponDef | Meaning | Evidence |
| --- | --- | --- |
| +654, int32 | fuseTime, milliseconds | 41c55b initializes ps+34 |
| +bcc, byte | cookOffHold | 41ccff..41cd0e subtracts frame msec from held grenade timer only when set |
| +be2, byte | timedDetonation | 530930..5309cf grenade fuse scheduling, matching retained G_FireGrenade |
| +7c8, int32 | stickiness enum; expanded beyond IW3 | 52eaa0..52eb78 collision stick decision |

At `53094b` C1 tests +be2. When set and the owner's ps+34 is positive, it
adds that timer to level.time and stores entity nextthink at+1cc. The zero
branch clears ps+34. With no held timer, it uses the supplied fuse; the helper
then applies the same 30-second default and 60-second cap as retained
G_FireGrenade. This establishes the semantic mapping without equating offsets.

Passive reads of named C1 WeaponDefs confirmed +be2 is1 for semtex/frag/flash/
smoke/throwingknife and0 for C4/claymore. These values corroborate the consumer;
they are not a per-name substitution rule.

## Stickiness needs an expanded consumer

C1 +7c8 values observed: semtex1, C4=2, claymore4, throwingknife5, ordinary
grenades0. At52eac7 and52ead0, both1 and2 take the all-surface-stick branch.
The retained IW3 enum2 means ground-only and has no4/5. Therefore a raw integer
copy would be incorrect. The C1 routine also checks byte+bde for its special
collision target and applies additional directional/velocity logic to5.

`CODOL_ApplyNativeWeaponFuse` now copies verified bytes+be2 and+bcc into
native timedDetonation and cookOffHold alongside the existing fuseTime mapping.
It validates both boolean bytes are0/1 and fuseTime fits int before any writes.
Source inspected and changed; parent build and live grenade verification remain.
No stickiness offset or enumeration should be guessed. No tests, builds, UI
actions, or process writes performed during this investigation.

## Deployed field verification

Passive inspection of native PID61844, build
`5BC16E6E159424A0C6EB1CA22ABBA70FAFB706ED3824CE8E5A3B96881BAACB1E`,
confirmed the mounted values below. Linked producer instructions independently
confirm native destinations timedDetonation+5ac and bCookOffHold+4fc.

| Mounted weapon | Native index | timedDetonation | bCookOffHold |
| --- | ---: | ---: | ---: |
| frag_grenade_mp | 6 | 1 | 1 |
| semtex_mp | 7 | 1 | 0 |
| c4_mp | 10 | 0 | 0 |

This verifies deployed data, not a post-fix throw/detonation.

## Proposed C1 stickiness consumer work (not implemented)

1. Retain the C1 enum+7c8 and its independent target flag+bde in native
   projectile metadata. OpenBLOPS `bg_weapons.h:250` documents six values:
   none0, all1, all-no-sentients2, ground3, ground-with-yaw4, flesh5. C1's
   independent consumers below must remain authoritative for behavior.
2. Replace `BounceMissile`'s stick/stop decision in `_g_missile.asm`.
   Its current `BounceMissile_10` excludes every trace entity<=63 for any
   nonzero stickiness, while C1 `52e740` resolves the hit entity and classifies
   eType1/player and18/actor; `52eaa0` uses byte+bde for that case. For other
   hits, C1 permits1/2 on all normals, treats5 with directional/speed checks,
   and applies the ground-normal threshold to3/4. Zero permits low-speed
   settling. C1 callsite is `52fcb8`.
3. Audit resting orientation in `BounceMissile_120/130` and
   `MissileLandAngles`. Retained3 means preserve yaw; C1's expanded4 carries
   that role. Do not globally change comparisons without separating retainable
   IW3 assets from C1 metadata.
4. Update `G_RunMissile` attachment maintenance and post-trace decisions.
   The retained entry only treats1 as attached; later code groups2/3 as ground
   cases. C1 `52df00` groups1/2/5 as attachable and is called at52fe8e.
   Entity ownership, hit classification, trajectory and attachment lifetime
   must use the actual C1 meanings.
5. Update `G_ExplodeMissile_140/230` attachment-relative explosion origin.
   Retained code only admits1; C1 `52ee31..52ee46` admits1/2/5 before its
   attached-entity branch. This affects where the effect/damage originates.

Existing retained accesses to stickiness are confined to these three missile
functions; the asset loader and enum declaration also need representation work.
This is a coordinated native consumer change, not an integer-only mapping.

## Native decision helper (source written; shared integration pending)

`codol_missile_stickiness.c/.h` now read the verified fields atomically into a
separate six-value native representation. They implement attachment eligibility
and the C1 52eaa0 stop predicate. The latter takes resolved player/actor identity,
surface normal, post-reflection trajectory velocity and the current stop-speed
dvar explicitly. It does not classify retained IW3 entity integers as C1 actors.

The target check precedes all mode checks: player/actor hits return byte+bde.
Other hits stop unconditionally for modes1/2. Mode5 stops when normal.z>0.7 and
speed<stop-speed, or when dot(normal, normalized reflected velocity)>0.7.
Other modes require normal.z>0.7; mode0 additionally requires speed<stop-speed.
Equality does not satisfy these comparisons. C1 6190b0 normalizes with divisor1
for a zero-length vector. Callsite52fc55/52fc62/52fcb8 proves post-reflection
velocity, rather than the incoming trajectory, is the argument.

C1 registration52e448..52e47b creates float dvar `1193`, default20, minimum0,
maximumFLT_MAX, flags0x84. The helper accepts its current value; it does not bake
the default into gameplay.

Parent integration must retain metadata with each base/composed weapon core,
initialize via the reader, resolve actual native target identity and replace
the retained stop/attachment branches. The shared assembly/struct files were
not edited by this worker. Actual resting orientation remains unresolved:
52eaa0 is used by trajectory simulation52fc10, not an orientation writer.
OpenBLOPS's resting code treats modes4 *and2* as maintaining direction, which
is a useful lead but is not proof of C1 orientation. No orientation fallback or
raw IW3 enum substitution was implemented. No builds/tests/process changes.

## Follow-up: stop helper is prediction, not the authoritative bounce writer

The bounded direct-call audit establishes the complete visible call chain:

| Address | Evidence |
| --- | --- |
| 52eaa0 | Stop predicate; sole direct caller52fcb8. |
| 52fc10 | Reflects and changes the supplied trajectory; sole direct caller530171. |
| 52fd50 | Copies nine dwords from entity+0xc into stack trajectory at52fd6f..52fd7d. Simulates from current time+50, incrementing50 at5301b7. Returns projected position and stop time. Sole direct caller6da5bd. |
| 6da5bd | Supplies grenade remaining fuse, receives stop time, stores it at entity+218; projected position is stored at+20c/+210/+214. This is grenade prediction used by AI handling, not the per-frame projectile collision writer. |

Consequently, the new helper implements a verified C1 **prediction decision**.
That is insufficient evidence to replace authoritative `BounceMissile` and call
the result exact C1 gameplay. Shared metadata storage is independently valid.
Do not infer authoritative orientation or collision side effects from this
simulation, which operates on a copied trajectory and never writes rest angles.

The remaining direct WeaponDef+7c8 references examined do not supply the missing
orientation writer:438884 groups1/2/5 in a client predicate;46c20a groups1/2/5
versus3/4 into client output categories3 versus2;52ee31 groups1/2/5 for explosion
placement with ground entity present;67791e groups1/2/5 during attached-missile
entity handling;6db3f5 selects mode0 in AI grenade handling. Other raw displacement
matches at7ca91f/abf861 are unrelated structures. Byte+bde's only verified direct
WeaponDef consumer is52eab2; the6b026e raw match is an instruction immediate,
not a WeaponDef field read.

No authoritative resting-orientation writer or actual per-frame bounce routine
was identified in this bounded pass. This is an unresolved evidence requirement,
not proof that the executable lacks that behavior. No additional source changes,
builds, tests or process actions were performed.
