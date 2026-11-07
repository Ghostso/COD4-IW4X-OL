#include "codol_xmodel.h"
#include "codol_asset_stream.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static float f32(const uint8_t *p)
{ uint32_t bits=u32(p); float v; memcpy(&v,&bits,4); return v; }
/* C1 accessors 0x643a40..0x643b77 establish these LOD fields. */
int CODOL_ReadXModelLods(const codol_asset_t *asset,codol_xmodel_lods_t *out)
{
    codol_xmodel_lods_t result={0};
    unsigned i;
    if (!asset || !out || asset->type!=4 || !asset->data || asset->size<360) return 0;
    result.first=asset->data[0x128]; result.count=asset->data[0x129];
    /* C1 0x64221c tests this signed byte before model collision tracing. */
    result.collision_lod=asset->data[0x12a];
    if (result.collision_lod>=128) result.collision_lod-=256;
    if (result.count>4 || result.first>result.count) return 0;
    for (i=0;i<4;++i) {
        const uint8_t *p=asset->data+0x48+56*i;
        codol_xmodel_lod_t *lod=result.lods+i;
        lod->distance=f32(p);
        lod->surface_count=(uint16_t)(p[4]|p[5]<<8);
        lod->surface_index=(uint16_t)(p[6]|p[7]<<8);
        lod->surfaces_reference=u32(p+8); lod->name_reference=u32(p+12);
        memcpy(lod->remaining,p+16,sizeof(lod->remaining));
        if (i>=result.first && i<result.count &&
            (!isfinite(lod->distance) || lod->distance<0)) return 0;
    }
    *out=result; return 1;
}
static int bounds(const uint8_t *p, float *mins, float *maxs, float *center)
{
    unsigned j;
    for (j=0;j<3;++j) {
        float mid=f32(p+4*j), half=f32(p+12+4*j);
        if (!isfinite(mid)||!isfinite(half)||half<0) return 0;
        mins[j]=mid-half; maxs[j]=mid+half;
        if (!isfinite(mins[j])||!isfinite(maxs[j])) return 0;
        if (center) center[j]=mid;
    }
    return 1;
}
void CODOL_FreeXModelBounds(codol_xmodel_bounds_t *m)
{
    if (!m) return;
    free(m->bones); memset(m,0,sizeof(*m));
}
int CODOL_ReadXModelBounds(const codol_asset_t *asset, codol_xmodel_bounds_t *out)
{
    codol_xmodel_collision_t collision={0};
    codol_xmodel_bounds_t result={0};
    const uint8_t *b;
    size_t p;
    unsigned i;
    if (!out || !CODOL_ReadXModelCollision(asset,&collision)) return 0;
    p=collision.consumed; CODOL_FreeXModelCollision(&collision); b=asset->data;
    result.radius=f32(b+0x13c);
    /* C1 0x635ce0 tests model+0x134 against a contents mask; 0x635d10
     * combines the same field across a DObj's model array. */
    result.contents=u32(b+0x134);
    /* C1 0x4374ba reads this byte for the "flags = %d" model diagnostic.
     * 0x15d is separately printed as loadOnDemandFlags, not model flags. */
    result.flags=b[0x12b];
    if (!isfinite(result.radius)||result.radius<0 ||
        !bounds(b+0x140,result.mins,result.maxs,NULL)) return 0;
    result.bone_count=b[4]; result.bone_info_reference=u32(b+0x138);
    if (result.bone_info_reference && result.bone_count) {
        if (result.bone_count>(asset->size-p)/28) return 0;
        result.bones=calloc(result.bone_count,sizeof(*result.bones));
        if (!result.bones) return 0;
        for (i=0;i<result.bone_count;++i) {
            codol_xmodel_bone_info_t *bone=result.bones+i;
            const uint8_t *raw=b+p+28*i;
            if (!bounds(raw,bone->bounds[0],bone->bounds[1],bone->offset)) goto fail;
            bone->radiusSquared=f32(raw+24);
            if (!isfinite(bone->radiusSquared)||bone->radiusSquared<0) goto fail;
        }
        p+=(size_t)result.bone_count*28;
    }
    result.physics_preset_reference=u32(b+0x160);
    result.physics_map_reference=u32(b+0x164);
    result.consumed=p; *out=result; return 1;
fail:
    CODOL_FreeXModelBounds(&result); return 0;
}
int CODOL_ReadXModelExtent(const codol_asset_t *asset, size_t *consumed)
{
    codol_xmodel_bounds_t result={0};
    size_t p;
    uint32_t preset,map;
    if (!consumed || !CODOL_ReadXModelBounds(asset,&result)) return 0;
    p=result.consumed; preset=result.physics_preset_reference; map=result.physics_map_reference;
    CODOL_FreeXModelBounds(&result);
    if (preset>=UINT32_MAX-1 && !CODOL_AdvancePhysicsPresetStream(asset->data,asset->size,&p)) return 0;
    if (map>=UINT32_MAX-1 && !CODOL_AdvancePhysicsMapStream(asset->data,asset->size,&p)) return 0;
    *consumed=p; return 1;
}
int CODOL_XModelInlinePhysicsAssets(const codol_asset_t *asset,codol_asset_t out[2])
{
    codol_asset_t result[2]={{0}}; codol_xmodel_bounds_t bounds={0};
    size_t extent,p,start; unsigned i;
    if (!out || !CODOL_ReadXModelExtent(asset,&extent) || !CODOL_ReadXModelBounds(asset,&bounds)) return 0;
    p=bounds.consumed; CODOL_FreeXModelBounds(&bounds);
    for (i=0;i<2;++i) if (u32(asset->data+0x160+4*i)>=UINT32_MAX-1) {
        start=p;
        if (!(i ? CODOL_AdvancePhysicsMapStream(asset->data,extent,&p) :
                  CODOL_AdvancePhysicsPresetStream(asset->data,extent,&p))) return 0;
        result[i]=(codol_asset_t){i,asset->data+start,p-start};
    }
    memcpy(out,result,sizeof(result)); return 1;
}
int CODOL_XModelInlineSurfaceAssets(const codol_asset_t *asset,codol_asset_t out[4])
{
    codol_asset_t result[4]={{0}};
    codol_xmodel_skeleton_t skeleton={0};
    size_t extent,p,materials;
    const uint8_t *b;
    unsigned i;
    if (!out || !CODOL_ReadXModelExtent(asset,&extent) || !CODOL_ReadXModelSkeleton(asset,&skeleton)) return 0;
    p=skeleton.consumed; CODOL_FreeXModelSkeleton(&skeleton); b=asset->data;
    if (u32(b+0x44)) {
        materials=p; p+=(size_t)b[6]*4;
        for (i=0;i<b[6];++i)
            if (u32(b+materials+4*i)>=UINT32_MAX-1 && !CODOL_AdvanceMaterialStream(b,extent,&p)) return 0;
    }
    for (i=0;i<4;++i) {
        const uint8_t *lod=b+0x48+56*i;
        if (u32(lod+8)>=UINT32_MAX-1) {
            size_t start=p;
            if (!CODOL_AdvanceModelSurfacesStream(b,extent,&p)) return 0;
            result[i]=(codol_asset_t){3,b+start,p-start};
        }
        if (u32(lod+12)==UINT32_MAX) {
            const uint8_t *end=memchr(b+p,0,extent-p);
            if (!end) return 0;
            p=(size_t)(end-b)+1;
        }
    }
    memcpy(out,result,sizeof(result)); return 1;
}
void CODOL_FreeXModelMaterials(codol_xmodel_materials_t *out)
{
    if (!out) return;
    free(out->materials); memset(out,0,sizeof(*out));
}
int CODOL_ReadXModelMaterials(const codol_asset_t *asset,codol_xmodel_materials_t *out)
{
    codol_xmodel_materials_t result={0}; codol_xmodel_skeleton_t skeleton={0};
    size_t extent,p,refs; unsigned i;
    if (!out || !CODOL_ReadXModelExtent(asset,&extent) || !CODOL_ReadXModelSkeleton(asset,&skeleton)) return 0;
    p=skeleton.consumed; CODOL_FreeXModelSkeleton(&skeleton);
    result.count=asset->data[6]; result.array_reference=u32(asset->data+0x44);
    if(result.count && !(result.materials=calloc(result.count,sizeof(*result.materials)))) return 0;
    if(result.array_reference) {
        refs=p;
        if(p>extent || result.count>(extent-p)/4) goto fail;
        p+=(size_t)result.count*4;
        for(i=0;i<result.count;++i) {
            codol_xmodel_material_t *slot=result.materials+i;
            slot->reference=u32(asset->data+refs+4*i);
            if(slot->reference>=UINT32_MAX-1) {
                size_t start=p;
                if(!CODOL_AdvanceMaterialStream(asset->data,extent,&p)) goto fail;
                slot->inline_asset=(codol_asset_t){5,asset->data+start,p-start};
            }
        }
    }
    result.consumed=p; *out=result; return 1;
fail:
    CODOL_FreeXModelMaterials(&result); return 0;
}
