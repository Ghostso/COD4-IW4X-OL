/* Per-command pmove result ring + client-prediction error decomposition.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 * See codol_pmove_trace.h for why this exists. */
#ifdef CODOL_SERVER
#include "codol_pmove_trace.h"
#include "codol_bot.h"
#include "codol_terrain_probe.h"
#include "qcommon_io.h"
#include "qcommon.h"
#include "q_shared.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define CODOL_PMTRACE_RING 160u
#define CODOL_PMTRACE_MAX_LINES 4000

typedef struct {
    int commandTime;              /* ps->commandTime AFTER the substep */
    int msec;
    float origin_before[3];
    float origin_after[3];
    float velocity_before[3];
    float velocity_after[3];
    float wishdir[3];
    float viewangles[3];
    float normal[3];              /* last plane the slide/step solver clipped */
    float wishspeed;
    float cmdScale;
    float fwd, right;             /* the command axes wish() actually used */
    float stepDelta;              /* origin.z change contributed by step_slide */
    float fraction;
    float gt_fraction, gt_normz;  /* post-move PM_GroundTrace result */
    float gnormal[3];             /* the plane the walk mover projected onto */
    float slide_xy, final_xy, step_up;
    unsigned step_flags;
    float gn_fraction;
    float projWishDeg, projVelDeg;
    int gn_hitType, gn_hitId;
    unsigned gn_sflags, gn_cflags;
    float posFrac;                /* ps->fWeaponPosFrac (ADS ramp) */
    float mss, adsmss;            /* WeaponDef +0x670 / +0x674 */
    unsigned char adsWeapon;      /* which of the two PM_CmdScale selected */
    unsigned direction, prev_direction, buttons;
    unsigned pm_flags_before, pm_flags_after;
    int groundEntityNum, speed, viewHeightTarget;
    int hitType;
    unsigned char substep, final, walking, groundPlane, almost, blocked, valid;
    unsigned char fallback;       /* the retained IW3 Pmove ran this command */
} codol_pmtrace_entry_t;

typedef struct {
    codol_pmtrace_entry_t ring[CODOL_PMTRACE_RING];
    unsigned head;
    /* Staging written by wish()/the slide solver during the current substep. */
    float pend_wishdir[3];
    float pend_normal[3];
    float pend_wishspeed, pend_cmdScale, pend_fwd, pend_right;
    float pend_stepDelta, pend_fraction;
    float pend_mss, pend_adsmss;
    float pend_gnormal[3], pend_gn_fraction, pend_projWishDeg, pend_projVelDeg;
    float pend_slide_xy, pend_final_xy, pend_step_up;
    unsigned pend_step_flags;
    int pend_gn_hitType, pend_gn_hitId;
    unsigned pend_gn_sflags, pend_gn_cflags;
    int pend_blocked, pend_hitType, pend_adsWeapon;
    /* Previous accepted report, for the travelled-distance ratio. */
    int prev_time;
    float prev_pred[3];
    float prev_srv[3];
    unsigned char prev_valid;
    int last_line_ms;
    unsigned fallbacks;
    unsigned prev_direction;
    /* Acceptance counters: `diverged` must equal the `toofar` count printed by
     * `CoDOL rov:` for the same second.  They are summarised on their own line
     * so the check survives the detail-line cap. */
    unsigned frames, diverged;
    /* Does a forced correction actually LAND?  The rov gate republishes origin
     * AND velocity with a zero delta base on every frame over 0.1 units, so the
     * very next frame should read ~0 if the client accepted it.  An error that
     * simply persists across consecutive forced frames is not a pmove modelling
     * fault at all -- it is the correction failing to take. */
    float prev_errxy;
    unsigned since_force;
    float sum_err, worst_err;
    int last_sum_ms;
} codol_pmtrace_client_t;

static codol_pmtrace_client_t codol_pmtrace[MAX_CLIENTS];
static int codol_pmtrace_lines;
static int codol_pmtrace_owner = -1;   /* first non-bot client, latched */

void CODOL_PmoveTraceResetClient(unsigned client)
{
    if(client >= MAX_CLIENTS) return;
    memset(&codol_pmtrace[client], 0, sizeof(codol_pmtrace[client]));
    if(codol_pmtrace_owner == (int)client) codol_pmtrace_owner = -1;
}

