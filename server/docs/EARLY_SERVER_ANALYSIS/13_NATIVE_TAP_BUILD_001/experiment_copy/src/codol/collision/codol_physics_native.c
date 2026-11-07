#include "codol_physics_native.h"
#include "cm_local.h"
#include <stddef.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(struct PhysPreset)==44,"IW3 physics preset ABI");
_Static_assert(offsetof(struct PhysPreset,mass)==8,"IW3 preset mass");
_Static_assert(offsetof(struct PhysPreset,sndAliasPrefix)==28,"IW3 preset sound");
_Static_assert(offsetof(struct PhysPreset,tempDefaultToCylinder)==40,"IW3 cylinder flag");
_Static_assert(sizeof(PhysGeomList_t)==44,"IW3 physics map ABI");
_Static_assert(sizeof(PhysGeomInfo_t)==68,"IW3 physics geometry ABI");
_Static_assert(offsetof(PhysGeomInfo_t,orientation)==8,"IW3 physics orientation");
_Static_assert(offsetof(PhysGeomInfo_t,offset)==44,"IW3 physics offset");
_Static_assert(offsetof(PhysGeomInfo_t,halfLengths)==56,"IW3 physics dimensions");
_Static_assert(sizeof(BrushWrapper_t)==80,"IW3 brush wrapper ABI");
_Static_assert(offsetof(BrushWrapper_t,planes)==76,"IW3 brush wrapper planes");
_Static_assert(sizeof(cbrushside_t)==12,"IW3 brush side ABI");

static uint32_t read32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int floats(const uint8_t *p,float *out,unsigned count)
{
    unsigned i;
    for (i=0;i<count;++i) {
        uint32_t bits=read32(p+4*i); memcpy(out+i,&bits,4);
        if (!isfinite(out[i])) return 0;
    }
    return 1;
}
void CODOL_FreeNativePhysicsMap(codol_native_physics_map_t *out)
{
    unsigned i;
    if (!out) return;
    if (out->brush_storage)
        for (i=0;i<out->map.count;++i) free(out->brush_storage[i]);
    free(out->brush_storage);
    free(out->map.geoms); free(out->name); memset(out,0,sizeof(*out));
}

static unsigned read16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static int plane(const uint8_t *p,cplane_t *d)
{
    unsigned j; float values[4],length=0;
    if (!p || !floats(p,values,4)) return 0;
    memcpy(d->normal,values,12); d->dist=values[3]; d->type=3;
    for (j=0;j<3;++j) {
        length+=values[j]*values[j];
        if (values[j]<0) d->signbits|=1u<<j;
        if (values[j]==1 && values[(j+1)%3]==0 && values[(j+2)%3]==0) d->type=j;
    }
    return fabsf(length-1)<=0.001f;
}

