# Four reload branches: current source review

Direct C1 disassembly was compared again with `codol_weapon_reload.c` and
the snapshot reload publisher on 2026-09-14. No new gameplay run was made.

| Magazine phase | C1 animation ID | Name slot | Duration | Ammo-add delay |
| --- | --- | --- | --- | --- |
| Normal, nonempty | 13 | 9 | +0x5c8 | +0x5dc |
| Quick, nonempty | 14 | 10 | +0x5cc | +0x5e0 |
| Normal, empty | 15 | 11 | +0x5d4 | +0x5e4 |
| Quick, empty | 16 | 12 | +0x5d8 | +0x5e8 |

C1 `4192f0` reads current inventory byte2 at `41930a`. A nonzero byte and
WeaponDef byte `+0xbc7` select the quick branch. Empty/nonempty comes from
`418ec0`: the selected hand's clip is absent/zero and weapon type `+0x340`
is zero. The duration/animation branches are `419356..419376`,
`41937e..4193b5`, `4193e3..419403`, and `419405..41943c`.
`419150` supplies the four add delays: zero or a delay at least as long as
the selected duration uses that duration. Inventory byte2 toggles upon the
ammo-transfer attempt, not at animation start; the existing native phase
capture correctly prevents that toggle from changing an ongoing animation.

Current native source agrees with those decisions. The timing extension
loader retains all four add times and both quick duration variants.
`CODOL_OverlayEngineReloadPhase` publishes the phase captured at start;
inventory publication separately carries the next-magazine bit in flag4.
The prior live M4 capture already showed quick14/16 and matching snapshots;
do not redo that fix merely because an animation is invisible.

Current passive probe of C1 PID102052 passed the executable signatures, but
returned commandTime0 and no snapshot. Therefore no currently equipped
definition was read, and the current reported weapon's identity is unknown.
The older event-M4 empty quick-name finding remains specific to its recorded
descriptor; it is not proof that all fastmag weapons need asset changes.

The previously pending selected-item consumer was narrowed further:
`60b21e` calls `609920`, then the path at `60b40d` invokes `5e9130`.
Its `60d780` callee resolves `mp/coCharItems/%s.csv` and the selectors
`model` (`c5ca48`) and `jointTag` (`c6dd24`) through `729090`.
The adjacent `611ba0` lookup reads weapon-class field `+0x344` and updates
the preview class global. These inspected bodies do not initialize quick
reload names or establish an event-to-ordinary weapon remap.

No native behavior change is justified by this review alone. Next decisive
evidence is the reported equipped descriptor and its four animation-name
slots, paired with a quick reload's predicted and authoritative phase.
No extra zone, client asset patch, timing substitution, tests, build, restart,
or memory write was performed.

## Known event weapon: new complete header comparison

Parent confirmed the reported weapon is the previously captured
`m4a1techevent_mp`. Reopened the shipped `patch_common_gametype_mp.ff` with
archive verification and compared all 767 words of the two 0xbfc headers.
Only these words differ between ordinary asset87 and event asset96:

| Offset | Ordinary | Event |
| --- | --- | --- |
| 0x008 | 0xffffffff | 0x3009a669 |
| 0x0a4 | 0x30090205 | 0x300080b1 |
| 0x0ac | 0x30095066 | 0x300080b1 |
| 0x134 | 0xffffffff | 0x3009a67a |
| 0x138 | 0xffffffff | 0x3009a68e |

Every scalar, model reference, other animation reference, sound reference,
and other serialized word is equal. This is stronger evidence than comparing
only reload slots, but equality of pointer tokens alone does not resolve
the three inline-versus-shared differences.

The ordinary asset's complete inline payload is, in order,
`m4a1tech_mp`, `WEAPON_M4A1_TECH`, `viewmodel_m4_ADS_up`,
`viewmodel_m4_ADS_down`, each NUL terminated. Only header offsets0,8,134,138
are inline in its string/model/animation region. Event's complete inline
payload is only `m4a1techevent_mp`. The three event shared-reference increments
are17 and20 bytes, exactly matching the display and ADS-up string lengths
including NUL. This supports their equivalence but is not yet a resolved
stream-block proof. The native archive loader already owns resolved block3
data and could settle these three values through existing mounted accessors.

