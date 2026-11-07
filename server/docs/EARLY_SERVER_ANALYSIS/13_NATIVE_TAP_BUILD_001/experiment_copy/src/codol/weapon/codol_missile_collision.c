/* Native C1 sticky collision policy; never reads IW3 WeaponDef.stickiness. */
#ifdef CODOL_SERVER
#include "codol_missile_stickiness.h"
#include "entity.h"
#include "cm_public.h"
#include "codol_sentient.h"

int CODOL_NativeMissileStickinessMode(const struct WeaponDef *definition)
{
    codol_missile_stickiness_t metadata;
    if(!CODOL_GetNativeWeaponMissileStickiness(definition,&metadata))return -1;
    return metadata.mode;
}
/* Low byte: C1 mode. Bit8: collision may settle against this receiver.
 * T5 BounceMissile separates ground/all modes and excludes sentients for
 * all-no-sentients. Resolve actual native target identity, not C1 offsets. */
int CODOL_NativeMissileCollisionPolicy(const struct WeaponDef *definition,trace_t *trace)
{
    int mode=CODOL_NativeMissileStickinessMode(definition),may_stop=1;
    unsigned target=(unsigned)(unsigned short)Trace_GetEntityHitId(trace);
    gentity_t *hit=target<ENTITYNUM_WORLD ? &g_entities[target] : NULL;
    if(mode<0)return 0;
    if(hit && hit->r.inuse) {
        int sentient=hit->s.eType==ET_PLAYER || CODOL_Sentient_ForEntity(hit)!=NULL;
        if(sentient && mode!=CODOL_STICK_NONE && mode!=CODOL_STICK_ALL &&
           mode!=CODOL_STICK_FLESH)may_stop=0;
        if(hit->s.eType==ET_MISSILE && mode!=CODOL_STICK_GROUND_WITH_YAW)may_stop=0;
    }
    return mode|(may_stop?0x100:0);
}
#endif
