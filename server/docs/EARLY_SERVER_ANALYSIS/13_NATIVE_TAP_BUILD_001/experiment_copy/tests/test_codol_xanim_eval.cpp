#include "q_shared.h"
#include "xassets/xanims.h"
#include "codol_xanim_native.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <cstdio>
extern "C" void CODOL_TestEvalXAnim16(const XAnimParts *,const uint8_t *,float,float,float *,const uint32_t *);
extern "C" void _GLOBAL__I__Z13XAnim_SetTimefiP9XAnimTime();
extern "C" void CODOL_DispatchXAnimLeaf(XAnimInfo *,float,void *,float *);
// animToModel: eight-word bone mask, part count, then one model bone per part.
static uint8_t anim_map[0x22];
/* Other functions in the retained object reference these engine services.
 * This leaf evaluator must never call them in this fixture. */
extern "C" const char *SL_ConvertToString(unsigned handle) { assert(handle==1); return reinterpret_cast<const char *>(anim_map); }
extern "C" void *GetAnimInfo(unsigned) { std::abort(); }
extern "C" void Com_PrintWarning(int,const char *,...) { std::abort(); }
extern "C" void XAnim_CalcDeltaForTime(const XAnimParts *,float,float *,float *);
static void delta_evaluation_test()
{
    {
        uint8_t bytes[88]={}; codol_mounted_xanim_t source={};
        codol_xanim_handles_t handles={}; codol_native_xanim_t native={};
        source.asset={2,bytes,sizeof(bytes)}; source.name="empty_delta"; source.index_width=1;
        bytes[14]=30; bytes[84]=255; bytes[85]=255; bytes[86]=255; bytes[87]=255;
        assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
        assert(native.parts->bDelta && native.parts->deltaPart);
        assert(!native.parts->deltaPart->trans && !native.parts->deltaPart->quat);
        for(unsigned sample=0;sample<=4;++sample) {
            alignas(16) float translation[4]={1,2,3,4}; float rotation[2]={1,2};
            XAnim_CalcDeltaForTime(native.parts,sample*0.25f,rotation,translation);
            assert(rotation[0]==0 && rotation[1]==32767);
            for(unsigned i=0;i<4;++i) assert(translation[i]==0);
        }
        CODOL_FreeNativeXAnim(&native);
    }
    for(unsigned width=1;width<=2;++width) for(unsigned small=0;small<=1;++small) {
        uint8_t bytes[256]={}; codol_mounted_xanim_t source={};
        codol_xanim_handles_t handles={}; codol_native_xanim_t native={};
        source.asset={2,bytes,sizeof(bytes)}; source.name="root_motion"; source.index_width=width;
        unsigned frames=width==1 ? 20 : 256;
        bytes[14]=frames&255; bytes[15]=frames>>8; bytes[29]=1; bytes[84]=1;
        source.tracks[0]={bytes+100,bytes+104,bytes+132,bytes+144,1,small ? 3u : 6u};
        bytes[100]=1; bytes[102]=small; bytes[128]=1;
        const float bounds[]={3,-2,1,2,4,6}; std::memcpy(bytes+104,bounds,sizeof(bounds));
        bytes[132+width]=frames&255; if(width==2) bytes[135]=frames>>8;
        for(unsigned axis=0;axis<3;++axis) bytes[144+(small ? 3+axis : 6+2*axis)]=10;
        assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
        for(unsigned sample=0;sample<3;++sample) {
            alignas(16) float translation[4]={}; float rotation[2]={};
            XAnim_CalcDeltaForTime(native.parts,sample*0.5f,rotation,translation);
            for(unsigned axis=0;axis<3;++axis)
                assert(translation[axis]==bounds[axis]+bounds[axis+3]*sample*5);
        }
        CODOL_FreeNativeXAnim(&native);
    }
}
int main()
{
    uint8_t bytes[192]={}; codol_mounted_xanim_t source={}; codol_xanim_handles_t handles={};
    codol_native_xanim_t native={};
    source.asset={2,bytes,sizeof(bytes)}; source.name="constant_translation";
    source.bone_count=handles.bone_count=1; handles.bones[0]=7; source.index_width=2;
    bytes[15]=1; bytes[17]=1; bytes[24]=1; bytes[26]=1; // 256 frames, no quat, constant translation, total one
    bytes[4]=1; bytes[8]=3; source.stream_counts[0]=1; source.stream_counts[2]=3;
    source.streams[0]=bytes+96; source.streams[2]=bytes+100;
    float translation[]={4,-8,12}; std::memcpy(bytes+100,translation,sizeof(translation));
    assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
    _GLOBAL__I__Z13XAnim_SetTimefiP9XAnimTime();
    delta_evaluation_test();
    const uint8_t map[]={1}; // Source bone zero writes destination bone one.
    for(unsigned masked=0;masked<2;++masked) for(unsigned frame=0;frame<3;++frame) {
        struct alignas(16) { float before[4],bones[2][8],after[4]; } output={};
        for(unsigned i=0;i<4;++i) { output.before[i]=123; output.after[i]=456; }
        uint32_t ignored[4]={masked ? 0x40000000u : 0u,0,0,0};
        CODOL_TestEvalXAnim16(native.parts,map,frame*0.5f,0.25f,output.bones[0],ignored);
        for(unsigned i=0;i<8;++i) assert(output.bones[0][i]==0);
        assert(output.bones[1][0]==0 && output.bones[1][1]==0 && output.bones[1][2]==0);
        assert(output.bones[1][3]==(masked ? 0 : 0.25f));
        for(unsigned i=0;i<3;++i) assert(output.bones[1][4+i]==(masked ? 0 : translation[i]*0.25f));
        assert(output.bones[1][7]==(masked ? 0 : 0.25f));
        for(unsigned i=0;i<4;++i) assert(output.before[i]==123 && output.after[i]==456);
    }
    // Two byte-quantized translation keys at frames 0 and 256. This exercises
    // the actual index search and interpolation, not just constant samples.
    bytes[24]=0; bytes[22]=1; bytes[6]=3; bytes[8]=6; bytes[10]=6;
    source.stream_counts[1]=3; source.streams[1]=bytes+128;
    source.stream_counts[2]=6; source.stream_counts[4]=6; source.streams[4]=bytes+140;
    uint16_t keys[]={1,0,256}; std::memcpy(bytes+128,keys,sizeof(keys));
    float bounds[]={0,0,0,1,1,1}; std::memcpy(bytes+100,bounds,sizeof(bounds));
    bytes[143]=10; bytes[144]=20; bytes[145]=30;
    assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
    // XAnimCalc dispatches exact time 1.0 through its endpoint path instead
    // of this interpolation entry point. Exercise its [0,1) contract here.
    for(unsigned frame=0;frame<4;++frame) {
        alignas(16) float output[16]={}; uint32_t ignored[4]={};
        CODOL_TestEvalXAnim16(native.parts,map,frame*0.25f,1.0f,output,ignored);
        assert(output[11]==1 && output[15]==1);
        for(unsigned i=0;i<3;++i) assert(output[12+i]==(i+1)*10*frame*0.25f);
    }
    // Full dispatch selects the 8/16-bit path and handles the exact endpoint.
    uint32_t used=0x40000000; std::memcpy(anim_map,&used,4); anim_map[0x21]=1;
    for(unsigned width=1;width<=2;++width) {
        const unsigned frames=width==1 ? 64 : 256;
        bytes[14]=frames&255; bytes[15]=frames>>8; source.index_width=width;
        // Byte indices follow the bone index in dataByte; 16-bit indices
        // follow the key count in dataShort. They are different streams.
        bytes[4]=width==1 ? 3 : 1; source.stream_counts[0]=bytes[4];
        bytes[6]=width==1 ? 1 : 3; source.stream_counts[1]=bytes[6];
        std::memset(bytes+128,0,6); bytes[128]=1;
        if(width==1) { bytes[97]=0; bytes[98]=64; } else bytes[133]=1;
        assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
        for(unsigned frame=0;frame<=4;++frame) {
            alignas(16) static uint8_t calc[0xc040]; std::memset(calc,0,sizeof(calc)); alignas(16) float output[16]={};
            XAnimInfo info={}; info.animToModel=1; info.u.parts=native.parts; info.state.time=frame*0.25f;
            CODOL_DispatchXAnimLeaf(&info,1.0f,calc,output);
            for(unsigned i=0;i<8;++i) assert(output[i]==0);
            assert(output[11]==1 && output[15]==1);
            for(unsigned i=0;i<3;++i) {
                if(output[12+i]!=(i+1)*10*frame*0.25f)
                    std::fprintf(stderr,"width=%u frame=%u component=%u actual=%g expected=%g\n",width,frame,i,output[12+i],(i+1)*10*frame*0.25f);
                assert(output[12+i]==(i+1)*10*frame*0.25f);
            }
        }
    }
    CODOL_FreeNativeXAnim(&native);
    std::puts("PASS: retained XAnim evaluator consumes converted constants, interpolation, remapping, weights and masks");
}