Together with the earlier composed-definition capture and replacement
operator trace, the immediate missing-name cause remains established:
event quick source names are empty and `[r]` cannot replace text in them.
What remains unestablished is the original official server's event-item to
runtime weapon descriptor producer. No such original GSC/Lua producer has
been located; the current overlay and Python recipe are reconstructions.
The newly demonstrated near-equivalence makes an existing ordinary-base
recipe a concrete candidate for review, rather than justification to modify
correct reload timers or install new assets. It still requires resolving the
three strings and confirming equivalent attachment lookup/default behavior
before any source change.

Fresh comparison of the winning `mp/coWeaponAttachmentTable.csv` from
`patch_code_post_gfx_mp.ff` confirms all eleven event items also occur for
ordinary M4 and resolve to the same attachment assets. Ten have variant0
in both rows. `sra_hbs` is the exception: both use `heartbeat_shareda`, but
event variant0 versus ordinary variant20. A base substitution that recomputes
ordinary variants therefore is not equivalent. The event's default set also
differs from ordinary defaults, so those must remain selected from the event
item. Base-model CSV selection and context substitutions additionally depend
on base name; their equivalence has not been established. This comparison
supports further investigation of an existing-assets recipe, not a blind alias.

## Reviewed-policy implementation staged in native source

Parent authorized an existing-asset recipe adaptation after the comparisons.
`codol_loadout_fastmag.c` now implements that narrow policy for event M4 with
`mag_dualar15`. This is a compatibility adaptation, not a claim that the
official server emitted the same descriptor.

Before substituting the composition index, it resolves both mounted source
images and checks all header bytes and resolved name fields, allowing only
internal name and the two empty quick slots to differ. Display name, ADS
names, other animation names, scalar gameplay data, hide tags and sound arrays
must agree. The event's two quick names must be empty; ordinary quick names
must be seeded from their respective normal names. It checks the selected
base model/camo and every selected part's world/view/tag models using the
event's original variant bytes. Every pair must select the same attachment
asset for both bases. Applying the complete set to both images must preserve
equivalence, including context-sensitive replacements, while producing four
nonempty ordinary reload names with different quick/normal names and dualMag1.
Parent review: a failed equivalence check logs a warning and preserves the original selected recipe; it cannot turn an existing class into a recipe failure. Successful checks alone publish the alternate composition.

Fresh shipped-table evidence additionally confirmed both base-model CSVs
have22 camo rows and identical world/view names at every corresponding row.
The unpatched dualmags attachment's entries at a0/a4/a8/ac are kind0, inline
literal names for normal/quick/normal-empty/quick-empty. Its patched entries
instead reference the previously verified replacement strings. This explains
how the required base-name seeds became relevant.

`codol_script_profile_loadout.c` finishes event item/default/camo resolution
first. Only the emitted header base index changes after successful validation.
Event `base_name`/`base_index` remain available for profile identity; new
`composition_base_name`/`composition_base_index` explicitly describe the
runtime definition. Pair order, IDs, variant bytes, camo flag, and event
defaults are untouched. No client asset/zone is changed, and no other weapon
is aliased. Native reload timing/state producers remain unchanged because
they already match C1's four branches.

Source written and manually reviewed by the worker. Parent integration review,
build, and live four-branch verification remain required. No worker tests,
builds, restarts, UI actions or process writes were performed.


## Follow-up: rejected recipe and model-table lookup (2026-09-14)

Current passive C1 capture (PID102092, command178909) still has dualMag1,
normal reload names and empty quick slots. The server logs the equivalence
rejection, so the earlier adaptation is not active. This is not fixed visually.

