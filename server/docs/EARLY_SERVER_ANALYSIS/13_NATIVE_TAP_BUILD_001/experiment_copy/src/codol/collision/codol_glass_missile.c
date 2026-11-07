/* Missile flight through native C1 glass.
 * IW4 Missile_PenetrateGlass 5e6f40 (called from G_RunMissile 5e8f0b with
 * predicted=0), C1 predicted twin 52f200 (from 52fe34): a missile whose
 * trace hits a glass piece at or above missileGlassShatterVel (C1 dvar
 * 0x24b99d0, registered at 52df20 with default 600, minimum 0) destroys that
 * piece at the impact point and is traced again, so it flies on through the
 * opening instead of bouncing. Slower missiles bounce and leave the piece to
 * explosion radius damage. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "q_shared.h"
#include "q_math.h"
#include "g_shared.h"
#include "cm_public.h"
#include "qcommon.h"
#include "codol_glass_world.h"
#include <math.h>

extern void BG_EvaluateTrajectoryDelta(const trajectory_t *, int, float *);
extern char bulletPriorityMap[];

/* Returns 1 when the piece was destroyed and results now hold the new trace. */
int CODOL_MissilePenetrateGlass(trace_t *results,gentity_t *ent,
    const float *start,const float *end)
{
    vec3_t velocity,direction={0,0,0},position;
    float speed_squared,limit;
    unsigned piece;
    int pass;
    if (!results || !ent || !start || !end ||
        results->hitType!=TRACE_HITTYPE_GLASS || !results->hitId ||
        !CODOL_GlassWorldEnsureMap()) return 0;
    if (ent->s.lerp.pos.trType==TR_INTERPOLATE) {
        /* 52f251..52f294: the step itself, squared and scaled by 1/0.05^2. */
        VectorSubtract(end,start,velocity);
        speed_squared=DotProduct(velocity,velocity)/0.0025f;
    } else {
        BG_EvaluateTrajectoryDelta(&ent->s.lerp.pos,level.time,velocity);
        speed_squared=DotProduct(velocity,velocity);
    }
    limit=CODOL_GlassMissileShatterVelocity();
    /* 52f2e8/5e702d: skip only when limit^2 is greater than speed^2. */
    if (!isfinite(speed_squared) || limit*limit>speed_squared) {
        Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL glass: missile %d bounced off piece %u (speed %.0f < %.0f)\n",
            ent->s.number,(unsigned)results->hitId-1,sqrtf(speed_squared),limit);
        return 0;
    }
    if (DotProduct(velocity,velocity)>0.0f) Vec3NormalizeTo(velocity,direction);
    Vec3Lerp(start,end,results->fraction,position);
    piece=(unsigned)results->hitId-1;
    CODOL_GlassWorldShatterAt(piece,position,direction,level.time);
    pass=ent->r.ownerNum.number ? ent->r.ownerNum.number-1 : ENTITYNUM_NONE;
    G_LocationalTrace(results,start,end,pass,ent->clipmask,bulletPriorityMap);
    Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL glass: missile %d shattered piece %u at speed %.0f\n",
        ent->s.number,piece,sqrtf(speed_squared));
    return 1;
}
#endif
