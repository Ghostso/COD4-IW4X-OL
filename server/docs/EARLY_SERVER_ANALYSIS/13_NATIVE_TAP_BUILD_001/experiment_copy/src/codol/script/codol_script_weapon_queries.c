#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_weapon_native.h"
#include "codol_weapon_compose.h"
#include "qcommon_io.h"
#include "xassets/sounds.h"
#include <stddef.h>
#include "codol_weapon_budget.h"
#include "codol_weapon_bits.h"
#include "codol_assets.h"
#include <string.h>

typedef char codol_drop_queue_offset_check[
    offsetof(level_locals_t,droppedWeaponCue)==0x1544 ? 1 : -1];
typedef char codol_drop_queue_handle_size_check[sizeof(EntHandle)==4 ? 1 : -1];

static void weapon_fire_sound(int player)
{
    int index=Scr_GetInt(0),status;
    struct WeaponDef *definition;
    const snd_alias_list_t *alias;
    codol_weapon_sounds_t sounds;
    /* T5 0x64d570/0x64d5c0 take indices, with 0/-1 meaning no weapon. */
    if(index==0 || index==-1) { Scr_AddString("");return; }
    if(index<0 || index>=BG_GetNumWeapons()) {
        Scr_ParamError(0,"weapon sound: weapon index out of range");return;
    }
    definition=BG_GetWeaponDef(index);
    status=CODOL_LoadMountedWeaponSounds(definition->szInternalName,&sounds);
    if(status<0) {
        Scr_Error("weapon sound: invalid CoDOL sound dependencies");return;
    }
    if(status==1) {
        /* C1 CG_FireWeapon 0x4820fd calls 0x481d60, which selects
         * ordinary +380 and local-player +384 at 0x481db3/0x481dc7.
         * Serialized names start at +364, giving slots 7 and 8. */
        const char *name=sounds.names[player ? 8 : 7];
        Scr_AddString(name ? name : "");return;
    }
    alias=player ? definition->fireSoundPlayer : definition->fireSound;
    Scr_AddString(alias && alias->aliasName ? alias->aliasName : "");
}
void CODOL_Scr_GetWeaponFireSound(void) { weapon_fire_sound(0); }
void CODOL_Scr_GetWeaponFireSoundPlayer(void) { weapon_fire_sound(1); }

/* IW4 0x5dc490 and 0x5dc580 enumerate registered indices in ascending
 * order, selecting owned weapons (or all when g_giveAll is enabled). The
 * retained playerState stores ownership in a bitset instead of 15 slots. */
static void player_weapon_list(scr_entref_t ref,int inventory)
{
    playerState_t *ps;
    unsigned weapon,count,capacity;
    qboolean giveAll;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client) {
        Scr_ObjectError("Not a player");return;
    }
    ps=&g_entities[ref.entnum].client->ps;
    count=(unsigned)BG_GetNumWeapons();
    capacity=CODOL_WEAPON_SLOTS;
    giveAll=Cvar_GetBool("g_giveAll");
    Scr_MakeArray();
    for(weapon=1;weapon<count;++weapon) {
        struct WeaponDef *definition;
        if(!giveAll && (weapon>=capacity ||
           !CODOL_WeaponBitsOwned(ps,weapon)))continue;
        definition=BG_GetWeaponDef((int)weapon);
        if(inventory>=0 && definition->inventoryType!=inventory)continue;
        Scr_AddString(definition->szInternalName);
        Scr_AddArray();
    }
}

void CODOL_Scr_GetWeaponsListAll(scr_entref_t ref)
{ player_weapon_list(ref,-1); }
void CODOL_Scr_GetWeaponsListOffhands(scr_entref_t ref)
{ player_weapon_list(ref,WEAPINVENTORY_OFFHAND); }
void CODOL_Scr_GetWeaponsListItems(scr_entref_t ref)
{ player_weapon_list(ref,WEAPINVENTORY_ITEM); }
/* IW4 0x5dc6b0 selects inventory type 4 through helper 0x5dc580. */
void CODOL_Scr_GetWeaponsListExclusives(scr_entref_t ref)
{ player_weapon_list(ref,WEAPINVENTORY_EXCLUSIVE); }

/* IW4 0x491810 walks all 32 dropped-weapon handles in queue order. This
 * is an entity array, not a catalog of weapon definitions or inventory.
 * T5 getdroppedweapons (0x655100) has the same 32-slot handle traversal,
 * skips undefined handles, and adds entities in slot order. */
void CODOL_Scr_GetWeaponArray(void)
{
    unsigned slot;
    /* Validate before allocating a VM result; zero is the empty handle. */
    for(slot=0;slot<32;++slot) {
        if(level.droppedWeaponCue[slot].number>MAX_GENTITIES) {
            Scr_Error("getweaponarray: invalid dropped weapon entity handle");
            return;
        }
    }
    Scr_MakeArray();
    for(slot=0;slot<32;++slot) {
        unsigned number=level.droppedWeaponCue[slot].number;
        if(number) {
            Scr_AddEntity(&g_entities[number-1]);
            Scr_AddArray();
        }
    }
}

