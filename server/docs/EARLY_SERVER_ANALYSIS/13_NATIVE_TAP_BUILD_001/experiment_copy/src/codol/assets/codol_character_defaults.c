#include "codol_character_variant.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>
static unsigned lower(unsigned c){return c>='A' && c<='Z' ? c+32:c;}
static int equal(const char *a,const char *b)
{
    while(*a && lower((unsigned char)*a)==lower((unsigned char)*b)){++a;++b;}
    return lower((unsigned char)*a)==lower((unsigned char)*b);
}
static int find(const codol_engine_table_t *table,unsigned col,const char *key)
{
    int r;
    for(r=table->rowCount-1;r>=0;--r) {
        const char *value=table->values[(size_t)r*table->columnCount+col];
        if(!value)return -2;
        if(equal(value,key))return r;
    }
    return -1;
}
int CODOL_ApplyCharacterDefaults(const codol_engine_table_t *market,
    const codol_engine_table_t *characters,uint16_t character_item,uint16_t slots[18])
{
    codol_character_item_t identity;uint16_t next[18];int row,status;unsigned i;
    if(!slots || !market || !characters || market->columnCount<4 || market->rowCount<0 ||
       characters->columnCount<21 || characters->rowCount<0 ||
       (market->rowCount && !market->values) || (characters->rowCount && !characters->values))return 0;
    status=CODOL_CharacterItem(market,character_item,&identity);
    if(status<0)return 0;if(!status)return 1;
    row=find(characters,0,identity.name);if(row==-2)return 0;if(row<0)return 1;
    memcpy(next,slots,sizeof(next));
    for(i=0;i<18;++i) {
        const char *name,*id;char *end;long value;int item_row;
        if(next[i])continue;
        name=characters->values[(size_t)row*characters->columnCount+3+i];
        if(!name)return 0;if(!*name)continue;
        item_row=find(market,1,name);if(item_row==-2)return 0;if(item_row<0)continue;
        id=market->values[(size_t)item_row*market->columnCount];if(!id)return 0;
        errno=0;value=strtol(id,&end,10);
        /* Retail uses atoi; preserve its numeric-prefix behavior, but bound
         * results before storing a profile-sized item ID. */
        if(errno==ERANGE || value>65535)return 0;
        if(end!=id && value>0)next[i]=(uint16_t)value;
    }
    memcpy(slots,next,sizeof(next));return 1;
}
int CODOL_ChestRigSelector(unsigned weapon_class,unsigned *selector)
{
    static const unsigned mapping[]={0,4,2,1,3};
    if(!selector || weapon_class>=5)return 0;
    *selector=mapping[weapon_class];return 1;
}
int CODOL_ApplyCharacterChestRig(const codol_engine_table_t *market,
    const codol_engine_table_t *rigs,unsigned selector,uint16_t slots[18])
{
    codol_character_item_t source;uint16_t selected;int r,status;
    if(!slots || !rigs || rigs->rowCount<0 || rigs->columnCount<3 ||
       selector>=(unsigned)rigs->columnCount-2 || (rigs->rowCount && !rigs->values))return 0;
    if(!slots[5] || slots[5]>=32768)return 1;
    status=CODOL_CharacterItem(market,slots[5],&source);if(status<0)return 0;
    if(!status)return 1;
    selected=slots[15];
    for(r=0;r<rigs->rowCount;++r) {
        const char *const *cells=rigs->values+(size_t)r*rigs->columnCount;
        const char *id;int item_row;long n;char *end;
        if(!cells[0] || !cells[2+selector])return 0;
        if(strcmp(cells[0],source.name) || strcmp(cells[2+selector],"1"))continue;
        if(!cells[1])return 0;
        item_row=find(market,1,cells[1]);if(item_row==-2)return 0;
        if(item_row<0){selected=0;continue;}
        id=market->values[(size_t)item_row*market->columnCount];if(!id)return 0;
        errno=0;n=strtol(id,&end,10);
        if(errno==ERANGE || n<0 || n>65535)return 0;
        selected=end==id ? 0:(uint16_t)n;
    }
    slots[15]=selected;return 1;
}
