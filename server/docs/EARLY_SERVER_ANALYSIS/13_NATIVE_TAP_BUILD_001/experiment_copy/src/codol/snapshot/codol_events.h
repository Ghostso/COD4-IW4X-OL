#ifndef CODOL_EVENTS_H
#define CODOL_EVENTS_H
#include <stdint.h>
/* Return -1 for unsupported semantics; never copy an IW3 numeric event ID. */
int CODOL_EventToWire(unsigned engine_event);
int CODOL_EntityTypeToWire(unsigned engine_type);
/* Parameter semantics are independent from event-name/ID matching.
 * 1=resolved, 0=unimplemented event, -1=invalid known parameter/output.
 * Output is untouched unless resolved. NONE canonicalizes its unused value. */
int CODOL_EventParameterToWire(unsigned engine_event,uint32_t parameter,uint32_t *out);
/* Four physical queue slots, matching the engine's arrays. No partial output
 * when any event lacks a verified parameter mapping or has an invalid value. */
int CODOL_ResolveEventParameters(const uint32_t events[4],const uint32_t parameters[4],uint32_t out[4]);
/* The player-state event ring, unlike an entity event, carries C1's own
 * EV_SV_FIRE_WEAPON family for a shot. bg_eventNames at 0xcd81d8 names 30
 * EV_FIRE_WEAPON, 31 EV_FIRE_WEAPON_LASTSHOT and 43 EV_SV_FIRE_WEAPON; the
 * producer C1's own PM uses for the ring is 0x41b8b0, which picks base 43 or,
 * when BG_ClipEmpty (0x41e3f0) reports the magazine emptied and the weapon is
 * not fire type 5, base 44 -- and adds 2 for the left hand (0x41b8db..0x41b8f3).
 * 30/31 stay the entity-event names a third-person world report uses, which is
 * why CODOL_EventToWire keeps them. Anything that is not a fire event is
 * delegated unchanged. */
int CODOL_PlayerFireEventToWire(unsigned engine_event,unsigned hand,unsigned last_shot);
/* CoDOL-only internal event: C1 event 9 EV_STANCE_INVALID, queued with
 * parameter 3 when a prone body turn is refused (0x41462f). The retained
 * BGEvent enum has no counterpart; 140..142 are the dive/mantle events. */
#define CODOL_EV_STANCE_INVALID 143
#endif
