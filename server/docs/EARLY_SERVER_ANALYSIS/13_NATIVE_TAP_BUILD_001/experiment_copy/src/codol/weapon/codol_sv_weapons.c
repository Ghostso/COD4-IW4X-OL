#ifdef CODOL_SERVER
#include "codol_sv_weapons.h"
#include "codol_weapon_state.h"
#include "codol_sv_state.h"
#include "codol_weapon_native.h"
#include "codol_weapon_compose.h"
#include "codol_usercmd.h"
#include "codol_weapon_bits.h"
#include "server.h"
#include <stddef.h>
#include <string.h>
#include <stdio.h>
/* _bg_weapons.asm pools: 128 pointers each (resb 0x200); the counters sit
 * directly in front of the next pool, so an overflow corrupts its neighbour. */
extern unsigned int bg_numAmmoTypes, bg_numWeapClips, bg_numSharedAmmoCaps;
extern struct WeaponDef *bg_weapAmmoTypes[], *bg_weapClips[], *bg_sharedAmmoCaps[];
extern unsigned int bg_lastParsedWeaponIndex;
extern struct WeaponDef *bg_weaponDefs[];

/* Capacity gate for BG_GetWeaponIndexForName (_bg_weapons.asm), called with
 * the loaded definition before anything is appended.
 *
 * C1's BG_ClearWeaponDefs (0x41F570) sizes all four tables at 700 pointers
 * (0xAF0 each: defs 0x0150D720, clips 0x015106F8, shared caps 0x0150CC30,
 * ammo 0x0150FC08), so its pools can never overflow. The retained server
 * keeps 128 entries per pool because every ammo/clip index is also an index
 * into playerState ammo[128] (ps+0x15C) / ammoclip[128] (ps+0x35C), and the
 * unchecked appends wrote entry 128 straight over the next pool's counter.
 * Refuse such a definition instead: the caller reports an unknown weapon,
 * which a script or composer already handles, where the overrun corrupted
 * the pools for every later weapon. Also refuses a definition past C1's
 * 700-slot table (bg_weaponDefs holds 700 plus the retained sentinel). */
static int codol_pool_has(struct WeaponDef **pool, unsigned count, size_t field,
                          const char *name, int nocase)
{
    unsigned i;
    for (i = 0; i < count; ++i) {
        const char *other = pool[i] ? *(const char **)((const char *)pool[i] + field) : NULL;
        if (other && (nocase ? !Q_stricmp(other, name) : !strcmp(other, name))) return 1;
    }
    return 0;
}
int CODOL_AdmitWeaponPools(const struct WeaponDef *def)
{
    const char *why = NULL;
    if (!def) return 0;
    if (bg_lastParsedWeaponIndex + 1u >= CODOL_WEAPON_SLOTS)
        why = "weapon table";
    else if (bg_numAmmoTypes >= CODOL_NATIVE_AMMO_POOL && def->szAmmoName &&
             !codol_pool_has(bg_weapAmmoTypes, bg_numAmmoTypes,
                             offsetof(struct WeaponDef, szAmmoName), def->szAmmoName, 0))
        why = "ammo pool";
    else if (bg_numWeapClips >= CODOL_NATIVE_AMMO_POOL && def->szClipName &&
             !codol_pool_has(bg_weapClips, bg_numWeapClips,
                             offsetof(struct WeaponDef, szClipName), def->szClipName, 0))
        why = "clip pool";
    else if (bg_numSharedAmmoCaps >= CODOL_NATIVE_AMMO_POOL && def->szSharedAmmoCapName &&
             *def->szSharedAmmoCapName &&
             !codol_pool_has(bg_sharedAmmoCaps, bg_numSharedAmmoCaps,
                             offsetof(struct WeaponDef, szSharedAmmoCapName),
                             def->szSharedAmmoCapName, 1))
        why = "shared ammo cap pool";
    if (!why) return 1;
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL weapons: '%s' refused, native %s is full (defs %u/%u, ammo %u/%u, clip %u/%u, cap %u/%u)\n",
        def->szInternalName ? def->szInternalName : "?", why,
        bg_lastParsedWeaponIndex + 1u, (unsigned)CODOL_WEAPON_SLOTS,
        bg_numAmmoTypes, (unsigned)CODOL_NATIVE_AMMO_POOL,
        bg_numWeapClips, (unsigned)CODOL_NATIVE_AMMO_POOL,
        bg_numSharedAmmoCaps, (unsigned)CODOL_NATIVE_AMMO_POOL);
    return 0;
}
static codol_weapon_registry_t *registry;
unsigned char codol_ammo_binding_refused[MAX_CLIENTS];
static int valid;
/* CODOL_RefreshServerWeaponMappings runs for every usermove packet and every
 * snapshot, and rebuilding it is an O(N^2) name search. It is recomputed only
 * when one of its inputs moves: the registry (replaced or appended to), the
 * native weapon count, the identity of every native definition and its name
 * (an O(N) pointer signature: a reordering keeps the count and both ends), or
 * the usercmd map itself (reset at level load, replaced by an append). */
