#include "scr_vm_functions.h"
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
gentity_t g_entities[MAX_GENTITIES];
static unsigned calls,errors;
static unsigned angle_calls;
static float delta,received[3];
float Scr_GetFloat(unsigned index) { assert(!index); return delta; }
void G_SetAngle(gentity_t *entity,const float *angles)
{ assert(entity==&g_entities[3]); ++angle_calls; memcpy(received,angles,sizeof(received)); }
void Scr_ObjectError(const char *message) { assert(message); ++errors; }
void Scr_Error(const char *message) { assert(message && *message); ++errors; }
void ScrCmd_Delete(scr_entref_t ref) { assert(ref.entnum==3); ++calls; }
void ScrCmd_Show(scr_entref_t ref) { assert(ref.entnum==3); ++calls; }
void ScrCmd_Hide(scr_entref_t ref) { assert(ref.entnum==3); ++calls; }
void ScrCmd_ShowToPlayer(scr_entref_t ref) { assert(ref.entnum==3); ++calls; }
int main(void)
{
    scr_entref_t ref={3,0};
    void (*methods[])(scr_entref_t)={CODOL_Scr_Delete,CODOL_Scr_Show,CODOL_Scr_Hide,CODOL_Scr_ShowToPlayer};
    g_entities[3].s.lerp.eFlags=6;
    for(unsigned i=0;i<4;++i) methods[i](ref);
    assert(calls==4 && !errors);
    CODOL_Scr_WillNeverChange(ref); CODOL_Scr_WillNeverChange(ref);
    assert((uint32_t)g_entities[3].s.lerp.eFlags==UINT32_C(0x80000006));
    for(unsigned i=0;i<4;++i) methods[i](ref);
    assert(calls==4 && errors==4);
    ref.classnum=1; CODOL_Scr_WillNeverChange(ref);
    ref.classnum=0; ref.entnum=MAX_GENTITIES; CODOL_Scr_WillNeverChange(ref);
    assert(errors==6 && !g_entities[2].s.lerp.eFlags);
    ref.entnum=3;
    CODOL_Scr_AddPitch(ref); assert(errors==7 && !angle_calls);
    g_entities[3].s.lerp.eFlags=6;
    g_entities[3].r.currentAngles[0]=10; g_entities[3].r.currentAngles[1]=20; g_entities[3].r.currentAngles[2]=30;
    delta=5; CODOL_Scr_AddPitch(ref); assert(received[0]==15 && received[1]==20 && received[2]==30);
    delta=-7; CODOL_Scr_AddYaw(ref); assert(received[0]==10 && received[1]==13 && received[2]==30);
    delta=360; CODOL_Scr_AddRoll(ref); assert(received[0]==10 && received[1]==20 && received[2]==390);
    delta=INFINITY; CODOL_Scr_AddRoll(ref); assert(errors==8 && angle_calls==3);
    delta=NAN; CODOL_Scr_AddRoll(ref); assert(errors==9 && angle_calls==3);
    puts("PASS: native static-entity marker, idempotence, method guards and invalid references");
}
