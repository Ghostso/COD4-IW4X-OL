# Playerdata-driven character composition

Player appearance must be composed from the player's selected character record
and equipment. A single stock model or a fixed team model is not the complete
CoDOL player appearance path. This requirement includes both the third-person
body and first-person arms/hands.

The alpha0022 reference is `model_configstrings.py`, especially
`resolve_character`, `player_model_publish`, and the viewhand helpers.
`resources/mpdata.playerclass.md` provides explicit multi-part fixtures.
Read these as evidence with their stated measured/inferred distinctions; do
not copy the reference's live profile or its hardcoded geometry census as a
universal default.

The v220 public playerdata schema has 48 `characterClasses`, each containing
20 short item slots, with faction selectors `tfCharacterIndex`,
`scCharacterIndex`, and `zmCharacterIndex`. The Python reference's introductory
slot order is superseded by the directly verified C1 map below.
The native implementation should resolve fields through the mounted schema,
not introduce unversioned absolute offsets. The selector-to-record relation
is marked inferred in the reference's introductory analysis and still needs
the corresponding C1 reader verified.

Item IDs resolve through marketplace and `mp/cocharitems/<part>.csv` tables.
Those tables distinguish gender, faction, camouflage and separate third-person
and first-person models. `pat` selects a material, not a body XModel. Zero-slot
defaults and missing-geometry behavior must follow the character rules rather
than silently picking an unrelated model.

The reference documents C1 `CG_NewClientInfo` at 0x46cb17..0x46ce34 and model
registration at 0x444290. It reports a base model plus 16 attachment slots,
with registration stopping at the first empty attachment model. The engine's
fallback order uses trousers (`fpa`) as the root, followed by boots, jacket,
hands, vest, head, headgear and pads. This fallback is evidence for assembly
order, not proof of the complete profile selection algorithm. Empty attachment
tags as the shared-skeleton merge mechanism are explicitly inferred there.

## Native gap

`CODOL_OverlayServerClient` in `src/codol_sv_assets.c` currently translates the
retained IW3 base model and only six retained attachment slots. It does not
resolve `characterClasses` or assemble the player's selected CoDOL outfit.
Expanding a loop alone would read beyond the retained ABI. A separate native
CoDOL appearance state must support the full composition, publish model names
before their snapshot indices, and clear removed parts on outfit changes.
First-person arms/hands need the corresponding playerstate mapping as well.

Validation must cover distinct player profiles, faction selection, defaults,
model/material separation, outfits exceeding six parts, contiguous attachment
publication, removal in delta frames, and matching first-person arms/hands.
Synthetic field tests alone will not establish correct C1 rendering.

## Sixteen-part semantic overlay

`codol_client_appearance_t` and `CODOL_OverlayClientAppearance` now provide
independent storage and publication into all sixteen CoDOL client-state
model/tag pairs. The operation validates the entire composition before changing
the destination, rejects gaps and dangling tags, and clears every removed part.
It preserves unrelated team/perk/vehicle fields and the client number. The
retained IW3 arrays and their ABI remain unchanged.

`tests/test_codol_client_appearance.c` passed 32-bit ASan/UBSan: all sixteen
parts, shrinking an outfit to six, field reachability for baseline and delta,
serialization, bounds, gap rejection and failure atomicity. This is the native
output primitive for the pending playerdata composition producer. It is not
yet called by the live appearance collector and does not establish profile
selection, model loading, or visual correctness.

## Character profile reader

Static inspection of the local C1 executable on 2026-09-08 found the faction
selector reader at 0x68f890. It indexes the string pointers at 0xccc93c
(`tf`, `sc`, `zm`), formats `%sCharacterIndex` (0xc74854), and reads the resulting
single-field path with 0x590670. The character slot reader at 0x590d00 constructs
the four-part path `characterClasses`, decimal record index, `slots`, decimal
slot index. The cache loader at 0x590dc0 iterates twenty slots per record and
48 records, storing each record at a 0x70-byte cache stride. These addresses
refer to the same 1.1.1.13 executable identified in CODOL_TEAM_THERMAL.md.

`CODOL_ProfileCharacter` now reads the faction selector and twenty stored item
IDs using the mounted schema interface, with no fixed profile byte offsets.
It requires a complete profile whose version/checksum matches exactly one
definition, verifies short field types and array bounds, and leaves output
unchanged if any slot cannot be read. Zero items remain zero for subsequent
character-default resolution; item validity is not inferred at this layer.

The synthetic schema test `tests/test_codol_profile_character.c` passed 32-bit
ASan/UBSan for three faction records, record 47, all twenty slots, invalid
selection, malformed/truncated layouts, profile size and header mismatch.
Mounted-profile integration and the item-to-model resolver are still pending.

## Measured character variant selection

