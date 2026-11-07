/* C1 ability modifiers. SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_abilities.h"
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
static int same_name(const char *a,const char *b)
{
    unsigned x,y;
    do {
        x=(unsigned char)*a++; y=(unsigned char)*b++;
        if(x>='A' && x<='Z') x+='a'-'A';
        if(y>='A' && y<='Z') y+='a'-'A';
        if(x!=y) return 0;
    } while(x);
    return 1;
}
static int index_value(const char *text,unsigned limit,unsigned *out)
{
    char *end; long value;
    if(!text || !*text) return 0;
    value=strtol(text,&end,10);
    if(end==text || *end || value<0 || (unsigned long)value>=limit) return 0;
    *out=(unsigned)value; return 1;
}
int CODOL_ReadAbilityDefinition(const codol_engine_table_t *table,const char *name,codol_ability_definition_t *out)
{
    codol_ability_definition_t result={0,-1,0,0}; int row; unsigned slot;
    if(!table || !name || !*name || !out || table->rowCount<0 || table->columnCount<4 ||
       (table->rowCount && !table->values)) return -1;
    for(row=table->rowCount-1;row>=0;--row) {
        const char *const *cells=table->values+(size_t)row*table->columnCount;
        if(!cells[1] || !same_name(cells[1],name)) continue;
        if(!index_value(cells[0],128,&result.id) || !cells[2] || !cells[3]) return -1;
        if(*cells[2]) {
            if(!index_value(cells[2],CODOL_ABILITY_VALUES,&slot)) return -1;
            result.value_slot=(int)slot;
            if(*cells[3]) {
                char *end; double value=strtod(cells[3],&end);
                if(end==cells[3] || *end || !isfinite(value) || value>3.4028234663852886e38 ||
                   value< -3.4028234663852886e38) return -1;
                result.default_value=(float)value; result.has_default=1;
            }
        }
        *out=result; return 1;
    }
    return 0;
}
static int valid_definition(const codol_ability_definition_t *definition)
{
    return definition && definition->id<128 && definition->value_slot>=-1 &&
        definition->value_slot<CODOL_ABILITY_VALUES &&
        (!definition->has_default || (definition->value_slot>=0 && isfinite(definition->default_value)));
}
int CODOL_ReadAbilityValueSlot(const codol_engine_table_t *table,unsigned id,unsigned *out)
{
    char key[4]; int row;
    if(!table || !out || id>=128 || table->rowCount<0 || table->columnCount<3 ||
       (table->rowCount && !table->values) ||
       (size_t)table->rowCount>SIZE_MAX/sizeof(*table->values)/(size_t)table->columnCount) return -1;
    snprintf(key,sizeof(key),"%u",id);
    for(row=table->rowCount-1;row>=0;--row) {
        const char *const *cells=table->values+(size_t)row*table->columnCount;
        unsigned slot;
        /* C1 formats the ID before string lookup, so "00" is not ID zero. */
        if(!cells[0] || !same_name(cells[0],key)) continue;
        if(!cells[2] || !*cells[2]) return 0;
        if(!index_value(cells[2],CODOL_ABILITY_VALUES,&slot)) return -1;
        *out=slot; return 1;
    }
    return 0;
}
int CODOL_GetActiveAbilityValue(const codol_client_abilities_t *state,const codol_engine_table_t *table,
                               unsigned id,float *out)
{
    unsigned slot;
    if(!state || !out || id>=128) return -1;
    if(!(state->masks[id>>5] & (UINT32_C(0x80000000)>>(id&31)))) return 0;
    if(CODOL_ReadAbilityValueSlot(table,id,&slot)!=1 || !isfinite(state->values[slot])) return -1;
    *out=state->values[slot]; return 1;
}
int CODOL_SetAbility(codol_client_abilities_t *state,const codol_ability_definition_t *definition)
{
    if(!state || !valid_definition(definition)) return 0;
    /* C1 5185fe..51862e calls default initializer403090 before OR. */
    if(definition->has_default) state->values[definition->value_slot]=definition->default_value;
    state->masks[definition->id>>5]|=UINT32_C(0x80000000)>>(definition->id&31);
    return 1;
}
int CODOL_SetAbilityValue(codol_client_abilities_t *state,const codol_ability_definition_t *definition,float value)
{
    if(!state || !valid_definition(definition) || definition->value_slot<0 || !isfinite(value)) return 0;
    /* C1 5189cb..5189ff has no default addition, clamp or mask update. */
    state->values[definition->value_slot]=value; return 1;
}
int CODOL_UnsetAbility(codol_client_abilities_t *state,const codol_ability_definition_t *definition)
{
    if(!state || !valid_definition(definition)) return 0;
    state->masks[definition->id>>5]&=~(UINT32_C(0x80000000)>>(definition->id&31));
    return 1;
}
void CODOL_ClearAbilities(codol_client_abilities_t *state)
{
    if(state) memset(state->masks,0,sizeof(state->masks));
}
int CODOL_HasAbility(const codol_client_abilities_t *state,const codol_ability_definition_t *definition,int *out)
{
    if(!state || !out || !valid_definition(definition)) return 0;
    /* C1 51871e..51873d normalizes the masked word to integer 0/1. */
    *out=!!(state->masks[definition->id>>5] & (UINT32_C(0x80000000)>>(definition->id&31)));
    return 1;
}
