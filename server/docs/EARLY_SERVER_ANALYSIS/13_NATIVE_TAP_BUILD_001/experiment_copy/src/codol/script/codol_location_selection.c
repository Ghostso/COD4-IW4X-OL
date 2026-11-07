/* C1 5161f0: selector(shader, directional, optional radius).
 * This is C1's own byte, not T5's separate locationSelectionType. */
#ifdef CODOL_SERVER
#include "codol_location_selection.h"
#include "g_shared.h"
#include "entity.h"
#include "codol_weapon_input.h"
#include <math.h>
extern int GScr_GetLocSelIndex(const char *name);
static gentity_t *selection_player(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].r.inuse ||
       !g_entities[ref.entnum].client){Scr_ObjectError("location selection requires a player");return NULL;}
    return &g_entities[ref.entnum];
}
static void begin_selection(gentity_t *ent,const char *shader,int directional,
    int hasRadius,float radius,unsigned radiusArgument)
{
    int selector=GScr_GetLocSelIndex(shader);
    if(hasRadius){
        if(!isfinite(radius)||radius<=0){Scr_ParamError(radiusArgument,"Radius of location selector must be greater than zero");return;}
        radius/=level.compassMapWorldSize[1]>0?level.compassMapWorldSize[1]:1000.0f;
        if(radius>1)radius=1;
    }
    if(selector<1 || selector>3){Scr_Error("location selector must be precached");return;}
    /* 516360..5163b6: single precision product, add2^-30 then fistp.
     * Client431276..43128b reads five radius bits, leaving bit7 for direction. */
    ent->client->ps.locationSelectionInfo=(selector&3)|(((int)nearbyint((double)(float)(radius*31.0f)+9.313225746154785e-10)&31)<<2)|((directional&1)<<7);
}
void CODOL_BeginLocationSelection(scr_entref_t ref)
{
    gentity_t *ent=selection_player(ref);
    if(!ent)return;
    if(Scr_GetNumParam()<2 || Scr_GetNumParam()>3){Scr_Error("beginLocationSelection(shader, directional[, radius])");return;}
    begin_selection(ent,Scr_GetString(0),Scr_GetInt(1),Scr_GetNumParam()>2,
        Scr_GetNumParam()>2?Scr_GetFloat(2):.15f,2);
}
void CODOL_BeginLocationMortarSelection(scr_entref_t ref)
{
    gentity_t *ent=selection_player(ref);
    if(!ent)return;
    if(Scr_GetNumParam()<1 || Scr_GetNumParam()>2){Scr_Error("beginLocationMortarSelection(shader[, radius])");return;}
    /* T5 argument/receiver interface, native C1 selector representation.
     * Original mortar GSC counts three confirmations; C1 consumes its own
     * five-bit radius and nondirectional selector, not T5's typed PS offset. */
    begin_selection(ent,Scr_GetString(0),0,Scr_GetNumParam()>1,
        Scr_GetNumParam()>1?Scr_GetFloat(1):.15f,1);
}
void CODOL_EndLocationSelection(scr_entref_t ref)
{
    gentity_t *ent=selection_player(ref);
    if(ent)ent->client->ps.locationSelectionInfo=0;
}
int CODOL_LocationSelectionAction(gentity_t *ent)
{
    codol_weapon_input_t input;
    unsigned pressed;
    if(!CODOL_ExecutedWeaponInput(ent->s.number,&input) || !input.raw_valid)
        return 0;
    pressed=input.raw.buttons & ~(input.previous_raw_valid ? input.previous_raw_buttons : 0u);
    /* C1 client 490ae4/490af7 confirms; 490b10 cancels. Confirmation wins
     * when both are present, matching the retained script event ordering. */
    if(pressed & 0x20000u)return 1;
    if(pressed & 0x40000u)return 2;
    return 0;
}
void CODOL_ConfirmLocation(gentity_t *ent, const float *position)
{
    codol_weapon_input_t input;
    unsigned count=1;
    /* C1 50cb02..50cb3b pushes compass-relative yaw before the position.
     * Use the accepted command, not the latest network packet, which can
     * differ during synchronous/synthetic execution. */
    if(CODOL_ExecutedWeaponInput(ent->s.number,&input) && input.raw_valid) {
        float yaw=(float)(atan2(level.compassNorth[1],level.compassNorth[0])*(180.0/3.14159265358979323846));
        yaw+=input.raw.selectedLocationAngle*(360.0f/255.0f);
        yaw=fmodf(yaw,360.0f);
        if(yaw<0.0f)yaw+=360.0f;
        Scr_AddFloat(yaw);
        count=2;
    }
    Scr_AddVector(position);
    Scr_Notify(ent,scr_const.confirm_location,count);
}
#endif
