#include "dobj.h"
#include "xassets/xmodel.h"
#include "cscr_stringlist.h"
#include <string.h>
/*
duplicate of void __cdecl DObjDumpInfo(DObj *obj)

void PrintDObjInfo(DObj_t* dobj)
{
	int idx, i, j;
	const char* duplicatePartsString;

	if(dobj)
	{
		////////////////////////////////////////////////////////////////////////////////////////////////
		Com_Printf(CON_FIRST_DEBUG_CHANNEL,"\nModels:\n");
		if ( dobj->numModels > 0 )
		{
			idx = 0;
			for(j = 0; j < dobj->numModels; ++j)
			{
				Com_Printf(CON_FIRST_DEBUG_CHANNEL,"%d: '%s'\n", idx, dobj->models[j]->name);
				idx += dobj->models[j]->numBones;
			}
		}
		///////////////////////////////////////////////////////////////////////////////////////////////
		Com_Printf(CON_FIRST_DEBUG_CHANNEL,"\nBones:\n");
		if(dobj->numBones)
		{
			idx = 0;
			for(i = 0; i < dobj->numModels; ++i)
			{
				for(j = 0; j < dobj->models[i]->numBones; ++j)
					Com_Printf(CON_FIRST_DEBUG_CHANNEL,"Bone %d: '%s'\n", idx++, SL_ConvertToString(dobj->models[i]->boneNames[j]));
			}
		}
		/////////////////////////////////////////////////////////////////////////////////////
		Com_Printf(CON_FIRST_DEBUG_CHANNEL,"\nPart duplicates:\n");
		if(dobj->duplicateParts)
		{
			duplicatePartsString = SL_ConvertToString(dobj->duplicateParts);
			i = 16;
			while(duplicatePartsString[i])
			{
				Com_Printf(CON_FIRST_DEBUG_CHANNEL,"%d -> %d\n", duplicatePartsString[i], duplicatePartsString[i + 1]);
				i += 2;
			}
		}
		else
			Com_Printf(CON_FIRST_DEBUG_CHANNEL,"\nNo part duplicates.\n");
		Com_Printf(CON_FIRST_DEBUG_CHANNEL,"\n");
	}
	else
		Com_Printf(CON_FIRST_DEBUG_CHANNEL,"No Dobj\n");
}
*/

void __cdecl ConvertQuatToMat(DObjAnimMat *mat, vec3_t axis[3])
{
  vec3_t scaledQuat;
  float xx;
  float xy;
  float xz;
  float xw;
  float yy;
  float yz;
  float yw;
  float zz;
  float zw;

  assert(!IS_NAN((mat->quat)[0]) && !IS_NAN((mat->quat)[1]) && !IS_NAN((mat->quat)[2]) && !IS_NAN((mat->quat)[3]));
  assert(!IS_NAN(mat->transWeight));

  VectorScale(mat->quat, mat->transWeight, scaledQuat);
  xx = scaledQuat[0] * mat->quat[0];
  xy = scaledQuat[0] * mat->quat[1];
  xz = scaledQuat[0] * mat->quat[2];
  xw = scaledQuat[0] * mat->quat[3];
  yy = scaledQuat[1] * mat->quat[1];
  yz = scaledQuat[1] * mat->quat[2];
  yw = scaledQuat[1] * mat->quat[3];
  zz = scaledQuat[2] * mat->quat[2];
  zw = scaledQuat[2] * mat->quat[3];
  axis[0][0] = 1.0 - (yy + zz);
  axis[0][1] = xy + zw;
  axis[0][2] = xz - yw;
  axis[1][0] = xy - zw;
  axis[1][1] = 1.0 - (xx + zz);
  axis[1][2] = yz + xw;
  axis[2][0] = xz + yw;
  axis[2][1] = yz - xw;
  axis[2][2] = 1.0 - (xx + yy);
}


