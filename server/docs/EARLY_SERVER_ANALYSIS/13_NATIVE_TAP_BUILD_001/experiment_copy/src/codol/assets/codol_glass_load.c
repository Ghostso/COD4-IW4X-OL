/* GameWorldMp named glass groups retained by the C1 stream replay.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_glass_load.h"
#include <stdlib.h>
#include <string.h>

static uint32_t glass_word(const uint8_t *p)
{
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|
        ((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static int glass_extent(const uint8_t *base,size_t size,const void *pointer,size_t bytes)
{
    uintptr_t offset;
    if(!base || !pointer || (uintptr_t)pointer<(uintptr_t)base) return 0;
    offset=(uintptr_t)pointer-(uintptr_t)base;
    return offset<=size && bytes<=size-offset;
}
int CODOL_LoadGlassGroups(const codol_load_blocks_t *blocks,const codol_asset_t *world,
                         codol_glass_groups_t *out)
{
    const codol_glass_span_t *marker=NULL;
    codol_glass_group_view_t *groups=NULL;
    uint32_t piece_count=0,group_count=0;
    size_t i,j,seen=0;
    int ok=0;
    if(!blocks || !world || !out || world->type!=18 || !world->data || world->size<84 ||
       !glass_extent(blocks->source,blocks->source_size,world->data,world->size) ||
       blocks->glass_record_count>blocks->glass_record_capacity ||
       (blocks->glass_record_count && !blocks->glass_records)) return 0;
    for(i=0;i<blocks->glass_record_count;++i) {
        const codol_glass_span_t *row=blocks->glass_records+i;
        if(row->world!=world->data || row->group!=UINT32_MAX) continue;
        if(marker) return 0;
        marker=row;
    }
    /* Missing replay metadata cannot stand in for a known empty world. */
    if(!marker || (!!marker->glass!=!!glass_word(world->data+80))) return 0;
    if(marker->glass) {
        if(!glass_extent(world->data,world->size,marker->glass,128)) return 0;
        piece_count=glass_word(marker->glass+4);
        group_count=glass_word(marker->glass+12);
        if((piece_count && !glass_word(marker->glass)) ||
           (group_count && !glass_word(marker->glass+16)) ||
           group_count>world->size/12 || group_count>SIZE_MAX/sizeof(*groups)) return 0;
    }
    groups=group_count?calloc(group_count,sizeof(*groups)):NULL;
    if(group_count && !groups) return 0;
    for(i=0;i<blocks->glass_record_count;++i) {
        const codol_glass_span_t *row=blocks->glass_records+i;
        const char *name;
        uint16_t *ids=NULL;
        if(row->world!=world->data || row->group==UINT32_MAX) continue;
        /* Preserve source order, including duplicate group names and IDs. */
        if(row->glass!=marker->glass || seen>=group_count || row->group!=seen) goto done;
        if(row->name_reference==UINT32_MAX) {
            size_t offset;
            name=row->inline_name;
            if(!glass_extent(world->data,world->size,name,1)) goto done;
            offset=(size_t)((uintptr_t)name-(uintptr_t)world->data);
            if(!memchr(name,0,world->size-offset)) goto done;
        } else {
            if(row->inline_name) goto done;
            name=CODOL_LoadBlockString(blocks,row->name_reference);
            if(!name) goto done;
        }
        if(row->count) {
            if(!glass_extent(world->data,world->size,row->ids,(size_t)row->count*2)) goto done;
            ids=malloc((size_t)row->count*sizeof(*ids));
            if(!ids) goto done;
        }
        groups[seen]=(codol_glass_group_view_t){name,ids,row->count};
        ++seen; /* Include this allocation in cleanup if an ID is invalid. */
        for(j=0;j<row->count;++j) {
            ids[j]=(uint16_t)((unsigned)row->ids[j*2]|((unsigned)row->ids[j*2+1]<<8));
            if(ids[j]>=piece_count) goto done;
        }
    }
    if(seen!=group_count) goto done;
    ok=CODOL_InstallGlassGroups(out,piece_count,groups,group_count);
done:
    for(i=0;i<seen;++i) free((void *)groups[i].pieces);
    free(groups);
    return ok;
}
