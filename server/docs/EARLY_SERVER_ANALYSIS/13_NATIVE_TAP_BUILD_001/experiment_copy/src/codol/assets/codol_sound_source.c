/* Serialized CoDOL sound traversal. SPDX-License-Identifier: AGPL-3.0-or-later
 * Mirrors C1's loader order exactly: alias list header, list name, alias array,
 * then per alias the five names, the sound file, the falloff curve and the
 * speaker map. Nothing here fabricates a native object or keeps a serialized
 * pointer; codol_sound_native.c performs the conversion. */
#include "codol_sound.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
typedef struct {
    const uint8_t *data;
    size_t size,pos;
    int pooled; /* block 3 replay memory, which the loader aligns */
} cursor_t;
/* First hard failure of the current lookup; reset by the engine sound loader. */
static int src_fail_line;
static int src_fail(int line) { if(!src_fail_line) src_fail_line=line; return -1; }
static int src_fail0(int line) { if(!src_fail_line) src_fail_line=line; return 0; }
int CODOL_SoundSourceFailureLine(void) { return src_fail_line; }
void CODOL_ResetSoundSourceFailure(void) { src_fail_line=0; }
static int src_detail_status; static unsigned src_detail_type; static uint32_t src_detail_reference;
void CODOL_SoundSourceFailureDetail(int *status,unsigned *type,uint32_t *reference)
{ *status=src_detail_status; *type=src_detail_type; *reference=src_detail_reference; }
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
/* Serialized bytes are packed; replayed block writes align to the loader's
 * requested alignment, including after an odd-length name. */
static int take(cursor_t *c,size_t count,size_t stride,unsigned alignment,const uint8_t **out)
{
    size_t at=c->pos;
    if(!stride || !alignment) return src_fail0(__LINE__);
    if(c->pooled) at=(at+alignment-1)&~(size_t)(alignment-1);
    if(at>c->size || count>(c->size-at)/stride) return src_fail0(__LINE__);
    *out=c->data+at; c->pos=at+count*stride; return 1;
}
static int take_string(cursor_t *c,const codol_sound_view_t *view,uint32_t reference,const char **out)
{
    const uint8_t *p,*end; size_t available,offset;
    if(!reference) { *out=NULL; return 1; }
    if(reference==UINT32_MAX) {
        if(c->pos>c->size) return src_fail0(__LINE__);
        p=c->data+c->pos; available=c->size-c->pos;
        if(!(end=memchr(p,0,available))) return src_fail0(__LINE__);
        c->pos+=(size_t)(end-p)+1;
    } else {
        if(((reference-1)>>28)!=3 || !view->blocks[3].data) return src_fail0(__LINE__);
        offset=(reference-1)&0xfffffff;
        if(offset>=view->blocks[3].size) return src_fail0(__LINE__);
        p=view->blocks[3].data+offset; available=view->blocks[3].size-offset;
        if(!memchr(p,0,available)) return src_fail0(__LINE__);
    }
    *out=(const char *)p; return 1;
}
static int take_float(uint32_t bits,float *out)
{
    float value;
    memcpy(&value,&bits,4);
    if(!isfinite(value)) return src_fail0(__LINE__);
    *out=value; return 1;
}
static int pooled_cursor(const codol_sound_view_t *view,uint32_t reference,cursor_t *out)
{
    size_t offset;
    if(!reference || reference>=UINT32_MAX-1 || ((reference-1)>>28)!=3 || !view->blocks[3].data) return src_fail0(__LINE__);
    offset=(reference-1)&0xfffffff;
    if(offset>view->blocks[3].size) return src_fail0(__LINE__);
    *out=(cursor_t){view->blocks[3].data,view->blocks[3].size,offset,1}; return 1;
}
static int nested_view(codol_sound_resolver_t resolve,void *context,unsigned type,
    uint32_t reference,codol_sound_view_t *out,cursor_t *cursor)
{
    int status=resolve ? resolve(context,type,reference,out) : -2;
    if(status!=1 || !out->asset.data || out->asset.type!=type) {
        if(!src_fail_line) { src_detail_status=status; src_detail_type=type; src_detail_reference=reference; }
        return src_fail0(__LINE__);
    }
    *cursor=(cursor_t){out->asset.data,out->asset.size,0,0}; return 1;
}
/* Deduplicated data pointer: replay the serialized span the loader wrote at
 * that address instead of reading reconstructed memory, so nested loaded
 * sounds and inline curves stay reachable. */
