/* PARENT REVIEW: archive representation updated, runtime still unvalidated.
 * The original -98 codec stores only 24 bits. CoDOL retained eFlags table
 * entries now use NATIVE_EFLAGS_BITS=32, the existing full-word delta codec,
 * for player, entity and archived-entity state. Client wire tables are separate.
 * Frame/registry/overlay integration and carrier collision review remain.
 */
/* Radar / EMP state carried by a playerState, and its publication to the CoDOL
 * wire.
 *
 * This half is deliberately free of the script VM and of level/g_entities: it
 * holds the carrier definitions, the readers, and the two translations the
 * snapshot writer needs, so a serializer only ever reads the state it is
 * serializing. The six script builtins, the level team array and the per-frame
 * producer live in codol_script_radar.h.
 *
 * =====================================================================
 * What the C1 client consumes, and where the distance test lives
 * =====================================================================
 * C1 1.1.1.13 exposes four HUD/menu expression operands for this subsystem. The
 * name table at 0x00cd0980 carries them at indices 88..91: "radarisjammed"
 * (0xc69914), "radarjamintensity" (0xc69900), "radarisenabled" (0xc698f0) and
 * "isempjammed" (0xc698e4). Each has its own handler, and each resolves the
 * local client's playerState through the obfuscated pointer
 * *(0x016d3b58 + 4*localClient) ^ 0x490b400c:
 *
 *   radarisenabled    0x005e2f60  cmp dword [ps+0x21c], 1 ; sete
 *   isempjammed       0x005e2fb0  (dword [ps+0x10] >> 10) & 1
 *   radarisjammed     0x005e5611 -> core 0x004714b0
 *   radarjamintensity 0x005e2f10 -> core 0x00471500
 *
 * The two cores, read instruction by instruction:
 *
 *   CG_RadarIsJammed 0x004714b0
 *       if (ps[0x220] != 0) return 1;                        ; 0x4714c2
 *       d = cg[0x1743f0];                                    ; 0x4714cd
 *       if (!(0 < d)) return 0;                              ; 0x4714d5
 *       if (d > radarjamDistMax) return 0;                   ; 0x4714e3..0x4714f3
 *       return 1;
 *   CG_RadarJamIntensity 0x00471500
 *       if (!CG_RadarIsJammed()) return 0.0f;                ; 0x47151b
 *       if (ps[0x220] != 0) return 1.0f;                     ; 0x47152a -> 0x471588
 *       ramp d between radarjamDistMin (*(0x016ec788)) and radarjamDistMax
 *       (*(0x016ec814)), 1 at the near end and 0 at the far end, optionally
 *       shaped by the third dvar (*(0x016ec7dc), tested as a byte at 0x47159a)
 *       through the sine helper at 0xae0e60.
 *
 * cg[0x1743f0] is produced by the client, not by the server. The per-entity add
 * loop at 0x0045b986 walks the entities of the frame and, for every entity that
 * is not the local/viewed one (the flag it computes at 0x45b994..0x45b9ba) and
 * whose **entityState eFlags (es+8) carries bit 0x200000** (test at 0x45ba83),
 * takes the distance from that entity to the local playerState's origin
 * (ps+0x1c, helper 0x403280) and keeps the smallest (0x45baa1..0x45bac0).
 *
 * So the radius and the intensity ramp are entirely client side, driven by
 * radarjamDistMin/radarjamDistMax; the server neither knows nor needs a radius.
 * The server's whole job for the local jammer is to publish one bit on the
 * jammer's own entity state, which every other client then measures its own
 * distance to. The server's job for the EMP jam and the team radar block is to
 * publish two other bits on the jammed player's own playerState. Nothing has to
 * aggregate the three: C1 reads isEMPJammed() and radarIsJammed() separately and
 * combines them itself.
 *
 * =====================================================================
 * The three bits and their widths
 * =====================================================================
 *   C1 ps 0x21c  radarEnabled  1 bit, changeHint 2 (codol_player_fields.inc
 *                entry 104); read as "== 1" by the operand above.
 *   C1 ps 0x220  radarBlocked  1 bit, changeHint 2 (entry 105); the hard-jam bit
 *                both cores test first.
 *   C1 ps 0x010  otherFlags    26 bits (entry 62). Bit 0x400 is the EMP jam; it
 *                is not a field of its own.
 *   C1 es 0x008  eFlags        full width in every eType table
 *                (codol_entity_fields.inc). Bit 0x200000 is the jammer.
 *
 * The names come from IW4, whose playerState netfield table at 0x00742020
 * carries them: entry 32 eFlags = ps+0xb0, entry 55 otherFlags = ps+0x10, and
 * three adjacent one-bit entries radarEnabled = ps+0x1a8, radarBlocked =
 * ps+0x1ac, radarMode = ps+0x1b0. C1's 0x21c/0x220 are enabled/blocked.
 * Earlier notes incorrectly inferred C1 0x224 was IW4 radarMode from nearby
 * string constants. Direct C1 43322e/433272 and435730 show 0x224 is the
 * spyplane type and0x228 the satellite type, both two-bit fields. Their native
 * producers, captured state and publication now live in codol_radar_types.
 *
 * The EMP bit is confirmed on both sides inside C1: its own setEMPJammed handler
 * at 0x005497c0 ors or clears 0x400 in client+0x10 - the gclient starts with the
 * playerState, so ps->otherFlags - which is exactly the bit its isempjammed
 * operand reads back.
 *
 * =====================================================================
 * Why ps->eFlags is the carrier
 * =====================================================================
 * All three states belong to a *playerState* in both references, and none of
 * them is keyed by a client number anywhere here. That is the whole answer to
 * delayed frames, spectators and archived history: every copy the server makes
 * of a playerState - the snapshot ring slot, the archive slot, and the
 * spectator's own storage that SpectatorClientEndFrame overwrites with the
 * followed player's archived state - carries these bits with it.
 *
 * ps->eFlags is the carrier rather than the CoDOL playerState extension, and
 * rather than the retained ps->otherFlags that C1 itself uses for the EMP bit,
 * because of what the retained archive keeps: SV_ArchiveSnapshot writes the
 * playerState with the msg.c playerStateFields table, where CoDOL now explicitly
 * selects the 32-bit eFlags codec (NATIVE_EFLAGS_BITS) while otherFlags is five bits
 * ({ PSF(otherFlags), 5, 0 }, msg.c:2408). A bit above the fifth in otherFlags
 * would be dropped by the archive and a follower on a delayed state would
 * silently lose the EMP jam. The original -98 eFlags codec was also too narrow:
 * it stores 24 bits. The CoDOL table change is required for these carriers to
 * survive archives; ordinary in-memory copies already preserve the full word.
 *
 * The jammer bit reaches other clients natively for the same reason: the
 * retained BG_PlayerStateToEntityState copies ps+0xb0 into es+8 wholesale
 * (_bg_misc.asm:2164..2167). CoDOL entity and archived-entity eFlags table entries
 * also select the 32-bit codec so the archived entity keeps the jammer bit.
 *
 * The three native bit values below are CoDOL-only carriers, deliberately not
 * the reference bit values, and they are never published as themselves. IW4's
 * own jammer bit 0x200000 is already taken in this tree: Pmove_890
 * (_bg_pmove.asm:5896) sets it on ps+0xb0. The bits chosen are not set, cleared
 * or tested by any retained producer (no or/and/test against them at ps+0xb0 or
 * es+8 anywhere in src/asmsource) and have no EF_ definition. They are NOT
 * free on C1's side: C1's compass actor update (0x433979..0x4339e8) reads
 * es+8 0x04000000 as "skip this player" and 0x08000000 as "show this player",
 * so every eFlags publisher (player ps 0x0ec, player and corpse es+8) strips
 * CODOL_PS_EF_RADAR_CARRIERS. Before that strip, a counter-UAV's team block
 * showed every jammed enemy on the caller team's compass. The two overlays
 * translate the carriers into C1's own bit positions explicitly.
 *
 * =====================================================================
 * Lifecycle
 * =====================================================================
 * Because these are playerState bits, the retained ClientSpawn's playerState
 * clear removes the per-player halves on every respawn, exactly as IW4's does -
 * which is why IW4's _emp.gsc reapplies setEMPJammed on "spawned_player" and
 * _perkfunctions.gsc reapplies radarJamOn. There is no per-client reset in this
 * subsystem *because there is no per-client store*: nothing survives a respawn
 * or a slot reuse that a reset would have to undo. A player who goes to the
 * spectators keeps the cleared state; while following, its own playerState is
 * overwritten by the followed player's archived one, so a follower publishes and
 * sees the followed player's jam and its own is not consulted. Captured
 * snapshots and archived history keep the values they were taken with, which is
 * what a delayed frame must publish.
 */
