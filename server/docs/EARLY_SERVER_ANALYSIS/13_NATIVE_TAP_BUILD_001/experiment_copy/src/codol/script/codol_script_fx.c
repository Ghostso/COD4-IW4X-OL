#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "codol_sv_state.h"
#include "codol_configstrings.h"

void CODOL_Scr_PrecacheFxTeamThermal(void)
{
    int index; char effect[1024]; const char *tag;
    if(!level.initializing) {
        Scr_Error("PrecacheFxTeamThermal must be called before any wait statements"); return;
    }
    if(Scr_GetNumParam()!=2) {
        Scr_Error("PrecacheFxTeamThermal requires an effect ID and attachment tag"); return;
    }
    index=Scr_GetInt(0); tag=Scr_GetString(1);
    if(index<=0 || index>=CODOL_EFFECT_SLOTS) {
        Scr_Error("PrecacheFxTeamThermal: invalid retained effect ID"); return;
    }
    CODOL_GetNativeEffectName((unsigned)index,effect,sizeof(effect));
    if(!*effect || CODOL_RegisterTeamThermal(CODOL_ServerConfigstrings(),
        CODOL_ServerInheritedConfigstrings(),effect,tag)<0)
        Scr_Error("PrecacheFxTeamThermal: invalid or exhausted effect/thermal configstrings");
}
#endif
