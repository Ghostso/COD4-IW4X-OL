/* Native C1 profile rank/within-rank XP bridge for retained total-XP scripts.
 * Read conversion is CODOL_ProfileExperience's recovered C1 algorithm.
 * Writes normalize that representation against the current mounted rank table;
 * they edit the existing secure session view, never generic getter semantics.
 */
#ifdef CODOL_SERVER
#include "codol_script_rank_experience.h"
#include "codol_script_profile_vm.h"
#include "codol_profile.h"
#include "codol_stats.h"
#include "codol_assets.h"
#include "scr_vm_functions.h"
#include "server.h"
#include "zlib/zlib.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <limits.h>

static int receiver(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=MAX_CLIENTS ||
       !g_entities[ref.entnum].r.inuse || !g_entities[ref.entnum].client) {
        Scr_ObjectError("rank experience: entity must be a player");return 0;
    }
    return 1;
}
static int rank_view(unsigned client,const codol_structured_schema_t **schema,
    const codol_engine_table_t **table,const uint8_t **blob,int *rank,int *total)
{
    *schema=CODOL_ScriptProfileSchema(CODOL_PROFILE_SECURE);
    *blob=CODOL_ScriptProfileBlob(client,CODOL_PROFILE_SECURE);
    return *schema && *blob && CODOL_LoadEngineStringTable("mp/rankTable.csv",table)==1 &&
        CODOL_ProfileExperience(*blob,CODOL_STATS_SIZE,*schema,*table,rank,total);
}
void CODOL_Scr_GetRankExperience(scr_entref_t ref)
{
    const codol_structured_schema_t *schema;const codol_engine_table_t *table;
    const uint8_t *blob;int rank,total;
    if(!receiver(ref))return;
    if(Scr_GetNumParam()!=0) {Scr_Error("getRankExperience requires no arguments");return;}
    if(!rank_view(ref.entnum,&schema,&table,&blob,&rank,&total)) {
        Scr_Error("getRankExperience: secure rank/experience/version or mounted rank table is invalid");return;
    }
    Scr_AddInt(total);
}
static int integer(const char *s,int *out)
{
    char *end;long v;
    if(!s || !*s)return 0;
    errno=0;v=strtol(s,&end,10);
    if(errno==ERANGE || end==s || *end || v<0 || v>INT_MAX)return 0;
    *out=(int)v;return 1;
}
static const char **find_row(const codol_engine_table_t *t,const char *key)
{
    const char **found=NULL;int i;
    for(i=0;i<t->rowCount;++i) {
        const char **r=t->values+(size_t)i*t->columnCount;
        if(r[0] && !strcmp(r[0],key)) {if(found)return NULL;found=r;}
    }
    return found;
}
void CODOL_Scr_SetRankExperience(scr_entref_t ref)
{
    const codol_structured_schema_t *schema;const codol_engine_table_t *table;
    const codol_structured_definition_t *def;const uint8_t *blob,*record;
    codol_structured_field_t fields[3];size_t capacity;
    static const char *names[]={"rank","experience","rankVersion"};
    const char **row,**metadata;char key[16];int rank,total,oldrank,oldtotal,minimum,version,i;
    uint32_t values[3],crc;uint8_t *copy,*session;
    if(!receiver(ref))return;
    if(Scr_GetNumParam()!=1) {Scr_Error("setRankExperience requires total XP");return;}
    total=Scr_GetInt(0);
    if(total<0) {Scr_ParamError(0,"total XP must be nonnegative");return;}
    if(!rank_view(ref.entnum,&schema,&table,&blob,&oldrank,&oldtotal) ||
       !CODOL_RankForExperience(table,total,&rank) || rank==INT_MAX ||
       !CODOL_ProfileRecord(blob,CODOL_STATS_SIZE,schema,&def,&record,&capacity)) {
        Scr_Error("setRankExperience: invalid secure profile or rank table");return;
    }
    snprintf(key,sizeof(key),"%d",rank);row=find_row(table,key);metadata=find_row(table,"maxrank");
    if(!row || !metadata || !integer(row[2],&minimum) || total<minimum ||
       !integer(metadata[3],&version)) {
        Scr_Error("setRankExperience: invalid rank threshold/version");return;
    }
    values[0]=(uint32_t)rank+1;values[1]=(uint32_t)(total-minimum);values[2]=(uint32_t)version;
    for(i=0;i<3;++i) {
        codol_structured_path_t path={names[i],0};
        if(!CODOL_ResolveStructuredField(def,&path,1,&fields[i]) || fields[i].type.kind!=0) {
            Scr_Error("setRankExperience: rank fields must be secure integers");return;
        }
    }
    copy=malloc(CODOL_STATS_SIZE);
    if(!copy) {Scr_Error("setRankExperience: allocation failed");return;}
    memcpy(copy,blob,CODOL_STATS_SIZE);
    for(i=0;i<3;++i) {
        if(!CODOL_StructuredWriteScalar(&def->layout,0,fields[i].logical_index,copy+4,capacity,values[i])) {
            free(copy);Scr_Error("setRankExperience: rank field is outside profile storage");return;
        }
    }
    /* Check the normalized record through the same recovered read contract
     * before committing any part of the live session profile. */
    if(!CODOL_ProfileExperience(copy,CODOL_STATS_SIZE,schema,table,&oldrank,&oldtotal) ||
       oldrank!=rank || oldtotal!=total) {
        free(copy);Scr_Error("setRankExperience: normalized rank failed validation");return;
    }
    crc=(uint32_t)crc32(0,copy+4,CODOL_STATS_SIZE-4);
    for(i=0;i<4;++i)copy[i]=(uint8_t)(crc>>(8*i));
    session=CODOL_ClientSecureProfileWritable(ref.entnum);
    if(!session) {free(copy);Scr_Error("setRankExperience: no writable secure session");return;}
    memcpy(session,copy,CODOL_STATS_SIZE);free(copy);
}
#endif
