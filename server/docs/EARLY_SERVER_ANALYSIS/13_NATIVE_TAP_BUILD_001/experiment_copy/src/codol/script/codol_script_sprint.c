#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_sprint_state.h"
#include "qcommon_io.h"
#include <math.h>

/* T5 PlayerCmd_SetSprintDuration (CoDMPServer 60cb00) and
 * PlayerCmd_SetSprintCooldown (60cc40) share one shape:
 *   <player> setsprintduration( <seconds> )
 *   <player> setsprintcooldown( <seconds> )
 * Both take exactly one float parameter in seconds, return nothing, require a
 * player entref, reject seconds below zero (60cbce/60cd0e) or at/above 16383
 * (60cbee/60cd2e), and store seconds * 1000 as milliseconds into the caller's
 * playerState. Their usage, range and entity messages are reproduced. */
static void set_sprint_value(scr_entref_t ref, int cooldown)
{
    const char *name = cooldown ? "setsprintcooldown" : "setsprintduration";
    gentity_t *entity;
    float seconds;
    int milliseconds;

    if (ref.classnum) { Scr_ObjectError("not an entity"); return; }
    if (ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum)); return;
    }
    entity = &g_entities[ref.entnum];
    if (!entity->client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum)); return;
    }
    if (Scr_GetNumParam() != 1) {
        Scr_Error(va("USAGE: <player> %s( <duration> )\n", name)); return;
    }
    seconds = Scr_GetFloat(0);
    /* T5's comparisons let a NaN reach its truncation; reject it instead. */
    if (!isfinite(seconds) || seconds < 0) {
        Scr_ParamError(0, va("%s: duration must be >= 0", name)); return;
    }
    if (seconds >= (float)CODOL_SPRINT_SECONDS_LIMIT) {
        Scr_ParamError(0, va("%s: duration must be < %d", name, CODOL_SPRINT_SECONDS_LIMIT));
        return;
    }
    milliseconds = (int)(seconds * 1000.0f);
    if (!(cooldown ? CODOL_SetSprintCooldownMs((int)ref.entnum, milliseconds) :
                    CODOL_SetSprintDurationMs((int)ref.entnum, milliseconds)))
        Scr_Error("sprint override state or ability mapping unavailable");
}

void CODOL_Scr_SetSprintDuration(scr_entref_t ref) { set_sprint_value(ref, 0); }
void CODOL_Scr_SetSprintCooldown(scr_entref_t ref) { set_sprint_value(ref, 1); }
#endif
