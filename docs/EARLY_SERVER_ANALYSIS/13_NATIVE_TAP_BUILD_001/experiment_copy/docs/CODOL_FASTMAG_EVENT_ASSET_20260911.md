# M4A1Tech event fastmag animation gap

Correction: empty names are confirmed for the currently emitted descriptor,
but that does not prove the official loadout uses this descriptor or requires
asset repair. The earlier delivery recommendation was premature. Trace C1
loadout identity resolution and initialization before choosing a fix. No
additional zone is established as necessary; isolated repair is diagnostic only.

## Vanilla-path audit reopened

The user confirms this worked in vanilla. No extra zone or asset patch is the
selected solution. Native `CODOL_ComposeLoadoutWeaponRecipe` currently creates
the descriptor from marketplace column1, selected profile attachments, and
declared defaults. Its equivalence to the original producer remains unverified.
The local `_class.gsc` is an IW4-derived overlay, not original CoDOL evidence.

C1's only direct caller of constructor421590 is weapon lookup41f7e3. Subsequent
registration41f640 installs the definition, runs helpers41f200/41f310/41f3f0,
partner registration41f4b0/41f510, then an optional caller-supplied callback.
Literal `*a ` references42075e/4207bf and `*b `41ef33 search existing strings;
these references do not establish the original loadout producer. Audit that
producer and initialization callbacks before changing base selection or defaults.

Callback audit: configstring consumer483600 passes NULL to lookup41f7a0.
Server callback529bc0 calls529aa0 for accuracy-graph/model registration, then
publishes weapon/partner names at configstring base0x14f2 and count at0x1975.
The inspected callback bodies contain no quick-animation bank initialization.
This rejects that specific proposed seed path, not all possible initialization.

Status: C1/source investigation plus isolated inflated-zone repair artifact.
No installed client asset, running process, or gameplay change in this audit.

The native reload producer and snapshot are selecting quick reload correctly.
`obj/m4-fastmag-live.jsonl` records active gameplay: predicted command743017
uses state8/animation1038 (quick nonempty with restart bit), followed by the
same snapshot animation at743068. Inventory byte2 subsequently toggles1->0.
Native logs also record quick empty animation1040 and normal empty1039.

The missing animation is in the client-owned event weapon definition. Active
M4 composed definition0x1536d00, wire114, has dualMag1 and reload durations
2009/1800/2299/2100ms. Its normal and normal-empty animation names exist;
quick and quick-empty names are empty in all three animation banks.

Read-only attachment lookup uses C1's map populated at41fc96:
`bg_attachIdx[(27 << 8) | 153]` at0x15111e8 gives137, and
`bg_attachmentDefs[137]` at0x150f408 points to `dualmags_m4tech`.
Its actual patched animation entries are replacements:

| WeaponDef offset | Operand |
| --- | --- |
| 0xa0 | `[r] reload dualmag_reload_normal` |
| 0xa4 | `[r] reload dualmag_reload_quick` |
| 0xa8 | `[r] reload_empty dualmag_reload_normal_empty` |
| 0xac | `[r] reload_empty dualmag_reload_quick_empty` |

Replacing text in an empty source string leaves it empty. C1 applies these
text operations through4208e0/41ebc0; the kind0 string result is interned and
stored by420d80..420d95. The server attachment implementation likewise treats
these as replacements, so changing reload timers or animation IDs cannot
repair their source strings.

The shipped inflated `patch_common_gametype_mp.zone` confirms the mismatch:

| Asset | +0xa0 | +0xa4 | +0xa8 | +0xac |
| --- | --- | --- | --- | --- |
| 87: m4a1tech_mp | 0x30090205 | 0x30090205 | 0x30095066 | 0x30095066 |
| 96: m4a1techevent_mp | 0x30090205 | 0x300080b1 | 0x30095066 | 0x300080b1 |

Live base26 `m4a1tech_mp` resolves the first pair to
`viewmodel_m4a1tech_reload` and the second pair to
`viewmodel_m4a1tech_reload_empty`. Base27 `m4a1techevent_mp` instead resolves
its two0x300080b1 fields to empty strings. Thus the patch seeded the ordinary
weapon's quick slots for replacement, but omitted that step for the event
weapon. The original common_gametype_mp m4a1tech asset also had empty quick
slots; this was specifically a patch-time change.

