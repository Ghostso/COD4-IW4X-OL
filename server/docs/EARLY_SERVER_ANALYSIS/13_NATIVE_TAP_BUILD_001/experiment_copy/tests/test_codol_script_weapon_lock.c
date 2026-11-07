#include "scr_vm_functions.h"
#include "codol_weapon_lock.h"
#include "qcommon_io.h"
#include <assert.h>
#include <string.h>
#include <setjmp.h>
#include <stdio.h>
gentity_t g_entities[MAX_GENTITIES];
static int count=3,value=1,bad_vector;static unsigned type=VAR_POINTER;
static jmp_buf error;static float vectors[2][3]={{1,2,3},{100,0,-32}};
int Scr_GetNumParam(void){return count;}
unsigned Scr_GetType(unsigned index){assert(index==0);return type;}
unsigned Scr_GetPointerType(unsigned index){assert(index==0);return VAR_ENTITY;}
gentity_t *Scr_GetEntity(unsigned index){assert(index==0);return &g_entities[17];}
void Scr_Error(const char *s){assert(s);longjmp(error,1);}
void Scr_ObjectError(const char *s){Scr_Error(s);}
void Scr_GetVector(unsigned index,float *out)
{ if(index>=(unsigned)count || (bad_vector && index==1))Scr_Error("vector");memcpy(out,vectors[index],12); }
int Scr_GetInt(unsigned index){if(index>=(unsigned)count)Scr_Error("int");return value;}
/* The lock lives in the playerState extension now, so the harness supplies the
 * live storage its resolver walks: clients[0].ps is client 0's state, and the
 * snapshot and archive classes are absent here. */
static gclient_t clients[1];
const void *CODOL_PlayerStateExtLiveBase(unsigned *count){if(count)*count=1;return clients;}
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_PlayerStateExtArchiveBase(unsigned *count){if(count)*count=0;return NULL;}
/* codol_playerstate_ext.c reports untracked storage through this hook. */
void Com_PrintWarning(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
int main(void)
{
    scr_entref_t ref={0};codol_weapon_lock_t before,*lock=CODOL_ClientWeaponLock(0);
    g_entities[0].client=&clients[0];g_entities[17].s.number=17;
    CODOL_Scr_WeaponLockStart(ref);assert(lock->entity==17 && lock->flags==1);
    CODOL_Scr_WeaponLockFinalize(ref);assert(lock->flags==7 && lock->missile_offset[2]==-32);
    CODOL_Scr_WeaponLockTargetTooClose(ref);CODOL_Scr_WeaponLockNoClearance(ref);
    assert(lock->flags==0x37);
    before=*lock;bad_vector=1;
    if(!setjmp(error)){CODOL_Scr_WeaponLockFinalize(ref);assert(0);}
    assert(!memcmp(&before,lock,sizeof(before)));bad_vector=0;
    count=1;type=VAR_VECTOR;CODOL_Scr_WeaponLockStart(ref);
    assert(lock->flags==0x71 && lock->position[2]==3);
    CODOL_Scr_WeaponLockFinalize(ref);assert(lock->flags==0x7b && !lock->missile_offset[2]);
    CODOL_Scr_WeaponLockFree(ref);assert(lock->flags==0x70 && lock->entity==2047);
    before=*lock;ref.classnum=1;
    if(!setjmp(error)){CODOL_Scr_WeaponLockStart(ref);assert(0);}
    assert(!memcmp(&before,lock,sizeof(before)));ref.classnum=0;count=0;
    if(!setjmp(error)){CODOL_Scr_WeaponLockNoClearance(ref);assert(0);}
    assert(!memcmp(&before,lock,sizeof(before)));
    puts("PASS: GSC lock methods mutate native state, entity/vector arguments, defaults and atomic VM errors");
}
