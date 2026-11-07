/* C1 545510 sphere VM producer; client event payload uses three floats.
 * Server ground-body impulse dispatch remains pending the native vehicle world.
 * This function implements the complete client physics event, not that solver. */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "g_shared.h"
#include "bg.h"
#include <math.h>
extern gentity_t *G_TempEntity(const vec3_t origin,int event);
void CODOL_Scr_PhysicsExplosionSphere(void)
{
    vec3_t origin;float outer,inner,magnitude;gentity_t *event;
    if(Scr_GetNumParam()!=4) {Scr_Error("physicsexplosionsphere requires origin, outer radius, inner radius, magnitude");return;}
    Scr_GetVector(0,origin);outer=Scr_GetFloat(1);inner=Scr_GetFloat(2);magnitude=Scr_GetFloat(3);
    if(!isfinite(origin[0])||!isfinite(origin[1])||!isfinite(origin[2])||
       !isfinite(outer)||!isfinite(inner)||!isfinite(magnitude)||inner<0||outer<inner) {
        Scr_Error("physicsexplosionsphere requires finite values and outer radius >= inner radius >= 0");return;
    }
    event=G_TempEntity(origin,EV_PHYS_EXPLOSION_SPHERE);
    event->s.eventParm=0;
    event->s.lerp.u.explosion.innerRadius=inner;
    event->s.lerp.u.explosion.outerRadius=outer;
    event->s.lerp.u.explosion.magnitude=magnitude;
}
#endif
