#ifdef CODOL_SERVER
#include "server.h"
#include "codol_sv_entities.h"
#include "codol_weapon_lock.h"
#include "codol_playerstate_ext.h"
#include "codol_entitystate_ext.h"
#include <stdlib.h>
#include <string.h>

int codol_entity_failure_number=-1, codol_entity_failure_type=-1;
const char *codol_entity_failure_stage;
/* Why the resolver refused the entity that is about to be dropped. The
 * resolver writes it; this file only prints it. A dropped entity does not fail
 * the frame, so the frame-rejection trace never reports these - without this
 * the log said only "type N cannot be seeded" and a whole killstreak could go
 * missing with no stated reason. Empty when the resolver did not say. */
char codol_entity_seed_reason[160];
/* The snapshot area's own share of an entity-slot reset: the event epochs the
 * collectors below read. CODOL_ResetEntityEventGeneration in
 * codol_sv_entity_events.c calls these after it has reset the vehicle, model,
 * missile and glass state that lives outside this area. Keeping the epoch
 * reset here is what lets the collectors be linked without the rest of the
 * server behind them. */
void CODOL_ResetEntityEventEpoch(unsigned number)
{
    CODOL_EntityStateExtClearEntity(number);
    CODOL_PlayerStateExtClearClientEvents(number);
}
void CODOL_ResetEntityEventEpochs(void)
{
    unsigned i;
    /* Live slots only. A captured snapshot or an archived frame keeps the
     * epoch it was taken with, so re-sampling a frame after a slot recycles
     * still serializes the history that frame actually had. Dropping the
     * captured tables too is a teardown, and belongs to
     * CODOL_ResetEntityEventGenerations. */
    for(i=0;i<(unsigned)ENTITYNUM_WORLD;++i) CODOL_EntityStateExtClearEntity(i);
    for(i=0;i<32;++i) CODOL_PlayerStateExtClearClientEvents(i);
}
/* The strict form: every entity must seed. Kept for the callers and tests
 * that treat an unseedable entity as a fault rather than as one dropped
 * entity. */
int CODOL_CollectServerEntities(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context)
{
    /* Collect into a buffer of our own so a short result never reaches the
     * caller's array. This form's contract is all or nothing: on failure the
     * destination is left exactly as it was. */
    codol_entity_state_t *staged=NULL;
    size_t emitted=0; int ok;
    if(count>0 && (size_t)count<=capacity && out) {
        staged=malloc((size_t)count*sizeof(*staged));
        if(!staged) { codol_entity_failure_stage="allocation"; return 0; }
    }
    ok=CODOL_CollectServerEntitiesEmitted(first,count,staged?staged:out,capacity,resolve,context,&emitted);
    if(ok && emitted!=(size_t)count) ok=0;
    if(ok && staged) memcpy(out,staged,(size_t)count*sizeof(*staged));
    free(staged);
    return ok;
}
int CODOL_CollectCurrentServerEntities(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context)
{
    return CODOL_CollectServerEntities(first,count,out,capacity,resolve,context);
}

/* Collect the ring's entities, dropping any the resolver cannot seed.
 *
 * A seed failure used to fail the whole array, which failed the frame, which
 * meant one entity of a type with no seed arm stopped every client receiving
 * snapshots at all. ET_VEHICLE is the known case. Dropping the entity instead
 * keeps the match running and costs only that entity, and the ascending-number
 * ordering the writer needs is preserved because skipping cannot break it.
 * Structural faults - a bad ring span, a bad number, allocation - still fail.
 * *emitted receives the number actually written. */
