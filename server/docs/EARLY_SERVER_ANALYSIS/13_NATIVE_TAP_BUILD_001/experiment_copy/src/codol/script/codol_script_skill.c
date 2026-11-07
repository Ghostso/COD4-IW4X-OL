#ifdef CODOL_SERVER
#include "codol_profile_skill.h"
#include "scr_vm_functions.h"
#include "server.h"
#include "cvar.h"

/* Retained parser owns/reset/sets this flag, including script-load lifetime. */
extern qboolean Scr_LoadedImpureScript(void);

static int skill_player(gentity_t *entity,const char *role)
{
    if(!entity || !entity->client) {
        Scr_Error(va("USAGE: UpdateSkill: %s isn't a client.",role)); return -1;
    }
    if(entity->s.number<0 || entity->s.number>=level.maxclients ||
       entity->s.number>=MAX_CLIENTS || entity!=&g_entities[entity->s.number] ||
       !svs.clients) {
        Scr_Error("UpdateSkill: invalid player slot"); return -1;
    }
    return entity->s.number;
}
/* IW4 5f9650: receiverless global, >=2 entity args; mode defaults to tdm,
 * weight to1. Test clients exit before optional-argument parsing or writes.
 * IW4x src/Game/Server.cpp names4d6e40 SV_IsTestClient, matching the binary
 * exclusion calls5f96c0/5f96d3. Native bot producers use NA_BOT. */
void CODOL_Scr_UpdateSkill(void)
{
    gentity_t *winner,*loser;
    const char *mode="tdm";
    float weight=1.0f;
    int first,second,count=Scr_GetNumParam();
    if(count<2) { Scr_Error("USAGE: UpdateSkill( winner, loser )"); return; }
    winner=Scr_GetEntity(0);
    loser=Scr_GetEntity(1);
    first=skill_player(winner,"winner");
    if(first<0) return;
    second=skill_player(loser,"loser");
    if(second<0) return;
    if(svs.clients[first].netchan.remoteAddress.type==NA_BOT ||
       svs.clients[second].netchan.remoteAddress.type==NA_BOT) return;
    if(count>=3) mode=Scr_GetString(2);
    if(count>=4) weight=Scr_GetFloat(3);
    if(winner->client->sess.connected!=CON_CONNECTED ||
       loser->client->sess.connected!=CON_CONNECTED) {
        Scr_Error("UpdateSkill: player is not connected"); return;
    }
    /* IW4 persistent-write guard5f8da0. Use native parser/cvar state,
     * never copy reference offsets into this server's structures. */
    if(Scr_LoadedImpureScript()) {
        Scr_Error("cannot set persistent data: impure scripts loaded."); return;
    }
    if(Cvar_VariableBooleanValue("developer_script")) {
        Scr_Error("cannot set persistent data: developer_script must be false."); return;
    }
    if(!CODOL_UpdateProfileSkills((unsigned)first,(unsigned)second,mode,weight))
        Scr_Error("UpdateSkill: cannot update skills in playerdata");
}
#endif