#ifndef CODOL_RADAR_STATE_H
#define CODOL_RADAR_STATE_H
#include "codol_playerstate.h"
#include "codol_entities.h"
#include "player.h"
#include "entity.h"
#ifdef __cplusplus
extern "C" {
#endif

/* CoDOL-only playerState eFlags carriers; see above. They travel with the
 * playerState, and the jammer one also with the entityState the retained
 * BG_PlayerStateToEntityState copies eFlags into. */
#define CODOL_PS_EF_RADAR_JAMMER  0x02000000
#define CODOL_PS_EF_EMP_JAMMED    0x04000000
#define CODOL_PS_EF_RADAR_BLOCKED 0x08000000
/* All three; stripped from every eFlags word published to C1, where
 * 0x04000000 and 0x08000000 are compass visibility bits of their own. */
#define CODOL_PS_EF_RADAR_CARRIERS 0x0e000000

/* The level half: the blocked counterpart of the retained
 * level.teamHasRadar[TEAM_NUM_TEAMS] at level+0x214, i.e. IW4's byte array at
 * 0x1a83580 beside its UAV array at 0x1a8357c. It lives here rather than in
 * level_locals_t because every member after level+0x214 is addressed by a
 * hardcoded offset in the retained assembly, and it lives in this half rather
 * than with the builtins so that the map/game reset does not have to link the
 * script VM. Indexed by team_t (TEAM_FREE 0, TEAM_AXIS 1, TEAM_ALLIES 2 -
 * q_shared.h:786, and the indices the retained GScr_SetTeamRadar writes for the
 * same three constants); an out of range team reads as unblocked and is ignored
 * on write rather than reading or writing past the array. */
int CODOL_TeamRadarBlocked(int team);
void CODOL_SetTeamRadarBlocked(int team, int blocked);
/* Map/game reset, from CODOL_ResetGameInput. The per-player halves need no
 * reset: they are playerState bits cleared by the retained ClientSpawn, which is
 * exactly why IW4's scripts reapply them on "spawned_player". */
void CODOL_ResetTeamRadarBlocks(void);

/* The three states a playerState carries. These read the state passed in and
 * never a live client, so an archived or spectator-followed state answers for
 * itself. A NULL state reads as not blocked / not jammed / not jamming. */
int CODOL_PlayerStateRadarBlocked(const playerState_t *ps);
int CODOL_PlayerStateEMPJammed(const playerState_t *ps);
int CODOL_PlayerStateRadarJammer(const playerState_t *ps);

/* Arm/disarm on a playerState storage. The script methods in
 * codol_script_radar.c use these on the receiver's own playerState, and the
 * per-frame producer uses the blocked one; nothing else writes these bits. */
void CODOL_PlayerStateSetRadarJammer(playerState_t *ps, int on);
void CODOL_PlayerStateSetEMPJammed(playerState_t *ps, int on);
void CODOL_PlayerStateSetRadarBlocked(playerState_t *ps, int on);

/* Publishes the playerState bits C1 reads for the state being serialized:
 * 0x21c radar enabled, from the retained ps->radarEnabled the engine produced
 * with that state, 0x220 radar blocked, and bit 0x400 of the 26-bit flags word
 * 0x010 for the EMP jam. Reads only *ps. The flags word is a read-modify-write
 * of one bit, so the mode overlay that owns other bits of it is unaffected in
 * either order. Atomic: an unknown field leaves the destination unchanged and
 * the call fails, like every other overlay in codol_engine_state.c. */
int CODOL_OverlayEngineRadar(codol_player_fields_t *wire, const playerState_t *ps);

/* Publishes C1 entityState eFlags bit 0x200000 - the jammer bit the C1 client's
 * per-entity loop measures its distance to - for a player entity state, from the
 * eFlags that state carries. One bit, read-modify-write, so the shared
 * player-entity flags overlay (which preserves every bit outside its own mask)
 * may run before or after it. */
int CODOL_OverlayEngineRadarJammer(codol_entity_state_t *wire, const entityState_t *es);

#ifdef __cplusplus
}
#endif
#endif
