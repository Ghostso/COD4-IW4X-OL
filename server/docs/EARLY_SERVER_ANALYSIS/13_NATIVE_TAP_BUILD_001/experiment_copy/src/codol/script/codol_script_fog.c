#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "g_shared.h"
#include "cvar.h"
#include "codol_script_fog.h"
#include <float.h>
#include <stdio.h>

extern cvar_t *g_fogColorReadOnly;
extern cvar_t *g_fogStartDistReadOnly;
extern cvar_t *g_fogHalfDistReadOnly;
static cvar_t *fog_color,*fog_start,*fog_half,*fog_opacity,*fog_sun;
static cvar_t *fog_sun_color,*fog_direction,*fog_begin,*fog_end,*fog_scale;

void CODOL_RegisterFogDvars(void)
{
    /* C1 registrations52c737..52c8f5: numeric names1411..1420.
     * Native read-only flags follow the retained fog diagnostic dvars;
     * C1 flag bits cannot be copied into the IW3 dvar implementation. */
    const unsigned short flags=0x10c0;
    fog_color=Cvar_RegisterColor("1411",1,0,0,1,flags,"Script fog color");
    fog_start=Cvar_RegisterFloat("1412",0,0,FLT_MAX,flags,"Script fog start distance");
    fog_half=Cvar_RegisterFloat("1413",0.1f,0,FLT_MAX,flags,"Script fog halfway distance");
    fog_opacity=Cvar_RegisterFloat("1414",1,0,1,flags,"Script fog maximum opacity");
    fog_sun=Cvar_RegisterBool("1415",qfalse,flags,"Script sun fog enabled");
    fog_sun_color=Cvar_RegisterColor("1416",1,0,0,1,flags,"Script sun fog color");
    fog_direction=Cvar_RegisterVec3("1417",0,0,0,-1,1,flags,"Script sun fog direction");
    fog_begin=Cvar_RegisterFloat("1418",0,0,180,flags,"Script sun fog begin angle");
    fog_end=Cvar_RegisterFloat("1419",180,0,180,flags,"Script sun fog end angle");
    fog_scale=Cvar_RegisterFloat("1420",1,0,100,flags,"Script sun fog scale");
}

/* IW4 5f41a0 and C1 546040 accept seven/fourteen arguments. The C1
 * usage string is misleading: arg10 is a vector, 11/12 are fade angles,
 * and13 is scale (546267..54629b), not a sun-opacity argument.
 * Retain the old six-argument call as an IW3 script compatibility extension.
 * Diagnostic dvars update before common-helper validation, like C1. */
void CODOL_Scr_SetExponentialFog(void)
{
    unsigned argc=Scr_GetNumParam();
    float start,half,density,r,g,b,opacity,seconds;
    float sun[3]={0,0,0},direction[3]={0,0,0},begin=0,end=0,scale=1;
    char value[512];
    int length;
    if(argc!=6 && argc!=7 && argc!=14) {
        Scr_Error("setexpfog requires 7 or 14 parameters (6 for legacy scripts)"); return;
    }
    start=Scr_GetFloat(0);
    if(start<0) { Scr_Error("setexpfog start distance must be nonnegative"); return; }
    half=Scr_GetFloat(1);
    if(half<=0) { Scr_Error("setexpfog halfway distance must be positive"); return; }
    /* C1 c85470 is the promoted float ln(2), not full double ln(2). */
    density=(float)(0.6931471824645996/(double)half);
    r=Scr_GetFloat(2); g=Scr_GetFloat(3); b=Scr_GetFloat(4);
    opacity=argc==6 ? 1.0f : Scr_GetFloat(5);
    if(opacity<0 || opacity>1) { Scr_Error("setexpfog opacity must be in [0,1]"); return; }
    seconds=Scr_GetFloat(argc==6 ? 5 : 6);
    /* Reference updates these diagnostic dvars before reading sun args and
     * before the common helper validates RGB/transition time. */
    Cvar_SetColor(g_fogColorReadOnly,r,g,b,1);
    Cvar_SetFloat(g_fogStartDistReadOnly,start);
    Cvar_SetFloat(g_fogHalfDistReadOnly,half);
    Cvar_SetColor(fog_color,r,g,b,1);
    Cvar_SetFloat(fog_opacity,opacity);
    Cvar_SetFloat(fog_start,start);
    Cvar_SetFloat(fog_half,half);
    if(argc==14) {
        sun[0]=Scr_GetFloat(7); sun[1]=Scr_GetFloat(8); sun[2]=Scr_GetFloat(9);
        Scr_GetVector(10,direction);
        begin=Scr_GetFloat(11); end=Scr_GetFloat(12); scale=Scr_GetFloat(13);
        Cvar_SetBool(fog_sun,qtrue);
        Cvar_SetColor(fog_sun_color,sun[0],sun[1],sun[2],1);
        Cvar_SetVec3(fog_direction,direction[0],direction[1],direction[2]);
        Cvar_SetFloat(fog_begin,begin);
        Cvar_SetFloat(fog_end,end);
        Cvar_SetFloat(fog_scale,scale);
    } else {
        /* C1 546377 disables the extension without overwriting its mirrors. */
        Cvar_SetBool(fog_sun,qfalse);
    }
    if(r<0 || r>1 || g<0 || g>1 || b<0 || b>1) {
        Scr_Error("setexpfog RGB must be in [0,1]"); return;
    }
    if(seconds<0) { Scr_Error("setexpfog transition time must be nonnegative"); return; }
    if(argc==14) {
        if(sun[0]<0 || sun[0]>1 || sun[1]<0 || sun[1]>1 || sun[2]<0 || sun[2]>1) {
            Scr_Error("setexpfog sun RGB must be in [0,1]"); return;
        }
        if(begin<0 || begin>180 || end<0 || end>180) {
            Scr_Error("setexpfog sun fade angles must be in [0,180]"); return;
        }
        /* The reference permits the disabled pair (0,0). */
        if(begin>=end && (begin!=0 || end!=0)) {
            Scr_Error("setexpfog sun begin fade must be less than end fade"); return;
        }
        if(scale<0) { Scr_Error("setexpfog sun scale must be nonnegative"); return; }
        length=snprintf(value,sizeof(value),
            "%g %g %g %g %g %g %.0f 1 %g %g %g %g %g %g %g %g %g",
            start,density,r,g,b,opacity,(double)seconds*1000.0,
            sun[0],sun[1],sun[2],direction[0],direction[1],direction[2],begin,end,scale);
    } else {
        length=snprintf(value,sizeof(value),"%g %g %g %g %g %g %.0f 0",
            start,density,r,g,b,opacity,(double)seconds*1000.0);
    }
    if(length<0 || (size_t)length>=sizeof(value)) {
        Scr_Error("setexpfog payload is too long"); return;
    }
    /* Keep the full payload in native map storage so later refreshes and
     * initial gamestates reproduce it. The publisher translates slot9->13.
     * Do not invoke IW3 G_setfog's incompatible seven-field culling parser. */
    SV_SetConfigstring(9,value);
    level.fFogOpaqueDist=FLT_MAX;
    level.fFogOpaqueDistSqrd=FLT_MAX;
}
#endif