/* ---------------------------------------------------------------------------
 * CoDOL: 253-bone DObjs.
 *
 * C1's DObj holds up to 253 bones and eight-word part masks; the retained IW3
 * one held 128 bones and four-word masks. These drivers replace the retained
 * _dobj.asm / _dobj_skel.asm versions whose stack masks were four words. The
 * per-bone math stays in the retained helpers.
 * ------------------------------------------------------------------------- */
#define DOBJ_REGPARM __attribute__((regparm(3)))
/* _dobj_skel.asm: model in eax, skeleton in edx, first bone in ecx. */
extern void DOBJ_REGPARM CalcSkelRootBonesNoParentOrDuplicate(const XModel *model, DSkel_t *skel,
    int minBoneIndex, int *calcPartBits);
extern void DOBJ_REGPARM CalcSkelRootBonesWithParent(const XModel *model, DSkel_t *skel,
    int minBoneIndex, int parentIndex, int *calcPartBits, const int *controlPartBits);
extern void DOBJ_REGPARM CalcSkelNonRootBones(const XModel *model, DSkel_t *skel,
    int minBoneIndex, int *calcPartBits, const int *controlPartBits);
struct DObjModel_s;
extern void __cdecl DObjCalcAnim(const DObj *obj, int *partBits);
extern void __cdecl DObjCreate(struct DObjModel_s *dobjModels, unsigned int numModels,
    struct XAnimTree_s *tree, DObj *obj, unsigned int entnum);
extern void __cdecl SL_RemoveRefToStringOfSize(unsigned int stringValue, unsigned int len);
extern void __cdecl MT_Free(void *p, int numBytes);
extern unsigned int g_empty;

/* The duplicate-part string: a DOBJ_PART_BIT_WORDS mask of duplicated bones,
 * then (duplicate + 1, original + 1) byte pairs ascending, then a zero. */
#define DOBJ_DUPLICATE_PAIRS_OFFSET (DOBJ_PART_BIT_WORDS * 4)

void __cdecl DObjCalcSkel(DObj *obj, int *partBits)
{
  DSkel_t *skel = (DSkel_t *)&obj->skel;
  int calcPartBits[DOBJ_PART_BIT_WORDS];
  int controlPartBits[DOBJ_PART_BIT_WORDS];
  int uptodate[DOBJ_PART_BIT_WORDS];
  const unsigned char *duplicates;
  const unsigned char *pairs;
  const unsigned char *parents;
  DObjAnimMat *mats;
  int word, allDone = 1;
  unsigned int modelIndex, boneStart;

  for ( word = 0; word < DOBJ_PART_BIT_WORDS; ++word )
  {
    uptodate[word] = ~partBits[word] | skel->partBits.skel[word];
    if ( uptodate[word] != -1 )
      allDone = 0;
  }
  if ( allDone )
    return;

  DObjCalcAnim(obj, partBits);

  duplicates = (const unsigned char *)SL_ConvertToString(obj->duplicateParts);
  for ( word = 0; word < DOBJ_PART_BIT_WORDS; ++word )
  {
    int duplicateBits;
    memcpy(&duplicateBits, duplicates + 4 * word, sizeof(duplicateBits));
    skel->partBits.skel[word] |= partBits[word];
    controlPartBits[word] = skel->partBits.control[word];
    calcPartBits[word] = ~(uptodate[word] | duplicateBits);
  }

  pairs = duplicates + DOBJ_DUPLICATE_PAIRS_OFFSET;
  parents = (const unsigned char *)(obj->models + obj->numModels);
  mats = (DObjAnimMat *)skel->mat;
  boneStart = 0;
  for ( modelIndex = 0; modelIndex < obj->numModels; ++modelIndex )
  {
    const XModel *model = obj->models[modelIndex];
    unsigned int boneEnd = boneStart + (unsigned char)model->numBones;

    /* A melded part's duplicate bones take the pose of the bone they merge with. */
    while ( (unsigned int)(pairs[0] - 1) < boneEnd )
    {
      mats[pairs[0] - 1] = mats[pairs[1] - 1];
      pairs += 2;
    }
    if ( parents[modelIndex] == 0xff )
      CalcSkelRootBonesNoParentOrDuplicate(model, skel, boneStart, calcPartBits);
    else
      CalcSkelRootBonesWithParent(model, skel, boneStart, parents[modelIndex], calcPartBits, controlPartBits);
    CalcSkelNonRootBones(model, skel, boneStart + (unsigned char)model->numRootBones, calcPartBits, controlPartBits);
    boneStart = boneEnd;
  }
}