void CODOL_PmoveTraceWish(int client, const float *wishdir, float wishspeed,
                          float cmdScale, float fwd, float right)
{
    codol_pmtrace_client_t *c;
    if((unsigned)client >= MAX_CLIENTS) return;
    c = &codol_pmtrace[client];
    if(wishdir) memcpy(c->pend_wishdir, wishdir, sizeof(c->pend_wishdir));
    else memset(c->pend_wishdir, 0, sizeof(c->pend_wishdir));
    c->pend_wishspeed = wishspeed;
    c->pend_cmdScale = cmdScale;
    c->pend_fwd = fwd;
    c->pend_right = right;
}

void CODOL_PmoveTraceScale(int client, float mss, float adsmss, int adsWeapon)
{
    codol_pmtrace_client_t *c;
    if((unsigned)client >= MAX_CLIENTS) return;
    c = &codol_pmtrace[client];
    c->pend_mss = mss;
    c->pend_adsmss = adsmss;
    c->pend_adsWeapon = adsWeapon;
}

void CODOL_PmoveTraceGround(int client, const float *normal, float fraction,
                            int hitType, int hitId, unsigned sflags,
                            unsigned cflags, float projWishDeg,
                            float projVelDeg)
{
    codol_pmtrace_client_t *c;
    if((unsigned)client >= MAX_CLIENTS) return;
    c = &codol_pmtrace[client];
    if(normal) memcpy(c->pend_gnormal, normal, sizeof(c->pend_gnormal));
    else memset(c->pend_gnormal, 0, sizeof(c->pend_gnormal));
    c->pend_gn_fraction = fraction;
    c->pend_gn_hitType = hitType;
    c->pend_gn_hitId = hitId;
    c->pend_gn_sflags = sflags;
    c->pend_gn_cflags = cflags;
    c->pend_projWishDeg = projWishDeg;
    c->pend_projVelDeg = projVelDeg;
}

void CODOL_PmoveTraceStep(int client, unsigned flags, float slide_xy,
                          float final_xy, float step_up)
{
    codol_pmtrace_client_t *c;
    if((unsigned)client >= MAX_CLIENTS) return;
    c = &codol_pmtrace[client];
    c->pend_step_flags = flags;
    c->pend_slide_xy = slide_xy;
    c->pend_final_xy = final_xy;
    c->pend_step_up = step_up;
}

void CODOL_PmoveTraceCollision(int client, int blocked, float stepDelta,
                               const float *normal, float fraction, int hitType)
{
    codol_pmtrace_client_t *c;
    if((unsigned)client >= MAX_CLIENTS) return;
    c = &codol_pmtrace[client];
    c->pend_blocked = blocked;
    c->pend_stepDelta = stepDelta;
    /* A NULL normal means "keep what the slide solver already recorded": the
     * step/exit call updates only the blocked flag and the step height. */
    if(normal) {
        memcpy(c->pend_normal, normal, sizeof(c->pend_normal));
        c->pend_fraction = fraction;
        c->pend_hitType = hitType;
    }
}

