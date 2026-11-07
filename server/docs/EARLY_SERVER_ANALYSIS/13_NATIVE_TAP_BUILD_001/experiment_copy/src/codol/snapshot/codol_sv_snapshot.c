/* Engine message bridge for the native CoDOL snapshot serializer. */
#include "codol_sv_state.h"
#include "codol_actor_delivery.h"
#include "codol_glass_world.h"
#include "codol_frame_builder.h"
#include <stdio.h>
#include "codol_sv_frame.h"
#include "codol_frame_builder.h"
#include "codol_matchdata.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include "sys_cod4defs.h"
#include <ctype.h>
#include <errno.h>
int CODOL_ApplyServerPositionBase(codol_delta_context_t *context)
{
    const char *value=CODOL_GetConfigstring(CODOL_ServerConfigstrings(),CODOL_CS_MAP_CENTER);
    float center[3]={0}; unsigned i;
    if(!context) return 0;
    if(!value) value=CODOL_GetConfigstring(CODOL_ServerInheritedConfigstrings(),CODOL_CS_MAP_CENTER);
    if(value && *value) {
        for(i=0;i<3;++i) {
            char *end;
            while(isspace((unsigned char)*value)) ++value;
            errno=0; center[i]=strtof(value,&end);
            if(end==value || errno==ERANGE || (*end && !isspace((unsigned char)*end))) return 0;
            value=end;
        }
        while(isspace((unsigned char)*value)) ++value;
        if(*value) return 0;
    }
    return CODOL_SetDeltaPositionBase(context,center);
}
static codol_history_t *client_histories[MAX_CLIENTS];
static struct {
    const msg_t *message;
    const void *data;
    unsigned char *serialized;
    int size;
    uint32_t sequence;
    uint32_t match_time;
    int match_sent;
} client_pending[MAX_CLIENTS];

static void clear_pending(unsigned n)
{
    free(client_pending[n].serialized);
    memset(&client_pending[n], 0, sizeof(client_pending[n]));
}

void CODOL_DiscardClientSnapshot(unsigned client_number)
{
    if (client_number >= MAX_CLIENTS) return;
    if (client_pending[client_number].message)
        CODOL_FinishHistory(client_histories[client_number], client_pending[client_number].sequence, 0);
    clear_pending(client_number);
}
int CODOL_ClientSnapshotPrepared(unsigned n, const msg_t *msg, uint32_t sequence)
{
    return n < MAX_CLIENTS && msg && msg->data && !msg->overflowed && !msg->splitData &&
        msg->cursize >= 0 && msg->maxsize >= msg->cursize && client_pending[n].serialized &&
        client_pending[n].message == msg && client_pending[n].data == msg->data &&
        client_pending[n].size == msg->cursize && client_pending[n].sequence == sequence &&
        !memcmp(client_pending[n].serialized, msg->data, (size_t)msg->cursize);
}
int CODOL_ClientSnapshotPending(unsigned n)
{ return n<MAX_CLIENTS && client_pending[n].message!=NULL; }
int CODOL_FinishClientSnapshot(unsigned n, const msg_t *msg, uint32_t sequence, int accepted)
{
    int result;
    if (accepted != 1 || !CODOL_ClientSnapshotPrepared(n, msg, sequence)) {
        CODOL_DiscardClientSnapshot(n); return 0;
    }
    result = CODOL_FinishHistory(client_histories[n], sequence, 1);
    /* Only a fully serialized snapshot advances the animation journal's
     * delivered range; building a pending one must not. */
    if(result) CODOL_ActorAnimPublished(n,sequence);
    if(result && client_pending[n].match_sent)
        CODOL_ClientMatchDataSent(n,client_pending[n].match_time);
    clear_pending(n);
    return result;
}
const char *codol_snapshot_failure;
int CODOL_PrepareClientSnapshot(unsigned n, msg_t *msg,
    const codol_snapshot_state_t *state, uint32_t acknowledged,
    const codol_player_array_updates_t *updates, const codol_animcmd_t *commands,
    size_t command_count, unsigned flags, int rov, codol_delta_context_t *context)
{
    codol_history_t *history;
    codol_delta_context_t next;
    unsigned char *serialized = NULL;
    if(!context) { if(msg) msg->overflowed=qtrue; return 0; }
    next=*context;
    /* Reserve the copy before serialization so allocation failure cannot leave
     * a newly prepared frame or partially advance the caller's message. */
    if ((codol_snapshot_failure="client/pending/message state",
         n >= MAX_CLIENTS || client_pending[n].message || !msg || !msg->data ||
         msg->overflowed || msg->splitData || msg->cursize < 0 ||
         msg->maxsize <= 0 || msg->maxsize > INT_MAX/8 || msg->maxsize < msg->cursize) ||
        (codol_snapshot_failure="position base", !CODOL_ApplyServerPositionBase(&next)) ||
        (codol_snapshot_failure="serialized copy allocation", !(serialized = malloc((size_t)msg->maxsize))) ||
        (codol_snapshot_failure="history allocation", !(history = CODOL_ClientSnapshotHistory(n))) ||
        (codol_snapshot_failure="prepare server snapshot",
         !CODOL_PrepareServerSnapshot(msg, history, state, acknowledged, updates,
                                    commands, command_count, flags, rov, &next))) {
        free(serialized);
        if (msg) msg->overflowed = qtrue;
        return 0;
    }
    if(!(flags&2) && CODOL_ClientMatchDataDue(n,(uint32_t)context->server_time)) {
        codol_client_matchdata_t *match=CODOL_ClientMatchData();codol_msg_t wire;
        CODOL_MsgWriteInit(&wire,msg->data,(size_t)msg->maxsize-1); /* reserve EOF */
        wire.size=msg->cursize>0 ? (size_t)msg->cursize-1 : 0;
        if(!match || msg->cursize<=0 || msg->data[msg->cursize-1]!=5 ||
           !CODOL_WriteClientMatchDataSection(&wire,match->name,match->record,sizeof(match->record))) {
            codol_snapshot_failure="match data section";
            CODOL_FinishHistory(history,state->sequence,0);free(serialized);
            msg->overflowed=qtrue;return 0;
        }
        wire.capacity++;CODOL_WriteByte(&wire,5);msg->cursize=(int)wire.size;
        client_pending[n].match_sent=1;client_pending[n].match_time=(uint32_t)context->server_time;
    }
    client_pending[n].message = msg; client_pending[n].data = msg->data;
    memcpy(serialized, msg->data, (size_t)msg->cursize);
    client_pending[n].serialized = serialized;
    client_pending[n].size = msg->cursize; client_pending[n].sequence = state->sequence;
    *context=next;
    return 1;
}

