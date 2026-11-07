/* Native C1 animation-command transport lifetime.
 * C1 46AFF0/46B202 increments consumed timestamp watermarks after a batch;
 * retries must retain original timestamps. This module never restamps them.
 * See docs/CODOL_DOGS_IMPLEMENTATION_20260914.md.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_actor_anim_journal.h"
#include "q_shared.h"
#include "qcommon_io.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

static char delivery_failure_text[256];
const char *codol_actor_delivery_failure;
int CODOL_ActorDeliveryFail(const char *format,...)
{
    va_list args;
    va_start(args,format);
    vsnprintf(delivery_failure_text,sizeof(delivery_failure_text),format,args);
    va_end(args);
    delivery_failure_text[sizeof(delivery_failure_text)-1]=0;
    codol_actor_delivery_failure=delivery_failure_text;
    return 0;
}
#define FAIL CODOL_ActorDeliveryFail

#define JOURNAL_CAPACITY 65536u
#define DELIVERY_HISTORY 32u
typedef struct {
    codol_actor_anim_event_t event;
    uint64_t serial;
} journal_entry_t;
typedef struct {
    codol_actor_anim_cut_t cut;
    int frame,valid;
} archive_cut_t;
typedef struct {
    codol_actor_anim_cut_t cut;
    uint32_t sequence,timeline;
    int valid;
} delivery_t;
typedef struct {
    uint32_t timeline,epoch;
    int initialized,pendingValid;
    codol_actor_anim_cut_t bootstrapCut;
    codol_actor_anim_event_t *bootstrap;
    unsigned bootstrapCount;
    codol_animcmd_t *pending;
    unsigned pendingCount;
    delivery_t pendingDelivery,history[DELIVERY_HISTORY];
} client_delivery_t;

static journal_entry_t journal[JOURNAL_CAPACITY];
static archive_cut_t archiveCuts[CODOL_ACTOR_ANIM_ARCHIVES];
static client_delivery_t clients[MAX_CLIENTS];
static uint64_t firstSerial=1,nextSerial=1;
static uint32_t mapEpoch=1,lastTime;
static int hasTime;
static uint32_t sealedTime;
static int hasCut;

static int valid_event(const codol_actor_anim_event_t *event)
{
    const codol_animcmd_t *c=&event->command;
    return event->generation && c->entity<2046 && c->time>0 && c->time<INT32_MAX &&
        c->type>=1 && c->type<=6 && c->ref<2048 && c->sub<2048 && c->arg2<4 &&
        isfinite(c->goal_weight) && c->goal_weight>=0 && c->goal_weight<=5 &&
        isfinite(c->playback_rate) && c->playback_rate>=0 && c->playback_rate<=5 &&
        isfinite(c->blend) && c->blend>=0 && c->blend<=1.7f &&
        isfinite(c->fraction) && c->fraction>=0 && c->fraction<=1;
}
static int valid_cut(const codol_actor_anim_cut_t *cut)
{
    return cut && cut->epoch==mapEpoch && cut->end>=firstSerial &&
        cut->end<=nextSerial && cut->time<INT32_MAX;
}
void CODOL_ActorAnimClientClear(unsigned client)
{
    client_delivery_t *state;
    if(client>=MAX_CLIENTS)return;
    state=&clients[client];free(state->bootstrap);free(state->pending);
    memset(state,0,sizeof(*state));
}
void CODOL_ActorAnimJournalReset(void)
{
    unsigned i;
    for(i=0;i<MAX_CLIENTS;++i)CODOL_ActorAnimClientClear(i);
    memset(archiveCuts,0,sizeof(archiveCuts));
    firstSerial=nextSerial=1;lastTime=0;hasTime=0;sealedTime=0;hasCut=0;
    if(++mapEpoch==0)mapEpoch=1;
}
int CODOL_ActorAnimJournalAppend(const codol_actor_anim_event_t *events,unsigned count)
{
    unsigned i;uint32_t time;
    if(!count)return 1;
    if(!events || count>CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT)return 0;
    time=events[0].command.time;
    if((hasTime && time<lastTime) || (hasCut && time<=sealedTime))return 0;
    /* Validate the entire batch before making any event observable. */
    for(i=0;i<count;++i)
        if(!valid_event(events+i) || events[i].command.time!=time)return 0;
    for(i=0;i<count;++i){
        journal_entry_t *entry=&journal[nextSerial%JOURNAL_CAPACITY];
        entry->event=events[i];entry->serial=nextSerial++;
    }
    if(nextSerial-firstSerial>JOURNAL_CAPACITY)firstSerial=nextSerial-JOURNAL_CAPACITY;
    lastTime=time;hasTime=1;
    return 1;
}
int CODOL_ActorAnimJournalCut(uint32_t time,codol_actor_anim_cut_t *out)
{
    if(!out || time>=INT32_MAX)return FAIL("journal cut: bad time %u",time);
    if(hasTime && time<lastTime)
        return FAIL("journal cut at %u is older than the last appended event at %u",time,lastTime);
    if(hasCut && time<sealedTime)
        return FAIL("journal cut at %u is older than the sealed cut at %u",time,sealedTime);
    sealedTime=time;hasCut=1;
    out->end=nextSerial;out->epoch=mapEpoch;out->time=time;return 1;
}
int CODOL_ActorAnimArchive(int frame,uint32_t time)
{
    archive_cut_t *slot;codol_actor_anim_cut_t cut;
    if(frame<0)return 0;
    slot=&archiveCuts[(unsigned)frame%CODOL_ACTOR_ANIM_ARCHIVES];slot->valid=0;
    if(!CODOL_ActorAnimJournalCut(time,&cut))return 0;
    slot->cut=cut;slot->frame=frame;slot->valid=1;return 1;
}
int CODOL_ActorAnimArchiveCut(int frame,uint32_t time,codol_actor_anim_cut_t *out)
{
    const archive_cut_t *slot;
    if(frame<0 || !out)return 0;
    slot=&archiveCuts[(unsigned)frame%CODOL_ACTOR_ANIM_ARCHIVES];
    if(!slot->valid || slot->frame!=frame || slot->cut.time!=time || !valid_cut(&slot->cut))
        return FAIL("archived journal cut for frame %d time %u missing (slot valid %d frame %d time %u)",
                    frame,time,slot->valid,slot->frame,slot->cut.time);
    *out=slot->cut;return 1;
}
static int add_visible(codol_animcmd_t *out,unsigned *count,
                      const codol_actor_anim_event_t *event,
                      codol_actor_anim_visible_t visible,void *context)
{
    int present=visible(event->command.entity,event->generation,context);
    if(present!=0 && present!=1)return 0;
    if(!present)return 1;
    if(*count>=CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT)return 0;
    out[(*count)++]=event->command;return 1;
}
int CODOL_ActorAnimCapture(unsigned client,uint32_t sequence,uint32_t ackSequence,
    uint32_t timeline,const codol_actor_anim_cut_t *cut,
    const codol_actor_anim_event_t *bootstrap,unsigned bootstrapCount,int bootstrapKnown,
    codol_actor_anim_visible_t visible,void *context)
{
    client_delivery_t *state;
    const delivery_t *ack;
    codol_animcmd_t *output;
    unsigned count=0,i;
    uint64_t start,serial;
    int fresh=0;
    if(client>=MAX_CLIENTS)return FAIL("journal capture: bad client %u",client);
    state=&clients[client];state->pendingValid=0;
    if(!visible)return FAIL("journal capture: no visibility callback");
    if(!valid_cut(cut))
        return FAIL("journal capture: cut invalid (epoch %u/%u end %lu first %lu next %lu time %u)",
                    cut?cut->epoch:0,mapEpoch,cut?(unsigned long)cut->end:0ul,
                    (unsigned long)firstSerial,(unsigned long)nextSerial,cut?cut->time:0);
    if(!state->initialized || state->epoch!=mapEpoch || state->timeline!=timeline){
        codol_actor_anim_event_t *saved=NULL;
        if(!bootstrapKnown)
            return FAIL("journal capture: new timeline %u for client %u without a bootstrap",timeline,client);
        if(bootstrapCount>CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT || (bootstrapCount && !bootstrap))
            return FAIL("journal capture: bootstrap of %u commands exceeds the %u per-snapshot cap",
                        bootstrapCount,CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT);
        /* Bootstrap is a state reconstruction at this exact captured time,
         * not stale animation commands borrowed from the live tree. */
        for(i=0;i<bootstrapCount;++i){
            if(!valid_event(bootstrap+i))
                return FAIL("journal capture: bootstrap command %u invalid (ent %u type %u ref %u gw %g rate %g blend %g frac %g)",
                            i,bootstrap[i].command.entity,bootstrap[i].command.type,bootstrap[i].command.ref,
                            bootstrap[i].command.goal_weight,bootstrap[i].command.playback_rate,
                            bootstrap[i].command.blend,bootstrap[i].command.fraction);
            if(bootstrap[i].command.time!=cut->time)
                return FAIL("journal capture: bootstrap command %u time %u != cut time %u",
                            i,bootstrap[i].command.time,cut->time);
        }
        if(bootstrapCount){
            saved=malloc(bootstrapCount*sizeof(*saved));if(!saved)return FAIL("journal capture: out of memory");
            memcpy(saved,bootstrap,bootstrapCount*sizeof(*saved));
        }
        CODOL_ActorAnimClientClear(client);
        state=&clients[client];state->bootstrap=saved;state->bootstrapCount=bootstrapCount;
        state->bootstrapCut=*cut;state->timeline=timeline;state->epoch=mapEpoch;state->initialized=1;
        fresh=1;
    }
    /* Backward playback requires a new timeline and matching bootstrap. */
    if(cut->time<state->bootstrapCut.time || cut->end<state->bootstrapCut.end)
        return FAIL("journal capture: cut (time %u end %lu) is behind the timeline bootstrap (time %u end %lu)",
                    cut->time,(unsigned long)cut->end,state->bootstrapCut.time,
                    (unsigned long)state->bootstrapCut.end);
    output=malloc(CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT*sizeof(*output));if(!output)return FAIL("journal capture: out of memory");
    ack=&state->history[ackSequence%DELIVERY_HISTORY];
    if(ack->valid && ack->sequence==ackSequence && ack->timeline==timeline &&
       ack->cut.epoch==mapEpoch && ack->cut.end<=cut->end && ack->cut.time<=cut->time){
        start=ack->cut.end;
    }else{
        /* MEASUREMENT (docs/CODOL_ZOMBIE_ANIM_SMOOTHNESS_20260921.md): a
         * bootstrap replayed into an ESTABLISHED timeline means the
         * acknowledged snapshot was never Published (or fell out of the
         * 32-deep history); C1 drops the copies by timestamp watermark, but
         * the cadence is part of the record. Bounded to 64 lines. */
        if(!fresh){
            static unsigned replayLines;
            if(replayLines<64){
                ++replayLines;
                Com_Printf(CON_CHANNEL_SERVER,
                    "CoDOL actor: bootstrap replayed to client %u at seq %u: acknowledged %u not in delivery history (slot seq %u valid %d timeline %u/%u)%s",
                    client,sequence,ackSequence,ack->sequence,ack->valid,ack->timeline,timeline,"\n");
            }
        }
        start=state->bootstrapCut.end;
        for(i=0;i<state->bootstrapCount;++i)
            if(!add_visible(output,&count,state->bootstrap+i,visible,context)){
                FAIL("journal capture: bootstrap replay overflowed the %u per-snapshot cap at command %u",
                     CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT,i);
                goto fail;
            }
    }
    /* Lost history is an explicit failure, never a silently incomplete pose. */
    if(start<firstSerial){
        FAIL("journal capture: history lost (start %lu < first retained %lu)",
             (unsigned long)start,(unsigned long)firstSerial);
        goto fail;
    }
    for(serial=start;serial<cut->end;++serial){
        const journal_entry_t *entry=&journal[serial%JOURNAL_CAPACITY];
        if(entry->serial!=serial){
            FAIL("journal capture: serial %lu missing from the journal ring",(unsigned long)serial);goto fail;
        }
        if(entry->event.command.time>cut->time){
            FAIL("journal capture: event %lu time %u is newer than the cut time %u (game frame ahead of snapshot time)",
                 (unsigned long)serial,entry->event.command.time,cut->time);
            goto fail;
        }
        if(!add_visible(output,&count,&entry->event,visible,context)){
            FAIL("journal capture: %u commands exceed the %u per-snapshot cap",count+1,CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT);
            goto fail;
        }
    }
    free(state->pending);state->pending=output;state->pendingCount=count;
    state->pendingDelivery.cut=*cut;state->pendingDelivery.sequence=sequence;
    state->pendingDelivery.timeline=timeline;state->pendingDelivery.valid=1;
    state->pendingValid=1;return 1;
fail:
    free(output);return 0;
}
int CODOL_ActorAnimCopy(unsigned client,uint32_t sequence,codol_animcmd_t *out,
                       unsigned capacity,unsigned *count)
{
    const client_delivery_t *state;
    if(client>=MAX_CLIENTS || !count)return FAIL("journal copy: bad arguments");
    state=&clients[client];
    if(!state->pendingValid || state->pendingDelivery.sequence!=sequence ||
       capacity<state->pendingCount || (state->pendingCount && !out))
        return FAIL("journal copy: no pending capture for sequence %u (pending %d seq %u count %u capacity %u)",
                    sequence,state->pendingValid,state->pendingDelivery.sequence,state->pendingCount,capacity);
    if(state->pendingCount)memcpy(out,state->pending,state->pendingCount*sizeof(*out));
    *count=state->pendingCount;return 1;
}
int CODOL_ActorAnimPublished(unsigned client,uint32_t sequence)
{
    client_delivery_t *state;
    if(client>=MAX_CLIENTS)return 0;
    state=&clients[client];
    if(!state->pendingValid || state->pendingDelivery.sequence!=sequence)return 0;
    state->history[sequence%DELIVERY_HISTORY]=state->pendingDelivery;
    return 1;
}
