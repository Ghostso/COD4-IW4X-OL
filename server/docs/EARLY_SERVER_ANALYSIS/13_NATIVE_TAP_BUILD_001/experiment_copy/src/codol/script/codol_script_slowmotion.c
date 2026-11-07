/* Native slow-motion configstring producer and common-clock factor.
 * Registered in scr_vm_main.c; advanced from Com_ModifyUsec, reset alongside
 * the configstring bank by SV_ClearServer. Fast restart retains both bank and
 * factor. Source implementation only; runtime and numerical parity untested. */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "g_shared.h"
#include "qcommon.h"
#include "codol_sv_state.h"
#include "codol_script_slowmotion.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static struct {
    int active;
    float start, end, scale;
    int32_t spanMs;
    unsigned remainderUsec;
    double fractionalUsec;
} slowmotion = {0, 1.0f, 1.0f, 1.0f, 0, 0, 0.0};

/* C1 ae0410 returns the x86 integer-indefinite value for invalid/out-of-range
 * conversion. In particular equal endpoints make both schedule offsets
 * indefinite, hence a zero span and an endpoint snap on the next update. */
static int32_t slowmotion_truncate(double value)
{
    if(!isfinite(value) || value >= 2147483648.0 || value <= -2147483649.0)
        return INT32_MIN;
    return (int32_t)value;
}

static void slowmotion_schedule(float start, float end, int durationMs)
{
    double duration = (float)durationMs;
    double difference = (double)end - start;
    double current = com_timescale->value;
    int32_t first, last;
    uint32_t span;

    /* C1 54a60d..54a646 measures both offsets from the same common clock.
     * Only their wrapping difference is consumed by599440. Retain the
     * running ramp factor: scheduling does not snap it to start. */
    if(difference == 0.0) {
        first = last = INT32_MIN;
    } else {
        first = slowmotion_truncate(duration * ((double)start - current) / difference);
        last = slowmotion_truncate(duration * ((double)end - current) / difference);
    }
    span = (uint32_t)last - (uint32_t)first;
    memcpy(&slowmotion.spanMs, &span, sizeof(span));
    slowmotion.start = start;
    slowmotion.end = end;
    slowmotion.active = 1;
}

float CODOL_SlowMotionAdvance(unsigned rawUsec)
{
    uint64_t elapsed = (uint64_t)rawUsec + slowmotion.remainderUsec;
    unsigned milliseconds = (unsigned)(elapsed / 1000u);
    float step, next;
    slowmotion.remainderUsec = (unsigned)(elapsed % 1000u);
    if(!slowmotion.active) return slowmotion.scale;
    if(!slowmotion.spanMs) {
        slowmotion.scale = slowmotion.end;
        slowmotion.active = 0;
        return slowmotion.scale;
    }
    /* C1 599483 stores the increment as float before adding current scale. */
    step = (float)(((double)slowmotion.end - slowmotion.start) *
                   milliseconds / slowmotion.spanMs);
    next = step + slowmotion.scale;
    if((slowmotion.start > slowmotion.end && next <= slowmotion.end) ||
       (slowmotion.start < slowmotion.end && next >= slowmotion.end) ||
       slowmotion.start == slowmotion.end) {
        next = slowmotion.end;
        slowmotion.active = 0;
    }
    slowmotion.scale = next;
    return next;
}

void CODOL_SlowMotionReset(void)
{
    memset(&slowmotion, 0, sizeof(slowmotion));
    slowmotion.start = slowmotion.end = slowmotion.scale = 1.0f;
}

unsigned CODOL_SlowMotionScaleTime(unsigned rawUsec, float operatorScale,
                                 unsigned fixedUsec)
{
    float ramp = CODOL_SlowMotionAdvance(rawUsec);
    double factor = (double)ramp * operatorScale;
    double scaled;
    unsigned result;

    /* C1 599590 advances the ramp even under fixedtime.5995dd..599613
     * retains the fractional scaled time and clears it on fixedtime or1x.
     * Retain native microsecond resolution rather than rounding the server
     * frame clock down to C1's millisecond representation. */
    if(fixedUsec || factor == 1.0) {
        slowmotion.fractionalUsec = 0.0;
        return fixedUsec ? fixedUsec : (rawUsec ? rawUsec : 1u);
    }
    scaled = rawUsec * factor + slowmotion.fractionalUsec;
    if(!isfinite(scaled) || scaled >= UINT_MAX) {
        slowmotion.fractionalUsec = 0.0;
        return scaled > 0.0 ? UINT_MAX : 1u;
    }
    if(scaled <= 0.0) {
        slowmotion.fractionalUsec = 0.0;
        return 1u;
    }
    result = (unsigned)scaled;
    slowmotion.fractionalUsec = scaled - result;
    return result ? result : 1u;
}

/* C1 54a510..54a5d9 and IW4 5f5f50 agree on >=1 arguments, optional end
 * default1 and duration default1000ms. C1 uses configstring6132; its parser
 * 466eb0 reads timestamp,duration,start,end with the same four-field format.
 * The local ramp at54a5de..54a64c is scheduled separately below. */
void CODOL_Scr_SetSlowMotion(void)
{
    unsigned count = Scr_GetNumParam();
    float startScale, endScale = 1.0f;
    int durationMs = 1000, i, length, changed;
    char value[128];
    codol_configstrings_t *bank;
    const char *old;

    if(count < 1) {
        Scr_Error("SetSlowMotion requires at least 1 parameter.");
        return;
    }
    startScale = Scr_GetFloat(0);
    if(count >= 2) endScale = Scr_GetFloat(1);
    if(count >= 3) {
        /* C1 54a59e multiplies the script float by a double constant before
         * ae0410 truncates. Do not round through a float millisecond value. */
        double milliseconds = (double)Scr_GetFloat(2) * 1000.0;
        /* Native guard against undefined C float-to-int conversion. Retail
         * x87 conversion behavior outside this domain is not reproduced. */
        if(!isfinite(milliseconds) || (double)milliseconds < INT_MIN ||
           (double)milliseconds > INT_MAX) {
            Scr_ParamError(2, "slow-motion duration is outside the integer millisecond range");
            return;
        }
        durationMs = (int)milliseconds;
    }
    if(!isfinite(startScale) || !isfinite(endScale)) {
        Scr_Error("slow-motion scales must be finite");
        return;
    }
    length = snprintf(value, sizeof(value), "%i %i %g %g",
                      level.time, durationMs, startScale, endScale);
    if(length < 0 || (size_t)length >= sizeof(value)) {
        Scr_Error("Could not format slow-motion configstring");
        return;
    }
    bank = CODOL_ServerConfigstrings();
    old = CODOL_GetConfigstring(bank, CODOL_CS_SLOWMOTION);
    changed = !old || strcmp(old, value);
    if(changed &&
       !CODOL_SetConfigstring(bank, CODOL_CS_SLOWMOTION, value)) {
        Scr_Error("Could not set slow-motion configstring");
        return;
    }
    /* Local scheduling still occurs when the bank already has this value or
     * no clients are connected, matching the post-publication C1 path. */
    slowmotion_schedule(startScale, endScale, durationMs);
    if(!changed || !svs.clients || !sv_maxclients) return;
    for(i = 0; i < sv_maxclients->integer; ++i)
        if(svs.clients[i].state >= CS_PRIMED && svs.clients[i].gamestateSent)
            SV_SendServerCommandNoLoss(&svs.clients[i], "d %u %s",
                                       CODOL_CS_SLOWMOTION, value);
}
#endif
