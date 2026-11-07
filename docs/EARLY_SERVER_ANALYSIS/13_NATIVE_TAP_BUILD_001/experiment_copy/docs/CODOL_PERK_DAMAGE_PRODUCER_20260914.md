# Explosion and fall perk damage: producer evidence boundary

2026-09-14 bounded source/offline audit. No native implementation was added
because exact original MOD coverage and ordering were not established. No
tests, builds, process writes or UI changes were performed.

The selected MP table proves modifier60 explosive scale delta-0.5/default1,
and modifier52 fall scale delta-1/default1. The current native aggregator
therefore stores0.5 and0 respectively under its documented aggregation policy.
It does not establish where original damage code consumes these values.

## Python does not implement the claimed damage producer

`alpha0022/docs/perks_fix.md` explicitly proposes
`damage = int(damage * _pset.explosive_damage_scale())` for grenade-splash,
projectile-splash and explosive damage, followed by:
"no such path exists in game-server.py today — helper only".
The Python accessors return scalar values for display/consumption elsewhere;
they are not evidence of working engine coverage, rounding or ordering.

The overlay's `maps/mp/_utility.gsc::isExplosiveDamage` includes direct
`MOD_GRENADE` and `MOD_PROJECTILE`, both splash variants and `MOD_EXPLOSIVE`.
This is already broader than the Python document's proposed coverage.
`MOD_EXPLOSIVE_BULLET` is categorized as primary damage in that overlay.
Names alone cannot resolve whether modifier60 should affect these cases.

## Existing pipeline and duplicate-application risk

`maps/mp/perks/_perks.gsc::cac_modified_damage` currently computes legacy
explosive attack/blastshield damage adjustments, then other adjustments and
combat-high damage reduction, finally returning `int(damage + damageAdd)`.
It checks `specialty_falldamage` for falling, not the C1 selected upgrade22.
There is no demonstrated modifier60/52 consumer in this overlay.

OpenBLOPS `Game/Server/game_mp/g_combat_mp.cpp::G_DamageClient` applies hit
location scaling, truncates to integer, raises damage<=0 to1 and only then
calls `Scr_PlayerDamage`. It contains no flak-jacket/fall-damage modifier
consumer that could settle the missing C1 semantics. Applying fall immunity
before that minimum-one clamp would erroneously turn immunity into1damage.

A direct C1 first-word/second-word ability access survey found native
movement/weapon consumers, but no direct modifier52/60 mask consumer in the
bounded scan. This is not proof that none exists: server-only values may be
script-owned or accessed through generic facilities rather than fixed masks.

## Required next evidence before implementation

Locate the original damage-script aggregation/finish path or its actual C1
native producer, then establish eligible MODs, explosive bullet handling,
direct versus splash handling, cap/minimum placement and integer conversion.
Implement one native consumer at that reviewed boundary, using authoritative
effective ability values. Coordinate the old script modifiers so the same
effect is not multiplied independently in radius damage and final damage.
Do not copy native MOD integers from C1 until the broader enum migration is
complete; C1 suicide13 versus retained suicide12 demonstrates the mismatch.

No stub or names-only perk-damage implementation was introduced. These
consumers remain missing; the stored ability values are not functional
damage support by themselves.
