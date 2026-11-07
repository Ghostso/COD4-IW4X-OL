#include "codol_sv_weapons.h"
#include "codol_sv_state.h"
#include "codol_weapon_native.h"
#include "codol_usercmd.h"
#include "codol_game.h"
#include "codol_weapon_slots.h"
#include "codol_weapon_compose.h"
#include "codol_weapon_bits.h"
#include "codol_playerstate_ext.h"
#include "qcommon_io.h"
#include "server.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
static int native_count=3;
static struct WeaponDef native_defs[3];
static unsigned broadcasts,broadcast_first,broadcast_count;
/* The fixture runs the production registry, server publication and engine
 * mapping over a synthetic retained-engine table. Only engine-owned services
 * and the unrelated composed-weapon/map-sun adapters are supplied here. */
cvar_t *codol_debugTrace;
serverStatic_t svs;
static gclient_t fixture_client;
const void *CODOL_PlayerStateExtLiveBase(unsigned *count)
{if(count)*count=1;return &fixture_client;}
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count)
{if(count)*count=0;return NULL;}
const void *CODOL_PlayerStateExtArchiveBase(unsigned *count)
{if(count)*count=0;return NULL;}
unsigned int bg_numAmmoTypes=1, bg_numWeapClips=1, bg_numSharedAmmoCaps=1;
unsigned int bg_lastParsedWeaponIndex;
struct WeaponDef *bg_weapAmmoTypes[CODOL_NATIVE_AMMO_POOL];
struct WeaponDef *bg_weapClips[CODOL_NATIVE_AMMO_POOL];
struct WeaponDef *bg_sharedAmmoCaps[CODOL_NATIVE_AMMO_POOL];
struct WeaponDef *bg_weaponDefs[CODOL_WEAPON_SLOTS+1];
void Com_Printf(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
void Com_PrintWarning(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
int CODOL_RefreshMapSunSampleSize(void){return 1;}
void CODOL_ResetMapSunSampleSize(void){}
int CODOL_RegisterComposedWeaponKeys(codol_weapon_registry_t *r,unsigned slot,const char *name)
{(void)r;(void)slot;(void)name;assert(!"composed weapon outside this fixture");return 0;}
int CODOL_ParseComposedWeaponName(const char *name,codol_composed_weapon_t *out)
{(void)out;assert(name && name[0]!='*');return 0;}
int CODOL_ComposedWeaponTail(const char *name,codol_weapon_tail_t *out)
{(void)name;(void)out;assert(!"composed weapon outside this fixture");return 0;}
int CODOL_LoadComposedWeapon(const char *name,const struct WeaponDef **out)
{(void)name;(void)out;assert(!"composed weapon outside this fixture");return 0;}
int BG_GetWeaponIndexForName(const char *name,void (*register_weapon)(unsigned))
{(void)name;(void)register_weapon;assert(!"native append outside this fixture");return 0;}
void G_RegisterWeapon(unsigned weapon)
{(void)weapon;assert(!"native append outside this fixture");}
void CODOL_BroadcastWeaponConfigstrings(unsigned first,unsigned count)
{
    ++broadcasts; broadcast_first=first; broadcast_count=count;
    assert(CODOL_WeaponToWire(2)==4);
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5366),"m4_mp"));
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5367),"gl_m4_mp"));
}
int BG_GetNumWeapons(void) { return native_count; }
struct WeaponDef *BG_GetWeaponDef(int index) { assert(index>=0 && index<3); return native_defs+index; }
/* Mounted facts are controlled here; actual mounted loading is covered by
 * test_codol_weapon_loader. Configstring precedence and registry are real. */
