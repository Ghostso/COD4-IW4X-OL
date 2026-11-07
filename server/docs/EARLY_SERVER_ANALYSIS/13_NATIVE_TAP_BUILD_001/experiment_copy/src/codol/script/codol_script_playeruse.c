#ifdef CODOL_SERVER
#include "codol_script_playeruse.h"
#include "scr_vm_functions.h"
#include <stdint.h>
#include <string.h>

/* IW4 client+327c stores one disabled-use bit per target entity. This is
 * server selection state, not a playerState wire flag. It lives in IW4's
 * clientSession_t, which ClientSpawn preserves, so it survives a respawn and
 * is reset only with the client's connection and the level's input state. */
static uint32_t disabled[MAX_CLIENTS][(MAX_GENTITIES+31)/32];

static void set_player_use(scr_entref_t target,int blocked)
{
    gentity_t *player=Scr_GetEntity(0);
    int slot;
    uint32_t mask;
    if(!player || !player->client) {
        Scr_ParamError(0,"Not a player");return;
    }
    if(target.classnum || target.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity");return;
    }
    slot=player->s.number;
    if(slot<0 || slot>=MAX_CLIENTS) {
        Scr_ParamError(0,"Not a player");return;
    }
    mask=UINT32_C(1)<<(target.entnum&31);
    if(blocked)disabled[slot][target.entnum>>5]|=mask;
    else disabled[slot][target.entnum>>5]&=~mask;
}
/* IW4 4164d0 ->489a90 sets; 4d8d20 ->4bc370 clears. Both take
 * the player as script argument0 and the target as the method receiver. */
void CODOL_Scr_DisablePlayerUse(scr_entref_t target) {set_player_use(target,1);}
void CODOL_Scr_EnablePlayerUse(scr_entref_t target) {set_player_use(target,0);}

/* IW4 5fe737 calls4431e0 while constructing candidate use targets. */
int CODOL_PlayerUseAllowed(const struct gentity_s *player,const struct gentity_s *target)
{
    int slot,number;
    if(!player || !player->client || !target)return 0;
    slot=player->s.number;number=target->s.number;
    if(slot<0 || slot>=MAX_CLIENTS || number<0 || number>=MAX_GENTITIES)return 0;
    return !(disabled[slot][(unsigned)number>>5]&(UINT32_C(1)<<(number&31)));
}
void CODOL_PlayerUseResetClient(int slot)
{ if(slot>=0 && slot<MAX_CLIENTS)memset(disabled[slot],0,sizeof(disabled[slot])); }
void CODOL_PlayerUseResetAll(void) {memset(disabled,0,sizeof(disabled));}
/* IW4 G_FreeEntityRefs 416250 calls the clear-bit helper at416392 for
 * every active player. Clear all rows here as inactive rows reset on spawn. */
void CODOL_PlayerUseClearTarget(int number)
{
    unsigned slot;
    uint32_t keep;
    if(number<0 || number>=MAX_GENTITIES)return;
    keep=~(UINT32_C(1)<<(number&31));
    for(slot=0;slot<MAX_CLIENTS;++slot)disabled[slot][(unsigned)number>>5]&=keep;
}
#endif
