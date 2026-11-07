# C1 equipment slot ordering

## Verified shipped definitions

Fresh `zone_assets.inflate_ff(..., verify=True)` of the shipped Chinese
`common_gametype_mp.ff`, parsed as type28 assets, gives these signed/unsigned
integer-equivalent offhand classes at WeaponDef+354. Names were read from each
asset's inline name at+bfc, not assumed from old live weapon indices.

| Asset | Directory index | Offhand class |
| --- | ---: | ---: |
| frag_grenade_mp | 4073 | 1 |
| semtex_mp | 4082 | 5 |
| flash_grenade_mp | 4094 | 3 |
| smoke_grenade_mp | 4100 | 2 |
| white_phosphorus_grenade_mp | 4109 | 1 |
| claymore_mp | 4121 | 5 |
| c4_mp | 4134 | 5 |

Patched `patch_common_gametype_mp.ff` semtex asset608 retains class5. This is
important: asset class alone cannot determine every marketplace loadout group.
Semtex can be explicitly selected as lethal despite sharing class5 with C4.

## Native selection and input

At40c7e0 C1 reads the actual weapon's+354 class. For empty-slot eligibility it
groups1/4 with ps+32c,2/3 with ps+330, and5 with ps+334. Before each empty-slot
fallback, exact equality with the already-selected weapon is accepted
(40c82a,40c83c,40c84f). Explicit assignments therefore need not obey those
fallback class groups.

The actual input selection routine reads:

| Button mask | C1 playerstate slot | Address |
| --- | --- | --- |
| 4000 | +32c | 41cb44..41cb5a |
| 8000 | +330 | 41cb62..41cb78 |
| 10000 | +334 | 41cb80..41cba2 |

Each branch also checks the old button and current phase flags to require a
fresh press. The input mapping itself is verified, not inferred from Python.

C1's binding-name table atcd62c0 contains IDs5/6 `+frag`/`-frag`, IDs7/8
`+smoke`/`-smoke`, and IDs9/10 `+tact`/`-tact`. Strings are atc43a84,c46fa0,
c46f90 respectively. Table consumers492c07/492c0e use these names when reporting
binding changes. The exact dispatch from those binding IDs to the button bits
has not been traced in this pass; table adjacency alone is not that proof.

## Interpretation for native loadouts

The conventional C1 slot semantics, plus shipped flash/smoke and C4/claymore
classes, support ordering the marketplace loadout as **lethal, special,
tactical**. Existing Python/native policy `lethal,tactical,special` conflicts
with those conventional classes for both category2 and category3. Preserve
explicit lethal assignment for semtex rather than sorting every weapon by its
class. A category-order swap is distinct from changing input masks or the
snapshot slots, whose C1 correspondence is already verified.

No original official server GSC loadout setter was found in this bounded pass.
Thus this proves conventional class/input slots and the mismatch in inferred
category policy; it does not establish an undocumented universal restriction
against explicit cross-class slots. Parent owns the policy change and review.
No source edits, tests, builds, restarts or client writes were made here.
