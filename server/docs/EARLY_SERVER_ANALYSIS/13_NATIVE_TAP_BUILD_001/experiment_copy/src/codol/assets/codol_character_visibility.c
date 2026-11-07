#include "codol_character_variant.h"
#include <string.h>
static unsigned lower(unsigned c){return c>='A' && c<='Z' ? c+32:c;}
static int equal(const char *a,const char *b)
{
    while(*a && lower((unsigned char)*a)==lower((unsigned char)*b)){++a;++b;}
    return lower((unsigned char)*a)==lower((unsigned char)*b);
}
int CODOL_CharacterSlot7Allowed(const codol_engine_table_t *parts,const char *item,int *allowed)
{
    size_t offset;int r;
    if(!parts || !item || !allowed || parts->rowCount<0 || parts->columnCount<4 ||
       (parts->rowCount && !parts->values))return 0;
    offset=strlen(item);if(offset>SIZE_MAX-6)return 0;offset+=6;
    for(r=parts->rowCount-1;r>=0;--r) {
        const char *const *cells=parts->values+(size_t)r*parts->columnCount;
        const char *model;unsigned c;
        if(!cells[0])return 0;if(!equal(cells[0],item))continue;
        model=cells[3];if(!model)return 0;
        if(strlen(model)<offset){*allowed=0;return 1;}
        /* Equality deliberately includes the terminator: C1 tests length <
         * offset, then treats a NUL at offset as a non-digit. */
        c=(unsigned char)model[offset];*allowed=c<'0' || c>'9';return 1;
    }
    *allowed=0;return 1;
}
