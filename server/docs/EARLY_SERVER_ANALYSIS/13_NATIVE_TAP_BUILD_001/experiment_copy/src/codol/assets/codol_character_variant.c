#include "codol_character_variant.h"
#include <string.h>
static unsigned lower(unsigned c){return c>='A' && c<='Z' ? c+32:c;}
static int same_fold(const char *a,const char *b)
{
    while(*a && lower((unsigned char)*a)==lower((unsigned char)*b)){++a;++b;}
    return lower((unsigned char)*a)==lower((unsigned char)*b);
}
int CODOL_CharacterVariant(const codol_engine_table_t *table,const char *item,const char *kind,
    unsigned gender,unsigned faction,const char *camo,const char *skin,unsigned *row,const char **value)
{
    static const char *factions[]={"tf","sc","zm"};
    int r,best=-1,selected=-1; char g=gender ? 'f':'m';
    if(!table || table->rowCount<0 || table->columnCount<2 ||
       (table->rowCount && !table->values) || !item || !*item || !kind || !*kind ||
       gender>1 || faction>2 || !camo || strlen(camo)!=3 || !skin || !row || !value) return -1;
    /* StringTable_LookupRowNum at 61ed00 finds the last case-insensitive item
     * match. 729090 then walks backward within that exact-name group. */
    for(r=table->rowCount-1;r>=0;--r) {
        const char *name=table->values[(size_t)r*table->columnCount];
        if(!name) return -1;
        if(same_fold(name,item)) break;
    }
    for(;r>=0;--r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        const char *key; int score;
        if(!cells[0]) return -1;
        if(strcmp(cells[0],item)) break;
        if(!cells[1]) return -1;
        if(strcmp(cells[1],kind)) continue;
        /* Not every character item supplies geometry: pat.csv contains
         * three-column material rows. Only a matching model/variant row
         * needs the selector and result columns; a different row kind is
         * a valid absence, not a malformed outfit. */
        if(table->columnCount<4) return -1;
        key=cells[2];
        if(!key || strlen(key)<8 || !cells[3]) return -1;
        if(key[0]==g) score=-1;
        else if(key[0]=='s') score=-2;
        else continue;
        if(!memcmp(key+2,factions[faction],2)) score+=2;
        else if(!memcmp(key+2,"ss",2)) ++score;
        else continue;
        if(!memcmp(key+5,camo,3)) score+=2;
        else if(!memcmp(key+5,"sss",3)) ++score;
        else continue;
        if(!strcmp(kind,"model") && strstr(cells[3],skin)) score+=100;
        if(score>best){best=score;selected=r;}
    }
    if(selected<0) return 0;
    *row=(unsigned)selected;*value=table->values[(size_t)selected*table->columnCount+3];return 1;
}
