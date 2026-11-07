// dobj.h and dobj.c contains structure of ingame DObj and various functions to work with it.

#ifndef __DOBJ_H__
#define __DOBJ_H__

#include "q_shared.h"
#include "entity.h"
#include "qcommon_io.h"
#include "misc.h"


/* Bones one XModel may carry (XModelGetBoneIndex, CoDOL model cores). */
#define DOBJ_MAX_PARTS 160
/* Bones one server DObj may carry: C1's DObjCreate (0x633D90) accepts 253.
 * DObj bone indices stay byte-sized up to 252; 0xfe and 0xff remain the
 * "not looked up" / "not found" sentinels of the bone-index caches. */
#define DOBJ_MAX_BONES 253
/* DObj, DSkel, hide and XAnim part masks hold eight 32-bit words, like C1's
 * (IW3 had four). Bit b is word[b >> 5] & (0x80000000 >> (b & 31)). */
#define DOBJ_PART_BIT_WORDS 8
#define DOBJ_PART_BIT_COUNT (DOBJ_PART_BIT_WORDS * 32)
/* XAnim bone maps send anim parts without a model bone here; the ignore mask
 * always carries its bit. */
#define DOBJ_XANIM_NO_BONE 0xff

typedef struct XBoneInfo
{
  float bounds[2][3];
  float offset[3];
  float radiusSquared;
}XBoneInfo_t;


typedef struct DObjAnimMat
{
  vec4_t quat;
  vec3_t trans;
  float transWeight;
}DObjAnimMat;


typedef struct DObjSkeletonPartMatrix_s // Same as DObjAnimMat_t? Need confirmation!
{
	float p1[4];
	float p2[4];
}DObjSkeletonPartMatrix_t;


typedef struct DSkelPartBits_s
{
	int anim[DOBJ_PART_BIT_WORDS];
	int control[DOBJ_PART_BIT_WORDS];
	int skel[DOBJ_PART_BIT_WORDS];
} DSkelPartBits_t;


typedef struct DSkel
{
	DSkelPartBits_t partBits;
	int timeStamp;
	DObjSkeletonPartMatrix_t *mat;
} DSkel_t;


/* The retained asm (_dobj*.asm, _xanim*.asm, _xmodel.asm) addresses these
 * fields by offset; the static asserts below pin them. */
typedef struct DObj_s
{
  struct XAnimTree_s *tree;             /* 0x00 */
  uint16_t duplicateParts;              /* 0x04 SL string: part mask, then (dup+1, orig+1) byte pairs */
  uint16_t entnum;                      /* 0x06 */
  byte unusedDuplicatePartsSize;        /* 0x08 IW3's byte size; see duplicatePartsSize */
  byte numModels;                       /* 0x09 */
  byte numBones;                        /* 0x0a up to DOBJ_MAX_BONES */
  byte pad;
  unsigned int ignoreCollision;         /* 0x0c */
  volatile int locked;                  /* 0x10 */
  struct DSkel skel;                    /* 0x14 */
  float radius;                         /* 0x7c */
  int hidePartBits[DOBJ_PART_BIT_WORDS];/* 0x80 */
  struct XModel **models;               /* 0xa0 numModels pointers, then numModels parent-bone bytes */
  uint16_t duplicatePartsSize;          /* 0xa4 byte length of duplicateParts */
  uint16_t pad2;
} DObj_t, DObj;

#ifdef __cplusplus
#define DOBJ_STATIC_ASSERT static_assert
#else
#define DOBJ_STATIC_ASSERT _Static_assert
#endif
DOBJ_STATIC_ASSERT(sizeof(DSkelPartBits_t)==0x60,"DSkel part masks");
DOBJ_STATIC_ASSERT(__builtin_offsetof(DObj,skel)==0x14 && __builtin_offsetof(DObj,skel.timeStamp)==0x74 &&
    __builtin_offsetof(DObj,skel.mat)==0x78,"retained asm DSkel offsets");
