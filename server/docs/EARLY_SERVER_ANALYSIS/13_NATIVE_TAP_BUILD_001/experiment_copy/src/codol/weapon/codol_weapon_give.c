/* Five retained IW3 weapon primitives ported to C so the retained assembly no
 * longer touches the per-weapon playerState arrays inside them
 * (docs/CODOL_WEAPON_TABLE_20260915.md, "Function ports" section):
 *
 *   CODOL_GivePlayerWeapon        <- G_GivePlayerWeapon      _g_weapon.asm:944
 *   CODOL_UseOffHand              <- G_UseOffHand            _g_weapon.asm:740
 *   CODOL_PlayerCmd_dropItem      <- PlayerCmd_dropItem      _g_client_script_cmd_mp.asm:991
 *   CODOL_PlayerCmd_giveMaxAmmo   <- PlayerCmd_giveMaxAmmo   _g_client_script_cmd_mp.asm:5492
 *   CODOL_PlayerCmd_giveStartAmmo <- PlayerCmd_giveStartAmmo _g_client_script_cmd_mp.asm:5578
 *
 * The names are distinct from the retained symbols on purpose: the assembly
 * bodies stay in the tree until the owner of the asm files retargets their
 * callers (the anchored diffs are in the doc section named above), so both can
 * be linked at once. The algorithm is the retained assembly's, branch for
 * branch, including the CODOL_SERVER paths it already carried (no IW3 offhand
 * auto-select on acquisition; CODOL_WeaponStateOffhandGranted after a grant).
 *
 * Ownership / raised-before / rechamber / model state goes through the
 * 700-wide CODOL_WeaponBits* API (codol_weapon_bits.h), never the ps arrays.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "q_shared.h"
#include "q_math.h"
#include "g_shared.h"
#include "server.h"
#include "scr_vm.h"
#include "bg_public.h"
#include "xassets/weapondef.h"
#include "codol_weapon_bits.h"
#include "codol_weapon_slots.h"
#include "codol_weapon_state.h"
#include "codol_weapon_give.h"
#include <string.h>

struct gitem_s;
/* Retained assembly callees (global cdecl symbols unless noted). */
extern int __cdecl BG_GetAmmoPlayerMax(const playerState_t *ps, unsigned weapon, unsigned flag);
extern void __cdecl Add_Ammo(gentity_t *ent, unsigned weapon, unsigned char model, int count, int fillClip);
extern gentity_t *__cdecl Drop_Weapon(gentity_t *ent, int weapon, unsigned char model, unsigned int tag);
extern gentity_t *__cdecl Drop_Item(gentity_t *ent, const struct gitem_s *item, float angle, int flags);
extern struct gitem_s *__cdecl G_FindItem(const char *name, int flags);
extern unsigned int __cdecl Scr_GetConstLowercaseString(unsigned int param);
extern void __cdecl GScr_AddEntity(gentity_t *ent);
/* _g_client_script_cmd_mp.asm G_InitializeAmmo(gentity_s*, int, unsigned char, int):
 * eax = ent, edx = weapon, cl = model, the fourth argument on the stack. */
extern int __attribute__((regparm(3))) G_InitializeAmmo(gentity_t *ent, int weapon, unsigned char model, int flags);
extern void __cdecl Weapon_Throw_Grenade(gentity_t *ent, int weapon, unsigned char model, codol_weaponParms_t *parms);

static void grant(const playerState_t *ps, unsigned weapon, unsigned char model)
{
    CODOL_WeaponBitsOwnedSet(ps, weapon, 1);
    CODOL_WeaponBitsRechamberSet(ps, weapon, 0);
    CODOL_WeaponBitsOldSet(ps, weapon, 0);
    CODOL_WeaponBitsModelSet(ps, weapon, model);
}

int __cdecl CODOL_GivePlayerWeapon(playerState_t *ps, int weapon, unsigned char model)
{
    struct WeaponDef *def;
    unsigned alt;
    if (!ps || weapon <= 0 || (unsigned)weapon >= CODOL_WEAPON_SLOTS) return 0;
    if (CODOL_WeaponBitsOwned(ps, (unsigned)weapon)) return 0;          /* asm :963-965 */
    def = BG_GetWeaponDef(weapon);
    if (!def) return 0;
    /* asm :1001-1009: weapClass 7 and 8 skip the model check; every other
     * class needs gunXModel[model] to exist. */
    if (def->weapClass != 7 && def->weapClass != 8 &&
        (model >= 16 || !def->gunXModel[model])) {
        /* A refused give is silent to script (hasWeapon just stays false);
         * say which weapon and why, once per weapon index. */
        static unsigned char reported[CODOL_WEAPON_SLOTS];
        if (com_developer && com_developer->integer && !reported[weapon]) {
            reported[weapon] = 1;
            Com_DPrintf(CON_CHANNEL_SERVER, "CoDOL give refused: %s (index %d) has no gun model %u (class %d)\n",
                def->szInternalName ? def->szInternalName : "?", weapon, (unsigned)model, (int)def->weapClass);
        }
        return 0;
    }
    grant(ps, (unsigned)weapon, model);                              /* asm :1010-1023 */
    /* asm :1024-1035: weapClass 9 and any offhand class stop here (under
     * CODOL_SERVER the offhand slot is raised on input, never on acquisition).
     * Otherwise walk the altWeaponIndex chain and grant each alternate that is
     * not already owned (asm :1074-1111). */
    if (def->weapClass != 9 && def->offhandClass == 0) {
        alt = def->altWeaponIndex;
        while (alt && alt < CODOL_WEAPON_SLOTS && !CODOL_WeaponBitsOwned(ps, alt)) {
            const struct WeaponDef *altdef;
            grant(ps, alt, model);
            altdef = BG_GetWeaponDef((int)alt);
            if (!altdef) break;
            alt = altdef->altWeaponIndex;
        }
    }
    CODOL_WeaponStateOffhandGranted(ps, (unsigned)weapon);           /* asm :966-985 */
    return 1;
}

