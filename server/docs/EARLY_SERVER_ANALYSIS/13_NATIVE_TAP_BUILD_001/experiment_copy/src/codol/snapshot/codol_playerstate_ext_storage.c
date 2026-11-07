/* Binds the playerState extension to the server's playerState storages.
 *
 * codol_playerstate_ext.c resolves a playerState to its extension block by
 * address, which needs the three arrays those states live in. Keeping the
 * binding here means the resolver itself references no engine global: the
 * server build gets level.clients / svs.clients / svs.cachedSnapshotClients,
 * and a harness that exercises the extension binds its own arrays instead of
 * dragging in the whole server state.
 *
 * level.clients is the retained g_clients reservation (G_InitGame,
 * _g_main_mp.asm:619), so it is NULL until the game module starts; the
 * resolver treats a NULL base as "no storage of that class". */
#include "codol_playerstate_ext.h"
#include "codol_entitystate_ext.h"
#include "g_shared.h"
#include "server.h"
#include "sys_cod4defs.h"

const void *CODOL_PlayerStateExtLiveBase(unsigned *count)
{
    if (count) *count = level.clients ? MAX_CLIENTS : 0;
    return level.clients;
}

const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count)
{
    if (count) *count = MAX_CLIENTS;
    return svs.clients;
}

const void *CODOL_PlayerStateExtArchiveBase(unsigned *count)
{
    if (count)
        *count = (unsigned)(sizeof(svs.cachedSnapshotClients) / sizeof(svs.cachedSnapshotClients[0]));
    return svs.cachedSnapshotClients;
}

/* The entity storages, bound the same way: the live gentity array, the
 * snapshot entity ring the writer serializes from, and the cached-snapshot
 * entity ring that holds the delayed history. */
const void *CODOL_EntityStateExtLiveBase(unsigned *count)
{
    /* Match the expanded native entity allocation and extension table. The
     * retained IW3 limit excluded valid CoDOL slots 1022..2045. */
    if (count) *count = ENTITYNUM_WORLD;
    return g_entities;
}

const void *CODOL_EntityStateExtSnapshotBase(unsigned *count)
{
    if (count)
        *count = (unsigned)(sizeof(svs.snapshotEntities) / sizeof(svs.snapshotEntities[0]));
    return svs.snapshotEntities;
}

const void *CODOL_EntityStateExtArchiveBase(unsigned *count)
{
    if (count)
        *count = (unsigned)(sizeof(svs.cachedSnapshotEntities) / sizeof(svs.cachedSnapshotEntities[0]));
    return svs.cachedSnapshotEntities;
}
