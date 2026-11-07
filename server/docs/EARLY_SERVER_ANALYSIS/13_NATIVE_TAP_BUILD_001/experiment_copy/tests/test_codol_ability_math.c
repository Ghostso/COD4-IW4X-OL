/* C1 ability timing arithmetic (src/codol/weapon/codol_ability_math.c). */
#include "codol_ability_math.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>

int main(void)
{
    int out = -1;

    /* modOffhandSpeedScale / modWeaponRecoveryTimeScale: ftol(time / value). */
    assert(CODOL_AbilityDivideMsec(500, 2.0f, &out) && out == 250);
    assert(CODOL_AbilityDivideMsec(333, 2.0f, &out) && out == 166);   /* truncates */
    assert(CODOL_AbilityDivideMsec(1250, 1.5f, &out) && out == 833);
    assert(CODOL_AbilityDivideMsec(0, 2.0f, &out) && out == 0);
    /* Single-precision control word: 1000 / 0.1f rounds to 10000.0f,
     * where a double quotient (9999.9998...) would truncate to 9999. */
    assert(CODOL_AbilityDivideMsec(1000, 0.1f, &out) && out == 10000);
    out = 7;
    assert(!CODOL_AbilityDivideMsec(500, 0.0f, &out) && out == 7);
    assert(!CODOL_AbilityDivideMsec(500, -1.0f, &out) && out == 7);
    assert(!CODOL_AbilityDivideMsec(500, NAN, &out) && out == 7);
    assert(!CODOL_AbilityDivideMsec(0x7fffffff, 1e-30f, &out) && out == 7);
    assert(!CODOL_AbilityDivideMsec(1, 1.0f, NULL));

    /* adsFireOnly fire delay: (1 - frac) * (1 / oo) [/ value10]. */
    assert(CODOL_AdsFireOnlyDelay(1.0f / 200.0f, 0.5f, 0, 1.0f, &out) && out == 100);
    assert(CODOL_AdsFireOnlyDelay(1.0f / 200.0f, 0.5f, 1, 1.5f, &out) && out == 66);
    assert(CODOL_AdsFireOnlyDelay(1.0f / 200.0f, 1.0f, 1, 1.5f, &out) && out == 0);
    assert(CODOL_AdsFireOnlyDelay(1.0f / 200.0f, 0.0f, 0, 1.0f, &out) && out == 200);
    out = 7;
    assert(!CODOL_AdsFireOnlyDelay(0.0f, 0.5f, 0, 1.0f, &out) && out == 7);

    /* Mantle anim length: (float)(frames / rate) * 1000 in single precision.
     * 9 / 10 = 0.89999998f, times 1000 rounds to 900.0f. */
    assert(CODOL_MantleAnimMsec(9, 10.0f) == 900);
    assert(CODOL_MantleAnimMsec(27, 30.0f) == 900);
    assert(CODOL_MantleAnimMsec(16, 30.0f) == 533);
    assert(CODOL_MantleAnimMsec(0, 30.0f) == 0);

    puts("codol ability math: ok");
    return 0;
}