Offline source/header comparison found raw differences only at resolved name
slots 8/a4/ac/134/138. Archive-local graph/tag references are not the observed
base-header rejection. All eleven event attachment rows have matching ordinary
assets, including explicit nop rows; missing attachment rows were another
hypothesis, not the established failure.

The selected grip exposes a real native lookup defect. Ordinary M4 contains
multiple exact model-table rows: first gri_default_m4_blk, later
 gri_default_m4a1tech_blk. C1 42047a loads the composed HEADER camo at +90,
420484 pushes reverse=1, and calls 728060. That branch starts at the last
matching item row, walks backwards at728421, and updates only on a strictly
larger score at728416..41e. Thus the last equally specific row wins.
Native CODOL_ComposedItemModelRow previously walked forwards and returned the
first exact match. The fastmag verifier also incorrectly passed part.variant,
instead of the header camo used by this C1 model consumer.

Source now corrects reverse tie traversal and the verifier's header-camo input.
Other lookup semantics are unchanged. The verifier logs its rejecting stage,
name/scalar offset or model part to distinguish any further failures.

This does NOT establish that ordinary-base substitution is valid. The shipped
ordinary muz_default also has duplicate zero-camo rows: its winning last row is
muz_flashhiderar_ssncm_blk, while event uses muz_default_m4a1techncm_blk.
Both have matching TAG_SILENCER but different model names. With correct C1
lookup, this genuine geometry difference must continue to reject the strict
alias. No guard was removed and no zone/client asset was changed. Fast reload
requires a further supported recipe/asset delivery solution; the animation
absence remains unresolved.

Worker source review complete. Parent build/deploy and actual client behavior
remain separate; no worker tests, builds, UI input or process changes.

## Follow-up: archive provenance and alternative muzzle recipe (2026-09-14)

Current source `patch_common_gametype_mp.ff` still has SHA256
`04f5290c5b705260b832a3ba8455233e48381d17a8cb5b77d773138ce26f4256`,
identical to the archive recorded in the earlier direct evidence. Its current
last-write timestamp is2014-03-05; common_gametype_mp is2014-01-03. Timestamps
alone cannot authenticate an archive, but the unchanged hash establishes that
this session's Python/lobby/native changes did not create a new source-file
quick-slot regression relative to that previously captured artifact.

A focused Python source search found animlist/patch_common_mp tooling, but no
m4a1techevent/dualmags quick-slot mutation of patch_common_gametype_mp. This is
negative search evidence, not proof of an untouched installation. Another
local CoDOL build has a different patch file hash; its version/content is not
established equivalent and was not substituted.

A fresh winning-table scan of all coWeapItems tables searched every cell for
`muz_default_m4a1techncm_blk`, the exact event muzzle model. It occurs only in
mp/coweapitems/muz.csv row52 (muz_default,m4a1tech_mp,camo0) and row54
(muz_default,m4a1techevent_mp,camo0); their viewmodel and TAG_SILENCER match.
There is no different muzzle item name in those tables supplying that model.
The ordinary row52 loses the already verified reverse equal-specificity tie
to the later ordinary muz_default model. Thus simply substituting another
published muzzle attachment item cannot recover event appearance while using
the ordinary seeded-animation base. Changing the selected camo/default rules
or relaxing geometry equivalence would be an unproven semantic change, so the
guard remains intact.

The exact C1 event constructor/replacement behavior and four native reload
phases remain as previously established. No new legal existing-asset descriptor
that preserves the selected event definition and seeds its missing client
quick slots has been demonstrated. No speculative source change, hook, client
patch, extra zone or animation-timing workaround was added in this increment.

## New load-order survey: current lobby delivery and viewer zone

Read-only decoding of the current served
`alpha0022/resources/ffotd_client.ff` used its actual IWffu100 unwrap path,
not the stock IWff0100 parser. SHA256 is
`fe93c7b05cf1fc34471d44761a5f5aec6ffcbfb33dade6e582e14245f6014b6b`.
Its decoded8588-byte zone contains0 weapons,0 attachments,1 rawfile and2
tables: mp/uinotifications.csv and mp/functionalunlocktable.csv. No event-M4
or dualmags asset names appear. Thus this current lobby-delivered asset file
cannot be the source of a weapon quick-slot override.

