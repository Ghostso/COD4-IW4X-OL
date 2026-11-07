# Perk effects versus C1 perk IDs

## Confirmed integration gap

`CODOL_Scr_SetPerk` updates only `extension->perks` via `CODOL_SetPerk`.
The latter writes a perk ID to its table-selected slot. This is distinct from
`extension->abilities`: it neither sets modifier bits nor initializes numeric
ability values. A perk icon/ID therefore does not establish a functioning perk.

The overlay `_utility::_setPerk` calls this native method, records its local
`self.perks` membership and invokes the old per-perk callback. No overlay call
to `setAbilityModifier` or `setAbilityModifierValue` was found. Consequently
native movement/weapon consumers that correctly require C1 ability masks will
not see the selected perk's effect through this route.

## Shipped table evidence

Fresh, integrity-verified inflation of Chinese `code_post_gfx_mp.ff` and the
existing stringtable parser resolved both tables. Cross-table string hashes
were resolved only to known matching strings; unknown cells were not guessed.
`mp/coPerkStatsTable.csv` is92x22; effects begin at columns15/16,17/18,19/20,
and optional flag-only name21. Column8 declares the associated pro perk, not
proof that it is unlocked or should be awarded automatically.

| Perk ID/name | Slot | Effect in columns15/16 |
| --- | --- | --- |
| 3 specialty_fastreload | perk1 | modReloadSpeedScale, 1 |
| 7 specialty_lightweight | perk1 | modMoveSpeedScale, 0.1 |
| 10 specialty_quickdraw | perk2 | modADSSpeedScale, 0.5 |
| 17 specialty_fastmantle | upgrade1 | modSprintForceRecoverTime, 1 |
| 18 specialty_quickswap | upgrade1 | modWeaponSwitchSpeedScale, 1 |

In particular, the *name* `specialty_fastmantle` does not authorize setting
modifier9 `modFastMantle`. The actual shipped row chooses sprint recovery.

`mp/coAbilityModifiersTable.csv` is97x7. Columns0..6 are ID,name,value slot,
default,min,max,clientside. Verified relevant rows:

| Modifier | ID | Value slot | Default | Min | Max | Clientside |
| --- | ---: | --- | --- | --- | --- | ---: |
| modReloadSpeedScale | 1 | 1 | 1 | 1 | empty | 1 |
| modFastMantle | 9 | empty | empty | empty | empty | 1 |
| modWeaponSwitchSpeedScale | 22 | 11 | 1 | 0 | empty | 1 |
| modSprintForceRecoverTime | 33 | 16 | 1 | 1 | empty | 1 |
| modMoveSpeedScale | 42 | empty | 1 | 0 | empty | 0 |

Lightweight is therefore a server-only numeric modifier with **no** C1
abilityValues slot. Publishing bit42 alone cannot express its0.1 magnitude.
Native server-owned modifier storage and a movement producer are required.
The current native ability reader retains defaults only for slotted values,
and its value setter rejects slotless modifiers, so that API cannot currently
carry this parameter.

## What C1 producers establish

`SetAbilityModifier` initializes a slotted default through403090 before setting
the MSB-first bit. At4030d9..403103 the initializer looks up the modifier name,
reads ability-table column3 and stores the parsed float in the resolved value
slot. `SetAbilityModifierValue`5189cb..5189ff stores its supplied float directly;
it does not add a table default, set the mask, or clamp a range.

Existing C1 consumers independently establish that reload/switch timers use
the stored scale (41abb6/41ac09), and ADS rate uses its stored scale41875b.
These support the intended effect units but do not prove the higher-level
perk aggregation algorithm.

Python `perks_support.py` uses `clamp(default + perkValue,min,max)`. Its own
listed evidence cites those consumers, not an original aggregation producer.
For example default1 plus fastreload's1 gives2x while passing the row's1
straight to the native value setter gives no acceleration. Additive/clamped
aggregation is a strong table-consistent implementation lead, but remains
separate from the directly verified C1 setters. Original server GSC aggregation
was not located in this bounded pass; do not present that missing proof as
established native behavior.

## Required implementation boundaries

A native perk-effect layer needs selection/upgrade ownership, aggregation of
all active effect rows, and recomputation on replacement/unset/clear/spawn.
It must preserve independently script-owned ability modifiers rather than
clearing the entire ability state when a perk changes. Server-only numeric
effects need native storage/consumers, while slotted effects need both mask
and numeric publication. Boolean effects must not be forced into float slots.

The old lightweight callback currently assigns `moveSpeedScaler=1.07` in
`_perkfunctions.gsc`, differing from the table's0.1 modifier. Once table-based
movement is implemented, that callback must be coordinated so both producers
do not multiply or overwrite each other. This is an integration issue, not
evidence for changing the shipped table.

No shared source, build, tests, processes or runtime state were changed by this
audit. Source-written, table-verified, and original-producer-verified findings
are deliberately distinguished above.
