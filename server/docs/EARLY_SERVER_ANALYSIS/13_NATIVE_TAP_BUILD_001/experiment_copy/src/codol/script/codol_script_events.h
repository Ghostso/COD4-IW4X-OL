/* C1's scripted player event queue: the server-side half.
 *
 * C1 keeps two player event queues. The predicted one (playerState 0x0f0
 * sequence, 0x0f4 events, 0x104 parameters, cursor 0x114) is filled by pmove
 * and is the one the retained IW3 playerState also has. The scripted one
 * (0x118 sequence, 0x120 events, 0x130 parameters, cursor 0x11c) is filled by
 * the server: G_AddEvent @0x00572d30 takes its player branch at 0x00572da5,
 * writes client+0x120[seq & 3] and client+0x130[seq & 3], and advances
 * client+0x118 modulo 2048.
 *
 * Both queues are consumed the same way at both ends:
 *   client   CG_CheckPlayerstateEvents @0x0045d680 replays the predicted queue
 *            at 0x45d6d0 and the scripted one at 0x45d744.
 *   server   C1's playerState-to-entityState transfer @0x0040d000 calls the
 *            same helper @0x0040cf10 twice - once with
 *            (events 0x0f4, parms 0x104, sequence 0x0f0, cursor 0x114) and once
 *            with (0x120, 0x130, 0x118, 0x11c). The helper dispatches each
 *            event to the pmove handler table (0xcd816c), then filters it
 *            against two event lists and appends what survives to the entity
 *            queue at ent+0xb0/+0xb4/+0xc4.
 *
 * The retained BG_PlayerStateToEntityState (_bg_misc.asm:2199..2330) is that
 * helper for the predicted queue: it calls pmoveHandlers[type].event -
 * G_PlayerEvent on the server - then skips event 0x1f, the rest of
 * serverOnlyEvents, event 6 and the rest of singleClientEvents, and appends the
 * survivors to the entity state. CODOL_TransferScriptEventsToEntity is the
 * second call C1 makes, for the queue the retained playerState does not have.
 */
#ifndef CODOL_SCRIPT_EVENTS_H
#define CODOL_SCRIPT_EVENTS_H
#include "player.h"
#include "entity.h"
#include "codol_playerstate.h"
#include "codol_playerstate_ext.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Publish the scripted queue of this playerState into C1 fields 0x118,
 * 0x120..0x12c and 0x130..0x13c. The parameters are supplied already resolved,
 * because the compound mappings some events need (EV_PLAY_FX_ON_TAG through
 * CODOL_ServerTaggedEffectToWire) are server state this translation layer must
 * not reach into; codol_sv_gameframe.c resolves them with the same code the
 * entity queue uses. Atomic: anything unpublishable leaves the destination
 * unchanged and fails rather than publishing an empty queue over it. */
int CODOL_OverlayEngineScriptEvents(codol_player_fields_t *wire, const playerState_t *ps,
                                    const uint32_t parameters[CODOL_PS_SCRIPT_EVENT_SLOTS]);
/* Same queue with recipient-visible physical slots. Preserve sequence and
 * native history; write event/parameter zero only for excluded wire slots. */
int CODOL_OverlayEngineScriptEventsVisible(codol_player_fields_t *,const playerState_t *,
    const uint32_t parameters[CODOL_PS_SCRIPT_EVENT_SLOTS],unsigned visibleSlots);

/* The second transfer C1 performs. Called from the retained
 * BG_PlayerStateToEntityState with its own handler-table index, after the
 * predicted queue has been transferred: dispatches each pending scripted event
 * to the same pmove handler, applies the same two filters, appends the
 * survivors to the entity queue and counts them into that entity state's event
 * epoch. Moves the scripted transfer cursor. */
void CODOL_TransferScriptEventsToEntity(playerState_t *ps, entityState_t *es, int handlers);

#ifdef __cplusplus
}
#endif
#endif
