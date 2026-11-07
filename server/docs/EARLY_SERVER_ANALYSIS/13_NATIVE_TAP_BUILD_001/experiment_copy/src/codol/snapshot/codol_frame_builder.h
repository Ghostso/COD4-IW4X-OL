#ifndef CODOL_FRAME_BUILDER_H
#define CODOL_FRAME_BUILDER_H
#include "server.h"
#include "codol_sv_frame.h"
#include "codol_sv_entities.h"
#include "codol_snapshot.h"
typedef struct codol_native_frame_s codol_native_frame_t;
/* Diagnostic for the last synchronous frame-build attempt; not wire state. */
extern const char *codol_frame_failure;
/* Step of the player/HUD overlay that rejected the frame, for the trace. */
extern const char *codol_player_failure;
/* Why the last client snapshot write overflowed, for the recovery warning. */
extern const char *codol_snapshot_failure;
#pragma pack(push, 8)
typedef struct {
    const codol_player_fields_t *player_seed;
    const codol_player_array_updates_t *array_seed;
    const codol_engine_player_bindings_t *player;
    codol_snapshot_entity_resolver_t entity_resolve;
    void *entity_context;
    codol_snapshot_client_resolver_t client_resolve;
    void *client_context;
    const codol_actor_state_t *actors;
    size_t actor_count;
    const codol_animcmd_t *commands;
    size_t command_count;
} codol_native_frame_bindings_t;
#pragma pack(pop)
/* Replace NULL/prior owned frame only after every section succeeds. Neither
 * event counter is staged here: both are properties of the states being
 * serialized. Asset publication and read-only resolvers must precede/obey this
 * transaction. Uses the native frame's exact ring spans and sequence-matched
 * HUD. Requires explicit seeds, including unmapped fields. This builds semantic
 * state; wire reachability is checked by serialization. */
int CODOL_BuildNativeFrame(codol_native_frame_t **,unsigned,uint32_t,
    const clientSnapshot_t *,const codol_native_frame_bindings_t *);
void CODOL_FreeNativeFrame(codol_native_frame_t *);
/* Own one assembled frame per recipient. A failed rebuild invalidates the
 * previous frame, including retries using the same outgoing sequence. Ammo
 * bindings are resolved from source->ps and the server's native weapon registry;
 * supplied ammo bindings and event parameters are replaced by native semantic
 * resolution, while other bindings are kept. Unsupported events reject. */
int CODOL_BuildClientNativeFrame(unsigned,uint32_t,const clientSnapshot_t *,
    const codol_native_frame_bindings_t *);
const codol_native_frame_t *CODOL_ClientNativeFrame(unsigned,uint32_t);
void CODOL_ClearClientNativeFrame(unsigned);
/* Current gameplay only; archived frames require historical metadata. */
int CODOL_BuildGameplayFrame(unsigned,uint32_t,const clientSnapshot_t *);
/* The server's event parameter resolution, shared by both event queues: the
 * generic per-event mapping plus the compound slots (EV_PLAY_FX_ON_TAG through
 * CODOL_ServerTaggedEffectToWire). Fails rather than publishing an unmapped
 * slot; count is at most four. */
int CODOL_ServerResolveEventParameters(const uint32_t *events,const uint32_t *parameters,
                                       uint32_t *out,unsigned count);
const codol_snapshot_state_t *CODOL_NativeFrameState(const codol_native_frame_t *);
const codol_player_array_updates_t *CODOL_NativeFrameUpdates(const codol_native_frame_t *);
const codol_animcmd_t *CODOL_NativeFrameCommands(const codol_native_frame_t *,size_t *);
#endif
