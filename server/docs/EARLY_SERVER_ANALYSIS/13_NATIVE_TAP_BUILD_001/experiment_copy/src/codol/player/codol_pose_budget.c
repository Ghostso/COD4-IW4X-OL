/* Server-pose copies of CoDOL character parts; see codol_pose_budget.h. */
#include "codol_pose_budget.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Bone arrays keep the 16-byte alignment the loader gives them
 * (codol_xmodel_skeleton.c) for the native skeletal consumers. */
static size_t reserve(size_t *size,size_t bytes)
{
    size_t at=(*size+15)&~(size_t)15;
    *size=at+bytes;
    return at;
}

XModel *CODOL_BuildGameplayPoseModel(const XModel *source,const char *(*bone_name)(unsigned handle))
{
    unsigned char keep[256];
    unsigned char map[256];
    unsigned bones,roots,kept=0,moving,i;
    size_t size=sizeof(XModel),names_at,parents_at,quats_at,trans_at,classes_at,base_at,info_at;
    uint8_t *storage;
    XModel *model;
    if(!source || !bone_name || !source->boneNames)return NULL;
    bones=(unsigned char)source->numBones;
    roots=(unsigned char)source->numRootBones;
    if(!bones || roots>bones || (bones>roots && !source->parentList))return NULL;
    memset(keep,0,sizeof(keep));
    for(i=0;i<bones;++i) {
        const char *name=bone_name(source->boneNames[i]);
        if(i<roots)keep[i]=1;
        else if(name && !strncmp(name,"tag_",4))keep[i]=1;
        else if(source->boneInfo && source->boneInfo[i].radiusSquared>0.0f)keep[i]=1;
    }
    /* Parents precede children (the loader rejects any other order), so one
     * descending pass closes the kept set over ancestors. */
    for(i=bones;i-->roots;) {
        unsigned offset=(unsigned char)source->parentList[i-roots];
        if(!offset || offset>i)return NULL;
        if(keep[i])keep[i-offset]=1;
    }
    for(i=0;i<bones;++i)if(keep[i])map[i]=(unsigned char)kept++;
    if(kept==bones)return NULL;
    moving=kept-roots;
    names_at=reserve(&size,kept*sizeof(*source->boneNames));
    parents_at=reserve(&size,moving);
    quats_at=reserve(&size,moving*4*sizeof(short));
    trans_at=reserve(&size,moving*3*sizeof(float));
    classes_at=reserve(&size,kept);
    base_at=reserve(&size,kept*sizeof(DObjAnimMat));
    info_at=reserve(&size,kept*sizeof(XBoneInfo_t));
    /* malloc's alignment is only 8 on this target; over-allocate and align
     * the model itself so every array offset above stays 16-aligned. */
    storage=(uint8_t *)calloc(1,size+15+sizeof(void *));
    if(!storage)return NULL;
    {
        uintptr_t base=((uintptr_t)(storage+sizeof(void *))+15)&~(uintptr_t)15;
        ((void **)base)[-1]=storage;
        model=(XModel *)base;
    }
    *model=*source;
    model->numBones=(char)kept;
    model->boneNames=(xScriptString_t *)((uint8_t *)model+names_at);
    model->parentList=source->parentList ? (char *)((uint8_t *)model+parents_at) : NULL;
    model->quats=source->quats ? (short *)((uint8_t *)model+quats_at) : NULL;
    model->trans=source->trans ? (float *)((uint8_t *)model+trans_at) : NULL;
    model->partClassification=source->partClassification ? (char *)((uint8_t *)model+classes_at) : NULL;
    model->baseMat=source->baseMat ? (DObjAnimMat *)((uint8_t *)model+base_at) : NULL;
    model->boneInfo=source->boneInfo ? (XBoneInfo_t *)((uint8_t *)model+info_at) : NULL;
    /* Collision surfaces name bones by source index; players and corpses are
     * hit through the bone boxes (DObjTraceline), never these. */
    model->collSurfs=NULL;
    model->numCollSurfs=0;
    for(i=0;i<bones;++i) {
        unsigned to;
        if(!keep[i])continue;
        to=map[i];
        model->boneNames[to]=source->boneNames[i];
        if(model->partClassification)model->partClassification[to]=source->partClassification[i];
        if(model->baseMat)model->baseMat[to]=source->baseMat[i];
        if(model->boneInfo)model->boneInfo[to]=source->boneInfo[i];
        if(i<roots)continue;
        model->parentList[to-roots]=(char)(to-map[i-(unsigned char)source->parentList[i-roots]]);
        if(model->quats)memcpy(model->quats+(to-roots)*4,source->quats+(i-roots)*4,4*sizeof(short));
        if(model->trans)memcpy(model->trans+(to-roots)*3,source->trans+(i-roots)*3,3*sizeof(float));
    }
    return model;
}

void CODOL_FreeGameplayPoseModel(XModel *model)
{
    if(model)free(((void **)model)[-1]);
}
