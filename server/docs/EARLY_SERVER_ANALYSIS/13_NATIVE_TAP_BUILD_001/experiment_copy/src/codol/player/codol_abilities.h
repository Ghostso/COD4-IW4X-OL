#ifndef CODOL_ABILITIES_H
#define CODOL_ABILITIES_H
#include "codol_assets.h"
#include "codol_clients.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    unsigned id;
    int value_slot; /* -1 for a modifier without a value. */
    int has_default;
    float default_value;
} codol_ability_definition_t;
/* Columns 1 -> 0,2,3 of coAbilityModifiersTable. Last matching name wins,
 * ASCII case-insensitive, as C1 61ed00/6283d0. Malformed numeric fields are
 * rejected rather than accepting an out-of-range index. 1 found,0 absent,-1
 * invalid; output unchanged on failure. */
int CODOL_ReadAbilityDefinition(const codol_engine_table_t *,const char *,codol_ability_definition_t *);
/* C1 402f20: decimal ID text in column0 -> value slot in column2, last
 * matching row. Slot output unchanged unless found; 1 found,0 absent,-1 bad. */
int CODOL_ReadAbilityValueSlot(const codol_engine_table_t *,unsigned id,unsigned *slot);
/* Native consumers test the mask first, then resolve the value slot by ID.
 * 0 inactive (table unnecessary),1 active value,-1 invalid active mapping.
 * Never initializes defaults or mutates state; value output is transactional. */
int CODOL_GetActiveAbilityValue(const codol_client_abilities_t *,const codol_engine_table_t *,
                                unsigned id,float *value);
/* Set initializes an available default then sets the MSB-first mask bit.
 * SetValue writes the supplied value directly, independently of that bit.
 * These are VM operations, not the higher-level perk accumulation policy. */
int CODOL_SetAbility(codol_client_abilities_t *,const codol_ability_definition_t *);
int CODOL_SetAbilityValue(codol_client_abilities_t *,const codol_ability_definition_t *,float);
/* Unset/Clear change only masks; stored values survive (C1 518842,
 * 5188da..5188f8). Has returns 0/1 through out, unchanged on invalid input. */
int CODOL_UnsetAbility(codol_client_abilities_t *,const codol_ability_definition_t *);
void CODOL_ClearAbilities(codol_client_abilities_t *);
int CODOL_HasAbility(const codol_client_abilities_t *,const codol_ability_definition_t *,int *out);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
