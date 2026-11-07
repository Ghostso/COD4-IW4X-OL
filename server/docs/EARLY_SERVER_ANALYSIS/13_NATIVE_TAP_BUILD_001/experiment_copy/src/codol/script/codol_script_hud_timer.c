#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "g_hud.h"
#include <math.h>
#include <limits.h>

/* IW4 5e1780/5e1890 -> 5e1440. A static timer stores a duration in
 * milliseconds, without adding level.time. C1 draws raw time for types 7/10. */
static void static_timer(scr_entref_t ref,he_type_t type)
{
    float seconds,milliseconds;
    double rounded;
    game_hudelem_t *hud;
    if(ref.classnum!=1 || ref.entnum>=MAX_HUDELEMS || !g_hudelems[ref.entnum].elem.type) {
        Scr_ObjectError("static timer requires a HUD element");return;
    }
    if(Scr_GetNumParam()!=1) {
        Scr_Error("static timer requires exactly one duration");return;
    }
    seconds=Scr_GetFloat(0);
    milliseconds=(float)((double)seconds*1000.0);
    /* IW4 uses x87 nearest rounding after adding the double at 70f030.
     * Check representability before converting, and commit only after reads. */
    rounded=nearbyint((double)milliseconds+0.4999999990686774);
    if(!isfinite(rounded) || rounded<=0 || rounded>INT_MAX) {
        Scr_ParamError(0,"static timer duration must be positive and fit signed milliseconds");return;
    }
    hud=&g_hudelems[ref.entnum];
    HudElem_ClearTypeSettings(hud);
    hud->elem.type=type;
    hud->elem.time=(int)rounded;
}
void CODOL_Scr_SetTimerStatic(scr_entref_t ref)
{
    static_timer(ref,HE_TYPE_TIMER_STATIC);
}
void CODOL_Scr_SetTenthsTimerStatic(scr_entref_t ref)
{
    static_timer(ref,HE_TYPE_TENTHS_TIMER_STATIC);
}
#endif
