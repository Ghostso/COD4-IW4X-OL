#include "codol_physics.h"
#include "codol_asset_stream.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static uint32_t read32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static const char *pooled_string(const codol_model_block_t blocks[8],uint32_t ref)
{
    size_t offset; const uint8_t *p;
    if (!ref || ((ref-1)>>28)!=3) return NULL;
    offset=(ref-1)&0xfffffff;
    if (!blocks[3].data || blocks[3].size>CODOL_ASSET_LIMIT || offset>=blocks[3].size) return NULL;
    p=blocks[3].data+offset;
    return memchr(p,0,blocks[3].size-offset) ? (const char *)p : NULL;
}
static const uint8_t *pooled_planes(const codol_model_block_t blocks[8],uint32_t ref,uint32_t count)
{
    size_t offset;
    if (!ref || ((ref-1)>>28)!=3) return NULL;
    offset=(ref-1)&0xfffffff;
    if (!blocks[3].data || blocks[3].size>CODOL_ASSET_LIMIT ||
        offset>blocks[3].size || count>(blocks[3].size-offset)/20) return NULL;
    return blocks[3].data+offset;
}
void CODOL_FreePhysicsMap(codol_physics_map_t *map)
{
    uint32_t i;
    if (!map) return;
    for (i=0;i<map->count;++i) free(map->geometries[i].side_planes);
    free(map->geometries); memset(map,0,sizeof(*map));
}
int CODOL_ReadPhysicsMap(const codol_mounted_model_physics_t *source,codol_physics_map_t *out)
{
    codol_physics_map_t result={0};
    const uint8_t *b,*records; size_t extent=0,p=72; uint32_t ref,i,j;
    if (!source || !out || source->asset.type!=1 ||
        !CODOL_AdvancePhysicsMapStream(source->asset.data,source->asset.size,&extent) ||
        extent!=source->asset.size) return 0;
    b=source->asset.data; ref=read32(b); result.header=b;
    if (ref==UINT32_MAX) { result.name=(const char *)b+p; p+=strlen(result.name)+1; }
    else result.name=pooled_string(source->blocks,ref);
    if (!result.name || !*result.name || *result.name==',') return 0;
    /* C1 0x658be0 passes header+12 to 0x658b50. That consumer uses
     * +0 for the center, +12 for moments and +24 for products; 0x658030
     * places the latter two into the diagonal and off-diagonal ODE tensor. */
    for (i=0;i<9;++i) {
        uint32_t bits=read32(b+12+4*i); float value;
        memcpy(&value,&bits,4); if (!isfinite(value)) return 0;
        if (i<3) result.center_of_mass[i]=value;
        else if (i<6) result.moments_of_inertia[i-3]=value;
        else result.products_of_inertia[i-6]=value;
    }
    result.count=read32(b+4);
    if (result.count && !read32(b+8)) return 0;
    if (result.count>CODOL_ASSET_LIMIT/sizeof(*result.geometries)) return 0;
    records=b+p; p+=(size_t)result.count*68;
    if (result.count) {
        result.geometries=calloc(result.count,sizeof(*result.geometries));
        if (!result.geometries) return 0;
    }
    for (i=0;i<result.count;++i) {
        codol_physics_geometry_t *g=result.geometries+i;
        g->record=records+68*i;
        if (!read32(g->record)) continue;
        g->brush=b+p; p+=68;
        g->side_count=g->brush[24]|(uint32_t)g->brush[25]<<8;
        if (read32(g->brush+28)) {
            g->sides=b+p; p+=(size_t)g->side_count*8;
            if (g->side_count) {
                g->side_planes=calloc(g->side_count,sizeof(*g->side_planes));
                if (!g->side_planes) goto fail;
            }
            for (j=0;j<g->side_count;++j) {
                ref=read32(g->sides+8*j);
                if (ref==UINT32_MAX) { g->side_planes[j]=b+p; p+=20; }
                else if (ref && !(g->side_planes[j]=pooled_planes(source->blocks,ref,1))) goto fail;
            }
        }
        g->adjacency_size=read32(g->brush+60);
        if (read32(g->brush+32)) { g->adjacency=b+p; p+=g->adjacency_size; }
        ref=read32(g->brush+64);
        if (ref==UINT32_MAX) { g->planes=b+p; p+=(size_t)g->side_count*20; }
        else if (ref && !(g->planes=pooled_planes(source->blocks,ref,g->side_count))) goto fail;
    }
    if (p!=extent) goto fail;
    CODOL_FreePhysicsMap(out); *out=result; return 1;
fail:
    CODOL_FreePhysicsMap(&result); return 0;
}
void CODOL_FreePhysicsPreset(codol_physics_preset_t *preset)
{
    if (!preset) return;
    free(preset->storage); memset(preset,0,sizeof(*preset));
}
int CODOL_ReadPhysicsPreset(const codol_mounted_model_physics_t *source,codol_physics_preset_t *out)
{
    static const unsigned offsets[7]={8,12,16,20,24,32,36};
    codol_physics_preset_t result={0}; float values[7];
    const uint8_t *b; const char *name,*sound=NULL;
    size_t extent=0,p=68,name_size,sound_size=0; uint32_t ref; unsigned i;
    if (!source || !out || source->asset.type!=0 ||
        !CODOL_AdvancePhysicsPresetStream(source->asset.data,source->asset.size,&extent) ||
        extent!=source->asset.size) return 0;
    b=source->asset.data; ref=read32(b);
    if (ref==UINT32_MAX) { name=(const char *)b+p; p+=strlen(name)+1; }
    else name=pooled_string(source->blocks,ref);
    if (!name || !*name || *name==',') return 0;
    ref=read32(b+28);
    if (ref==UINT32_MAX) sound=(const char *)b+p;
    else if (ref && !(sound=pooled_string(source->blocks,ref))) return 0;
    for (i=0;i<7;++i) {
        uint32_t bits=read32(b+offsets[i]); memcpy(values+i,&bits,4);
        if (!isfinite(values[i])) return 0;
    }
    name_size=strlen(name)+1; if (sound) sound_size=strlen(sound)+1;
    if (name_size>CODOL_ASSET_LIMIT || sound_size>CODOL_ASSET_LIMIT-name_size) return 0;
    result.storage=malloc(name_size+sound_size); if (!result.storage) return 0;
    memcpy(result.storage,name,name_size); result.name=result.storage;
    if (sound) { memcpy(result.storage+name_size,sound,sound_size); result.sound_prefix=result.storage+name_size; }
    result.type=read32(b+4); result.mass=values[0]; result.bounce=values[1]; result.friction=values[2];
    result.bullet_force_scale=values[3]; result.explosive_force_scale=values[4];
    result.pieces_spread_fraction=values[5]; result.pieces_upward_velocity=values[6];
    memcpy(result.extended,b+40,sizeof(result.extended)); *out=result; return 1;
}
