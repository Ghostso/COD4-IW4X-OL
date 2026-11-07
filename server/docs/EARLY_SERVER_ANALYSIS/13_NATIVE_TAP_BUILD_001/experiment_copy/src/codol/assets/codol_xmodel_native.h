#ifndef CODOL_XMODEL_NATIVE_H
#define CODOL_XMODEL_NATIVE_H
#include "codol_xmodel.h"
#include "codol_xsurface.h"
#include "xassets/xmodel.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* Construction state, not a publishable asset. Skeleton, strings and bone
 * bounds and collision triangle arrays are borrowed and must outlive this core.
 * Collision surface descriptors and any
 * bound material-handle array are owned; mesh geometry/material assets are borrowed.
 * Complete header metadata and material/LOD/physics binding before installing
 * model in the engine. Fields outside this core deliberately remain zero. */
typedef struct {
    XModel model;
    uint32_t physics_preset_reference,physics_map_reference;
} codol_native_model_core_t;
int CODOL_BuildNativeModelCore(const codol_mounted_model_skeleton_t *,
    const codol_mounted_model_geometry_t *,const uint16_t *,unsigned,
    codol_native_model_core_t *);
void CODOL_FreeNativeModelCore(codol_native_model_core_t *);
/* Native SL system must be initialized. Returns 1/0/-1 for ready/absent/invalid.
 * Borrowed mounted data remains valid until archive unmount; free the core first. */
int CODOL_LoadNativeModelCore(const char *,codol_native_model_core_t *);
/* Cached dedicated collision model: native skeleton, triangle descriptors,
 * active LOD mesh and dedicated material handles. The owning model generation
 * retains all dependencies and bone-string references until full unmount,
 * including after map-group replacement. Output unchanged on failure.
 * 1=ready, 0=absent, -1=invalid/unresolved or changed string provider.
 * For static collision consumers only: general DB lookup uses the physics
 * view below. Never use this as a graphical asset. */
int CODOL_LoadMountedCollisionXModel(const char *,codol_bone_string_acquire_t,
    codol_bone_string_release_t,void *,const XModel **);
/* Production SL adapter, called only after the engine string system starts. */
int CODOL_LoadEngineCollisionXModel(const char *,const XModel **);
/* Separate cached model view with resolved native preset and primitive physics
 * map pointers. Shares skeleton/mesh ownership with the collision view. Same
 * lifetime, status and string-provider contract; missing or unsupported physics
 * dependencies fail atomically. Dedicated DB XModel lookup publishes this view;
 * it does not itself activate physics or provide graphical rendering resources. */
int CODOL_LoadMountedPhysicsXModel(const char *,codol_bone_string_acquire_t,
    codol_bone_string_release_t,void *,const XModel **);
int CODOL_LoadEnginePhysicsXModel(const char *,const XModel **);
typedef struct {
    unsigned count;
    XRigidVertList_t *lists;
} codol_native_rigid_lists_t;
/* Owned conversion of inline rigid lists and trees. Pooled references require
 * relocation first and fail explicitly here; failure leaves output unchanged. */
int CODOL_BuildNativeRigidLists(const codol_surface_t *,codol_native_rigid_lists_t *);
void CODOL_FreeNativeRigidLists(codol_native_rigid_lists_t *);
/* Resolves pooled lists/trees from retained block 3, applying loader alignment.
 * All returned data is owned; blocks may be released after success. */
int CODOL_ResolveNativeRigidLists(const codol_surface_t *,const codol_model_block_t[8],codol_native_rigid_lists_t *);
typedef struct {
    XSurface surface;
    codol_surface_arrays_t arrays;
    codol_native_rigid_lists_t rigid;
    uint8_t source_header[84];
} codol_native_surface_geometry_t;
/* Construction state: geometry, modes and representable part bits are native.
 * Remaining header metadata needs mapping before publication. Fully owned.
 * Source masks above the native 128-bit range fail explicitly. */
int CODOL_BuildNativeSurfaceGeometry(const codol_surface_t *,const codol_model_block_t[8],codol_native_surface_geometry_t *);
void CODOL_FreeNativeSurfaceGeometry(codol_native_surface_geometry_t *);
int CODOL_LoadNativeModelSurfaceGeometry(const char *,unsigned,unsigned,codol_native_surface_geometry_t *);
typedef struct {
    unsigned count;
    XSurface *surfaces;
    codol_native_surface_geometry_t *owners;
    uint32_t part_bits[4];
} codol_native_lod_geometry_t;
/* Contiguous native surface array backed by owned geometry, with cumulative
 * 16-bit triangle/vertex offsets and the union of surface bone masks, as in
 * native XModelLoad_640..680. Atomic construction;
 * model-level materials, LOD metadata and publication remain separate steps. */
int CODOL_BuildNativeLodGeometry(const codol_model_surfaces_t *,const codol_model_block_t[8],codol_native_lod_geometry_t *);
int CODOL_LoadNativeModelLodGeometry(const char *,unsigned,codol_native_lod_geometry_t *);
void CODOL_FreeNativeLodGeometry(codol_native_lod_geometry_t *);
typedef struct {
    unsigned count,lod_count;
    int collision_lod;
    XSurface *surfaces;
    uint16_t *material_indices;
    XModelLodInfo_t lods[4];
    codol_native_lod_geometry_t owners[4];
} codol_native_model_mesh_t;
/* Owned contiguous model geometry. Active source LODs are compacted while
 * preserving their original material indices; collision LOD is remapped.
 * Material handles and remaining model metadata are required before publication. */
int CODOL_BuildNativeModelMesh(unsigned,const codol_xmodel_lods_t *,
    const codol_mounted_model_surfaces_t *const [4],codol_native_model_mesh_t *);
int CODOL_LoadNativeModelMesh(const char *,codol_native_model_mesh_t *);
void CODOL_FreeNativeModelMesh(codol_native_model_mesh_t *);
/* Attach an assembled mesh using its original material-slot mapping. Mesh and
 * material assets must outlive the core. Atomic replacement; does not publish. */
int CODOL_BindNativeModelMesh(codol_native_model_core_t *,const codol_native_model_mesh_t *,
    xMaterial_t *const *,unsigned);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
