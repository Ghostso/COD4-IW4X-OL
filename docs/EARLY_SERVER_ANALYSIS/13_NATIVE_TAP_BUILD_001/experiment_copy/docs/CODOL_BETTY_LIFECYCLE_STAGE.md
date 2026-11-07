# Bouncing Betty lifecycle stage

Staged source: obj/equipment-stage/maps/mp/equipment/_bouncingbetty.gsc.
Primary reference: https://github.com/plutoniummod/iw5-scripts at
42f3db22261febd7180075842e250d2e0f3d0507, maps/mp/gametypes/_weapons.gsc
spawnmine/minethrown/mineproximitytrigger/minebounce/mineexplode and _damage.gsc.
Decompiled-source attribution retained. No live script edits or native changes.

## Implemented staged lifecycle

Native missile settles, then script_model replaces it on the traced ground.
Native trigger_radius arms after2seconds (radius100,height20). Enemy movement
and DamageConeTrace gate triggering; click precedes0.3second grace (3seconds for
specialty_delaymine). Native moveTo/rotateVelocity implement the64unit pop with
0.7second motion and0.65second deceleration. Explosion follows at0.65seconds.
Tagged spin/explosion effects and native positional sounds use verified shipped
identities. RadiusDamage includes owner/attacker, MOD_EXPLOSIVE, and actual
bouncingbetty_mp weapon identity. Radius/inner/outer use C1 WeaponDef256/100/70,
not IW5 script maximum210.

Owner pickup restores stock. Owner/team/disconnect/match cleanup and configured
spawn cleanup delete pickup/armed trigger alongside model. Placement count uses
existing scr_maxPerPlayerExplosives policy. All deletion dispatches independent
level-thread destroyNow, so notifying death cannot kill cleanup through caller's
endon. Damage listener exits after scheduling explosion; proximity is ended by
mine_destroyed. Triggering ends damage listener before the delay/pop path.

## C1 model/FX verification

Installed client_shipRetail/chinese/common_gametype_mp.ff asset4138(type28):
embedded XModel header at blob+21000, inline name at+21360:
projectile_bouncing_betty_grenade. Header size0x168 agrees native C1 model loader
4bbb80/codol_xmodel_skeleton.c. Header name pointer and bone-array pointer(+2c)
are FFFFFFFF, bone count7/root count1. Inline bone IDs resolve zone script pool:
24tag_origin,715tag_wobble,102tag_fx,716tag_fx_spin1,717tag_fx_spin2,
718tag_fx_spin3,719tag_fx_spin4. Thus every tagged FX target in stage exists.

Same zone FX assets9588 impacts/bouncing_betty_launch_dirt,
9589 dust/bouncing_betty_swirl,9590 explosions/bouncing_betty_explosion.
Asset9590's display-name heuristic is unreliable; its blob contains exact inline
explosion name. common_mp.ff sound3316 grenade_explode_metal;3331mine_betty_click,
3332mine_betty_spin. No guessed FX indices or replacement assets.

## Native support verified by source

Existing registered methods: moveTo, rotateVelocity, setCanDamage, makeUsable,
disable/enablePlayerUse, getVelocity(player-only), getAmmoCount, radiusDamage,
getGroundPosition, DamageConeTrace and standard spawn/FX/sound methods.
The stage only admits players to proximity before calling player getVelocity;
no missing generic getEntityVelocity stand-in needed.

GScr_EntityRadiusDamage resolves entity receiver and forwards to native internal
radius routine. That routine reads optional attacker(index4), means-of-death5,
and weapon-name6, resolves weapon via G_GetWeaponIndexForName and forwards it
to G_RadiusDamage. Seven-argument call is supported. Timing worker's extended
tenth damage notification argument supplies weapon filters used by the stage.

## Required parent integration BEFORE deployment

1. Install staged file then call maps\mp\equipment\_bouncingbetty::init()
   once per map from existing _weapons::init before connected listeners start.
2. At player damage callback, with actual weapon/inflictor/victim locals, apply
   IW5 _damage.gsc1243..1247: if weapon==bouncingbetty_mp and staged
   damageHeightPassed(inflictor,victim)==false, return without damage. For accepted
   damage halve integer amount when crouch or prone. Staged helper contains the
   reference +/-46height test and stance-center offsets32stand/24crouch/10prone.
   No claim of correct avoid-by-prone behavior until this callback integration.
3. Deploy with reviewed native10argument damage notification change, then map
   restart for precache/listener setup. Parent handles build/run validation.

No extra native shared-file edits needed for method availability. Still omitted:
friendly/enemy mine beacon, bombsquad highlight, bespoke mine killcam object and
statistics feedback. Core deployment/trigger/pop/damage/cleanup is implemented
in stage. No runtime success claimed; no tests/build/process/UI actions performed.
