#ifndef CODOL_ENGINE_WORLD_H
#define CODOL_ENGINE_WORLD_H
struct ComPrimaryLight
{
  unsigned char type, canUseShadowMap, exponent, unused;
  float color[3], dir[3], origin[3];
  float radius, cosHalfFovOuter, cosHalfFovInner, cosHalfFovExpanded;
  float rotationLimit, translationLimit;
  const char *defName;
};
struct GameWorldMp
{
  const char *name;
};


struct ComWorld
{
  const char *name;
  int isInUse;
  unsigned int primaryLightCount;
  struct ComPrimaryLight *primaryLights;
};


extern struct ComWorld comWorld;
extern struct GameWorldMp gameWorldMp;
#endif
