#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_assets.h"
#include "codol_map_custom.h"
#include "cvar.h"
#include "qcommon.h"
#include "qcommon_io.h"
void CODOL_Scr_GetMapCustom(void)
{
    const codol_engine_rawfile_t *raw=NULL;char value[1024];int status;const char *key;
    if(Scr_GetNumParam()<1){Scr_Error("getMapCustom requires a key");return;}
    key=Scr_GetString(0);
    status=CODOL_LoadEngineRawFile("mp/basemaps.arena",&raw);
    if(status<0){Scr_Error("getMapCustom: invalid arena asset");return;}
    if(!status){Scr_AddString("");return;}
    status=CODOL_MapCustom(raw->buffer,(size_t)raw->len,Cvar_GetVariantString("mapname"),key,value,sizeof(value));
    if(status<0){Scr_Error("getMapCustom: invalid arena metadata");return;}
    if (com_developer && com_developer->integer)
        Com_DPrintf(CON_CHANNEL_SCRIPT, "getMapCustom %s -> '%s'\n", key, status ? value : "");
    Scr_AddString(status ? value : "");
}
#endif
