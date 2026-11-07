/* The six radar / EMP builtins, the level team-block array and the per-frame
 * producer. Contracts and evidence: codol_script_radar.h; the state they write
 * and its wire publication: codol_radar_state.h. */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_script_radar.h"
#include "codol_radar_input.h"
#include "codol_radar_types.h"
#include "codol_playerstate_ext.h"
#include "cscr_stringlist.h"
#include "qcommon_io.h"

/* allies -> TEAM_ALLIES, axis -> TEAM_AXIS, none -> TEAM_FREE: the mapping the
 * retained GScr_SetTeamRadar makes for the same array (see the header). */
static int codol_radar_team_index(unsigned param, int *out)
{
    unsigned short name = (unsigned short)Scr_GetConstString(param);
    if (name == scr_const.allies) { *out = TEAM_BLUE; /* allies */ return 1; }
    if (name == scr_const.axis) { *out = TEAM_RED; /* axis */ return 1; }
    if (name == scr_const.none) { *out = TEAM_FREE; return 1; }
    /* Does not return; the index 4 IW4 writes afterwards is unreachable. */
    Scr_ParamError(0, va("illegal team: %s", SL_ConvertToString(name)));
    return 0;
}

/* C1's setEMPJammed at 0x005497c0 requires ent+0x17c, its gclient pointer, and
 * raises "SetEMPJammed: Entity must be a player entity" (0xc58868) when it is
 * absent; IW4's three methods test the same thing at 0x5f553d/0x5f55ad/0x5f58cc.
 * Only entities below maxclients can have a gclient, so the range test is that
 * test. C1 has no builtin named radarJamOn/radarJamOff, so its wording is
 * followed for all three methods rather than inventing a second style. */
static gentity_t *codol_radar_player(scr_entref_t ref, const char *method)
{
    gentity_t *entity;
    if (ref.classnum) {
        Scr_ObjectError(va("%s: Entity must be a player entity", method)); return NULL;
    }
    if (ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients) {
        Scr_ObjectError(va("%s: Entity must be a player entity", method)); return NULL;
    }
    entity = &g_entities[ref.entnum];
    if (!entity->client) {
        Scr_ObjectError(va("%s: Entity must be a player entity", method)); return NULL;
    }
    return entity;
}

/* Ability 35 modInvalidCounterUav (Stalker Pro, specialty_delaymine). C1's
 * PERKS_DESC_STALKER_PRO ends with "cancels the enemy counter-UAV effect".
 * Nothing on the C1 client exempts the holder: CG_RadarIsJammed 0x004714b0
 * returns 1 as soon as ps+0x220 (radarBlocked) is non-zero, before and
 * independently of any ability test, and no C1 reader of ability 35 exists in
 * its game code either. So the exemption has to be in what the server
 * publishes as radarBlocked, which in this tree only ever carries the
 * counter-UAV: the team block (_uav.gsc updateTeamUAVStatus) and, in
 * free-for-all, the per-player isRadarBlocked input (updatePlayersUAVStatus).
 * The EMP is a different bit (ps->otherFlags 0x400, setEMPJammed) and the
 * portable jammer is the jammer's own eFlags bit measured client side, so
 * neither is touched by this exemption. MSB-first mask word 1, bit 31-3. */
#define CODOL_RADAR_ABILITY_INVALID_COUNTER_UAV 35u
static int codol_radar_ignores_counter_uav(const playerState_t *ps)
{
    const codol_ps_ext_t *ext = CODOL_PlayerStateExtConst(ps);
    return ext && ext->abilities_known &&
        (ext->abilities.masks[CODOL_RADAR_ABILITY_INVALID_COUNTER_UAV >> 5] &
         (0x80000000u >> (CODOL_RADAR_ABILITY_INVALID_COUNTER_UAV & 31u))) != 0;
}

void CODOL_PublishClientRadar(unsigned client)
{
    gclient_t *player;
    /* IW4 ClientEndFrame 0x005d8090:
     *     ps->radarBlocked = teamRadarBlocked[client[0x31dc]] ||
     *                        client->isradarblocked
     * client[0x31dc] is its session team, the same input the retained
     * ClientEndFrame_300 reads from client+0x3010 for the enabled half. The
       * second operand is the native script-owned radar input. It is kept
       * separate from the published bit so team blocking never changes script
       * reads and following another player never replaces this input.
       * The state is rewritten every
     * frame either way, so a team change or a respawn needs no script call. */
    if (client >= MAX_CLIENTS || (int)client >= level.maxclients) return;
    player = g_entities[client].client;
    if (!player) return;
    CODOL_PublishClientRadarTypes(client);
    CODOL_PlayerStateSetRadarBlocked(&player->ps,
        !codol_radar_ignores_counter_uav(&player->ps) &&
        (CODOL_TeamRadarBlocked((int)player->sess.cs.team) ||
         CODOL_ClientRadarBlockInput(client)));
}

void CODOL_Scr_BlockTeamRadar(void)
{
    int team;
    /* IW4 0x5f9ffb/0x5fa011/0x5fa023: byte[team] = 1, no return. */
    if (!codol_radar_team_index(0, &team)) return;
    CODOL_SetTeamRadarBlocked(team, 1);
}

void CODOL_Scr_UnblockTeamRadar(void)
{
    int team;
    /* IW4 0x5fa07d/0x5fa093/0x5fa0a6: the same byte = 0, no return. */
    if (!codol_radar_team_index(0, &team)) return;
    CODOL_SetTeamRadarBlocked(team, 0);
}

void CODOL_Scr_IsTeamRadarBlocked(void)
{
    int team;
    /* IW4 0x5fa0fc/0x5fa11c/0x5fa139 read the byte and answer through
     * Scr_AddInt (0x41d7d0). */
    if (!codol_radar_team_index(0, &team)) return;
    Scr_AddInt(CODOL_TeamRadarBlocked(team));
}

void CODOL_Scr_RadarJamOn(scr_entref_t ref)
{
    gentity_t *entity = codol_radar_player(ref, "RadarJamOn");
    if (!entity) return;
    /* IW4 0x5f5560 sets one playerState eFlags bit and returns nothing; no
     * argument is read. The bit reaches other clients through the entity state
     * the retained BG_PlayerStateToEntityState fills, and each of them measures
     * its own distance to it. */
    CODOL_PlayerStateSetRadarJammer(&entity->client->ps, 1);
}

void CODOL_Scr_RadarJamOff(scr_entref_t ref)
{
    gentity_t *entity = codol_radar_player(ref, "RadarJamOff");
    if (!entity) return;
    /* IW4 0x5f55d0 clears the same bit. */
    CODOL_PlayerStateSetRadarJammer(&entity->client->ps, 0);
}

void CODOL_Scr_SetEMPJammed(scr_entref_t ref)
{
    gentity_t *entity = codol_radar_player(ref, "SetEMPJammed");
    if (!entity) return;
    /* C1 0x00549817 and IW4 0x5f58e4 read argument zero as an integer and treat
     * any non-zero value as on; C1 clears the bit at 0x00549826 and sets it at
     * 0x00549832. The argument is read only after the receiver is accepted, as
     * both handlers do. */
    CODOL_PlayerStateSetEMPJammed(&entity->client->ps, Scr_GetInt(0) != 0);
}
#endif
