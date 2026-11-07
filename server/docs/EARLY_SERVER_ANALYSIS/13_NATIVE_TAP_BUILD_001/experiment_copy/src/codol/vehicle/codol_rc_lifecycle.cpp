/* T5 RC script interface adaptation. C1 has no proven T5 eFlags2 analogue:
 * these flags remain server-owned and have explicit native/script consumers.
 * Stun suppresses driving demands; countdown/timeout notify presentation.
 * They are never copied into unrelated C1 entity flags. */
#ifdef CODOL_SERVER
#include "codol_rc_lifecycle.h"
#include "codol_vehicle_ground_runtime.h"
#include "codol_vehicle_native.h"
#include "g_shared.h"
#include "g_scr_vehicle.h"
#include "cscr_stringlist.h"
#include <cstring>
namespace {
struct state_t { unsigned generation;int initialized,owner,owner_generation;unsigned flags; };
state_t states[ENTITYNUM_MAX_NORMAL];
bool valid(const gentity_t *e) {
    return e&&e->s.number>=0&&e->s.number<ENTITYNUM_MAX_NORMAL&&e==&g_entities[e->s.number]&&
        e->r.inuse&&e->s.eType==ET_VEHICLE&&CODOL_GroundVehicleOwned(e);
}
state_t *state(const gentity_t *e) {
    if(!valid(e))return NULL;
    state_t &s=states[e->s.number];
    if(!s.initialized||s.generation!=(unsigned)e->useCount) {
        std::memset(&s,0,sizeof(s));s.initialized=1;s.generation=(unsigned)e->useCount;s.owner=-1;
    }
    return &s;
}
gentity_t *receiver(scr_entref_t ref) {
    if(ref.classnum||ref.entnum>=ENTITYNUM_MAX_NORMAL||!valid(&g_entities[ref.entnum])) {
        Scr_ObjectError("method requires an owned native RC vehicle");return NULL;
    }
    return &g_entities[ref.entnum];
}
void flagMethod(scr_entref_t ref,int operation) {
    gentity_t *e=receiver(ref);if(!e)return;
    if(Scr_GetNumParam()!=1){Scr_Error("vehicle client flag requires one integer index");return;}
    int bit=Scr_GetInt(0);if((unsigned)bit>=16){Scr_ParamError(0,"vehicle client flag index must be0..15");return;}
    state_t *s=state(e);unsigned mask=1u<<bit;
    if(operation==0){Scr_AddInt((s->flags&mask)!=0);return;}
    const unsigned next=operation>0?s->flags|mask:s->flags&~mask;
    if(next==s->flags)return;
    s->flags=next;
    // Original T5 CSC flags9/1/2 are identified by pinned _clientflags.gsc.
    // C1 presentation is adapted by server GSC consuming this transition;
    // no T5 CSC is injected into the C1 client. No entity use after notify.
    unsigned event=SL_GetString("codol_vehicle_clientflag",0);
    Scr_AddInt(operation>0);Scr_AddInt(bit);Scr_Notify(e,event,2);
    SL_RemoveRefToString(event);
}
}
extern "C" void CODOL_Scr_VehicleSetOwner(scr_entref_t ref) {
    gentity_t *e=receiver(ref);if(!e)return;
    if(Scr_GetNumParam()!=1){Scr_Error("setowner requires one player entity");return;}
    gentity_t *p=Scr_GetEntity(0);
    if(!p||!p->r.inuse||!p->client||p->s.number<0||p->s.number>=32||p!=&g_entities[p->s.number]) {
        Scr_ParamError(0,"setowner requires a live C1 player");return;
    }
    state_t *s=state(e);s->owner=p->s.number;s->owner_generation=p->useCount;
    // C1 native vehicle ownership presentation uses entityState.clientNum at
    // wire74. T5 packed faction bits and C1 exclusive remote r.ownerNum are
    // separate contracts; neither is overwritten with the other's encoding.
    CODOL_CaptureVehicleSpawnClient(e,p);
}
extern "C" void CODOL_Scr_VehicleGetClientFlag(scr_entref_t r){flagMethod(r,0);}
extern "C" void CODOL_Scr_VehicleSetClientFlag(scr_entref_t r){flagMethod(r,1);}
extern "C" void CODOL_Scr_VehicleClearClientFlag(scr_entref_t r){flagMethod(r,-1);}
extern "C" int CODOL_RCVehicleStunned(const gentity_t *e) {
    state_t *s=state(e);return s&&(s->flags&(1u<<9));
}
extern "C" gentity_t *CODOL_RCVehicleOwner(const gentity_t *e) {
    state_t *s=state(e);if(!s||s->owner<0||s->owner>=32)return NULL;
    gentity_t *p=&g_entities[s->owner];
    return p->r.inuse&&p->client&&p->useCount==s->owner_generation?p:NULL;
}
extern "C" void CODOL_RCEntityFreed(const gentity_t *e) {
    if(!e||e->s.number<0||e->s.number>=ENTITYNUM_MAX_NORMAL)return;
    state_t &s=states[e->s.number];
    if(s.initialized&&s.generation==(unsigned)e->useCount)std::memset(&s,0,sizeof(s));
}
extern "C" void CODOL_RCResetLifecycle(void){std::memset(states,0,sizeof(states));}
#endif
