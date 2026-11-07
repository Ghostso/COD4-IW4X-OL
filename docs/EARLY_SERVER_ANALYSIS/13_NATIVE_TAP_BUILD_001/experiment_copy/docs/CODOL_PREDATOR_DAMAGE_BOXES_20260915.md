# Predator damage and target boxes — 2026-09-15

## Damage correction ready for parent review/build

Retained MissileImpact loads WeaponDef+5a0 (`bProjImpactExplode`) at entry.
It skips its radial-damage branch when that field is zero, even if the bound
radius and inner/outer damage are nonzero. No native producer previously set
this field for mounted C1 definitions; zero-initialized cores therefore left it off.

Native `CODOL_ApplyNativeWeaponProjectile` now validates C1 packed byte+bdd as
boolean before any output mutation, then binds it to the named native field.
Evidence is the independently verified C1 tail anchors bdb rolling, bdc explosion
normal-up, bde stick-to-players; the IW4 named schema places impact-explode
between the latter two. Passive C1 PID90404 capture command210990 independently
shows bdd=1 for remote missile/RPG/M79 and0 for frag/semtex/throwing knife.
Remote definition index85 has radius450, inner1000, outer10, cone180.
This is schema-plus-live validation, not recovery of the C1 impact instruction.
No weapon-specific damage override, script damage workaround or client patch.

Source: src/codol/weapon/codol_weapon_native.c. No worker build/tests/restart.

## Enemy box producer/consumer audit — no fix claimed

Original IW4 _remotemissile.gsc calls delayedFOFOverlay after camera vision,
waits0.15 then calls ThermalVisionFOFOverlayOn, and clears it on cleanup.
Native registry routes the method to the real ps.otherFlags bit0x10 producer.
Snapshot overlay preserves this bit in C1 wire playerState+10.

C1 43b90a tests that bit and invokes483fd0 for enemy boxes. The latter requires:
- local clientinfo valid (484055);
- target clientinfo valid (484092), not local (484086), and different team unless
  local team0 (48409c..4840a3);
- current centity valid bit0 at+1fc (4840bd), type1 at+e8 (4840d0);
- target clientinfo perk word bit27 clear (4840c6..4840ce).
Projection483c90 decodes the actual centity origin at+18/+1c/+20, projects base
and elevated point, and returns false for offscreen/behind-view points. It does
not need a head tag or DObj model to draw these boxes.

Capture command210990 outside remote mode: enemies1/3/5/7 pass valid/type/team/
perk gates. OtherFlags1000 has no overlay bit, as expected outside missile use.
This does not establish what occurs during actual missile flight.

A separate native camera publication gap is worth tracing: SV_BuildClientSnapshot
uses ps.origin+viewHeightCurrent for entity PVS even with a linked missile camera.
No linked-camera origin is consulted. Distant enemies can therefore be omitted
from the received state before HUD filtering. This remains a candidate, not a
proved explanation of the reported flight. Correct reference camera PVS and
archive contract must be established before changing it; do not force-broadcast
enemies or override legitimate perk/team filtering.

Passive tool obj/codol-predator-passive.py validates fixed C1 image signature,
requires active snapshot/command, and reads clientinfo/entity eligibility plus
loaded projectile values. Revalidate PID/path before use. A capture during an
actual remote flight is the next discriminator: otherFlags10, received enemy
validity, projection origin/camera, and material/dvar state if all gates pass.

## Additional passive capture

A bounded30-sample passive watcher crossed a map transition (command360250 to
23516) without observing remote bits; it therefore captured no actual missile
flight. Revalidated active capture at command29997 resolves material pointer
1e26198 to `hud_fofbox_hostile`, so the required box material is loaded.
The exact projection sizing dvars read by483c90 are numeric569=640,568=30,
567=1.3, all nonzero. No material or sizing-dvar changes are justified by this
capture. Runtime settings and gameplay were not mutated by this worker.

## Remote-camera PVS reference audit and current exclusion

OpenBLOPS server_mp/sv_snapshot_mp.cpp2091+ uses copied playerState origin plus
viewheight/lean for visibility, without a camera entity branch. This is not proof
that native C1 should substitute its linked camera origin.

Local IW4 iw4mp.pdb public symbol resolves SV_BuildClientSnapshot4a6b70, matched
against iw4x.exe. Its shared snapshot pipeline differs materially:
- 4950e0 invokes628460 for a common captured entity set.
- 628480..6284cb includes linked entities, excluding svFlags bit1 and clientMask
  all-ones, copying each complete state+clientMask record; no PVS-origin query.
- Writer629490 filters captured entities by recipient self, clientMask+fc, and
  linked-parent exclusion629420. Missiles are exempt from parent exclusion.
- 629420 follows captured parent references; no camera-position/PVS calculation.
This supports auditing native recipient-selection architecture, but does not
justify copying IW4 policy as proven C1 behavior. No C1 server snapshot producer
was recovered in this bounded pass. No guessed camera-origin or force-broadcast
patch was made.

More decisively for the current symptom, native mounted collision already calls
CODOL_BuildUnculledNativeClipMap (codol_sv_xmodel.c196). The builder assigns every
leaf cluster0 and supplies an all-FF visibility row. Actual read-only native
PID104024/baseac0000 capture matched G_GetFogOpaqueDistSqrd's absolute-load/ret
instructions; at level.time416500 its returned field is FLT_MAX
(3.4028234663852886e38). Thus finite Killhouse player distances do not exceed the
fog limit. Camera versus body origin does not remove these enemies through the
current cluster/fog paths. This narrows out the proposed PVS explanation for this
state, rather than treating a missing camera branch as automatically defective.

Source remains unchanged. Needed enemy-box discriminator is an actual remote
snapshot: flag0x10, recipient/target mode gates, received entity validity, decoded
projection coordinates and camera. Passive capture does not require changing
user gameplay or forcing visibility.
