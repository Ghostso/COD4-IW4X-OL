/* Native dog animation owner and captured pose bootstrap.
 * Uses retained engine structures by their actual native definition, never C1
 * process offsets. C1 command semantics: 443E90 -> 63C520 / 63BBE0 / 63C310.
 * Staged pending actor/archive/frame integration.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "q_shared.h"
#include "dobj.h"
#include "xassets/xanims.h"
#include "codol_dog_animation.h"
#include "cscr_stringlist.h"
#include "g_shared.h"
#include <math.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <limits.h>
#define FAIL CODOL_ActorDeliveryFail

extern XAnimInfo g_xAnimInfo[4096];
extern int XAnimSetGoalWeight(DObj *,unsigned,float,float,float,unsigned,unsigned,int);
extern int XAnimSetCompleteGoalWeight(DObj *,unsigned,float,float,float,unsigned,unsigned,int);
extern int XAnimSetGoalWeightKnob(DObj *,unsigned,float,float,float,unsigned,int);
extern int CODOL_XAnimSetCompleteGoalWeightKnob(DObj *,unsigned,float,float,float,int);
extern int CODOL_XAnimSetCompleteGoalWeightKnobNotified(DObj *,unsigned,float,float,float,int,unsigned);
extern void XAnimClearTreeGoalWeights(struct XAnimTree_s *,unsigned,float);
extern void XAnimSetTime(struct XAnimTree_s *,unsigned,float);
/* These assertions refer to this executable's retained _xanim allocation and
 * state accesses (pool0x38000/4096), not an assumed cross-version layout. */
typedef char native_info_size[(sizeof(XAnimInfo)==56)?1:-1];
typedef char native_state_offset[(offsetof(XAnimInfo,state)==24)?1:-1];
typedef char native_goal_offset[(offsetof(XAnimInfo,state.goalWeight)==40)?1:-1];

