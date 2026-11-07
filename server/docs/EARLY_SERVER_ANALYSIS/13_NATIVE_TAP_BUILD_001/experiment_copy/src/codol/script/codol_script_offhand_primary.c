/* IW4 offhand class family: setters5d94d0/5d95f0, getters5d9580/5d96a0.
 * All use the same six-string table799bd0; native CoDOL selection is recorded
 * separately from the IW3 offhandSecondary field. */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "cscr_stringlist.h"
#include "codol_weapon_state.h"
#include "codol_script_offhand_primary.h"
#include <string.h>

static const char *const offhand_class_names[CODOL_OFFHAND_PRIMARY_CLASS_COUNT]={
    "none","frag","smoke","flash","throwingknife","other"
};
static playerState_t *offhand_player(scr_entref_t ref)
{
    if(ref.classnum) { Scr_ObjectError("not an entity"); return NULL; }
    if(ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player",ref.entnum)); return NULL;
    }
    return &g_entities[ref.entnum].client->ps;
}
static void set_offhand_class(scr_entref_t ref,int secondary)
{
    playerState_t *ps=offhand_player(ref);
    const char *name;
    unsigned selected;
    int recorded;
    if(!ps) return;
    if(Scr_GetNumParam()!=1) { Scr_Error("Incorrect number of parameters."); return; }
    name=SL_ConvertToString(Scr_GetConstString(0));
    for(selected=0;selected<CODOL_OFFHAND_PRIMARY_CLASS_COUNT;++selected)
        if(!strcmp(name,offhand_class_names[selected])) break;
    if(selected==CODOL_OFFHAND_PRIMARY_CLASS_COUNT) {
        Scr_Error(secondary?
            "Must specify 'smoke', 'flash', 'frag', 'throwingknife', or 'none' class to set secondary offhand to.":
            "Must specify 'smoke', 'flash', 'frag', 'throwingknife', or 'none' class to set primary offhand to.");
        return;
    }
    /* Both reference errors omit 'other', although their table accepts it.
     * Return remains undefined; a grant can occur after this call. */
    recorded=secondary?CODOL_WeaponStateSetOffhandSecondaryClass(ps,selected):
                       CODOL_WeaponStateSetOffhandPrimaryClass(ps,selected);
    if(!recorded) Scr_Error("could not record offhand class");
}
static void get_offhand_class(scr_entref_t ref,int secondary)
{
    playerState_t *ps=offhand_player(ref);
    unsigned selected;
    int recorded;
    if(!ps) return;
    /* IW4 getters have no argument-count check. Reset stores class0 (none),
     * and a setter retains its class even when no matching weapon is owned. */
    recorded=secondary?CODOL_WeaponStateOffhandSecondaryClass(ps,&selected):
                       CODOL_WeaponStateOffhandPrimaryClass(ps,&selected);
    if(!recorded || selected>=CODOL_OFFHAND_PRIMARY_CLASS_COUNT) {
        Scr_Error("offhand class state is unavailable"); return;
    }
    Scr_AddString(offhand_class_names[selected]);
}
void CODOL_Scr_SetOffhandPrimaryClass(scr_entref_t ref) { set_offhand_class(ref,0); }
void CODOL_Scr_SetOffhandSecondaryClass(scr_entref_t ref) { set_offhand_class(ref,1); }
void CODOL_Scr_GetOffhandPrimaryClass(scr_entref_t ref) { get_offhand_class(ref,0); }
void CODOL_Scr_GetOffhandSecondaryClass(scr_entref_t ref) { get_offhand_class(ref,1); }
#endif
