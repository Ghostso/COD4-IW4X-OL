# C1 throwing-knife pickup: native branch evidence

## Passive capture, 2026-09-15

Read-only probe obj/knife-live-probe.py resolves symbols from the deployed PE,
accounts for module relocation and checks live code bytes before reading native
state. Capture obj/knife-live-43028.json belongs to build8AAD9CB3. The mounted
throwingknife_mp is engine2, ammo/clip indices2, clipSize1, clipOnly1,
sharedAmmoCap-1. This rules out a zero loaded clip capacity for this build.
Four current training bots own no knife; no live knife missile was present.
This capture cannot prove recovery or diagnose the user's failed pickup.

Follow-up source trace: G_InitGrenadeEntity gives grenade-type knives use contents
0x200000 and item identity/clientNum64; attachment settle preserves these and
relinks the same missile. Candidate and activation paths route inventory missiles
to native capacity/Touch_Item. No new confirmed fault found in those paths.
Next useful evidence is a live thrown knife and its owner's inventory/use state,
including candidate line-of-sight. Do not label this investigation a pickup fix.

Read-only C1 1.1.1.13 binary inspection; no gameplay implementation claimed.

C1 `528270` handles weapon pickup. Its missile branch (`entity+4 == 4`)
checks WeaponDef class at `+344` for 9 at `528292`. That case calls `5277b0`
with the captured weapon index and two integer arguments of 1, before the
ordinary missile trigger notification. `5277b0` validates player inventory
and accesses ammo/clip state, consistent with AddAmmo; remaining quantity
and capacity branches need full comparison before implementation.

The retained `_g_items.asm::Touch_Item_170` only emits the missile trigger
notification. It has no corresponding knife-specific ammo transfer. Thus a
generic pickup script should not be used to hide this missing native path.

C1 UI `4561e1..45621d` independently treats missile type4/class9 differently
from other grenades: the latter take the throwback hint branch, while knives
take the ordinary pickup branch. Implementing recovery requires both the
native inventory transfer and matching use/hint classification, plus checking
how settled knives remain pickup candidates and are removed after success.

OpenBLOPS `Game/Server/game/g_missile.cpp::createRetrieveableProjectile` instead
emits a six-argument stationary notification for its retrievable projectiles.
This is a useful alternative reference, but it is not evidence that C1 uses
that script-mediated path: the direct C1 pickup branch above is stronger.

## Native transfer implemented (2026-09-15)

C1 full disassembly confirms5277b0 checks held/compatible inventory, adds count to reserve, optionally fills clip, clamps stock/clip/shared cap, returns actual positive delta or0. The direct class9 missile branch528292..5282a5 passes count1/fill1 and ignores AddAmmo result because eligibility was checked earlier. Parent caller528653..528660 frees the picked entity when the branch returns1 (5727a0).

Native Add_Ammo equivalent has five cdecl arguments (player,engine weapon,variant,count,fillClip). It checks ownership/compatible weapon, capacity and returns stock+clip delta at Add_Ammo_70. New codol_knife_pickup.c calls it with captured weapon/variant and1/1 only for C1 original class9. Zero transfer refuses trigger/removal even if an upstream path admitted a full inventory. Ordinary missiles return-1 and retain existing behavior.

Touch_Item_170 now invokes that helper before its original trigger. Successful transfer continues existing pickup event, death notification atTouch_Item_140, thenG_FreeEntity. No separate ammo give and no script proxy. Existing item packed index supplies captured engine weapon and variant; no late mutable player selection is consulted.

C1 source class is retained explicitly in native core as source_weapon_class from+344, bounded to0..11 exactly matching verified source class table. Native registry query checks archive/retired archive/composed core by definition identity. Existing retained class mappings remain unchanged. Composed definitions built through native core retain metadata. No snapshot payload or archive player fields were modified.

