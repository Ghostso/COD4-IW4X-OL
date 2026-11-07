/* Exercise the actual engine lookup with an inaccessible page after the array. */
#include "xassets/xmodel.h"
#include <sys/mman.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#undef assert
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"failed: %s:%d: %s\n",__FILE__,__LINE__,#x); abort(); } } while (0)
extern "C" int XModelGetBoneIndex(XModel *,unsigned,unsigned,uint8_t *);
extern "C" XModelLodInfo_t *XModelGetLodInfo(const XModel *,int);
extern "C" float XModelGetLodDist(const XModel *,unsigned);
extern "C" int XModelGetSurfCount(const XModel *,int);
extern "C" int XModelGetLodForDist(const XModel *,float);
extern "C" void XModelSetSModelCacheForLod(XModel *,unsigned,unsigned,unsigned);
extern "C" int XModelGetStaticModelCacheVertCount(XModel *,unsigned);
extern "C" XSurface *XModelGetSurface(const XModel *,int,int);
extern "C" int XModelGetSurfaces(const XModel *,XSurface **,int);
extern "C" int XModelGetLodRampType(const XModel *);
extern "C" qboolean Assert_MyHandler(const char *exp,const char *file,int line,const char *,const char *,...)
{
    fprintf(stderr,"engine assertion: %s:%d: %s\n",file,line,exp); abort();
}

int main(void)
{
    const size_t page=(size_t)sysconf(_SC_PAGESIZE);
    unsigned char *memory=(unsigned char *)mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    CHECK(memory!=MAP_FAILED);
    CHECK(!mprotect(memory+page,page,PROT_NONE));
    XModel model={};
    XSurface surfaces[8]={};
    model.surfs=surfaces;
    model.numLods=4;
    model.lodRampType=XMODEL_LOD_RAMP_RIGID;
    CHECK(XModelGetLodRampType(&model)==XMODEL_LOD_RAMP_RIGID);
    model.lodRampType=XMODEL_LOD_RAMP_SKINNED;
    CHECK(XModelGetLodRampType(&model)==XMODEL_LOD_RAMP_SKINNED);
    for (unsigned i=0;i<4;++i) {
        model.lodInfo[i].dist=(float)(100*(i+1));
        model.lodInfo[i].numsurfs=(unsigned short)(10+i);
        model.lodInfo[i].surfIndex=(unsigned short)i;
        XSurface *first=NULL;
        CHECK(XModelGetSurface(&model,i,1)==&surfaces[i+1]);
        CHECK(XModelGetSurfaces(&model,&first,i)==10+(int)i && first==&surfaces[i]);
        CHECK(XModelGetLodInfo(&model,i)==&model.lodInfo[i]);
        CHECK(XModelGetLodDist(&model,i)==model.lodInfo[i].dist);
        CHECK(XModelGetSurfCount(&model,i)==10+(int)i);
        XModelSetSModelCacheForLod(&model,i,20+i,4+i);
        CHECK(model.lodInfo[i].smodelCacheIndexPlusOne==21+i);
        CHECK(model.lodInfo[i].smodelCacheVertCountExponent==4+i);
        CHECK(XModelGetStaticModelCacheVertCount(&model,i)==(1<<(4+i)));
    }
    CHECK(XModelGetLodForDist(&model,250)==2);
    CHECK(XModelGetLodForDist(&model,400)==-1);
    uint8_t index=73;
    model.boneNames=(uint16_t *)(memory+page); /* zero bones must never dereference */
    CHECK(!XModelGetBoneIndex(&model,1,0,&index) && index==73);
    model.numBones=(char)159;
    model.boneNames=(uint16_t *)(memory+page)-159;
    for (unsigned i=0;i<159;++i) model.boneNames[i]=(uint16_t)(i+1);
    CHECK(!XModelGetBoneIndex(&model,999,0,&index) && index==73);
    CHECK(XModelGetBoneIndex(&model,159,0,&index) && index==158);
    CHECK(XModelGetBoneIndex(&model,159,97,&index) && index==255);
    CHECK(!XModelGetBoneIndex(&model,159,98,&index) && index==255);
    CHECK(!XModelGetBoneIndex(&model,1,256,&index) && index==255);
    model.boneNames[1]=1;
    CHECK(XModelGetBoneIndex(&model,1,5,&index) && index==5); /* first match */
    CHECK(!munmap(memory,page*2));
    puts("PASS: native model lookup bounds and assembly LOD layout/accessors");
}