codol_history_t *CODOL_ClientSnapshotHistory(unsigned client_number)
{
    if (client_number >= MAX_CLIENTS) return NULL;
    if (!client_histories[client_number]) client_histories[client_number] = CODOL_CreateHistory();
    return client_histories[client_number];
}
int CODOL_ClientSnapshotHasBase(unsigned n, uint32_t acknowledged,
                                uint32_t next_sequence, unsigned flags)
{
    codol_history_t *history;
    if (n >= MAX_CLIENTS || (flags & 8u) ||
        !(history = client_histories[n]) || !CODOL_HistoryLatestSequence(history)) return 0;
    return CODOL_FindHistoryBase(history, acknowledged, next_sequence) != NULL ||
           CODOL_HistoryBaseline(history) != NULL;
}
void CODOL_ResetClientSnapshotHistory(unsigned client_number)
{
    if (client_number >= MAX_CLIENTS) return;
    CODOL_AcknowledgeClientMatchData(client_number);
    CODOL_ClearClientSnapshotHud(client_number);
    CODOL_ActorDeliveryClear(client_number);
    CODOL_ClearClientNativeFrame(client_number);
    CODOL_DiscardClientSnapshot(client_number);
    CODOL_DestroyHistory(client_histories[client_number]);
    client_histories[client_number] = NULL;
}
void CODOL_ResetSnapshotHistories(void)
{
    unsigned i;
    for (i = 0; i < MAX_CLIENTS; ++i) CODOL_ResetClientSnapshotHistory(i);
}
int CODOL_WriteServerSnapshot(msg_t *msg, const codol_snapshot_state_t *state,
                              const codol_snapshot_state_t *base,
                              const codol_player_array_updates_t *updates,
                              const codol_animcmd_t *commands, size_t command_count,
                              unsigned flags, int rov, codol_delta_context_t *context)
{
    codol_msg_t wire;
    codol_delta_context_t next;
    codol_snapshot_state_t captured;
    codol_glass_wire_piece_t glass[CODOL_GLASS_MAX_PIECES];
    unsigned glass_count=0;
    if (!state) goto fail;
    captured=*state;
    if (!CODOL_GlassWorldEnsureMap()) {
        codol_snapshot_failure="glass map state unavailable"; goto fail;
    }
    if (!CODOL_GlassWorldCapture(glass,CODOL_GLASS_MAX_PIECES,&glass_count)) {
        codol_snapshot_failure="glass capture failed"; goto fail;
    }
    captured.glass=glass;captured.glass_count=glass_count;
    state=&captured;
    if (!msg || !msg->data || msg->overflowed || msg->splitData || msg->cursize < 0 ||
        msg->maxsize < msg->cursize || msg->maxsize > INT_MAX/8 || !context) goto fail;
    next = *context;
        CODOL_MsgWriteInit(&wire, msg->data+msg->cursize, msg->maxsize-msg->cursize);
    if (!CODOL_WriteSnapshot(&wire, state, base, updates, commands, command_count, flags, rov, &next)) {
        static char why[200];
        snprintf(why,sizeof(why),"CODOL_WriteSnapshot: %s (written %u of %u bytes room, cursize %d, base %s, entities %u, clients %u)",
            CODOL_WriteSnapshotFailure() ? CODOL_WriteSnapshotFailure() : "?",(unsigned)wire.size,
            (unsigned)(msg->maxsize-msg->cursize),msg->cursize,base ? "delta" : "full",
            (unsigned)state->entity_count,(unsigned)state->client_count);
        codol_snapshot_failure=why; goto fail;
    }
    msg->cursize += wire.size;
    msg->bit = msg->cursize*8;
    *context = next;
    return 1;
fail:
    if (msg) msg->overflowed = qtrue;
    return 0;
}

