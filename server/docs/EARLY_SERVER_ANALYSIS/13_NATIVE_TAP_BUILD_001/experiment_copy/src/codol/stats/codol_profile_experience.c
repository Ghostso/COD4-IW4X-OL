#include "codol_profile.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
static int number(const char *s,int *out)
{
    char *end;long value;
    if(!s || !*s)return 0;
    errno=0;value=strtol(s,&end,10);
    if(errno==ERANGE || end==s || *end || value<0 || value>INT_MAX)return 0;
    *out=(int)value;return 1;
}
static const char **row(const codol_engine_table_t *table,const char *key)
{
    const char **found=NULL;int i;
    for(i=0;i<table->rowCount;++i) {
        const char **r=table->values+(size_t)i*table->columnCount;
        if(r[0] && !strcmp(r[0],key)){if(found)return NULL;found=r;}
    }
    return found;
}
int CODOL_RankForExperience(const codol_engine_table_t *table,int experience,int *rank_out)
{
    const char **metadata;int maximum,i,previous=0,result=0;
    if(!rank_out || experience<0 || !table || !table->values || table->rowCount<=0 || table->columnCount<8)return 0;
    metadata=row(table,"maxrank");
    if(!metadata || !number(metadata[1],&maximum) || maximum>=table->rowCount)return 0;
    for(i=0;i<=maximum;++i) {
        char key[16];const char **r;int minimum,next;
        snprintf(key,sizeof(key),"%d",i);r=row(table,key);
        if(!r || !number(r[2],&minimum) || !number(r[7],&next) || minimum!=previous || next<=minimum)return 0;
        if(experience>=minimum)result=i;
        previous=next;
    }
    *rank_out=result;return 1;
}
int CODOL_ProfileExperience(const uint8_t *profile,size_t size,const codol_structured_schema_t *schema,
    const codol_engine_table_t *table,int *rank_out,int *experience_out)
{
    const char *names[]={"rank","experience","rankVersion"};int values[3],i,rank,minimum,next,version,total;
    const codol_structured_definition_t *def;const uint8_t *record;size_t capacity;
    const char **rank_row,**metadata;char key[16];
    if(!rank_out || !experience_out || !table || !table->values || table->rowCount<=0 || table->columnCount<8 ||
       !CODOL_ProfileRecord(profile,size,schema,&def,&record,&capacity))return 0;
    for(i=0;i<3;++i) {
        codol_structured_path_t path={names[i],0};codol_structured_field_t field;uint32_t value;
        if(!CODOL_ResolveStructuredField(def,&path,1,&field) || field.type.kind!=0 ||
           !CODOL_StructuredReadScalar(&def->layout,0,field.logical_index,record,capacity,&value) || value>INT_MAX)return 0;
        values[i]=(int)value;
    }
    rank=values[0]>0 ? values[0]-1 : 0;
    snprintf(key,sizeof(key),"%d",rank);rank_row=row(table,key);metadata=row(table,"maxrank");
    if(!rank_row || !metadata || !number(rank_row[2],&minimum) ||
       !number(rank_row[7],&next) || next<=minimum || !number(metadata[3],&version))return 0;
    /* C1 0x58efa7..0x58efd4: equal versions bypass the stale-version clamp;
     * with mismatched versions equality at the rank span also bypasses it. */
    if(values[2]!=version && values[1]>next-minimum)total=next-1;
    else {if(values[1]>INT_MAX-minimum)return 0;total=minimum+values[1];}
    *rank_out=rank;*experience_out=total;return 1;
}
