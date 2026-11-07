#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "qcommon_io.h"
#include <stdint.h>
#include <string.h>

/* Retained BG_GetShellshockParms returns one 0x268-byte settings record.
 * BG_SetShellShockParmsFromDvars writes its fade interval at +0x14.
 * IW4 5ee350 and C1 538ac0 both read that same settings member. */
extern const void *BG_GetShellshockParms(int index);

/* PrecacheShellShock loads mounted raw text through DB_FindXAssetHeaderReal
 * and initializes BG_GetShellshockParms. C1 40e634 and the retained settings
 * writer both initialize +0x14 to 3000 ms. Snapshot/configstring publication
 * is supplied by codol_engine_state.c and codol_sv_assets.c. */
void CODOL_Scr_FadeOutShellShock(scr_entref_t ref)
{
    playerState_t *ps;
    int fade;
    uint32_t duration,end;
    if(ref.classnum) { Scr_ObjectError("not an entity"); return; }
    if(ref.entnum>=MAX_CLIENTS || (int)ref.entnum>=level.maxclients ||
       !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player",ref.entnum)); return;
    }
    if(Scr_GetNumParam()) {
        Scr_Error("USAGE: <player> fadeoutshellshock()\n"); return;
    }
    ps=&g_entities[ref.entnum].client->ps;
    if(!(ps->pm_flags&0x8000) || ps->shellshockDuration<=0) return;
    if((unsigned)ps->shellshockIndex>=16) {
        Scr_Error("shellshock index out of range"); return;
    }
    memcpy(&fade,(const unsigned char *)BG_GetShellshockParms(ps->shellshockIndex)+0x14,4);
    end=(uint32_t)ps->shellshockTime+(uint32_t)ps->shellshockDuration-(uint32_t)fade;
    if((int32_t)end<=level.time) return;
    duration=(uint32_t)level.time+(uint32_t)fade-(uint32_t)ps->shellshockTime;
    /* C1 538b75..538b87 / IW4 5ee3d9..5ee3eb preserve the old low seven
     * bits after shortening the duration. They are not rounded to zero. */
    duration=(duration&~UINT32_C(127))|((uint32_t)ps->shellshockDuration&127u);
    ps->shellshockDuration=(int32_t)duration;
}
#endif
