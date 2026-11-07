# IW5 equipment lifecycle adaptation (staged)

Primary reference: https://github.com/plutoniummod/iw5-scripts
Commit42f3db22261febd7180075842e250d2e0f3d0507; local read-only clone under
obj/reference/iw5-scripts. Repository marks scripts as IW5 source decompiled
by xensik/gsc-tool. Retain attribution in adaptations.

## Reviewable scrambler increment

Staged obj/equipment-stage/maps/mp/equipment/_scrambler.gsc implements actual
missile->script_model deployment, makeScrambler owner publication, one deployed
unit per owner, native damage listener/100health budget, owner-only use/pickup,
three-second beacon, death/disconnect/team-change/match-end cleanup. The native
missile remains the authoritative mover until settled; no proxy mover, polling
physics, memory patch or hidden fake jammer replaces it.

Reference _scrambler.gsc monitors grenade_fire then missile_stuck, validates
placement within40units using a downward trace, spawns script_model, assigns
owner/team, enables damage, calls makeScrambler, and deletes original missile.
The adaptation consumes native stationary instead: our BounceMissile producer
emits it exactly on moving->settled transition. Native ownership/damage/use and
snapshot methods already exist. No extra native methods required for this batch.

The IW5 refund branch erroneously reads trophy_mp ammo when restoring scrambler;
staged code restores its own stock. No unnecessary give/perk/offhand-class change
is made when equipping classes; class code already grants selected equipment.
Pending deployment is cancelled on owner death/disconnect/team change, so a
missile cannot activate for a subsequent life of the same owner. An explicit
pickup ownership check covers clients joining after initial use-mask setup.
Undefined world-damage attackers bypass the retained friendlyFireCheck wrapper,
which otherwise dereferences attacker.team without an undefined guard.

## C1 shipped asset corroboration

Reference zone client_shipRetail/chinese/common_gametype_mp.ff under the installed
Call of Duty Online1.1.1.13 directory:
- scrambler type28 asset4137 contains inline weapon_jammer model name at blob+226855.
- weapon_jammer_bombsquad occurs in type4 asset9224.
- scrambler_beep is sound asset9686.
- Betty type28 asset4138 contains projectile_bouncing_betty_grenade at blob+21360.
- Betty bombsquad model asset9586 and trigger model9587 are present.
- Betty launch/swirl effects assets9588/9589 are present.
These are shipped identities; no model substitution or generated effect index.

## Parent deployment integration

After reviewing staged source, install as scripts/codol/maps/mp/equipment/_scrambler.gsc.
In existing maps/mp/gametypes/_weapons::init, before its player-connect waiters
are started, call maps\mp\equipment\_scrambler::init(); exactly once per map.
The new init starts its own connected listener; it does not replace the existing
C4/claymore listeners. No standalone script autoload assumption is made.
Map restart after deployment is needed for precache/connect listeners. No live
scripts were changed by this worker, and no build/restart/test was performed.

## Deliberately unclaimed work

No runtime verification yet. Destruction cosmetics, friendly head icons/bombsquad
attachments, and IW5's additional proximity blind-eye perk behavior are not in
this increment; the actual C1 makeScrambler entity remains the radar-jamming
producer. Betty source is recovered in IW5 _weapons::spawnmine and related
mineproximitytrigger/mineexplode routines, but that lifecycle is not implemented
by this scrambler increment. Native arming/mover/damage semantics still need
review before staging its deployment. This is a real scrambler lifecycle stage,
not a claim that all equipment behavior is complete.
