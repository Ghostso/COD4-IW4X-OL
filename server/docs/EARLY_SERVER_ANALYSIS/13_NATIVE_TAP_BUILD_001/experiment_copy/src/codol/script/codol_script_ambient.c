#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_sv_state.h"
#include "server.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Native x87 implementation beside the retained ambient functions. */
int CODOL_AmbientFadeMillis(float seconds);

/* C1 SetAC130Ambience555cb0: global function, exactly one/two arguments.
 * Optional float1 is read before string0. No alias asset lookup or return.
 * Client4676b6 selects this bank when player flags contain0x8000;44f2e0
 * reads the n/t info keys and computes the remaining fade from client time. */
void CODOL_Scr_SetAC130Ambience(void)
{
    unsigned argc=Scr_GetNumParam();
    int fade=0, deadline, length, client;
    uint32_t deadline_bits;
    const char *name, *old;
    char value[CODOL_CONFIGSTRING_VALUE_CHARS+1];
    char stored[CODOL_CONFIGSTRING_VALUE_CHARS+1];
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    if(argc!=1 && argc!=2) {
        Scr_Error("USAGE: SetAC130Ambience(alias_name, <fadetime>);");
        return;
    }
    if(argc==2) fade=CODOL_AmbientFadeMillis(Scr_GetFloat(1));
    name=Scr_GetString(0);
    if(!*name) { Scr_Error("SetAC130Ambience alias must not be empty"); return; }
    if(fade<0) { Scr_Error("SetAC130Ambience fade time must not be negative"); return; }
    deadline_bits=(uint32_t)level.time+(uint32_t)fade;
    memcpy(&deadline,&deadline_bits,sizeof(deadline));
    length=snprintf(value,sizeof(value),"n\\%s\\t\\%i",name,deadline);
    if(length<0 || (size_t)length>=sizeof(value)) {
        Scr_Error("SetAC130Ambience configstring is too long");
        return;
    }
    old=CODOL_GetConfigstring(bank,CODOL_CS_AC130_AMBIENT);
    if(old && !strcmp(old,value)) return;
    /* C1 SV_SetConfigstring5d3198 chooses lowercase storage at index>=1300
     * through5cb3f0, but broadcasts the original input at5d3235. */
    memcpy(stored,value,(size_t)length+1);
    Q_strlwr(stored);
    if(!CODOL_SetConfigstring(bank,CODOL_CS_AC130_AMBIENT,stored)) {
        Scr_Error("Could not store AC130 ambience");
        return;
    }
    /* Retain the override for initial gamestate; update existing recipients. */
    if((sv.state!=SS_GAME && !sv.restarting) || !svs.clients || !sv_maxclients) return;
    for(client=0;client<sv_maxclients->integer;++client) {
        client_t *target=&svs.clients[client];
        if(target->state>=CS_PRIMED && target->gamestateSent)
            SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_AC130_AMBIENT,value);
    }
}
#endif
