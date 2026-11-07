#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "cvar.h"
#include <stdio.h>
#include <stdint.h>
#include <math.h>

typedef struct {
    uint32_t hash;
    const cvar_t *var;
} codol_dvar_lookup_t;

/* T5 Com_HashString (0x6f9cb0). Dvar names use ASCII identifiers. Keep
 * unsigned wraparound so negative script integers retain their hash bits. */
static void find_dvar_hash(const cvar_t *var, void *context)
{
    codol_dvar_lookup_t *lookup=context;
    const unsigned char *name=(const unsigned char *)var->name;
    uint32_t hash=5381u;
    while(*name) {
        unsigned ch=*name++;
        if(ch>='A' && ch<='Z') ch+='a'-'A';
        hash=hash*33u+ch;
    }
    if(!lookup->var && hash==lookup->hash) lookup->var=var;
}

static void get_dvar_color_component(unsigned component)
{
    const cvar_t *var;
    float value;
    if(Scr_GetType(0)==VAR_INTEGER) {
        codol_dvar_lookup_t lookup={(uint32_t)Scr_GetInt(0),NULL};
        Cvar_ForEach(find_dvar_hash,&lookup);
        var=lookup.var;
    } else {
        const char *name=Scr_GetString(0);
        var=*name ? Cvar_FindVar(name) : NULL;
    }
    if(!var) { Scr_AddFloat(1.0f);return; }
    if(var->type==CVAR_COLOR) {
        value=(float)var->color.rgba[component]*0.003921568859368563f;
    } else if(var->type==CVAR_STRING && (var->flags&CVAR_USER_CREATED)) {
        float color[4]={0,0,0,0};
        float scaled;
        /* T5 0x7be150 accepts partial input, clamps, quantizes to bytes,
         * then 0x7be040 converts those bytes back to normalized floats. */
        sscanf(var->string,"%g %g %g %g",&color[0],&color[1],&color[2],&color[3]);
        value=color[component];
        if(value>1.0f) value=1.0f;
        if(value<0.0f) value=0.0f;
        if(!isfinite(value)) value=0.0f;
        scaled=value*255.0f;
        value=(float)nearbyint((double)scaled+9.313225746154785e-10)
              *0.003921568859368563f;
    } else {
        /* The reference asserts on a registered non-color dvar. Report a
         * script error instead of interpreting the wrong union member. */
        Scr_Error("getdvarcolor: dvar is not a color or user-created string");
        return;
    }
    Scr_AddFloat(value);
}

void CODOL_Scr_GetDvarColorRed(void) { get_dvar_color_component(0); }
void CODOL_Scr_GetDvarColorGreen(void) { get_dvar_color_component(1); }
void CODOL_Scr_GetDvarColorBlue(void) { get_dvar_color_component(2); }

void CODOL_Scr_GetDvarVector(void)
{
    int count=Scr_GetNumParam();
    const char *name,*value,*fallback="0.0f 0.0f 0.0f";
    float vector[3];
    if(count!=1 && count!=2) {
        Scr_Error("getdvarvector requires one or two parameters");return;
    }
    if(count==2)fallback=Scr_GetString(1);
    name=Scr_GetString(0);
    value=Cvar_FindVar(name) ? Cvar_GetVariantString(name) : fallback;
    /* IW4 0x5ec6e0 tries these scanf formats in this order. Three assigned
     * components suffice; trailing characters are not a parse failure. */
    if(sscanf(value,"(%f, %f, %f)",&vector[0],&vector[1],&vector[2])!=3 &&
       sscanf(value,"%f %f %f",&vector[0],&vector[1],&vector[2])!=3) {
        Scr_Error("getdvarvector: dvar/default is not a three-component vector");return;
    }
    Scr_AddVector(vector);
}

/* IW4 0x5ec460 / 0x5ec510 initialize absent OR empty displayed values.
 * Only read the initial value if initialization is needed. Source 2 in
 * 0x647400 preserves write protection/latching but bypasses cheat protection,
 * matching the native script setter. These are not localized/multiarg setdvar. */
static void set_dvar_if_uninitialized(const char *usage)
{
    const char *name;
    if(Scr_GetNumParam()!=2) {
        Scr_Error(usage);
        return;
    }
    name=Scr_GetString(0);
    if(!*Cvar_GetVariantString(name))
        Cvar_SetAllowCheatOnly(name,Scr_GetString(1));
}

void CODOL_Scr_SetDvarIfUninitialized(void)
{
    set_dvar_if_uninitialized(
        "GScr_SetDvarIfUninitialized( dvarName, initialValue ) requires two parameters");
}

void CODOL_Scr_SetDevDvarIfUninitialized(void)
{
    set_dvar_if_uninitialized(
        "GScr_SetDevDvarIfUninitialized( dvarName, initialValue ) requires two parameters");
}
#endif