/* T5 65fcc0..65ffb3 reject an empty/unresolved weapon name. Resolve through
 * the native registry so queries see the same definition as gameplay. */
static struct WeaponDef *query_weapon(void)
{
    const char *name=Scr_GetString(0);
    int index=G_GetWeaponIndexForName(name);
    if(!index) {
        Scr_ParamError(0, name[0] ? "unknown weapon name" : "weapon name is empty");
        return NULL;
    }
    return BG_GetWeaponDef(index);
}
void CODOL_Scr_GetWeaponMinDamageRange(void)
{
    struct WeaponDef *weapon=query_weapon();
    if(weapon)Scr_AddFloat(weapon->fMinDamageRange);
}
void CODOL_Scr_GetWeaponMaxDamageRange(void)
{
    struct WeaponDef *weapon=query_weapon();
    if(weapon)Scr_AddFloat(weapon->fMaxDamageRange);
}
void CODOL_Scr_GetWeaponMinDamage(void)
{
    struct WeaponDef *weapon=query_weapon();
    if(weapon)Scr_AddFloat((float)weapon->minDamage);
}
void CODOL_Scr_GetWeaponMaxDamage(void)
{
    struct WeaponDef *weapon=query_weapon();
    if(weapon)Scr_AddFloat((float)weapon->damage);
}
/* T5 64d920 returns the normal reload duration in seconds. */
void CODOL_Scr_WeaponReloadTime(void)
{
    struct WeaponDef *weapon=query_weapon();
    if(weapon)Scr_AddFloat((float)weapon->iReloadTime * 0.001f);
}
/* IW4 5f2770 returns zero for non-burst modes, otherwise the burst length. */
void CODOL_Scr_WeaponBurstCount(void)
{
    struct WeaponDef *weapon=query_weapon();
    int count=0;
    if(!weapon)return;
    switch(weapon->fireType) {
    case WEAPON_FIRETYPE_BURSTFIRE2: count=2; break;
    case WEAPON_FIRETYPE_BURSTFIRE3: count=3; break;
    case WEAPON_FIRETYPE_BURSTFIRE4: count=4; break;
    default: break;
    }
    Scr_AddInt(count);
}
/* IW4 5f26d0 requires both full-auto fire type and bullet weapon type. */
void CODOL_Scr_WeaponIsAuto(void)
{
    struct WeaponDef *weapon=query_weapon();
    if(weapon)Scr_AddBool(weapon->fireType==WEAPON_FIRETYPE_FULLAUTO &&
                         weapon->weapType==WEAPTYPE_BULLET);
}

/* T5 660170 warns and leaves the result undefined for resolver index zero.
 * Its +2c field is inventoryType (also passed to
 * BG_GetWeaponInventoryTypeName at 64d2f8). The native loader translates
 * C1 +34c into this enum before registering the definition. */
void CODOL_Scr_IsWeaponPrimary(void)
{
    const char *name=Scr_GetString(0);
    int index=G_GetWeaponIndexForName(name);
    if(!index) {
        Com_PrintWarning(CON_CHANNEL_SCRIPT, "isweaponprimary: unknown weapon '%s'\n", name);
        return;
    }
    Scr_AddInt(BG_GetWeaponDef(index)->inventoryType==WEAPINVENTORY_PRIMARY);
}

/* T5 64d530 exposes the server registry index, including zero. Keep native
 * indices here; engine-to-C1 index conversion belongs to snapshot encoding. */
void CODOL_Scr_GetWeaponIndexFromName(void)
{
    Scr_AddInt(G_GetWeaponIndexForName(Scr_GetString(0)));
}

/* CoDOL loadout bases can exist in the mounted C1 weapon archive without a
 * retained BG registration of their plain name. Script classification still
 * has to work for them; requiring PreCacheItem would reject valid composed
 * event weapons after they were already given. */
static struct WeaponDef *query_any_weapon(const char *name)
{
    const struct WeaponDef *definition=NULL;int index;
    if(!name || !*name || !Q_stricmp(name,"none"))return NULL;
    index=G_GetWeaponIndexForName(name);
    if(index>0 && index<BG_GetNumWeapons())return BG_GetWeaponDef(index);
    if(name[0]=='*') {
        if(CODOL_LoadComposedWeapon(name,&definition)==1)return (struct WeaponDef *)definition;
        return NULL;
    }
    if(CODOL_LoadMountedNativeWeapon(name,CODOL_LoadEngineWeaponCore,&definition)==1)
        return (struct WeaponDef *)definition;
    return NULL;
}

void CODOL_Scr_WeaponInventoryTypeSafe(void)
{
    const char *name=Scr_GetString(0);struct WeaponDef *definition=query_any_weapon(name);
    static const char *const names[]={"primary","offhand","item","altmode","exclusive","scavenger"};
    if(!definition || (unsigned)definition->inventoryType>=sizeof(names)/sizeof(*names)) {
        Scr_AddString("unknown");return;
    }
    Scr_AddString(names[definition->inventoryType]);
}

