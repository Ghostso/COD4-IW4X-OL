# ExtraAmmo48 / ExtraExplosive93: bounded implementation audit

Resumed after the user's pause, 2026-09-14. Read-only source investigation;
no native helper or staged gameplay change added without verified units.
No tests, builds, launches or process changes.

## New local primary reference

`D:/CoD/CODOL Builds/Warfare2Client/DevData/devraw/maps/mp/gametypes/_class.gsc`
lines515..527 contains the same IW4 extra-ammunition behavior already present
in the native server overlay: `specialty_extraammo` grants `giveMaxAmmo` to
the primary and to a non-projectile secondary. The accompanying devraw
`mp/perktable.csv` identifies the perk as extra ammunition magazines; it has
no numeric CoDOL modifier48/93 effects. This grounds the existing IW4 policy,
but does not identify the meaning of CoDOL's number30.

## Existing evidence retained

Selected CoDOL upgrade19 contributes numeric modifier48 value30 and boolean
modifier93. Co-op rows can contribute modifier48 value6. The ability table
provides neither a default nor a unit for48. Python
`perks_support.py::extra_ammo_mult` explicitly calls its interpretation as
reserve percentage **INFERRED**. Its self-check repeats that caveat; it is
not independent engine evidence.

OpenBLOPS native ammo and item sources provide ammo registration, capacity and
pickup behavior, but the bounded search found extraammo names only in perk
registration, not a numeric30 or extra-explosive grant consumer. No equivalent
modifier93 count or eligible equipment class rule was established. A direct
C1 ability-word access survey likewise did not locate a fixed93 consumer;
this does not prove none exists, because server scripts/generic accessors may
own the effect.

## Current native inventory behavior

`scripts/codol/maps/mp/gametypes/_class.gsc` retains the grounded IW4
giveMaxAmmo policy. Profile equipment is granted separately through
`codol_giveEquipment`: giveWeapon then giveStartAmmo, followed by the selected
offhand-slot assignment. There is no selected93 increment in that path.
Blindly appending +1 could affect launchers, plantable devices, tactical
insertion or shared ammo pools without verified eligibility/cap behavior.

ExtraAmmo48's numeric units and ExtraExplosive93's grant quantity/coverage
therefore remain missing implementation evidence. Adding a percentage/round
conversion now would silently replace existing verified behavior with a
guess. No helper with fabricated defaults or empty support was introduced.

## Concrete next integration boundary once semantics are chosen

Use the actual selected native perk effects, after weapon/equipment creation
and initial-ammo seeding. Apply grants once per spawn, respect shared ammo
indexes and existing native ammo caps, and avoid applying them to both
shared-pool weapons independently. Replace the old extraammo MaxAmmo calls
in the same change if modifier48 becomes their authoritative replacement.
Keep data-driven units distinct from an explicitly approved IW4-based fallback
policy; never describe that fallback as recovered CoDOL behavior.

## New shipped localization evidence (resumed bounded audit)

Fresh verified archive reads recovered `PERKS_DESC_SCAVENGER_PRO` from
localized_code_post_gfx_mp (type27 localize, inline value/name):

> 从敌人尸体上获得补给+增加破片及粘性手雷起始携带量（但无法补给这些手雷）

Meaning: resupply from enemy corpses, plus increased **initial** carrying
amount for fragmentation and sticky grenades, but those grenades cannot be
resupplied. Base `PERKS_DESC_SCAVENGER` says only resupply from enemy corpses.
No changed definition of these keys appeared in patch_localized_code_post_gfx_mp.
This newly grounds93's initial-only scope and frag/semtex eligibility, but
not its numeric grant quantity. It specifically contradicts the current
IW4-derived scavenger loop incrementing every offhand's clip by1.

The actual C1 native-family enum values also rule out a broad enum shortcut:

| Asset | C1 type340 | class344 | offhand354 |
|---|---:|---:|---:|
| frag_grenade_mp / frag_grenade_short_mp |1|6|1|
| semtex_mp |1|6|5|
| white_phosphorus_grenade_mp |1|6|1|
| c4_mp |1|6|5|
| throwingknife_mp |1|9|4|
| flash_grenade_mp |1|6|3|
| concussion_grenade_mp |1|6|2|

Thus offhand1/5 or grenade-class filtering would also discard unrelated
weapons. Proposed parent-owned `_weapons` patch resolves the existing
`codol_getWeaponBaseName(offhand)` native accessor, skips the exact frag,
short-frag and semtex base identities above, then leaves other offhands under
the current policy. That accessor decodes recipe base IDs and preserves plain
names; `_utility::getBaseWeaponName` instead truncates at underscores and must
not be used here. No generic whitelist or new native method is needed.

Co-op row83 `specialty_coop_extra_ammo` has modifier48 value6, name
`PERKS_EXTENDEDMAGS`, description `PERKS_DESC_EXTENDEDMAGS`. Its actual localized
text is `每个弹夹拥有更多的弹药`: more ammunition in each magazine. This does not
prove the numeric6 unit or even that this reused description matches the
server consumer, but reinforces that reserve-percent interpretation is not
established. MP extraammo19's localized description contains no numeric30.
No source edit fabricating48 units or93 initial quantity was made.
