/* C1 damage-driven flinch/stumble animation state.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * playerState damageTimer/damageDuration/flinchYawAnim are the only inputs the
 * third-person pain animations have.  The GSC damage receiver charges the timer
 * and copies it into the duration; the movement simulation is what discharges
 * it again.  Everything here is arithmetic over those three ints so it can be
 * exercised without a pmove, a client or a loaded animation script.
 */
#ifndef CODOL_PAIN_STATE_H
#define CODOL_PAIN_STATE_H

#ifdef __cplusplus
extern "C" {
#endif

/* C1 PM_WalkMove 0x00410997 / 0x004109bb..0x004109e1 (also duplicated in
 * PmoveSingle 0x0041678f for the branch that never reaches PM_WalkMove):
 * damageTimer -= elapsed command milliseconds, clamped at zero. */
int CODOL_PainTimerStep(int damage_timer, int msec);

/* C1 PM_GetNotMovingAnim 0x004135d5..0x004135ee: flinch while the timer is
 * still inside the first player_dmgtimer_flinchTime ms of its duration. */
int CODOL_PainFlinching(int damage_timer, int damage_duration, int flinch_time);

/* C1 PM_GetMoveAnim 0x00413773..0x00413791: the same test against
 * player_dmgtimer_stumbleTime selects the stumble column of 0x00C40978. */
int CODOL_PainStumbling(int damage_timer, int damage_duration, int stumble_time);

/* C1 0x004135f4: movements 32..35 are flinch_forward/backward/left/right. */
int CODOL_PainFlinchIdleAnim(int flinch_yaw_anim);

/* C1 PM_GetMoveAnim table 0x00C40978 plus its sprint override: movements
 * 36..42 are the stumble_* variants of the ordinary walk/run movements.
 * stance_class is the C1 stance index plus the backward bias (0..7). */
int CODOL_PainMoveAnim(int stumbling, int ads, int stance_class, int sprinting);

#ifdef __cplusplus
}
#endif

#endif
