#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_profile.h"
#include "codol_script_profile_vm.h"
#include "codol_stats.h"
#include "cvar.h"
/* <player> isItemUnlocked( <item> )
 *
 * IW4 method 0x5f9960 (table entry 0x79afc0). The requirement columns come
 * from the mounted CoDOL tables and the player's own secure profile; the
 * definition set and the profile blob are the ones the playerdata script
 * accessors observe, so a script write made this session is read back here.
 *
 * There is no unlocked-by-default answer for a missing or unreadable profile,
 * table or requirement: each of those is a script error. The single true
 * result this returns without proving a requirement is for an item that
 * mp/unlocktable.csv does not list at all, which is what IW4 itself answers
 * and what CODOL_ProfileItemUnlocked documents. */
/* Resolve one item for a player. On success returns 1 with *value set; on
 * failure returns 0 with *reason naming what could not be established. The
 * two script methods below differ only in what they do with a failure. */
static int item_unlocked(scr_entref_t ref,const char *item,int *value,const char **reason)
{
    const codol_structured_schema_t *schema;const uint8_t *profile;
    const codol_engine_table_t *unlocks=NULL,*ranks=NULL,*challenges=NULL;
    int status;cvar_t *root;
    schema=CODOL_ScriptProfileSchema(CODOL_PROFILE_SECURE);
    profile=CODOL_ScriptProfileBlob(ref.entnum,CODOL_PROFILE_SECURE);
    if(!schema){*reason="isItemUnlocked requires the mounted mp/playersecuredata.def";return 0;}
    if(!profile){*reason="isItemUnlocked requires a server-bound secure profile";return 0;}
    status=CODOL_LoadEngineStringTable("mp/unlocktable.csv",&unlocks);
    root=Cvar_FindVar("codol_scriptPath");
    if(!status && root)status=CODOL_LoadReferenceStringTable(root->string,"mp/unlocktable.csv",&unlocks);
    if(status!=1 || CODOL_LoadEngineStringTable("mp/rankTable.csv",&ranks)!=1 ||
       CODOL_LoadEngineStringTable("mp/allChallengesTable.csv",&challenges)!=1) {
        *reason="isItemUnlocked requires the mounted unlock, rank and challenge tables";return 0;
    }
    if(!CODOL_ProfileItemUnlocked(profile,CODOL_STATS_SIZE,schema,unlocks,ranks,challenges,item,value)) {
        *reason="isItemUnlocked: this profile does not satisfy the table's requirement semantics";return 0;
    }
    return 1;
}
static const char *player_item_param(scr_entref_t ref,const char *method)
{
    const char *item;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client ||
       !g_entities[ref.entnum].r.inuse) {Scr_Error(va("%s: entity must be a player entity",method));return NULL;}
    if(Scr_GetNumParam()!=1){Scr_Error(va("%s requires one item name",method));return NULL;}
    item=Scr_GetString(0);
    if(!item || !*item){Scr_ParamError(0,va("%s requires one item name",method));return NULL;}
    return item;
}
void CODOL_Scr_IsItemUnlocked(scr_entref_t ref)
{
    const char *item,*reason=NULL;int value;
    if(!(item=player_item_param(ref,"isItemUnlocked")))return;
    if(!item_unlocked(ref,item,&value,&reason)){Scr_Error(reason);return;}
    Scr_AddInt(value);
}
/* <player> codol_tryIsItemUnlocked( <item> )
 *
 * isItemUnlocked without the script error: the same resolution, but an item
 * whose requirement cannot be established returns undefined (and says why on
 * the console) instead of stopping the VM. A loadout asks this so that one
 * bad unlock row cannot abort a spawn; the caller decides what undefined
 * means. Argument errors (not a player, no item) are still script errors. */
void CODOL_Scr_TryIsItemUnlocked(scr_entref_t ref)
{
    const char *item,*reason=NULL;int value;
    if(!(item=player_item_param(ref,"codol_tryIsItemUnlocked")))return;
    if(!item_unlocked(ref,item,&value,&reason)) {
        Com_Printf(CON_CHANNEL_SCRIPT,"^3codol_tryIsItemUnlocked(%s) for client %d: %s\n",item,ref.entnum,reason);
        Scr_AddUndefined();
        return;
    }
    Scr_AddInt(value);
}
/* <player> codol_tryChallengeState( <challenge ref> )
 *
 * The derived state of one challenge for this player: one plus the number of
 * mp/allChallengesTable.csv targets the stored progress (secure profile
 * challenges[<column 4 id>]) has reached -- the value C1's unlock flags and
 * IW4's unlock rules compare against (a tier N gate is met when state > N).
 * Returns undefined, with the reason on the console, when the player has no
 * bound secure profile or the challenge cannot be resolved; it never stops
 * the VM, because a loadout asks it in the middle of a spawn. */
void CODOL_Scr_TryChallengeState(scr_entref_t ref)
{
    const codol_structured_schema_t *schema;const uint8_t *profile;
    const codol_engine_table_t *challenges=NULL;const char *ref_name,*reason=NULL;int state;
    if(!(ref_name=player_item_param(ref,"codol_tryChallengeState")))return;
    schema=CODOL_ScriptProfileSchema(CODOL_PROFILE_SECURE);
    profile=CODOL_ScriptProfileBlob(ref.entnum,CODOL_PROFILE_SECURE);
    if(!schema)reason="requires the mounted mp/playersecuredata.def";
    else if(!profile)reason="requires a server-bound secure profile";
    else if(CODOL_LoadEngineStringTable("mp/allChallengesTable.csv",&challenges)!=1)
        reason="requires the mounted challenge table";
    else if(!CODOL_ProfileChallengeState(profile,CODOL_STATS_SIZE,schema,challenges,ref_name,&state))
        reason="the challenge has no stored progress or targets";
    if(reason) {
        Com_Printf(CON_CHANNEL_SCRIPT,"^3codol_tryChallengeState(%s) for client %d: %s\n",ref_name,ref.entnum,reason);
        Scr_AddUndefined();
        return;
    }
    Scr_AddInt(state);
}
#endif
