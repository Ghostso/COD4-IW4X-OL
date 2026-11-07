#ifdef CODOL_SERVER
#include "codol_script_appearance.h"
#include "codol_player_appearance.h"
#include "scr_vm_functions.h"
#include "server.h"
#include <string.h>
/* Native spawn bridge. Character selection/parts come from this client's
 * uploaded profile. Optional gender/camouflage are visual context, matching
 * the reference Python default m/urb until the gametype supplies another. */
void CODOL_Scr_ApplyProfileCharacter(scr_entref_t ref)
{
    const char *faction,*weapon,*camo="urb";int gender=0,n=Scr_GetNumParam();
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].r.inuse ||
       !g_entities[ref.entnum].client) {
        Scr_ObjectError("codol_applyProfileCharacter requires a player");return;
    }
    if(n<2 || n>4) {
        Scr_Error("codol_applyProfileCharacter requires faction, weapon [, gender, camouflage]");return;
    }
    faction=Scr_GetString(0);weapon=Scr_GetString(1);
    if(strcmp(faction,"tf") && strcmp(faction,"sc") && strcmp(faction,"zm")) {
        Scr_ParamError(0,"character faction must be tf, sc or zm");return;
    }
    if(n>=3)gender=Scr_GetInt(2);
    if(n>=4)camo=Scr_GetString(3);
    if(gender<0 || gender>1) {Scr_ParamError(2,"character gender must be 0 or 1");return;}
    if(strlen(camo)!=3) {Scr_ParamError(3,"character camouflage must have three characters");return;}
    if(!CODOL_SelectClientCharacterForWeapon(ref.entnum,faction,(unsigned)gender,camo,weapon)) {
        Scr_Error("codol_applyProfileCharacter could not compose/publish this player's character");return;
    }
}
/* <player> codol_getZombieCharacter(): the mp/cyborgclasstable.csv row key
 * (zm1..zm4) of this player's zombies character, the same row
 * codol_applyProfileCharacter composes. Undefined when the profile names no
 * roster character (a test client has no uploaded profile); C1 row 0 is the
 * fallback character, and choosing it is the caller's decision. */
void CODOL_Scr_GetZombieCharacter(scr_entref_t ref)
{
    const char *key=NULL;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].r.inuse ||
       !g_entities[ref.entnum].client) {
        Scr_ObjectError("codol_getZombieCharacter requires a player");return;
    }
    if(CODOL_ClientZombieCharacterKey(ref.entnum,&key) && key && *key)
        Scr_AddString(key);
}
/* <player> codol_getVoicePrefix(): the faction/gender voice prefix this
 * player's character speaks with, exactly the cg_vo_prefix the server sent
 * C1 ("UK_M1_", "AB_F1_"; mp/factiontable.csv voice column + gender + voice
 * 1). C1's player voice aliases are named <prefix><line>, e.g.
 * uk_m1_inform_reloading_generic, ab_f1_mp_death. Undefined until the
 * character is published. */
void CODOL_Scr_GetVoicePrefix(scr_entref_t ref)
{
    const char *prefix;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].r.inuse ||
       !g_entities[ref.entnum].client) {
        Scr_ObjectError("codol_getVoicePrefix requires a player");return;
    }
    if((prefix=CODOL_ClientVoicePrefix(ref.entnum))!=NULL)
        Scr_AddString(prefix);
}
#endif