/* DB_SaveDObjs/DB_LoadDObjs park every DObj across a zone reload in its own
 * storage: parent bones by name, so the models can be re-melded afterwards. */
typedef struct DObjModelArchive_s
{
  XModel *model;
  uint16_t boneName;
  uint8_t ignoreCollision;
  uint8_t pad;
} DObjModelArchive;

typedef struct DObjArchived_s
{
  uint16_t parentBoneNames[32];
  XModel **models;
  unsigned int ignoreCollision;
  uint16_t numModels;
  uint16_t entnum;
  struct XAnimTree_s *tree;
  int hidePartBits[DOBJ_PART_BIT_WORDS];
} DObjArchived;

DOBJ_STATIC_ASSERT(sizeof(DObjModelArchive) == 8, "DObjModel_s stride");
DOBJ_STATIC_ASSERT(sizeof(DObjArchived) <= __builtin_offsetof(DObj, models), "archived DObj fits before models");

void __cdecl DObjArchive(DObj *obj)
{
  DObjArchived archived;
  unsigned int boneStart[32];
  unsigned int numModels = obj->numModels;
  const unsigned char *parents = (const unsigned char *)(obj->models + numModels);
  unsigned int i, total = 0;

  memset(&archived, 0, sizeof(archived));
  archived.numModels = numModels;
  archived.entnum = obj->entnum;
  archived.tree = obj->tree;
  archived.models = obj->models;
  memcpy(archived.hidePartBits, obj->hidePartBits, sizeof(archived.hidePartBits));
  for ( i = 0; i < numModels && i < 32; ++i )
  {
    unsigned int parent = parents[i];
    boneStart[i] = total;
    total += XModelNumBones(obj->models[i]);
    if ( obj->ignoreCollision & (1u << i) )
      archived.ignoreCollision |= 1u << i;
    if ( parent != 0xff && i > 0 )
    {
      int j;
      for ( j = (int)i - 1; j >= 0 && boneStart[j] > parent; --j )
        ;
      if ( j >= 0 )
        archived.parentBoneNames[i] = obj->models[j]->boneNames[parent - boneStart[j]];
    }
  }
  obj->models = NULL;
  obj->tree = NULL;
  if ( obj->duplicateParts )
  {
    if ( obj->duplicateParts != g_empty )
      SL_RemoveRefToStringOfSize(obj->duplicateParts, obj->duplicatePartsSize);
    obj->duplicatePartsSize = 0;
    obj->duplicateParts = 0;
  }
  memcpy(obj, &archived, sizeof(archived));
}

void __cdecl DObjUnarchive(DObj *obj)
{
  DObjArchived archived;
  DObjModelArchive models[32];
  unsigned int i;

  memcpy(&archived, obj, sizeof(archived));
  for ( i = 0; i < archived.numModels && i < 32; ++i )
  {
    models[i].model = archived.models[i];
    models[i].boneName = archived.parentBoneNames[i];
    models[i].ignoreCollision = (archived.ignoreCollision >> i) & 1;
    models[i].pad = 0;
  }
  MT_Free(archived.models, 5 * archived.numModels);
  DObjCreate((struct DObjModel_s *)models, archived.numModels, archived.tree, obj, archived.entnum);
  memcpy(obj->hidePartBits, archived.hidePartBits, sizeof(obj->hidePartBits));
}
