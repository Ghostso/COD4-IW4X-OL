/* C1 52e850/52e98d supplies the projection/friction/restitution math and
 * registration defaults. OpenBLOPS game/g_missile.cpp::BounceMissile supplies
 * authoritative rolling-contact semantics and angular velocity: unlike the
 * C1 trajectory predictor, a shallow contact continues moving. This bounded
 * producer does not claim the additional wobble/curve/bump subsystem. */
#include "codol_missile_rolling.h"
#include "codol_weapon_native.h"
#include "bg_public.h"
#include "g_shared.h"
#include "cvar.h"
#include <float.h>
#include <math.h>
#include <string.h>

static cvar_t *enabled,*friction_low,*friction_high,*friction_threshold,*restitution;
static cvar_t *rest_threshold;

int CODOL_MissileBelowRestSpeed(const float velocity[3])
{
    float speed;
    if(!velocity)return 0;
    /* C1 registration52e476..52e491: default20, range0..FLT_MAX, flags84.
     * Preserve strict '<' and reject nonfinite velocity, as the retained
     * unordered/greater-or-equal branches do. Sticky policy stays in caller. */
    if(!rest_threshold)
        rest_threshold=Cvar_RegisterFloat("1193",20.0f,0.0f,FLT_MAX,0x84,
            "Grenade floor-rest speed threshold");
    if(!rest_threshold)return 0;
    speed=sqrtf(velocity[0]*velocity[0]+velocity[1]*velocity[1]+velocity[2]*velocity[2]);
    return isfinite(speed) && speed<rest_threshold->value;
}

static int rolling_parameters(void)
{
    /* C1 registration52e480..52e555,52e70e..52e732. Numeric names are the
     * actual shipped C1 dvars; English labels in T5 are reference only. */
    if(!enabled) enabled=Cvar_RegisterBool("1194",qtrue,0xc4,"Enable rolling grenade collision response");
    if(!friction_low) friction_low=Cvar_RegisterFloat("1195",0.01f,0.0f,1.0f,0x84,"Rolling grenade low-speed friction");
    if(!friction_high) friction_high=Cvar_RegisterFloat("1196",0.4f,0.0f,1.0f,0x84,"Rolling grenade high-speed friction");
    if(!friction_threshold) friction_threshold=Cvar_RegisterFloat("1197",100.0f,0.0f,FLT_MAX,0x84,"Rolling grenade friction speed threshold");
    if(!restitution) restitution=Cvar_RegisterFloat("1206",0.3f,0.0f,FLT_MAX,0x84,"Rolling grenade restitution limit");
    return enabled && friction_low && friction_high && friction_threshold && restitution;
}

int CODOL_MissileApplyRollingResponse(gentity_t *ent,const struct WeaponDef *definition,
    const float normal[3],const float incoming[3],unsigned surface)
{
    float coefficients[2],velocity[3],dot,speed,friction,factor,angles[3];
    trajectory_t *position,*rotation;
    int rolling;
    unsigned i;
    if(!ent || !normal || !incoming ||
       !CODOL_GetNativeWeaponRolling(definition,&rolling) || !rolling ||
       !CODOL_GetNativeWeaponBounce(definition,surface,coefficients) ||
       !rolling_parameters() || !enabled->boolean) return -1;
    for(i=0;i<3;++i) if(!isfinite(normal[i]) || !isfinite(incoming[i])) return -1;
    speed=sqrtf(incoming[0]*incoming[0]+incoming[1]*incoming[1]+incoming[2]*incoming[2]);
    if(!isfinite(speed) || speed<=0.0f) return -1;
    dot=incoming[0]*normal[0]+incoming[1]*normal[1]+incoming[2]*normal[2];
    if(!isfinite(dot) || dot>0.0f) return -1;
    /* Projection must use incoming velocity, not the ordinary reflection
     * already computed by retained BounceMissile before this call. */
    for(i=0;i<3;++i) velocity[i]=incoming[i]-dot*normal[i];
    speed=sqrtf(velocity[0]*velocity[0]+velocity[1]*velocity[1]+velocity[2]*velocity[2]);
    if(!isfinite(speed)) return -1;
    friction=speed<=friction_threshold->value ? friction_low->value : friction_high->value;
    for(i=0;i<3;++i) velocity[i]*=1.0f-friction;
    rolling=fabsf(dot)<25.0f;
    if(!rolling) {
        factor=fminf(1.0f-(1.0f-coefficients[1])*normal[2],
            fmaxf(restitution->value,coefficients[1]));
        for(i=0;i<3;++i) velocity[i]-=factor*dot*normal[i];
    }
    for(i=0;i<3;++i) if(!isfinite(velocity[i])) return -1;
    position=&ent->s.lerp.pos;
    rotation=&ent->s.lerp.apos;
    if(rolling) {
        BG_EvaluateTrajectory(rotation,level.time,angles);
        for(i=0;i<3;++i) if(!isfinite(angles[i])) return -1;
    }
    memcpy(position->trDelta,velocity,sizeof(velocity));
    if(rolling) {
        /* OpenBLOPS authoritative rolling radius5 and angular relation
         * 360*speed/(2*pi*radius). Integrate old pitch before rebasing so
         * successive contacts do not reset the visible rotation phase. */
        speed=sqrtf(velocity[0]*velocity[0]+velocity[1]*velocity[1]+velocity[2]*velocity[2]);
        rotation->trType=TR_LINEAR;
        rotation->trTime=level.time;
        rotation->trDuration=0;
        rotation->trBase[0]=angles[0];
        rotation->trBase[1]=atan2f(velocity[1],velocity[0])*57.29577951308232f;
        rotation->trBase[2]=90.0f;
        rotation->trDelta[0]=speed*11.459155902616465f;
        rotation->trDelta[1]=rotation->trDelta[2]=0.0f;
    }
    return rolling;
}