The precise repair is to seed event-base +0xa4 from +0xa0 and +0xac from +0xa8
before the existing attachment replacement pass. This must reach both the
client and server asset definitions. Corrected asset delivery can preserve
the event weapon's identity and other properties. Changing the server's
descriptor from base27 to ordinary base26 is not established as equivalent
and would also change the client weapon's base identity.

## Exact source and review artifact

Reference tools reside at
`D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/CODOL/1.1.1.13_server/alpha0022`.
The actual source archive is
`D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/client_shipRetail/chinese/patch_common_gametype_mp.ff`.
Its SHA256 is `04f5290c5b705260b832a3ba8455233e48381d17a8cb5b77d773138ce26f4256`.
Fresh inflation directly from that archive, with existing section/block hash
validation, yields 4,464,458 bytes, SHA256
`53b9936ba1fc3d58d0d1c0b64275cc5bfbed81c661cd770ec7a80bf0b7195c74`.
This evidence does not depend on the older temporary zone cache.

Asset96 has directory offset0xc0709 relative to the XAssetList at0x28;
its absolute zone start is0xc0731 and length3085. Its inline internal name
at blob+0xbfc is `m4a1techevent_mp`.

| Absolute inflated-zone offset | Field | Before | After |
| --- | --- | --- | --- |
| 0xc07d5 | WeaponDef+0xa4 | 0x300080b1 | 0x30090205 |
| 0xc07dd | WeaponDef+0xac | 0x300080b1 | 0x30095066 |

These are serialized block3 references, not file offsets or process pointers.
Live resolution establishes0x30090205 as `viewmodel_m4a1tech_reload`,
0x30095066 as `viewmodel_m4a1tech_reload_empty`, and0x300080b1 as empty.
The repair reuses existing same-zone references and preserves every length,
directory entry, inline string, and event identity.

`tools/codol_prepare_event_fastmag_asset.py` generates the isolated repair and
manifest, guarding the source SHA and field values. It refuses output beneath
the client install and uses exclusive creation. Generated artifact:
`obj/event-fastmag-asset-repair/patch_common_gametype_mp.event_fastmag.zone`.
SHA256: `c9e6d1eae874105dd251b9f64e1db85ae4a996bcd7d39a280ed22c6d269036ad`.
The adjacent `manifest.json` records provenance and both field replacements.
This is an inflated review artifact, not a loadable or installed fastfile.

## Existing writer and delivery constraints

The reference `ffwriter/codol_ff.py` implements `wrap_ffotd`: RSA-OAEP-SHA256
encrypts an AES192 key/IV, then a single little-endian CTR stream encrypts
the zlib-compressed zone. Its `IWffu100` output does not preserve or reproduce
the shipped `IWff0100` RSA signature/block structure. The writer does not have
the signing key. Reusing the original signature after this edit is invalid.

Crucially, `ffwriter/build_animlist.py` lines90-135 documents C1's gate at
0x004B5F02: an unsigned file with a real disk handle is fatal. Thus wrapping
this full repaired zone and replacing the disk archive is **not a viable
delivery route**. `IWffu100` is accepted through the existing in-memory
FFOTD route. Its buffer is limited to65535 bytes (0x005926F2), fetched as
`ffotd_client.ff` from lobby `resources/`, and reloaded last per level
(0x004CD22E); FFOTD asset override selection is at0x004CC5F4.
These constraints are recorded reference disassembly findings, not a new
live loading validation in this audit.

`ffwriter/zone_splice.py` can retain/rebuild a complete zone stream; it does
not make an individual WeaponDef self-contained. Copying asset96 alone into
FFOTD would leave its numerous block-relative references pointing at absent
data. A faithful compact FFOTD weapon override requires a WeaponDef serializer
that resolves and re-emits the complete pointer graph and required names,
plus confirmation the existing FFOTD payload and override lifecycle permit
the addition. No such general weapon serializer was identified in the examined
ffwriter tooling. Do not deploy the isolated zone or replace the event base
with the non-event weapon as a shortcut.

No build, gameplay test, installed asset write, process restart, or memory edit
was performed. Client delivery remains the unresolved implementation step.

## Reopened native construction audit

The asset-delivery conclusion above is withdrawn. The user reports vanilla
behavior worked and requires existing assets only. The missing names establish
a symptom of the current descriptor, not the correctness of that descriptor.

Additional direct C1 evidence:

