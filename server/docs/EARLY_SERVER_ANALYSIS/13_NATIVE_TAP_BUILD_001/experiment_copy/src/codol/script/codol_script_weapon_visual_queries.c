#ifdef CODOL_SERVER
#include "codol_script_weapon_visual_queries.h"
#include "scr_vm_functions.h"
#include "codol_weapon_native.h"
#include "codol/weapon/codol_weapon_compose.h"
#include "qcommon_io.h"
#include "cvar.h"
#include "xassets.h"
#include "xassets/xmodel.h"

extern int BG_GetNumWeapons(void);
extern int __cdecl XModelGetBoneIndex(XModel *,unsigned int,unsigned int,uint8_t *);

/* IW4 stows one monolithic world model and then applies this list to that
 * model. CoDOL composes its live weapon from a base model plus attachment
 * models, so attachment-only tags (tag_up/tag_down are common sight-rail
 * examples) do not exist on the base model passed to HidePart. Returning such
 * a tag makes the retained IW4 method terminate the map. Keep only tags that
 * can actually be hidden on the model the stow script attaches. */
static int composed_stow_model_has_tag(struct WeaponDef *definition,unsigned int tag)
{
    const char *world=NULL;
    XModel *model;
    uint8_t index;
    if(!CODOL_ComposedWeaponBaseArt(definition,&world,NULL)) return 1;
    if(!world || !world[0]) return 0;
    model=DB_FindXAssetHeader(ASSET_TYPE_XMODEL,world,false,0).model;
    if(!model) return 0;
    return XModelGetBoneIndex(model,tag,0,&index);
}

/* Both references resolve the argument the same way: Scr_GetString(0) then
 * G_GetWeaponIndexForName (IW4 0x425900/0x49e540, C1 0x5cded0/0x41f6c0), with
 * zero meaning unresolved. The engines differ only in what they do with a
 * failure, so the resolver returns it and each query decides. Slot bounds are
 * a IW4OL guard: the reference indexes its definition table unchecked because
 * only its own resolver can produce the index. */
static int visual_query_weapon(const char **name)
{
    int index;
    *name=Scr_GetString(0);
    index=G_GetWeaponIndexForName(*name);
    if(index<=0 || index>=BG_GetNumWeapons()) return 0;
    return index;
}

/* C1 0x5358d0, IW4 0x5ec8c0. The array is made first and filled with the
 * definition's hide tags in slot order, stopping at the first zero: C1 walks
 * 32 inline uint16 slots at definition+0x3c (loop bound 0x20 at 0x5359ef),
 * IW4 walks 32 slots of WeaponCompleteDef::hideTags (loop bound 0x40 bytes at
 * 0x5ec940). Neither raises a script error. An empty name and "none" return
 * quietly; any other unresolved name prints on the error channel (C1 channel
 * 0x14 at 0x535937, IW4 channel 0x11 at 0x5ec8fb) and still returns undefined. */
void CODOL_Scr_GetWeaponHideTags(void)
{
    const codol_weapon_hide_tag_handles_t *tags;
    struct WeaponDef *definition;
    const char *name;
    int index=visual_query_weapon(&name);
    unsigned i;
    if(!index) {
        if(name[0] && Q_stricmp(name,"none"))
            Com_PrintError(CON_CHANNEL_ERROR,"unknown weapon '%s' in getWeaponHideTags\n",name);
        return;
    }
    definition=BG_GetWeaponDef(index);
    Scr_MakeArray();
    /* CoDOL definitions carry all 32 source slots, acquired by
     * CODOL_BindMountedWeaponHideTags; the retained IW3 WeaponDef.hideTags[8]
     * is a truncation of that array and is only the right answer for weapons
     * that came from a retained fastfile rather than a mounted archive. */
    if(CODOL_GetNativeWeaponHideTags(definition,&tags)) {
        for(i=0;i<32;++i) {
            if(!tags->tags[i]) break;
            if(!composed_stow_model_has_tag(definition,tags->tags[i])) continue;
            Scr_AddConstString(tags->tags[i]); Scr_AddArray();
        }
        return;
    }
    for(i=0;i<8;++i) {
        if(!definition->hideTags[i]) break;
        Scr_AddConstString(definition->hideTags[i]); Scr_AddArray();
    }
}

/* C1 registers the gate as Dvar_RegisterBool at 0x40c1fc with its name
 * stripped to "209" and a default of true, keeping the pointer in 0x150c550;
 * IW4's equivalent lives at 0x7adbe8. Only the enabled/disabled meaning is
 * portable, so this is a server dvar with the same default. */
static cvar_t *silenced_flash_tag_gate(void)
{
    static cvar_t *gate;
    if(!gate) gate=Cvar_RegisterBool("bg_silencedFlashTag",qtrue,0,
        "Use tag_flash_silenced for silenced weapons in getweaponflashtagname");
    return gate;
}