static int scalar(float value,float maximum)
{ return isfinite(value) && value>=0 && value<=maximum; }
static int valid_node(const codol_dog_anim_node_t *n)
{
    return n->ref<2048 && n->leaf<=1 && n->sync_root<=1 && n->looping<=1 && scalar(n->current_weight,5) &&
        scalar(n->goal_weight,5) && scalar(n->remaining_blend,1.7f) &&
        scalar(n->playback_rate,5) && scalar(n->fraction,1);
}
typedef struct {
    const struct XAnimTree_s *tree;
    codol_dog_anim_pose_t pose;
    unsigned char visited[4096];
    uint16_t poseIndex[4096];
} capture_t;
static int capture_branch(capture_t *capture,unsigned index,unsigned parent,unsigned depth)
{
    while(index){
        const XAnimInfo *info;
        codol_dog_anim_node_t *node;
        if(index>=4096 || depth>=CODOL_DOG_ANIM_NODES || capture->visited[index])
            return FAIL("pose capture: XAnimInfo %u (depth %u) out of range or revisited",index,depth);
        capture->visited[index]=1;info=&g_xAnimInfo[index];
        if(info->parent!=parent)
            return FAIL("pose capture: XAnimInfo %u parent %u != walked parent %u",index,info->parent,parent);
        if(info->animIndex>=capture->tree->anims->size)
            return FAIL("pose capture: XAnimInfo %u anim ref %u exceeds tree size %u",index,info->animIndex,capture->tree->anims->size);
        if(capture->pose.count>=CODOL_DOG_ANIM_NODES)
            return FAIL("pose capture: more than %u live nodes",CODOL_DOG_ANIM_NODES);
        node=&capture->pose.nodes[capture->pose.count++];
        capture->poseIndex[index]=capture->pose.count;
        node->parent=parent?capture->poseIndex[parent]:0;
        node->ref=info->animIndex;
        node->leaf=capture->tree->anims->entries[node->ref].numAnims==0;
        node->sync_root=!node->leaf && (capture->tree->anims->entries[node->ref].u.animParent.flags&4)!=0;
        node->looping=node->leaf?capture->tree->anims->entries[node->ref].u.parts->bLoop!=0:
            (capture->tree->anims->entries[node->ref].u.animParent.flags&1)!=0;
        node->current_weight=info->state.weight;
        node->goal_weight=info->state.goalWeight;
        node->remaining_blend=info->state.goalTime;
        node->playback_rate=info->state.rate;
        node->fraction=info->state.time;
        if(!valid_node(node))
            return FAIL("pose capture: XAnimInfo %u ref %u state out of wire range (weight %g goal %g goalTime %g rate %g time %g)",
                        index,node->ref,node->current_weight,node->goal_weight,node->remaining_blend,
                        node->playback_rate,node->fraction);
        if(info->children && !capture_branch(capture,info->children,index,depth+1))return 0;
        index=info->next;
    }
    return 1;
}
int CODOL_DogAnimCapture(const struct XAnimTree_s *tree,unsigned entity,
    uint32_t generation,uint32_t time,codol_dog_anim_pose_t *out)
{
    capture_t capture;
    if(!out || !tree || !tree->anims || !tree->anims->size ||
       tree->anims->size>2048 || entity>=2046 || !generation || !time || time>=INT32_MAX)
        return FAIL("pose capture: bad source (ent %u gen %u time %u tree %p anims %u)",
                    entity,generation,time,(const void*)tree,(tree&&tree->anims)?tree->anims->size:0u);
    memset(&capture,0,sizeof(capture));capture.tree=tree;
    capture.pose.entity=(uint16_t)entity;capture.pose.generation=generation;capture.pose.time=time;
    if(!capture_branch(&capture,tree->children,0,0))return 0;
    *out=capture.pose;return 1;
}
static codol_actor_anim_event_t event_for(const codol_dog_anim_pose_t *pose,unsigned type,unsigned ref)
{
    codol_actor_anim_event_t event;
    memset(&event,0,sizeof(event));event.generation=pose->generation;
    event.command.time=pose->time;event.command.entity=pose->entity;
    event.command.type=(uint8_t)type;event.command.ref=(uint16_t)ref;
    return event;
}
typedef struct {
    const codol_dog_anim_pose_t *pose;
    codol_actor_anim_event_t events[CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT];
    unsigned count;
} bootstrap_t;
static int emit_bootstrap(bootstrap_t *b,codol_actor_anim_event_t event)
{
    if(b->count>=CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT)
        return FAIL("pose bootstrap: ent %u needs more than %u commands",b->pose->entity,CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT);
    b->events[b->count++]=event;return 1;
}
static int bootstrap_children(bootstrap_t *,unsigned,unsigned);
static int bootstrap_node(bootstrap_t *b,unsigned index,int restart,float fade,int willClone)
{
    const codol_dog_anim_node_t *n=&b->pose->nodes[index];
    codol_actor_anim_event_t e=event_for(b->pose,3,n->ref);
    float phase=n->fraction;
    if(willClone){
        /* Native XAnimRestart keeps the old branch fading to zero and inserts
         * its reset clone before it. C1 63C380 follows the same sync-root path.
         * A loop at phase0 is pose-equivalent to phase1, which also preserves
         * the nonzero-time restart predicate after wire quantization. */
        if(!n->leaf && !n->sync_root)
            return FAIL("pose bootstrap: ent %u ref %u: restarted clone is neither a leaf nor a sync root",b->pose->entity,n->ref);
        if(n->goal_weight!=0 || n->current_weight<=0 || n->remaining_blend<=0)
            return FAIL("pose bootstrap: ent %u ref %u: old clone not fading (weight %g goal %g blend %g)",
                        b->pose->entity,n->ref,n->current_weight,n->goal_weight,n->remaining_blend);
        if(phase<0.5f/31.0f){
            if(!n->looping)return FAIL("pose bootstrap: ent %u ref %u: non-looping clone at phase 0",b->pose->entity,n->ref);
            phase=1.0f;
        }
    }
    e.command.goal_weight=n->current_weight;e.command.playback_rate=n->playback_rate;
    if(restart){
        e.command.arg2=2;e.command.blend=fade;
        if(!emit_bootstrap(b,e))return 0;
        e.command.arg2=0;e.command.blend=0;
    }
    if(!emit_bootstrap(b,e))return 0;
    e.command.goal_weight=n->goal_weight;e.command.blend=n->remaining_blend;
    if(!emit_bootstrap(b,e))return 0;
    if(!bootstrap_children(b,index+1,0))return 0;
    /* C1 SetTime63C310 accepts both leaf and synchronization nodes. Internal
     * phase is required: restart promotes a leaf to its nearest sync root. */
    e=event_for(b->pose,6,n->ref);e.command.fraction=phase;
    return emit_bootstrap(b,e);
}
static int bootstrap_children(bootstrap_t *b,unsigned parent,unsigned unused)
{
    unsigned i,j,k,group[CODOL_DOG_ANIM_NODES],count;
    (void)unused;
    for(i=0;i<b->pose->count;++i){
        const codol_dog_anim_node_t *first=&b->pose->nodes[i];
        float priorFade=0;int restart=0;
        if(first->parent!=parent)continue;
        /* Entries are sorted by ref in each actual native sibling list. Only
         * the newest member of a group starts reconstruction. */
        for(j=0;j<i;++j)if(b->pose->nodes[j].parent==parent &&
            b->pose->nodes[j].ref==first->ref)break;
        if(j<i)continue;
        count=0;
        for(j=i;j<b->pose->count;++j)if(b->pose->nodes[j].parent==parent &&
            b->pose->nodes[j].ref==first->ref)group[count++]=j;
        /* Oldest first; each restart freezes that prior branch and creates
         * the next native incarnation. Zero-weight fading branches need no
         * renderer reconstruction, but remain intact in the archived pose. */
        for(k=count;k>0;--k){
            unsigned index=group[k-1];
            const codol_dog_anim_node_t *n=&b->pose->nodes[index];
            int older=(k>1);
            if(older && n->current_weight==0 && n->goal_weight==0)continue;
            if(!bootstrap_node(b,index,restart,priorFade,older))return 0;
            priorFade=n->remaining_blend;restart=1;
        }
    }
    return 1;
}
int CODOL_DogAnimBootstrap(const codol_dog_anim_pose_t *pose,
    codol_actor_anim_event_t *out,unsigned capacity,unsigned *count)
{
    bootstrap_t *b;unsigned i;int result=0;
    if(!pose || !count || !out || pose->count>CODOL_DOG_ANIM_NODES ||
       !pose->generation || pose->entity>=2046 || !pose->time || pose->time>=INT32_MAX)
        return FAIL("pose bootstrap: bad archived pose");
    for(i=0;i<pose->count;++i)
        if(!valid_node(&pose->nodes[i]) || pose->nodes[i].parent>i)
            return FAIL("pose bootstrap: ent %u archived node %u invalid",pose->entity,i);
    b=calloc(1,sizeof(*b));if(!b)return FAIL("pose bootstrap: out of memory");b->pose=pose;
    if(!emit_bootstrap(b,event_for(pose,1,0)) || !bootstrap_children(b,0,0))goto done;
    if(b->count>capacity){FAIL("pose bootstrap: ent %u needs %u commands, %u left in this snapshot",pose->entity,b->count,capacity);goto done;}
    memcpy(out,b->events,b->count*sizeof(*out));*count=b->count;result=1;
done:
    free(b);return result;
}
int CODOL_DogAnimGoal(DObj *obj,unsigned entity,uint32_t generation,
    uint32_t time,unsigned ref,float goal_weight,float blend,float playback_rate,
    int complete,int restart)
{
    codol_actor_anim_event_t event;
    if(!obj || !obj->tree || !obj->tree->anims || ref>=obj->tree->anims->size ||
       ref>=2048 || entity>=2046 || !generation || !time || time>=INT32_MAX ||
       !scalar(goal_weight,5) || !scalar(blend,1.7f) || !scalar(playback_rate,5) ||
       (complete!=0 && complete!=1) || (restart!=0 && restart!=1))return 0;
    memset(&event,0,sizeof(event));event.generation=generation;
    event.command.entity=(uint16_t)entity;event.command.time=time;
    /* C1 encoding (see apply_batch): type is plain/knob, arg2 bit0 is
     * complete. This entry point never knobs, so it is always type 3 and
     * carries `complete` in bit 0. It previously wrote type=4 for complete,
     * which C1 executes as a knob. */
    event.command.ref=(uint16_t)ref;event.command.type=3;
    event.command.arg2=(uint8_t)((restart<<1)|(complete?1:0));
    event.command.goal_weight=goal_weight;event.command.blend=blend;
    event.command.playback_rate=playback_rate;
    return CODOL_DogAnimApplyBatch(obj,&event,1);
}
static int apply_batch(DObj *obj,const codol_actor_anim_event_t *events,unsigned count,
    unsigned notifyEvent,unsigned notifyName)
{
    unsigned i;
    if(!obj || !obj->tree || !obj->tree->anims || !events || !count ||
       count>CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT)return 0;
    for(i=0;i<count;++i){
        const codol_animcmd_t *c=&events[i].command;
        if(events[i].generation!=events[0].generation || c->entity!=events[0].command.entity ||
           c->ref>=obj->tree->anims->size || c->arg2&~3u ||
           ((c->type==1 || c->type==6) && c->arg2) ||
           (c->type!=1 && c->type!=3 && c->type!=4 && c->type!=6))return 0;
    }
    if(!CODOL_ActorAnimJournalAppend(events,count))return 0;
    /* _xanim XAnimSetGoalWeightNode_50 returns0 for notifyName0 or a real leaf.
     * The ordinary error2 requires an invalid internal sync notify, excluded
     * by the notified entry point before publication. */
    for(i=0;i<count;++i){
        const codol_animcmd_t *c=&events[i].command;
        unsigned channel=i==notifyEvent?notifyName:0;
        int result=0;
        if(c->type==1)XAnimClearTreeGoalWeights(obj->tree,c->ref,c->blend);
        else if(c->type==6)XAnimSetTime(obj->tree,c->ref,c->fraction);
        /* C1 0x443e90 is the authority for this encoding. Its type dispatch is
         * jmp *0x444140(,%eax,4) with eax = type-1, and the table reads
         * 0x443f1d 0x443f35 0x443f4d 0x443fed 0x44408f 0x444126 (re-verified
         * byte for byte). Type 3's arm calls 0x63c520/0x63c730, type 4's calls
         * 0x63bbe0/0x63b8b0, and BOTH type-5 targets (0x63b9c0, 0x63bad0) open
         * by calling 0x63bbe0 -- exactly what the retained
         * XAnimSetGoalWeightKnobAll does with XAnimSetGoalWeightKnob. So
         * 0x63bbe0 is Knob, 0x63c520 is the plain setter, and the fields are
         *     type      = plain (3) / knob (4) / knob-all (5)
         *     arg2 bit0 = complete
         *     arg2 bit1 = restart
         * which is also T5's own (type, flags) split.
         *
         * This read type as plain/complete and bit0 as knob. The two readings
         * agree on (3,0) and (4,1) and DISAGREE on (3,1) and (4,0) -- and
         * codol_dog_states.cpp::completeGoal emitted (4,0), so on every
         * completeGoal the server set a complete goal weight where C1 performs
         * a knob. The emitters are corrected alongside this so each keeps its
         * intended meaning: setGoal (3,0), completeGoal (3,1),
         * completeKnob (4,1). */
        else if(c->type==4 && (c->arg2&1))result=CODOL_XAnimSetCompleteGoalWeightKnobNotified(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,c->arg2>>1,channel);
        else if(c->type==4)result=XAnimSetGoalWeightKnob(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,c->arg2>>1);
        else if(c->arg2&1)result=XAnimSetCompleteGoalWeight(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,0,c->arg2>>1);
        else result=XAnimSetGoalWeight(obj,c->ref,c->goal_weight,c->blend,c->playback_rate,channel,0,c->arg2>>1);
        if(result!=0)Com_Error(ERR_DROP,"CoDOL dog XAnim operation violated validated leaf/goal return contract");
    }
    return 1;
}
int CODOL_DogAnimApplyBatch(DObj *obj,const codol_actor_anim_event_t *events,unsigned count)
{ return apply_batch(obj,events,count,UINT_MAX,0); }

