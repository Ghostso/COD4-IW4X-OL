/* CoDOL melee diagnostics.
 *
 * The retained melee path is FireWeaponMelee (src/asmsource/_g_weapon.asm)
 * -> Weapon_Melee_internal -> Melee_Trace -> G_LocationalTrace / G_Damage.
 * Every value the trace depends on is reported here so a miss can be told
 * apart from a zeroed weapon definition, a bad lunge, a stale antilag rewind
 * and a trace that stopped on the world.
 */
#include "q_shared.h"
#include "entity.h"
#include "g_shared.h"
#include "bg_public.h"
#include "cm_public.h"
#include "xassets/weapondef.h"
#include "qcommon.h"

extern cvar_t *codol_meleeDebug;
extern cvar_t *g_antilag;

/* weaponParms as the retained melee builds it: forward/right/up/origin. */
typedef struct
{
    vec3_t forward;   /* +0x00 */
    vec3_t right;     /* +0x0c */
    vec3_t up;        /* +0x18 */
    vec3_t origin;    /* +0x24 */
} codol_melee_parms_t;

static struct
{
    int attempts;
    int traceHits;      /* Melee_Trace returned a contact of any kind */
    int entityHits;     /* contact resolved to a damageable entity */
    int playerHits;     /* contact resolved to another client */
    int damaged;        /* G_Damage actually ran */
    int missedInRange;  /* an enemy client was inside the melee cylinder and we still missed */
    int actorTraces;    /* CODOL_ActorMeleeTrace: no FireWeaponMelee ahead of it */
    int report;
} codol_melee_stats;

static int melee_verbose(void)
{
    return codol_meleeDebug && codol_meleeDebug->boolean;
}

/* Closest live enemy client to the melee volume, so a miss can be scored
 * against a target that should have been reachable. */
static gentity_t *closest_enemy(gentity_t *ent, const codol_melee_parms_t *wp,
                                float range, float *outDist, float *outAhead, float *outSide)
{
    gentity_t *best = NULL;
    float bestDist = 1.0e9f;
    int i;
    if(!ent || !wp) return NULL;
    for(i = 0; i < level.maxclients; ++i)
    {
        gentity_t *other = &g_entities[i];
        vec3_t d;
        float dist, ahead, side;
        if(other == ent || !other->client || !other->r.inuse) continue;
        if(other->health <= 0 || !other->takedamage) continue;
        VectorSubtract(other->r.currentOrigin, wp->origin, d);
        dist = (float)sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
        if(dist > range + 48.0f) continue;
        ahead = DotProduct(d, wp->forward);
        side = DotProduct(d, wp->right);
        if(ahead < 0.0f) continue;
        if(dist < bestDist)
        {
            bestDist = dist;
            best = other;
            if(outDist) *outDist = dist;
            if(outAhead) *outAhead = ahead;
            if(outSide) *outSide = side;
        }
    }
    return best;
}

static gentity_t *g_meleeCandidate;
static int g_meleeFirePending, g_meleeLastFromPlayer;
static float g_meleeCandidateDist, g_meleeCandidateAhead, g_meleeCandidateSide;

void __cdecl CODOL_MeleeDebugFire(gentity_t *ent, int antilagTime, const void *parms,
                                  float range, float width, float height)
{
    const codol_melee_parms_t *wp = (const codol_melee_parms_t *)parms;
    const playerState_t *ps;
    const struct WeaponDef *def;
    if(!ent || !ent->client || !wp) return;
    ps = &ent->client->ps;
    def = BG_GetWeaponDef((int)ps->weapon);

    ++codol_melee_stats.attempts;
    g_meleeFirePending = 1;
    g_meleeCandidate = NULL;
    g_meleeCandidateDist = g_meleeCandidateAhead = g_meleeCandidateSide = 0.0f;
    g_meleeCandidate = closest_enemy(ent, wp, range, &g_meleeCandidateDist,
                                     &g_meleeCandidateAhead, &g_meleeCandidateSide);

    if(!melee_verbose()) return;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL melee: fire attacker %d weapon %u %s cmdTime %d levelTime %d antilagTime %d rewind %d g_antilag %d\n",
        ent->s.number, ps->weapon,
        def && def->szInternalName ? def->szInternalName : "<null>",
        ps->commandTime, level.time, antilagTime, level.time - antilagTime,
        g_antilag ? g_antilag->boolean : -1);
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL melee: def damage %d delay/time %d/%d chargeDelay/chargeTime %d/%d dvar range/width/height %.1f/%.1f/%.1f\n",
        def ? def->iMeleeDamage : -1, def ? def->iMeleeDelay : -1, def ? def->iMeleeTime : -1,
        def ? def->meleeChargeDelay : -1, def ? def->meleeChargeTime : -1, range, width, height);
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL melee: traceStart (%.1f %.1f %.1f) entOrigin (%.1f %.1f %.1f) fwd (%.2f %.2f %.2f) vel (%.0f %.0f %.0f) pm_flags 0x%x chargeTime %d chargeDist %d chargeYaw %.1f\n",
        wp->origin[0], wp->origin[1], wp->origin[2],
        ent->r.currentOrigin[0], ent->r.currentOrigin[1], ent->r.currentOrigin[2],
        wp->forward[0], wp->forward[1], wp->forward[2],
        ps->velocity[0], ps->velocity[1], ps->velocity[2],
        (unsigned)ps->pm_flags, ps->meleeChargeTime, ps->meleeChargeDist, ps->meleeChargeYaw);
    if(g_meleeCandidate)
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL melee: nearest enemy %d serverOrigin (%.1f %.1f %.1f) dist %.1f ahead %.1f side %.1f\n",
            g_meleeCandidate->s.number,
            g_meleeCandidate->r.currentOrigin[0], g_meleeCandidate->r.currentOrigin[1],
            g_meleeCandidate->r.currentOrigin[2],
            g_meleeCandidateDist, g_meleeCandidateAhead, g_meleeCandidateSide);
    else
        Com_Printf(CON_CHANNEL_SERVER, "CoDOL melee: no enemy client inside the melee volume\n");
}

