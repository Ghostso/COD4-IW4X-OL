#ifdef CODOL_SERVER
#include "scr_vm_functions.h"

/* IW4 0x5ed590/0x5ed600 clear/set turret flags bit 0x200. The retained
 * engine uses that bit for idle pitch, so G_IsTurretUsable consumes a
 * separate CoDOL flag. Allocation clears it; stance changes preserve it. */

static gentity_t *script_turret_entity(scr_entref_t ref)
{
    gentity_t *entity;
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity"); return NULL;
    }
    entity=&g_entities[ref.entnum];
    if(!entity->pTurretInfo) {
        Scr_Error("maketurretoperable/maketurretinoperable requires a turret");
        return NULL;
    }
    return entity;
}

/* IW4 0x5ed590. */
void CODOL_Scr_MakeTurretOperable(scr_entref_t ref)
{
    gentity_t *entity=script_turret_entity(ref);
    if(entity) entity->pTurretInfo->flags&=~CODOL_TURRET_OPERABLE_DISABLED;
}

/* IW4 0x5ed600 changes eligibility without forcing an occupant out. */
void CODOL_Scr_MakeTurretInoperable(scr_entref_t ref)
{
    gentity_t *entity=script_turret_entity(ref);
    if(entity) entity->pTurretInfo->flags|=CODOL_TURRET_OPERABLE_DISABLED;
}
#endif
