/* Two-pass StringTableCell stream, alpha0022/ffwriter/codol_ff.py.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_assets.h"
#include <stdlib.h>
#include <string.h>
static uint32_t read32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static const char *take_string(uint8_t *data, size_t size, size_t *position)
{
    const char *start = (char *)data + *position;
    const char *end = memchr(start, 0, size - *position);
    if (!end) return NULL;
    *position += (size_t)(end-start) + 1;
    return start;
}
const char *CODOL_StringTableName(const codol_asset_t *asset)
{
    if (!asset || !asset->data || asset->type != CODOL_ASSET_STRINGTABLE || asset->size < 17 ||
        read32(asset->data) != UINT32_MAX || !memchr(asset->data+16, 0, asset->size-16)) return NULL;
    return (const char *)asset->data+16;
}
void CODOL_FreeStringTable(codol_stringtable_t *t)
{
    if (t) { free(t->cells); free(t->storage); memset(t, 0, sizeof(*t)); }
}
uint32_t CODOL_StringTableHash(const char *text)
{
    const unsigned char *s=(const unsigned char *)text; uint32_t hash=0;
    if(!s) return 0;
    for(;*s;++s) {
        unsigned c=*s;
        if(c>='A' && c<='Z') c+='a'-'A';
        hash=hash*31+(c>=128 ? c-256 : c);
    }
    return hash;
}
int CODOL_ReadStringTable(const codol_asset_t *asset, codol_stringtable_t *out)
{
    codol_stringtable_t t = {0};
    size_t pos = 16, records, count, i;
    if (!asset || !out || !asset->data || asset->type != CODOL_ASSET_STRINGTABLE ||
        asset->size < 16 || asset->size > CODOL_ASSET_LIMIT) return 0;
    t.columns = read32(asset->data+4); t.rows = read32(asset->data+8);
    if (t.columns && t.rows > SIZE_MAX/t.columns) return 0;
    count = (size_t)t.columns*t.rows;
    if (count > (asset->size-16)/8 || count > CODOL_ASSET_LIMIT/sizeof(*t.cells)) return 0;
    t.storage = malloc(asset->size);
    if (!t.storage) return 0;
    memcpy(t.storage, asset->data, asset->size);
    t.name_reference = read32(t.storage); t.values_reference = read32(t.storage+12);
    if (t.name_reference == UINT32_MAX) {
        t.name = take_string(t.storage, asset->size, &pos);
        if (!t.name) goto fail;
    }
    if (count > (asset->size-pos)/8) goto fail;
    records = pos; pos += count*8;
    if (count && !(t.cells = calloc(count, sizeof(*t.cells)))) goto fail;
    for (i = 0; i < count; ++i) {
        codol_table_cell_t *cell = &t.cells[i];
        cell->reference = read32(t.storage+records+8*i);
        cell->hash = read32(t.storage+records+8*i+4);
        if (cell->reference == UINT32_MAX) {
            cell->text = take_string(t.storage, asset->size, &pos);
            if (!cell->text) goto fail;
            if (CODOL_StringTableHash(cell->text) != cell->hash) goto fail;
        } else if (cell->reference) ++t.unresolved;
    }
    if (pos != asset->size) goto fail;
    *out = t; return 1;
fail:
    CODOL_FreeStringTable(&t); return 0;
}
const codol_table_cell_t *CODOL_StringTableCell(const codol_stringtable_t *t, unsigned row, unsigned col)
{
    return t && t->cells && row < t->rows && col < t->columns ? &t->cells[(size_t)row*t->columns+col] : NULL;
}

/* Offline reference CSVs retain header rows and pad short rows with empty
 * cells. Quoted newlines and
 * doubled quotes remain cell content. All pointers belong to the result. */
int CODOL_ReadCSVStringTable(const char *data,size_t size,codol_stringtable_t *out)
{
    codol_stringtable_t t={0};const char **fields=NULL;size_t *ends=NULL;
    size_t p=0,w=0,n=0,rows=0,columns=0,row_start=0,i,j,begin,slots;
    if(!data || !out || !size || size>16*1024*1024 || memchr(data,0,size))return 0;
    slots=size<1048576 ? size+1 : 1048577;
    t.storage=malloc(size+2);fields=malloc(slots*sizeof(*fields));
    ends=malloc(slots*sizeof(*ends));
    if(!t.storage || !fields || !ends)goto fail;
    while(p<size) {
        int quoted=data[p]=='"',closed=!quoted;
        if(n>=1048576)goto fail;
        fields[n++]=(char *)t.storage+w;
        if(quoted)++p;
        while(p<size) {
            char c=data[p];
            if(quoted) {
                if(c=='"') {
                    ++p;
                    if(p<size && data[p]=='"'){t.storage[w++]='"';++p;continue;}
                    closed=1;break;
                }
            } else if(c==',' || c=='\r' || c=='\n')break;
            else if(c=='"')goto fail;
            t.storage[w++]=(uint8_t)c;++p;
        }
        if(!closed || (quoted && p<size && data[p]!=',' && data[p]!='\r' && data[p]!='\n'))goto fail;
        t.storage[w++]=0;
        if(p<size && data[p]==',') {
            ++p;
            if(p<size)continue;
            fields[n++]=(char *)t.storage+w;t.storage[w++]=0;
        }
        if(n-row_start>columns)columns=n-row_start;
        ends[rows++]=n;row_start=n;
        if(p<size && data[p]=='\r') {++p;if(p<size && data[p]=='\n')++p;}
        else if(p<size && data[p]=='\n')++p;
    }
    if(!rows || !columns || rows>1048576/columns)goto fail;
    t.storage[w]=0;
    t.cells=calloc(rows*columns,sizeof(*t.cells));if(!t.cells)goto fail;
    for(i=0,begin=0;i<rows;begin=ends[i++])
        for(j=0;j<columns;++j) {
            codol_table_cell_t *cell=t.cells+i*columns+j;
            cell->text=begin+j<ends[i] ? fields[begin+j] : (char *)t.storage+w;
            cell->hash=CODOL_StringTableHash(cell->text);
        }
    t.rows=(uint32_t)rows;t.columns=(uint32_t)columns;
    free(fields);free(ends);*out=t;return 1;
fail:
    free(fields);free(ends);CODOL_FreeStringTable(&t);return 0;
}