static unsigned registry_generation;
static struct {
    int valid, count;
    unsigned registry_generation, map_generation;
    const codol_weapon_registry_t *registry;
    const struct WeaponDef *first, *last;
    uintptr_t signature;
} mapping_cache;
static uintptr_t native_weapon_signature(int count)
{
    uintptr_t h=(uintptr_t)count;
    int i;
    for(i=0;i<count;++i) {
        const struct WeaponDef *def=BG_GetWeaponDef(i);
        h=h*31u+(uintptr_t)def;
        h=h*31u+(uintptr_t)(def ? def->szInternalName : NULL);
    }
    return h;
}
static char error[256];
static int append_native_weapons(void);
extern int BG_GetWeaponIndexForName(const char *,void (*)(unsigned));
extern void G_RegisterWeapon(unsigned);
static int replay_weapon(codol_weapon_registry_t *r,unsigned slot,const char *name)
{
    if(!name || !*name) return 0;
    return name[0]=='*' ? CODOL_RegisterComposedWeaponKeys(r,slot,name) :
        CODOL_RegisterMountedWeaponKeys(r,slot,name);
}
const char *CODOL_ServerWeaponRegistryError(void) { return error; }
void CODOL_ResetServerWeaponRegistry(void)
{ CODOL_DestroyWeaponRegistry(registry); registry=NULL; valid=0; error[0]=0; ++registry_generation; }
const codol_weapon_registry_t *CODOL_ServerWeaponRegistry(void)
{ return valid ? registry : NULL; }
int CODOL_RefreshServerWeaponMappings(void)
{
    int count=BG_GetNumWeapons(),mapping[CODOL_WEAPON_SLOTS],i;
    uintptr_t signature;
    if(!valid || count<1 || (unsigned)count>CODOL_WEAPON_SLOTS) return 0;
    signature=native_weapon_signature(count);
    if(mapping_cache.valid && mapping_cache.count==count &&
       mapping_cache.registry==registry &&
       mapping_cache.registry_generation==registry_generation &&
       mapping_cache.map_generation==CODOL_WeaponMapGeneration() &&
       mapping_cache.first==BG_GetWeaponDef(0) &&
       mapping_cache.last==BG_GetWeaponDef(count-1) &&
       mapping_cache.signature==signature) return 1;
    mapping_cache.valid=0;
    for(i=0;i<count;++i) {
        const struct WeaponDef *def=BG_GetWeaponDef(i);
        if(!def || !def->szInternalName) return 0;
        if(CODOL_FindRegisteredWeapon(registry,def->szInternalName)<0)
            return append_native_weapons();
    }
    for(i=0;i<count;++i) {
        const struct WeaponDef *def=BG_GetWeaponDef(i);
        if(!def || (mapping[i]=CODOL_FindRegisteredWeapon(registry,def->szInternalName))<0) return 0;
    }
    /* One table per change in the native count: what the client is told
     * (wire slot, registry ammo/clip keys) beside what the engine stores
     * (bg_ pool indices), so a client-side expectation can be diffed. */
    {
        static int printed_count=-1;
        if(CODOL_TRACE_VERBOSE() && printed_count!=count) {
            printed_count=count;
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL weapon table (%d): engine wire ammoKey clipKey engAmmo engClip clipSize name [gate ammoName/clipName]\n",count);
            for(i=1;i<count;++i) {
                const struct WeaponDef *def=BG_GetWeaponDef(i); int a=-1,c=-1;
                const char *an="",*cn=""; unsigned gate=0,noclip=0;
                CODOL_GetWeaponKeys(registry,(unsigned)mapping[i],&a,&c);
                CODOL_RegisteredWeaponKeyNames(registry,(unsigned)mapping[i],&an,&cn,&gate,&noclip);
                if(CODOL_TRACE_VERBOSE()) Com_Printf(CON_CHANNEL_SERVER,"CoDOL weapon table: %d %d %d %d %d %d %d %s [%u%s '%s'/'%s']\n",
                    i,mapping[i],a,c,def->iAmmoIndex,def->iClipIndex,def->iClipSize,def->szInternalName,
                    gate,noclip ? " noclip" : "",an,cn);
            }
        }
    }
    if(!CODOL_ReplaceWeaponMap(mapping,(unsigned)count)) return 0;
    mapping_cache.valid=1; mapping_cache.count=count;
    mapping_cache.registry=registry;
    mapping_cache.registry_generation=registry_generation;
    mapping_cache.map_generation=CODOL_WeaponMapGeneration();
    mapping_cache.first=BG_GetWeaponDef(0);
    mapping_cache.last=BG_GetWeaponDef(count-1);
    mapping_cache.signature=signature;
    return 1;
}
int CODOL_RefreshServerWeaponRegistry(void)
{
    codol_weapon_registry_t *next;
    const codol_configstrings_t *published=CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    unsigned slot; int gap=0;
    valid=0; error[0]=0; ++registry_generation;
    if(!inherited) { strcpy(error,"inherited configstrings not installed"); return 0; }
    if(!(next=CODOL_CreateWeaponRegistry())) { strcpy(error,"registry allocation failed"); return 0; }
    for(slot=0;slot<CODOL_WEAPON_SLOTS;++slot) {
        const char *name=CODOL_GetConfigstring(published,CODOL_CS_WEAPONS+slot);
        if(!name) name=CODOL_GetConfigstring(inherited,CODOL_CS_WEAPONS+slot);
        if(slot<2) {
            const char *implicit=slot ? "defaultweapon_mp" : "none";
            if(name && *name && strcmp(name,implicit)) {
                snprintf(error,sizeof(error),"slot %u conflicts with implicit %s: '%s'",slot,implicit,name); goto fail;
            }
            name=implicit;
        } else if(!name || !*name) { gap=1; continue; }
        /* CG_Init validates each name's registered index against its slot.
         * Empty override strings suppress inherited names, they do not fall back. */
        if(gap) { snprintf(error,sizeof(error),"registration gap before slot %u: '%s'",slot,name); goto fail; }
        if(!replay_weapon(next,slot,name)) {
            snprintf(error,sizeof(error),"cannot register mounted slot %u: '%s'",slot,name); goto fail;
        }
    }
    CODOL_DestroyWeaponRegistry(registry); registry=next; valid=1; ++registry_generation; return 1;
fail:
    CODOL_DestroyWeaponRegistry(next); return 0;
}
int CODOL_BuildServerAmmoBindings(codol_engine_player_bindings_t *out,const playerState_t *ps)
{
    struct WeaponDef *definitions[CODOL_WEAPON_SLOTS]={0}; int count,i;
    if(!out || !ps || !CODOL_RefreshServerWeaponMappings()) return 0;
    count=BG_GetNumWeapons(); if(count<1 || (unsigned)count>CODOL_WEAPON_SLOTS) return 0;
    for(i=0;i<count;++i) {
        definitions[i]=BG_GetWeaponDef(i);
        if(!definitions[i]) return 0;
    }
    if(!CODOL_BuildEngineAmmoBindings(out,ps,registry,definitions)) {
        /* A refused binding set leaves the client on its last published
         * magazines. Say so, with the inventory size (the 15-slot ceiling is
         * the usual reason), once per client per streak. */
        unsigned c=(unsigned)ps->clientNum, owned=0, w;
        for(w=1;w<CODOL_WEAPON_SLOTS;++w) if(CODOL_WeaponBitsOwned(ps,w)) ++owned;
        if(c<MAX_CLIENTS && !codol_ammo_binding_refused[c]) {
            codol_ammo_binding_refused[c]=1;
            Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL ammo bindings: client %u REFUSED (owned %u weapons, ceiling 15)\n",c,owned);
        }
        return 0;
    }
    /* Publish the second hand's magazine for every bound clip slot. IW4's
     * 0x48d170 and C1's PM_ReloadClip scan the same fifteen {key, ammo[2]}
     * records; a single-hand weapon's slot reports zero, not an absent one. */
    for(i=0;i<16;++i) {
        int left=0, index=out->clips[i].engine_index, dual=0; unsigned w;
        if(!(out->clip_mask&(1u<<i))) continue;
        if(!CODOL_WeaponStateClipAmmoByIndex(ps,index,1,&left) ||
           left<0 || left>511) return 0;
        /* A single-hand weapon has one magazine. alpha0022's live-verified
         * encoder (weapon_loadout.write_ammo_in_clip_section) publishes that
         * magazine in BOTH hand values; C1 reads ammoClip[hand] (0x41a4b2) and
         * a zero second value showed as an empty primary / a frozen secondary
         * on 2026-09-16. Only a dual-wield pair carries a distinct second
         * magazine. */
        for(w=1;w<CODOL_WEAPON_SLOTS && !dual;++w)
            if(CODOL_WeaponBitsOwned(ps,w) && definitions[w] && definitions[w]->iClipIndex==index &&
               CODOL_WeaponIsDualWield(w)) dual=1;
        if(!dual && index>=0 && index<128) left=ps->ammoclip[index];
        out->clips[i].left_ammo=(int16_t)left;
    }
    if((unsigned)ps->clientNum<MAX_CLIENTS) codol_ammo_binding_refused[ps->clientNum]=0;
    /* What the held weapon's magazine looks like on the wire, for a human
     * client, whenever any part of it changes: the section-2 record slot
     * (field), the client-side clip key it is addressed by, and both hand
     * values. The client's HUD reads ammoClip[hand] of the record whose key
     * equals its own def->iClipIndex (0x41a4b2), so key here must be what C1
     * assigned when it registered this name. */
    {
        static struct { int weapon,slot,key,a0,a1; } last_wire[MAX_CLIENTS];
        unsigned c=(unsigned)ps->clientNum;
        if(c<MAX_CLIENTS && svs.clients[c].netchan.remoteAddress.type!=NA_BOT &&
           ps->weapon>0 && ps->weapon<count && definitions[ps->weapon]) {
            const struct WeaponDef *def=definitions[ps->weapon]; int slot=-1;
            for(i=0;i<16;++i) if((out->clip_mask&(1u<<i)) && out->clips[i].engine_index==def->iClipIndex) { slot=i; break; }
            if(slot>=0) {
                int a0=def->iClipIndex>=0 && def->iClipIndex<128 ? ps->ammoclip[def->iClipIndex] : -1;
                int a1=out->clips[slot].left_ammo, key=out->clips[slot].wire_key;
                if(last_wire[c].weapon!=ps->weapon || last_wire[c].slot!=slot || last_wire[c].key!=key ||
                   last_wire[c].a0!=a0 || last_wire[c].a1!=a1) {
                    last_wire[c].weapon=ps->weapon; last_wire[c].slot=slot; last_wire[c].key=key;
                    last_wire[c].a0=a0; last_wire[c].a1=a1;
                    if(CODOL_TRACE_VERBOSE())
                    Com_Printf(CON_CHANNEL_SERVER,"CoDOL ammo wire: client %u weapon %s clip idx %d -> field %d key %d value %d/%d\n",
                        c,def->szInternalName,def->iClipIndex,slot,key,a0,a1);
                }
            } else if(last_wire[c].weapon!=ps->weapon || last_wire[c].slot!=-1) {
                last_wire[c].weapon=ps->weapon; last_wire[c].slot=-1;
                if(CODOL_TRACE_VERBOSE())
                Com_Printf(CON_CHANNEL_SERVER,"CoDOL ammo wire: client %u weapon %s clip idx %d -> NO RECORD\n",
                    c,def->szInternalName,def->iClipIndex);
            }
        }
    }
    /* Per-client trace of the published magazine/reserve records whenever the
     * set of bound slots or their keys changes (counts change every shot and
     * are not traced). */
    {
        static codol_engine_player_bindings_t last[MAX_CLIENTS];
        unsigned c=(unsigned)ps->clientNum;
        if(CODOL_TRACE_VERBOSE() && c<MAX_CLIENTS && (last[c].clip_mask!=out->clip_mask || last[c].reserve_mask!=out->reserve_mask ||
           memcmp(last[c].clips,out->clips,sizeof(out->clips)) || memcmp(last[c].reserves,out->reserves,sizeof(out->reserves)))) {
            char line[1024]; int n=0;
            n+=snprintf(line+n,sizeof(line)-n,"CoDOL ammo bindings: client %u clips",c);
            for(i=0;i<16 && n<(int)sizeof(line)-48;++i) if(out->clip_mask&(1u<<i))
                n+=snprintf(line+n,sizeof(line)-n," [%d eng%d key%d %d/%d]",i,out->clips[i].engine_index,out->clips[i].wire_key,
                    out->clips[i].engine_index>=0 && out->clips[i].engine_index<128 ? ps->ammoclip[out->clips[i].engine_index] : -1,
                    out->clips[i].left_ammo);
            n+=snprintf(line+n,sizeof(line)-n," reserves");
            for(i=0;i<16 && n<(int)sizeof(line)-40;++i) if(out->reserve_mask&(1u<<i))
                n+=snprintf(line+n,sizeof(line)-n," [%d eng%d key%d %d]",i,out->reserves[i].engine_index,out->reserves[i].wire_key,
                    out->reserves[i].engine_index>=0 && out->reserves[i].engine_index<128 ? ps->ammo[out->reserves[i].engine_index] : -1);
            Com_Printf(CON_CHANNEL_SERVER,"%s\n",line);
            last[c]=*out;
        }
    }
    return 1;
}
static int register_stock(codol_weapon_registry_t *r,const char **names,unsigned *count,const char *name)
{
    codol_weapon_tail_t tail; unsigned i,j;
    const unsigned char *p;
    static const unsigned partners[]={0xb78,0xb88};
    if(!name || !*name) return 1;
    if(name[0]=='*') {
        codol_composed_weapon_t record;
        if(CODOL_ParseComposedWeaponName(name,&record)!=1 || strcmp(name,record.canonical)) return 0;
        /* Numeric fields contain only decimal digits. Validate the tag before
         * allowing spaces as the measured composed-name separators. */
        for(p=(const unsigned char *)record.tag;*p;++p)
            if(*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\') return 0;
    } else for(p=(const unsigned char *)name;*p;++p)
            if(*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\') return 0;
    for(i=0;i<*count;++i) if(!strcmp(names[i],name)) return 1;
    if(*count>=CODOL_WEAPON_SLOTS || !replay_weapon(r,*count,name) ||
       (name[0]=='*' ? CODOL_ComposedWeaponTail(name,&tail) : CODOL_LoadMountedWeaponTail(name,&tail))!=1 || tail.count>64) {
        snprintf(error,sizeof(error),"cannot register weapon '%s'",name); return 0;
    }
    names[(*count)++]=name;
    /* C1 registrar resolves +b78 then +b88 after appending the current def.
     * Already registered names (including cycles) reuse their original slot. */
    for(j=0;j<2;++j) for(i=0;i<tail.count;++i) if(tail.entries[i].offset==partners[j]) {
        if(tail.entries[i].kind!=CODOL_WEAPON_DEP_STRING ||
           !register_stock(r,names,count,tail.entries[i].name)) return 0;
    }
    return 1;
}
/* Where the native definition budget actually goes.
 *
 * "The table is full" is useless on its own: it does not say whether the
 * CODOL_WEAPON_SLOTS budget went on stock definitions, on the partner/alternate definitions the C1
 * registrars append beside them, on killstreak weapons, or on the composed
 * loadouts that are the whole point. Categorise it by name shape, which is the
 * only signal the native table carries:
 *
 *   composed  - a canonical composed name (CODOL_ParseComposedWeaponName)
 *   partner   - an alternate/companion definition, i.e. a name the wire
 *               registry never published on its own behalf
 *   stock     - everything else that came from the mounted weapon set
 *
 * Printed once per map after the stock set is installed, and again on every
 * composed publish, so one match shows exactly what has to be trimmed or how
 * much headroom a widening bought. */
static void report_weapon_budget(const char *stage)
{
    int total = BG_GetNumWeapons(), i, composed = 0, partner = 0, stock = 0;
    codol_composed_weapon_t parsed;
    if (!CODOL_TRACE_VERBOSE()) return;
    if (total < 1) return;
    for (i = 1; i < total; ++i) {
        const struct WeaponDef *def = BG_GetWeaponDef(i);
        const char *name = def ? def->szInternalName : NULL;
        if (!name || !*name) continue;
        if (CODOL_ParseComposedWeaponName(name, &parsed) == 1) ++composed;
        else if (registry && CODOL_FindRegisteredWeapon(registry, name) < 0) ++partner;
        else ++stock;
    }
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL weapon budget (%s): %d/%d native definitions - %d stock, %d partner, "
        "%d composed; %d free; pools ammo %u/%u clip %u/%u sharedcap %u/%u\n",
        stage, total, CODOL_WEAPON_SLOTS, stock, partner, composed,
        CODOL_WEAPON_SLOTS - total, bg_numAmmoTypes, (unsigned)CODOL_NATIVE_AMMO_POOL,
        bg_numWeapClips, (unsigned)CODOL_NATIVE_AMMO_POOL,
        bg_numSharedAmmoCaps, (unsigned)CODOL_NATIVE_AMMO_POOL);
}

/* Undoing a native weapon registration.
 *
 * BG_GetWeaponIndexForName appends to bg_weaponDefs and advances
 * bg_lastParsedWeaponIndex; BG_GetNumWeapons is that index plus one. If a
 * later step of the publish fails, the definition stays in the native table
 * with no wire slot and no configstring - exactly the blanked "*a" shape that
 * makes the client's CG_Init walk (C1 0x47d1d0, 1..count-1) read a definition
 * the gamestate never named. Put the table back where it was.
 *
 * Only the tail this call appended is removed: the index is restored to the
 * value captured before registration and the vacated slots are cleared, so
 * BG_GetNumWeapons and every [index*4+bg_weaponDefs] read return to their
 * previous answers. G_RegisterWeapon's model and hint strings stay published;
 * they are name-keyed, nothing references them once the definition is gone,
 * and re-registering the same weapon later reuses them. */
typedef struct {
    unsigned last_index, ammo, clips, caps;
} codol_native_weapon_mark_t;

static codol_native_weapon_mark_t mark_native_weapons(void)
{
    codol_native_weapon_mark_t mark;
    mark.last_index = bg_lastParsedWeaponIndex;
    mark.ammo = bg_numAmmoTypes;
    mark.clips = bg_numWeapClips;
    mark.caps = bg_numSharedAmmoCaps;
    return mark;
}

/* The three pools append in step with the table, so a rolled-back tail also
 * owns every pool entry added since the mark; leaving them counted pinned
 * pool capacity to definitions that no longer exist. */
static void rollback_native_weapons(const codol_native_weapon_mark_t *mark)
{
    unsigned i, previous_last_index = mark->last_index;
    for (i = mark->ammo; i < bg_numAmmoTypes && i < CODOL_NATIVE_AMMO_POOL; ++i) bg_weapAmmoTypes[i] = NULL;
    for (i = mark->clips; i < bg_numWeapClips && i < CODOL_NATIVE_AMMO_POOL; ++i) bg_weapClips[i] = NULL;
    for (i = mark->caps; i < bg_numSharedAmmoCaps && i < CODOL_NATIVE_AMMO_POOL; ++i) bg_sharedAmmoCaps[i] = NULL;
    if (bg_numAmmoTypes > mark->ammo) bg_numAmmoTypes = mark->ammo;
    if (bg_numWeapClips > mark->clips) bg_numWeapClips = mark->clips;
    if (bg_numSharedAmmoCaps > mark->caps) bg_numSharedAmmoCaps = mark->caps;
    if (bg_lastParsedWeaponIndex <= previous_last_index) return;
    for (i = previous_last_index + 1; i <= bg_lastParsedWeaponIndex; ++i)
        bg_weaponDefs[i] = NULL;
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL weapons: publish failed; rolled the native table back from %u to %u definitions\n",
        bg_lastParsedWeaponIndex + 1, previous_last_index + 1);
    bg_lastParsedWeaponIndex = previous_last_index;
}

