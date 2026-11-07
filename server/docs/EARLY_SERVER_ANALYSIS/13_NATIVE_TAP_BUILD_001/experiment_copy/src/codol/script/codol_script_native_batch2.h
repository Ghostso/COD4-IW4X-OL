/*
 * Missing GSC natives, batch 2: spawn-point validation and tagged-effect
 * shutdown. Both are map-startup / gameplay builtins the alpha MP script
 * corpus calls and this tree has no binding or implementation for.
 *
 * Reference handlers (IW4 iw4x.exe, the primary reference):
 *   canspawn      builtin table 0x0079aba0  name 0x0072f3bc  handler 0x005f7290
 *   stopfxontag   builtin table 0x0079a638  name 0x006daac0  handler 0x005f38e0
 * Both table entries carry developer word 0, so neither is developer-only.
 *
 * See src/codol_script_native_batch2.c for the decoded contracts and for the
 * per-call evidence, and obj/claude-workers/gsc-native-batch2-report.md for
 * the registry / event-map integration this worker does not own.
 */
#ifndef __CODOL_SCRIPT_NATIVE_BATCH2_H__
#define __CODOL_SCRIPT_NATIVE_BATCH2_H__

#ifdef CODOL_SERVER

#include "q_shared.h"
#include "bg.h"

#ifdef __cplusplus
extern "C" {
#endif

/* canspawn( <origin> )
 *
 * Boolean: does a player-sized volume placed at <origin> fit without being
 * entirely inside solid. IW4 0x005f7290 traces the volume against itself
 * (start == end == origin) and returns the negation of trace.allsolid. */
void CODOL_Scr_CanSpawn(void);

/* stopfxontag( <effect>, <entity>, <tagname> )
 *
 * Stops the looping effect <effect> that is playing on <tagname> of <entity>.
 * Global function, not a method: the entity is parameter 1, exactly like the
 * already-bound playfxontag. */
void CODOL_Scr_StopFxOnTag(void);

/* The engine-side event id this module queues for stopfxontag.
 *
 * The retained bg.h enumeration has no stop-fx event at all - IW3 never had
 * one - so the id cannot be taken from it today. C1's own bg_eventNames table
 * at VA 0x00cd81d8 does name the event: slot 89 EV_PLAY_FX_ON_TAG (which
 * codol_event_map.inc already maps) and slot 90 EV_STOP_FX_ON_TAG. The wire
 * value is therefore 90, established directly from C1 and not inferred from
 * IW4's own numbering (IW4 queues 0x55 for this builtin, which is a different
 * table and must not be copied).
 *
 * The retained assembly hardcodes numeric event ids (Scr_PlayFXOnTag queues a
 * literal 0x38, _g_utils_mp.asm's G_AddEvent takes them as integers), so the
 * enumerator MUST be appended at the END of the bg.h enum: inserting it next
 * to EV_PLAY_FX_ON_TAG would renumber every later event and desync the
 * assembly. Appending gives it exactly the value defined here, which is why
 * this module can name it before the parent applies that one-line patch.
 * Until codol_event_map.inc gains its "case ... return 90;" line the event is
 * dropped by CODOL_EventToWire rather than published wrongly; the exact
 * shared patches are in the worker report. */
#define CODOL_EV_STOP_FX_ON_TAG ((int)EV_STOP_FX_ON_TAG)

/* C1 slot for the event above, from bg_eventNames 0x00cd81d8[90]. Supplied so
 * the parent's codol_event_map.inc patch and this module cannot drift. */
#define CODOL_WIRE_EV_STOP_FX_ON_TAG 90

#ifdef __cplusplus
}
#endif

#endif /* CODOL_SERVER */
#endif
