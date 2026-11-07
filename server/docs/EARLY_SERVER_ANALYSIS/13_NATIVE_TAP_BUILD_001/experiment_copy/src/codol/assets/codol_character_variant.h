#ifndef CODOL_CHARACTER_VARIANT_H
#define CODOL_CHARACTER_VARIANT_H
#include "codol_assets.h"
#pragma pack(push, 8)
/* C1 729090 row selection over coCharItems tables. Gender 0=male,1=female;
 * faction 0=tf,1=sc,2=zm. Only exact/shared variants are eligible. Returns
 * 1 and a borrowed column-3 value/row, 0 absent, -1 malformed input. Failure
 * preserves outputs. Geometry loading and profile defaults are separate. */
int CODOL_CharacterVariant(const codol_engine_table_t *,const char *item,const char *kind,
    unsigned gender,unsigned faction,const char *camo,const char *skin,
    unsigned *row,const char **value);
typedef struct {const char *name,*type,*group;} codol_character_item_t;
/* C1 UI group->profile/composition slot map at c309a4, indexed by ccc990.
 * Returns -1 for an unknown group; this is not DObj attachment ordering. */
int CODOL_CharacterSlotForGroup(const char *group);
/* Decimal marketplace item ID lookup; C1's last matching row wins.
 * 1 found, 0 absent, -1 invalid. Strings borrow the table's lifetime. */
int CODOL_CharacterItem(const codol_engine_table_t *,uint16_t id,codol_character_item_t *);
int CODOL_LoadCharacterItemParts(uint16_t id,codol_character_item_t *,const codol_engine_table_t **);
/* Mounted marketplace -> part table -> measured model-variant selection.
 * Item zero is unresolved here: character-default selection belongs upstream.
 * This resolves names only; callers must load geometry before publication. */
int CODOL_LoadCharacterItemModel(uint16_t id,unsigned gender,unsigned faction,
    const char *camo,const char *skin,const char **model);
/* The same selection, additionally returning the selected row's column 4.
 * That column is the item's first-person "vmchar" model and exists only for
 * the jacket (fja) and glove (han) tables; every other part table leaves it
 * empty. *viewmodel is set to NULL when the row has no column 4 or the table
 * is narrower than five columns, which is not a failure. Both outputs borrow
 * the mounted table's storage and are preserved unless the call returns 1. */
int CODOL_LoadCharacterItemModels(uint16_t id,unsigned gender,unsigned faction,
    const char *camo,const char *skin,const char **model,const char **viewmodel);
/* C1 729d50: the player's skin tone, taken from the head item itself.
 *
 * The caller passes composition slot 4 (the head/identity item). C1 requires
 * that item's marketplace type to be "cha" (primary category 3, 729530) and
 * its group to be "hea" (subcategory 0x12 through the group table at c30978),
 * then reads column 3 of the *last* case-insensitive column-0 match in
 * mp/coCharItems/hea.csv - the raw row, not the gender/faction variant - and
 * copies the three bytes at strlen(item)+6 when the model name is at least
 * strlen(item)+9 long. Every other case yields C1's own default, "wht".
 *
 * So "hea_hernandez" -> "hea_hernandez_ss_m_yel_00" -> "yel". Always writes
 * four bytes and always succeeds; the return value distinguishes a resolved
 * tone (1) from the default (0). This is the skin argument of the variant
 * matcher, not its camouflage argument: C1 keeps those in separate fields
 * (the character context's +0xb8 camouflage and this three-byte tone). */
int CODOL_CharacterSkinTone(uint16_t head_item,char out[4]);
/* C1 60d020: fill zero entries among eighteen composition slots from
 * character table columns 3..20, resolving default names through marketplace.
 * Explicit character identity; profile-to-composition mapping is separate.
 * Returns 1 success (including missing defaults), 0 malformed; atomic. */
int CODOL_ApplyCharacterDefaults(const codol_engine_table_t *market,
    const codol_engine_table_t *characters,uint16_t character_item,uint16_t slots[18]);
/* C1 60d090: source item slot 5 selects coChestRigs column 0; an exact "1"
 * in column 2+selector applies column-1 item to slot 15. Last active row wins.
 * Selector follows the weapon-class mapping in CODOL_ChestRigSelector.
 * Returns 1 success, 0 malformed. Atomic; no active row preserves slot 15. */
int CODOL_ApplyCharacterChestRig(const codol_engine_table_t *market,
    const codol_engine_table_t *rigs,unsigned selector,uint16_t slots[18]);
/* C1 611ba0: classes 0..4 map to 0,4,2,1,3. Other classes leave the
 * previous selector unchanged and return zero. Uses CoDOL weapon classes. */
int CODOL_ChestRigSelector(unsigned weapon_class,unsigned *selector);
/* C1 60d220: inspect the last matching item's column-3 string at
 * strlen(item)+6. A digit or too-short string forbids composition slot 7.
 * This uses the raw last row, not the gender/faction variant matcher.
 * 1 queried (including absent=false), 0 malformed; failure preserves output. */
int CODOL_CharacterSlot7Allowed(const codol_engine_table_t *parts,const char *item,int *allowed);
#pragma pack(pop)
#endif
