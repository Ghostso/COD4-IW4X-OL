# Selected extra-ammo effects: current producer audit

The live class path applies selected perks before equipment initialization.
Therefore an ordering change is not justified for the missing extra-explosive
effect. _class.gsc::codol_giveEquipment calls giveWeapon then giveStartAmmo
for each profile equipment member. Primary and secondary extra-ammo handling
still calls giveMaxAmmo based on the specialty_extraammo selection.

Retained PlayerCmd_giveStartAmmo resolves the weapon and ownership, then calls
G_InitializeAmmo. That routine computes shared-pool shortfalls from the
definition's start ammo, calls Add_Ammo/Fill_Clip and follows owned alternate
weapons. It has no selected-ability read. It should not be changed to add an
arbitrary count or percentage without establishing the selected effect's units
and intended weapon categories.

The existing catalogue audit identifies ExtraAmmo48 value30 and the boolean
ExtraExplosive93. A cached C1 .text scan for direct ps+4d8/4db references found
state copy/reset sites, not a modifier93 consumer. Aligned inspection of
50d380..50d3b6 confirms the 50d398 hit copies all four ability words into
client state. This does not prove absence of an indirect or script consumer.

Next evidence needed: original script or native ammo-grant consumer defining
value30 units, eligible equipment and reserve/clip cap behavior. Keep this gap
open; default start/max ammo grants are not proof of complete selected perk
support. No source behavior change, automated test or live mutation in this audit.
