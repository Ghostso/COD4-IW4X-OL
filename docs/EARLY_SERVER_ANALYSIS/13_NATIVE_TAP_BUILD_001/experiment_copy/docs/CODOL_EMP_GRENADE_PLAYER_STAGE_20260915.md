# EMP grenade player effect stage

Source-only staged increment under obj/emp-grenade-stage. No live script edits,
builds, tests, client writes, or process changes. Parent review required.

## Evidence and missing consumer

C1 marketplace item1206 is emp_grenade_mp (equipment/special). The shipped
common_gametype_mp weapon definition has radius512 at778, inner/outer damage1/1
at780/784 and fuse1000ms at654. Existing native projectile imports populate
these fields; native splash damage therefore supplies the affected-player
callback without an invented polling/distance scan.

The live overlay lacked _empgrenade initialization and the player damage
notification. Its only empExplodeWaiter invocation covers flash/concussion,
with the distinct eight-second equipment-disable notification. That path is
not the personal EMP effect.

Primary reference source available locally:
obj/reference/iw5-scripts/maps/mp/_empgrenade.gsc and
maps/mp/gametypes/_damage.gsc:1252. The latter notifies emp_grenaded for EMP
damage except MOD_IMPACT, preserving normal damage handling afterward.
The reference applies ten seconds of EMP and one second flashbang shellshock,
refreshes repeated hits, handles friendly-fire reflect/share, clears on death,
and preserves global EMP when the personal effect expires.

Native SetEMPJammed already publishes C1 ps+10 bit400. C1 setter549826/549832
and isempjammed consumer5e2fcb establish that field. No new client assets are
introduced: flashbang_mp is already precached by the active flash subsystem.
Ten-second duration and friendly-fire policy are explicit IW5 adaptations,
not claimed recovered CoDOL script constants.

## Staged changes and lifecycle

- New _empgrenade registers one per-life listener, refreshes one timed effect,
  retains selected-player receiver rules, and emits emp_hit on valid attackers.
- _damage emits the reference notification before normal damage processing;
  it does not replace blast damage or multiply it.
- _weapons initializes the subsystem. _utility::isEMPed includes its personal
  state so reward/device eligibility observes the actual effect.
- Overlay _emp preserves personal state when team/global trackers update the
  single native EMP flag. Personal expiry likewise preserves global state.
- Spawn restart cancels old listeners/timers, death and team/spectator change
  clear the effect, disconnect cancels entity-owned work, and game end clears
  personal state. Cleanup generation guards protect against cancelled nested
  waits resuming after a newer spawn. No account data is changed.

Scope is player EMP behavior. Device destruction/disable coverage, selected
EMP immunity provenance, exact C1 duration and live mixer/visual behavior are
not claimed complete. Existing specialty_empimmune check follows the reference;
no new perk ID or ability flag was fabricated. Reference challenge progression
and rumble are not required for the native jam lifecycle and were not invented.

Parent should merge the narrow staged hunks into current sources, especially
_utility/_damage/_weapons, which can receive independent ongoing fixes.
