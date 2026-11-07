#ifndef CODOL_SV_STATE_H
#define CODOL_SV_STATE_H
#include "codol_configstrings.h"
#include "msg.h"
#include "codol_snapshot.h"
#include "codol_history.h"

/* C linkage: db_load.cpp and other C++ translation units consume these,
 * and without the guard they look for a mangled symbol that the C
 * definitions never emit. The sibling headers in this directory already
 * do this; this one was simply missed until a C++ consumer appeared. */
#ifdef __cplusplus
extern "C" {
#endif

/* Native semantic producers use CoDOL indices, never IW3 array offsets. */
codol_configstrings_t *CODOL_ServerConfigstrings(void);
/* Derive wide-position bases from published CS 16, including decimal parsing
 * and C1 rounding. Falls back to inherited CS 16; empty/absent means zero.
 * Other context members are preserved. */
int CODOL_ApplyServerPositionBase(codol_delta_context_t *);
void CODOL_ResetServerConfigstrings(void);
/* Capture the map whose archives and constant configstring table are mounted.
 * A gamestate for another map/type would make C1 load one BSP and then apply
 * another map's namespace.  The identity is immutable until map reset. */
int CODOL_SetServerMapIdentity(const char *map, const char *zone_type);
int CODOL_ServerMapIdentityMatches(const char *map, const char *zone_type);
/* "mp", "coop" or "zm" for the map whose archives are mounted; NULL before
 * map setup installs an identity. Borrowed, valid until the next map reset. */
const char *CODOL_ServerZoneType(void);
/* The mounted map's name; NULL before map setup installs an identity.
 * Borrowed, valid until the next map reset. Use it to scope per-map state:
 * a process-lifetime cache silently masks a real failure on a later map. */
const char *CODOL_ServerMapName(void);
/* Install once after map archives load; reset clears inherited and overrides.
 * NULL before installation. Constants are owned and immutable for this map. */
const codol_configstrings_t *CODOL_ServerInheritedConfigstrings(void);
/* Effective C1 menu name: override (including explicit clear), then inherited
 * fastfile value. NULL for an absent or out-of-range slot. Borrowed string. */
const char *CODOL_ServerMenuName(unsigned slot);
int CODOL_SetServerInheritedConfigstrings(const char *zone_type,size_t rows,const char *const *cells);
int CODOL_SetServerInfo(const char *map,const char *gametype,unsigned max_clients,const char *hostname);
/* Set once during full map setup before loading animlists or issuing a
 * gamestate. The four class bits are human/dog/civilian/zombie; reset clears.
 * The loader must use this same captured value as serverinfo key2482. */
int CODOL_SetServerAnimListFlags(unsigned flags);
unsigned CODOL_ServerAnimListFlags(void);
int CODOL_SetServerId(int32_t server_id);
int CODOL_PublishServerId(int32_t server_id);
/* Allocated lazily, outside retained client_t's assembly-sensitive layout.
 * Clear on client disconnect and server reset. Never share ACK bases between
 * slots. Returned pointers are invalid after the corresponding reset. */
codol_history_t *CODOL_ClientSnapshotHistory(unsigned client_number);
/* Whether the client's ACK names the exact retained base which the next
 * snapshot preparation will use.  A missing base requires an origin seed. */
int CODOL_ClientSnapshotHasBase(unsigned client_number, uint32_t acknowledged,
                                uint32_t next_sequence, unsigned flags);
void CODOL_ResetClientSnapshotHistory(unsigned client_number);
void CODOL_ResetSnapshotHistories(void);
/* Bind prepared state to one complete outgoing message, including its EOF.
 * Owns a byte copy until finish/discard/reset; commit requires an exact match.
 * Preparation derives context.position_base from the published CoDOL map
 * center before history quantization/serialization; failure preserves context.
 * Begin/recovery must discard it before reusing a message buffer. */
int CODOL_PrepareClientSnapshot(unsigned client_number, msg_t *msg,
    const codol_snapshot_state_t *state, uint32_t acknowledged,
    const codol_player_array_updates_t *updates, const codol_animcmd_t *commands,
    size_t command_count, unsigned flags, int rov, codol_delta_context_t *context);
int CODOL_ClientSnapshotPrepared(unsigned client_number, const msg_t *msg, uint32_t sequence);
/* Any prepared frame, including one whose message/sequence no longer matches. */
int CODOL_ClientSnapshotPending(unsigned client_number);
int CODOL_FinishClientSnapshot(unsigned client_number, const msg_t *msg, uint32_t sequence, int accepted);
void CODOL_DiscardClientSnapshot(unsigned client_number);
int CODOL_WriteServerGamestate(msg_t *msg, const char *map, const char *zone_type,
                               const char *gametype, unsigned max_clients, uint32_t sequence,
                               uint32_t client_number, uint32_t checksum_feed,const char *hostname);
/* Append a complete snapshot including EOF after reliable ACK/commands. On
 * failure marks overflow without advancing the engine message or context.
 * Caller must not append another EOF or commit snapshot history on failure. */
int CODOL_WriteServerSnapshot(msg_t *msg, const codol_snapshot_state_t *state,
                              const codol_snapshot_state_t *base,
                              const codol_player_array_updates_t *updates,
                              const codol_animcmd_t *commands, size_t command_count,
                              unsigned flags, int read_origin_velocity,
                              codol_delta_context_t *context);
/* Select an exact ACK base (otherwise full), prepare owned history and append.
 * Success requires FinishHistory(state->sequence, transport_accepted) after the
 * send attempt. Failed appends discard only the newly prepared frame. */
int CODOL_PrepareServerSnapshot(msg_t *msg, codol_history_t *history,
                                const codol_snapshot_state_t *state, uint32_t acknowledged,
                                const codol_player_array_updates_t *updates,
                                const codol_animcmd_t *commands, size_t command_count,
                                unsigned flags, int read_origin_velocity,
                                codol_delta_context_t *context);
#ifdef __cplusplus
}
#endif
#endif
