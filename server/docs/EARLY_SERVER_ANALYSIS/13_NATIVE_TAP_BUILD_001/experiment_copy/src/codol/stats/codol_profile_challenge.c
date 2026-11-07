#include "codol_profile.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <math.h>
static int decimal(const char *s,int *out)
{
    char *end;long n;
    if(!s || !*s)return 0;
    errno=0;n=strtol(s,&end,10);
    if(errno==ERANGE || *end || end==s || n<0 || n>INT_MAX)return 0;
    *out=(int)n;return 1;
}
int CODOL_ProfileChallengeState(const uint8_t *profile,size_t size,const codol_structured_schema_t *schema,
    const codol_engine_table_t *table,const char *challenge,int *out)
{
    const char **row=NULL;const codol_structured_definition_t *def;const uint8_t *record;
    size_t capacity;codol_structured_path_t path[2]={{"challenges",0},{NULL,0}};
    codol_structured_field_t field;uint32_t bits;float progress;int r,id,previous=0,stage=1,col;
    if(!table || !table->values || table->rowCount<0 || table->columnCount<23 ||
       !challenge || !*challenge || !out)return 0;
    for(r=0;r<table->rowCount;++r) {
        const char **candidate=table->values+(size_t)r*table->columnCount;
        if(candidate[0] && !strcmp(candidate[0],challenge)) {
            if(row)return 0;row=candidate;
        }
    }
    if(!row || !decimal(row[4],&id) || id>=1000)return 0;
    path[1].index=id;
    if(!CODOL_ProfileRecord(profile,size,schema,&def,&record,&capacity) ||
       !CODOL_ResolveStructuredField(def,path,2,&field) || field.type.kind!=8 ||
       !CODOL_StructuredReadScalar(&def->layout,8,field.logical_index,record,capacity,&bits))return 0;
    memcpy(&progress,&bits,4);if(!isfinite(progress) || progress<0)return 0;
    for(col=6;col<24;col+=2) {
        int target;
        if(!row[col])return 0;
        if(!*row[col] || !strcmp(row[col],"0"))break;
        if(!decimal(row[col],&target) || target<=previous)return 0;
        previous=target;if((double)progress>=target)++stage;
    }
    if(!previous)return 0;
    *out=stage;return 1;
}