int CODOL_RegisterMountedWeaponKeys(codol_weapon_registry_t *r,unsigned slot,const char *name)
{
    if(!strcmp(name,"scar_mp") || !strcmp(name,"scarsapr_mp"))
        return CODOL_RegisterWeaponKeys(r,slot,name,"nato","scar_clip",1,0,-1);
    if(!strcmp(name,"none") || !strcmp(name,"defaultweapon_mp") ||
       !strcmp(name,"m4_mp") || !strcmp(name,"gl_m4_mp"))
        return CODOL_RegisterWeaponKeys(r,slot,name,NULL,NULL,0,0,-1);
    return 0;
}
static int table_failure,partner_failure;
int CODOL_LoadEngineStringTable(const char *name,const codol_engine_table_t **out)
{
    static const char *cells[]={"scar_mp","scar_mp","scarsapr_mp"};
    static codol_engine_table_t table={"mp/coWeaponAttachmentTable.csv",1,3,cells};
    assert(!strcmp(name,table.name)); if(table_failure) return -1;
    *out=&table; return 1;
}
int CODOL_LoadMountedWeaponTail(const char *name,codol_weapon_tail_t *out)
{
    if(partner_failure && !strcmp(name,"gl_m4_mp")) return -1;
    memset(out,0,sizeof(*out));
    out->count=1; out->entries[0].offset=0xb78; out->entries[0].kind=CODOL_WEAPON_DEP_STRING;
    if(!strcmp(name,"scar_mp")) out->entries[0].name="scarsapr_mp";
    if(!strcmp(name,"scarsapr_mp")) out->entries[0].name="scar_mp"; /* Already registered cycle. */
    if(!strcmp(name,"m4_mp")) out->entries[0].name="gl_m4_mp";
    if(!strcmp(name,"gl_m4_mp")) out->entries[0].name="m4_mp";
    return 1;
}
int main(void)
{
    const char *cells[]={"5364","scar_mp","5365","scarsapr_mp"};
    const codol_weapon_registry_t *r; int ammo=-99,clip=-99;
    assert(!CODOL_RefreshServerWeaponRegistry() && !CODOL_ServerWeaponRegistry());
    assert(CODOL_SetServerInheritedConfigstrings("mp",2,cells));
    assert(CODOL_RefreshServerWeaponRegistry()); r=CODOL_ServerWeaponRegistry();
    assert(r && CODOL_GetWeaponKeys(r,0,&ammo,&clip) && !ammo && !clip);
    assert(CODOL_GetWeaponKeys(r,1,&ammo,&clip) && ammo==1 && clip==1);
    assert(CODOL_GetWeaponKeys(r,3,&ammo,&clip) && ammo==2 && clip==2);
    native_defs[0].szInternalName="none"; native_defs[1].szInternalName="scarsapr_mp";
    native_defs[2].szInternalName="scar_mp";
    assert(CODOL_RefreshServerWeaponMappings());
    assert(CODOL_WeaponToWire(1)==3 && CODOL_WeaponToEngine(3)==1);
    assert(CODOL_WeaponToWire(2)==2 && CODOL_WeaponToEngine(2)==2 && CODOL_WeaponToEngine(1)==-1);
    {
        codol_usercmd_t wire={0}; usercmd_t command;
        wire.serverTime=1234; wire.weapon=3; wire.offHandIndex=2; wire.direction=1;
        CODOL_ToEngineUsercmd(&wire,&command,0,0);
        assert(command.weapon==1 && command.offHandIndex==2 && command.serverTime==1234 && command.forwardmove==127);
        /* Same definition count, different native registration order: a count
         * cache would miss this change. The next input uses the new mapping. */
        native_defs[1].szInternalName="scar_mp"; native_defs[2].szInternalName="scarsapr_mp";
        assert(CODOL_RefreshServerWeaponMappings());
        CODOL_ToEngineUsercmd(&wire,&command,0,0);
        assert(command.weapon==2 && command.offHandIndex==1);
        wire.weapon=699; CODOL_ToEngineUsercmd(&wire,&command,2,0);
        assert(command.weapon==2); /* Unloaded client ID retains current weapon. */
        native_defs[1].szInternalName="scarsapr_mp"; native_defs[2].szInternalName="scar_mp";
        assert(CODOL_RefreshServerWeaponMappings());
    }
    native_defs[2].szInternalName="unpublished";
    assert(!CODOL_RefreshServerWeaponMappings());
    assert(CODOL_WeaponToEngine(3)==1 && CODOL_WeaponToWire(2)==2);
    native_defs[2].szInternalName="scarsapr_mp";
    assert(!CODOL_RefreshServerWeaponMappings() && CODOL_WeaponToWire(2)==2);
    native_defs[2].szInternalName="scar_mp"; native_count=CODOL_WEAPON_SLOTS+1;
    assert(!CODOL_RefreshServerWeaponMappings() && CODOL_WeaponToEngine(3)==1);
    native_count=1; assert(CODOL_RefreshServerWeaponMappings());
    assert(CODOL_WeaponToWire(1)==-1 && CODOL_WeaponToEngine(3)==-1);
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),5364,"unresolved"));
    assert(!CODOL_RefreshServerWeaponRegistry() && !CODOL_ServerWeaponRegistry());
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),5364,""));
    assert(!CODOL_RefreshServerWeaponRegistry() && !CODOL_ServerWeaponRegistry());
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),5364,"scar_mp"));
    assert(CODOL_RefreshServerWeaponRegistry());
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),5365,""));
    assert(CODOL_RefreshServerWeaponRegistry());
    r=CODOL_ServerWeaponRegistry(); ammo=clip=-99;
    assert(!CODOL_GetWeaponKeys(r,3,&ammo,&clip) && ammo==-99 && clip==-99);
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),5363,"scar_mp"));
    assert(!CODOL_RefreshServerWeaponRegistry() && !CODOL_ServerWeaponRegistry());
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),42,"unrelated"));
    assert(CODOL_InitializeServerWeaponConfigstrings("mp"));
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5364),"scar_mp"));
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5365),"scarsapr_mp"));
    assert(!*CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5439)); /* Stale inherited tail suppressed. */
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),42),"unrelated"));
    assert(CODOL_RefreshServerWeaponRegistry());
    table_failure=1;
    native_count=3; native_defs[2].szInternalName="m4_mp";
    partner_failure=1; r=CODOL_ServerWeaponRegistry();
    assert(!CODOL_RefreshServerWeaponMappings() && CODOL_ServerWeaponRegistry()==r && !broadcasts);
    assert(!*CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5366));
    assert(CODOL_WeaponToWire(2)==-1);
    partner_failure=0;
    assert(CODOL_RefreshServerWeaponMappings());
    assert(broadcasts==1 && broadcast_first==4 && broadcast_count==2);
    assert(CODOL_WeaponToWire(1)==3 && CODOL_WeaponToWire(2)==4);
    assert(CODOL_GetWeaponKeys(CODOL_ServerWeaponRegistry(),5,&ammo,&clip) && ammo==4 && clip==4);
    assert(CODOL_RefreshServerWeaponMappings() && broadcasts==1);
    native_defs[2].szInternalName="unknown_stock";
    r=CODOL_ServerWeaponRegistry();
    assert(!CODOL_RefreshServerWeaponMappings() && CODOL_ServerWeaponRegistry()==r);
    assert(CODOL_WeaponToWire(2)==4 && broadcasts==1);
    assert(!*CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5368));
    native_defs[2].szInternalName="m4_mp";
    {
        playerState_t *ps=&fixture_client.ps;
        codol_engine_player_bindings_t binding={0},before;
        binding.alt_weapon=73;
        native_defs[1].iAmmoIndex=7; native_defs[1].iClipIndex=9;
        native_defs[2].iAmmoIndex=8; native_defs[2].iClipIndex=10;
        CODOL_WeaponBitsOwnedSet(ps,1,1); CODOL_WeaponBitsOwnedSet(ps,2,1);
        ps->ammo[7]=90; ps->ammo[8]=75;
        ps->ammoclip[9]=30; ps->ammoclip[10]=25;
        assert(CODOL_BuildServerAmmoBindings(&binding,ps));
        assert(binding.alt_weapon==73 && binding.clip_mask==0x7fff && binding.reserve_mask==0x7fff);
        assert(binding.clips[0].engine_index==9 && binding.clips[0].wire_key==2);
        assert(binding.clips[1].engine_index==10 && binding.clips[1].wire_key==3);
        assert(binding.reserves[0].engine_index==7 && binding.reserves[0].wire_key==2);
        {
            codol_player_array_updates_t updates={0};
            assert(CODOL_OverlayEngineAmmo(&updates,ps,binding.clip_mask,binding.clips,
                binding.reserve_mask,binding.reserves));
            assert(updates.clip_ammo[0][0]==30 && updates.clip_ammo[1][0]==25);
            assert(updates.reserve_ammo[0]==90 && updates.reserve_ammo[1]==75);
        }
        before=binding; CODOL_WeaponBitsOwnedSet(ps,3,1); /* Owned but not loaded. */
        assert(!CODOL_BuildServerAmmoBindings(&binding,ps) && !memcmp(&binding,&before,sizeof(binding)));
        CODOL_WeaponBitsInventoryClear(ps);
        assert(CODOL_BuildServerAmmoBindings(&binding,ps));
        assert(binding.clips[0].engine_index==-1 && binding.reserves[0].engine_index==-1);
    }
    assert(!CODOL_InitializeServerWeaponConfigstrings("mp") && !CODOL_ServerWeaponRegistry());
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),5364),"scar_mp"));
    CODOL_ResetServerWeaponRegistry(); CODOL_ResetServerConfigstrings();
    assert(!CODOL_ServerWeaponRegistry());
    puts("PASS: server weapon registry follows inherited/override names, rejects gaps and invalidates failed refreshes");
    return 0;
}