static int span_cursor(codol_sound_resolver_t resolve,void *context,uint32_t reference,
    cursor_t *out)
{
    codol_sound_view_t span;
    memset(&span,0,sizeof(span));
    int status=resolve ? resolve(context,CODOL_SOUND_SPAN,reference,&span) : -2;
    if(status!=1 || !span.asset.data || !span.asset.size) {
        if(!src_fail_line) { src_detail_status=status; src_detail_type=CODOL_SOUND_SPAN; src_detail_reference=reference; }
        return src_fail0(__LINE__);
    }
    *out=(cursor_t){span.asset.data,span.asset.size,0,0}; return 1;
}
/* C1 0x4b80b0, whose payload relocation at +0x2c uses the length at +0x0c.
 * C1 0x73e22c hands record+4 to AIL_set_sample_info, but the shipped zones
 * show that block is forty bytes rather than the thirty-six of the retained
 * AILSOUNDINFO: +0x1c is a constant sentinel, the sample count is at +0x20
 * (twice the byte count for 4-bit ADPCM, half for 16-bit mono PCM) and the
 * 512..2048 block size at +0x24. Fields are therefore placed individually. */
static int read_loaded_sound(cursor_t *c,const codol_sound_view_t *view,codol_loaded_sound_t *out)
{
    const uint8_t *h,*payload; codol_loaded_sound_t sound={0}; uint32_t data;
    if(!take(c,1,48,4,&h)) return src_fail0(__LINE__);
    if(!take_string(c,view,u32(h),&sound.name)) return src_fail0(__LINE__);
    sound.format=u32(h+4); sound.data_length=u32(h+12); sound.rate=u32(h+16);
    sound.bits=u32(h+20); sound.channels=u32(h+24); sound.sentinel=u32(h+28);
    sound.samples=u32(h+32); sound.block_size=u32(h+36);
    data=u32(h+44);
    /* Payloads are replayed into the scratch block, which rewinds; a
     * deduplicated payload pointer therefore has no reconstructed bytes. */
    if(data<UINT32_MAX-1) { if(data) return src_fail0(__LINE__); }
    else {
        if(!take(c,sound.data_length,1,1,&payload)) return src_fail0(__LINE__);
        sound.payload=sound.data_length ? payload : NULL;
    }
    *out=sound; return 1;
}
/* C1 0x4b82b0 and evaluator 0x7375b0: 16-bit knot count at +4, then up to 16
 * (x,y) pairs interpolated by 0x618d80 with an 8-byte stride. */
static int read_curve(cursor_t *c,const codol_sound_view_t *view,codol_sound_curve_t *out)
{
    const uint8_t *h; codol_sound_curve_t curve={0}; unsigned i;
    if(!take(c,1,136,4,&h)) return src_fail0(__LINE__);
    if(!take_string(c,view,u32(h),&curve.name)) return src_fail0(__LINE__);
    curve.knot_count=h[4]|(unsigned)h[5]<<8;
    if(curve.knot_count>16) return src_fail0(__LINE__);
    for(i=0;i<2u*curve.knot_count;++i)
        if(!take_float(u32(h+8+4*i),&curve.knots[i/2][i%2])) return src_fail0(__LINE__);
    *out=curve; return 1;
}
/* C1 0x4b8240 and validity check 0x7384e0: type byte, presence byte, then
 * either a LoadedSound reference or the streamed directory/name pair. */