void __cdecl CODOL_MeleeDebugTrace(gentity_t *ent, int hit, const trace_t *tr,
                                   const float *hitpos, int meleeDamage)
{
    gentity_t *target = NULL;
    int reachable;
    int fromPlayer;
    if(!ent || !tr) return;
    /* Weapon_Melee_internal is shared with CODOL_ActorMeleeTrace, which has no
     * FireWeaponMelee ahead of it. Only player melee feeds the attempt totals. */
    fromPlayer = g_meleeFirePending;
    g_meleeFirePending = 0;
    g_meleeLastFromPlayer = fromPlayer;
    if(!fromPlayer)
    {
        ++codol_melee_stats.actorTraces;
        if(melee_verbose())
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL melee: actor trace from %d hit %d fraction %.3f hitId %d meleeDamage %d\n",
                ent->s.number, hit, tr->fraction, (int)tr->hitId, meleeDamage);
        return;
    }
    if(hit)
    {
        ++codol_melee_stats.traceHits;
        if(tr->hitType == TRACE_HITTYPE_ENTITY && tr->hitId < MAX_GENTITIES)
        {
            target = &g_entities[tr->hitId];
            if(target->takedamage) ++codol_melee_stats.entityHits;
            if(target->client) ++codol_melee_stats.playerHits;
        }
    }
    reachable = g_meleeCandidate != NULL;
    if(reachable && !(target && target->client)) ++codol_melee_stats.missedInRange;

    if(melee_verbose())
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL melee: trace hit %d fraction %.3f hitType %d hitId %d cflags 0x%x sflags 0x%x partName %d startsolid %d point (%.1f %.1f %.1f) targetIsClient %d takedamage %d meleeDamage %d reachableEnemy %d\n",
            hit, tr->fraction, (int)tr->hitType, (int)tr->hitId, (unsigned)tr->cflags,
            (unsigned)tr->sflags, (int)tr->partName, (int)tr->startsolid,
            hitpos ? hitpos[0] : 0.0f, hitpos ? hitpos[1] : 0.0f, hitpos ? hitpos[2] : 0.0f,
            target && target->client ? 1 : 0,
            target ? (int)target->takedamage : -1,
            meleeDamage, reachable);

    if(++codol_melee_stats.report >= 20)
    {
        codol_melee_stats.report = 0;
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL melee: totals attempts %d traceContacts %d damageableEnts %d players %d damaged %d missedWithEnemyInRange %d actorTraces %d playerHitRate %.1f%%\n",
            codol_melee_stats.attempts, codol_melee_stats.traceHits, codol_melee_stats.entityHits,
            codol_melee_stats.playerHits, codol_melee_stats.damaged, codol_melee_stats.missedInRange,
            codol_melee_stats.actorTraces,
            codol_melee_stats.attempts ? 100.0f * (float)codol_melee_stats.playerHits / (float)codol_melee_stats.attempts : 0.0f);
    }
}

void __cdecl CODOL_MeleeDebugDamage(gentity_t *targ, gentity_t *attacker, int damage)
{
    if(g_meleeLastFromPlayer) ++codol_melee_stats.damaged;
    if(!melee_verbose() || !targ) return;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL melee: damage %d to %d health %d from %d\n",
        damage, targ->s.number, targ->health, attacker ? attacker->s.number : -1);
}