static int append_weapon_set(const char *requested,unsigned *requested_slot)
{
    codol_configstrings_t next={0},*published=CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    const char *names[CODOL_WEAPON_SLOTS]={0};
    codol_weapon_registry_t *r=NULL;
    unsigned count=0,first,i;
    int native_count=BG_GetNumWeapons(),mapping[CODOL_WEAPON_SLOTS],gap=0,
        requested_index=-1,requested_engine=-1;
    /* Captured before anything can register, so the fail path can restore it.
     *
     * The ceiling is the ownership bitset, which now lives in the playerState
     * extension at CODOL_WEAPON_SLOTS (700) bits - C1's own table width (see
     * codol_weapon_slots.h). Rejecting past the bitset is still the right
     * behaviour: beyond it a definition could be registered but never
     * owned. */
    codol_native_weapon_mark_t previous=mark_native_weapons();
    if(!valid || !inherited || native_count<1 || (unsigned)native_count>CODOL_WEAPON_SLOTS) return 0;
    r=CODOL_CreateWeaponRegistry(); if(!r) return 0;
    /* Replay existing slots exactly. Dependencies may already occupy later
     * slots, so recurse only for newly appended definitions. */
    for(i=0;i<CODOL_WEAPON_SLOTS;++i) {
        const char *name=CODOL_GetConfigstring(published,CODOL_CS_WEAPONS+i);
        if(!name) name=CODOL_GetConfigstring(inherited,CODOL_CS_WEAPONS+i);
        if(i<2) {
            const char *implicit=i ? "defaultweapon_mp" : "none";
            if(name && *name && strcmp(name,implicit)) goto fail;
            name=implicit;
        }
        if(!name || !*name) { gap=1; continue; }
        if(gap || !replay_weapon(r,i,name)) goto fail;
        names[count++]=name;
    }
    first=count;
    for(i=0;i<(unsigned)native_count;++i) {
        const struct WeaponDef *def=BG_GetWeaponDef(i);
        if(!def || !def->szInternalName || !*def->szInternalName ||
           !register_stock(r,names,&count,def->szInternalName)) goto fail;
    }
    if(requested) {
        const struct WeaponDef *expected=NULL;
        if(!register_stock(r,names,&count,requested) ||
           (requested_index=CODOL_FindRegisteredWeapon(r,requested))<0) goto fail;
        /* Runtime G_GetWeaponIndexForName is deliberately find-only after
         * level initialization. Profile composition happens then, so merely
         * publishing the wire name left bg_weaponDefs without this definition
         * and every give resolved to engine index zero. Perform the same native
         * registration BG_GetWeaponIndexForName uses during initialization,
         * including G_RegisterWeapon's model/hint publication callback. */
        if(CODOL_LoadComposedWeapon(requested,&expected)!=1 || !expected ||
           (requested_engine=BG_GetWeaponIndexForName(requested,G_RegisterWeapon))<=0 ||
           requested_engine>=BG_GetNumWeapons() || BG_GetWeaponDef(requested_engine)!=expected)
            goto fail;
    }
    /* Native registration can append the requested composed definition and
     * any retained alternate definition. Re-read the table, extend the wire
     * registry for those dependencies, and build the complete engine->wire
     * map from final indices rather than the pre-registration count. */
    native_count=BG_GetNumWeapons();
    if(native_count<1 || (unsigned)native_count>CODOL_WEAPON_SLOTS) goto fail;
    for(i=0;i<(unsigned)native_count;++i) {
        const struct WeaponDef *def=BG_GetWeaponDef(i);
        if(!def || !def->szInternalName || !*def->szInternalName ||
           !register_stock(r,names,&count,def->szInternalName) ||
           (mapping[i]=CODOL_FindRegisteredWeapon(r,def->szInternalName))<0) goto fail;
    }
    if(requested && mapping[requested_engine]!=requested_index) goto fail;
    for(i=0;i<CODOL_MAX_CONFIGSTRINGS;++i)
        if(published->values[i] && !CODOL_SetConfigstring(&next,i,published->values[i])) goto fail;
    for(i=first;i<count;++i)
        if(!CODOL_SetConfigstring(&next,CODOL_CS_WEAPONS+i,names[i])) goto fail;
    /* C1 4673d4 routes CS6517 updates to 47d1d0, which initializes
     * translated display names and weapon HUD records through count-1.
     * Updating definition names alone leaves a newly owned secondary's
     * display name null until its first viewmodel registration. */
    if(count>first) {
        char count_text[16];
        snprintf(count_text,sizeof(count_text),"%u",count);
        if(!CODOL_SetConfigstring(&next,CODOL_CS_WEAPON_COUNT,count_text)) goto fail;
    }
    /* The map validates duplicates/limits before changing either direction.
     * All remaining commits are non-failing swaps. */
    if(!CODOL_ReplaceWeaponMap(mapping,(unsigned)native_count)) goto fail;
    CODOL_ClearConfigstrings(published); *published=next;
    CODOL_DestroyWeaponRegistry(registry); registry=r; error[0]=0; ++registry_generation;
    CODOL_BroadcastWeaponConfigstrings(first,count-first);
    if(requested) report_weapon_budget(requested);
    if(requested_slot) *requested_slot=(unsigned)requested_index;
    return 1;
fail:
    rollback_native_weapons(&previous);
    CODOL_DestroyWeaponRegistry(r); CODOL_ClearConfigstrings(&next); return 0;
}
static int append_native_weapons(void)
{ return append_weapon_set(NULL,NULL); }
int CODOL_PublishComposedWeapon(const char *name,const char *base_name,unsigned *slot)
{
    codol_composed_weapon_t record; const char *registered_base;
    if(!valid || !registry || !slot || !base_name ||
       CODOL_ParseComposedWeaponName(name,&record)!=1 || strcmp(name,record.canonical) ||
       CODOL_RegisteredWeaponName(registry,record.base,&registered_base)!=1 ||
       strcmp(registered_base,base_name)) {
        strcpy(error,"composed publication requires a canonical name and matching published base"); return 0;
    }
    /* Replay/append even when the wire name already exists: an earlier caller
     * may have published it before native registration was required. This is
     * idempotent for both registries and repairs the engine->wire mapping. */
    if(!append_weapon_set(name,slot)) {
        strcpy(error,"composed weapon publication failed"); return -1;
    }
    return 1;
}
/* Where a category's weapon window comes from.
 *
 * MEASURED (docs/CODOL_CATEGORY_WEAPON_WINDOW_20260917.md), by decoding the
 * three shipped stringtables out of code_post_gfx_mp: EVERY category's constant
 * configstring table already carries the whole window in the CS_WEAPONS space
 * plus the CG_Init count at CS 6517 -
 *
 *   mp    CS 5363..5537  (indices 1..175, 22 holes)   CS 6517 = "176"
 *   coop  CS 5363..5425  (indices 1..63,  hole-free)  CS 6517 = "64"
 *   zm    CS 5363..5492  (indices 1..130, hole-free)  CS 6517 = "131"
 *
 * and CS 5363 is "defaultweapon_mp" in all three. sv_main.c installs the
 * category's own table as the inherited configstrings immediately before
 * calling us, so the window is already in hand with no extra asset lookup.
 *
 * The coop table's index 2 is "beretta_so", which is exactly the client's
 * 2026-08-19 coop failure `181 beretta_so 0 2` ("the name at slot 2 resolved
 * to 0, slot 2 demands 2") - the client does NOT skip a category it has no
 * server window for, it validates its own constants.
 *
 * mp stays on the measured attachment-table order: the const mp window has 22
 * holes an mp match would have to fill before its 176 could be published, and
 * that is a separate, live-path change. coop and zm are hole-free and are read
 * straight from the constants, which is what the client registers from.
 *
 * How far the category's window can actually be backed, established against a
 * scratch registry so nothing half-registered survives into the kept one.
 *
 * mp keeps its exact previous walk: the attachment table is an ORDERED LIST,
 * not a slot map - a parent's registration appends its launcher/masterkey
 * partner (+b78/+b88) between two rows, so row k does not sit at slot k+2 and
 * nothing may assume it does. A row that will not register is still a hard
 * failure there, as it always was.
 *
 * coop/zm walk the constants by SLOT, because the constant table IS the slot
 * map - the same one the client registers from, partner rows included (coop 12
 * `m16_grenadier_reddot_so` is followed by its launcher at 13, 49/50 and 36/37
 * likewise). When a slot is already filled by the partner the previous row
 * appended, agreeing with the constant is the check that our replay and the
 * client's are still in step; disagreeing means they have diverged and the rest
 * of the window is no longer trustworthy.
 *
 * Stopping short is the safe direction there. C1's CG_Init loop (0x47d1d0)
 * walks 1..count-1 over bg_weaponDefs and dereferences the definition at
 * 0x47c1f7 with no NULL check, so the published count must never exceed the
 * contiguous prefix that registered here; truncating costs weapons,
 * overshooting costs the client. Returns 0 on a hard failure. */
