#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_weapon_flags.h"
static void control(scr_entref_t ref,unsigned mask,int disabled)
{
    playerState_t *ps;
    if(ref.classnum || ref.entnum>=MAX_GENTITIES || !g_entities[ref.entnum].client) {
        Scr_ObjectError("Player control requires a player"); return;
    }
    ps=&g_entities[ref.entnum].client->ps;
    if(disabled) ps->weapFlags|=mask;
    else ps->weapFlags&=~mask;
}
void CODOL_Scr_EnableOffhandWeapons(scr_entref_t ref) { control(ref,CODOL_WEAP_OFFHAND_DISABLED,0); }
void CODOL_Scr_DisableOffhandWeapons(scr_entref_t ref) { control(ref,CODOL_WEAP_OFFHAND_DISABLED,1); }
void CODOL_Scr_EnableWeaponSwitch(scr_entref_t ref) { control(ref,CODOL_WEAP_SWITCH_DISABLED,0); }
void CODOL_Scr_DisableWeaponSwitch(scr_entref_t ref) { control(ref,CODOL_WEAP_SWITCH_DISABLED,1); }
void CODOL_Scr_EnableUsability(scr_entref_t ref) { control(ref,CODOL_USE_DISABLED,0); }
void CODOL_Scr_DisableUsability(scr_entref_t ref) { control(ref,CODOL_USE_DISABLED,1); }
#endif
