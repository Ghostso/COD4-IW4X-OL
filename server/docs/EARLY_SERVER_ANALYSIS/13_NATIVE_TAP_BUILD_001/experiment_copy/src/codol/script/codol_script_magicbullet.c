#ifdef CODOL_SERVER
/* Native magicbullet(weapon, start, end[, attacker]).
 * IW4 handler497ed0, registry79a92c. Arguments and weapon lookup are validated
 * before firing; an explicit attacker must be a player, otherwise world owns
 * the shot. Hitscan returns undefined; grenade-launcher and rocket projectile
 * classes return their spawned entity. Grenade weapon TYPE is rejected.
 *
 * Both projectile paths restore explicit owner handles and every successful
 * shot emits EV_FIRE_WEAPON with its weapon index. Scripted rockets skip the
 * player's kickback and launch delay. Direction is normalized directly (zero
 * remains zero), with zero side axes and spread, matching the reference.
 *
 * Producers use this server's retained native weapon/trace/missile machinery;
 * no IW4 offsets are reused as native offsets. Evidence and remaining runtime
 * validation are recorded in docs/CODOL_IMPLEMENTATION_PASS.json. Historical
 * worker claims in obj/claude-workers/magicbullet-r1-report.md are superseded
 * by the parent review entries there. This implementation is not runtime tested.
 */
#include "codol_script_magicbullet.h"
#include "scr_vm.h"
#include "g_shared.h"
#include "entity.h"
#include "q_math.h"
#include "bg.h"
#include "xassets/weapondef.h"

/* G_GetWeaponIndexForName (src/g_shared.h) and BG_GetWeaponDef
 * (src/xassets/weapondef.h) are already declared by the headers above. */

/* Same 0x40-byte native call layout src/codol_script_turret_target.cpp already
 * established for these two producers (three axis rows, shot origin, a
 * copy of the direction, and the WeaponDef Bullet_Fire dereferences at
 * +0x3c). Kept as an independent local copy, per this file's ownership
 * scope, with the same compile-time size guard. */
typedef struct
{
    vec3_t forward;
    vec3_t right;
    vec3_t up;
    vec3_t start;
    vec3_t dir;
    struct WeaponDef *weapDef;
} codol_magicBulletFireParams_t;

typedef char codol_magicBulletFireParams_size_check[
    (sizeof(codol_magicBulletFireParams_t) == 0x40) ? 1 : -1];

extern void Bullet_Fire(gentity_t *attacker, float spread, void *fireParams,
                        gentity_t *weaponEnt, int time);
/* Native script entry shares rocket creation and omits physical kickback. */
extern gentity_t *CODOL_Weapon_RocketLauncher_FireScript(gentity_t *ent, int weapon,
                                             float spread, void *fireParams,
                                             const float *velocity,
                                             gentity_t *target, const float *targetOffset);
extern gentity_t *Weapon_GrenadeLauncher_Fire(gentity_t *ent, int weapon,
                                             unsigned char mode, void *fireParams);
extern gentity_t *G_TempEntity(const float *origin, int event);

/* IW4 498081..4980ad creates event 30 at the copied start position, sets
 * the weapon and clears its parameter. Event-name table 795748 starts with
 * EV_NONE; entry30 at7957c0 names EV_FIRE_WEAPON. Use the native semantic
 * ID so the existing CoDOL event and weapon mapping handles publication. */
static void magicbullet_publish_shot(const float start[3], int weapon)
{
    gentity_t *event = G_TempEntity(start, EV_FIRE_WEAPON);
    if(!event) return;
    event->s.weapon = weapon;
    event->s.eventParm = 0;
    event->s.eventParms[event->s.eventSequence & 3] = 0;
}

