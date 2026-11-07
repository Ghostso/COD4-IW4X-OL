# C1 native corpse snapshot trace

Offline C1 1.1.1.13 evidence; source integration and runtime validation pending.

`443c70` is an aligned per-entity rendering dispatcher. It reads type at cent+e8, bounds0..20, indexes byte table443d74 and jump table443d40. Type2 maps to case2, `443ccc`, which calls `45baf0` with the centity in edi. Type1 separately calls45b760. The earlier guessed443c60 start is table/padding and is not code evidence.

Aligned `45baf0`:
- `45bb00` rejects hidden bit10 at cent+ec (entity flags8).
- `45bb15..45bb37` resolves the DObj by entity number through25d9ed8 and2575ed8/stridec8; missing DObj exits.
- `45bb63..45bb75` type2 uses a distinct corpse-info pointer: base from6c3d284, plus entityNumber*b50+975a4. Do not substitute the player-info lookup at45bb48.
- `45bb80..45bb9e` writes entitywire9c into info+8 and wire d8/dc into info+9f4/9f8 (legs/torso).
- `45bba4..45bbb2` copies wire6c and68 floats to info+9fc/a00 before407a50.

Retained PlayerCmd_ClonePlayer copies the original player's clientNum into native es+8c, creates type2, clones animation tree and clientInfo into g_scr_data corpse storage, and captures legs/torso. The new snapshot resolver currently rejects type2. Native corpse model construction/client-info lifecycle correspondence still needs tracing before enabling an adapter.

Python alpha damage_death.md explicitly calls its corpse section a design sketch. Its later killcam.py workaround uses a spare ET_PLAYER and clients record, which is not evidence for C1's native type2 corpse protocol. Preserve the actual type2 design.

## Corpse model builder reached
Aligned `45bc40` selects the corpse-info record for type2 and passes it with the captured entityState and existing DObj to `407b80` at45bcf6. Type2 is explicitly excluded from the local-player flag at45bcad..45bcc4.

Aligned `407b80` requires info[0] nonzero and a nonempty model string at info+e0 (`407bf1..407c0b`). At407cab..407cbe it passes that string to the model resolver callback at context+92200. It then walks16 attachment name slots at info+160 with stride40, resolving each nonempty model and its string tag at slot+400 (`407cf0..407d40`). Thus an entityState-only seed is insufficient: the client corpse-info model/name population must be established first. Callback identity and corpse-info initialization are the next trace targets.

`407a50`, called later from the renderer, updates animation state; it is not the initial model-info producer. Candidate47ca94 adds800 to its DObj handle, so it must not be assumed a corpse allocator merely because it calls59a800. Guessed middle-instruction starts47ca50/47c940/4823c0/45ca70 are discarded; only aligned entry and known-branch sequences above support this note.

## Snapshot reset copies player appearance into corpse info
`46b901` is an aligned branch target stored in jump table46bae4. It reads cent+180 (wire9c/clientNum) to select cg+15ae24+clientNum*b50, and cent+e4 (entity number) to select cg+1601a4+entityNumber*b50. Flag80000 in cent+ec selects unconditional copying at46b93f.

`46ad70` copies exactly2d4 dwords (=b50 bytes) from edx/source player info to eax/destination corpse info, then processes attachment strings. The caller preserves the corpse's existing tree pointer+ae4 around that copy and passes original-player/corpse trees to63c9f0 at46b957. Aligned63c9f0 clears the destination's existing children and clones source children through63c900 when present. The clear-flag branch46b978 also copies when the corpse model string is empty or the info identity differs.

Retained PlayerCmd_ClonePlayer already copies player clientNum and setsa0000 (including80000). Required next work is validate C1 reset dispatch/type and corpse entity-number bounds, then map captured corpse flags/animation/body/weapon fields without substituting a spare player entity. No server/client structure cast: b50 is C1-only.

Pass A443ba0 table443c4c maps type2 tocase1/443bcb->45bc40; pass B separately draws it. Aligned450480 supplies the generic DObj allocator wrapper59a800; client initialization stores450480 at cg+15ae04 (`450810`). Earlier guessed4507f0 instruction alignment is discarded.