DOBJ_STATIC_ASSERT(__builtin_offsetof(DObj,radius)==0x7c && __builtin_offsetof(DObj,hidePartBits)==0x80 &&
    __builtin_offsetof(DObj,models)==0xa0 && __builtin_offsetof(DObj,duplicatePartsSize)==0xa4 &&
    sizeof(DObj)==0xa8,"retained asm DObj offsets (objBuf stride 0xa8)");

struct DObjTrace_s
{
  float fraction;
  int sflags;
  vec3_t normal;
  uint16_t modelIndex;
  uint16_t partName;
  uint16_t partGroup;
};



#ifdef __cplusplus
extern "C"{
#endif


DObj_t* GetDObjForEntity(int entNum);
qboolean EntHasDObj(gentity_t* ent);
extern signed int __cdecl G_DObjGetWorldTagMatrix(struct gentity_s *ent, unsigned int tagName, float (*tagMat)[3]);
extern void DObjInit();
extern void DB_LoadDObjs();

void __cdecl DObjGetBounds(DObj_t *obj, float *mins, float *maxs);
DObj *__cdecl Com_GetServerDObj(int handle);
qboolean __cdecl DObjHasContents(DObj *obj, int contentmask);
float __cdecl DObjGetRadius(DObj *obj);
void __cdecl DObjGeomTracelinePartBits(DObj *obj, int contentmask, int *partBits);
void __cdecl DObjGeomTraceline(DObj *obj, float *localStart, float *localEnd, int contentmask, struct DObjTrace_s *results);
void __cdecl DObjTraceline(DObj *obj, float *start, float *end, char *priorityMap, struct DObjTrace_s *trace);
void __cdecl DObjTracelinePartBits(DObj *obj, int *partBits);
qboolean __cdecl DObjSkelExists(DObj *obj, int timeStamp);
qboolean __cdecl DObjSkelAreBonesUpToDate(DObj *obj, int *partBits);
int __cdecl DObjGetAllocSkelSize(DObj *obj);
void __cdecl DObjCreateSkel(DObj *obj, char *buf, int timeStamp);
int __cdecl DObjSkelIsBoneUpToDate(DObj *obj, int boneIndex);
int __cdecl DObjGetBoneIndex(DObj *obj, unsigned int name, char *index, int modelNum);
struct DObjAnimMat *__cdecl DObjGetRotTransArray(DObj *obj);
void __cdecl DObjInitServerTime(DObj *obj, float dtime);
int __cdecl DObjUpdateServerInfo(DObj *obj, float dtime, int notifyFlags);
struct XAnimTree_s *__cdecl DObjGetTree(DObj *obj);
void __cdecl DObjDisplayAnim(DObj *obj, const char *header);
void __cdecl DObjDumpInfo(DObj *obj);
int __cdecl DObjNumBones(DObj *obj);
void __cdecl DObjGetBoneInfo(DObj *obj, struct XBoneInfo **boneInfo);
int __cdecl DObjGetNumModels(DObj *obj);
struct XModel *__cdecl DObjGetModel(DObj *obj, int modelIndex);
bool __cdecl DObjIgnoreCollision(DObj *obj, int modelIndex);
void __cdecl ConvertQuatToMat(struct DObjAnimMat *mat, vec3_t axis[3]);
void __cdecl DObjSetLocalTag(DObj *obj, int *partBits, unsigned int boneIndex, const float *trans, const float *angles);
void __cdecl DObjSetControlTagAngles(DObj *obj, int *partBits, unsigned int boneIndex, float *angles);
void Com_InitDObj();
void __cdecl DObjGetHierarchyBits(DObj *obj, int boneIndex, int *partBits);
void __cdecl DObjCalcSkel(DObj *obj, int *partBits);
struct DObjAnimMat *__cdecl G_DObjGetLocalTagMatrix(struct gentity_s *ent, unsigned int tagName);

#ifdef __cplusplus
}
#endif

extern uint16_t serverObjMap[MAX_GENTITIES]; /* storage in _dobj_management.asm, indexed by entity number */
extern DObj_t objBuf[2048];

#endif //__DOBJ_H__


