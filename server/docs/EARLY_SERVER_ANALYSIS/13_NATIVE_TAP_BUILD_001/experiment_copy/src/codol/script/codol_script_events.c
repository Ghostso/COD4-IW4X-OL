/* Scripted player event queue: publication and the transfer C1 performs for it.
 * See codol_script_events.h for the C1 provenance of both. */
#include "codol_script_events.h"
#include "codol_events.h"
#include "codol_entitystate_ext.h"
#include "g_shared.h"
#include <string.h>

/* pmoveHandlers[type] is a { trace, event } pair; the server's event handler is
 * G_PlayerEvent (_bg_pmove.asm:8698). The retained transfer calls it for every
 * event it walks, before any filtering, and so does C1's helper at 0x0040cf55. */
extern void *pmoveHandlers[];

static int filtered(unsigned event)
{
    /* C1 40cf6c..40cf9e: zero, initial server-only 23 followed by
     * c3ee20 until zero; initial single-client 6 followed by c3ef7c.
     * Compare the ID actually published by the scripted player queue, not
     * an IW3 numeric ID or its different player-predicted firing variant. */
    switch (CODOL_EventToWire(event)) {
    case 0:
    case 23: case 22: case 28: case 16:
    case 43: case 44: case 45: case 46:
    case 6: case 7: case 8: case 9: case 51:
    case 14: case 15: case 17: case 54:
    case 108: case 109: case 110: case 111: case 112:
    case 63: case 64: case 65:
        return 1;
    default:
        /* Unsupported mappings remain visible to snapshot validation rather
         * than being silently discarded by the filter. */
        return 0;
    }
}

int CODOL_OverlayEngineScriptEvents(codol_player_fields_t *wire, const playerState_t *ps,
                                    const uint32_t parameters[CODOL_PS_SCRIPT_EVENT_SLOTS])
{
    codol_player_fields_t out;
    uint32_t events[CODOL_PS_SCRIPT_EVENT_SLOTS], params[CODOL_PS_SCRIPT_EVENT_SLOTS];
    int mapped[CODOL_PS_SCRIPT_EVENT_SLOTS];
    unsigned sequence, found = 0, i, j;
    if (!wire || !ps || !parameters) return 0;
    if (!CODOL_PlayerStateScriptEventQueue(ps, &sequence, events, params)) return 0;
    for (i = 0; i < CODOL_PS_SCRIPT_EVENT_SLOTS; ++i) {
        mapped[i] = CODOL_EventToWire(events[i]);
        /* C1 carries eleven bits per slot in 0x120../0x130..; the queue itself
         * holds the native values, so the width limit applies here, at the
         * translation, and not to what the producer or the archive stored. */
        if (mapped[i] < 0 || mapped[i] > 2047 || parameters[i] > 2047) return 0;
    }
    out = *wire;
    for (j = 0; j < CODOL_PLAYER_FIELDS; ++j) {
        unsigned offset = CODOL_PlayerField(j)->offset;
        if (offset == 0x118) { out.field[j] = sequence; found |= 1; }
        else for (i = 0; i < CODOL_PS_SCRIPT_EVENT_SLOTS; ++i) {
            if (offset == 0x120u + 4u * i) { out.field[j] = (uint32_t)mapped[i]; found |= 2u << i; }
            else if (offset == 0x130u + 4u * i) { out.field[j] = parameters[i]; found |= 0x20u << i; }
        }
    }
    if (found != 0x1ff) return 0;
    *wire = out;
    return 1;
}

int CODOL_OverlayEngineScriptEventsVisible(codol_player_fields_t *wire,const playerState_t *ps,
    const uint32_t parameters[CODOL_PS_SCRIPT_EVENT_SLOTS],unsigned visibleSlots)
{
    codol_player_fields_t out;
    unsigned i,j;
    if(!wire || (visibleSlots & ~15u)) return 0;
    out = *wire;
    /* Keep validation independent of the recipient, including excluded slots. */
    if(!CODOL_OverlayEngineScriptEvents(&out,ps,parameters)) return 0;
    for(j=0;j<CODOL_PLAYER_FIELDS;++j) {
        unsigned offset = CODOL_PlayerField(j)->offset;
        for(i=0;i<CODOL_PS_SCRIPT_EVENT_SLOTS;++i) {
            if(visibleSlots & (1u << i)) continue;
            if(offset == 0x120u+4u*i || offset == 0x130u+4u*i)
                out.field[j] = 0;
        }
    }
    *wire = out;
    return 1;
}

void CODOL_TransferScriptEventsToEntity(playerState_t *ps, entityState_t *es, int handlers)
{
    uint32_t events[CODOL_PS_SCRIPT_EVENT_SLOTS], params[CODOL_PS_SCRIPT_EVENT_SLOTS];
    void (*handler)(int, int);
    unsigned count, i, slot;
    if (!ps || !es) return;
    count = CODOL_PlayerStateScriptEventsToTransfer(ps, events, params);
    if (!count) {
        CODOL_PlayerStateScriptEventsTransferred(ps);
        es->eventParm = 0;
        return;
    }
    handler = (handlers >= 0 && handlers < 4) ? (void (*)(int, int))pmoveHandlers[handlers * 2 + 1] : NULL;
    for (i = 0; i < count; ++i) {
        /* The handler runs for every event, filtered or not, exactly where the
         * retained transfer runs it (_bg_misc.asm:2243..2254) and where C1's
         * helper runs it (0x0040cf55). On the server that is G_PlayerEvent. */
        if (handler) handler(es->number, (int)events[i]);
        if (filtered(events[i])) continue;
        /* The entity queue takes the native values. The retained loop reads the
         * player parameter back as a byte, which the CoDOL entity parameter
         * resolvers cannot use for compound indices; C1's helper copies the
         * whole word (0x0040cf48/0x0040cf4e) and so does this. */
        slot = (unsigned)es->eventSequence & 3u;
        memcpy(&es->events[slot], &events[i], sizeof(uint32_t));
        memcpy(&es->eventParms[slot], &params[i], sizeof(uint32_t));
        es->eventSequence = (es->eventSequence + 1) & 0xff;
        CODOL_EntityStateEventAdded(es);
    }
    CODOL_PlayerStateScriptEventsTransferred(ps);
    /* C1 40d054 clears the standalone parameter after both queue transfers,
     * including their gameplay callbacks, not before invoking those callbacks. */
    es->eventParm = 0;
}
