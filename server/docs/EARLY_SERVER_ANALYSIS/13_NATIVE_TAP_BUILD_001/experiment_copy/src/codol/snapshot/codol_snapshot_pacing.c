/* Per-snapshot usercmd consumption pacing.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 * See codol_snapshot_pacing.h for why this exists. */
#ifdef CODOL_SERVER
#include "codol_snapshot_pacing.h"
#include "codol_bot.h"
#include "qcommon_io.h"
#include "qcommon.h"
#include "q_shared.h"
#include <math.h>
#include <string.h>

#define CODOL_PACING_WINDOW 64u      /* >= one second of snapshots at any sv_fps */

typedef struct {
    /* Accumulated since the previous snapshot for this client. */
    unsigned pending_cmds, pending_packets;
    /* Cursors. */
    int prev_ps_time, prev_sv_time;
    unsigned char have_prev;
    /* One reporting window. */
    int adv[CODOL_PACING_WINDOW];
    int wall[CODOL_PACING_WINDOW];
    unsigned char cmds[CODOL_PACING_WINDOW];
    unsigned char pkts[CODOL_PACING_WINDOW];
    unsigned n;
    unsigned delayed;
    int window_start;
} codol_pacing_t;

static codol_pacing_t codol_pacing[MAX_CLIENTS];

void CODOL_PacingResetClient(unsigned client)
{
    if(client >= MAX_CLIENTS) return;
    memset(&codol_pacing[client], 0, sizeof(codol_pacing[client]));
}

void CODOL_PacingPacket(unsigned client, int cmdCount)
{
    if(client >= MAX_CLIENTS || cmdCount <= 0) return;
    ++codol_pacing[client].pending_packets;
}

void CODOL_PacingExecuted(unsigned client, int commandTime)
{
    (void)commandTime;
    if(client >= MAX_CLIENTS) return;
    ++codol_pacing[client].pending_cmds;
}

static void report(unsigned client, codol_pacing_t *p)
{
    double sum = 0.0, sumsq = 0.0, mean, var;
    double wsum = 0.0, csum = 0.0, psum = 0.0;
    int lo = 0x7fffffff, hi = -0x7fffffff;
    unsigned i, nshort = 0, nnear = 0, nlong = 0;
    unsigned prev_short_total = 0, prev_long_total = 0;
    unsigned short_after_short = 0, short_after_long = 0;
    int prev_class = 0;   /* -1 short, 0 first/near, +1 long */

    if(p->n < 4) return;
    for(i = 0; i < p->n; ++i) {
        sum += (double)p->adv[i];
        sumsq += (double)p->adv[i]*(double)p->adv[i];
        wsum += (double)p->wall[i];
        csum += (double)p->cmds[i];
        psum += (double)p->pkts[i];
        if(p->adv[i] < lo) lo = p->adv[i];
        if(p->adv[i] > hi) hi = p->adv[i];
    }
    mean = sum/(double)p->n;
    var = sumsq/(double)p->n - mean*mean;
    if(var < 0.0) var = 0.0;

    /* Classify against this window's own mean, so the test does not depend on
     * sv_fps or on the client's frame rate.  "near" is within +-20% of the
     * mean: a unimodal distribution puts almost every sample there, the
     * reported bimodal 35/70 around a 52 mean puts almost none. */
    for(i = 0; i < p->n; ++i) {
        double d = (double)p->adv[i] - mean;
        int cls;
        if(fabs(d) <= 0.20*mean) { ++nnear; cls = 0; }
        else if(d < 0.0)         { ++nshort; cls = -1; }
        else                     { ++nlong; cls = 1; }
        if(i) {
            if(prev_class < 0) { ++prev_short_total; if(cls < 0) ++short_after_short; }
            else if(prev_class > 0) { ++prev_long_total; if(cls < 0) ++short_after_long; }
        }
        prev_class = cls;
    }

    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL pacing: c%u n %u advance mean %.1f sd %.1f min %d max %d "
        "near %u short %u long %u P(short|long) %.3f P(short|short) %.3f "
        "cmds/snap %.2f pkts/snap %.2f cmds/pkt %.2f wall/snap %.1f "
        "ratedelayed %u/%u\n",
        client, p->n, mean, sqrt(var), lo, hi, nnear, nshort, nlong,
        prev_long_total ? (double)short_after_long/(double)prev_long_total : -1.0,
        prev_short_total ? (double)short_after_short/(double)prev_short_total : -1.0,
        csum/(double)p->n, psum/(double)p->n,
        psum > 0.0 ? csum/psum : -1.0, wsum/(double)p->n,
        p->delayed, p->n);
}

void CODOL_PacingSnapshot(unsigned client, int psCommandTime, int serverTime,
                          int rateDelayed)
{
    codol_pacing_t *p;
    if(!CODOL_TRACE_ON()) return;
    if(client >= MAX_CLIENTS) return;
    if(CODOL_ClientIsBotClient(client)) return;
    p = &codol_pacing[client];

    if(p->have_prev) {
        int advance = psCommandTime - p->prev_ps_time;
        int wall = serverTime - p->prev_sv_time;
        /* A map change, a spawn or a commandTime retime makes the difference
         * meaningless; drop the sample rather than let it pollute the mean. */
        if(advance >= 0 && advance < 1000 && wall > 0 && wall < 1000 &&
           p->n < CODOL_PACING_WINDOW) {
            p->adv[p->n] = advance;
            p->wall[p->n] = wall;
            p->cmds[p->n] = (unsigned char)(p->pending_cmds > 255 ? 255 : p->pending_cmds);
            p->pkts[p->n] = (unsigned char)(p->pending_packets > 255 ? 255 : p->pending_packets);
            ++p->n;
            if(rateDelayed) ++p->delayed;
        }
    } else {
        p->window_start = serverTime;
    }
    p->pending_cmds = p->pending_packets = 0;
    p->prev_ps_time = psCommandTime;
    p->prev_sv_time = serverTime;
    p->have_prev = 1;

    if(serverTime - p->window_start >= 1000 || p->n >= CODOL_PACING_WINDOW) {
        report(client, p);
        p->n = 0;
        p->delayed = 0;
        p->window_start = serverTime;
    }
}
#endif