static unsigned collect_weapon_window(const codol_engine_table_t *table,
                                      const codol_configstrings_t *inherited,const char **names,
                                      const char **stopped_name,unsigned *stopped_slot)
{
    codol_weapon_registry_t *scratch;
    unsigned count=0,i;
    *stopped_name=NULL; *stopped_slot=0;
    if(!(scratch=CODOL_CreateWeaponRegistry())) return 0;
    if(!register_stock(scratch,names,&count,"none") || count!=1 ||
       !register_stock(scratch,names,&count,"defaultweapon_mp") || count!=2) { count=0; goto done; }
    if(table) {
        for(i=0;i<(unsigned)table->rowCount;++i)
            if(!register_stock(scratch,names,&count,table->values[(size_t)i*table->columnCount])) { count=0; goto done; }
        goto done;
    }
    for(i=2;i<CODOL_WEAPON_SLOTS;++i) {
        const char *name=CODOL_GetConfigstring(inherited,CODOL_CS_WEAPONS+i);
        if(!name || !*name) break;
        if(i<count) {
            if(!strcmp(names[i],name)) continue;
            *stopped_name=name; *stopped_slot=i; count=i; break;
        }
        if(count!=i || !register_stock(scratch,names,&count,name)) {
            *stopped_name=name; *stopped_slot=i; count=i; break;
        }
    }
done:
    CODOL_DestroyWeaponRegistry(scratch);
    return count;
}

