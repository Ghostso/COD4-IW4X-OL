#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "bg_public.h"
#include "xassets/weapondef.h"
#include <stddef.h>
#include <string.h>
extern "C" {
#include "codol_weapon_lock.h"
}

static_assert(offsetof(gentity_t,missileTargetEnt)==0x214,
              "native missile target handle offset changed");
static_assert(offsetof(gentity_t,missile)+offsetof(missile_ent_t,targetOffset)==0x1dc,
              "native missile target offset changed");
static_assert(offsetof(gentity_t,missile)+offsetof(missile_ent_t,flightMode)==0x1ec,
              "native missile trajectory flight-mode offset changed");
static_assert(offsetof(entityState_t,lerp)+offsetof(LerpEntityState,u)+
              offsetof(LerpEntityStateMissile,flightMode)==0x58,
              "captured missile mode must alias archived anonymous.data[1]");

static gentity_t *rocket_argument(scr_entref_t ref,bool rejectGrenade=true)
{
    if(ref.classnum || ref.entnum>=ENTITYNUM_WORLD) {
        Scr_ObjectError("Not an entity");
        return NULL;
    }
    gentity_t *entity=&g_entities[ref.entnum];
    /* IW4 0x5eddd0 checks the rocket classname and rejects the grenade
     * weapon class through 0x4bfda0. Use native enum values, not IW4's 6. */
    if(entity->classname!=scr_const.rocket ||
       (rejectGrenade && BG_GetWeaponDef(entity->s.weapon)->weapClass==WEAPCLASS_GRENADE)) {
        Scr_Error("Entity is not a rocket");
        return NULL;
    }
    return entity;
}
/* IW4 5ede70 and C1 5381a0 check classname and persistent lock state;
 * neither checks the weapon class or consumes script arguments. */
static void set_flight_mode(scr_entref_t ref,MissileFlightMode mode)
{
    gentity_t *entity=rocket_argument(ref,false);
    if(!entity)return;
    if(!codol_missile_lock_active[ref.entnum]) {
        Scr_Error(va("Entity %i is not locked on to anything.",ref.entnum));
        return;
    }
    entity->missile.flightMode=mode;
    entity->s.lerp.u.missile.flightMode=mode;
}
extern "C" void CODOL_Scr_MissileSetFlightModeDirect(scr_entref_t ref)
{ set_flight_mode(ref,MISSILEFLIGHTMODE_DIRECT); }
extern "C" void CODOL_Scr_MissileSetFlightModeTop(scr_entref_t ref)
{ set_flight_mode(ref,MISSILEFLIGHTMODE_TOP); }

extern "C" void CODOL_Scr_MissileClearTarget(scr_entref_t ref)
{
    gentity_t *entity=rocket_argument(ref);
    if(!entity)return;
    /* Retained MissileTrajectory gates homing on the entity handle or
     * CoDOL point-target state. Clear both through their owning APIs.
     * Preserve velocity, flight mode, and flight stage, as IW4 does. */
    entity->missileTargetEnt.setEnt(NULL);
    CODOL_ResetMissilePosition(ref.entnum);
    memset(entity->missile.targetOffset,0,sizeof(entity->missile.targetOffset));
}
#endif
