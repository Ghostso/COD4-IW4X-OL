/* IW4 5f5cc0/5f5d30: named, ordered glass-piece queries.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_script_glass.h"
#include "codol_glass_load.h"
#include "scr_vm_functions.h"
#include "server.h"
#include "cvar.h"
#include "qcommon.h"
#include "cscr_stringlist.h"

static int named_glass(const uint16_t **pieces,uint16_t *count)
{
    const codol_glass_groups_t *groups;
    const char *name;
    char world[MAX_QPATH];
    unsigned key;
    if(Scr_GetNumParam()!=1) {
        Scr_Error("glass query requires exactly one group name"); return 0;
    }
    key=(unsigned short)Scr_GetConstString(0);
    name=SL_ConvertToString(key);
    if(!sv_mapname || !sv_mapname->string || !*sv_mapname->string) {
        Scr_Error("glass query has no active map"); return 0;
    }
    Com_GetBspFilename(world,sizeof(world),sv_mapname->string);
    /* Resolve each query against the active mounted definition. Cache ownership
     * belongs to that archive; no global pointer survives unmount or map switch. */
    if(CODOL_LoadMountedGlassGroups(world,&groups)!=1 ||
       !CODOL_FindGlassGroup(groups,name,pieces,count)) {
        Scr_Error("glass query could not load the active map's glass groups"); return 0;
    }
    return 1;
}
void CODOL_Scr_GetGlass(void)
{
    const uint16_t *pieces;
    uint16_t count;
    if(!named_glass(&pieces,&count)) return;
    if(!count) { Scr_AddUndefined(); return; }
    if(count>1) {
        Scr_Error("getglass found more than one piece for the group name"); return;
    }
    Scr_AddInt(pieces[0]);
}
void CODOL_Scr_GetGlassArray(void)
{
    const uint16_t *pieces;
    uint16_t count;
    unsigned i;
    if(!named_glass(&pieces,&count)) return;
    Scr_MakeArray();
    for(i=0;i<count;++i) { Scr_AddInt(pieces[i]); Scr_AddArray(); }
}
#endif
