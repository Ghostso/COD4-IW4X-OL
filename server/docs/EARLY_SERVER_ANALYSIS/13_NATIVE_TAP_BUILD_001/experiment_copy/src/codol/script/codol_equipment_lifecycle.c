/* Native equipment lifecycle notifications. */
#ifdef CODOL_SERVER
#include "g_shared.h"
#include "entity.h"
#include "scr_vm_functions.h"
#include "cscr_stringlist.h"
#include "bg_public.h"
#include "scr_vm.h"

/* G_Damage's weapon parameter is an engine index, not a client wire index.
 * Script notify arguments are pushed in reverse order, so this is pushed
 * before damage flags and becomes the tenth damage notification argument. */
void CODOL_AddDamageWeaponArgument(int weapon)
{
    const struct WeaponDef *def;
    if(weapon < 0 || weapon >= BG_GetNumWeapons()) {
        Scr_AddUndefined();
        return;
    }
    def = BG_GetWeaponDef(weapon);
    if(!def || !def->szInternalName || !*def->szInternalName) {
        Scr_AddUndefined();
        return;
    }
    Scr_AddString(def->szInternalName);
}

/* Call only with the live G_Damage receiver and already-pushed arguments.
 * Always dispatch the notification, consuming those VM arguments. A waiter
 * may delete the receiver and even allocate another entity in the same slot;
 * neither case may continue through the old receiver's pain/death handler. */
int CODOL_NotifyDamageEntity(gentity_t *entity, unsigned notify, unsigned count)
{
    int generation = entity->useCount;
    Scr_Notify(entity, notify, count);
    return entity->r.inuse && entity->useCount == generation;
}

/* T5 g_missile.cpp BounceMissile emits stationary with no parameters only
 * after settling. The caller captures the entry trajectory and excludes
 * airborne bounces and repeated stationary collisions. C1 registers the
 * same notification string at 578551..57856a. The shipped IW4 GSC also
 * waits for missile_stuck with the impact entity as its sole argument.
 * Its exact C1 native notification order has not been established. */
int CODOL_NotifyMissileStationary(gentity_t *entity)
{
    gentity_t *target=NULL;
    unsigned notify;
    unsigned hit;
    int generation,target_generation=0;
    if(!entity || !entity->r.inuse || entity->s.eType!=ET_MISSILE)return 0;
    generation=entity->useCount;
    hit=(unsigned)entity->s.groundEntityNum;
    if(hit<ENTITYNUM_WORLD && g_entities[hit].r.inuse) {
        target=&g_entities[hit];
        target_generation=target->useCount;
    }
    notify=SL_GetString("stationary",0);
    Scr_Notify(entity,notify,0);
    SL_RemoveRefToString(notify);
    /* Waiters may delete or convert their receiver. Never let the impact
     * caller emit further missile events against that freed/reused slot. */
    if(!entity->r.inuse || entity->useCount!=generation ||
       entity->s.eType!=ET_MISSILE)return 0;
    if(target && target->r.inuse && target->useCount==target_generation)
        Scr_AddEntity(target);
    else
        Scr_AddUndefined();
    notify=SL_GetString("missile_stuck",0);
    Scr_Notify(entity,notify,1);
    SL_RemoveRefToString(notify);
    return entity->r.inuse && entity->useCount==generation &&
        entity->s.eType==ET_MISSILE;
}
#endif
