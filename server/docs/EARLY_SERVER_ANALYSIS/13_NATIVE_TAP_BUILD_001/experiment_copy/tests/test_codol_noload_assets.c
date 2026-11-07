/* Measured C1 asset families with no loader accept directory-only records. */
#include "codol_load_blocks.h"
#include <assert.h>
#include <string.h>

/* Unused by this focused path; codol_load_blocks.c also exports XModel replay. */
int CODOL_ReadXModelSkeleton(const codol_asset_t *asset,codol_xmodel_skeleton_t *out)
{ (void)asset; (void)out; return 0; }
void CODOL_FreeXModelSkeleton(codol_xmodel_skeleton_t *model) { (void)model; }
int CODOL_ReadXModelExtent(const codol_asset_t *asset,size_t *size)
{ (void)asset; (void)size; return 0; }

static void put32(uint8_t *p,uint32_t value)
{
    unsigned i;
    for(i=0;i<4;++i) p[i]=(uint8_t)(value>>(8*i));
}

static void initialize(uint8_t data[73],codol_zone_t *zone,codol_load_blocks_t *stream)
{
    uint32_t capacities[8]={0};
    memset(data,0,73);
    put32(data+60,32);             /* asset body begins at byte 72 */
    put32(data+64,UINT32_MAX);     /* inline directory header */
    zone->data=data;
    zone->size=72;
    zone->table_offset=56;
    zone->asset_count=1;
    assert(CODOL_InitLoadBlocks(stream,data,72,capacities,3));
    stream->source_position=72;
}

int main(void)
{
    static const unsigned no_load_types[]={23,29,32,33,34,35};
    uint8_t data[73];
    codol_zone_t zone;
    codol_load_blocks_t stream,saved;
    unsigned i;

    for(i=0;i<sizeof(no_load_types)/sizeof(no_load_types[0]);++i) {
        initialize(data,&zone,&stream);
        put32(data+56,no_load_types[i]);
        saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(!memcmp(&saved,&stream,sizeof(stream)));
        CODOL_FreeLoadBlocks(&stream);
    }

    initialize(data,&zone,&stream);
    put32(data+56,23); put32(data+68,1);
    zone.size=73; stream.source_size=73;
    saved=stream;
    assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
    assert(!memcmp(&saved,&stream,sizeof(stream)));
    CODOL_FreeLoadBlocks(&stream);

    initialize(data,&zone,&stream);
    put32(data+56,44);
    saved=stream;
    assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==0);
    assert(!memcmp(&saved,&stream,sizeof(stream)));
    CODOL_FreeLoadBlocks(&stream);
    return 0;
}
