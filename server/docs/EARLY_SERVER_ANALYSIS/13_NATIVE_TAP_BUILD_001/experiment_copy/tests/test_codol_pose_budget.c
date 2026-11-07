/* Server-pose copies of character parts (codol_pose_budget.c). */
#include "codol_pose_budget.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* A head-like part: root tag_origin, then j_neck -> j_head with face bones,
 * tag_eye and j_helmet under j_head. Handles are bone indices + 1. */
static const char *const names[]={"tag_origin","j_neck","j_head","j_brow_le","tag_eye","j_jaw","j_head_end","j_helmet"};
static const char *bone_name(unsigned handle)
{
    return handle>=1 && handle<=sizeof(names)/sizeof(names[0]) ? names[handle-1] : NULL;
}

int main(void)
{
    xScriptString_t handles[8]={1,2,3,4,5,6,7,8};
    /* Parent offsets for bones 1..7: neck<-root, head<-neck, brow<-head,
     * eye<-head, jaw<-head, head_end<-head, helmet<-head_end. */
    char parents[7]={1,1,1,2,3,4,1};
    short quats[7*4];
    float trans[7*3];
    char classes[8]={0,3,2,2,2,2,2,2};
    DObjAnimMat base[8];
    XBoneInfo_t info[8];
    XModelCollSurf_t coll={0};
    XModel source,*pose;
    unsigned i;
    static const unsigned kept[]={0,1,2,4,6,7};
    memset(&source,0,sizeof(source));
    memset(base,0,sizeof(base));
    memset(info,0,sizeof(info));
    for(i=0;i<7*4;++i)quats[i]=(short)(100+i);
    for(i=0;i<7*3;++i)trans[i]=(float)i+0.5f;
    for(i=0;i<8;++i){ base[i].trans[2]=(float)(10*i); base[i].quat[3]=1.0f; }
    /* Hit volumes on the neck, the head and the helmet only. */
    info[1].radiusSquared=20.8f; info[2].radiusSquared=50.8f; info[7].radiusSquared=9.5f;
    info[2].bounds[1][0]=7.8f;
    source.name="hea_test"; source.numBones=8; source.numRootBones=1;
    source.boneNames=handles; source.parentList=parents; source.quats=quats; source.trans=trans;
    source.partClassification=classes; source.baseMat=base; source.boneInfo=info;
    source.collSurfs=&coll; source.numCollSurfs=1; source.contents=0x2000000; source.radius=12.0f;

    pose=CODOL_BuildGameplayPoseModel(&source,bone_name);
    assert(pose);
    /* Kept: root, the three hit bones, tag_eye and j_head_end (the helmet's
     * parent). Dropped: the face bones with no volume. */
    assert((unsigned char)pose->numBones==6 && pose->numRootBones==1);
    for(i=0;i<6;++i) {
        unsigned from=kept[i];
        assert(pose->boneNames[i]==handles[from]);
        assert(pose->partClassification[i]==classes[from]);
        assert(!memcmp(&pose->baseMat[i],&base[from],sizeof(base[from])));
        assert(!memcmp(&pose->boneInfo[i],&info[from],sizeof(info[from])));
        if(i) {
            assert(!memcmp(pose->quats+(i-1)*4,quats+(from-1)*4,4*sizeof(short)));
            assert(!memcmp(pose->trans+(i-1)*3,trans+(from-1)*3,3*sizeof(float)));
        }
    }
    /* Parents re-expressed as offsets in the reduced numbering:
     * neck<-root, head<-neck, eye<-head, head_end<-head, helmet<-head_end. */
    assert(pose->parentList[0]==1 && pose->parentList[1]==1 && pose->parentList[2]==1 &&
           pose->parentList[3]==2 && pose->parentList[4]==1);
    assert(((uintptr_t)pose&15)==0 && ((uintptr_t)pose->boneNames&15)==0 && ((uintptr_t)pose->quats&15)==0 &&
           ((uintptr_t)pose->trans&15)==0 && ((uintptr_t)pose->baseMat&15)==0 && ((uintptr_t)pose->boneInfo&15)==0);
    assert(!pose->collSurfs && !pose->numCollSurfs);
    assert(pose->name==source.name && pose->contents==source.contents && pose->radius==source.radius);
    /* The source is untouched. */
    assert((unsigned char)source.numBones==8 && source.collSurfs==&coll);
    CODOL_FreeGameplayPoseModel(pose);

    /* Nothing to drop: every bone is a root, a tag, a hit bone or an ancestor. */
    info[3].radiusSquared=1.0f; info[5].radiusSquared=1.0f;
    assert(!CODOL_BuildGameplayPoseModel(&source,bone_name));
    /* Malformed parent offsets are refused rather than copied. */
    info[3].radiusSquared=0.0f;
    parents[4]=9;
    assert(!CODOL_BuildGameplayPoseModel(&source,bone_name));
    puts("PASS: server pose copy keeps roots, tags, hit bones and their ancestors");
    return 0;
}
