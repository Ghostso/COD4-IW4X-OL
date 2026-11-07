#ifndef CODOL_RADIUS_DAMAGE_H
#define CODOL_RADIUS_DAMAGE_H
/* C1 G_RadiusDamage (0x522950) rules the retained IW3 body lacks.
 * Both are called from G_RadiusDamage in src/asmsource/_g_combat_mp.asm.
 * SPDX-License-Identifier: AGPL-3.0-or-later */

struct gentity_s;

/* Squared distance inside which ent takes splash from an explosion of the
 * given squared radius. Players and native actors take the whole radius;
 * every other entity only min(radius, g_radiusDamageMax) (C1 0x522bc4). */
float CODOL_RadiusDamageReachSq(struct gentity_s *ent, float radiusSq);

/* Fraction of splash a riot shield attached to ent absorbs from an explosion
 * at origin, 0 when ent carries no shield or faces away (C1 0x5750e0). */
float CODOL_ShieldBlastProtection(struct gentity_s *ent, const float *origin);

/* C1 0x522d02..0x522d1a: iDFlags radius | no knockback |
 * SHIELD_EXPLOSIVE_SPLASH, and hit location 19 (C1 hitLocName[19] "shield"). */
#define CODOL_DFLAGS_SHIELD_SPLASH 0x85
#define CODOL_HITLOC_SHIELD 19

/* The splash that got past a shield goes straight to the player damage
 * callback with hitLoc shield (C1 0x521700), bypassing G_DamageClient. */
void CODOL_RadiusDamageShieldCallback(struct gentity_s *targ, struct gentity_s *inflictor,
    struct gentity_s *attacker, int damage, int meansOfDeath, int weapon,
    const float *point, const float *dir);

#endif
