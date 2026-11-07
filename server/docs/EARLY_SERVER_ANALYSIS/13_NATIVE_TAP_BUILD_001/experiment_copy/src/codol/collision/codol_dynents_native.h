#ifndef CODOL_DYNENTS_NATIVE_H
#define CODOL_DYNENTS_NATIVE_H
#include "codol_dynents.h"
#include "cm_local.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    struct XModel *model;
    struct FxEffectDef *effect;
    struct PhysPreset *preset;
} codol_dynamic_binding_t;
typedef struct {
    uint32_t count[2];
    DynEntityDef *definitions[2];
    DynEntityPose *poses[2];
    DynEntityClient *clients[2];
    DynEntityColl *collisions[2];
} codol_native_dynamic_entities_t;
/* bindings have one entry per decoded entity. All nonnull references require
 * genuine native dependencies, borrowed for the result's entire lifetime.
 * Types 1/2 match C1's clutter/destruct table; all others are rejected.
 * Owns definitions and zeroed runtime arrays (32/12/20-byte records), matching
 * the retained loader's initial state. Engine activation is a separate phase.
 * Success replaces out; failure leaves it intact. Does not install clipMap. */
int CODOL_BuildNativeDynamicEntities(const codol_dynamic_entities_t *,
    const codol_dynamic_binding_t *const [2],codol_native_dynamic_entities_t *);
void CODOL_FreeNativeDynamicEntities(codol_native_dynamic_entities_t *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
