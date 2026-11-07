/* The six radar / EMP script builtins, the level team-block array and the
 * per-frame producer of the blocked bit.
 *
 * The state these write, its widths, the C1 consumers that read it, why
 * ps->eFlags is the carrier and the lifecycle are all in codol_radar_state.h.
 * This header covers only the script contracts and the producer.
 *
 * Script surface (six names). Receivers, arguments and returns come from
 * iw4x.exe's own builtin tables, which name all six, and - for setEMPJammed -
 * from C1's own handler, which C1.exe still contains:
 *
 *   blockTeamRadar( <team> )        level function, table 0x79ac9c -> 0x5f9fe0
 *   unblockTeamRadar( <team> )      level function, table 0x79aca8 -> 0x5fa060
 *   isTeamRadarBlocked( <team> )    level function, table 0x79acb4 -> 0x5fa0e0
 *   <player> radarJamOn()           player method,  table 0x73d72c -> 0x5f5520
 *   <player> radarJamOff()          player method,  table 0x73d738 -> 0x5f5590
 *   <player> setEMPJammed( <on> )   player method,  table 0x73d7bc -> 0x5f58a0
 *                                   and C1 0x005497c0
 *
 * The three team entries
 * ----------------------
 * All start with Scr_GetConstString(0) and compare the result against three team
 * constants, mapping them to byte indices 2, 1 and 0 of the array at 0x1a83580;
 * anything else formats "illegal team: %s" (0x70c1a0) through va and raises
 * Scr_ParamError on parameter 0.
 *   blockTeamRadar     0x5f9ffb/0x5fa011/0x5fa023: byte[team] = 1, no return.
 *   unblockTeamRadar   0x5fa07d/0x5fa093/0x5fa0a6: the same byte = 0, no return.
 *   isTeamRadarBlocked 0x5fa0fc/0x5fa11c/0x5fa139: reads that byte and returns it
 *                      through Scr_AddInt (0x41d7d0).
 * The neighbouring pair setTeamRadar 0x5f9ec0 / getTeamRadar 0x5f9f40 uses the
 * same decoding on a *second* array at 0x1a8357c - the UAV half - and the
 * retained GScr_SetTeamRadar (_g_scr_main_mp.asm:7554) is that same function over
 * level.teamHasRadar (level+0x214..0x216), already registered in this tree. So
 * only the blocked half is added here.
 *
 * That retained decoder is also where this module's index mapping comes from
 * rather than from an equated offset: it decodes the same three constants -
 * scr_const+0xc, +0xe and +0x58, i.e. allies, axis and none (scr_vm.h) - and
 * writes level+0x216, level+0x215 and level+0x214, which is teamHasRadar indexed
 * by team_t with TEAM_FREE 0, TEAM_AXIS 1, TEAM_ALLIES 2 (q_shared.h:786). IW4's
 * order (2, 1, 0) is the same mapping. Scr_ParamError does not return - the
 * retained decoder shows the same call as its last - so the index 4 IW4 still
 * writes on the illegal-team path is unreachable and is not imitated.
 *
 * The three player methods
 * ------------------------
 * Each takes the entity from the entref and requires a client - IW4 tests
 * ent+0x158 at 0x5f553d/0x5f55ad/0x5f58cc, C1 tests its own ent+0x17c at
 * 0x005497d6 - then sets or clears one bit of that player's own playerState, and
 * returns nothing:
 *   radarJamOn/Off  IW4 0x5f5560 / 0x5f55d0 flip ps+0xb0 (eFlags) bit 0x200000.
 *                   No argument is read. C1 has no builtin of these two names
 *                   (no such string exists in C1.exe), so IW4 is the only
 *                   reference for them; the bit they set is the one C1's client
 *                   measures distances to, so the behaviour is still C1-verified
 *                   on the consuming end.
 *   setEMPJammed    C1 0x005497c0: resolve the entref (0x534a10), require the
 *                   gclient or raise "SetEMPJammed: Entity must be a player
 *                   entity" (0xc58868), read one integer (0x5cda50) and clear
 *                   (0x00549826) or set (0x00549832) 0x400 in client+0x10, i.e.
 *                   ps->otherFlags. IW4 0x5f58e4/0x5f58f6 does the same with the
 *                   same bit. Any non-zero value is on. The argument is read
 *                   after the receiver is accepted, as both handlers do.
 * Both references write the playerState of whatever player entity they were
 * given, including a spectator's own - which SpectatorClientEndFrame overwrites
 * on its next follow copy - and never the followed player's.
 *
 * The producer
 * ------------
 * IW4's ClientEndFrame 0x005d7f25 publishes both halves at 0x005d8070:
 *     team = client[0x31dc]
 *     ps->radarEnabled(0x1a8) = teamHasRadar[team]     || client->hasradar
 *     ps->radarBlocked(0x1ac) = teamRadarBlocked[team] || client->isradarblocked
 *     ps->radarMode(0x1b0)    = client->radarmode
 * (IW4's client field table at 0x0073c318 names those gclient members:
 * 'hasradar' client+0x3258, 'isradarblocked' client+0x325c, 'radarmode'
 * client+0x3260. C1's table at 0x00c3c078 keeps the same shape with its own
 * names: 'hasspyplane' client+0x3890, 'hassatellite' client+0x3894,
 * 'isradarblocked' client+0x35a4, 'motiontrackerenabled' client+0x35a8.)
 *
 * The retained tree already has IW4's first line: ClientEndFrame_300..420
 * (_g_active_mp.asm:686..699) computes
 * radarEnabled = teamHasRadar[client->sess.cs.team] || client->hasRadar, with
 * client+0x3010 = sess.cs.team and client+0x3178 = the 'hasradar' script field
 * (g_client_fields.cpp:447). CODOL_PublishClientRadar is the second line, called
 * from the same point, so a player who joins, changes team or respawns into a
 * blocked team is blocked without the script repeating the call - the IW4 model,
 * where the level array is read per player per frame. It is not called on the
 * following-spectator path, for the same reason the HUD icon publisher is not:
 * that path copies the followed player's archived playerState over the
 * follower's, and publishing after it would overwrite the state the follower is
 * meant to see.
 *
 * The per-client input is stored in codol_radar_input.c and exposed by custom
 * g_client_fields.cpp callbacks for isradarblocked (C1 client+35a4). Its integer
 * script value is ORed with the team input here, before snapshot capture.
 * Connection, map and spawn resets clear the script input independently.
 */
#ifndef CODOL_SCRIPT_RADAR_H
#define CODOL_SCRIPT_RADAR_H
#include "codol_radar_state.h"
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Script entry points. Registered in scr_vm_main.c. */
void CODOL_Scr_BlockTeamRadar(void);
void CODOL_Scr_UnblockTeamRadar(void);
void CODOL_Scr_IsTeamRadarBlocked(void);
void CODOL_Scr_RadarJamOn(scr_entref_t ref);
void CODOL_Scr_RadarJamOff(scr_entref_t ref);
void CODOL_Scr_SetEMPJammed(scr_entref_t ref);

/* Producer: publishes level.teamRadarBlocked[team] into this client's live
 * playerState, once per frame, from the retained ClientEndFrame playing path -
 * the same point and the same shape as the retained store of ps->radarEnabled it
 * mirrors. Takes a client number because that path holds one. Ignores a number
 * without a gclient. */
void CODOL_PublishClientRadar(unsigned client);

#ifdef __cplusplus
}
#endif
#endif
