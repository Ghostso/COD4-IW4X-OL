/* Death / killcam / follow lifecycle trace.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Diagnostic only: it publishes nothing and mutates no game state.  It exists
 * because the two reported death-camera defects are only distinguishable by
 * what the server actually holds at the moment of death and at the moment of
 * skip, and the candidate producers (SpectatorClientEndFrame's forced arm, its
 * ordinary follow arm, Cmd_FollowCycle_f, and the script's ClearKillcamState)
 * all write the same small tuple.  Printing that tuple on change separates
 * them in one round.
 *
 * Quiet by construction: gated on CODOL_TRACE_ON(), bots excluded, one line
 * only when the tuple changes, and a process-wide cap.  A full match with
 * twelve bots produced no output at all with the dvar off.
 */
#ifdef CODOL_SERVER
#include "codol_killcam_trace.h"
#include "q_shared.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include "g_shared.h"
#include "server.h"
#include "player.h"
#include "entity.h"
#include "sys_net.h"

#define CODOL_KILLCAM_TRACE_MAX_LINES 600

typedef struct {
    int valid;
    int sessionState;
    int forceSpectatorClient;
    int spectatorClient;
    int killCamEntity;
    int archiveTime;
    int psOffsetTime;
    int deltaTime;
    int psKillCamEntity;
    int psClientNum;
    int pmType;
} killcam_trace_key_t;

static killcam_trace_key_t last_key[MAX_CLIENTS];
static int trace_lines;
static int trace_last_time;

void CODOL_KillcamTraceFrame(void)
{
    int i;
    if (!CODOL_TRACE_ON()) {
        /* Keep the keys from going stale across a trace-off window so the first
           line after re-enabling is a real transition rather than a dump. */
        trace_last_time = level.time;
        return;
    }
    if (level.time == trace_last_time) return;
    trace_last_time = level.time;
    if (trace_lines >= CODOL_KILLCAM_TRACE_MAX_LINES) return;

    for (i = 0; i < level.maxclients && i < MAX_CLIENTS; ++i) {
        gclient_t *cl = &level.clients[i];
        killcam_trace_key_t key;
        if (cl->sess.connected != CON_CONNECTED) { last_key[i].valid = 0; continue; }
        /* Bots die constantly and none of them can report a camera bug. */
        if (svs.clients[i].netchan.remoteAddress.type == NA_BOT) continue;

        key.valid = 1;
        key.sessionState = (int)cl->sess.sessionState;
        key.forceSpectatorClient = cl->sess.forceSpectatorClient;
        key.spectatorClient = cl->spectatorClient;
        key.killCamEntity = cl->sess.killCamEntity;
        key.archiveTime = cl->sess.archiveTime;
        key.psOffsetTime = cl->sess.psOffsetTime;
        key.deltaTime = cl->ps.deltaTime;
        key.psKillCamEntity = cl->ps.killCamEntity;
        key.psClientNum = cl->ps.clientNum;
        key.pmType = cl->ps.pm_type;

        if (last_key[i].valid && !memcmp(&last_key[i], &key, sizeof(key))) continue;
        last_key[i] = key;
        ++trace_lines;
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL killcam: t=%d cl=%d ss=%d fsc=%d sc=%d kce=%d arch=%d psoff=%d "
            "dT=%d pkce=%d psCl=%d pm=%d hp=%d org=%.0f %.0f %.0f\n",
            level.time, i, key.sessionState, key.forceSpectatorClient,
            key.spectatorClient, key.killCamEntity, key.archiveTime,
            key.psOffsetTime, key.deltaTime, key.psKillCamEntity,
            key.psClientNum, key.pmType, cl->ps.stats[0],
            cl->ps.origin[0], cl->ps.origin[1], cl->ps.origin[2]);
        if (trace_lines >= CODOL_KILLCAM_TRACE_MAX_LINES) {
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL killcam: line cap %d reached, trace silenced\n",
                CODOL_KILLCAM_TRACE_MAX_LINES);
            return;
        }
    }
}
#endif
