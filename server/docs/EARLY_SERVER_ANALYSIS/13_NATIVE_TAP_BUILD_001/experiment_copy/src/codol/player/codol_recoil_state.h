/* Per-playerState fire-recoil scale (player_recoilScaleOn / player_recoilScaleOff).
 *
 * IW4 owns this pair. iw4x.exe registers them as player methods at 0x73c934 /
 * 0x73c940; the handlers at 0x5dd2d0 / 0x5dd370 read one integer, reject
 * anything outside 0..100 with "Given scale must be between %i and %i.", then
 * set ps flags bit 0x400 (ps+0x2bc) and store the percentage at ps+0x3110.
 * IW4's BG_WeaponFireRecoil folds that percentage into the recoil scale at
 * 0x4a60c8: scale *= (float)(percent / 100.0).
 *
 * C1.exe 1.1.1.13 keeps the same pair. Scr_PlayerRecoilScaleOn @0x00519750
 * arms weapFlags bit 0x400 (ps+0x344, alpha0022 equipment.py PS_WEAP_FLAGS)
 * and stores the percentage at ps+0x3330; Scr_PlayerRecoilScaleOff @0x00519850
 * clears the bit only. C1's BG_WeaponFireRecoil @0x00422150 consumes both at
 * 0x004222b6, multiplying the same scale that feeds the view kick (0x004222de)
 * and the gun-speed accumulator (0x00422418) - one scale, both outputs.
 *
 * T5 provides no fallback: CoDMPServer has neither builtin, and its
 * BG_WeaponFireRecoil (0x0045ae50, map bg_weapons.obj) has no scale branch.
 * It does confirm the shared signature
 * BG_WeaponFireRecoil(const playerState_s *, float *speed, float *kick).
 *
 * State model
 * -----------
 * Both engines keep flag and magnitude inside the playerState, so both travel
 * with every playerState copy. Here the flag is the retained weapFlags bit
 * CODOL_WEAP_RECOIL_SCALE, which travels with the bytes, and the magnitude is
 * the playerState extension (codol_playerstate_ext.h), which travels with the
 * same copies, is serialized into the archived-snapshot stream beside the
 * playerState it belongs to, and is handed through scratch buffers as an
 * explicit value. Both are therefore properties of the *state*, not of a
 * client number: a spectator following an archived playerState - including one
 * rebuilt from the archive stream - gets the magnitude that was armed when
 * that state was archived.
 *
 * Consumers
 *   - CODOL_PlayerRecoilScale is called from the retained BG_WeaponFireRecoil
 *     (_bg_weapons.asm, BG_WeaponFireRecoil_80) and scales the kick angles and
 *     the client->vGunSpeed accumulation the server computes on every fire
 *     event (G_PlayerEvent, _g_active_mp.asm).
 *   - CODOL_OverlayEngineRecoilScale publishes weapFlags bit 0x400 and the
 *     percentage through the measured C1 playerState fields 0x344 and 0x3330,
 *     so the client's own BG_WeaponFireRecoil applies the identical scale to
 *     its predicted recoil.
 */
#ifndef CODOL_RECOIL_STATE_H
#define CODOL_RECOIL_STATE_H
#include "player.h"
#include "codol_playerstate.h"
#include "codol_playerstate_ext.h"
#ifdef __cplusplus
extern "C" {
#endif

/* IW4 0x5dd32e..0x5dd335 and C1 0x005197e3..0x005197ea reject scale < 0 and
 * scale > 100. The C1 wire field at 0x3330 is seven bits wide, which holds the
 * whole accepted range. */
#define CODOL_RECOIL_SCALE_MIN 0
#define CODOL_RECOIL_SCALE_MAX 100

/* Record the magnitude on this playerState's storage and arm the flag, the way
 * C1 0x0051982f/0x00519839 writes both halves of its own playerState. Rejects
 * a percentage outside the accepted range and leaves the state untouched. */
int CODOL_ArmPlayerRecoilScale(playerState_t *ps, int percent);
/* Clear the flag and keep the magnitude, as C1 0x005198da does. */
void CODOL_DisarmPlayerRecoilScale(playerState_t *ps);
/* The recorded magnitude for a state, or -1 when none was recorded. */
int CODOL_PlayerRecoilScalePercent(const playerState_t *ps);

/* Retained-assembly consumer. Returns the multiplier BG_WeaponFireRecoil
 * applies to its shared kick/speed scale: percent/100 while the playerState
 * carries CODOL_WEAP_RECOIL_SCALE and a magnitude is recorded for it,
 * otherwise exactly 1.0f. An armed state whose magnitude was never recorded is
 * left unscaled rather than silently reduced to no recoil at all. */
float CODOL_PlayerRecoilScale(const playerState_t *ps);

/* Publish the armed bit and the percentage through the C1 playerState fields
 * 0x344 bit 0x400 and 0x3330. Atomic: unknown fields leave the destination
 * unchanged. */
int CODOL_OverlayEngineRecoilScale(codol_player_fields_t *wire, const playerState_t *ps);

/* IW4 and C1 clear both halves with the gclient memset in ClientSpawn, so a
 * respawn drops the scale and scripts reapply it. The retained flag rides that
 * memset already; these drop the magnitude for a live client slot and for
 * every slot. Both keep the names the integrated lifecycle sites already
 * call. */
void CODOL_ResetPlayerRecoilScale(unsigned client);
void CODOL_ResetAllPlayerRecoilScales(void);

#ifdef __cplusplus
}
#endif
#endif
