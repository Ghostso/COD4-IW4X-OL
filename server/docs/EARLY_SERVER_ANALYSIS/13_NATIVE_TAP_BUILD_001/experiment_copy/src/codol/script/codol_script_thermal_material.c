/* Native global thermal-body material configstring producer.
 * IW4 5f4da0 -> SV_SetConfigstring4982e0 at slot45b. C1's corresponding
 * client slot518 (1304) dispatches4675bf ->43de20 ->a78170, registering a
 * type5 Material into client+17447c; empty input clears that pointer.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_script_thermal_material.h"
#include "scr_vm_functions.h"
#include "codol_sv_state.h"
#include "server.h"
#include <string.h>

void CODOL_Scr_SetThermalBodyMaterial(void)
{
    const char *name=Scr_GetString(0), *old, *p;
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    int client;
    /* No receiver or explicit count check: extra args are ignored by IW4.
     * Bound/validate the name before changing the reliable-command bank. */
    if(strlen(name)>MAX_STRING_CHARS-32) {
        Scr_Error("Thermal body material name is too long"); return;
    }
    for(p=name;*p;++p)
        if((unsigned char)*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\') {
            Scr_Error("Invalid thermal body material name"); return;
        }
    old=CODOL_GetConfigstring(bank,CODOL_CS_THERMAL_BODY_MATERIAL);
    if(old && !strcmp(old,name)) return;
    /* Own even an empty override, so an inherited map value cannot reappear.
     * The normal CoDOL bank supplies late join gamestates and map teardown;
     * no per-player state or separate reset lifecycle belongs here. */
    if(!CODOL_SetConfigstring(bank,CODOL_CS_THERMAL_BODY_MATERIAL,name)) {
        Scr_Error("Could not set thermal body material"); return;
    }
    if(!svs.clients || !sv_maxclients) return;
    for(client=0;client<sv_maxclients->integer;++client) {
        client_t *target=&svs.clients[client];
        if(target->state>=CS_PRIMED && target->gamestateSent) {
            if(*name) SV_SendServerCommandNoLoss(target,"d %u %s",
                CODOL_CS_THERMAL_BODY_MATERIAL,name);
            else SV_SendServerCommandNoLoss(target,"d %u \"\"",
                CODOL_CS_THERMAL_BODY_MATERIAL);
        }
    }
}
#endif
