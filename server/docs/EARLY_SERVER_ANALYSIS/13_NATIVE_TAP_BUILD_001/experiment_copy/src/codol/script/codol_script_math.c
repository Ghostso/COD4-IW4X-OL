#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "cscr_variable.h"
#include "cscr_stringlist.h"
#include "q_math.h"
#include <math.h>

void AxisToAngles(vec3_t axis[3],vec3_t angles);

/* Row-vector rigid transforms, matching IW4 41dfe0. Separate outputs keep
 * the two compositions independent of in-place matrix aliasing. */
static void transform_multiply(const float a[4][3],const float b[4][3],float out[4][3])
{
    unsigned row,column;
    for(row=0;row<4;++row)
        for(column=0;column<3;++column) {
            out[row][column]=a[row][0]*b[0][column]+
                a[row][1]*b[1][column]+a[row][2]*b[2][column];
            if(row==3) out[row][column]+=b[3][column];
        }
}

static void transform_result_vector(const char *name,const float value[3])
{
    unsigned key;
    Scr_AddVector(value);
    key=SL_GetString(name,0);
    Scr_AddArrayStringIndexed(key);
    SL_RemoveRefToString(key);
}

/* IW4 5f1f10 takes three (origin,angles) vector pairs. With transforms T0,
 * T1,T2 in argument order, it returns T2 * inverse(T1) * T0 as an associative
 * array with origin/angles keys. 455890 is the rigid inverse; 41dfe0 is the
 * multiply. This preserves rotation/translation order, including roll. */
void CODOL_Scr_TransformMove(void)
{
    float frame[3][4][3],inverse[4][3],relative[4][3],result[4][3];
    vec3_t angles;
    unsigned index,row,column;
    for(index=0;index<3;++index) {
        Scr_GetVector(index*2,frame[index][3]);
        Scr_GetVector(index*2+1,angles);
        AnglesToAxis(angles,frame[index]);
    }
    for(row=0;row<3;++row)
        for(column=0;column<3;++column)
            inverse[row][column]=frame[1][column][row];
    for(column=0;column<3;++column)
        inverse[3][column]=-(frame[1][3][0]*inverse[0][column]+
            frame[1][3][1]*inverse[1][column]+frame[1][3][2]*inverse[2][column]);
    transform_multiply(frame[2],inverse,relative);
    transform_multiply(relative,frame[0],result);
    AxisToAngles(result,angles);
    Scr_MakeArray();
    transform_result_vector("origin",result[3]);
    transform_result_vector("angles",angles);
}

/* IW4 5f14e0 reads a float, evaluates exp, and returns a float. */
void CODOL_Scr_Exp(void)
{
    Scr_AddFloat(expf(Scr_GetFloat(0)));
}

/* IW4 5f1510 and 5f1570 preserve float return values. */
void CODOL_Scr_Log(void) { Scr_AddFloat(logf(Scr_GetFloat(0))); }
void CODOL_Scr_Squared(void)
{
    float value = Scr_GetFloat(0);
    Scr_AddFloat(value * value);
}

/* IW4 5f15a0 reads upper, lower, value, then clamps upper before lower. */
void CODOL_Scr_Clamp(void)
{
    float upper = Scr_GetFloat(2);
    float lower = Scr_GetFloat(1);
    float value = Scr_GetFloat(0);
    if (value > upper) value = upper;
    if (value < lower) value = lower;
    Scr_AddFloat(value);
}

/* IW4 5f15e0 -> 438dc0 uses fractional turns, not integer angle packing. */
void CODOL_Scr_AngleClamp(void)
{
    float turns = (float)(Scr_GetFloat(0) * (1.0 / 360.0));
    float result = (float)((turns - floor((double)turns)) * 360.0);
    if (result >= 360.0f) result -= 360.0f;
    Scr_AddFloat(result);
}

/* IW4 5f1d00 -> 45ad10: zero horizontal direction has yaw zero. */
void CODOL_Scr_VectorToYaw(void)
{
    float vector[3], yaw = 0.0f;
    if (Scr_GetNumParam() != 1) {
        Scr_Error("VectorToYaw requires exactly one vector"); return;
    }
    Scr_GetVector(0, vector);
    if (vector[0] != 0.0f || vector[1] != 0.0f) {
        float radians = (float)atan2((double)vector[1], (double)vector[0]);
        yaw = (float)(radians * (180.0 / 3.14159265358979323846));
        if (yaw < 0.0f) yaw += 360.0f;
    }
    Scr_AddFloat(yaw);
}