void CODOL_Scr_GetWeaponClassSafe(void)
{
    const char *name=Scr_GetString(0);struct WeaponDef *definition=query_any_weapon(name);
    const char *result="other";
    if(definition) switch(definition->weapClass) {
    case WEAPCLASS_RIFLE: result="weapon_assault";break;
    case WEAPCLASS_MG: result="weapon_lmg";break;
    case WEAPCLASS_SMG: result="weapon_smg";break;
    case WEAPCLASS_SPREAD: result="weapon_shotgun";break;
    case WEAPCLASS_PISTOL: result="weapon_pistol";break;
    case WEAPCLASS_GRENADE:
    case WEAPCLASS_ROCKETLAUNCHER: result="weapon_projectile";break;
    default: break;
    }
    Scr_AddString(result);
}

/* "Can this weapon actually be handed to a player right now?"
 *
 * Distinct from codol_weaponInventoryType, which answers whether a definition
 * exists in the mounted archive. A definition can exist, be precached, and
 * still be unusable, because the native weapon registry is finite and shared
 * with composed weapons: a weapon that lands at or past index 128 has no
 * publishable wire index. That is how rcbomb_mp reached
 * "engine 128 wire -1 owned 0", after which the give silently failed and the
 * following setActionSlot ended the match.
 *
 * Scripts granting a reward weapon should ask this first and skip the grant,
 * keeping the reward earned and pending, rather than granting into the void.
 * CODOL_WeaponAlreadyLive uses the find-only lookup, so asking costs nothing
 * and never registers a definition. */
void CODOL_Scr_IsWeaponPublished(void)
{
    if(Scr_GetNumParam()!=1) {
        Scr_Error("Usage: codol_isWeaponPublished( <weapon name> )"); return;
    }
    Scr_AddInt(CODOL_WeaponAlreadyLive(Scr_GetString(0)) ? 1 : 0);
}

/* Whether a weapon name resolves in a mounted zone, WITHOUT registering it.
 *
 * Scripts used to gate on getWeaponIndexFromName, which is the REGISTERING
 * path: CODOL_Scr_GetWeaponIndexFromName is a bare G_GetWeaponIndexForName,
 * and BG_GetWeaponIndexForName (_bg_weapons.asm:5098) reaches
 * BG_LoadWeaponDef_FastFile, a plain DB_FindXAssetHeaderReal(0x17,name) with
 * no default-asset check, then unconditionally increments
 * bg_lastParsedWeaponIndex and returns a NON-ZERO index. For a name that is
 * in no mounted zone, db_load.cpp:3499 hands back the defaultweapon_mp
 * definition, so the gate passed, a native weapon slot was burned, a
 * publish/republish cycle ran, and an _mp definition body entered the match
 * under a zm name. thundergun_zm stayed in the mystery box backed by that
 * clone on every map that does not ship it.
 *
 * This is the same probe precacheItem already runs internally
 * (codol_script_precache.c), which is find-only and registers nothing, so
 * asking costs nothing. Prefer this over codol_isWeaponPublished for
 * roster construction: that one additionally requires CODOL_WeaponToWire > 0,
 * and roster init runs before the first gamestate, so a stale engine-to-wire
 * map would empty the entire roster rather than just the absent entries. */
void CODOL_Scr_IsWeaponMounted(void)
{
    const char *name;
    const struct WeaponDef *weapon=NULL;
    int status;
    if(Scr_GetNumParam()!=1) {
        Scr_Error("Usage: codol_isWeaponMounted( <weapon name> )"); return;
    }
    name=Scr_GetString(0);
    if(!name || !*name) { Scr_AddInt(0); return; }
    /* Composed names and the two reserved names bypass the zone probe in
     * precacheItem; report them present so callers keep that behaviour. */
    if(name[0]=='*' || !strcmp(name,"none") || !strcmp(name,"defaultweapon_mp")) {
        Scr_AddInt(1); return;
    }
    status=CODOL_LoadMountedNullWeapon(name,&weapon);
    if(status==0) status=CODOL_LoadMountedNativeWeapon(name,CODOL_LoadEngineWeaponCore,&weapon);
    Scr_AddInt(status!=0 ? 1 : 0);
}

void CODOL_Scr_WeaponInheritsPerks(void)
{
    const char *name=Scr_GetString(0);
    int weapon=G_GetWeaponIndexForName(name),value;
    /* C1 0x541aab returns true for resolver index zero. Use the native resolver
     * so normal registration and its errors retain their engine behavior. */
    if(!weapon) { Scr_AddInt(1); return; }
    if(!CODOL_GetNativeWeaponInheritsPerks(BG_GetWeaponDef(weapon),&value)) {
        Scr_Error("weaponInheritsPerks: missing native CoDOL weapon metadata"); return;
    }
    Scr_AddInt(value);
}
#endif

