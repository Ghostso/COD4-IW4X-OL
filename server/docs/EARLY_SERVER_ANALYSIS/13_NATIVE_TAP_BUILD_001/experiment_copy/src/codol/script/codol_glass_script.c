/* C1 glass script producers: 54a0e0(origin),54a1c0(query),54a2c0(shatter),54a410(remove). */
#ifdef CODOL_SERVER
#include "g_shared.h"
#include "scr_vm_functions.h"
#include "codol_glass_world.h"
#include <math.h>
static int glass_id(unsigned minimum,unsigned maximum)
{
    int index;
    unsigned count=Scr_GetNumParam();
    if (count<minimum || count>maximum) { Scr_Error("wrong number of glass function parameters");return -1; }
    index=Scr_GetInt(0);
    if (!CODOL_GlassWorldEnsureMap()) { Scr_Error("active map glass data is unavailable");return -1; }
    if (index<0 || (unsigned)index>=CODOL_GlassWorldCount()) {
        Scr_ParamError(0,"glass ID is outside the active map's piece array");return -1;
    }
    return index;
}
void CODOL_Scr_GetGlassOrigin(void)
{
    vec3_t origin;
    int index=glass_id(1,1);
    if (index<0) return;
    CODOL_GlassWorldOrigin(index,origin);Scr_AddVector(origin);
}
void CODOL_Scr_IsGlassDestroyed(void)
{
    int index=glass_id(1,1);
    if (index>=0) Scr_AddInt(CODOL_GlassWorldState(index)>=2);
}
void CODOL_Scr_DestroyGlass(void)
{
    vec3_t direction={0,0,0};
    unsigned i;
    int index=glass_id(1,2);
    if (index<0) return;
    if (Scr_GetNumParam()==2) Scr_GetVector(1,direction);
    for (i=0;i<3;++i) if (!isfinite(direction[i])) {
        Scr_ParamError(1,"glass impact direction must be finite");return;
    }
    CODOL_GlassWorldShatter(index,direction,level.time);
}
void CODOL_Scr_DeleteGlass(void)
{
    int index=glass_id(1,1);
    if (index>=0) CODOL_GlassWorldRemove(index,level.time);
}
#endif