/* Retained XAnimSetGoalWeightNode_60..180 accepts a synced group when
 * an active descendant with positive goal weight exists. A preceding complete
 * leaf goal in this transaction guarantees that ancestry before publication;
 * absent proof, refuse rather than publish and then fail mid-transaction. */
static int notified_target_proven(DObj *obj,const codol_actor_anim_event_t *events,
                                  unsigned index)
{
    const XAnim_s *tree=obj->tree->anims;
    unsigned target=events[index].command.ref,i;
    if(target>=tree->size)return 0;
    if(!tree->entries[target].numAnims)return tree->entries[target].u.parts!=NULL;
    if(!(tree->entries[target].u.animParent.flags&3))return 0;
    for(i=0;i<index;++i){
        const codol_animcmd_t *c=&events[i].command;
        unsigned ancestor=c->ref,depth=0,j;
        /* The proof is a leaf goal with positive weight that reaches the
         * target through weighted ancestors: a COMPLETE goal (arg2 bit0, plain
         * or knob) raises every ancestor, a limited one only itself, so a
         * limited goal proves its direct parent alone.
         *
         * This used to test `type==4`, which was "complete" before a845790d
         * adopted C1's encoding (type 3 plain / 4 knob, arg2 bit0 complete)
         * and moved completeGoal from (4,0) to (3,1). From then on no batch
         * carried a proof, so every notified knob on a synced parent was
         * refused -- dog move_start (run_start under run_start_knob), move_run
         * and traverse_through_hole (run under run_knob) -- and setanimstate
         * raised "could not publish its native C1 tree transaction" the first
         * time a dog moved. */
        if((c->type!=3 && c->type!=4) || c->ref>=tree->size || tree->entries[c->ref].numAnims ||
           !(c->goal_weight>0) || !(c->playback_rate>0))continue;
        if(!(c->arg2&1) && tree->entries[c->ref].parent!=target)continue;
        while(ancestor && ancestor<tree->size && ancestor!=target && depth++<tree->size)
            ancestor=tree->entries[ancestor].parent;
        if(ancestor!=target)continue;
        /* Conservative: a subsequent clear, a goal on the same node, or a knob
         * (which zeroes siblings anywhere) could cancel this proof. Reject
         * those batches until a richer preflight exists. Under the old
         * reading arg2 bit0 was the knob bit; it is now `complete`, which
         * zeroes nothing, and a knob is type 4 or 5. */
        for(j=i+1;j<index;++j){
            const codol_animcmd_t *later=&events[j].command;
            if(later->type==1 || later->ref==c->ref || later->type==4 || later->type==5)break;
        }
        if(j==index)return 1;
    }
    return 0;
}