void CODOL_Scr_MagicBullet(void)
{
    const char *weaponName;
    int weaponIndex;
    struct WeaponDef *weapDef;
    vec3_t start, end, dir;
    codol_magicBulletFireParams_t params;
    gentity_t *owner;
    gentity_t *missile;
    int explicitOwner;

    if (Scr_GetNumParam() < 3)
    {
        Scr_Error("MagicBullet invalid parameters");
        return;
    }

    /* Traced order (0x497ed0): the optional attacker is resolved and
     * validated before the weapon name, which is resolved before the
     * vectors. Matched here so multi-error scripts surface the same
     * first error the reference would. */
    explicitOwner = Scr_GetNumParam() > 3;
    if (explicitOwner)
    {
        owner = Scr_GetEntity(3);
        if (!owner)
        {
            return;
        }
        if (!owner->client)
        {
            Scr_Error("Owner must be a player.");
            return;
        }
    }
    else
    {
        /* IW4 (19bd0f0 - 18835d8) / 274 == 2046, its world slot.
         * Use the retained world's semantic index, not IW4's numeric slot. */
        owner = &g_entities[ENTITYNUM_WORLD];
    }

    weaponName = Scr_GetString(0);
    weaponIndex = G_GetWeaponIndexForName(weaponName);
    if (!weaponIndex)
    {
        Scr_Error(va("MagicBullet called with unknown weapon name %s",
                             weaponName));
        return;
    }
    weapDef = BG_GetWeaponDef(weaponIndex);

    Scr_GetVector(1, start);
    Scr_GetVector(2, end);

    VectorSubtract(end, start, dir);
    /* IW4 453500 normalizes in place using divisor1 for zero length, so a
     * coincident start/end remains zero. Do not invent a vertical shot or
     * round-trip through Euler angles. 498015..49802b explicitly zeroes
     * both side axes; this script shot supplies no spread basis. */
    Vec3NormalizeTo(dir, dir);
    VectorCopy(dir, params.forward);
    VectorClear(params.right);
    VectorClear(params.up);
    VectorCopy(start, params.start);
    VectorCopy(dir, params.dir);
    params.weapDef = weapDef;

    if (weapDef->weapType == WEAPTYPE_BULLET)
    {
        /* Aimed shot along the given line, not a spread cone. */
        /* IW4 498159 passes NULL weaponEnt. Bullet_Fire440389 maps that
         * to its world trace index; retained Bullet_Fire_20 does the same.
         * Damage attribution still uses the separate owner argument. */
        Bullet_Fire(owner, 0.0f, &params, NULL, level.time);
        magicbullet_publish_shot(start, weaponIndex);
        return;
    }
    if (weapDef->weapType == WEAPTYPE_PROJECTILE)
    {
        if (weapDef->weapClass == WEAPCLASS_GRENADE)
        {
            missile = Weapon_GrenadeLauncher_Fire(owner, weaponIndex, 0, &params);
            if (missile) {
                Scr_AddEntity(missile);
                if(explicitOwner) CODOL_MagicBulletSetOwner(missile, owner);
            }
            magicbullet_publish_shot(start, weaponIndex);
            return;
        }
        /* IW4 stops at rocket launchers and raises for every other projectile
         * class. T5 GScr_MagicBullet (OpenBLOPS g_scr_main_mp.cpp:13838)
         * also fires a WEAPCLASS_TURRET projectile weapon through
         * Weapon_RocketLauncher_Fire. C1's SAM turret is T5's: its launcher
         * tow_turret_mp is a turret-class projectile (class 7, type 2), and
         * there is no separate rocket-class SAM missile to fire instead, so
         * the T5 case is the one C1 content needs. */
        if (weapDef->weapClass == WEAPCLASS_ROCKETLAUNCHER ||
            weapDef->weapClass == WEAPCLASS_TURRET)
        {
            missile = CODOL_Weapon_RocketLauncher_FireScript(owner, weaponIndex, 0.0f,
                                                 &params, vec3_origin, NULL, NULL);
            if (missile)
            {
                /* IW4 magicbullet supplies final flag1 (498118), which
                 * G_FireRocket490bd3 tests to skip the player launch delay.
                 * The retained producer has no corresponding argument; its
                 * launchTime adjustment is complete before this return. */
                missile->s.lerp.u.missile.launchTime = level.time;
                Scr_AddEntity(missile);
                if(explicitOwner) CODOL_MagicBulletSetOwner(missile, owner);
            }
            magicbullet_publish_shot(start, weaponIndex);
            return;
        }
        Scr_Error("MagicBullet(): Unhandled projectile weapClass.");
        return;
    }
    if(weapDef->weapType == WEAPTYPE_GRENADE) {
        /* IW4 49802f tests the weapon TYPE, not projectile class6. */
        Scr_Error("MagicBullet() does not work with grenade-type weapons.");
        return;
    }
    Scr_Error("MagicBullet(): Unhandled weapType.");
}
#endif
