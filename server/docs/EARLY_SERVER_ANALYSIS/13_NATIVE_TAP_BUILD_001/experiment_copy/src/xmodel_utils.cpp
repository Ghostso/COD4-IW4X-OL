#include "xassets.h"
#include "xassets/xmodel.h"
#include "dobj.h"

extern "C"{

int __cdecl XModelGetBoneIndex(XModel *model, unsigned int name, unsigned int offset, uint8_t *index)
{
  unsigned int numBones;
  unsigned int localBoneIndex;
  uint16_t *boneNames;

  assert(index != NULL);

  if (!model || !index) return 0;
  boneNames = model->boneNames;
  numBones = (uint8_t)model->numBones;

  assert(numBones < DOBJ_MAX_PARTS);

  if (!boneNames || numBones >= DOBJ_MAX_PARTS || offset > UINT8_MAX) return 0;
  for ( localBoneIndex = 0;localBoneIndex < numBones; ++localBoneIndex )
  {
    if ( name == boneNames[localBoneIndex] )
    {
      if (localBoneIndex > UINT8_MAX-offset) return 0;
      *index = localBoneIndex + offset;
      return 1;
    }
  }
  return 0;
}


}