void __cdecl CODOL_UseOffHand(gentity_t *ent)
{
    gclient_t *client;
    playerState_t *ps;
    codol_weaponParms_t parms;
    vec3_t angles;
    if (!ent || !(client = ent->client)) return;
    ps = &client->ps;
    memset(&parms, 0, sizeof(parms));
    /* asm :755-763: pitch/yaw from client->fGunPitch/fGunYaw (gclient+0x30a4/
     * +0x30a8), roll from ps->viewangles[2]. */
    angles[0] = client->fGunPitch;
    angles[1] = client->fGunYaw;
    angles[2] = ps->viewangles[2];
    AngleVectors(angles, parms.forward, parms.right, parms.up);
    G_GetPlayerViewOrigin(ps, parms.muzzleTrace);
    parms.weapDef = BG_GetWeaponDef(ps->offHandIndex);
    Weapon_Throw_Grenade(ent, ps->offHandIndex,
        (unsigned char)CODOL_WeaponBitsModelGet(ps, (unsigned)ps->offHandIndex), &parms);
}

static gentity_t *give_player_entity(scr_entref_t ref)
{
    if (ref.classnum) { Scr_ObjectError("not an entity"); return NULL; }
    if (ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients ||
        !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum));
        return NULL;
    }
    return &g_entities[ref.entnum];
}

/* <player> dropItem(<weaponName>[, <tag>]) */
void CODOL_PlayerCmd_dropItem(scr_entref_t ref)
{
    gentity_t *ent = give_player_entity(ref);
    const char *name;
    int weapon;
    struct gitem_s *item;
    if (!ent) return;
    name = Scr_GetString(0);
    weapon = G_GetWeaponIndexForName(name);
    if (weapon) {
        /* asm :1020-1029 / :1068-1071: second argument, else scr_const+0xac
         * (tag_weapon_right). */
        unsigned int tag = Scr_GetNumParam() > 1 ? Scr_GetConstLowercaseString(1)
                                                 : scr_const.tag_weapon_right;
        GScr_AddEntity(Drop_Weapon(ent, weapon,
            (unsigned char)CODOL_WeaponBitsModelGet(&ent->client->ps, (unsigned)weapon), tag));
        return;
    }
    /* asm :1048-1063: not a weapon; try an item, undefined when neither. */
    item = G_FindItem(name, 0);
    GScr_AddEntity(item ? Drop_Item(ent, item, 0.0f, 0) : NULL);
}

/* <player> giveMaxAmmo(<weaponName>) */
void CODOL_PlayerCmd_giveMaxAmmo(scr_entref_t ref)
{
    gentity_t *ent = give_player_entity(ref);
    playerState_t *ps;
    unsigned weapon;
    struct WeaponDef *def;
    int add;
    if (!ent) return;
    ps = &ent->client->ps;
    weapon = (unsigned)G_GetWeaponIndexForName(Scr_GetString(0));
    if (!CODOL_WeaponBitsOwned(ps, weapon)) return;                      /* asm :5522-5532 */
    def = BG_GetWeaponDef((int)weapon);
    if (!def) return;
    add = BG_GetAmmoPlayerMax(ps, weapon, 0) - ps->ammo[def->iAmmoIndex]; /* asm :5540-5550 */
    if (add <= 0) return;
    Add_Ammo(ent, weapon, (unsigned char)CODOL_WeaponBitsModelGet(ps, weapon), add, 0);
}

/* <player> giveStartAmmo(<weaponName>) */
void CODOL_PlayerCmd_giveStartAmmo(scr_entref_t ref)
{
    gentity_t *ent = give_player_entity(ref);
    playerState_t *ps;
    unsigned weapon;
    if (!ent) return;
    ps = &ent->client->ps;
    weapon = (unsigned)G_GetWeaponIndexForName(Scr_GetString(0));
    if (!CODOL_WeaponBitsOwned(ps, weapon)) return;                      /* asm :5606-5617 */
    G_InitializeAmmo(ent, (int)weapon, (unsigned char)CODOL_WeaponBitsModelGet(ps, weapon), 0);
}
