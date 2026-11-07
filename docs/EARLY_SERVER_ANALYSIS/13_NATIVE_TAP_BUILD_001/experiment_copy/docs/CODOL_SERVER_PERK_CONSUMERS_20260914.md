# Remaining perk consumers: bounded audit

2026-09-14, source and offline C1 evidence only. No builds, tests or runtime
changes. Parent owns code integration. Audit was interrupted by the urgent
shellshock expiry regression; damage/ammo original producers remain open.

## Highest-confidence native gates

### Last Stand: ability8, not legacy perk bit7

C1 `51c1a8..51c21a` is the lethal-player-damage branch. It requires health<=0,
`client+3a38 == 0`, and `(ps[4d0] >> 23) & 1`. MSB-first ability numbering
makes this modifier8. It then sets client3a38=1, client3a3c=level.time+500,
and invokes callback562840. No numeric perk-duration read occurs in this
entry branch. Native `CODOL_LastStand_CanEnter` and the direct retained
`PlayerCmd_finishPlayerDamage` gate still read IW3 `ps.perks` bit7, whose
producer was replaced by C1 perk/ability storage. Both gates require repair.

Fresh verified inflation of shipped Chinese `code_post_gfx_mp.ff` confirms:
`specialty_pistoldeath` perk14 in perk3 contributes `modPistolDeath=10`.
Ability8 has no wire value slot, default0, minimum0, clientside1. Numeric
duration belongs to a separate lifecycle consumer, not the500ms entry grace.
Do not conflate this perk with deathstreak `specialty_finalstand`41, which
contributes server modifier59 `modFinalStandTime=20` instead.

### Martyrdom: ability21, not legacy perk bit6

C1 `5208a7` excludes damage MOD13. At `5208b7..5208c2` it requires
`(ps[4d0] >> 10) & 1`, hence modifier21. It looks up weapon stringc53cd0,
uses the selected definition's fuse654 at520909, constructs a small random
throw vector and calls grenade launch5309d0 at520952. The native retained
`_g_combat_mp.asm` legacy perk byte5fc mask40 must instead read C1 activation.
Preserve the surrounding exclusion, launch and lifecycle logic while changing
the gate; this evidence does not justify broad projectile rewrites.

## Verified selected MP table rows

`mp/coPerkStatsTable.csv` is92x22. Effects use pairs15/16,17/18,19/20 and flag21.
The ability table has97x7 columns ID/name/valueSlot/default/min/max/clientside.
Rows below were resolved from shipped tables, not inferred from perk names.

| Selected perk | Effects | Native consumer status at audit |
|---|---|---|
| flakjacket5, perk2 | ArmorExplosiveDamageScale60, delta-0.5, default1/min0 | No modifier60 damage consumer found |
| fastsprintrecovery22, upgrade1 | FastMantle9 boolean; FallDamageScale52 delta-1, default1/min0 | Old falling script checks different perk `specialty_falldamage` |
| extraammo19, upgrade1 | ExtraAmmo48 value30 (no declared default/min/max); ExtraExplosive93 boolean | Class script gives MaxAmmo for legacy extraammo, which does not establish value30 units |
| pistoldeath14, perk3 | PistolDeath8 value10/default0/min0 | Entry gate still legacy bit7; C1 mask verified above |
| copycat38, perk4 | CopyPerks57 boolean | Full copy lifecycle outside this bounded audit |
| combathigh39, perk4 | CombatHighTime58 value8 | Existing script damage branch exists; duration consumer not verified |
| grenadepulldeath40, perk4 | GrenadePullDeath21 boolean | Native legacy gate mismatch verified above |
| finalstand41, perk4 | FinalStandTime59 value20 | Distinct from PistolDeath8; full lifecycle not verified |

All four MP deathstreak rows38..41 have **column6 =4** in the shipped CoDOL
table. The old `mp/perkTable.csv` lookup is not the authoritative table source.

## Damage/ammo work still required

`scripts/codol/maps/mp/perks/_perks.gsc::cac_modified_damage` checks the IW4
names `specialty_explosivedamage` and `_specialty_blastshield` for explosions,
and `specialty_falldamage` for falling. It does not consume C1 modifier60/52.
Table-consistent current aggregation yields explosion scale0.5 and falling
scale0 for the above selected MP rows, but the exact C1 damage rounding,
MOD coverage and cap ordering were not traced in this pass. Apply effects at
one reviewed damage producer; do not multiply them independently in both
radius damage and the script callback.

`_class.gsc` calls giveMaxAmmo for primary/secondary with extraammo. Neither
that behavior nor the value's name proves that table value30 means rounds,
percent or clips. Exact C1 ammo producer evidence remains necessary before
replacing it or implementing ExtraExplosive93. Python is a lead, not proof.

OpenBLOPS reference files were located at
`Game/Server/game_mp/g_combat_mp.cpp`, `Game/Server/game/g_weapon.cpp` and
`Game/Shared/bgame/bg_weapons_ammo.cpp`; no T5 offset/enum equivalence is
asserted here. Last Stand and Martyrdom are the concrete immediate native
fixes, followed by reviewed explosion/fall damage modifier consumers.
