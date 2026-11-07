#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "g_hud.h"

static game_hudelem_t *hud_argument(scr_entref_t ref)
{
    if(ref.classnum!=1 || ref.entnum>=MAX_HUDELEMS || !g_hudelems[ref.entnum].elem.type) {
        Scr_ObjectError("waypoint method requires a HUD element");return NULL;
    }
    return &g_hudelems[ref.entnum];
}
/* IW4 5e1980: value, optional draw-icon flag, optional distance flag.
 * Absent options preserve their flags; no material-name argument is read. */
void CODOL_Scr_SetWaypoint(scr_entref_t ref)
{
    game_hudelem_t *hud=hud_argument(ref);
    int count,value,flags;
    if(!hud)return;
    count=Scr_GetNumParam();
    value=Scr_GetInt(0);
    flags=hud->elem.flags;
    if(count>2) {
        if(Scr_GetInt(2))flags|=0x10;else flags&=~0x10;
    }
    if(count>1) {
        if(Scr_GetInt(1))flags|=8;else flags&=~8;
    }
    hud->elem.type=HE_TYPE_WAYPOINT;
    hud->elem.value=(float)value;
    hud->elem.flags=flags;
}
static void waypoint_flag(scr_entref_t ref,int mask,int enabled)
{
    game_hudelem_t *hud=hud_argument(ref);
    if(!hud)return;
    if(hud->elem.type!=HE_TYPE_WAYPOINT) {
        Scr_Error("HUD element must be a waypoint");return;
    }
    if(enabled)hud->elem.flags|=mask;else hud->elem.flags&=~mask;
}
/* IW4 5e1a20/5e1a70 select opposite states of the same edge-style bit. */
void CODOL_Scr_SetWaypointEdgeStyleRotatingIcon(scr_entref_t ref)
{
    waypoint_flag(ref,0x20,1);
}
void CODOL_Scr_SetWaypointEdgeStyleSecondaryArrow(scr_entref_t ref)
{
    waypoint_flag(ref,0x20,0);
}
/* IW4 5e1ac0 sets the offscreen-only bit. C1 44aeda consumes bit six. */
void CODOL_Scr_SetWaypointIconOffscreenOnly(scr_entref_t ref)
{
    waypoint_flag(ref,0x40,1);
}
#endif
