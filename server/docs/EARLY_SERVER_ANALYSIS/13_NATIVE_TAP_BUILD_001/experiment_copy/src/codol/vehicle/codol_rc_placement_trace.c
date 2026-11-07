/* Original T5 RC placement needs a swept volume and structured result.
 * Retained IW4 physicstrace(start,end) returns a vector: keep that contract.
 * This explicit adapter implements T5 Scr_PhysicsTrace's six-argument form
 * (OpenBLOPS g_scr_main_mp.cpp7400), using the native C1 collision namespace.
 * The three mask categories are the T5 backend policy, not recovered C1 GSC.
 */
#ifdef CODOL_SERVER
#include "codol_rc_placement_trace.h"
#include "g_shared.h"
#include "server.h"
#include "scr_vm.h"
#include "cscr_variable.h"
#include "cscr_stringlist.h"
#include <math.h>
#include <string.h>

extern const char *Com_SurfaceTypeToName(int surface);
extern int CM_AreaEntities(const float *mins,const float *maxs,int *entities,int capacity,int mask);
static void key(const char *name)
{
    unsigned id=SL_GetString(name,0);
    Scr_AddArrayStringIndexed(id);
    SL_RemoveRefToString(id);
}
void CODOL_Scr_RCPlacementTrace(void)
{
    static const int category_mask[3]={42003603,529,32};
    vec3_t start,end,mins,maxs,position,normal;
    trace_t trace;
    int i,category,mask=0,ignore=ENTITYNUM_NONE,hit;
    float length;
    if(Scr_GetNumParam()!=6) {
        Scr_Error("codol_rcPlacementTrace(start,end,mins,maxs,ignored,maskCategories)");return;
    }
    Scr_GetVector(0,start);Scr_GetVector(1,end);
    Scr_GetVector(2,mins);Scr_GetVector(3,maxs);
    for(i=0;i<3;++i) {
        if(!isfinite(start[i])||!isfinite(end[i])||!isfinite(mins[i])||
           !isfinite(maxs[i])||mins[i]>maxs[i]) {
            Scr_Error("RC placement trace needs finite ordered bounds and endpoints");return;
        }
    }
    if(Scr_GetType(4)!=VAR_UNDEFINED) {
        gentity_t *entity=Scr_GetEntity(4);
        if(!entity||!entity->r.inuse||entity->s.number<0||
           entity->s.number>=ENTITYNUM_MAX_NORMAL||entity!=&g_entities[entity->s.number]) {
            Scr_ParamError(4,"ignored entity must be live");return;
        }
        ignore=entity->s.number;
    }
    category=Scr_GetInt(5);
    if(category<0||(category&~7)) {Scr_ParamError(5,"physics mask categories must be0..7");return;}
    for(i=0;i<3;++i)if(category&(1<<i))mask|=category_mask[i];
    memset(&trace,0,sizeof(trace));
    G_TraceCapsule(&trace,start,mins,maxs,end,ignore,mask);
    length=0;
    for(i=0;i<3;++i) {
        position[i]=start[i]+(end[i]-start[i])*trace.fraction;
        normal[i]=end[i]-start[i];length+=normal[i]*normal[i];
    }
    if(trace.fraction<1)memcpy(normal,trace.normal,sizeof(normal));
    else if(length>0) {length=sqrtf(length);for(i=0;i<3;++i)normal[i]/=length;}
    Scr_MakeArray();
    Scr_AddFloat(trace.fraction);key("fraction");
    Scr_AddVector(position);key("position");
    hit=Trace_GetEntityHitId(&trace);
    if(hit>=0&&hit<ENTITYNUM_MAX_NORMAL&&g_entities[hit].r.inuse)Scr_AddEntity(&g_entities[hit]);
    else Scr_AddUndefined();
    key("entity");
    Scr_AddVector(normal);key("normal");
    /* Native C1 collision surface category is five bits, unlike T5's six. */
    Scr_AddString(trace.fraction<1?Com_SurfaceTypeToName((trace.sflags>>20)&31):"none");
    key("surfacetype");
}

/* T5 Scr_BoundsWouldTelefrag6484: broadphase body/actor query followed by
 * live-player or actor filtering. T5 PM_DEAD9/ET_ACTOR14 are NOT C1 enums:
 * native C1 PM_DEAD8 and named ET_ACTOR are used here. */
void CODOL_Scr_RCBoundsWouldTelefrag(void)
{
    int entities[ENTITYNUM_MAX_NORMAL],count,i;
    vec3_t mins,maxs;
    if(Scr_GetNumParam()!=2){Scr_Error("codol_rcBoundsWouldTelefrag(mins,maxs)");return;}
    Scr_GetVector(0,mins);Scr_GetVector(1,maxs);
    for(i=0;i<3;++i)if(!isfinite(mins[i])||!isfinite(maxs[i])||mins[i]>maxs[i]) {
        Scr_Error("RC telefrag query needs finite ordered bounds");return;
    }
    count=CM_AreaEntities(mins,maxs,entities,ENTITYNUM_MAX_NORMAL,0x2800000);
    for(i=0;i<count;++i) {
        int number=entities[i];gentity_t *entity;
        if(number<0||number>=ENTITYNUM_MAX_NORMAL)continue;
        entity=&g_entities[number];
        if(entity->r.inuse&&((entity->client&&entity->client->ps.pm_type<8)||entity->s.eType==ET_ACTOR)) {
            Scr_AddInt(1);return;
        }
    }
    Scr_AddInt(0);
}
#endif
