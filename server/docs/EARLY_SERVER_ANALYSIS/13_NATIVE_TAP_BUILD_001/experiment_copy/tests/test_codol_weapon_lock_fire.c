#include "g_shared.h"
#include "bg.h"
#include "codol_weapon_native.h"
#include "codol_weapon_lock.h"
#include "qcommon_io.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int CODOL_WeaponLockFireEvent(const playerState_t *,const struct WeaponDef *);
static int warning_gate;
int CODOL_GetNativeWeaponLockWarningGate(const struct WeaponDef *weapon,int *out)
{ (void)weapon;*out=warning_gate;return 1; }
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
    unsigned char bytes[0xbfc]={0};struct WeaponDef weapon={0},before;
    codol_mounted_weapon_t source={0};playerState_t *ps=&clients[0].ps;
    source.asset.type=28;source.asset.data=bytes;source.asset.size=sizeof(bytes);
    bytes[0xbbe]=1;
    assert(CODOL_ApplyNativeWeaponLockRequirement(&source,&weapon) && weapon.requireLockonToFire);
    assert(CODOL_WeaponLockFireEvent(ps,&weapon)==EV_LOCKON_REQUIRED_HINT);
    assert(CODOL_SetWeaponLock(CODOL_ClientWeaponLock(0),17,NULL,0,NULL,0));
    assert(CODOL_WeaponLockFireEvent(ps,&weapon)==EV_LOCKON_REQUIRED_HINT);
    assert(CODOL_SetWeaponLock(CODOL_ClientWeaponLock(0),17,NULL,1,NULL,0));
    assert(!CODOL_WeaponLockFireEvent(ps,&weapon));
    warning_gate=1;
    assert(CODOL_SetWeaponLockWarning(CODOL_ClientWeaponLock(0),0x10,1));
    assert(CODOL_WeaponLockFireEvent(ps,&weapon)==EV_TARGET_TOO_CLOSE_HINT);
    assert(CODOL_SetWeaponLockWarning(CODOL_ClientWeaponLock(0),0x20,1));
    assert(CODOL_WeaponLockFireEvent(ps,&weapon)==EV_TARGET_TOO_CLOSE_HINT);
    assert(CODOL_SetWeaponLockWarning(CODOL_ClientWeaponLock(0),0x10,0));
    assert(CODOL_WeaponLockFireEvent(ps,&weapon)==EV_TARGET_NOT_ENOUGH_CLEARANCE);
    CODOL_FreeWeaponLock(CODOL_ClientWeaponLock(0));
    assert(CODOL_WeaponLockFireEvent(ps,&weapon)==EV_LOCKON_REQUIRED_HINT);
    bytes[0xbbe]=0;assert(CODOL_ApplyNativeWeaponLockRequirement(&source,&weapon));
    /* Clearance blocks even without a finalized lock; proximity does not. */
    assert(CODOL_WeaponLockFireEvent(ps,&weapon)==EV_TARGET_NOT_ENOUGH_CLEARANCE);
    assert(CODOL_SetWeaponLockWarning(CODOL_ClientWeaponLock(0),0x20,0));
    assert(CODOL_SetWeaponLockWarning(CODOL_ClientWeaponLock(0),0x10,1));
    assert(!CODOL_WeaponLockFireEvent(ps,&weapon));
    warning_gate=0;
    assert(CODOL_SetWeaponLockWarning(CODOL_ClientWeaponLock(0),0x20,1));
    assert(!CODOL_WeaponLockFireEvent(ps,&weapon));
    before=weapon;bytes[0xbbe]=2;
    assert(!CODOL_ApplyNativeWeaponLockRequirement(&source,&weapon) && !memcmp(&before,&weapon,sizeof(weapon)));
    puts("PASS: mounted lock requirement -> native firing gate; start/finalize/free transitions and atomic invalid flag");
}
