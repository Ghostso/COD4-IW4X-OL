#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"

/* IW4 5f0e30..5f0f79: GetGroundPosition(origin, radius[, down[, up]]).
 * Defaults are down=1000 (738d24), up=min(radius,64) (7369b8).
 * Its Bounds has midpoint (0,0,radius) and half-size (radius,radius,radius).
 * Convert that representation to the retained trace's mins/maxs; do not
 * reuse IW4 entity-none 0x7ff in this engine's entity namespace. */
void CODOL_Scr_GetGroundPosition(void)
{
    vec3_t start,end,mins,maxs,result;
    float radius,down,up;
    trace_t trace;
    unsigned i;
    Scr_GetVector(0,start);
    radius=Scr_GetFloat(1);
    down=Scr_GetNumParam()>2 ? Scr_GetFloat(2) : 1000.0f;
    up=Scr_GetNumParam()>3 ? Scr_GetFloat(3) : (radius<64.0f ? radius : 64.0f);
    for(i=0;i<3;++i) end[i]=start[i];
    end[2]-=down;
    start[2]+=up;
    mins[0]=mins[1]=-radius; mins[2]=0.0f;
    maxs[0]=maxs[1]=radius; maxs[2]=2.0f*radius;
    G_TraceCapsule(&trace,start,mins,maxs,end,ENTITYNUM_NONE,0x820015);
    if(trace.startsolid) {
        Scr_Error("GetGroundPosition: check starts in solid");
        return;
    }
    /* Preserve the actual trace fraction, including the no-hit endpoint. */
    for(i=0;i<3;++i) result[i]=start[i]+trace.fraction*(end[i]-start[i]);
    Scr_AddVector(result);
}
#endif