/* T5 643460 checks the VM value type without converting the argument. */
void CODOL_Scr_IsVec(void) { Scr_AddBool(Scr_GetType(0) == VAR_VECTOR); }

/* T5 64c4c0/64c590 clamp the interpolation factor before interpolation. */
static float blend_factor(float factor)
{
    if (factor >= 1.0f) return 1.0f;
    if (factor <= 0.0f) return 0.0f;
    return factor;
}
void CODOL_Scr_LerpFloat(void)
{
    float start = Scr_GetFloat(0), end = Scr_GetFloat(1);
    float fraction = blend_factor(Scr_GetFloat(2));
    Scr_AddFloat(start + (end - start) * fraction);
}
void CODOL_Scr_LerpVector(void)
{
    float start[3], end[3], result[3], fraction;
    unsigned axis;
    Scr_GetVector(0, start);
    Scr_GetVector(1, end);
    fraction = blend_factor(Scr_GetFloat(2));
    for (axis = 0; axis < 3; ++axis)
        result[axis] = start[axis] + (end[axis] - start[axis]) * fraction;
    Scr_AddVector(result);
}
/* T5 64f3f0 returns the ordered cross product of arguments zero and one. */
void CODOL_Scr_VectorCross(void)
{
    float left[3], right[3], result[3];
    Scr_GetVector(0, left);
    Scr_GetVector(1, right);
    result[0] = left[1] * right[2] - left[2] * right[1];
    result[1] = left[2] * right[0] - left[0] * right[2];
    result[2] = left[0] * right[1] - left[1] * right[0];
    Scr_AddVector(result);
}
/* T5 64f780 folds a full turn into the unsigned range [0, 180]. */
void CODOL_Scr_AbsAngleClamp180(void)
{
    float turns = Scr_GetFloat(0) / 360.0f;
    float integral = (float)floor((double)turns);
    float angle = (turns - integral) * 360.0f;
    Scr_AddFloat(angle > 180.0f ? 360.0f - angle : angle);
}
/* T5 64f810 rotates argument zero by argument one's Euler angles. Its
 * AnglesToQuat goes through AnglesToAxis; use the retained axis convention
 * directly for the same rotation, without translation or normalization. */
void CODOL_Scr_RotatePoint(void)
{
    float point[3], angles[3], axis[3][3], result[3];
    unsigned i;
    Scr_GetVector(0, point);
    Scr_GetVector(1, angles);
    AnglesToAxis(angles, axis);
    for (i = 0; i < 3; ++i)
        result[i] = point[0] * axis[0][i] + point[1] * axis[1][i] + point[2] * axis[2][i];
    Scr_AddVector(result);
}

void CODOL_Scr_AngleClamp180(void)
{
    float angle = Scr_GetFloat(0);
    if (!isfinite(angle)) { Scr_Error("angleclamp180 requires a finite angle"); return; }
    angle = fmodf(angle, 360.0f);
    if (angle > 180.0f) angle -= 360.0f;
    else if (angle <= -180.0f) angle += 360.0f;
    Scr_AddFloat(angle);
}

/* Iterate native VM array children, including associative keys. Borrowed
 * vector values stay owned by the array; nothing is removed or reinserted. */
static void average_vectors(int normalize)
{
    unsigned int array = Scr_GetObject(0), child, count = 0;
    double sum[3] = {0, 0, 0};
    float result[3] = {0, 0, 0};
    unsigned axis;
    if (Scr_GetObjectType(array) != VAR_ARRAY) {
        Scr_Error("expected an array of vectors"); return;
    }
    for (child = FindFirstSibling(array); child; child = FindNextSibling(child)) {
        const float *vector;
        if (GetValueType(child) != VAR_VECTOR) {
            Scr_Error("expected an array containing only vectors"); return;
        }
        vector = GetVariableValueAddress(child)->vectorValue;
        for (axis = 0; axis < 3; ++axis) {
            if (!isfinite(vector[axis])) {
                Scr_Error("expected finite vector components"); return;
            }
            sum[axis] += vector[axis];
        }
        ++count;
    }
    if (count) {
        double divisor = normalize ? sqrt(sum[0]*sum[0]+sum[1]*sum[1]+sum[2]*sum[2]) : count;
        if (divisor > 0)
            for (axis = 0; axis < 3; ++axis) result[axis] = (float)(sum[axis]/divisor);
    }
    Scr_AddVector(result);
}
void CODOL_Scr_AveragePoint(void) { average_vectors(0); }
void CODOL_Scr_AverageNormal(void) { average_vectors(1); }
#endif