int CODOL_DogAnimApplyNotifiedBatch(DObj *obj,const codol_actor_anim_event_t *events,
    unsigned count,unsigned notifyEvent,const char *channel)
{
    const codol_animcmd_t *c;
    unsigned name,entity;
    int result;
    if(!obj || !obj->tree || !obj->tree->anims || !events || !count ||
       count>CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT || notifyEvent>=count ||
       !channel || !*channel)return 0;
    c=&events[notifyEvent].command;entity=c->entity;
    if(entity>=MAX_GENTITIES || !g_entities[entity].r.inuse ||
       CODOL_ACTOR_INCARNATION(g_entities[entity].useCount)!=events[notifyEvent].generation ||
       obj->entnum!=entity+1 || Com_GetServerDObj(entity)!=obj ||
       (c->type!=3 && c->type!=4) || !(c->goal_weight>0) ||
       !(c->playback_rate>0) || !notified_target_proven(obj,events,notifyEvent))return 0;
    name=SL_GetString(channel,0);
    if(!name)return 0;
    if(name>UINT16_MAX){SL_RemoveRefToString(name);return 0;}
    result=apply_batch(obj,events,count,notifyEvent,name);
    SL_RemoveRefToString(name);
    return result;
}

int CODOL_DogAnimApplyNotifiedLeafBatch(DObj *obj,const codol_actor_anim_event_t *events,
    unsigned count,unsigned notifyEvent,const char *channel)
{
    const codol_animcmd_t *c;
    unsigned name,entity;
    int result;
    if(!obj || !obj->tree || !obj->tree->anims || !events || !count ||
       count>CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT || notifyEvent!=count-1 ||
       !channel || !*channel)return 0;
    c=&events[notifyEvent].command;entity=c->entity;
    /* DObj entnum is the actual server notification receiver plus one.
     * A captured/recycled DObj must never notify a different live actor. */
    if(entity>=MAX_GENTITIES || !g_entities[entity].r.inuse ||
       CODOL_ACTOR_INCARNATION(g_entities[entity].useCount)!=events[notifyEvent].generation ||
       obj->entnum!=entity+1 || Com_GetServerDObj(entity)!=obj ||
       (c->type!=3 && c->type!=4) || (c->arg2&1) ||
       c->ref>=obj->tree->anims->size ||
       obj->tree->anims->entries[c->ref].numAnims ||
       !obj->tree->anims->entries[c->ref].u.parts ||
       !(c->goal_weight>0) || !(c->playback_rate>0))return 0;
    name=SL_GetString(channel,0);
    if(!name)return 0;
    if(name>UINT16_MAX){SL_RemoveRefToString(name);return 0;}
    result=apply_batch(obj,events,count,notifyEvent,name);
    /* Successful XAnimSetGoalWeightNode acquired its own reference; failure
     * before journal append never mutates the native tree. */
    SL_RemoveRefToString(name);
    return result;
}

