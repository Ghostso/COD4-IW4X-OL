/* IW4 5f9580..5f9640. Source implementation; no runtime verification yet.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_skill_rating.h"
#include <limits.h>
#include <math.h>
#include <string.h>

/* x86 SUB/ADD wrap in 32 bits. Avoid signed-overflow UB, including the
 * reference's absolute-value computation for INT32_MIN. */
static int32_t signed_bits(uint32_t value)
{
    int32_t result;
    memcpy(&result,&value,sizeof(result));
    return result;
}
static int32_t magnitude(int32_t value)
{
    return value<0 ? signed_bits(0u-(uint32_t)value) : value;
}
static int32_t truncate_rating(long double value)
{
    /* IW4 6b5240's SSE path stores to double before CVTTSD2SI. That
     * conversion truncates toward zero and returns integer-indefinite for
     * NaN/infinity/out-of-range. Check the truncated value before C's cast. */
    double integral=trunc((double)value);
    if(!isfinite(integral) || integral<INT32_MIN || integral>INT32_MAX)
        return INT32_MIN;
    return (int32_t)integral;
}
void CODOL_UpdateSkillRatings(int32_t *winner,int32_t *loser,float weight)
{
    int32_t win=*winner,lose=*loser;
    int32_t largest=magnitude(win),other=magnitude(lose),delta;
    float exponent,power,probability,step;
    if(largest<other) largest=other;
    /* Explicit float stores mirror 5f959d/5f95b6/5f95d6. Constants read
     * from721058=400.0,721550=10.0,6f4d1c=32,6e5064=24,72d5e0=16. */
    exponent=(float)((long double)signed_bits((uint32_t)win-(uint32_t)lose)/400.0L);
    power=(float)powl(10.0L,(long double)exponent);
    probability=(float)(1.0L/(1.0L+(long double)power));
    if((uint32_t)largest+99u<=198u) step=32.0f;
    else if((uint32_t)largest+399u<=798u) step=24.0f;
    else step=16.0f;
    delta=truncate_rating((long double)step*probability*weight);
    *winner=signed_bits((uint32_t)win+(uint32_t)delta);
    /* Read the destination at the subtract, as the reference does, so
     * aliased pointers reproduce its sequential store/subtract behavior. */
    *loser=signed_bits((uint32_t)*loser-(uint32_t)delta);
}
