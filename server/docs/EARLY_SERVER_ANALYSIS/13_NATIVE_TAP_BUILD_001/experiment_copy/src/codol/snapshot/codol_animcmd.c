/* Native animcmd records. C1 5a1264..5a127d decodes goal weight before
 * blend and playback rate; 443fbd..443fcf passes that weight to XAnim. */
#include "codol_animcmd.h"
#include <math.h>
static double clamp(double v, double lo, double hi) { return v < lo ? lo : v > hi ? hi : v; }
static unsigned even(double v)
{
    double b = floor(v), d = v-b;
    return (unsigned)(d > .5 || (d == .5 && fmod(b, 2.) != 0) ? b+1 : b);
}
static void blend(codol_msg_t *m, float v)
{
    unsigned n = (unsigned)clamp(floor((double)v*10.+.5), 0, 17);
    CODOL_WriteBits(m, n != 2, 1);
    if (n == 2) return;
    CODOL_WriteBits(m, n != 1, 1);
    if (n != 1) CODOL_WriteBits(m, n ? n-2 : 0, 4);
}
static void goal_weight(codol_msg_t *m, float v)
{
    if (fabs(v) < 1e-6 || fabs((double)v-1.) < 1e-6) {
        CODOL_WriteBits(m, 0, 1); CODOL_WriteBits(m, fabs(v) >= 1e-6, 1); return;
    }
    CODOL_WriteBits(m, 1, 1); CODOL_WriteBits(m, v > 1, 1);
    CODOL_WriteBits(m, even(v > 1 ? (clamp(v, 1, 5)-1)/4*31 : clamp(v, 0, 1)*31), 5);
}
static void playback_rate(codol_msg_t *m, float v)
{
    CODOL_WriteBits(m, fabs((double)v-1.) >= 1e-6, 1);
    if (fabs((double)v-1.) < 1e-6) return;
    CODOL_WriteBits(m, v > 2, 1);
    CODOL_WriteBits(m, even(v > 2 ? (clamp(v, 2, 5)-2)/3*31 : clamp(v, 0, 2)/2*31), 5);
}
int CODOL_WriteAnimCommands(codol_msg_t *m, const codol_animcmd_t *commands,
                            size_t count, uint32_t server_time)
{
    size_t i;
    uint32_t ref_entity = UINT32_MAX, ref_time = (uint32_t)-100003;
    if (!m) return 0;
    if (count && !commands) goto fail;
    for (i = 0; i < count; ++i) {
        const codol_animcmd_t *c = &commands[i];
        if (c->type < 1 || c->type > 6 || c->entity > 2047 || c->ref > 2047 ||
            c->sub > 2047 || c->arg2 > 3 || !isfinite(c->goal_weight) || !isfinite(c->playback_rate) ||
            !isfinite(c->blend) || !isfinite(c->fraction)) goto fail;
        CODOL_WriteBits(m, 0, 1); /* new record; no previous-ring reuse */
        if (ref_entity != c->entity) {
            CODOL_WriteBits(m, 7, 4); CODOL_WriteBits(m, c->entity, 11); ref_entity = c->entity;
        }
        if (ref_time != c->time) {
            int64_t delta = (int64_t)server_time - c->time;
            CODOL_WriteBits(m, 8, 4); CODOL_WriteBits(m, delta < 0 || delta > 255, 1);
            if (delta >= 0 && delta <= 255) CODOL_WriteBits(m, delta, 8); else CODOL_WriteLong(m, c->time);
            ref_time = c->time;
        }
        CODOL_WriteBits(m, c->type, 4);
        if (c->type >= 3 && c->type <= 5) CODOL_WriteBits(m, c->arg2, 2);
        CODOL_WriteBits(m, c->ref, 11);
        if (c->type == 5) {
            CODOL_WriteBits(m, c->sub != 0 && c->sub != 3, 1);
            if (c->sub == 0 || c->sub == 3) CODOL_WriteBits(m, c->sub == 3, 1);
            else CODOL_WriteBits(m, c->sub, 11);
        }
        if (c->type <= 2) blend(m, c->blend);
        else if (c->type <= 5) { goal_weight(m, c->goal_weight); blend(m, c->blend); playback_rate(m, c->playback_rate); }
        else CODOL_WriteBits(m, even(clamp(c->fraction, 0, 1)*31), 5);
        if (m->failed) return 0;
    }
    CODOL_WriteBits(m, 0, 5); return !m->failed;
fail:
    m->failed = 1; return 0;
}
