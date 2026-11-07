#ifdef CODOL_SERVER
#include "codol_weapon_slots.h"
#include "codol_obituary.h"
#include "scr_vm_functions.h"
#include "server.h"
#include "bg.h"
#include "codol_weapon_native.h"
#include "codol_weapon_registry.h"
#include "codol_usercmd.h"
#include <string.h>

extern gentity_t *G_TempEntity(const float *,int);

/* C1 MOD table CD4940, producer54E560. Retained MOD indices differ. */
static const char *const obituary_mods[]={
    "MOD_UNKNOWN","MOD_PISTOL_BULLET","MOD_RIFLE_BULLET",
    "MOD_EXPLOSIVE_BULLET","MOD_GRENADE","MOD_GRENADE_SPLASH",
    "MOD_PROJECTILE","MOD_PROJECTILE_SPLASH","MOD_MELEE","MOD_HEAD_SHOT",
    "MOD_GAS","MOD_CRUSH","MOD_FALLING","MOD_SUICIDE","MOD_TRIGGER_HURT",
    "MOD_EXPLOSIVE","MOD_IMPACT"
};

void CODOL_GScr_Obituary(void)
{
    static const float origin[3]={0,0,0};
    gentity_t *victim,*attacker=0,*event;
    const char *mod_name;
    struct WeaponDef *definition;
    codol_bomb_weapon_t source;
    unsigned mod,source_class;
    int weapon,use_weapon=1;
    if(Scr_GetNumParam()!=4) {
        Scr_Error("obituary requires victim, attacker, weapon and means of death"); return;
    }
    victim=Scr_GetEntity(0);
    /* C1 CG_Obituary444732 bounds the victim to its19-client presentation pool. */
    if(!victim || !victim->client || victim->s.number<0 || victim->s.number>=19) {
        Scr_ParamError(0,"obituary victim must be a C1 player numbered0..18"); return;
    }
    if(Scr_GetType(1)==VAR_POINTER && Scr_GetPointerType(1)==VAR_ENTITY)
        attacker=Scr_GetEntity(1);
    weapon=G_GetWeaponIndexForName(Scr_GetString(2));
    if(weapon<0 || weapon>=BG_GetNumWeapons() || weapon>=(int)CODOL_WEAPON_SLOTS) {
        Scr_ParamError(2,"obituary weapon has no native definition"); return;
    }
    mod_name=Scr_GetString(3);
    for(mod=0;mod<sizeof(obituary_mods)/sizeof(obituary_mods[0]);++mod)
        if(!strcmp(mod_name,obituary_mods[mod])) break;
    if(mod==sizeof(obituary_mods)/sizeof(obituary_mods[0])) {
        Scr_ParamError(3,"unknown C1 obituary means of death"); return;
    }
    definition=BG_GetWeaponDef(weapon);
    switch(mod) {
    case 8:
        /* 54E6F8: riot-shield melee keeps the weapon kill icon. */
        if(!CODOL_GetNativeBombWeapon(definition,&source)) {
            Scr_ParamError(2,"obituary requires C1 weapon type metadata"); return;
        }
        use_weapon=source.type==3; break;
    case 16:
        /* 54E78F: throwing-knife impact keeps the weapon kill icon. */
        if(!CODOL_GetNativeWeaponClass(definition,&source_class)) {
            Scr_ParamError(2,"obituary requires C1 weapon class metadata"); return;
        }
        use_weapon=source_class==9; break;
    case 9: case 11: case 12: case 13:
        use_weapon=0; break;
    }
    event=G_TempEntity(origin,EV_OBITUARY);
    if(!event) return;
    /* All five values are ordinary archived entity-state members. There is no
     * live-victim lookup when replaying a delayed snapshot. index is a typed
     * obituary-only icon selector, not a model or ambiguous high-bit marker. */
    event->s.otherEntityNum=victim->s.number;
    event->s.attackerEntityNum=attacker ? attacker->s.number : ENTITYNUM_WORLD;
    event->s.weapon=weapon;
    event->s.eventParm=(int)mod;
    event->s.index=use_weapon;
    event->r.svFlags|=8; /* Same broadcast flag as retained obituary producer. */
}

int CODOL_DecodeObituary(const entityState_t *state,unsigned *victim,
                         unsigned *attacker,unsigned *death_code)
{
    int weapon;
    unsigned code;
    if(!state || !victim || !attacker || !death_code ||
       state->eType!=ET_EVENTS+EV_OBITUARY ||
       state->otherEntityNum<0 || state->otherEntityNum>=19 ||
       state->attackerEntityNum<0 || state->attackerEntityNum>ENTITYNUM_WORLD ||
       state->eventParm<0 || state->eventParm>=17 ||
       state->index<0 || state->index>1) return 0;
    if(state->index) {
        weapon=CODOL_WeaponToWire((unsigned)state->weapon);
        if(weapon<0 || weapon>=700) return 0;
        code=(unsigned)weapon;
    } else code=700u+(unsigned)state->eventParm;
    *victim=(unsigned)state->otherEntityNum;
    *attacker=(unsigned)state->attackerEntityNum;
    *death_code=code;
    return 1;
}
#endif