void CODOL_PmoveTraceCommit(const codol_pmove_c1_t *move,
                            const float *origin_before, int msec,
                            unsigned pm_flags_before, int substep, int final)
{
    codol_pmtrace_client_t *c;
    codol_pmtrace_entry_t *e;
    unsigned client;
    if(!move || !move->ps || !origin_before) return;
    client = (unsigned)move->ps->clientNum;
    if(client >= MAX_CLIENTS) return;
    c = &codol_pmtrace[client];
    e = &c->ring[c->head % CODOL_PMTRACE_RING];
    ++c->head;
    memset(e, 0, sizeof(*e));
    e->commandTime = move->ps->commandTime;
    e->msec = msec;
    memcpy(e->origin_before, origin_before, sizeof(e->origin_before));
    memcpy(e->origin_after, move->ps->origin, sizeof(e->origin_after));
    memcpy(e->velocity_before, move->local.previous_velocity,
           sizeof(e->velocity_before));
    memcpy(e->velocity_after, move->ps->velocity, sizeof(e->velocity_after));
    memcpy(e->wishdir, c->pend_wishdir, sizeof(e->wishdir));
    memcpy(e->viewangles, move->ps->viewangles, sizeof(e->viewangles));
    memcpy(e->normal, c->pend_normal, sizeof(e->normal));
    e->wishspeed = c->pend_wishspeed;
    e->cmdScale = c->pend_cmdScale;
    e->fwd = c->pend_fwd;
    e->right = c->pend_right;
    e->stepDelta = c->pend_stepDelta;
    e->fraction = c->pend_fraction;
    e->posFrac = move->ps->fWeaponPosFrac;
    e->mss = c->pend_mss;
    e->adsmss = c->pend_adsmss;
    e->adsWeapon = (unsigned char)(c->pend_adsWeapon != 0);
    e->direction = (unsigned)move->cmd.direction;
    /* The movement-key EDGE is the event to look for: C1's own client builds
     * cmd.forwardmove/rightmove, and if it uses fractional key-state (Q3
     * CL_KeyState) on the frame a key goes down or up, its wish vector for that
     * one command is shorter and points elsewhere than the +-127 this server
     * must reconstruct from the 4 wire direction bits.  That would be exactly a
     * bimodal, one-command-sized error with a perpendicular component. */
    e->prev_direction = c->prev_direction;
    c->prev_direction = e->direction;
    e->buttons = (unsigned)move->cmd.buttons;
    e->pm_flags_before = pm_flags_before;
    e->pm_flags_after = (unsigned)move->ps->pm_flags;
    e->groundEntityNum = move->ps->groundEntityNum;
    e->speed = move->ps->speed;
    e->viewHeightTarget = move->ps->viewHeightTarget;
    e->hitType = c->pend_hitType;
    e->substep = (unsigned char)(substep > 255 ? 255 : substep);
    e->final = (unsigned char)(final != 0);
    e->walking = (unsigned char)(move->local.walking != 0);
    e->groundPlane = (unsigned char)(move->local.groundPlane != 0);
    e->almost = (unsigned char)(move->local.almostGroundPlane != 0);
    e->gt_fraction = move->local.groundTrace.fraction;
    e->gt_normz = move->local.groundTrace.normal[2];
    memcpy(e->gnormal, c->pend_gnormal, sizeof(e->gnormal));
    e->gn_fraction = c->pend_gn_fraction;
    e->gn_hitType = c->pend_gn_hitType;
    e->gn_hitId = c->pend_gn_hitId;
    e->gn_sflags = c->pend_gn_sflags;
    e->gn_cflags = c->pend_gn_cflags;
    e->step_flags = c->pend_step_flags;
    e->slide_xy = c->pend_slide_xy;
    e->final_xy = c->pend_final_xy;
    e->step_up = c->pend_step_up;
    e->projWishDeg = c->pend_projWishDeg;
    e->projVelDeg = c->pend_projVelDeg;
    e->blocked = (unsigned char)(c->pend_blocked != 0);
    e->valid = 1;
    /* Staging belongs to one substep only; a substep that never reaches the
     * wish/slide producers must not inherit the previous one's numbers. */
    memset(c->pend_wishdir, 0, sizeof(c->pend_wishdir));
    memset(c->pend_normal, 0, sizeof(c->pend_normal));
    c->pend_wishspeed = c->pend_cmdScale = 0.0f;
    c->pend_fwd = c->pend_right = 0.0f;
    c->pend_stepDelta = c->pend_fraction = 0.0f;
    c->pend_mss = c->pend_adsmss = 0.0f;
    memset(c->pend_gnormal, 0, sizeof(c->pend_gnormal));
    c->pend_gn_fraction = c->pend_projWishDeg = c->pend_projVelDeg = 0.0f;
    c->pend_slide_xy = c->pend_final_xy = c->pend_step_up = 0.0f;
    c->pend_step_flags = 0;
    c->pend_gn_hitType = c->pend_gn_hitId = 0;
    c->pend_gn_sflags = c->pend_gn_cflags = 0;
    c->pend_blocked = c->pend_hitType = c->pend_adsWeapon = 0;
}

