/* Native C1 perk slot VM methods. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_playerstate_ext.h"
#include "codol_perk_runtime.h"
#include "qcommon.h"
#include <string.h>
enum { PERK_SET, PERK_HAS, PERK_UNSET, PERK_CLEAR };
static void perk_method(scr_entref_t ref, unsigned operation)
{
    codol_ps_ext_t *extension;
    codol_perk_definition_t definition;
    const codol_engine_table_t *table;
    int status, present;
    codol_perk_state_t next;
    if(ref.classnum) { Scr_ObjectError("not an entity"); return; }
    if(ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player",ref.entnum)); return;
    }
    /* C1 ClearPerks has no parameter-count check; the other three require 1. */
    if(operation!=PERK_CLEAR) {
        const char *name;
        /* IW4's hasPerk takes an optional second flag (its scripts pass
         * "true" for the upgraded-perk check); the setters take one name. */
        if(Scr_GetNumParam()<1 || Scr_GetNumParam()>(operation==PERK_HAS ? 2 : 1)) {
            Scr_Error("perk operation requires one perk name"); return;
        }
        name=Scr_GetString(0);
        /* IW4's "specialty_null" is the empty perk slot: its scripts give it
         * and query it like any other perk and the engine answers with a
         * no-op. CoDOL's table has no such row, so it is answered here. */
        if(name && !Q_stricmp(name,"specialty_null")) {
            if(operation==PERK_HAS) Scr_AddInt(0);
            return;
        }
        if(CODOL_LoadEngineStringTable("mp/coPerkStatsTable.csv",&table)!=1) {
            Scr_Error("perk table unavailable"); return;
        }
        if(CODOL_ReadPerkDefinition(table,name,&definition)!=1) {
            /* The IW4 gametype scripts name IW4 perks that CoDOL's table does
             * not carry. Adaptation: an unknown name is reported once in
             * developer mode and treated as absent, instead of ending the
             * spawn. C1 itself rejects unknown names with this error. */
            static char reported[32][48]; static unsigned reported_count;
            unsigned i; int seen=0;
            for(i=0;i<reported_count;++i) if(!strcmp(reported[i],name)) { seen=1; break; }
            if(!seen && reported_count<32) {
                Q_strncpyz(reported[reported_count++],name,48);
                Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL perk '%s' is not in mp/coPerkStatsTable.csv; "
                    "treated as absent (unknown or malformed perk in C1)\n",name);
            }
            if(operation==PERK_HAS) Scr_AddInt(0);
            return;
        }
    }
    extension=CODOL_PlayerStateExt(&g_entities[ref.entnum].client->ps);
    if(!extension) { Scr_Error("perk playerState storage unavailable"); return; }
    next=extension->perks;
    switch(operation) {
    case PERK_SET: status=CODOL_SetPerk(&next,&definition); break;
    case PERK_UNSET: status=CODOL_UnsetPerk(&next,&definition); break;
    case PERK_HAS:
        if(!CODOL_HasPerk(&extension->perks,&definition,&present)) {
            Scr_Error("invalid perk query"); return;
        }
        Scr_AddInt(present); return;
    default: CODOL_ClearPerks(&next); status=1; break;
    }
    if(!status || !CODOL_CommitPerkState(ref.entnum,&next))
        Scr_Error("invalid perk effect update or malformed modifier table");
}
void CODOL_Scr_SetPerk(scr_entref_t ref) { perk_method(ref,PERK_SET); }
void CODOL_Scr_HasPerk(scr_entref_t ref) { perk_method(ref,PERK_HAS); }
void CODOL_Scr_UnsetPerk(scr_entref_t ref) { perk_method(ref,PERK_UNSET); }
void CODOL_Scr_ClearPerks(scr_entref_t ref) { perk_method(ref,PERK_CLEAR); }
#endif
