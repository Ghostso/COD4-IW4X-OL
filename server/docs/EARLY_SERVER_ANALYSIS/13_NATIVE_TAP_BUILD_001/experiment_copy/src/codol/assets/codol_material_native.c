/* CPU material identity for IW4OL's existing dedicated/null renderer. */
#include "codol_material_native.h"
#include "codol_asset_stream.h"
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(Material_t)==80,"native material ABI");
_Static_assert(sizeof(MaterialInfo)==24,"native material info ABI");
_Static_assert(offsetof(MaterialInfo,surfaceTypeBits)==16,"native surface type bits");
_Static_assert(offsetof(Material_t,stateBitsEntry)==24,"native technique entries");
_Static_assert(offsetof(Material_t,techniqueSet)==64,"native technique pointer");

void CODOL_FreeNativeMaterial(codol_native_material_t *material)
{
    if (!material) return;
    free(material->owned_name); memset(material,0,sizeof(*material));
}
int CODOL_BuildNativeMaterial(const codol_mounted_model_material_t *source,codol_native_material_t *out)
{
    codol_native_material_t result={0}; size_t extent=0,length;
    const uint8_t *h;
    if (!source || !out || source->asset.type!=5 || !source->name || !*source->name ||
        source->name[0]==',' || !CODOL_AdvanceMaterialStream(source->asset.data,source->asset.size,&extent) ||
        extent!=source->asset.size) return 0;
    length=strlen(source->name)+1;
    result.owned_name=malloc(length); if (!result.owned_name) return 0;
    memcpy(result.owned_name,source->name,length); h=source->asset.data;
    result.material.info.name=result.owned_name;
    /* Both formats have the 24-byte MaterialInfo prefix. DrawSurf is a
     * renderer-specific packed key and is deliberately not translated. */
    result.material.info.gameFlags=(char)h[4];
    result.material.info.sortKey=(char)h[5];
    result.material.info.textureAtlasRowCount=(char)h[6];
    result.material.info.textureAtlasColumnCount=(char)h[7];
    memcpy(&result.material.info.surfaceTypeBits,h+16,4);
    memset(result.material.stateBitsEntry,255,sizeof(result.material.stateBitsEntry));
    *out=result; return 1;
}
int CODOL_LoadNativeModelMaterial(const char *name,unsigned index,codol_native_material_t *out)
{
    codol_mounted_model_material_t source; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedModelMaterialSource(name,index,&source);
    if (status!=1) return status;
    return CODOL_BuildNativeMaterial(&source,out) ? 1 : -1;
}
