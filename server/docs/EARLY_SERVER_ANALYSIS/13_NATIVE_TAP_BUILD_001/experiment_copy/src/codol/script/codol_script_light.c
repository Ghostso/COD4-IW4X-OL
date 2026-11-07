/* Native primary-light script state. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_script_light.h"
#include "scr_vm_functions.h"
#include "entity.h"
#include "cscr_stringlist.h"
#include "qcommon_io.h"
#include "world.h"
#include <math.h>

/* C1 547c60 checks the resolved entity's type before reading arguments. */
static gentity_t *light_entity(scr_entref_t ref)
{
    gentity_t *ent=VM_GetGEntityForEntRef(ref);
    if(!ent) return NULL;
    if(ent->s.eType!=ET_PRIMARY_LIGHT) {
        Scr_Error(va("Function can only be called on a 'light' entity; actual classname is '%s'\n",
            ent->classname ? SL_ConvertToString(ent->classname) : ""));
        return NULL;
    }
    return ent;
}
void CODOL_Scr_SetLightIntensity(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    float value;
    if(!ent) return;
    value=Scr_GetFloat(0);
    /* C1 547d21..547d9b, also T5 65b5a0: tolerate tiny negatives;
     * the ordered clamp maps negatives and unordered values to zero.
     * There is no argument-count guard or return value. */
    if(value < -0.001f) {
        Scr_ParamError(0,"intensity must be >= 0");
        return;
    }
    ent->s.lerp.u.primaryLight.intensity=value>=0.0f ? value : 0.0f;
}
void CODOL_Scr_GetLightIntensity(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    if(ent) Scr_AddFloat(ent->s.lerp.u.primaryLight.intensity);
}
void CODOL_Scr_GetLightRadius(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    if(ent) Scr_AddFloat(ent->s.lerp.u.primaryLight.radius);
}
void CODOL_Scr_SetLightRadius(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    float value, maximum, tolerance;
    if(!ent) return;
    /* SP_light stores the BSP primary-light index in native entityState88.
     * C1 555114..55512e resolves its corresponding field98 before float0. */
    if(!comWorld.primaryLights || (unsigned)ent->s.index>=comWorld.primaryLightCount) {
        Scr_Error("light entity has no valid BSP primary-light index");
        return;
    }
    maximum=comWorld.primaryLights[ent->s.index].radius;
    value=Scr_GetFloat(0);
    if(value < -0.001f) {
        Scr_ParamError(0,"radius must be >= 0");
        return;
    }
    /* C1 555170 stores the double addition back to float before comparison. */
    tolerance=(float)((double)maximum+0.001);
    if(value>tolerance) {
        Scr_ParamError(0,va("radius must be less than the bsp radius (%g)",maximum));
        return;
    }
    /* C1 clamp4010e0 preserves unordered input, unlike intensity's clamp. */
    ent->s.lerp.u.primaryLight.radius=value<0.0f ? 0.0f :
        value>maximum ? maximum : value;
}
/* C1 52db40: multiply by double255, store float, add double2^-30,
 * then FISTP under the current rounding mode and saturate the signed result.
 * Invalid positive conversion yields INT_MIN on x87 and therefore byte0.
 * Avoid an undefined C float-to-int conversion for that case. */
