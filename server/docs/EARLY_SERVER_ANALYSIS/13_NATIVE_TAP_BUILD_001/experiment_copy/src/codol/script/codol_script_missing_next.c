#ifdef CODOL_SERVER
#include "codol_script_missing_next.h"
#include "q_shared.h"
#include "q_math.h"
#include "qcommon_io.h"
#include "entity.h"
#include "player.h"
#include "dobj.h"
#include "g_shared.h"
#include "server.h"
#include "scr_vm.h"
#include "scr_vm_functions.h"

/* Entity use/collision state. Evidence and reference addresses are in
 * codol_script_missing_next.h; only native field names are used here, IW4
 * offsets are never reused as native offsets. */

static gentity_t *use_state_entity(scr_entref_t ref)
{
    gentity_t *entity;

    /* The IW4 handlers reject every non-entity receiver form before touching
     * the entity array: they test the high half of the entref and raise the
     * object error. Client, struct and array receivers all land there. */
    if(ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("Not an entity");
        return NULL;
    }
    entity = &g_entities[ref.entnum];
    /* A freed entity still has a slot; writing contents or eFlags into it and
     * relinking would resurrect a dead slot in the world tree. */
    if(!entity->r.inuse) {
        Scr_ObjectError("Entity is not in use");
        return NULL;
    }
    return entity;
}

/* IW4 0x5efee0.
 *
 * Publishes the use-trigger content bit, so the retained player-use trace
 * (_player_use_mp.asm, mask 0x200000) starts offering the entity to
 * "+activate", and gives the entity the engine's default cursor hint when the
 * map or script has not chosen one - otherwise a script-spawned trigger would
 * become usable with no hint at all. Vehicles additionally carry the usable
 * state in spawnflags bit 0, the same representation the native vehicle path
 * uses (CODOL_Scr_MakeVehicleUsable), so both stay in agreement.
 *
 * The relink is what makes the new contents reach the world tree; IW4 tail
 * calls SV_LinkEntity for exactly that reason. */
void CODOL_Scr_MakeUsable(scr_entref_t ref)
{
    gentity_t *entity = use_state_entity(ref);

    if(!entity)
        return;

    if(entity->scr_vehicle)
        entity->spawnflags |= 1;

    entity->r.contents |= CODOL_CONTENTS_TRIGGER;

    if(entity->s.un2 == 0)
        entity->s.un2 = CODOL_CURSORHINT_DEFAULT;

    SV_LinkEntity(entity);
}

/* IW4 0x5eff40.
 *
 * The inverse, minus the cursor hint: IW4 leaves the hint alone so a later
 * MakeUsable() restores the object with the hint the script picked. Clearing
 * the content bit is enough to take the entity out of the use trace. */
void CODOL_Scr_MakeUnusable(scr_entref_t ref)
{
    gentity_t *entity = use_state_entity(ref);

    if(!entity)
        return;

    if(entity->scr_vehicle)
        entity->spawnflags &= ~1;

    entity->r.contents &= ~CODOL_CONTENTS_TRIGGER;

    SV_LinkEntity(entity);
}

/* IW4 0x5eff90 / 0x5effe0.
 *
 * EF_SOFT is a published flag, not a link property, so neither handler
 * relinks. A player receiver carries it in its playerState, which the native
 * BG_PlayerStateToEntityState copy then republishes in the player's
 * entityState; every other entity carries it directly in its entityState. */
static void set_soft_state(scr_entref_t ref, int soft)
{
    gentity_t *entity = use_state_entity(ref);

    if(!entity)
        return;

    if(entity->client) {
        if(soft)
            entity->client->ps.eFlags |= CODOL_EF_SOFT;
        else
            entity->client->ps.eFlags &= ~CODOL_EF_SOFT;
        return;
    }

    if(soft)
        entity->s.lerp.eFlags |= CODOL_EF_SOFT;
    else
        entity->s.lerp.eFlags &= ~CODOL_EF_SOFT;
}

void CODOL_Scr_MakeSoft(scr_entref_t ref)
{
    set_soft_state(ref, 1);
}

void CODOL_Scr_MakeHard(scr_entref_t ref)
{
    set_soft_state(ref, 0);
}

int CODOL_ScriptEntityIsUsable(const struct gentity_s *entity)
{
    if(!entity || !entity->r.inuse)
        return 0;
    return (entity->r.contents & CODOL_CONTENTS_TRIGGER) != 0;
}

int CODOL_ScriptEntityIsSoft(const struct gentity_s *entity)
{
    if(!entity || !entity->r.inuse)
        return 0;
    if(entity->client)
        return (entity->client->ps.eFlags & CODOL_EF_SOFT) != 0;
    return (entity->s.lerp.eFlags & CODOL_EF_SOFT) != 0;
}
#endif

