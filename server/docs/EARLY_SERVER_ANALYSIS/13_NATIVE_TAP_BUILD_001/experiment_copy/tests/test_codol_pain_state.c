/* Offline trace/regression for the C1 damage flinch-stumble animation state.
 *
 * The live bug this covers: PlayerCmd_finishPlayerDamage charges
 * ps->damageTimer once, the C1 pmove core never discharged it, and
 * CODOL_PM_FootstepsC1 therefore latched movements 36..42 (stumble_*) and
 * 32..35 (flinch_*) until the playerState was rebuilt at respawn.
 */
#include "codol_pain_state.h"
#include <assert.h>
#include <stdio.h>

/* Retained defaults from src/g_sv_main.c. */
#define TIME_PER_POINT 100
#define MAX_TIME       750
#define STUMBLE_TIME   500
#define FLINCH_TIME    500

/* PlayerCmd_finishPlayerDamage (src/asmsource/_g_client_script_cmd_mp.asm):
 * timer += damage*timePerPoint, clamped to maxTime, duration = timer. */
static void charge(int *timer, int *duration, int damage)
{
    *timer += damage * TIME_PER_POINT;
    if(*timer < 0) *timer = 0x7fffffff;
    if(*timer > MAX_TIME) *timer = MAX_TIME;
    *duration = *timer;
}

int main(void)
{
    int timer, duration, elapsed, steps, cleared_at, stumble_stopped_at;
    int flinch_stopped_at;

    /* The discharge itself. */
    assert(CODOL_PainTimerStep(750, 66) == 684);
    assert(CODOL_PainTimerStep(66, 66) == 0);
    assert(CODOL_PainTimerStep(10, 66) == 0);
    assert(CODOL_PainTimerStep(0, 66) == 0);
    assert(CODOL_PainTimerStep(750, 0) == 750);
    assert(CODOL_PainTimerStep(750, -5) == 750);

    /* C1 PM_GetMoveAnim / PM_GetNotMovingAnim window: active while the
     * remaining timer is strictly above duration-window, zero-clamped. */
    assert(CODOL_PainStumbling(750, 750, STUMBLE_TIME) == 1);
    assert(CODOL_PainStumbling(251, 750, STUMBLE_TIME) == 1);
    assert(CODOL_PainStumbling(250, 750, STUMBLE_TIME) == 0);
    assert(CODOL_PainStumbling(0, 750, STUMBLE_TIME) == 0);
    /* A charge smaller than the window: the whole timer is stumble time. */
    assert(CODOL_PainStumbling(300, 300, STUMBLE_TIME) == 1);
    assert(CODOL_PainStumbling(1, 300, STUMBLE_TIME) == 1);
    assert(CODOL_PainStumbling(0, 300, STUMBLE_TIME) == 0);
    assert(CODOL_PainFlinching(750, 750, FLINCH_TIME) == 1);
    assert(CODOL_PainFlinching(250, 750, FLINCH_TIME) == 0);
    assert(CODOL_PainFlinching(0, 0, FLINCH_TIME) == 0);

    /* Movement selection: column 1 of C1 table 0x00C40978 is the stumble
     * variant of each ordinary movement (docs/CODOL_PLAYERANIM_TABLES.json). */
    assert(CODOL_PainMoveAnim(0, 0, 0, 0) == 10); /* run              */
    assert(CODOL_PainMoveAnim(1, 0, 0, 0) == 36); /* stumble_forward  */
    assert(CODOL_PainMoveAnim(0, 1, 0, 0) ==  4); /* walk             */
    assert(CODOL_PainMoveAnim(1, 1, 0, 0) == 38); /* stumble_walk_fwd */
    assert(CODOL_PainMoveAnim(0, 0, 2, 0) == 12); /* crouch run       */
    assert(CODOL_PainMoveAnim(1, 0, 2, 0) == 40); /* stumble_crouch   */
    assert(CODOL_PainMoveAnim(0, 0, 4, 0) == 11); /* backward run     */
    assert(CODOL_PainMoveAnim(1, 0, 4, 0) == 37); /* stumble_backward */
    assert(CODOL_PainMoveAnim(0, 0, 0, 1) == 20); /* sprint           */
    assert(CODOL_PainMoveAnim(1, 0, 0, 1) == 42); /* stumble_sprint   */
    assert(CODOL_PainMoveAnim(1, 0, 3, 1) == 52); /* sprint override
                                                     only at class 0  */
    assert(CODOL_PainFlinchIdleAnim(0) == 32);
    assert(CODOL_PainFlinchIdleAnim(3) == 35);
    assert(CODOL_PainFlinchIdleAnim(9) == 32);

    /* Offline trace: 8 points of damage, then 66ms command substeps as
     * CODOL_PmoveC1Try chops them, through CODOL_PM_NormalMoveC1. */
    timer = 0; duration = 0;
    charge(&timer, &duration, 8);
    assert(timer == MAX_TIME && duration == MAX_TIME);
    printf("elapsed  damageTimer  duration  stumble  flinch  legsAnim\n");
    cleared_at = -1; stumble_stopped_at = -1; flinch_stopped_at = -1;
    elapsed = 0;
    for(steps = 0; steps <= 20; ++steps) {
        int stumbling = CODOL_PainStumbling(timer, duration, STUMBLE_TIME);
        int flinching = CODOL_PainFlinching(timer, duration, FLINCH_TIME);
        printf("%7d  %11d  %8d  %7d  %6d  %8d\n", elapsed, timer, duration,
               stumbling, flinching, CODOL_PainMoveAnim(stumbling, 0, 0, 0));
        if(!stumbling && stumble_stopped_at < 0) stumble_stopped_at = elapsed;
        if(!flinching && flinch_stopped_at < 0) flinch_stopped_at = elapsed;
        if(!timer && cleared_at < 0) cleared_at = elapsed;
        timer = CODOL_PainTimerStep(timer, 66);
        elapsed += 66;
    }
    /* duration-stumbleTime is 250, so the stumble column is dropped on the
     * first substep whose remaining timer is <= 250: 750-66*8 = 222. */
    assert(stumble_stopped_at == 66 * 8);
    assert(flinch_stopped_at == 66 * 8);
    /* 750ms of charge is gone after ceil(750/66)=12 substeps. */
    assert(cleared_at == 66 * 12);
    assert(timer == 0);
    assert(CODOL_PainMoveAnim(CODOL_PainStumbling(timer, duration, STUMBLE_TIME),
                              0, 0, 0) == 10);

    /* Repeated damage re-arms and re-clears; it does not latch. */
    charge(&timer, &duration, 3);
    assert(timer == 300 && duration == 300);
    assert(CODOL_PainStumbling(timer, duration, STUMBLE_TIME) == 1);
    for(steps = 0; steps < 5; ++steps) timer = CODOL_PainTimerStep(timer, 66);
    assert(timer == 0);
    assert(CODOL_PainStumbling(timer, duration, STUMBLE_TIME) == 0);
    assert(CODOL_PainFlinching(timer, duration, FLINCH_TIME) == 0);

    /* The overflow guard the retained receiver applies still fits the 10-bit
     * damageTimer / 16-bit damageDuration netfields (src/msg.c). */
    timer = 0; duration = 0;
    charge(&timer, &duration, 100000);
    assert(timer == MAX_TIME && duration == MAX_TIME);
    assert(timer < 1024 && duration < 65536);

    printf("test_codol_pain_state: ok\n");
    return 0;
}
