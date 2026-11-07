#ifndef XASSETS_FX_H
#define XASSETS_FX_H
#include <stdint.h>
struct FxEffectDef;
/* Native CoDOL elements retain C1's 260-byte layout and source type IDs.
 * The non-CoDOL target keeps its 252-byte element. Scalar ranges remain
 * bit-preserving until named. Legacy IW3 serialized loading uses its own
 * retained assembly layout; it does not construct the mounted C1 graph. */
struct FxElemDef {
  uint8_t parameters[176];
  uint8_t elemType,visualCount,velIntervalCount,visIntervalCount;
  void *velSamples,*visSamples,*visuals;
  float collisionBounds[6];
  struct FxEffectDef *effectRefs[3];
  uint8_t emissionParameters[16];
  void *trailDef;
  uint8_t lighting[4];
#ifdef CODOL_SERVER
  uint8_t codolParameters[4]; /* C1 +252, inline scalar bytes (no loader fixup) */
  const char *spawnSound;     /* C1 +256: resolved XString, not an asset pointer */
#endif
};
typedef struct FxEffectDef
{
  const char *name;
  int flags;
  int totalSize;
  int msecLoopingLife;
  int elemDefCountLooping;
  int elemDefCountOneShot;
  int elemDefCountEmission;
  struct FxElemDef *elemDefs;
} FxEffectDef;


struct FxImpactTable
{
  const char *name;
  struct FxImpactEntry *table;
};
#endif
