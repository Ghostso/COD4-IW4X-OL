#include "q_shared.h"
#include "xassets/xanims.h"
#include "codol_xanim_native.h"
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <cstddef>
static_assert(sizeof(XAnimParts)==88,"IW3 XAnimParts ABI");
static_assert(offsetof(XAnimParts,boneCount)==18,"IW3 bone counts");
static_assert(offsetof(XAnimPartTrans,u.frames.indices)==32,"IW3 translation indices");
static_assert(offsetof(XAnimDeltaPartQuat,u.frames.indices)==8,"IW3 rotation indices");
static unsigned u16(const uint8_t *p) { return p[0]|unsigned(p[1])<<8; }
static uint32_t u32(const uint8_t *p) { return p[0]|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24; }
static bool span(const codol_asset_t &asset,const uint8_t *p,size_t size)
{
    if(!size) return true;
    uintptr_t base=reinterpret_cast<uintptr_t>(asset.data),at=reinterpret_cast<uintptr_t>(p);
    return p && at>=base && at-base<=asset.size && size<=asset.size-(at-base);
}
static bool reserve(size_t &size,size_t count,size_t stride,size_t alignment,size_t &offset)
{
    offset=(size+alignment-1)&~(alignment-1);
    if(offset>CODOL_ASSET_LIMIT || count>(CODOL_ASSET_LIMIT-offset)/stride) return false;
    size=offset+count*stride; return true;
}
void CODOL_FreeNativeXAnim(codol_native_xanim_t *out)
{ if(out) { std::free(out->storage); std::memset(out,0,sizeof(*out)); } }
int CODOL_BuildNativeXAnim(const codol_mounted_xanim_t *source,const codol_xanim_handles_t *handles,codol_native_xanim_t *out)
{
    static const unsigned widths[]={1,2,4,2,1,4},counts[]={4,6,8,32,10,12};
    size_t size=sizeof(XAnimParts),name_at,bones_at,notify_at,stream_at[6],indices_at;
    size_t delta_at=0,track_at[2]={},frames_at[2]={};
    float rate,frequency,previous=-1; unsigned i; codol_native_xanim_t result={};
    if(!source || !handles || !out || source->asset.type!=2 || !source->asset.data || source->asset.size<88 ||
       source->asset.size>CODOL_ASSET_LIMIT || !source->name || !*source->name || source->name[0]==',') return 0;
    const uint8_t *h=source->asset.data;
    if(source->index_width!=(u16(h+14)<256 ? 1u : 2u)) return 0;
    // IW3 has translation and quat2 tracks; never silently discard CoDOL quat4.
    if(h[29]>1 || source->tracks[2].header) return 0;
    bool delta=u32(h+84)!=0;
    for(i=0;i<2;++i) {
        const codol_xanim_track_t &t=source->tracks[i];
        if(!t.header) {
            if(t.metadata || t.indices || t.frames || t.count || t.frame_stride) return 0;
            continue;
        }
        if(!delta || !span(source->asset,t.header,4) || t.count!=u16(t.header) ||
           t.count>u16(h+14) || (i==0 && t.header[2]>1)) return 0;
        unsigned stride=i==0 ? (t.header[2] ? 3 : 6) : 4;
        if(t.frame_stride!=stride) return 0;
        if(!t.count) {
            if(t.metadata || t.indices || !span(source->asset,t.frames,i==0 ? 12 : 4)) return 0;
        } else {
            if(!span(source->asset,t.metadata,i==0 ? 28 : 4) ||
               !span(source->asset,t.indices,size_t(t.count+1)*source->index_width) ||
               !u32(t.metadata+(i==0 ? 24 : 0)) ||
               !span(source->asset,t.frames,size_t(t.count+1)*stride)) return 0;
            unsigned previous_index=0;
            for(unsigned j=0;j<=t.count;++j) {
                unsigned index=source->index_width==1 ? t.indices[j] : u16(t.indices+2*j);
                if(index>u16(h+14) || (j && index<=previous_index) || (!j && index)) return 0;
                previous_index=index;
            }
            if(previous_index!=u16(h+14)) return 0;
        }
        if(i==0) for(unsigned j=0;j<(t.count ? 6u : 3u);++j) {
            float value; std::memcpy(&value,(t.count ? t.metadata : t.frames)+4*j,4);
            if(!std::isfinite(value)) return 0;
        }
    }
    // A present delta container may have all three pointers null (for example
    // pb_prone_death_quickdeath). Preserve the container: native evaluation
    // explicitly handles missing rotation/translation as identity/zero.
    if(source->bone_count!=h[26] || source->notify_count!=h[27] ||
       handles->bone_count!=source->bone_count || handles->notify_count!=source->notify_count ||
       source->index_width!=(u16(h+14)<256 ? 1u : 2u) || source->index_count!=u32(h+36)) return 0;
    std::memcpy(&rate,h+40,4); std::memcpy(&frequency,h+44,4);
    if(!std::isfinite(rate) || !std::isfinite(frequency) || rate<0 || frequency<0 ||
       !span(source->asset,source->notifies,source->notify_count*8)) return 0;
    for(i=0;i<source->bone_count;++i) if(!handles->bones[i]) return 0;
    for(i=0;i<source->notify_count;++i) {
        float time; std::memcpy(&time,source->notifies+8*i+4,4);
        if(!handles->notifies[i] || !std::isfinite(time) || time<0 || time>1 || time<previous) return 0;
        previous=time;
    }
    if(!reserve(size,std::strlen(source->name)+1,1,1,name_at) ||
       !reserve(size,source->bone_count,2,2,bones_at) || !reserve(size,source->notify_count,8,4,notify_at)) return 0;
    for(i=0;i<6;++i) {
        uint32_t count=i==3 ? u32(h+counts[i]) : u16(h+counts[i]);
        if(source->stream_counts[i]!=count || !reserve(size,count,widths[i],widths[i],stream_at[i]) ||
           !span(source->asset,source->streams[i],size-stream_at[i])) return 0;
    }
    if(!reserve(size,source->index_count,source->index_width,source->index_width,indices_at) ||
       !span(source->asset,source->indices,size-indices_at)) return 0;
    if(delta) {
        if(!reserve(size,1,sizeof(XAnimDeltaPart),4,delta_at)) return 0;
        for(i=0;i<2;++i) if(source->tracks[i].header) {
            const codol_xanim_track_t &t=source->tracks[i];
            size_t bytes=i==0 ? sizeof(XAnimPartTrans) : sizeof(XAnimDeltaPartQuat);
            size_t indexed=(i==0 ? 32 : 8)+size_t(t.count+1)*source->index_width;
            if(t.count && indexed>bytes) bytes=indexed;
            if(!reserve(size,bytes,1,4,track_at[i]) ||
               (t.count && !reserve(size,t.count+1,t.frame_stride,i==0 && t.header[2] ? 1 : 2,frames_at[i]))) return 0;
        }
    }
    uint8_t *storage=static_cast<uint8_t *>(std::calloc(1,size)); if(!storage) return 0;
    result.storage=storage; result.size=size; result.parts=reinterpret_cast<XAnimParts *>(storage);
    XAnimParts *p=result.parts;
    std::memcpy(storage+name_at,source->name,std::strlen(source->name)+1); p->name=reinterpret_cast<char *>(storage+name_at);
    p->dataByteCount=u16(h+4); p->dataShortCount=u16(h+6); p->dataIntCount=u16(h+8);
    p->randomDataByteCount=u16(h+10); p->randomDataIntCount=u16(h+12); p->numframes=u16(h+14);
    /* Source byte 16 is a flags byte (IW4 layout: bit 0 looping, bit 1 delta,
     * higher bits other traits), not IW3's standalone bLoop byte. Copying the
     * whole byte made every non-looping delta animation read as looping, which
     * XAnimFillInSyncNodes_r then rejected inside nonloopsync groups. */
    p->bLoop=(h[16]&1) ? 1 : 0; std::memcpy(p->boneCount,h+17,10); p->notifyCount=h[27]; p->assetType=h[30];
    // C1 GetAbsDelta (63ac30) evaluates a leaf without IW3's +11 flag gate.
    // Retained XAnimGetAbsDelta requires that flag, so derive it from the
    // converted delta payload rather than copying source byte 29.
    p->bDelta=delta;
    p->randomDataShortCount=u32(h+32); p->indexCount=source->index_count; p->framerate=rate; p->frequency=frequency;
    if(source->bone_count) { std::memcpy(storage+bones_at,handles->bones,source->bone_count*2); p->names=reinterpret_cast<uint16_t *>(storage+bones_at); }
    if(source->notify_count) {
        p->notify=reinterpret_cast<XAnimNotifyInfo *>(storage+notify_at);
        for(i=0;i<source->notify_count;++i) { p->notify[i].name=handles->notifies[i]; std::memcpy(&p->notify[i].time,source->notifies+8*i+4,4); }
    }
    const size_t targets[]={offsetof(XAnimParts,dataByte),offsetof(XAnimParts,dataShort),offsetof(XAnimParts,dataInt),
        offsetof(XAnimParts,randomDataShort),offsetof(XAnimParts,randomDataByte),offsetof(XAnimParts,randomDataInt)};
    for(i=0;i<6;++i) if(source->stream_counts[i]) {
        void *data=storage+stream_at[i]; std::memcpy(data,source->streams[i],size_t(source->stream_counts[i])*widths[i]);
        std::memcpy(storage+targets[i],&data,sizeof(data));
    }
    if(source->index_count) { p->indices.data=storage+indices_at; std::memcpy(p->indices.data,source->indices,source->index_count*source->index_width); }
    if(delta) {
        p->deltaPart=reinterpret_cast<XAnimDeltaPart *>(storage+delta_at);
        for(i=0;i<2;++i) if(source->tracks[i].header) {
            const codol_xanim_track_t &t=source->tracks[i];
            uint8_t *target=storage+track_at[i];
            std::memcpy(target,t.header,4);
            if(!t.count) std::memcpy(target+4,t.frames,i==0 ? 12 : 4);
            else {
                if(i==0) std::memcpy(target+4,t.metadata,24);
                void *frames=storage+frames_at[i];
                std::memcpy(target+(i==0 ? 28 : 4),&frames,sizeof(frames));
                std::memcpy(target+(i==0 ? 32 : 8),t.indices,size_t(t.count+1)*source->index_width);
                std::memcpy(frames,t.frames,size_t(t.count+1)*t.frame_stride);
            }
            if(i==0) p->deltaPart->trans=reinterpret_cast<XAnimPartTrans *>(target);
            else p->deltaPart->quat=reinterpret_cast<XAnimDeltaPartQuat *>(target);
        }
    }
    CODOL_FreeNativeXAnim(out); *out=result; return 1;
}