- `BG_GetWeaponIndexForName` calls the custom constructor at0x41f7e3.
  Constructor0x421590 indexes the registered base at0x4215fe, copies0xbfc bytes
  verbatim at0x4216c4, collects attachment operations, applies grouped operations
  at0x4219e9, then builds models at0x4219fe and alternate identity at0x421a0e.
  No quick-slot seeding was found within this constructor.
- Marketplace accessor0x728750 formats item ID, searches
  `mp/coMarketplaceItems.csv` column0 at0x72879a, and returns column1 at0x7287aa.
  Menu attachment routines0x6b89e0 and0x6bd870 use this accessor. No event-base
  remapping was established in these callers.
- The patched marketplace row440 is ID1063, name `m4a1techevent_mp`, type `wea`,
  group `ast`; columns4..10 are empty, empty,1,0,0,0,empty. This row contains
  no alternate functional-base name. It does not by itself prove the final
  descriptor produced by the original server scripts.
- Patched attachment table rows1070..1080 define the event's exact item set:
  `cam_tiger`, `for_gripvtlong`, `gri_default`, `iro_default`, `mag_default`,
  `mag_dualar15`, `muz_default`, `rai_default`, `red_rmr`, `sra_hbs`,
  `sto_ar15acs`. Their non-nop assets are `grip_m4a1tech`, `dualmags_m4tech`,
  `reflex_m4a1tech`, `heartbeat_shareda`, `stock_shareda`.
- Patched `mp/coweapitemswea.csv` row55 declares ten default triplets, each
  enabled by `y`: bas=for_gripvtlong, gri=gri_default, iro=iro_default,
  mag=mag_dualar15, rai=rai_default, sto=sto_ar15acs, sco=red_rmr,
  hbs=sra_hbs, cam=cam_tiger, muz=muz_default. The hbs slot differs from the
  marketplace sra group; the previously fixed parser now retains it.
- A scan of all serialized weaponattach entry arrays in base and patched
  common_gametype_mp found only `dualmags_m4tech` writing +0xa4/+0xac among
  those event defaults. A missing listed default therefore does not explain
  seeding through a direct write to these offsets. Indirect operation or
  alternate construction semantics remain to be investigated.

No original CoDOL server loadout GSC/Lua producer has been located. The Python
builder's statement that event base27 is composable proves only that C1 accepts
it; acceptance does not prove official loadout semantics. No replacement base,
new attachment, or native construction change is justified by this audit yet.

## Native loadout default producer found (2026-09-14)

New direct C1 evidence identifies a native selected-item/default-item producer,
distinct from the custom WeaponDef constructor previously examined:

- `60d5b0` copies fifteen pairs from the selected-loadout globals into an
  output record. Slot0's weapon item ID and second word are copied unchanged
  at60d5d5..60d5e8. Other positive item IDs are categorized by the marketplace
  group accessor728830 at60d602, then copied to that category's output pair.
- Category strings atccc9bc are, in order: WEA, STO, RAI, SCO, MUZ, BAS, HBS,
  GRI, CQC, MAG, IRO, ROF, SRA, CAM, BIP. The comparison routine is called at
  60d61e. Do not interpret the pair's second word as an animation-bank selector;
  its further consumer has not been traced here.
- `60d5b0` subsequently calls `60d450` at60d661. The latter loops categories
  1..14 and calls default accessor6c4900. A positive default is inserted only
  when the output category's item ID is zero (60d575..60d585), with secondword1.
  The destination category is determined from the default item's marketplace
  column3, not blindly from the label used to locate it in the defaults table.
- `6c4900` resolves weapon marketplace name through728750, searches
  `mp/coWeapItemsWEA.csv` column0, scans labels at columns10,13,...49, and reads
  the matching item's name at column+1. It then searches marketplace column1
  and converts the returned column0 ID to an integer. This routine does not
  inspect the triplet's third/flag column. Missing/invalid IDs return-1.
- `609920` clears a0xf4-byte output and invokes60d5b0 twice, for weapon slots0
  and1, writing records at+4 and+0x7c. Its direct caller is60b21e. Another
  caller60afb0 also invokes60d5b0 twice at60b0be/60b0d2. These provide concrete
  next consumers for tracing the final native recipe rather than guessing a
  descriptor from marketplace tables alone.

No event-to-ordinary weapon remap or quick-animation seeding occurs in these
producer bodies. This narrows the remaining investigation but does not prove
the event descriptor's final identity. No additional assets, patch zones, source
changes, tests, restarts, or client writes were made.
