#include "q_shared.h"
#include "xassets/xanims.h"
#include "codol_xanim_native.h"
#include <cassert>
#include <cstring>
#include <cstdio>
static void put(uint8_t *p,uint32_t v) { std::memcpy(p,&v,4); }
static void delta_test()
{
    for(unsigned width=1;width<=2;++width) for(unsigned small=0;small<=1;++small) {
        uint8_t bytes[512]={}; codol_mounted_xanim_t source={};
        codol_xanim_handles_t handles={}; codol_native_xanim_t native={};
        source.asset={2,bytes,sizeof(bytes)}; source.name="delta"; source.index_width=width;
        unsigned frames=width==1 ? 25 : 256;
        bytes[14]=frames&255; bytes[15]=frames>>8; put(bytes+84,1);
        source.tracks[0]={bytes+100,bytes+104,bytes+132,bytes+144,1,small ? 3u : 6u};
        source.tracks[1]={bytes+180,bytes+184,bytes+188,bytes+200,1,4};
        bytes[100]=1; bytes[102]=small; bytes[180]=1;
        float scale=2,minimum=3; std::memcpy(bytes+104,&minimum,4); std::memcpy(bytes+116,&scale,4);
        put(bytes+128,1); put(bytes+184,1);
        bytes[132+width]=frames&255; bytes[188+width]=frames&255;
        if(width==2) { bytes[135]=frames>>8; bytes[191]=frames>>8; }
        bytes[144]=7; bytes[200]=11;
        assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
        XAnimParts *p=native.parts; assert(p->bDelta==1 && p->deltaPart);
        XAnimPartTrans *t=p->deltaPart->trans; XAnimDeltaPartQuat *q=p->deltaPart->quat;
        assert(t && q && t->size==1 && q->size==1 && t->smallTrans==small);
        assert(t->u.frames.mins[0]==3 && t->u.frames.size[0]==2);
        assert(((uint8_t *)t->u.frames.frames._1)[0]==7 && q->u.frames.frames[0][0]==11);
        assert((width==1 ? t->u.frames.indices._1[1] : t->u.frames.indices._2[1])==frames);
        assert((width==1 ? q->u.frames.indices._1[1] : q->u.frames.indices._2[1])==frames);
        bytes[144]=99; bytes[200]=99;
        assert(((uint8_t *)t->u.frames.frames._1)[0]==7 && q->u.frames.frames[0][0]==11);
        codol_native_xanim_t saved=native;
        source.tracks[2].header=bytes+220;
        assert(!CODOL_BuildNativeXAnim(&source,&handles,&native) && native.storage==saved.storage);
        source.tracks[2].header=NULL;
        bytes[132]=1;
        assert(!CODOL_BuildNativeXAnim(&source,&handles,&native) && native.storage==saved.storage);
        bytes[132]=0; source.tracks[0].frames=bytes+511;
        assert(!CODOL_BuildNativeXAnim(&source,&handles,&native) && native.storage==saved.storage);
        source.tracks[0]={bytes+100,NULL,NULL,bytes+104,0,small ? 3u : 6u}; bytes[100]=0;
        source.tracks[1]={bytes+180,NULL,NULL,bytes+200,0,4}; bytes[180]=0;
        assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
        assert(native.parts->deltaPart->trans->u.frame0[0]==3 && native.parts->deltaPart->quat->u.frame0[0]==99);
        CODOL_FreeNativeXAnim(&native);
    }
}
int main()
{
    delta_test();
    uint8_t bytes[256]={}; char name[]="animation";
    codol_mounted_xanim_t source={}; codol_xanim_handles_t handles={}; codol_native_xanim_t native={};
    source.asset={2,bytes,sizeof(bytes)}; source.name=name;
    source.bone_count=handles.bone_count=1; source.notify_count=handles.notify_count=1;
    source.index_count=2; source.index_width=2; source.indices=bytes+180; source.notifies=bytes+100;
    handles.bones[0]=77; handles.notifies[0]=88;
    bytes[15]=1; bytes[16]=1; bytes[17]=1; bytes[26]=1; bytes[27]=1; bytes[30]=2;
    put(bytes+36,2); float rate=30,frequency=2,time=0.5f;
    std::memcpy(bytes+40,&rate,4); std::memcpy(bytes+44,&frequency,4); std::memcpy(bytes+104,&time,4);
    unsigned counts[]={4,6,8,32,10,12},widths[]={1,2,4,2,1,4};
    for(unsigned i=0;i<6;++i) { bytes[counts[i]]=1; source.stream_counts[i]=1; source.streams[i]=bytes+120+8*i; std::memset(bytes+120+8*i,10+i,widths[i]); }
    bytes[182]=1;
    assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
    XAnimParts *p=native.parts;
    assert(p->bLoop==1 && !p->bDelta && p->boneCount[0]==1 && p->boneCount[9]==1 && p->notifyCount==1 && p->assetType==2);
    assert(p->names[0]==77 && p->notify[0].name==88 && p->notify[0].time==0.5f && !p->notify[0].pad);
    assert(p->numframes==256 && p->framerate==30 && p->frequency==2 && !p->deltaPart);
    assert(p->dataByte[0]==10 && ((uint8_t *)p->dataShort)[0]==11 && ((uint8_t *)p->dataInt)[0]==12);
    assert(((uint8_t *)p->randomDataShort)[0]==13 && p->randomDataByte[0]==14 && ((uint8_t *)p->randomDataInt)[0]==15);
    assert(p->indices._2[1]==1 && p->names!=handles.bones && p->notify!=(void *)source.notifies);
    bytes[120]=99; name[0]='A'; handles.bones[0]=99;
    assert(p->dataByte[0]==10 && p->name[0]=='a' && p->names[0]==77);
    put(bytes+84,0xffffffff);
    assert(CODOL_BuildNativeXAnim(&source,&handles,&native));
    p=native.parts;
    assert(p->bDelta && p->deltaPart && !p->deltaPart->trans && !p->deltaPart->quat);
    codol_native_xanim_t saved=native;
    source.tracks[0].metadata=bytes;
    assert(!CODOL_BuildNativeXAnim(&source,&handles,&native) && !std::memcmp(&saved,&native,sizeof(saved)));
    source.tracks[0].metadata=NULL;
    put(bytes+84,0); put(bytes+104,0x7fc00000);
    assert(!CODOL_BuildNativeXAnim(&source,&handles,&native) && native.parts==p);
    std::memcpy(bytes+104,&time,4); source.streams[5]=bytes+255;
    assert(!CODOL_BuildNativeXAnim(&source,&handles,&native) && native.parts==p);
    source.streams[5]=bytes+160;
    assert(CODOL_BuildNativeXAnim(&source,&handles,&native) && native.parts->name[0]=='A');
    CODOL_FreeNativeXAnim(&native); CODOL_FreeNativeXAnim(&native);
    std::puts("PASS: native XAnim ownership, header mapping, names, notifies and atomic rejection");
}