static int read_sound_file(cursor_t *c,const codol_sound_view_t *view,
    codol_sound_resolver_t resolve,void *context,codol_sound_file_t *out)
{
    const uint8_t *h; codol_sound_file_t file={0}; uint32_t reference;
    if(!take(c,1,12,4,&h)) return src_fail0(__LINE__);
    file.type=h[0]; file.exists=h[1];
    if(file.type==1) {
        reference=u32(h+4);
        if(!reference) return src_fail0(__LINE__);
        if(reference>=UINT32_MAX-1) {
            if(!read_loaded_sound(c,view,&file.loaded)) return src_fail0(__LINE__);
        } else {
            codol_sound_view_t nested; cursor_t inner;
            if(!nested_view(resolve,context,13,reference,&nested,&inner) ||
                !read_loaded_sound(&inner,&nested,&file.loaded)) return src_fail0(__LINE__);
        }
        file.has_loaded=1;
    } else if(file.type==2 || file.type==3) {
        if(!take_string(c,view,u32(h+4),&file.dir) ||
            !take_string(c,view,u32(h+8),&file.name)) return src_fail0(__LINE__);
    } else return src_fail0(__LINE__); /* C1 gives type 0 no reader semantics */
    *out=file; return 1;
}
static int read_alias(cursor_t *c,const codol_sound_view_t *view,codol_sound_resolver_t resolve,
    void *context,const uint8_t *r,codol_sound_alias_t *out)
{
    /* Words with no measured C1 consumer keep their record offsets instead of
     * borrowing IW3 names by position. */
    static const unsigned unmeasured[8]={52,64,68,76,80,92,96,100};
    codol_sound_alias_t alias={0}; cursor_t nested={NULL,0,0,0},*at;
    uint32_t reference; unsigned i;
    alias.record=r;
    for(i=0;i<5;++i) if(!take_string(c,view,u32(r+4*i),alias.names+i)) return src_fail0(__LINE__);
    if((reference=u32(r+20))) {
        at=c;
        if(reference!=UINT32_MAX) {
            /* A deduplicated sound file is replayed from its serialized span,
             * which keeps its loaded sound and payload reachable. */
            if(!span_cursor(resolve,context,reference,&nested)) return src_fail0(__LINE__);
            at=&nested;
        }
        if(!read_sound_file(at,view,resolve,context,&alias.file)) return src_fail0(__LINE__);
        alias.has_file=1;
    }
    alias.sequence=(int32_t)u32(r+24);
    if(!take_float(u32(r+28),alias.volume) || !take_float(u32(r+32),alias.volume+1) ||
        !take_float(u32(r+36),alias.pitch) || !take_float(u32(r+40),alias.pitch+1) ||
        !take_float(u32(r+44),alias.distance) || !take_float(u32(r+48),alias.distance+1) ||
        !take_float(u32(r+72),&alias.probability)) return src_fail0(__LINE__);
    if(alias.volume[0]<0 || alias.volume[1]<0 || alias.pitch[0]<0 || alias.pitch[1]<0 ||
        alias.distance[0]<0 || alias.distance[1]<0 || alias.probability<0) return src_fail0(__LINE__);
    alias.flags=u32(r+56); alias.priority=r[60]; alias.start_delay=(int32_t)u32(r+84);
    for(i=0;i<8;++i) if(!take_float(u32(r+unmeasured[i]),alias.unmeasured+i)) return src_fail0(__LINE__);
    if((reference=u32(r+88))) {
        if(reference>=UINT32_MAX-1) {
            if(!read_curve(c,view,&alias.curve)) return src_fail0(__LINE__);
        } else {
            codol_sound_view_t owner; cursor_t inner;
            if(!nested_view(resolve,context,12,reference,&owner,&inner) ||
                !read_curve(&inner,&owner,&alias.curve)) return src_fail0(__LINE__);
        }
        alias.has_curve=1;
    }
    if((reference=u32(r+104))) {
        const uint8_t *h;
        at=c;
        if(reference!=UINT32_MAX) {
            if(!pooled_cursor(view,reference,&nested)) return src_fail0(__LINE__);
            at=&nested;
        }
        if(!take(at,1,408,4,&h)) return src_fail0(__LINE__);
        alias.speakers.is_default=h[0];
        if(!take_string(at,view,u32(h+4),&alias.speakers.name)) return src_fail0(__LINE__);
        alias.speakers.channel_maps=h+8; alias.has_speakers=1;
    }
    *out=alias; return 1;
}
void CODOL_FreeSoundAliasList(codol_sound_alias_list_t *list)
{
    if(!list) return;
    free(list->aliases); memset(list,0,sizeof(*list));
}
int CODOL_ReadSoundAliasList(const codol_sound_view_t *view,codol_sound_resolver_t resolve,
    void *context,codol_sound_alias_list_t *out)
{
    codol_sound_alias_list_t list={0}; cursor_t c,pooled={NULL,0,0,0},*array;
    const uint8_t *h,*records;
    uint32_t reference; unsigned i;
    if(!view || !out || !view->asset.data || view->asset.type!=11) return src_fail0(__LINE__);
    c=(cursor_t){view->asset.data,view->asset.size,0,0};
    if(!take(&c,1,12,4,&h)) return src_fail0(__LINE__);
    if(!take_string(&c,view,u32(h),&list.name)) return src_fail0(__LINE__);
    list.count=u32(h+8); reference=u32(h+4);
    if(!list.count || list.count>CODOL_ASSET_LIMIT/108 || !reference) return src_fail0(__LINE__);
    if(reference==UINT32_MAX) {
        if(!take(&c,list.count,108,4,&records)) return src_fail0(__LINE__);
        array=&c;
    } else {
        /* A deduplicated alias array is replayed from the serialized span the
         * loader wrote at that address, not from reconstructed memory. */
        if(!span_cursor(resolve,context,reference,&pooled) ||
            !take(&pooled,list.count,108,4,&records)) return src_fail0(__LINE__);
        array=&pooled;
    }
    if(!(list.aliases=calloc(list.count,sizeof(*list.aliases)))) return src_fail0(__LINE__);
    for(i=0;i<list.count;++i)
        if(!read_alias(array,view,resolve,context,records+(size_t)i*108,list.aliases+i)) {
            free(list.aliases); return src_fail0(__LINE__);
        }
    /* Both the asset extent and a replayed span must be consumed exactly. */
    if(c.pos!=view->asset.size || (array!=&c && pooled.pos!=pooled.size)) {
        free(list.aliases); return src_fail0(__LINE__);
    }
    CODOL_FreeSoundAliasList(out); *out=list; return 1;
}
