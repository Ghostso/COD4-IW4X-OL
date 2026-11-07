#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_weapon_native.h"
#include "qcommon_io.h"
#include "xassets/sounds.h"

extern int BG_GetNumWeapons(void);

/* Mounted CoDOL definitions store sound names; native definitions store
 * alias assets. Resolve the mounted views first, exactly like the existing
 * fire-sound queries, and fall back to the native alias names. */
static int weapon_sound_names(const struct WeaponDef *definition,codol_native_weapon_sounds_t *out)
{
    codol_weapon_sounds_t sounds; codol_weapon_tail_t tail; int status;
    status=CODOL_LoadMountedWeaponSounds(definition->szInternalName,&sounds);
    if(status!=1) return status;
    status=CODOL_LoadMountedWeaponTail(definition->szInternalName,&tail);
    if(status!=1) return status;
    return CODOL_ApplyNativeWeaponSoundNames(&sounds,&tail,out) ? 1 : -1;
}

static void weapon_pickup_sound(int player)
{
    int index,status;
    struct WeaponDef *definition;
    const snd_alias_list_t *alias;
    codol_native_weapon_sounds_t names;
    /* C1 0x558d90/0x558df0 call Scr_GetString (0x5cded0), resolve
     * the name, and return empty for an unresolved weapon. Keep the T5
     * 0x64d610/0x64d660 integer form as well: 0/-1 mean no weapon.
     * This distinction matters for CoDOL scripts using native names. */
    if(Scr_GetType(0)==VAR_INTEGER) index=Scr_GetInt(0);
    else index=G_GetWeaponIndexForName(Scr_GetString(0));
    if(index==0 || index==-1) { Scr_AddString("");return; }
    if(index<0 || index>=BG_GetNumWeapons()) {
        Scr_ParamError(0,"weapon pickup sound: weapon index out of range");return;
    }
    definition=BG_GetWeaponDef(index);
    status=weapon_sound_names(definition,&names);
    if(status<0) {
        Scr_Error("weapon pickup sound: invalid CoDOL sound dependencies");return;
    }
    if(status==1) {
        const char *name=player ? names.pickup_player : names.pickup;
        Scr_AddString(name ? name : "");return;
    }
    alias=player ? definition->pickupSoundPlayer : definition->pickupSound;
    Scr_AddString(alias && alias->aliasName ? alias->aliasName : "");
}
void CODOL_Scr_GetWeaponPickupSound(void) { weapon_pickup_sound(0); }
void CODOL_Scr_GetWeaponPickupSoundPlayer(void) { weapon_pickup_sound(1); }

/* T5 65ff20/65ffc0 resolve a weapon name and reject unresolved ones with
 * their own parameter errors before reading the definition. */
static struct WeaponDef *query_weapon(void)
{
    const char *name=Scr_GetString(0);
    int index=G_GetWeaponIndexForName(name);
    if(!index) {
        if(name[0]) Scr_ParamError(0,va("Invalid weapon name %s",name));
        else Scr_ParamError(0,"Invalid weapon name");
        return NULL;
    }
    return BG_GetWeaponDef(index);
}

void CODOL_Scr_GetWeaponProjExplosionSound(void)
{
    struct WeaponDef *definition=query_weapon();
    const snd_alias_list_t *alias;
    codol_native_weapon_sounds_t names;
    int status;
    if(!definition)return;
    status=weapon_sound_names(definition,&names);
    if(status<0) {
        Scr_Error("getweaponprojexplosionsound: invalid CoDOL sound dependencies");return;
    }
    if(status==1) { Scr_AddString(names.proj_explosion ? names.proj_explosion : "");return; }
    /* T5 660038 returns empty for an absent field instead of erroring. */
    alias=definition->projExplosionSound;
    Scr_AddString(alias && alias->aliasName ? alias->aliasName : "");
}

/* T5 65ff9a converts the integer definition field and returns milliseconds,
 * not seconds. Zero means the weapon has no timed detonation. */
void CODOL_Scr_GetWeaponFuseTime(void)
{
    struct WeaponDef *definition=query_weapon();
    if(definition)Scr_AddFloat((float)definition->fuseTime);
}
#endif