typedef struct {
    int frame,valid;
    uint32_t time;
    unsigned count;
    codol_dog_anim_pose_t *poses;
} dog_anim_archive_t;
static dog_anim_archive_t poseArchive[CODOL_ACTOR_ANIM_ARCHIVES];
void CODOL_DogAnimArchiveReset(void)
{
    unsigned i;
    for(i=0;i<CODOL_ACTOR_ANIM_ARCHIVES;++i)free(poseArchive[i].poses);
    memset(poseArchive,0,sizeof(poseArchive));
}
int CODOL_DogAnimArchiveStore(int frame,uint32_t time,
    const codol_dog_anim_capture_source_t *sources,unsigned count)
{
    dog_anim_archive_t *slot;
    codol_dog_anim_pose_t *poses=NULL;
    unsigned i,j;
    if(frame<0)return 0;
    slot=&poseArchive[(unsigned)frame%CODOL_ACTOR_ANIM_ARCHIVES];
    slot->valid=0;
    if(count>32 || (count && !sources) || !time || time>=INT32_MAX)return 0;
    if(count){poses=malloc(count*sizeof(*poses));if(!poses)return 0;}
    for(i=0;i<count;++i){
        for(j=0;j<i;++j)if(sources[j].entity==sources[i].entity)goto fail;
        if(!CODOL_DogAnimCapture(sources[i].tree,sources[i].entity,
            sources[i].generation,time,poses+i))goto fail;
    }
    free(slot->poses);slot->poses=poses;slot->frame=frame;slot->time=time;
    slot->count=count;slot->valid=1;return 1;
fail:
    free(poses);return 0;
}
const codol_dog_anim_pose_t *CODOL_DogAnimArchiveFind(int frame,uint32_t time,
    unsigned entity,uint32_t generation)
{
    const dog_anim_archive_t *slot;
    unsigned i;
    if(frame<0 || !generation || entity>=2046){FAIL("pose archive: bad lookup");return NULL;}
    slot=&poseArchive[(unsigned)frame%CODOL_ACTOR_ANIM_ARCHIVES];
    if(!slot->valid || slot->frame!=frame || slot->time!=time){
        FAIL("pose archive: frame %d time %u not archived (slot valid %d frame %d time %u)",frame,time,slot->valid,slot->frame,slot->time);
        return NULL;
    }
    for(i=0;i<slot->count;++i)
        if(slot->poses[i].entity==entity && slot->poses[i].generation==generation)
            return &slot->poses[i];
    FAIL("pose archive: frame %d has no pose for ent %u gen %u",frame,entity,generation);
    return NULL;
}