C1's actual coCharItems matcher was located at 0x729090 through callers using
`mp/coCharItems/%s.csv` (0xc821d4). This supersedes the reference Python
`_variant_score` approximation for this path:

- 0x61ed00 finds the last case-insensitive item-name row; 0x729090 scans backward
  while column 0 still exactly matches the item. Other column-1 kinds are skipped.
- Gender must match (`m` or `f`) or be shared (`s`), starting at -1 or -2.
- Faction must match (`tf`, `sc`, `zm`) or be shared (`ss`), adding 2 or 1.
- The three-byte camouflage must match or be `sss`, adding 2 or 1.
- For kind `model`, a substring match of the requested skin in column 3 adds
  100. This is not limited to ties and does not require an underscore prefix.
- A strictly greater score replaces the selected row; reverse traversal means
  the last row wins ties. No eligible row returns empty. The result is column 3.

`CODOL_CharacterVariant` implements that row-selection path over an explicit
native stringtable. It returns the borrowed column-3 value and selected row,
allowing callers to inspect other columns separately once their consumers are
verified. It rejects short/missing variant cells and invalid native inputs
rather than reproducing unsafe retail reads. It does not prefilter by geometry
or silently accept an incompatible faction as the Python approximation does.

The 32-bit ASan/UBSan test passed exact/shared eligibility, skin priority over
specificity, reverse-order ties, contiguous item groups and malformed inputs.
This adapter is not yet connected to the live appearance producer. Selecting
character defaults, resolving marketplace IDs, first-person model consumers and
loading/publishing the assembled parts remain required.

## Mounted-table and model checks

`codol_checkcharvariant <table> <item> <m|f> <tf|sc|zm> <camo> <skin>` now
performs the same selection against a mounted native stringtable, without
editing profiles or publishing appearance. The Windows build passed
(`/tmp/sh1x-character-mounted-win32.log`). An isolated native Bog server on
UDP 17783 produced these results from the actual assets:

| Item and request | Selected row | Model |
| --- | --- | --- |
| fja_ghost, m/tf/urb/wht | 32 | fja_ghost_tf_m_00 |
| han_typea, m/tf/urb/wht | 50 | han_typea_ss_m_09 |
| fpa_soccomjeans, m/tf/urb/wht | 1 | fpa_soccomjeans_tf_m_00 |
| heg_swat, m/sc/urb/wht | 29 | heg_swat_sc_s_15 |
| knp_tactical, m/sc/urb/wht | absent | no compatible variant |
| boo_zmcowboy, m/zm/sss/wht | 14 | boo_zmcowboy_zm_m_00 |

The four selected MP models also passed `codol_checkmodel`, including skeleton,
geometry, materials, mesh, core and complete native model loading. The ZM boots
were absent from the mounted MP asset set despite their valid table row.
This confirms that row selection cannot replace an asset-availability check;
it does not establish whether the model loads under the appropriate ZM zones.
The diagnostic server was stopped. C1 and the Python lobby remained responsive.
These checks do not prove assembled character rendering or live profile routing.

## Marketplace-to-model adapter

`CODOL_CharacterItem` now resolves a stored numeric item ID through an explicit
marketplace table. C1 helpers 0x728750, 0x7287c0 and 0x728830 format the ID as
decimal, use 0x61ed00 to find the last matching column-0 row, and read columns
1 (name), 2 (type) and 3 (group). The adapter preserves that last-row behavior;
zero-padded ID text is not silently treated as the canonical numeric key.

`CODOL_LoadCharacterItemModel` joins the mounted marketplace to
`mp/coCharItems/<group>.csv` and calls the measured variant selector for kind
`model`. It does not substitute the profile slot's part name for the marketplace
group, return material entries as XModels, or infer defaults for zero/missing
items. It validates group path components and preserves the caller's output
on absence or failure. Returned names borrow the mounted asset lifetime.

The standalone 32-bit ASan/UBSan test passed duplicate-row precedence,
canonical ID lookup, part-table routing, incompatible variants, material
exclusion, malformed group rejection and output preservation. Its loader is
mocked; this does not add a claim of mounted end-to-end outfit validation.
The live appearance producer, character-default resolution and geometry checks
remain pending.

## Explicit character-default merge

C1 0x60d020 visits eighteen 32-bit composition slots. For each zero it resolves
the supplied character item with 0x728750, finds that name in column 0 of
`mp/coCharacterDefTable.csv`, reads column `3 + slot`, and converts the default
item name back to an ID through 0x7286e0. The latter searches marketplace
column 1 using the last matching row and converts column 0 with atoi. Only
positive IDs replace zero; existing nonzero selections survive.

