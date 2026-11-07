#ifndef CODOL_PHYSICS_H
#define CODOL_PHYSICS_H
#include "codol_xmodel.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    char *storage;
    const char *name,*sound_prefix;
    uint32_t type;
    float mass,bounce,friction,bullet_force_scale,explosive_force_scale;
    float pieces_spread_fraction,pieces_upward_velocity;
    uint8_t extended[28];
} codol_physics_preset_t;
/* Requires a resolved, non-stub preset. The 28-byte extension is retained verbatim;
 * offset 40 is not IW3's cylinder flag. Failure leaves output unchanged. */
int CODOL_ReadPhysicsPreset(const codol_mounted_model_physics_t *,codol_physics_preset_t *);
void CODOL_FreePhysicsPreset(codol_physics_preset_t *);
typedef struct {
    const uint8_t *record; /* 68-byte geometry record; not an IW3 object. */
    const uint8_t *brush;  /* Optional 68-byte CoDOL brush. */
    const uint8_t *sides,*adjacency,*planes;
    const uint8_t **side_planes;
    uint32_t side_count,adjacency_size;
} codol_physics_geometry_t;
typedef struct {
    const char *name;
    const uint8_t *header; /* Original 72-byte header. */
    uint32_t count;
    codol_physics_geometry_t *geometries;
    float center_of_mass[3],moments_of_inertia[3],products_of_inertia[3];
} codol_physics_map_t;
/* Owns descriptor arrays only. Byte views and name borrow the source/archive.
 * Resolves plane references within retained block 3, with complete bounds checks.
 * Initialize output to zero; success replaces it, failure leaves it unchanged.
 * Mass properties are decoded and checked for finite values, without applying
 * a simulation fallback or scale. Does not infer native brush contents or types. */
int CODOL_ReadPhysicsMap(const codol_mounted_model_physics_t *,codol_physics_map_t *);
void CODOL_FreePhysicsMap(codol_physics_map_t *);
/* Newest named map, including inline definitions. Cached views remain valid
 * until unmount, including after archive replacement. 1=ready, 0=absent,
 * -1=invalid; output changes only when ready. */
int CODOL_LoadMountedPhysicsMap(const char *,const codol_physics_map_t **);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