/* C1 0x548ea0, IW4 0x4b5560. Unlike the hide-tag query this one errors on any
 * unresolved name, including "none", with the same message text in both
 * engines (C1 0xc58744, IW4 0x6ed174), and never returns from it.
 * The tag itself is a two-way choice, inlined at C1 0x548f1d and factored into
 * IW4 0x4c6520/0x48e1f0: the silenced tag only when the gate dvar is enabled
 * and the definition's silenced byte is set, otherwise tag_flash. C1's byte is
 * definition+0xbda -- proven by this selector plus its only other consumers,
 * 0x422ae6 and 0x486ce0, which pick between the same two script strings. */
void CODOL_Scr_GetWeaponFlashTagName(void)
{
    const char *name;
    int index=visual_query_weapon(&name),silenced=0;
    if(!index) { Scr_Error(va("Unknown weapon name \"%s\"\n",name)); return; }
    /* Retained definitions have no CoDOL silenced byte; they answer tag_flash,
     * which is what the retained IW3 muzzle-flash tags already assume. */
    if(silenced_flash_tag_gate()->boolean &&
       CODOL_GetNativeWeaponSilenced(BG_GetWeaponDef(index),&silenced) && silenced) {
        /* Scr_AddString interns the same script string without extending the
         * retained scr_const layout addressed directly by assembly. */
        Scr_AddString("tag_flash_silenced"); return;
    }
    Scr_AddConstString(scr_const.tag_flash);
}

/* C1 0x535c10, whose failure message at 0xc55b80 names it GetWeaponScriptMods.
 * It resolves the name like the queries above (0x41f7a0 while the level is
 * loading, 0x41f6c0 otherwise), then answers the registered definition's
 * +a24 string (0x535c81..0x535c8e). An unresolved name other than "" or
 * "none" prints on channel 0x14 (0x535c6c); every failure still returns the
 * empty string (0x535c74), never undefined. The one consumer that matters is
 * the killcam silencer: weaponattach silencer_kcam (item muz_silencerkillcam)
 * overrides +a24 with "nokillcam", so the composed definition's own core,
 * not its base's, must answer. */
void CODOL_Scr_GetWeaponScriptMods(void)
{
    const char *name,*mods="";
    int index=visual_query_weapon(&name);
    if(!index) {
        if(name[0] && Q_stricmp(name,"none"))
            Com_PrintError(CON_CHANNEL_ERROR,"unknown weapon '%s' in GetWeaponScriptMods\n",name);
        Scr_AddString("");
        return;
    }
    /* Retained definitions have no +a24; they answer the empty string. */
    if(!CODOL_GetNativeWeaponScriptMods(BG_GetWeaponDef(index),&mods) || !mods) mods="";
    Scr_AddString(mods);
}

/* Four weapon-flag queries C1 answers from definition bytes (attachment
 * flags; see codol_native_weapon_core_t). Each loads the name like the queries above (0x41f7a0 while
 * the level loads, 0x41f6c0 after), indexes the registered definition at
 * 0x150d720 and pushes one byte with Scr_AddInt (0x5ce690).
 *
 *   C1 0x542010  +0xbe6  weaponhasthermalscope: the slot IW4's function table
 *                        gives that name, after isweaponcliponly (0x541eb0,
 *                        +0xbcd) and isweapondetonationtimed (0x541f00,
 *                        +0xbe2) and before getvehiclenode (0x682eb0). Only
 *                        thermal_* weaponattach assets write the byte.
 *   C1 0x542140  +0xbf4  gps_base (items gps_default, sra_tracker)
 *   C1 0x5421d0  +0xbf5  lock_base (item sra_idlock)
 *   C1 0x5583d0  +0xbf3  hpbt_base, heiap_barrett, slap_base (item mag_hpbt)
 *
 * The first three raise 'Unknown weapon name' (0xc55748) for a name that
 * does not resolve, other than "none", and still answer from definition 0;
 * 0x5583d0 raises nothing and answers 0. C1's function table carries no
 * names, so the last three are named here; the GSC tree is ours. A retained
 * (non-CoDOL) definition has none of these bytes and answers 0. */
static void weapon_script_flag(codol_weapon_script_flag_t flag,int strict)
{
    const char *name;
    int index=visual_query_weapon(&name),value=0;
    if(!index) {
        if(strict && Q_stricmp(name,"none"))
            Scr_Error(va("Unknown weapon name \"%s\": script may need to call PreCacheItem(\"%s\") during level init.\n",
                name,name));
        Scr_AddInt(0);
        return;
    }
    if(!CODOL_GetNativeWeaponScriptFlag(BG_GetWeaponDef(index),flag,&value)) value=0;
    Scr_AddInt(value!=0);
}
void CODOL_Scr_WeaponHasThermalScope(void) { weapon_script_flag(CODOL_WEAPON_SCRIPT_FLAG_THERMAL_SCOPE,1); }
void CODOL_Scr_WeaponHasGPS(void) { weapon_script_flag(CODOL_WEAPON_SCRIPT_FLAG_GPS,1); }
void CODOL_Scr_WeaponHasIDLock(void) { weapon_script_flag(CODOL_WEAPON_SCRIPT_FLAG_ID_LOCK,1); }
void CODOL_Scr_WeaponHasHPBT(void) { weapon_script_flag(CODOL_WEAPON_SCRIPT_FLAG_HPBT,0); }
#endif
