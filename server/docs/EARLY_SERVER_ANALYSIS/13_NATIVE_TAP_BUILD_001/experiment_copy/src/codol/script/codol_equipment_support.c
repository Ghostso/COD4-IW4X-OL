/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_equipment_support.h"
#include "scr_vm_functions.h"
#include "codol_radar_state.h"
#include <stdint.h>

/* C1 55caf0: makeScrambler(owner). The script mover itself emits the
 * scrambler flag; client distance/team checks decide who receives jamming.
 * This carrier and otherEntityNum already survive native entity archives. */
void CODOL_Scr_MakeScrambler(scr_entref_t ref)
{
    gentity_t *entity,*owner;
    if(Scr_GetNumParam()!=1) {
        Scr_Error("makeScrambler requires exactly one entity argument");return;
    }
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity");return;
    }
    entity=&g_entities[ref.entnum];
    if(entity->s.eType!=ET_SCRIPTMOVER) {
        Scr_ObjectError("Can only be called on a script mover");return;
    }
    if((uint32_t)entity->s.lerp.eFlags&UINT32_C(0x80000000)) {
        Scr_Error("Cannot change a 'willNeverChange' entity");return;
    }
    owner=Scr_GetEntity(0);
    if(!owner)return;
    /* C1 55cbf8 reads the actual owner entity number, not player/clientNum.
     * Any real entity is accepted; do not impose a player-only restriction. */
    entity->s.otherEntityNum=owner->s.number;
    entity->s.lerp.eFlags|=CODOL_PS_EF_RADAR_JAMMER;
}
int CODOL_OverlayEquipmentScrambler(codol_entity_state_t *wire,const entityState_t *entity)
{
    codol_entity_state_t next;
    unsigned i,found=0;
    if(!wire || !entity)return 0;
    if(entity->eType!=ET_SCRIPTMOVER)return 1;
    if(wire->type!=ET_SCRIPTMOVER)return 0;
    if(!(entity->lerp.eFlags&CODOL_PS_EF_RADAR_JAMMER))return 1;
    if(entity->otherEntityNum<0 || entity->otherEntityNum>=MAX_GENTITIES)return 0;
    next=*wire;
    for(i=0;i<CODOL_ENTITY_FIELDS;++i) {
        const codol_entity_field_t *field=CODOL_EntityField(next.type,i);
        if(!field)return 0;
        if(field->offset==0x008) {
            next.field[i]|=UINT32_C(0x200000);found|=1;
        }
        if(field->offset==0x080) {
            next.field[i]=(unsigned)entity->otherEntityNum;found|=2;
        }
    }
    if(found!=3)return 0;
    *wire=next;return 1;
}
#endif
