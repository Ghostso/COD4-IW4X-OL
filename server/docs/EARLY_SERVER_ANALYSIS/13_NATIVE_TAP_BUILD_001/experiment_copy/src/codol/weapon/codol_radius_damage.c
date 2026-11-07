/* C1 splash-damage rules on top of the retained IW3 G_RadiusDamage.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * C1 G_RadiusDamage is 0x522950. Against the IW3 body it differs in three
 * places, all handled by the retained assembly with the helpers below:
 *
 *   distance  0x522aca..0x522bb3: every entity is measured from the edge of
 *             its absolute box, |origin - boxMid| - boxHalf clamped at 0 per
 *             axis. IW3 did that only for brush models and measured
 *             everything else from its origin, which for a player is the
 *             feet: an explosion at chest height reached less far.
 *   reach     0x5229fd..0x522a2d, 0x522bc4..0x522bdb: an entity that is
 *             neither a client (+0x17c) nor an actor (+0x180) is only hit
 *             within min(radius, g_radiusDamageMax) - dvar 1279, default 256.
 *   shield    0x522c36..0x522c7c, 0x522cf6..0x522d22: a riot shield absorbs
 *             a share of the splash chosen by the angle between the shield
 *             tag's forward axis and the explosion (0x5750e0), and the rest
 *             reaches the damage callback with hitLoc shield and
 *             iDFlags 0x85 (radius | no knockback | SHIELD_EXPLOSIVE_SPLASH).
 */
#include "codol_radius_damage.h"
#include "codol_script_combat_builtins.h"
#include "g_shared.h"
#include "cvar.h"
#include "dobj.h"
#include "qcommon_io.h"
#include <float.h>
#include <math.h>

static cvar_t *radius_damage_max;
static cvar_t *shield_protection[4];
static cvar_t *shield_debug;

float CODOL_RadiusDamageReachSq(struct gentity_s *ent, float radiusSq)
{
    float limit;
    if(!ent || ent->client || ent->handler==ENT_HANDLER_CODOL_ACTOR) return radiusSq;
    /* C1 0x52b6a2..0x52b6b0: "1279" float 256, range 0..FLT_MAX. */
    if(!radius_damage_max)
        radius_damage_max=Cvar_RegisterFloat("1279",256.0f,0.0f,FLT_MAX,0x84,
            "Largest splash radius that damages anything but players and actors");
    if(!radius_damage_max) return radiusSq;
    limit=radius_damage_max->value*radius_damage_max->value;
    return limit<radiusSq ? limit : radiusSq;
}

/* C1 0x52b763..0x52b80d: "1282".."1285", defaults 0.95/0.8/0.55/0.15. */
static int shield_dvars(void)
{
    static const char *names[4]={"1282","1283","1284","1285"};
    static const char *descs[4]={
        "Riot shield splash protection within 30 degrees of its face",
        "Riot shield splash protection within 60 degrees of its face",
        "Riot shield splash protection within 120 degrees of its face",
        "Riot shield splash protection within 180 degrees of its face"};
    static const float defaults[4]={0.95f,0.8f,0.55f,0.15f};
    int i;
    for(i=0;i<4;++i) {
        if(!shield_protection[i])
            shield_protection[i]=Cvar_RegisterFloat(names[i],defaults[i],0.0f,1.0f,0x84,descs[i]);
        if(!shield_protection[i]) return 0;
    }
    return 1;
}

float CODOL_ShieldBlastProtection(struct gentity_s *ent, const float *origin)
{
    float tag[4][3], dir[3], length, dot;
    unsigned tagName;
    /* C1 0x5750e3..0x5750fd: only a client carrying a shield model
     * (AttachShieldModel sets ps+0x10 bit 0x100 and client+0x3a50). */
    if(!ent || !ent->client || !origin) return 0.0f;
    tagName=CODOL_PlayerShieldTag((unsigned)ent->s.number);
    if(!tagName) return 0.0f;
    /* C1 0x574f90 -> 0x571e00: the shield tag's world matrix; a missing tag
     * reads as facing away (0x575023 returns -1). */
    if(!shield_debug)
        shield_debug=Cvar_RegisterBool("codol_shieldBlastDebug",qfalse,0,
            "Print the riot shield splash protection decision");
    if(!G_DObjGetWorldTagMatrix(ent,tagName,tag)) {
        if(shield_debug && shield_debug->boolean)
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL shield blast: client %d tag %u has no world matrix\n",
                ent->s.number,tagName);
        return 0.0f;
    }
    /* C1 0x575037..0x575078: forward axis . normalize(explosion - tag). */
    dir[0]=origin[0]-tag[3][0];
    dir[1]=origin[1]-tag[3][1];
    dir[2]=origin[2]-tag[3][2];
    length=sqrtf(dir[0]*dir[0]+dir[1]*dir[1]+dir[2]*dir[2]);
    if(length>0.0f) { dir[0]/=length; dir[1]/=length; dir[2]/=length; }
    dot=tag[0][0]*dir[0]+tag[0][1]*dir[1]+tag[0][2]*dir[2];
    if(!shield_dvars()) return 0.0f;
    if(shield_debug && shield_debug->boolean)
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL shield blast: client %d tag (%.1f %.1f %.1f) forward (%.2f %.2f %.2f) dot %.3f\n",
            ent->s.number,tag[3][0],tag[3][1],tag[3][2],tag[0][0],tag[0][1],tag[0][2],dot);
    /* C1 0x57510e..0x57517d: strict comparisons against cos 15/30/60/90,
     * the half-angles of the 30/60/120/180 degree cones the dvars name. */
    if(dot>0.966f) return shield_protection[0]->value;
    if(dot>0.866f) return shield_protection[1]->value;
    if(dot>0.5f) return shield_protection[2]->value;
    if(dot>0.0f) return shield_protection[3]->value;
    return 0.0f;
}

/* Retained Scr_PlayerDamage (_g_scr_main_mp.asm): the Callback_PlayerDamage
 * dispatch G_DamageClient tail-calls. */
extern void Scr_PlayerDamage(struct gentity_s *self, struct gentity_s *inflictor,
    struct gentity_s *attacker, int damage, int dflags, int meansOfDeath, int weapon,
    const float *point, const float *dir, int hitLoc, int timeOffset);

void CODOL_RadiusDamageShieldCallback(struct gentity_s *targ, struct gentity_s *inflictor,
    struct gentity_s *attacker, int damage, int meansOfDeath, int weapon,
    const float *point, const float *dir)
{
    /* C1 0x521700: an unspecified weapon (-1, script radiusDamage) is taken
     * from the inflictor, then the attacker, else 0 (0x521060). */
    if(weapon==-1) {
        if(inflictor) weapon=inflictor->s.weapon;
        else if(attacker) weapon=attacker->s.weapon;
        else weapon=0;
    }
    if(weapon<0) weapon=0;
    Scr_PlayerDamage(targ,inflictor,attacker,damage,CODOL_DFLAGS_SHIELD_SPLASH,meansOfDeath,
        weapon,point,dir,CODOL_HITLOC_SHIELD,0);
}
