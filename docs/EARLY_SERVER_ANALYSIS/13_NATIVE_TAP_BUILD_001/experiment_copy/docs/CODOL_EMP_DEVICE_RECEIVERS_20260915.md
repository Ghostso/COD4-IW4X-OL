# EMP device receiver stage

Source-only changes under obj/emp-device-stage; no live edits, builds, tests,
runtime input, new assets, or new radius scans. Merge staged hunks into current
sources rather than replacing other pending _weapons changes.

C1's mounted emp_grenade_mp produces radius512 and inner/outer damage1/1.
The existing native radius-damage dispatch already supplies the affected device
and the tenth damage notification argument identifies the actual weapon.
CODOL equipment notification wrappers validate weapon indices and protect
against entity deletion/reuse after script notification. The appropriate fix
is in the receiving scripts, not a second projectile proximity pass.

## C4 and claymore

Both start _weapons::c4Damage. Its retained `damage < 5` rejection, originally
intended to ignore concussion grenades, also discards actual C1 EMP damage1.
Primary IW5 reference obj/reference/iw5-scripts/maps/mp/gametypes/_weapons.gsc
c4damage:1730 instead reads all ten arguments and excludes exact concussion,
smoke, and flash weapon names. EMP consequently enters the existing normal
detonation path.

Stage consumes the tenth weapon argument and uses those exact exclusions.
Friendly-fire/attacker filtering, pickup closure, explosion frame staggering,
chain/penetration metadata, destruction credit and detonate(attacker) remain
unchanged. This is IW5-based utility grenade behavior using actual C1 weapon
identity/damage, not a claim of recovered C1 script code.

## Sentry

The retained vendor _autosentry::sentry_handleDamage consumes only five
arguments and would subtract ordinary EMP damage1 from buffered turret health.
IW5 _autosentry::sentry_handledamage explicitly treats emp_grenade_mp as
maxhealth+1 damage, invoking the normal destroyed-killstreak path.

Stage consumes the tenth weapon argument and makes accepted EMP damage lethal
after the existing friendly-team rejection. The existing lifecycle still owns
mission/XP credit, death notification, turret disabling, owner clearing,
destroyed model, FX/sound and eventual deletion. No substitute model/controller
was added. This supplies one missing receiver rule; it does not certify every
existing sentry builtin or asset/controller path as complete.

## Deliberate scope limits

Current Betty damage already accepts enemy EMP damage (excludes its own weapon
and smoke) and enters its existing explosion path. No duplicate listener added.
IW5 scrambler damage has no special instant-kill EMP branch: it accumulates
ordinary damage after excluding concussion/smoke/flash. No unsupported blanket
instant-destruction rule was invented for scramblers, helicopters, radar,
vehicles, or not-yet-implemented devices. Their distinct EMP policies remain
separate work. Existing eight-second emp_damage notifications from
flash/concussion are also separate from EMP grenade weapon damage.