## Reset dispatch and retained clone-number range
Read C1 reset byte table46bb0c and branch table46badc as data. Type2 maps tocase2/46b901; aligned dispatcher46b829 bounds types0..20 before that lookup. This confirms the appearance-copy arm actually belongs to corpses.

Retained `_g_utils_mp.asm:G_SpawnPlayerClone` uses g_entities +9d00 +cycle*274, increments cycle modulo8 and computes the entity number from its native pointer. Since9d00=64*274, it allocates64..71. The corpse-info allocator separately scans8 slots in `_g_player_corpse_mp.asm`; those bookkeeping slots do not change the wire entity numbers.

C1's accepted corpse number range is still unverified. Do not enable those native64..71 values merely because C1 permits entity numbers below1022 generally: its corpse-specific lookup is a direct number*b50 calculation. No direct-reference hits for the candidate computed64 base18d5a4 or candidate19 base16d894 establish either range. The168514 references inspected use actor records of stride29c and are not proof of player-corpse bounds. Next evidence must come from C1's own clone allocator or corpse-array initialization.

## C1 clone allocator range established
Aligned C1 script handler51c780 takes entref and reads argument0 at51c816. At51c827..51c835 it computes `(cycle + 0x13) * 0x2cc + g_entities`;51c83c masks next cycle modulo8. It therefore allocates native C1 corpse entity19..26.51c87d/51c883 copies player's ps.clientNum into corpse wire9c, then51c897 setsa0000 including the appearance-copy flag. This matches the reset/renderer path already traced. The initial guessed51c7b0/51c760 starts are not entry evidence;51c780 is an aligned prologue.

The retained allocator64..71 is a real namespace mismatch. Before moving it, parent added a CoDOL-only null-client check in G_FreeEntityRefs' old64-slot cursor-hint cleanup scan. In-use corpse19..26 would otherwise dereference a null gclient. Readback also confirmed G_FreeEntity's ordinary free-list cutoff72 preserves reserved slots, but remaining fixed-MAX_CLIENTS handling (especially cached snapshot code) must be reviewed before relocation. Allocator not moved and corpse adapter not enabled yet. No builds/tests/runtime.

## Native clone allocation moved to19..26
CoDOL `_g_utils_mp.asm:G_SpawnPlayerClone` now uses19*274 as the entity-array base, including its classname and entity-number writes. The eight-slot cycle and retained structure stride are preserved. Non-CoDOL keeps64*274. The existing sv_maxclients registration caps CoDOL at18 and G_InitGame initializes client pointers only through level.maxclients; corpse19..26 do not overlap active player slots. Ordinary free-list cutoff72 keeps these reserved corpse slots out of generic allocation.

Connected prerequisite changes: cached player-position reconstruction now skips non-ET_PLAYER records; legacy delta player collision handling checks ET_PLAYER; Scr_GetPlayername rejects entities without clients/outside active client capacity. Together with the preceding G_FreeEntityRefs null-client fix, these remove the identified low-number-is-player assumptions. Native per-frame dispatch already routes ET_PLAYER_CORPSE before checking client pointers, and G_FreeEntity runs PlayerCorpse_Free by type. Snapshot corpse field adapter still pending; no builds/tests/runtime.

## Captured identity adapter and remaining clone fields
Added CODOL_OverlayEngineCorpseIdentity, called by the common overlay, with transactional writes of flags8, client9c, legs d8, torso dc and ground88. It validates corpse19..26 and original player0..17. Copy bit80000 is preserved from captured state, not forced on every corpse. C1 clone51caa5 writes ground7ff;51cb46..51cb58 copies ps c4/cc to es d8/dc. Retained clone writes ground3ff and the equivalent animation fields. WORLD/NONE are translated to2046/2047.

Continued aligned clone trace reaches51cc1f: when entity+180 is null,51cc28..51cc3a passes a32-byte copy from original entity+ec to corpse+ec. These correspond to eight part-visibility words in the type2 field table. Native body-pitch fields are raw float words despite int declarations, but their exact C1 mapping and visibility/ragdoll producers still require work. The server entity_seed continues to reject corpse types until the full adapter is ready. No builds/tests/runtime.

