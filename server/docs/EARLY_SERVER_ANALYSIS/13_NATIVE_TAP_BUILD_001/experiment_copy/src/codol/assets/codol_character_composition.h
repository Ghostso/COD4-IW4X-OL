#ifndef CODOL_CHARACTER_COMPOSITION_H
#define CODOL_CHARACTER_COMPOSITION_H
#include "codol_profile.h"
#define CODOL_COMPOSITION_SLOTS 18
typedef struct {
    unsigned character_index;
    uint16_t items[CODOL_COMPOSITION_SLOTS];
    const char *models[CODOL_COMPOSITION_SLOTS];      /* Third-person XModel per slot; NULL when none. */
    const char *viewmodels[CODOL_COMPOSITION_SLOTS];  /* Column-4 first-person model; only fja/han have one. */
} codol_character_composition_t;
/* Explicit player profile and visual context -> adjusted items and model names.
 * Names borrow mounted tables. No profile writes/configstring publication.
 * Returns 1 when name resolution finishes, including sparse selections;
 * this does not guarantee a complete outfit or available geometry.
 * Returns 0 unavailable/invalid, preserving output on failure.
 * Caller must validate geometry and publish in DObj order, including viewhands. */
int CODOL_ComposeProfileCharacter(const uint8_t *,size_t,const codol_structured_schema_t *,
    const char *faction,unsigned gender,const char *camo,const char *skin,
    unsigned rig_selector,codol_character_composition_t *);
/* The same composition with the skin tone taken from the profile's own head
 * item, the way C1 derives it (CODOL_CharacterSkinTone). The resolved tone is
 * reported through skin, which may be NULL when the caller does not need it.
 * Camouflage remains an explicit input: C1 keeps it in the character context
 * and this module has no measured producer for it. */
int CODOL_ComposeProfileCharacterAuto(const uint8_t *,size_t,const codol_structured_schema_t *,
    const char *faction,unsigned gender,const char *camo,
    unsigned rig_selector,codol_character_composition_t *,char skin[4]);
/* The sex mp/cyborgclasstable.csv gives the profile's zombies character.
 * 1 resolved into *gender (0 male, 1 female), 0 the profile's zombies head is
 * not one of the four roster characters, -1 unusable table/profile. Output is
 * preserved unless the call returns 1. */
int CODOL_ZombieCharacterGender(const uint8_t *,size_t,const codol_structured_schema_t *,
    unsigned *gender);
/* The mp/cyborgclasstable.csv row of the profile's zombies character (matched
 * by head identity, column 3). 1 resolved (*row, and *roster when non-NULL),
 * 0 no roster character, -1 unusable table/profile. */
/* roster receives the codol_engine_table_t (codol_assets.h), passed as void
 * so this header need not include the asset layer. */
int CODOL_ZombieCharacterRow(const uint8_t *,size_t,const codol_structured_schema_t *,
    int *row,const void **roster);
#endif
