#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "qcommon.h"
#include "sys_cod4defs.h"
const char* Sys_GetCommonVersionString(void);
#include <stdint.h>

void CODOL_Scr_GetPlayers(void)
{
    int slot;
    Scr_MakeArray();
    for (slot = 0; slot < level.maxclients && slot < MAX_CLIENTS; ++slot) {
        gentity_t *entity = &g_entities[slot];
        if (entity->r.inuse && entity->client && entity->client->sess.connected == CON_CONNECTED) {
            Scr_AddEntity(entity);
            Scr_AddArray();
        }
    }
}

void CODOL_Scr_GetSystemTime(void)
{
    /* Unix seconds, unlike IW4OL getrealtime's 2012-relative value. GSC
     * integers are 32-bit; retain the low bits across the signed boundary. */
    Scr_AddInt((int32_t)(uint32_t)Com_GetRealtime());
}
void CODOL_Scr_GetBuildNumber(void) { Scr_AddInt(Sys_GetBuild()); }
/* IW4 returns the short client build ("1.2.208"), which _matchdata.gsc stores
 * in the match record's fixed-width buildVersion string; the long product
 * name overflowed that field. The CoDOL client build this server serves is
 * 1.1.1.13; the sh1x version is separately available from getBuildNumber. */
void CODOL_Scr_GetBuildVersion(void) { Scr_AddString("1.1.1.13"); }
#endif