static int brush(const codol_physics_geometry_t *s,PhysGeomInfo_t *d,void **storage)
{
    const uint8_t *raw=s->brush;
    BrushWrapper_t *b; cplane_t *side_planes;
    float bounds[6]; unsigned j; size_t size;
    if (!raw || !floats(raw,bounds,6) || read16(raw+24)!=s->side_count ||
        read32(raw+60)!=s->adjacency_size ||
        (s->side_count && (!s->sides || !s->side_planes || !s->planes)) ||
        (s->adjacency_size && !s->adjacency)) return 0;
    size=sizeof(*b)+15+(size_t)s->side_count*(sizeof(cbrushside_t)+2*sizeof(cplane_t));
    if (size>CODOL_ASSET_LIMIT || s->adjacency_size>CODOL_ASSET_LIMIT-size) return 0;
    *storage=calloc(1,size+s->adjacency_size); if (!*storage) return 0;
    b=(BrushWrapper_t *)(((uintptr_t)*storage+15)&~(uintptr_t)15);
    d->brush=b;
    /* CoDOL stores midpoint/half-size, IW3 stores minima/maxima. The source
     * phys brush has no contents mask; ODE receives the shape directly. */
    for (j=0;j<3;++j) {
        if (bounds[j+3]<0) return 0;
        b->mins[j]=bounds[j]-bounds[j+3]; b->maxs[j]=bounds[j]+bounds[j+3];
        if (!isfinite(b->mins[j]) || !isfinite(b->maxs[j])) return 0;
    }
    b->numsides=s->side_count;
    b->sides=(cbrushside_t *)(b+1);
    b->planes=(cplane_t *)(b->sides+s->side_count);
    side_planes=b->planes+s->side_count;
    b->baseAdjacentSide=(char *)(side_planes+s->side_count);
    b->totalEdgeCount=s->adjacency_size;
    if (s->adjacency_size) memcpy(b->baseAdjacentSide,s->adjacency,s->adjacency_size);
    for (j=0;j<6;++j) {
        unsigned offset=raw[48+j],count=raw[54+j];
        if (count && (offset>s->adjacency_size || count>s->adjacency_size-offset)) return 0;
        memcpy(&b->axialMaterialNum[j/3][j%3],raw+36+2*j,2);
        b->firstAdjacentSideOffsets[j/3][j%3]=offset;
        b->edgeCount[j/3][j%3]=count;
    }
    for (j=0;j<s->side_count;++j) {
        const uint8_t *side=s->sides+8*j;
        unsigned offset=side[6],count=side[7];
        if (count && (offset>s->adjacency_size || count>s->adjacency_size-offset)) return 0;
        if (!plane(s->side_planes[j],side_planes+j) || !plane(s->planes+20*j,b->planes+j)) return 0;
        b->sides[j].plane=side_planes+j;
        b->sides[j].materialNum=read16(side+4);
        b->sides[j].firstAdjacentSideOffset=offset; b->sides[j].edgeCount=count;
    }
    return 1;
}
int CODOL_BuildNativePhysicsMap(const codol_physics_map_t *source,codol_native_physics_map_t *out)
{
    codol_native_physics_map_t result={0}; unsigned i,j; size_t name_size;
    if (!source || !out || !source->header || !source->name || !*source->name ||
        source->count>CODOL_ASSET_LIMIT/sizeof(PhysGeomInfo_t) ||
        (source->count && !source->geometries)) return 0;
    if (!floats(source->header+48,result.source_bounds,6)) return 0;
    for (i=0;i<3;++i) {
        if (result.source_bounds[i+3]<0 || !isfinite(source->center_of_mass[i]) ||
            !isfinite(source->moments_of_inertia[i]) || !isfinite(source->products_of_inertia[i])) return 0;
        result.map.mass.centerOfMass[i]=source->center_of_mass[i];
        result.map.mass.momentsOfInertia[i]=source->moments_of_inertia[i];
        result.map.mass.productsOfInertia[i]=source->products_of_inertia[i];
    }
    name_size=strlen(source->name)+1; if (name_size>CODOL_ASSET_LIMIT) return 0;
    result.name=malloc(name_size); if (!result.name) return 0;
    memcpy(result.name,source->name,name_size); result.map.count=source->count;
    if (result.map.count) {
        result.map.geoms=calloc(result.map.count,sizeof(*result.map.geoms));
        result.brush_storage=calloc(result.map.count,sizeof(*result.brush_storage));
        if (!result.map.geoms || !result.brush_storage) goto fail;
    }
    for (i=0;i<result.map.count;++i) {
        const codol_physics_geometry_t *s=source->geometries+i;
        PhysGeomInfo_t *d=result.map.geoms+i; uint32_t type; float orientation[9];
        if (!s->record || (!!s->brush != !!read32(s->record))) goto fail;
        type=read32(s->record+4);
        if (s->brush) {
            if (type!=0 || !brush(s,d,result.brush_storage+i)) goto fail;
            d->type=0;
        } else {
            if (type!=1 && type!=5) goto fail;
            d->type=type==1 ? 1 : 4;
        }
        if (!floats(s->record+8,orientation,9) ||
            !floats(s->record+44,d->offset,3) || !floats(s->record+56,d->halfLengths,3)) goto fail;
        memcpy(d->orientation,orientation,sizeof(orientation));
        for (j=0;j<3;++j) if (d->halfLengths[j]<0) goto fail;
    }
    CODOL_FreeNativePhysicsMap(out); *out=result; return 1;
fail:
    CODOL_FreeNativePhysicsMap(&result); return 0;
}

void CODOL_FreeNativePhysicsPreset(codol_native_physics_preset_t *preset)
{
    if (!preset) return;
    CODOL_FreePhysicsPreset(&preset->source);
    memset(preset,0,sizeof(*preset));
}
int CODOL_BuildNativePhysicsPreset(const codol_mounted_model_physics_t *source,codol_native_physics_preset_t *out)
{
    codol_native_physics_preset_t result={0};
    if (!out || !CODOL_ReadPhysicsPreset(source,&result.source)) return 0;
    result.preset.name=result.source.name;
    memcpy(&result.preset.type,&result.source.type,4);
    result.preset.mass=result.source.mass;
    result.preset.bounce=result.source.bounce;
    result.preset.friction=result.source.friction;
    result.preset.bulletForceScale=result.source.bullet_force_scale;
    result.preset.explosiveForceScale=result.source.explosive_force_scale;
    result.preset.sndAliasPrefix=result.source.sound_prefix;
    result.preset.piecesSpreadFraction=result.source.pieces_spread_fraction;
    result.preset.piecesUpwardVelocity=result.source.pieces_upward_velocity;
    /* C1 0x4e1b10 loads DynEntDef.physPreset, then tests byte +0x40.
     * Nonzero selects 0x658cc0 (cylinder); zero selects 0x658a40 (box).
     * The test accepts any nonzero byte, not only canonical bool 1. */
    result.preset.tempDefaultToCylinder=result.source.extended[24]!=0;
    *out=result;
    return 1;
}