int CODOL_InitializeServerWeaponConfigstrings(const char *zone_type)
{
    const codol_engine_table_t *table=NULL;
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    const char *names[CODOL_WEAPON_SLOTS]={0},*stopped_name=NULL,*demanded;
    codol_configstrings_t next={0},*published=CODOL_ServerConfigstrings();
    codol_weapon_registry_t *r=NULL; unsigned count,i,stopped_slot=0;
    /* registry/valid/error are file-static and outlive a match. A category
     * change must not be able to leave the previous category's registry
     * installed behind a failed rebuild, and the per-client ammo-refusal
     * latches belong to the match that set them. */
    CODOL_ResetServerWeaponRegistry();
    memset(codol_ammo_binding_refused,0,sizeof(codol_ammo_binding_refused));
    if(!zone_type || (strcmp(zone_type,"mp") && strcmp(zone_type,"coop") && strcmp(zone_type,"zm")) ||
       !inherited) { strcpy(error,"invalid zone type or missing constants"); return 0; }
    if(!strcmp(zone_type,"mp") && (CODOL_LoadEngineStringTable("mp/coWeaponAttachmentTable.csv",&table)!=1 ||
       !table || table->columnCount<=0 || table->rowCount<0 || (table->rowCount && !table->values))) {
        strcpy(error,"MP weapon attachment table unavailable"); return 0;
    }
    count=collect_weapon_window(table,inherited,names,&stopped_name,&stopped_slot);
    /* register_stock already names the weapon it could not build; only say
     * something when nothing did. */
    if(count<2) {
        if(!*error) strcpy(error,"implicit none/defaultweapon_mp could not be registered");
        return 0;
    }
    error[0]=0; /* a truncation names its weapon in the log, not in the error */
    /* Replayed from exactly the names that survived the probe, so the kept
     * registry holds no slot the published window does not name. */
    if(!(r=CODOL_CreateWeaponRegistry())) goto fail;
    for(i=0;i<count;++i) if(!replay_weapon(r,i,names[i])) goto fail;
    for(i=0;i<CODOL_MAX_CONFIGSTRINGS;++i)
        if(published->values[i] && !CODOL_SetConfigstring(&next,i,published->values[i])) goto fail;
    /* The tail is blanked, not left inherited: CODOL_WriteConfigstrings sends
     * every non-NULL value including the empty ones, which is what suppresses
     * the constants above our count on the client and keeps its registration
     * order identical to ours. */
    for(i=0;i<CODOL_WEAPON_SLOTS;++i)
        if(!CODOL_SetConfigstring(&next,CODOL_CS_WEAPONS+i,i<count ? names[i] : "")) goto fail;
    /* CS 6517 is the number of weapon definitions the client registers in
     * CG_Init (loop at C1 0x47d1d0, 1..count-1 over bg_weaponDefs). Publishing
     * the const table's own value would make that loop dereference a NULL
     * definition at 0x47c1f7 for every index this window does not back;
     * alpha0022 configstring_map.py documents the same invariant (count <=
     * published, buildable definitions). What goes out is our own prefix, for
     * every category - an empty value here used to mean "coop/zm skip the
     * loop", which the coop transcript refutes. */
    {
        char count_text[16];
        snprintf(count_text,sizeof(count_text),"%u",count);
        if(!CODOL_SetConfigstring(&next,CODOL_CS_WEAPON_COUNT,count_text)) goto fail;
    }
    CODOL_ClearConfigstrings(published); *published=next;
    CODOL_DestroyWeaponRegistry(registry); registry=r; valid=1; ++registry_generation;
    /* One line per map saying what this category asked for and what it got, so
     * a short window is a diagnosis instead of a silent unarmed match. */
    demanded=CODOL_GetConfigstring(inherited,CODOL_CS_WEAPON_COUNT);
    if(stopped_name)
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL weapon window (%s): published %u of the %s its constants demand; "
            "truncated at slot %u by '%s' (not buildable from the mounted archives, "
            "or out of step with the constant order)\n",
            zone_type,count,demanded && *demanded ? demanded : "?",stopped_slot,stopped_name);
    else
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL weapon window (%s): published %u definitions, CS %u = %u (constants demand %s)\n",
            zone_type,count,(unsigned)CODOL_CS_WEAPON_COUNT,count,
            demanded && *demanded ? demanded : "?");
    report_weapon_budget("map start");
    return 1;
fail:
    if(!*error) strcpy(error,"weapon configstring initialization failed");
    CODOL_DestroyWeaponRegistry(r); CODOL_ClearConfigstrings(&next); return 0;
}
#endif