static int write_server_snapshot_delta(msg_t *msg, const codol_snapshot_state_t *state,
                              const codol_snapshot_state_t *base, uint32_t delta_number,
                              const codol_player_array_updates_t *updates,
                              const codol_animcmd_t *commands, size_t command_count,
                              unsigned flags, int rov, codol_delta_context_t *context)
{
    codol_msg_t wire;
    codol_delta_context_t next;
    codol_snapshot_state_t captured;
    codol_glass_wire_piece_t glass[CODOL_GLASS_MAX_PIECES];
    unsigned glass_count=0;
    if (!state) goto fail;
    captured=*state;
    if (!CODOL_GlassWorldEnsureMap()) {
        codol_snapshot_failure="glass map state unavailable"; goto fail;
    }
    if (!CODOL_GlassWorldCapture(glass,CODOL_GLASS_MAX_PIECES,&glass_count)) {
        codol_snapshot_failure="glass capture failed"; goto fail;
    }
    captured.glass=glass;captured.glass_count=glass_count;
    state=&captured;
    if (!msg || !msg->data || msg->overflowed || msg->splitData || msg->cursize < 0 ||
        msg->maxsize < msg->cursize || msg->maxsize > INT_MAX/8 || !context) goto fail;
    next = *context;
    CODOL_MsgWriteInit(&wire, msg->data+msg->cursize, msg->maxsize-msg->cursize);
    if (!CODOL_WriteSnapshotDeltaNumber(&wire, state, base, delta_number, updates,
            commands, command_count, flags, rov, &next)) {
        codol_snapshot_failure="CODOL_WriteSnapshotDeltaNumber"; goto fail;
    }
    msg->cursize += wire.size; msg->bit = msg->cursize*8; *context = next;
    return 1;
fail:
    if (msg) msg->overflowed=qtrue;
    return 0;
}

int CODOL_PrepareServerSnapshot(msg_t *msg, codol_history_t *history,
                                const codol_snapshot_state_t *state, uint32_t acknowledged,
                                const codol_player_array_updates_t *updates,
                                const codol_animcmd_t *commands, size_t command_count,
                                unsigned flags, int rov, codol_delta_context_t *context)
{
    const codol_snapshot_state_t *base, *ack_base, *baseline;
    uint32_t delta_number = 0;
    int baseline_frame;
    if (!state || !history || !context || flags > 255) goto fail;
    ack_base = flags & 8u ? NULL : CODOL_FindHistoryBase(history, acknowledged, state->sequence);
    baseline = CODOL_HistoryBaseline(history);
    baseline_frame = (flags & 8u) != 0 ||
        (CODOL_HistoryLatestSequence(history) == 0) || !ack_base;
    /* 2026-09-15: a client that requests a non-delta snapshot mid-match
     * (deltaMessage -1 after an overflow-recovery message) must receive a
     * flag-8 frame. C1 0x49dd7e refreshes its saved baseline only on flag
     * 8, and a deltaNum-0/flag-0 frame decoded against that stale copy
     * produced team 7 and the 0x00aea51c strlen crash (DMP9B39, DMPF1E1). */
    if (baseline_frame) {
        base = NULL; flags |= 8u; rov = 1;
    } else if (ack_base) {
        base = ack_base; flags &= ~8u;
        delta_number = state->sequence - ack_base->sequence;
    } else {
        /* C1 0x49d9ce selects its persistent noDeltaSnapshot here. Encode
         * every section against our matching pinned copy while leaving the
         * wire deltaNum zero. The leading player-base bit remains one. */
        base = baseline; flags &= ~8u;
    }
    if (!(baseline_frame ?
          CODOL_PrepareBaselineHistory(history, state, rov, context) :
          CODOL_PrepareHistory(history, state, base->sequence, rov, context))) {
        static char why[240];
        snprintf(why,sizeof(why),"prepare history: %s",CODOL_HistoryFailure());
        codol_snapshot_failure=why; goto fail;
    }
    /* Serialize the reached state, not the raw one. The skip tests compare
     * against the held (already quantized) base, so a raw position or angle
     * never equals it and ~81% of entity-frames were resent every frame even
     * while static. The codecs produce the same wire value for a quantized
     * input. Measured with 12 bots: average delta 910 B -> 530 B. */
    if (CODOL_HistoryPendingState(history)) state = CODOL_HistoryPendingState(history);
    if (write_server_snapshot_delta(msg, state, base, delta_number, updates,
            commands, command_count, flags, rov, context)) return 1;
    CODOL_FinishHistory(history, state->sequence, 0);
fail:
    if (msg) msg->overflowed = qtrue;
    return 0;
}