`CODOL_ApplyCharacterDefaults` now implements that explicit-table operation.
It takes an explicit character item and eighteen slots, without assuming that
the twenty-slot profile record can be passed directly as the composition array.
Malformed tables or out-of-range positive IDs fail atomically; absent character
rows or unresolved defaults preserve the corresponding values. Its synthetic
32-bit ASan/UBSan fixture passed all eighteen slots, preserved overrides,
reverse case-insensitive item lookup and invalid-ID rollback.

The callers at 0x60d367/0x60d41c and 0x6986b6 obtain the identity from composition
slot 4. They then call 0x60d090 using `mp/coChestRigs.csv` and apply an additional
visibility rule through 0x60d220. Those subsequent rules and the profile-to-
composition conversion still need verification before live integration.

## Weapon-dependent chest-rig adjustment

`CODOL_ApplyCharacterChestRig` implements 0x60d090: resolve composition slot 5
to an item name, scan `mp/coChestRigs.csv` forward for exact column-0 matches
whose column `2 + selector` equals the literal `1`, then resolve column 1 to a
marketplace ID and replace composition slot 15. The loop continues, so the last
active row wins. A matching row with an unresolved replacement clears slot 15;
no active row preserves it. Invalid tables/IDs fail without partial mutation.

The selector owner is now partly verified: C1 0x611ba0 loads the named weapon
asset, reads its class at +0x344, and dispatches through the table at 0x611c38.
Classes 0,1,2,3,4 set global 0x7e4d690 to 0,4,2,1,3 respectively. Other classes
leave it unchanged. `CODOL_ChestRigSelector` captures that mapping with explicit
output ownership; it does not infer the player's equipped weapon.

The 32-bit ASan/UBSan fixture passed weapon-class mapping, column selection,
exact activation flags, last-row replacement, preservation without a match,
clearing unresolved replacements and atomic invalid-ID handling. The mapping
of profile slots into the eighteen-slot composition, the remaining visibility
rule, and live integration still need completion.

## Raw-row visibility predicate

`CODOL_CharacterSlot7Allowed` now implements 0x60d220 over an explicit part
table and marketplace item name. It uses the last case-insensitive column-0
match and column 3 directly, without invoking the model variant selector. It
returns false for an absent row or a name shorter than `strlen(item) + 6`.
Otherwise it returns whether the byte at that offset is outside ASCII `0..9`.
Equality with the model length deliberately reads the terminating NUL and
returns true, matching the measured unsigned byte comparison.

Callers 0x60d372..0x60d38c and 0x6986c4..0x6986dd apply this to positive
composition slot 2 and clear nonzero slot 7 when it returns false. Body-part
names are not assigned to these slots yet. The Python `_row_items` helper
recognizes identity by item type even when stored in another profile slot;
the native eighteen-slot composition uses identity at fixed slot 4. Their
conversion remains an integration requirement, not an assumed direct copy.

The focused 32-bit ASan/UBSan test and Windows build passed
(`/tmp/sh1x-character-visibility-win32.log`). This verifies the native predicate,
not live appearance selection or assembled C1 rendering.

## Verified profile/composition slot order

C1's group resolver 0x7298f0 indexes eleven names at 0xccc990. UI writes at
0x6a02be..0x6a02e4 and 0x6a13d0..0x6a13f6 use the corresponding integers at
0xc309a4 to address both the composition scratch array and the selected
character cache at 0x7245c60 with 0x70-byte record stride. The cache loader
0x590dc0 and writer 0x590ec0 use the same slot indices in the structured
`characterClasses[record].slots[index]` paths. Thus the profile is not ordered
by the addresses of the part-code string literals.

| Group | Profile/composition slot |
| --- | --- |
| fpa (trousers) | 0 |
| boo (boots) | 1 |
| fja (torso) | 2 |
| han (hands) | 3 |
| hea (head/identity) | 4 |
| ves (vest) | 5 |
| heg (headgear) | 6 |
| elp (elbow pads) | 7 |
| knp (knee pads) | 8 |
| pat (material) | 9 |
| eye (eyewear) | 13 |

`CODOL_CharacterSlotForGroup` exposes this measured mapping. It explains the
previously unnamed rules: defaults use the head identity, chest rigs are
selected from the vest, and the torso naming predicate can clear elbow pads.
The first eighteen cache slots participate in composition; the roles of slots
18 and 19 remain unverified and must not be guessed or emitted as parts.
Historical sections above record the investigation; this mapping supersedes
their earlier uncertainty and the Python slot-order approximation. It does not
by itself connect profile data to live snapshot publication.

## Connected native composition and mounted validation

`CODOL_ComposeProfileCharacter` now connects the schema-driven public-profile
reader to head-identity defaults, vest-derived chest rigs, torso/elbow-pad
visibility, marketplace part tables, and C1 variant selection. It preserves
explicit signed-short sentinels, never modifies the input profile, and publishes
its output only when the whole name-resolution pass succeeds. Returned names
borrow mounted table storage. A successful sparse result is not a complete outfit.