static byte light_color_byte(float value)
{
    volatile float scaled=(float)((double)value*255.0);
    double rounded=nearbyint((double)scaled+0x1p-30);
    if(!isfinite(rounded) || rounded>=2147483648.0 || rounded<=0.0) return 0;
    if(rounded>=255.0) return 255;
    return (byte)rounded;
}
void CODOL_Scr_SetLightColor(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    vec3_t color;
    unsigned i;
    if(!ent) return;
    Scr_GetVector(0,color);
    /* C1 5550a0 preserves the packed exponent byte across color conversion. */
    for(i=0;i<3;++i) ent->s.lerp.u.primaryLight.colorAndExp[i]=light_color_byte(color[i]);
}
void CODOL_Scr_GetLightColor(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    vec3_t color;
    unsigned i;
    if(!ent) return;
    /* Double at C1c84458 is the float reciprocal promoted to double. */
    for(i=0;i<3;++i)
        color[i]=(float)((double)ent->s.lerp.u.primaryLight.colorAndExp[i]*
            (double)0.003921568859368563f);
    Scr_AddVector(color);
}
static float light_half_angle_cos(float degrees)
{
    /* C1 c842f8 is the promoted float degrees-to-radians constant.
     * Setter55532e..555347 rounds the argument before calling cosine. */
    volatile float angle=(float)((double)degrees*0.01745329238474369*0.5);
    return (float)cos((double)angle);
}
static float light_clamp(float value, float minimum, float maximum)
{
    /* The ordered selections in C1 clamp4010e0 preserve unordered input. */
    return value<minimum ? minimum : value>maximum ? maximum : value;
}
void CODOL_Scr_GetLightFovInner(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    volatile float half;
    if(!ent) return;
    /* C1 555210 -> CRT acos ae1bc0; no conversion to degrees. */
    half=(float)acos((double)ent->s.lerp.u.primaryLight.cosHalfFovInner);
    Scr_AddFloat(half+half);
}
void CODOL_Scr_GetLightFovOuter(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    volatile float half;
    if(!ent) return;
    half=(float)acos((double)ent->s.lerp.u.primaryLight.cosHalfFovOuter);
    Scr_AddFloat(half+half);
}
void CODOL_Scr_SetLightFov(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    const struct ComPrimaryLight *bsp;
    float outer, outerCos, innerCos, minimum;
    if(!ent) return;
    if(!comWorld.primaryLights || (unsigned)ent->s.index>=comWorld.primaryLightCount) {
        Scr_Error("light entity has no valid BSP primary-light index");
        return;
    }
    bsp=&comWorld.primaryLights[ent->s.index];
    outer=Scr_GetFloat(0);
    /* Measured C1 double bounds are promoted single-precision constants. */
    if(outer<0.9990000128746033 || outer>=120.0009994506836) {
        Scr_ParamError(0,"outer fov must be in the range of 1 to 120");
        return;
    }
    outerCos=light_half_angle_cos(outer);
    minimum=(float)((double)bsp->cosHalfFovOuter-0.001);
    if(outerCos<minimum) {
        Scr_ParamError(0,"outer fov cannot be larger than the fov when the map was compiled");
        return;
    }
    outerCos=light_clamp(outerCos,bsp->cosHalfFovOuter,1.0f);
    minimum=(float)((double)outerCos+0.001);
    if(Scr_GetNumParam()==2) {
        float inner=Scr_GetFloat(1);
        if(inner< -0.001f || (double)inner>=(double)outer+0.001) {
            Scr_ParamError(1,"inner fov must be in the range of 0 to outer fov");
            return;
        }
        innerCos=light_clamp(light_half_angle_cos(inner),minimum,1.0f);
    } else {
        /* C1 5554c7 compares new outer+tolerance against compiled inner;
         * the JP arm discards the former for greater/unordered comparison.
         * Preserve that minimum selection without an extra clamp to one. */
        innerCos=minimum<=bsp->cosHalfFovInner ? minimum : bsp->cosHalfFovInner;
    }
    ent->s.lerp.u.primaryLight.cosHalfFovOuter=outerCos;
    ent->s.lerp.u.primaryLight.cosHalfFovInner=innerCos;
}
/* C1 5554f0/555510: exponent is the fourth packed byte, not a float. */
void CODOL_Scr_GetLightExponent(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    if(ent) Scr_AddInt(ent->s.lerp.u.primaryLight.colorAndExp[3]);
}
void CODOL_Scr_SetLightExponent(scr_entref_t ref)
{
    gentity_t *ent=light_entity(ref);
    int value;
    if(!ent) return;
    value=Scr_GetInt(0);
    if(value<0 || value>100) {
        Scr_ParamError(0,"exponent must be in the range from 0 to 100");
        return;
    }
    ent->s.lerp.u.primaryLight.colorAndExp[3]=(byte)value;
}
#endif