void CODOL_PmoveTraceFallback(unsigned client, int commandTime, int reason)
{
    codol_pmtrace_client_t *c;
    codol_pmtrace_entry_t *e;
    if(client >= MAX_CLIENTS) return;
    c = &codol_pmtrace[client];
    ++c->fallbacks;
    e = &c->ring[c->head % CODOL_PMTRACE_RING];
    ++c->head;
    memset(e, 0, sizeof(*e));
    e->commandTime = commandTime;
    e->hitType = reason;
    e->fallback = 1;
    e->final = 1;
    e->valid = 1;
}

static const codol_pmtrace_entry_t *find_entry(const codol_pmtrace_client_t *c,
                                               int commandTime, int *substeps)
{
    const codol_pmtrace_entry_t *found = NULL;
    unsigned i;
    int n = 0;
    for(i = 0; i < CODOL_PMTRACE_RING; ++i) {
        const codol_pmtrace_entry_t *e = &c->ring[i];
        if(!e->valid) continue;
        if(e->commandTime == commandTime && (!found || e->final)) found = e;
    }
    if(found) n = (int)found->substep + 1;
    if(substeps) *substeps = n;
    return found;
}

void CODOL_PmoveTraceReport(unsigned client, const float *serverOrigin,
                            const float *predictedOrigin, int predictedTime)
{
    codol_pmtrace_client_t *c;
    const codol_pmtrace_entry_t *e;
    static const codol_pmtrace_entry_t empty;
    float err[3], errlen, errxy, moved[3], movelen, dir[3];
    float along, perpx, perpy, perp, speed, spd0, ms, ratio;
    float srv_step, cli_step, turn, woff, stepaz, perp_signed;
    float projdz, pj_trace_z, pj_tri_z, pj_nz; int pj_tri, terr_mask;
    int dt, substeps = 0, ringmiss;
    char stepaz_s[16];

    if(!CODOL_TRACE_ON()) return;
    if(client >= MAX_CLIENTS || !predictedOrigin || !serverOrigin) return;
    if(codol_pmtrace_owner < 0) {
        if(CODOL_ClientIsBotClient(client)) return;
        codol_pmtrace_owner = (int)client;
    }
    if(codol_pmtrace_owner != (int)client) return;

    c = &codol_pmtrace[client];
    e = find_entry(c, predictedTime, &substeps);
    /* A ring miss must NOT suppress the line: this trace has to account for
     * every frame the rov gate acts on, or its count cannot be checked against
     * `toofar`.  The context columns simply read as zero and the line is
     * tagged, which is itself the diagnosis for that frame. */
    ringmiss = (e == NULL || e->fallback);
    if(!e) e = &empty;

    /* Exactly the vectors CODOL_ReadOriginVelocityFlag compares, so a
     * divergence line here and a `toofar` there are the same event. */
    err[0] = serverOrigin[0] - predictedOrigin[0];
    err[1] = serverOrigin[1] - predictedOrigin[1];
    err[2] = serverOrigin[2] - predictedOrigin[2];
    /* Both feet sampled against the SAME reference plane in one triangle scan.
     * `projdz` is the height difference the two horizontal positions alone
     * demand on this surface. If `err[2] - projdz` is ~0 on tilted ground there
     * is no height bug at all: the vertical symptom is the horizontal residual
     * projected onto a non-planar surface, identically zero on a plane by
     * construction. docs/CODOL_UNEVEN_GROUND_FIX_SWEEP.md #1.
     *
     * Sampled HERE because this is the only place both origins are in hand.
     * Rate limited and owner-only: the scan is cm.triCount barycentric tests
     * and must never run per client per frame. `tmask != 3` rows are NOT
     * APPLICABLE and must be excluded from the statistic, never read as zero. */
    projdz = 0.0f; terr_mask = 0;
    pj_trace_z = pj_tri_z = pj_nz = 0.0f; pj_tri = -1;
    {
        static int last_probe[MAX_CLIENTS];
        if(predictedTime - last_probe[client] >= 25 ||
           predictedTime < last_probe[client]) {
            float az = 0.0f, bz = 0.0f;
            last_probe[client] = predictedTime;
            terr_mask = CODOL_TerrainHeightUnder2(serverOrigin, predictedOrigin,
                                                  serverOrigin[2], &az, &bz,
                                                  &pj_tri, &pj_nz);
            pj_trace_z = serverOrigin[2];
            pj_tri_z = az;
            /* Self-validation, using a constant predicted BEFORE the capture:
             * a correct sample has the trace sitting SURFACE_CLIP_EPSILON above
             * the triangle the probe chose, i.e. tdz ~= +0.125. The first Diff A
             * capture showed tdz of 0.43 to 4.78 on a minority of rows -- the
             * probe had selected a surface the player is not standing on (a
             * brush floor, or an overlapping terrain layer), and reported
             * tmask 3 regardless, which is what broke the flat control. Those
             * rows are NOT APPLICABLE and must say so rather than contribute a
             * number. Healthy measured range was 0.12507..0.13385. */
            if(terr_mask == 3) {
                float tdz = serverOrigin[2] - az;
                if(tdz < 0.10f || tdz > 0.20f) terr_mask = 0;
                else projdz = az - bz;
            }
        }
    }
    errxy = (float)sqrt((double)(err[0]*err[0] + err[1]*err[1]));
    errlen = (float)sqrt((double)(err[0]*err[0] + err[1]*err[1] + err[2]*err[2]));

    /* Direction this command actually travelled, server-side. */
    moved[0] = e->origin_after[0] - e->origin_before[0];
    moved[1] = e->origin_after[1] - e->origin_before[1];
    moved[2] = 0.0f;
    movelen = (float)sqrt((double)(moved[0]*moved[0] + moved[1]*moved[1]));
    speed = (float)sqrt((double)(e->velocity_after[0]*e->velocity_after[0] +
                                 e->velocity_after[1]*e->velocity_after[1]));
    if(movelen > 0.0001f) {
        dir[0] = moved[0]/movelen; dir[1] = moved[1]/movelen;
    } else if(speed > 0.0001f) {
        dir[0] = e->velocity_after[0]/speed; dir[1] = e->velocity_after[1]/speed;
    } else {
        dir[0] = 1.0f; dir[1] = 0.0f;
    }
    dir[2] = 0.0f;
    along = err[0]*dir[0] + err[1]*dir[1];
    perpx = err[0] - along*dir[0];
    perpy = err[1] - along*dir[1];
    perp = (float)sqrt((double)(perpx*perpx + perpy*perpy));
    /* Signed lateral offset (+ = server is left of the client's track).  A
     * value that keeps its sign is a systematic bias in the move direction; one
     * that flips is correction dynamics or noise. */
    perp_signed = dir[0]*err[1] - dir[1]*err[0];
    ms = speed > 1.0f ? errxy/speed*1000.0f : -1.0f;
    /* The substep's own horizontal deceleration.  With no input and no
     * collision this is PM_Friction alone, so spd0 -> speed against the
     * client's travelled distance separates a friction disagreement from a
     * ground-trace (walking vs airborne) disagreement. */
    spd0 = (float)sqrt((double)(e->velocity_before[0]*e->velocity_before[0] +
                                e->velocity_before[1]*e->velocity_before[1]));

    /* Travelled-distance ratio since the previous report: a value a fraction of
     * a percent off 1.0 is a multiplicative speed fault; 1.0 with a growing
     * perpendicular term is a view-angle / wish-direction fault; a one-off
     * spike with blocked/hit set is the collision solver. */
    ratio = -1.0f;
    turn = -999.0f;
    srv_step = cli_step = -1.0f;
    dt = c->prev_valid ? predictedTime - c->prev_time : 0;
    if(c->prev_valid && dt > 0 && dt < 1000) {
        float sdx = serverOrigin[0]-c->prev_srv[0], sdy = serverOrigin[1]-c->prev_srv[1];
        float cdx = predictedOrigin[0]-c->prev_pred[0], cdy = predictedOrigin[1]-c->prev_pred[1];
        srv_step = (float)sqrt((double)(sdx*sdx + sdy*sdy));
        cli_step = (float)sqrt((double)(cdx*cdx + cdy*cdy));
        if(cli_step > 0.01f) ratio = srv_step/cli_step;
        /* The SIGNED angle between the two travelled step vectors, in degrees.
         * `ratio` == 1 with a non-zero `turn` is a pure ROTATION of the move
         * direction: the speed chain agrees and the wish DIRECTION does not. */
        if(srv_step > 0.05f && cli_step > 0.05f) {
            double a = atan2((double)sdy,(double)sdx) -
                       atan2((double)cdy,(double)cdx);
            a *= 180.0/3.14159265358979323846;
            while(a > 180.0) a -= 360.0;
            while(a < -180.0) a += 360.0;
            turn = (float)a;
        }
    }

    /* The wish direction expressed RELATIVE TO THE VIEW YAW.  On a diagonal
     * this is the one number that separates the candidate mechanisms:
     *   -45.0  = forward+strafe at full +-127 on both axes
     *   -33.5  = the same diagonal after PM_WalkMove's sprint rightmove
     *            rewrite (C1 0x00410932: ftol(127*0.667) = 84, and
     *            atan2(-84,127) = -33.5 deg)
     * Those two wish vectors have EXACTLY the same wishspeed, because
     * PM_CmdScale's `biggest / total` cancels the wish vector's length
     * (0x0041019b): with f=127 the `biggest` is 127 either way, so
     * wishspeed = ps->speed in both cases.  Disagreeing about the sprint flag
     * on one command therefore rotates the move by 11.5 deg with ratio 1.0000
     * and zero speed error -- exactly this trace's Finding 3 signature. */
    /* The azimuth of the substep's own horizontal travel MINUS the azimuth of
     * the velocity that produced it.  Everything in the walk path scales x and
     * y uniformly, so this is 0.000 unless the slide/step solver re-aimed the
     * move -- which is the only place inside this server that CAN rotate it. */
    stepaz = -999.0f;   /* no travel direction: printed as "n/a" */
    if(movelen > 0.0001f && speed > 0.0001f) {
        double a = atan2((double)moved[1],(double)moved[0]) -
                   atan2((double)e->velocity_after[1],(double)e->velocity_after[0]);
        a *= 180.0/3.14159265358979323846;
        while(a > 180.0) a -= 360.0;
        while(a < -180.0) a += 360.0;
        stepaz = (float)a;
    }

    woff = -999.0f;
    if(e->wishdir[0] != 0.0f || e->wishdir[1] != 0.0f) {
        double a = atan2((double)e->wishdir[1],(double)e->wishdir[0]);
        a = a*180.0/3.14159265358979323846 - (double)e->viewangles[1];
        while(a > 180.0) a -= 360.0;
        while(a < -180.0) a += 360.0;
        woff = (float)a;
    }

    /* Print EVERY frame past C1's 0.1-unit tolerance -- those are exactly the
     * frames the rov gate force-publishes -- and sample quiet frames at 5 Hz so
     * the divergence lines can simply be counted against `toofar`.  The detail
     * cap gates only the detail line: the per-second acceptance counters below
     * keep running for the whole session. */
    if(codol_pmtrace_lines >= CODOL_PMTRACE_MAX_LINES) goto remember;
    if(errxy <= 0.1f &&
       predictedTime - c->last_line_ms < 200 && predictedTime >= c->last_line_ms)
        goto remember;
    c->last_line_ms = predictedTime;
    /* A stationary substep has no travel direction, so stepaz has no value.
     * Print a token rather than a magic number: a sentinel that looks like a
     * float gets averaged into a median by accident. */
    if(stepaz <= -900.0f) memcpy(stepaz_s,"n/a",4);
    else snprintf(stepaz_s,sizeof(stepaz_s),"%+.4f",(double)stepaz);
    ++codol_pmtrace_lines;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL pmerr: c%u t%d sub %d/%d msec %d err %.4f (xy %.4f z %.4f) "
        "along %+.4f perp %.4f lat %+.4f ms %.2f ratio %.5f turn %+.3f (srv %.4f cli %.4f) "
        "spd %.2f<-%.2f psSpd %d scale %.5f wish %.3f f %.0f r %.0f dir 0x%x<-0x%x "
        "prev %.4f sincef %u woff %+.2f ang (%.3f %.3f %.3f) pmf 0x%x->0x%x edge 0x%x vht %d pof %.4f "
        "adsw %d mss %.3f/%.3f "
        "gnd %d walk %d gp %d blocked %d hit %d frac %.3f n (%.3f %.3f %.3f) "
        "stepdz %.3f gtfrac %.3f gtnz %.3f almost %d "
        "gn (%.6f %.6f %.6f) gnfrac %.5f gnhit %d/%d sf 0x%x cf 0x%x "
        "terr %d tracez %.4f triz %.4f tdz %+.5f tnz %.6f tri %d "
        "projdz %+.5f resid %+.5f tmask %d "
        "step 0x%02x slidexy %.4f finalxy %.4f dxy %+.4f stepup %.3f "
        "projw %+.4f projv %+.4f stepaz %s%s\n",
        client, predictedTime, (int)e->substep, substeps, e->msec,
        (double)errlen, (double)errxy, (double)err[2], (double)along, (double)perp, (double)perp_signed,
        (double)ms, (double)ratio, (double)turn, (double)srv_step,
        (double)cli_step,
        (double)speed, (double)spd0, e->speed, (double)e->cmdScale,
        (double)e->wishspeed,
        (double)e->fwd, (double)e->right, e->direction, e->prev_direction,
        (double)c->prev_errxy, c->since_force, (double)woff,
        (double)e->viewangles[0], (double)e->viewangles[1], (double)e->viewangles[2],
        e->pm_flags_before, e->pm_flags_after,
        e->pm_flags_before ^ e->pm_flags_after, e->viewHeightTarget,
        (double)e->posFrac, (int)e->adsWeapon, (double)e->mss, (double)e->adsmss,
        e->groundEntityNum, (int)e->walking,
        (int)e->groundPlane, (int)e->blocked, e->hitType, (double)e->fraction,
        (double)e->normal[0], (double)e->normal[1], (double)e->normal[2],
        (double)e->stepDelta, (double)e->gt_fraction, (double)e->gt_normz,
        (int)e->almost,
        (double)e->gnormal[0], (double)e->gnormal[1], (double)e->gnormal[2],
        (double)e->gn_fraction, e->gn_hitType, e->gn_hitId,
        e->gn_sflags, e->gn_cflags,
        (terr_mask & 1) ? 1 : 0, (double)pj_trace_z, (double)pj_tri_z,
        (double)((terr_mask & 1) ? pj_trace_z - pj_tri_z : 0.0f),
        (double)pj_nz, pj_tri,
        (double)projdz,
        (double)((terr_mask == 3) ? err[2] - projdz : 0.0f), terr_mask,
        e->step_flags, (double)e->slide_xy, (double)e->final_xy,
        (double)(e->final_xy - e->slide_xy), (double)e->step_up,
        (double)e->projWishDeg, (double)e->projVelDeg, stepaz_s,
        ringmiss ? " RING-MISS" : "");

remember:
    c->prev_errxy = errxy;
    if(errxy > 0.1f) c->since_force = 0; else ++c->since_force;
    ++c->frames;
    if(errxy > 0.1f) ++c->diverged;
    c->sum_err += errxy;
    if(errxy > c->worst_err) c->worst_err = errxy;
    if(predictedTime - c->last_sum_ms >= 1000 || predictedTime < c->last_sum_ms) {
        if(c->last_sum_ms)
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL pmerr sum: c%u diverged %u/%u frames (mean %.4f worst %.4f) "
                "-- must equal the `toofar` count in CoDOL rov:\n",
                client, c->diverged, c->frames,
                (double)(c->frames ? c->sum_err/(float)c->frames : 0.0f),
                (double)c->worst_err);
        c->last_sum_ms = predictedTime;
        c->frames = c->diverged = 0;
        c->sum_err = c->worst_err = 0.0f;
    }
    c->prev_time = predictedTime;
    memcpy(c->prev_srv, serverOrigin, sizeof(c->prev_srv));
    memcpy(c->prev_pred, predictedOrigin, sizeof(c->prev_pred));
    c->prev_valid = 1;
}
#endif