The diagnostic command is:

```
codol_checkcharacter <head item ID> <tf|sc|zm> <m|f> <camo> <skin>
```

It creates an in-memory synthetic profile using the mounted v220 playerdata
schema, sets only the head in record zero, and resolves with explicit visual
context and rig selector zero. It does not read or write a live player's data.

On the native Windows server with `mp_bog_sh` mounted, `115 sc m urb wht`
resolved these parts from a head-only profile:

| Slot | Item | Model |
| --- | --- | --- |
| 0 | 124 | fpa_technoa_sc_m_01 |
| 1 | 136 | boo_concepta_sc_s_00 |
| 2 | 142 | fja_standard_sc_m_01 |
| 3 | 169 | han_hands_ss_m_wht |
| 4 | 115 | hea_socomb_sc_m |
| 5 | 103 | ves_base_sc_m_15 |
| 6 | 155 | heg_beret_sc_s_00 |
| 15 | 224 | bar_baseassault_sc_m_15 |

All eight separately passed the native model diagnostic's skeleton, geometry,
materials, mesh, core, and complete checks. The wrong TF context leaves several
SC parts unresolved, which confirms that visual context must be derived correctly.
`160 tf m urb wht` resolves only the Ghost head from this sparse profile; the
composer does not invent missing clothing. Logs are retained locally in
`obj/character-composition-mounted.log` and `obj/character-composition-models.log`.

The end-to-end composition test checks selected faction/class routing, defaults,
rig replacement, elbow-pad suppression, preserved negative sentinels, immutable
input, and atomic output on table-loader errors. It and the affected marketplace
and rig tests passed with 32-bit ASan/UBSan. The Windows build passed
(`/tmp/sh1x-character-composition-win32.log`). These tests establish native
selection and asset availability, not assembled client rendering.

Still required: deriving the live visual context, viewhands, verified DObj part
ordering/attachment semantics, collision-safe configstring allocation, and
publication through the full sixteen-slot client appearance path. Real C1 match
entry remains unverified.

## Measured meaning of a -1 character slot (2026-09-15)

A stored slot of -1 is "nothing chosen for this slot", not "this slot stays
empty". C1 composes into a *zeroed* array and drops -1 while copying:

- `0060b074`: `push 0x4c; push 0; lea ecx,[ebp-0x308]; push ecx; call 0xae04c0`
  memsets the eighteen-slot composition (0x4c bytes) to zero, and only then
  `0060b097` calls the copier `0060d2c0`.
- `0060d2c0` copies the eighteen stored ints from `0x6c26538..0x6c26584` into
  that array, each guarded by `cmp ecx,0xffffffff / je` past the store
  (`0060d300`, `0060d30b`, `0060d315`, `0060d31f`, `0060d32a`, `0060d338`).
  The per-record variant `0060d3a0` (called from `0060b0fd` behind the same
  `memset 0x4c,0`) repeats the identical `cmp edx,0xffffffff / je` guard.
- The slots themselves come straight from the profile: `694818` reads slot *i*
  with `590d00` and stores the sign-extended value into both `0x6c26538[i]`
  and the character record at `+0xc` as a short (`694850`), so a profile -1
  reaches the copier as -1.
- `0060d020` then merges `mp/coCharacterDefTable.csv` into every slot that is
  **exactly zero** (`cmp DWORD PTR [eax+ebx*4],0x0 / jne`, `0060d02c`), so a
  slot that was -1 receives that character's default item.

Consequence for viewhands: a TF character saved without gloves (for example
`hea_sean`, marketplace 382, `SF_UI_HEA_SEAN_NAME` = "山地人", whose live
profile record has `slots[3] == -1`) still gets `charHAN` = `han_basic`, whose
`mp/coCharItems/han.csv` row supplies third-person `han_hands_ss_m_wht` and
column-4 first-person `han_basic_ss_m_vmchar_wht`. Preserving the -1 instead
produced `hands <none>` and a first person with arms and no hands, because C1
never fabricates a hands model: `0046d82e/0046d830` pass a literal NULL to
`CG_SetCustomizedViewmodel` (`0047cf30`) and `0047c6f8` then builds a one-part
viewmodel DObj. The only engine-side default is the weapon's own
`WeaponDef+0x10` handXModel for the *arms* (`0047d263`); the hands slot is
never defaulted. The hands name must therefore be produced by the composer.

`CODOL_ComposeProfileCharacter` now maps `0xFFFF` to zero across the eighteen
composition slots immediately after the legacy normalization and before the
default merge. Other negative values are not special-cased by C1 and remain
unresolvable, so the existing positive-ID guards are unchanged. This supersedes
the earlier "keep -1 sentinels" note in the composition source.