Fresh shipped-zone inventory found no relevant weapon/attachment override in
common_mp (one unrelated weapon), patch_common_mp, mp_killhouse_sh or
patch_mp_killhouse_sh. `ui_viewer_mp.ff`, however, contains64 weapons and no
attachment assets, including its own m4a1techevent_mp definition (3085 bytes).
Its animation pointers are a0=30577c22,a4=300249d3,a8=30577c3c,ac=300249d3;
normal/quick durations are2009/1750ms. These are archive-relative references,
not live pointers. The shared quick reference has not yet been independently
resolved in this viewer stream, so its contents must not be asserted empty
solely from the shared pointer. This is a new load-order lead; no viewer asset
was changed and no extra zone was requested.

Current C1 PID102092 passive instruction signatures pass, but commandTime0,
weapon0 and no snapshot make gameplay-definition pointers unsuitable for a
fresh live construction claim. No stale definition was treated as evidence.

## Viewer shared string resolved; zone group ordering narrowed

The earlier unresolved-reference note is superseded. Offline tool
`obj/fastmag-viewer-sharedref.py` reconstructs the string-table portion of block3
using the actual loader layout (`codol_load_blocks.c::replay_string_table`):
16-byte header in block0, name/cell array/inline strings in persistent block3.
For viewer asset2, mp/cocharitems/fja.csv, 347 repeated inline/hash references
independently yield one cell-array base: block3 offset0x223e4. There are no
competing base candidates. Reference0x300249d3 decodes to block3 offset0x249d2,
which is the inline empty string in cell374 (row74,column4). Adjacent strings:

- offset0x249c0: fja_basic_ss_f_00 (cell373)
- offset0x249d2: empty (cell374)
- offset0x249d3: fja_basic_ss_m_00 (cell378)

Thus viewer m4a1techevent_mp also has empty quick/quick-empty slots. The shared
reference is an XString address, not an asset alias slot requiring a second
pointer dereference. This result derives from source bytes and redundant
relocation anchors; no current/stale runtime pointer is used.

C1 UI loading at5984f0 constructs seven zone requests with allocation flag2:
patch_ui_mp, ui_mp, patch_localized_ui_mp, localized_ui_mp,
patch_ui_viewer_mp, ui_viewer_mp, ffotd_client. The stock current Chinese zone
directory contains ui_viewer_mp.ff and no patch_ui_viewer_mp.ff. At5985f0,
C1 checks whether viewer is loaded, then when global loaded flags include2,
issues a null-name request with allocFlags0/freeFlags2 (598631..59864a).
Caller599e53 invokes this UI unload path. Viewer definitions consequently must
not be assumed permanent gameplay overrides merely because lobby loaded them.

The MP common-gameplay request construction at4cd03e..4cd0f0 checks whether
common_gametype_mp is already loaded and otherwise appends, with allocFlags4:
patch_common_gametype_mp, common_gametype_mp,
patch_localized_common_gametype_mp, localized_common_gametype_mp. Patch is
submitted before base; a naive last-file-wins interpretation is therefore not
an adequate model of C1 asset registration precedence. Exact registry winner
selection across exceptional retained-zone states is not newly recovered here.
Previously captured active gameplay definition/attachment evidence remains the
actual winner evidence for that session.

The important resolved consequence is independent of that remaining registry
branch: both inspected candidate event definitions (viewer and gameplay patch)
have empty quick slots. Lobby ffotd has no weapon/attachment override, viewer
has no attachment overrides, and its event definition cannot supply the missing
seeds. Native recipe publication cannot create those client XString seeds by
merely changing zone ordering. No change to the guarded alias, selected event
geometry, client assets, runtime or native timing was made.
