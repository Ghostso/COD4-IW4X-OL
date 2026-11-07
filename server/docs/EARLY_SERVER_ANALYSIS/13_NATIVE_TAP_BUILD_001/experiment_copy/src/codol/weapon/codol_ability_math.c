/* C1 ability arithmetic for weapon and movement timing.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Precision. The C1 sequences below are x87, but C1's main thread runs them
 * with the x87 precision-control field at 24 bits: the IW engine line creates
 * its Direct3D 9 device without D3DCREATE_FPU_PRESERVE (T5 R_CreateDevice,
 * D:\CoD\OpenBLOPS\Engine\Renderer\gfx_d3d\r_init.cpp:335-338, behavior =
 * HARDWARE_VERTEXPROCESSING [| MULTITHREADED]), and Direct3D 9 then drops the
 * creating thread to single precision. Under that control word every fdiv,
 * fmul, fadd and fsub rounds to a float, even with a qword operand, so the
 * matching C is plain float arithmetic (this build is -mfpmath=sse, no FMA).
 * The conversion _ftol2_sse 0xae0410 then truncates toward zero.
 * No C1 FPU_PRESERVE flag or fldcw was located in C1.exe itself; this is the
 * one inference in this file. */
#include "codol_ability_math.h"
#include <math.h>

static int truncate_to_int(float value, int *out)
{
    if(!isfinite(value) || value>=2147483648.0f || value<-2147483648.0f) return 0;
    *out=(int)value;
    return 1;
}

int CODOL_AbilityDivideMsec(int msec, float value, int *out)
{
    float quotient;
    if(!out || !isfinite(value) || !(value>0.0f)) return 0;
    quotient=(float)msec/value;
    return truncate_to_int(quotient,out);
}

int CODOL_AdsFireOnlyDelay(float oo_pos_anim_length, float pos_frac,
                           int has_ability, float ads_value, int *out)
{
    float scale, remaining, delay;
    if(!out) return 0;
    scale=1.0f/oo_pos_anim_length;
    if(has_ability) scale=scale/ads_value;
    remaining=1.0f-pos_frac;
    delay=remaining*scale;
    return truncate_to_int(delay,out);
}

int CODOL_MantleAnimMsec(unsigned numframes, float framerate)
{
    float length=(float)numframes/framerate;
    float msec=length*1000.0f;
    int result;
    if(!truncate_to_int(msec,&result)) return 0;
    return result;
}
