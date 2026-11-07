/* C1 damage-driven flinch/stumble animation state.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Authority:
 *   charge      retained PlayerCmd_finishPlayerDamage
 *               (src/asmsource/_g_client_script_cmd_mp.asm, "player_dmgtimer_*"):
 *                 ps->damageTimer += damage * player_dmgtimer_timePerPoint
 *                 clamp to player_dmgtimer_maxTime
 *                 ps->damageDuration = ps->damageTimer
 *                 ps->flinchYawAnim  = quadrant of the incoming direction
 *   discharge   C1 PM_WalkMove 0x00410997, 0x004109bb..0x004109e1
 *               C1 PmoveSingle 0x00416781..0x004167a8
 *   flinch      C1 PM_GetNotMovingAnim 0x004135d5..0x004135fa
 *   stumble     C1 PM_GetMoveAnim      0x00413773..0x0041379a
 *
 * The charge side is one-shot; without the discharge the timer stays at its
 * charged value forever and every animation selector below stays latched on
 * its pain variant until the playerState is rebuilt on respawn.
 */
#ifdef CODOL_SERVER
#include "codol_pain_state.h"

int CODOL_PainTimerStep(int damage_timer, int msec)
{
    /* C1 0x004109c9..0x004109d7: ecx = damageTimer - (int)(frametime*1000),
     * stored, then replaced by zero unless it is strictly positive.  The
     * caller passes the same integer milliseconds the rest of the command
     * step uses, so a chopped 66ms substep discharges exactly 66. */
    int left;
    if(msec < 0) msec = 0;
    left = damage_timer - msec;
    return left > 0 ? left : 0;
}

static int pain_window(int damage_timer, int damage_duration, int window)
{
    /* C1 0x004135db..0x004135ee and 0x00413779..0x00413791 share this shape:
     * end = duration - window, negative clamped to zero, active while the
     * remaining timer is strictly greater than that end. */
    int end = damage_duration - window;
    if(end < 0) end = 0;
    return damage_timer > end;
}

int CODOL_PainFlinching(int damage_timer, int damage_duration, int flinch_time)
{
    return pain_window(damage_timer, damage_duration, flinch_time);
}

int CODOL_PainStumbling(int damage_timer, int damage_duration, int stumble_time)
{
    return pain_window(damage_timer, damage_duration, stumble_time);
}

int CODOL_PainFlinchIdleAnim(int flinch_yaw_anim)
{
    /* C1 0x004135f4: movement 0x20 + ps->flinchYawAnim.  The wire field is two
     * bits (src/msg.c PSF(flinchYawAnim)), so 32..35 is the whole range. */
    if((unsigned)flinch_yaw_anim > 3u) flinch_yaw_anim = 0;
    return 32 + flinch_yaw_anim;
}

int CODOL_PainMoveAnim(int stumbling, int ads, int stance_class, int sprinting)
{
    /* C1 PM_GetMoveAnim table 0x00C40978.  Column 1 of every pair is the
     * stumble_* movement (36..41, catalogued in
     * docs/CODOL_PLAYERANIM_TABLES.json). */
    static const int move_anims[32] = {
        10, 36,  4, 38,  8,  8,  8,  8, 12, 40,  6, 40, 52, 52, 52, 52,
        11, 37,  5, 39,  9,  9,  9,  9, 13, 41,  7, 41, 53, 53, 53, 53
    };
    int index;
    if(stumbling) stumbling = 1;
    if(ads) ads = 1;
    if((unsigned)stance_class > 7u) stance_class = 0;
    /* C1 0x00413794..0x0041379a: cl + 2*(arg + 2*stance_class). */
    index = stumbling + 2 * (ads + 2 * stance_class);
    /* C1 sprint override: stumble_sprint_forward (42) against sprint (20). */
    if(stance_class == 0 && sprinting) return stumbling ? 42 : 20;
    return move_anims[index];
}
#endif
