# C1 player world-weapon audit — 2026-09-15

Status: native producer source written; integration patch supplied to parent. No build or gameplay verification by this worker. Applies to human players and bots. Pose/animation-condition correctness is a separate parent investigation.

## Proven missing producer

The ordinary player appearance DObj does not contain the ordinary held gun in C1. C1 creates separate, genuinely linked `script_model` entities carrying a weapon selector. This is native C1 behavior, not a synthetic snapshot/model workaround.

Authoritative image: `D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/C1.exe` (image base 0x400000). Aligned excerpts are under `obj/bot-worldgun-audit/`; `570b70-full.txt` contains the complete producer.

- C1 `570b70`: desired weapon from player entityState+60. When zero and current weapon definition inventoryType+34c equals3, it uses playerState+340. Hidden owner entity flag1 and playerState flags0xc00 clear the desired selector (`570ba7..570bc5`).
- Existing children are owned at gclient+3594/+3598, compared against their captured selector and freed/replaced when weapon changes (`570c06..570c79`).
- `570c94..570ce8`: a worldKnifeModel at definition+30 enables torso knife-animation inspection; animation flag0x100 suppresses the second gun. Otherwise playerState+35c==1 selects two children.
- `570cf3..570d31`: original weapon type3 produces no linked world gun. Type1/class11 uses tag_weapon_right; other type1 uses tag_weapon. Other types use tag_weapon_right/tag_weapon_left for the two hands. String identities were independently read from C1's string pool, not inferred from retained scr_const offsets.
- `570a70` spawns and initializes a script_model, uses tag_origin as its root model, clears contents, resolves the parent's actual tag matrix, links to that tag and updates the link. `570b0a` writes the plain full weapon index to child entityState+68; there is no variant packing in this write.
- Client `43e83a` routes nonzero script-mover entityState+68 to `43e600`. That function resolves the weapon definition and world model+1c; composed weapon names invoke `421b10` to construct the world attachment model list. `43e730` allocates the child DObj and `422830` applies hide tags.
- Player DObj callback `450370` adds special melee/knife models; forcing its melee flags would not implement ordinary held guns.

## Live asset evidence

`obj/bot-worldgun-audit/live-model-pointers.json`, passive client PID100756, commandTime676381:

- Entity1 weapon118: composed KRISS descriptor; world model `weapon_kriss` exists.
- Entity3 weapon122: composed WA2000 descriptor; world model `weapon_wa2000` exists.
- Both had valid first-person models and world-knife models. Their ordinary player DObjs contained appearance pieces only. This is consistent with the missing separate producer, not evidence that weapon registration failed.

## Source and lifecycle

`src/codol/player/codol_player_worldweapon.c/.h` maintains generation-checked, owned child handles. It uses the existing semantic primary-weapon accessor (which preserves carried primary for alternate inventory type3), independently retained original C1 type/class metadata, and actual native animation-record flags. It creates real script_model entities, links with the native parent-tag transform and refreshes links after the final player pose. Missing tags defer creation until a valid skeleton exists; invalid weapon metadata clears stale children.

`obj/bot-worldgun-audit/worldweapon-integration.patch` adds the frame call after all ClientEndFrame calls, and live slot/map resets in codol_sv_entity_events.c. Owner records are cleared before freeing children, making recursive free/reset safe. Both child number and useCount are checked before destruction; recycled entity slots are never freed through a stale handle. Map reset forgets handles rather than walking an already-reset pool.

Parent owns `LerpEntityStateScriptMover.weaponIndex` in existing native anonymous.data[4] and snapshot publication to C1+68. Existing archive storage captures that field and native link state; the archive writer never consults mutable live owner records.

No guessed health-based gate was added: verified C1 visibility flags govern the producer. Owner freeing/reuse removes owned children; a separate corpse-owned persistence path has not been implemented or claimed. No new GSC callback, client memory patch or proxy gameplay was introduced.


## Map-switch cleanup review

Read-only follow-up after reported mp_nuked switch stall; no source changes.

- G_ShutdownGame (_g_main_mp.asm1397+) prints its shutdown banner before its ascending inuse entity loop. Each entity is checked again immediately before G_FreeEntity. A child freed recursively with its owner is therefore skipped later.
- G_FreeEntity (g_main_mp.cpp292+) unlinks the receiver and all tagChildren before the central generation reset at352. Thus owner cleanup sees detached weapon children, not an active parent child-list traversal. The owner record is zeroed before nested child frees; those child resets can only clear already-empty references, not recurse back into owner destruction.
- Each nested free appends its entity to the free list exactly once. Normal children are nonclient entities; the worldweapon reset loops have fixed MAX_CLIENTS*2 bounds and do not acquire locks or wait.
- G_EntUnlink's retained sibling scan assumes a consistent tag list, but the new producer uses G_EntLinkToWithOffset and never writes tagInfo/tagChildren directly. No source evidence presently implicates a corrupted list; a frozen stack would be required to establish that mechanism.
- SV_SpawnServer sends final snapshots and loadingnewmap, sleeps250ms, then calls SV_ShutdownGameProgs before logging Server Initialization. SV_ClearServer subsequently resets worldweapon handles without walking the pool. Source-only review found no introduced cleanup deadlock/free-list cycle.
- During this review current qconsole advanced through mp_nuked filesystem initialization and ended with `CoDOL native collision map could not be constructed: maps/mp/mp_nuked.d3dbsp`, followed by Server Shutdown. That independently observed initialization failure is not proof of the earlier freeze's cause, but it shows this attempt passed the worldweapon teardown phase.


## Follow-up: trailing duplicate gun after initial producer deployment

Initial linked-worldweapon implementation was incomplete: it created correct native child entities but omitted the C1 network link producer. Server-only pose updates cannot supply C1's predicted parent attachment.

C1 G_EntLinkTo575630 calls52d3e0 after linking.52d3e0 publishes parent entity number+1 as WORD entityState+e8; tag configstring index as BYTE+ea (570650); flags as BYTE+eb (bit0 indicates children,bit1 no named tag). With a nonclient child and visible parent, it also writes tag-local origin to+24/+28/+2c and local orientation to+48/+4c/+50. It clears the parent word when no eligible link exists. No guessed owner clientMask was justified by this code.

Client4404a0 reads the parent and specifically compares parent-1 with predicted playerState.clientNum at4404d3, using the local predicted player pose when equal;44050b resolves the registered tag name.440cdd and later code compose the local transform with that parent/tag matrix.4419a0/441a00 also use the parent relation for rendering order. This is a concrete explanation for a world gun trailing the owner when only interpolated server world coordinates were sent. Owner draw visibility must be assessed with this real relation present, rather than forcing a per-client exclusion that would break third-person/killcam views.

Staged patch: obj/bot-worldgun-audit/link-stage/link-publication.patch. Adds generic captured link word/local transform to entity extensions, symmetric internal archive records, wire+e8 and local transform overlay, and live producer sampling after final frame worldweapon updates. All map/entity reset and snapshot/archive copy paths already handle the complete extension. Archive stream changes require a restart; no old running archive stream is reused. No live source files were changed by this follow-up worker. Red gun FX remains a separately unproven symptom; no material/effect substitution was added.
