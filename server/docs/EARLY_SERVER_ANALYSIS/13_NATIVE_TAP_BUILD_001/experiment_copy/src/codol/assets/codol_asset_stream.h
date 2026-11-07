#ifndef CODOL_ASSET_STREAM_H
#define CODOL_ASSET_STREAM_H
#include <stddef.h>
#include <stdint.h>
/* Serialized dependency traversal; no GPU objects are created. Positions
 * advance only on success. Unsupported nested assets fail explicitly. */
int CODOL_AdvanceImageStream(const uint8_t *,size_t,size_t *);
int CODOL_AdvanceWaterStream(const uint8_t *,size_t,size_t *);
int CODOL_AdvanceTechniqueSetStream(const uint8_t *,size_t,size_t *);
int CODOL_AdvanceMaterialStream(const uint8_t *,size_t,size_t *);
int CODOL_AdvanceModelSurfacesStream(const uint8_t *,size_t,size_t *);
int CODOL_AdvancePhysicsPresetStream(const uint8_t *,size_t,size_t *);
int CODOL_AdvancePhysicsMapStream(const uint8_t *,size_t,size_t *);
#endif
