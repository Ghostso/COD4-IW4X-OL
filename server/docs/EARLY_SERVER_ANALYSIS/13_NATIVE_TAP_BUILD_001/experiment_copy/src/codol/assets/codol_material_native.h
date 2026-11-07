#ifndef CODOL_MATERIAL_NATIVE_H
#define CODOL_MATERIAL_NATIVE_H
#include "codol_xmodel.h"
#include "xassets/material.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* Dedicated-engine material. Owns its name; renderer-only draw sorting,
 * techniques, texture/constant/state tables are absent, consistent with the
 * null client's disabled renderer. Not an asset for a graphical IW3 client. */
typedef struct {
    Material_t material;
    char *owned_name;
} codol_native_material_t;
int CODOL_BuildNativeMaterial(const codol_mounted_model_material_t *,codol_native_material_t *);
void CODOL_FreeNativeMaterial(codol_native_material_t *);
int CODOL_LoadNativeModelMaterial(const char *,unsigned,codol_native_material_t *);
/* Native asset lookup. Newest named definition wins; repeated lookups reuse
 * its owned cache entry. Borrowed until unmount. 1=ready, 0=absent, -1=invalid
 * or a known stub has no definition. Output stays unchanged on failure. */
int CODOL_LoadEngineMaterial(const char *,const Material_t **);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