int CODOL_CollectServerEntitiesEmitted(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context,size_t *emitted)
{
    return CODOL_CollectServerEntitiesForClient(first,count,out,capacity,resolve,context,emitted,-1);
}
/* Report once per parent number: which parent went missing, and for whom. */
static void report_orphan(int child,int type,int parent,int local_client,const char *action)
{
    static int reported[64]; static unsigned reported_count; unsigned k;
    for(k=0;k<reported_count;++k) if(reported[k]==parent) return;
    if(reported_count>=64) return;
    reported[reported_count++]=parent;
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL link: entity %d (type %d) %s: its parent %d is not in the snapshot"
        " (viewer client %d); further reports for this parent are silenced\n",
        child,type,action,parent,local_client);
}
int CODOL_CollectServerEntitiesForClient(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context,size_t *emitted,int local_client)
{
    codol_entity_state_t *states=NULL;
    codol_snapshot_entity_bindings_t *saved=NULL;
    int *source_index=NULL;
    int i,kept=0,previous_number=-1;
    int ring_count=svsHeader.numSnapshotEntities,next=svsHeader.nextSnapshotEntities;
    codol_entity_failure_number=codol_entity_failure_type=-1;
    codol_entity_failure_stage="ring span";
    if(emitted) *emitted=0;
    if(count<0 || count>ENTITYNUM_WORLD || (size_t)count>capacity || first<0 || next<0 ||
       first>next || (int64_t)first+count>next) return 0;
    if(!count) { codol_entity_failure_stage=NULL; return 1; }
    if(!out || !resolve || !svsHeader.snapshotEntities || ring_count<=0 ||
       count>ring_count || first<(int64_t)next-ring_count) return 0;
    codol_entity_failure_stage="allocation";
    states=malloc((size_t)count*sizeof(*states));
    saved=malloc((size_t)count*sizeof(*saved));
    source_index=malloc((size_t)count*sizeof(*source_index));
    if(!states || !saved || !source_index) goto fail;
    for(i=0;i<count;++i) {
        const entityState_t *source=&svsHeader.snapshotEntities[((int64_t)first+i)%ring_count];
        codol_snapshot_entity_bindings_t bindings={0};
        codol_entity_failure_number=source->number; codol_entity_failure_type=source->eType;
        codol_entity_failure_stage="identity or seed";
        codol_entity_seed_reason[0]='\0';
        /* Validate the original span, including entries that will be omitted.
         * A rejected seed must not hide a duplicate or descending ring ID. */
        if(source->number<0 || source->number>=ENTITYNUM_WORLD ||
           source->number<=previous_number) goto fail;
        previous_number=source->number;
        if(!resolve(context,source,&bindings)) {
            /* One entity the resolver has no arm for. Report the type once and
             * leave it out; the alternative is no snapshot for anyone. */
            static int reported[64]; static unsigned reported_count; unsigned k; int seen=0;
            for(k=0;k<reported_count;++k) if(reported[k]==source->eType) { seen=1; break; }
            if(!seen && reported_count<64) {
                reported[reported_count++]=source->eType;
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "CoDOL entity type %d cannot be seeded; dropping it from snapshots"
                    " (entity %d%s%s)\n",
                    source->eType,source->number,
                    codol_entity_seed_reason[0] ? ": " : "",
                    codol_entity_seed_reason);
            }
            continue;
        }
        states[kept]=bindings.state;
        codol_entity_failure_stage="overlay";
        /* The event counter comes from this ring slot's own epoch, so nothing
         * is staged or committed per recipient here. */
        /* Apply suppression inside the first common overlay. Converting the
         * full queue first can reject precisely the event being omitted. XOR
         * preserves invalid high mask bits for validation. */
        /* An entity whose state cannot be converted is dropped, like an
         * unseedable one. Failing the frame instead cost every recipient that
         * could see it all snapshots: a dead human's dropped composed weapon
         * (item index >= 128) blacked out the victim through the death view
         * and killcam, then forced full frames (VPS 2026-09-27, 14 s of
         * 25-byte reliable-only packets after each death). */
        if(!CODOL_OverlayEngineEntityVisible(states+kept,source,bindings.event_parameters,
             bindings.event_suppressed_slots ^ 15u) ||
           (source->eType==ET_PLAYER &&
            !CODOL_OverlayEnginePlayerEntityWeapons(states+kept,source,
                bindings.primary_weapon))) {
            static int reported[64]; static unsigned reported_count; unsigned k; int seen=0;
            for(k=0;k<reported_count;++k) if(reported[k]==source->eType) { seen=1; break; }
            if(!seen && reported_count<64) {
                reported[reported_count++]=source->eType;
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "CoDOL entity type %d could not be converted; dropping such entities from snapshots"
                    " (first: entity %d, index %d)\n",
                    source->eType,source->number,source->index);
            }
            continue;
        }
        saved[kept]=bindings; source_index[kept]=i;
        ++kept;
    }
    /* A linked child must never reference a parent this snapshot does not
     * carry: C1 0x4419a0 then prints "Entity #%i of type %i: parent ent #%i
     * not in snapshot." every frame and resolves no parent. The visibility
     * pass (sv_snapshot.c) already adds every parent a recipient may see, so
     * what remains here is a parent that must stay hidden (hide() sets the
     * whole clientMask; the UAV rig is the standing case), one the resolver
     * dropped just above, or a full list. Publish such a child unlinked for
     * this frame: the native link producer keeps its world pose in trBase,
     * so it still draws where the server placed it. The recipient's own
     * player is never in its entity list and C1 resolves it from the
     * predicted player instead (0x4404a0), so it counts as present. Only if
     * the unlinked conversion itself fails is the child dropped, and a
     * dropped child can orphan a grandchild, hence the repeat. */
    if(kept) {
        unsigned char present[MAX_GENTITIES], unlinked_done[MAX_GENTITIES];
        int changed=1,k;
        codol_entity_failure_stage="link parents";
        memset(present,0,sizeof(present)); memset(unlinked_done,0,sizeof(unlinked_done));
        for(k=0;k<kept;++k) {
            const entityState_t *source=&svsHeader.snapshotEntities[((int64_t)first+source_index[k])%ring_count];
            present[source->number]=1;
        }
        while(changed) {
            int write=0;
            changed=0;
            for(k=0;k<kept;++k) {
                const entityState_t *source=&svsHeader.snapshotEntities[((int64_t)first+source_index[k])%ring_count];
                unsigned info; float link_origin[3],link_angles[3]; int parent;
                if(unlinked_done[source->number] ||
                   !CODOL_EntityStateLink(source,&info,link_origin,link_angles) || !(info&65535u)) {
                    states[write]=states[k]; saved[write]=saved[k]; source_index[write]=source_index[k]; ++write;
                    continue;
                }
                parent=(int)(info&65535u)-1;
                if(parent==local_client || (parent<MAX_GENTITIES && present[parent])) {
                    states[write]=states[k]; saved[write]=saved[k]; source_index[write]=source_index[k]; ++write;
                    continue;
                }
                {
                    codol_entity_state_t unlinked=saved[k].state;
                    unlinked_done[source->number]=1;
                    if(CODOL_OverlayEngineEntityVisibleUnlinked(&unlinked,source,saved[k].event_parameters,
                           saved[k].event_suppressed_slots ^ 15u) &&
                       (source->eType!=ET_PLAYER ||
                        CODOL_OverlayEnginePlayerEntityWeapons(&unlinked,source,saved[k].primary_weapon))) {
                        report_orphan(source->number,source->eType,parent,local_client,"published unlinked");
                        states[write]=unlinked; saved[write]=saved[k]; source_index[write]=source_index[k]; ++write;
                    } else {
                        report_orphan(source->number,source->eType,parent,local_client,"dropped");
                        present[source->number]=0; changed=1;
                    }
                }
            }
            kept=write;
        }
    }
    if(kept) memcpy(out,states,(size_t)kept*sizeof(*out));
    if(emitted) *emitted=(size_t)kept;
    free(states); free(saved); free(source_index); codol_entity_failure_stage=NULL; return 1;
fail:
    free(states); free(saved); free(source_index); return 0;
}
#endif
