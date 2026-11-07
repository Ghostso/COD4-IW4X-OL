/* Native perk ownership and publication. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_perk_runtime.h"
#include "codol_perk_effects.h"
#include "codol_playerstate_ext.h"
#include "codol_sv_state.h"
#include "g_shared.h"
#include <string.h>
#include <math.h>

/* Authoring state belongs only to live players. Captured/archived playerstate
 * already carries the effective abilities and resulting movement multiplier;
 * replay never consults these mutable sources. */
static struct {
    codol_client_abilities_t script;
    uint32_t written_values;
    codol_perk_effects_t perk;
} sources[MAX_CLIENTS];

void CODOL_ResetPerkRuntime(unsigned client)
{
    if(client<MAX_CLIENTS) memset(&sources[client],0,sizeof(sources[client]));
}
static codol_ps_ext_t *live_extension(unsigned client)
{
    if(client>=MAX_CLIENTS || !level.clients || client>=(unsigned)level.maxclients) return NULL;
    return CODOL_PlayerStateExt(&level.clients[client].ps);
}
static int merge(const codol_client_abilities_t *script,const codol_perk_effects_t *perk,
                 uint32_t written_values,const codol_engine_table_t *table,codol_client_abilities_t *out)
{
    unsigned id,slot;
    codol_client_abilities_t result=*script;
    for(id=0;id<128;++id) {
        uint32_t bit=UINT32_C(0x80000000)>>(id&31);
        if(!(perk->abilities.masks[id>>5]&bit)) continue;
        /* Explicit script activation owns its value; otherwise the perk's
         * aggregated value is published. Removing either source reveals the
         * remaining source, rather than clearing unrelated modifiers. */
        if(!(script->masks[id>>5]&bit)) {
            int status=CODOL_ReadAbilityValueSlot(table,id,&slot);
            if(status<0)return 0;
            if(status==1 && !(written_values&(UINT32_C(1)<<slot)))
                result.values[slot]=perk->abilities.values[slot];
        }
        result.masks[id>>5]|=bit;
    }
    *out=result;return 1;
}
int CODOL_GetScriptAbilities(unsigned client,codol_client_abilities_t *out)
{
    if(client>=MAX_CLIENTS || !out)return 0;
    *out=sources[client].script;return 1;
}
int CODOL_GetSelectedPerkValue(const playerState_t *ps,unsigned id,float *out)
{
    unsigned client;
    if(!ps || !out || id>=128)return 0;
    client=(unsigned)ps->clientNum;
    if(client>=MAX_CLIENTS || !level.clients || client>=(unsigned)level.maxclients ||
       ps!=&level.clients[client].ps ||
       !(sources[client].perk.server_value_masks[id>>5]&(UINT32_C(0x80000000)>>(id&31))))
        return 0;
    *out=sources[client].perk.server_values[id];return 1;
}
/* Abilities every player of an asset category has by virtue of the mode,
 * independent of the perks they selected.
 *
 * Today that is exactly one: zm gives everyone C1 ability 8 "modPistolDeath"
 * (ps+0x4d0 bit 23, C1 0x51c1c4) -- last stand. Going down is not a perk in
 * Zombies, it is the mode. CODOL_LastStand_CanEnter
 * (codol_script_laststand.c:100) gates the ENGINE's own last stand on that
 * bit and no GSC path sets it, so without this the down has to be faked in
 * script and the client never gets ps.pm_type 7, the 500 ms grace window or
 * the correct wire state.
 *
 * Gated on the mounted asset category, so an mp or coop match is bit-for-bit
 * unchanged. Deliberately a floor, not an override: it only ever adds, so a
 * perk or script that already granted the ability is unaffected. */
static void apply_category_ability_floor(codol_client_abilities_t *effective)
{
    const char *zone;
    if(!effective) return;
    zone = CODOL_ServerZoneType();
    if(zone && !strcmp(zone, "zm"))
        effective->masks[0] |= UINT32_C(0x00800000);
}
int CODOL_CommitScriptAbilities(unsigned client,const codol_client_abilities_t *state,int written_value_slot)
{
    const codol_engine_table_t *table;
    codol_client_abilities_t effective;
    codol_ps_ext_t *ext=live_extension(client);
    uint32_t written;
    if(!ext || !state || written_value_slot< -1 || written_value_slot>=CODOL_ABILITY_VALUES)return 0;
    written=sources[client].written_values;
    if(written_value_slot>=0)written|=UINT32_C(1)<<written_value_slot;
    if(CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1 ||
       !merge(state,&sources[client].perk,written,table,&effective))return 0;
    sources[client].written_values=written;
    sources[client].script=*state;
    apply_category_ability_floor(&effective);
    ext->abilities=effective;ext->abilities_known=1;return 1;
}
int CODOL_CommitPerkState(unsigned client,const codol_perk_state_t *selection)
{
    const codol_engine_table_t *perks,*abilities;
    codol_perk_effects_t effects;
    codol_client_abilities_t effective;
    codol_ps_ext_t *ext=live_extension(client);
    if(!ext || !selection || CODOL_LoadEngineStringTable("mp/coPerkStatsTable.csv",&perks)!=1 ||
       CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&abilities)!=1 ||
       CODOL_BuildPerkEffects(selection,perks,abilities,&effects)!=1 ||
       !merge(&sources[client].script,&effects,sources[client].written_values,abilities,&effective))return 0;
    sources[client].perk=effects;ext->perks=*selection;
    apply_category_ability_floor(&effective);
    ext->abilities=effective;ext->abilities_known=1;return 1;
}
void CODOL_UpdatePerkMoveSpeed(playerState_t *ps,float base)
{
    unsigned client;
    float scale=1.0f;
    if(!ps)return;
    client=(unsigned)ps->clientNum;
    if(client<MAX_CLIENTS && level.clients && client<(unsigned)level.maxclients &&
       ps==&level.clients[client].ps &&
       (sources[client].perk.server_value_masks[42>>5]&(UINT32_C(0x80000000)>>(42&31))))
        scale=sources[client].perk.server_values[42];
    /* Write once at the session->playerstate producer, so native movement and
     * the C1 snapshot's +254 use the same combined weapon/script/perk scale. */
    ps->moveSpeedScaleMultiplier=base*scale;
}
#endif
