# Equipment lifecycle audit - 2026-09-14

Scope: native scrambler and bouncing-Betty deployment. Source/reference reads
only. No device lifecycle implementation is claimed.

## Present and missing

Selected equipment now resolves profile IDs and grants native weapons. Native
makeScrambler has a real owner/flag producer plus archived snapshot publication.
It requires a scriptmover. A thrown/placed equipment projectile is a missile;
calling the method directly on that receiver is invalid.

The mounted retained scripts/codol/maps/mp/gametypes/_weapons.gsc initializes
C4/claymore tracking, grenade notifications, and bombsquad models. It has no
scrambler/Betty deployment handler. Previous exhaustive rawfile/script audit is
in CODOL_EQUIPMENT_SELECTION_AUDIT_20260914.md. Python's beacon path does not
perform device activation and its launch parameters contradict shipped assets.

No scrambler/Betty native special-case producer was found in OpenBLOPS server
code. C1 plain string lookup does not contain scrambler_mp/bouncingbetty_mp
literals; this does not prove there are no protected or asset-driven consumers.
No authoritative missile-to-scriptmover conversion call has yet been recovered.

## Concrete prerequisite candidate: stationary notification

OpenBLOPS Game/Server/game/g_missile.cpp BounceMissile ends its settled-projectile
path with Scr_Notify(ent, scr_const.stationary, 0), line2564. This occurs after
stopping, orienting, and optional platform attachment. MissileImpact also emits
stationary variants with impact arguments on relevant branches; those distinct
argument forms must not be collapsed into guessed generic notifications.

Retained src/asmsource/_g_missile.asm BounceMissile settles/orients at label
BounceMissile_220, performs grenade-danger notifications, and reaches its
settled return. It has no stationary string/notification producer. A narrow
zero-argument settle notification is a concrete T5 compatibility prerequisite.
C1 itself registers the string stationary at 0x578551; its interned constant is
stored at 0x24ee1fc at 0x57856a. Its actual C1 missile notification producer has
not yet been located, so do not assert full C1 argument parity from the constant.

A proposed native helper can emit that notification from the settled return,
with shared assembly integration coordinated through parent. It is deliberately
not a substitute for device activation, pickup, damage, destruction, timing, or
owner-disconnect policies. No speculative device proxy or fabricated lifecycle
was added during this audit.

## Implemented native prerequisites (parent review pending)

Added codol_equipment_lifecycle.c stationary notification, called from retained
BounceMissile only when entry position trajectory was moving and exit trajectory
is stationary. Strong airborne-bounce return1 does not qualify. Entry state is
stack-local, so no slot-reuse/reset side table exists. The notifier checks inuse,
useCount and missile type after resuming waiters. Internal return2 makes both
native MissileImpact direct callers return before queuing further missile events
against deleted/reused/converted receivers. String references are released.
Bounce stack allocation grew16bytes; callee-saved registers remain preserved.

Added codol_missile_collision.c metadata-backed C1 mode and target-policy helpers.
The mounted weapon stores C1 stickiness in native metadata, but retained collision
code read an unpopulated IW3 +0x5a4 field. BounceMissile now caches C1 mode, handles
all1/all-no-sentients2 separately from ground3/ground-with-yaw4, and preserves
sentient/projectile exclusions through actual native entity identity. Both stale
G_RunMissile mode consumers now read metadata as well. Attachment-relative modes
use existing C1-proven helper (modes1/2/5). Affected assembly restores caller-live
ground entity index after the cdecl helper. No IW3 enum is populated as a proxy.

T5 source supplies authoritative all/ground settle/orientation conditions.
Complete C1 flesh5 wall-embedding behavior remains outside this change; no claim
that the prediction helper implements authoritative collision was made. Device
activation/arming/pickup policies remain unimplemented. Parent owns integrating
rolling response, angular handling, and current rest-threshold dvar before build.

No worker tests/builds/restarts/process writes. Review and gameplay pending.
