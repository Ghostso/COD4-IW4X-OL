/* The melee hit's events, as C1's own server produces them.
 *
 * Weapon_Melee_internal (src/asmsource/_g_weapon.asm) calls this once the
 * trace has resolved the struck entity, in place of IW3's blood event and
 * temp entity. C1 is client and server in one binary, so its producer at
 * 0x573a20 defines what the C1 client expects:
 *
 *   blood   0x573c3b..0x573c7c  EV_MELEE_BLOOD on the attacker, only when the
 *           attacker is a player, the struck entity is a player or an actor,
 *           the hit is not on a riot shield (trace partGroup 19, 0x573bb0),
 *           and the two are not on the same team (OnSameTeam 0x56f1e0). The
 *           one exception is a hashed enum dvar at 0x220cfa0 whose values are
 *           beginner_l..hardcore_l (registered at 0x52a814, default 1):
 *           at 4 teammates bleed too. This server has no such setting, so the
 *           exception never applies, as on C1 at its default.
 *   event   0x573c86..0x573ca6  EV_MELEE_HIT on a player or actor, else
 *           EV_MELEE_MISS; IW3 counted only players.
 *   fields  +80 struck entity (0x573cad), +d4 attacker weapon (0x573cc1),
 *           +d6 attacker's knife row (0x573cd4, see below), +e6 weapon model
 *           (0x573ce1), +ac parameter: bit 0 when the weapon has a viewmodel
 *           knife (def+0x2c, C1's knifeModel; IW3's is def+0x304) and the
 *           attacker is a player (0x573ce7..0x573d00), bit 1 on a riot-shield
 *           hit (0x573d0a..0x573d11).
 *
 * The knife row is the mp/coKnifeStatsTable.csv row an attacking player
 * carries (es+0x64, read at 0x573a5f only for eType 1); C1 writes it only
 * when that row resolves. It rides in the temp entity's un2 until the snapshot
 * overlay (CODOL_OverlayEngineMeleeEvent) publishes it.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "q_shared.h"
#include "entity.h"
#include "g_shared.h"
#include "g_public.h"
#include "bg.h"
#include "cm_public.h"
#include "xassets/weapondef.h"
#include "codol_weapon_give.h"
#include "codol_radius_damage.h"
#include "codol_engine_state.h"

extern gentity_t *G_TempEntity(const float *origin, int event);
extern void __cdecl G_AddEvent(gentity_t *ent, int event, int parm);

/* coKnifeStatsTable.csv ships 21 rows (docs/CODOL_MELEE_C1_PATH_20260920.md). */
#define CODOL_KNIFE_TABLE_ROWS 21u

static int melee_character(const gentity_t *ent)
{
    return ent->client || ent->s.eType == ET_ACTOR;
}

gentity_t *__cdecl CODOL_MeleeHitEvent(gentity_t *attacker, gentity_t *target,
    const codol_weaponParms_t *wp, const trace_t *trace, const float *endpos)
{
    gentity_t *tent;
    int shield = trace->partGroup == CODOL_HITLOC_SHIELD;
    int character = melee_character(target);
    unsigned row = 0;

    if (attacker->client && character && !shield && !OnSameTeam(attacker, target))
        G_AddEvent(attacker, EV_MELEE_BLOOD, 0);

    tent = G_TempEntity(endpos, character ? EV_MELEE_HIT : EV_MELEE_MISS);
    tent->s.otherEntityNum = target->s.number;
    tent->s.eventParm = (wp->weapDef && wp->weapDef->knifeModel && attacker->client ? 1 : 0) |
                        (shield ? 2 : 0);
    tent->s.weapon = attacker->s.weapon;
    tent->s.weaponModel = attacker->s.weaponModel;
    if (attacker->s.eType == ET_PLAYER) {
        row = CODOL_ServerMeleeRow();
        if (row > CODOL_KNIFE_TABLE_ROWS) row = 0;
    }
    tent->s.un2 = (int)row;
    return tent;
}
