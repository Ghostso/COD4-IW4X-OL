#include "codol_profile.h"
#include "codol_unlock_rules.h"
#include <string.h>
typedef struct {
    const uint8_t *profile;size_t size;const codol_structured_schema_t *schema;
    const codol_engine_table_t *ranks,*challenges;
} context_t;
static int equal(const char *a,const char *b)
{
    for(;;++a,++b) {
        unsigned x=(unsigned char)*a,y=(unsigned char)*b;
        if(x>='A' && x<='Z')x+='a'-'A';if(y>='A' && y<='Z')y+='a'-'A';
        if(x!=y)return 0;if(!x)return 1;
    }
}
static int read_value(void *opaque,const char *group,const char *key,int *out)
{
    context_t *c=opaque;
    if(!strcmp(group,"experienceRank")) {
        int stored,total;
        return CODOL_ProfileExperience(c->profile,c->size,c->schema,c->ranks,&stored,&total) &&
               CODOL_RankForExperience(c->ranks,total,out);
    }
    if(!strcmp(group,"challengeState"))
        return CODOL_ProfileChallengeState(c->profile,c->size,c->schema,c->challenges,key,out);
    /* No CoDOL title/icon equivalent is established. Keep it unknown; the
     * evaluator can still prove true when ordinary requirements all pass. */
    return 0;
}
int CODOL_ProfileItemUnlocked(const uint8_t *profile,size_t size,const codol_structured_schema_t *schema,
    const codol_engine_table_t *unlocks,const codol_engine_table_t *ranks,
    const codol_engine_table_t *challenges,const char *item,int *unlocked)
{
    context_t c={profile,size,schema,ranks,challenges};
    const char **found=NULL;int i;
    const codol_structured_definition_t *def;const uint8_t *record;size_t capacity;
    if(!unlocked || !item || !*item || !unlocks || !unlocks->values ||
       unlocks->rowCount<=0 || unlocks->columnCount<4 ||
       !CODOL_ProfileRecord(profile,size,schema,&def,&record,&capacity))return 0;
    for(i=0;i<unlocks->rowCount;++i) {
        const char **row=unlocks->values+(size_t)i*unlocks->columnCount;
        if(row[0] && equal(row[0],item)) {if(found)return 0;found=row;}
    }
    if(!found){*unlocked=1;return 1;}
    return CODOL_EvaluateUnlockRule(found[0],found[1],found[2],found[3],read_value,&c,unlocked);
}