Files changed: codol_weapon_native.c/.h, codol_asset_registry.c, new codol_knife_pickup.c/.h, _g_items.asm. Source ready; no tests/builds by this worker.

Remaining parent integration in _player_use_mp.asm: class9 missile should take item activation/touch, ordinary weapon hint without throwback timer, and item eligibility/capacity candidate filtering. Current missile path is generic trigger/use, not the type3 active/touch path. CODOL_IsKnifeDefinition(definition) exposes exact metadata classification. Full player-visible retrieval remains unclaimed until those native producer/consumer paths and actual C1 behavior are verified.

## Native use/hint routing implemented (source only)

Added CODOL_IsKnifeEntity using ET_MISSILE plus captured packed item weapon identity, resolved original C1 class9. No weapon-name guesses or retained class equality.

_player_use_mp.asm now routes a selected class9 missile directly through Touch_Item after setting its native active flag. Touch_Item owns capacity validation, ammo transfer, pickup/trigger/death notifications and deletion. Activation then clears its use handle without touching the potentially freed target. Ordinary missiles retain their prior trigger/use path.

Cursor candidate collection caches class9 before floating-point scoring in dedicated previously unused local-30fc. Existing frame subtraction310c plus saved registers leaves ESP atEBP-3118; largest outgoing argument ends atEBP-3100, so local-30fc does not overlap outgoing call storage. Existing lowest spill is-30f8. No frame size or epilogue change required.

Class9 candidates bypass grenade contents prerequisite/inner-radius/speed/outer-radius processing and grenade priority bonus, use ordinary item distance scoring and BG_CanItemBeGrabbed capacity/ownership eligibility. Classified candidates preserve full original entity type; no type mutation or shadow entity. Final hint uses captured engine weapon+4 even when weapon already owned (ammo recovery); unlike retained generic item hint, it does not suppress owned weapons. It never writes throwBackGrenadeTimeLeft. Existing snapshot hint asset capture resolves engine weapon to C1 wire identity.

Re-read C1 UI4561e1..45621d confirms missile4/class9 branches to ordinary pickup hint while other missiles take throwback hint. Native inventory transfer528292 remains strongest authoritative pickup evidence. No actual C1 interaction, tests or build performed by worker; parent review/build and gameplay observation remain necessary.

Changed in this routing increment: _player_use_mp.asm, codol_knife_pickup.c/.h. Previous metadata/ammo changes already built by parent. Source ownership released after final review.

## Parent review correction: actual item eligibility

Parent found a prior migration bug in WeaponEntCanBeGrabbed_100: ESI is entityState (assigned from the first parameter), but its +4 comparison had been changed from4 to5 with a PM_SPECTATOR comment. This is eType, not player movement type. Restored ET_MISSILE4.

Restoring type alone is insufficient: the retained missile special case tests the offhand class for1 (frag), while CoDOL knives use the extended class. With touched0, the fallback rejects an already-owned weapon. Added a native original-class9 gate for missile entities before that fallback. CODOL_KnifeCanBeGrabbed checks owned/compatible inventory exactly like Add_Ammo and uses BG_GetMaxPickupableAmmo>0. That function handles clip-only capacity (clipSize-current clip), ordinary reserve capacity, and shared ammo caps. Ordinary missile/weapon paths retain their old predicates.

Both cursor candidate BG_CanItemBeGrabbed(...,0) and Touch_Item(...,0) now reach this actual knife-capacity branch. BG_CanItemBeGrabbed's earlier clientNum rejection does not inherently reject the thrower: grenade creation initializes missile clientNum to64 at _g_missile.asm5726, outside the player0..63 range. Existing session/weapon restrictions remain.

Touch_Item clears native active byte+16c on entry before eligibility; a refused knife returns with active0, no ammo or notifications/removal, and remains available for a later use which sets active1 again. Accepted knife adds one native ammo unit then retains trigger/pickup/death/free handling. Source-only correction; no build/tests. Added _bg_misc.asm to this increment's modified files.