## Native visibility capture preserved
Retained hidepart/showpart/showallparts persist the four-word hide mask at entity+e4..f0; DObjSetHidePartBits copies the same four words into DObj+50. PlayerCmd_ClonePlayer did not retain this mask. Added a CoDOL-only copy from the original entity before linking the clone. It reads the source entity, not the current player appearance during serialization. This fixes native capture only; it does not establish the eight-word C1 wire mask or combined playerdata model bone correspondence. Current XSurface conversion refuses nonzero upper four source mask words, while DOBJ_MAX_PARTS is160; full skeletal capacity requires separate review. No build/test/runtime.

## Capacity and pose follow-up
Retained DObjCreate_250 adds each XModelNumBones result to its running count, subtracts128 and branches to normal construction only when the result is nonpositive. Otherwise DObjCreate_110 calls Com_Error with maximum128. The160 header constant is not the actual composed-model capacity. Loader acceptance below160 and XModelGetBoneIndex's matching check do not prove support above128. Masks in DSkel/DObj/XSurface remain four words; widening requires coordinated native layout, stack temporaries, allocation and all assembly consumers, not merely the constant.

Aligned C1 conversion40d2a0 calls40d190 (trajectories/movementDir),40d070 (animations/client identity/loop sound/weapon pair/ground/visibility),40d000 (event transfer). This inspected path does not write es68/6c. Retained BG_PlayerStateToEntityState_280 explicitly normalizes ps5cc/5d0 into esdc/e0 for prone stance, and clears those entity words outside prone. Therefore matching field order is insufficient evidence for transplanting that producer into C1 body-pose words. Trace a C1 writer before enabling that mapping; absence in this path does not prove absence elsewhere.

## C1 movement output publishes body pose
Offline pattern helper parent-c1-bodypose-leads.py produced candidate float stores only, not function alignment proof. Candidates5018f0,50c0c0,586a10 inspect unrelated interpolation/scratch structures and are not entity-pose evidence. The helper's guessed function start50cae4 is explicitly rejected; actual aligned prologue is50c8d0. Saved complete linear listing parent-c1-clientthink-pose.txt begins there.

This client-think function resolves gclient via entity+17c. At50cba7/50cbb7 it reads entity6c/68 into scratch250/254. At50cc1a/50cc22 it passes scratch138 to416c30, making the two fields movement-struct118/11c. After player-state conversion, the still-pending four-byte stack argument shifts reads to254/258:50ce89 writes the first to entity6c;50ce93 writes the second to entity68.50cea0/50cea6 also publish them to animationinfo9fc/a00. This is the actual producer path missing from BG conversion; next trace must establish how416c30 computes those fields and their native equivalent. No field-name equivalence or full corpse support claimed.

## Movement finalizer and raw-angle output leads
Aligned416c30 runs415ff0 in steps no larger than66ms, then calls416ae0 with ESI=movement and ECX=player state. Finalizer416ae0 tests target view height ps158:22/11 enter normalization; other values, including40, clear both movement118/11c. With an active transition ps160, elapsed command time is divided by duration200/400 chosen from ps164/168, clamped0..1, and inverted when direction168 is zero. It normalizes each angle by subtracting the rounded whole turns, scales it by the transition weight, and writes movement118/11c. Constants atc849c8/c849d0 are the360 and reciprocal-angle factors. The native BG conversion has equivalent normalized-angle/interpolation structure but stores its raw angles in playerState5cc/5d0.

At the inspected prone call4121f9, movement118 is passed inEDX and movement11c as the second output pointer on stack to aligned40d310. Retained PM prone code passes ps5cc and ps5d0 as the two float-pointer outputs to BG_CheckProne. Next verification is the output semantics inside those ground-check routines, before mapping native torso/waist fields. Candidate401360 also references118/11c but initializes a different e60-stride structure and is excluded. No builds/tests/runtime.
