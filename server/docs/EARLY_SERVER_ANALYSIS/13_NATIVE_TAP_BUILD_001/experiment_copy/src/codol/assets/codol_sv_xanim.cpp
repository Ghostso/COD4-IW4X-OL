#ifdef CODOL_SERVER
#include "q_shared.h"
#include "xassets/xanims.h"
#include "xassets.h"
#include "cscr_stringlist.h"
#include "codol_xanim_native.h"
#include "dobj.h"
#include <cstring>
#include <cmath>
extern "C" void CODOL_DispatchXAnimLeaf(XAnimInfo *,float,void *,float *);
extern "C" void __cdecl SL_RemoveRefToStringOfSize(unsigned int stringValue,unsigned int len);
extern "C" void _GLOBAL__I__Z13XAnim_SetTimefiP9XAnimTime();
int CODOL_CheckEngineXAnim(const char *name,unsigned *bones)
{
    codol_mounted_xanim_t source={}; const XAnimParts *native=NULL,*again=NULL;
    unsigned map_handle; int status;
    if(!bones) return -1;
    status=CODOL_LoadMountedXAnim(name,&source); if(status!=1) return status;
    /* Anim part count, not DObj bones: XAnimLoadFile's part arrays hold 128. */
    if(source.bone_count>128) return -1;
    native=DB_FindXAssetHeader(ASSET_TYPE_XANIMPARTS,name,false,0).parts;
    again=DB_FindXAssetHeader(ASSET_TYPE_XANIMPARTS,name,false,0).parts;
    if(!native || native!=again) return -1;
    static bool initialized=false;
    if(!initialized) { _GLOBAL__I__Z13XAnim_SetTimefiP9XAnimTime(); initialized=true; }
    /* The retained animToModel layout: an eight-word model-bone mask, the
     * part count, then one model bone per part. */
    const unsigned map_header=DOBJ_PART_BIT_WORDS*4+1,map_size=map_header+source.bone_count;
    uint8_t map[DOBJ_PART_BIT_WORDS*4+1+DOBJ_MAX_BONES]={}; uint32_t used[DOBJ_PART_BIT_WORDS]={};
    map[map_header-1]=source.bone_count;
    for(unsigned i=0;i<source.bone_count;++i) { map[map_header+i]=i; used[i/32]|=0x80000000u>>(i%32); }
    std::memcpy(map,used,sizeof(used));
    map_handle=SL_GetStringOfSize(reinterpret_cast<const char *>(map),0,map_size,11);
    if(!map_handle || map_handle>65535) { if(map_handle) SL_RemoveRefToStringOfSize(map_handle,map_size); return -1; }
    status=1;
    for(unsigned sample=0;sample<5 && status==1;++sample) {
        /* 0x600 layer mats, then the two eight-word masks (DObjCalcAnim). */
        alignas(16) static uint8_t calc[0xc040]; alignas(16) float output[DOBJ_MAX_BONES*8]={};
        std::memset(calc,0,sizeof(calc));
        XAnimInfo info={}; info.animToModel=map_handle; info.u.parts=const_cast<XAnimParts *>(native); info.state.time=sample*0.25f;
        CODOL_DispatchXAnimLeaf(&info,1.0f,calc,output);
        for(unsigned i=0;i<source.bone_count*8;++i) if(!std::isfinite(output[i])) status=-1;
    }
    SL_RemoveRefToStringOfSize(map_handle,map_size);
    if(status==1) *bones=source.bone_count;
    return status;
}
#endif
