#include "codol_sprint_state.h"
#include "g_shared.h"
#include "cvar.h"
#include <stddef.h>
#include <string.h>
#ifdef CODOL_SERVER
#include "codol_playerstate_ext.h"
#include "codol_abilities.h"
#include "codol_perk_runtime.h"
#include "codol_weapon_input.h"
#include "codol_usercmd.h"
#include "qcommon.h"
#include "qcommon_io.h"
#endif

/* The retained producers read these through the sprint dvars; keep the same
 * globals the assembly used, so an unset override reproduces stock behaviour. */
extern cvar_t *player_sprintTime;
extern cvar_t *player_sprintRechargePause;

/* The retained assembly addresses sprintState as playerState + 0x5b8 with the
 * five original members (_bg_pmove.asm PM_IsSprinting/PM_GetSprintLeft,
 * _bg_misc.asm BG_GetMaxSprintTime). Fail the build rather than the game if
 * the C declaration ever stops matching. */
typedef char codol_sprint_state_offset_check[
    offsetof(playerState_t, sprintState) == 0x5b8 &&
    sizeof(sprintState_t) == 20 &&
    offsetof(playerState_t, torsoAnim) == 0x94 &&
    offsetof(playerState_t, torsoAnimDuration) == 0x9c ? 1 : -1];

typedef struct {
    int duration_ms, cooldown_ms;
    unsigned char has_duration, has_cooldown;
} codol_sprint_override_t;
static codol_sprint_override_t overrides[MAX_CLIENTS];

/* Only the owning client's live playerState carries an override. Server pmove
 * runs on level.clients[n].ps, so a followed or copied playerState (whose
 * clientNum names another player) keeps the engine defaults. */
static int owning_client(const playerState_t *ps)
{
    int client;
    if (!ps) return -1;
    client = ps->clientNum;
    if (client < 0 || client >= MAX_CLIENTS || client >= level.maxclients) return -1;
    if (!level.clients || &level.clients[client].ps != ps) return -1;
    return client;
}

int CODOL_SetSprintDurationMs(int client, int milliseconds)
{
    if (client < 0 || client >= MAX_CLIENTS || milliseconds < 0) return 0;
#ifdef CODOL_SERVER
    {
        codol_ps_ext_t *state;
        const codol_engine_table_t *table;
        codol_client_abilities_t next={0}; unsigned slot;
        if(!level.clients || client>=level.maxclients ||
           CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1 ||
           CODOL_ReadAbilityValueSlot(table,0,&slot)!=1) return 0;
        state=CODOL_PlayerStateExt(&level.clients[client].ps);
        if(!state) return 0;
        CODOL_GetScriptAbilities((unsigned)client,&next);
        next.values[slot]=(float)milliseconds/1000.0f;
        next.masks[0]|=UINT32_C(0x80000000);
        if(!CODOL_CommitScriptAbilities((unsigned)client,&next,(int)slot))return 0;
    }
#endif
    overrides[client].duration_ms = milliseconds;
    overrides[client].has_duration = 1;
    return 1;
}

int CODOL_SetSprintCooldownMs(int client, int milliseconds)
{
    if (client < 0 || client >= MAX_CLIENTS || milliseconds < 0) return 0;
    overrides[client].cooldown_ms = milliseconds;
    overrides[client].has_cooldown = 1;
    return 1;
}

int CODOL_SprintDurationOverrideMs(const playerState_t *ps, int *milliseconds)
{
    int client = owning_client(ps);
    if (client < 0 || !milliseconds || !overrides[client].has_duration) return 0;
    *milliseconds = overrides[client].duration_ms;
    return 1;
}

int CODOL_SprintCooldownOverrideMs(const playerState_t *ps, int *milliseconds)
{
    int client = owning_client(ps);
    if (client < 0 || !milliseconds || !overrides[client].has_cooldown) return 0;
    *milliseconds = overrides[client].cooldown_ms;
    return 1;
}

void CODOL_ResetSprintOverrides(unsigned client)
{
    if (client < MAX_CLIENTS) memset(&overrides[client], 0, sizeof(overrides[client]));
}

void CODOL_ResetAllSprintOverrides(void)
{
    memset(overrides, 0, sizeof(overrides));
}

/* BG_GetMaxSprintTime computed player_sprintTime->value * 1000 here before
 * multiplying by the weapon's sprintDurationScale and the longer-sprint perk.
 * T5 428710 instead converts its per-player ps+0x494 milliseconds at that same
 * point, so an override replaces only the base term. */
float CODOL_SprintBaseDurationMs(const playerState_t *ps)
{
    int milliseconds;
    /* T5 428780..42879f keeps the global zero-duration gate even when
     * the base duration came from a player's override. */
    if(player_sprintTime && player_sprintTime->value==0.0f)return 0.0f;
    if (CODOL_SprintDurationOverrideMs(ps, &milliseconds)) return (float)milliseconds;
    return player_sprintTime ? player_sprintTime->value * 1000.0f : 0.0f;
}

#ifdef CODOL_SERVER
/* C1 40f7b1/40f822 use different masks for starting/continuing sprint. */
int CODOL_SprintButtonsBlocked(const playerState_t *ps,unsigned native_buttons,int continuing)
{
    codol_weapon_input_t input;
    int client=owning_client(ps);
    /* Bind to the accepted command, not a timestamp or the latest received
     * packet. Restrict lookup to owning live storage to avoid borrowing a
     * followed player's current input for a copied playerState. */
    if(client>=0 && CODOL_ExecutedWeaponInput((unsigned)client,&input) &&
       (input.kind==CODOL_INPUT_NETWORK || input.raw_valid)) {
        codol_usercmd_t raw={0},game;
        raw.buttons=input.raw_buttons;
        /* The accepted record preserves wire data. Apply the same input-mode
         * filter as native command translation before examining gameplay bits. */
        CODOL_FilterUsercmd(&raw,&game);
        return !!(game.buttons & (continuing ? 0x1cf35u : 0x1cc35u));
    }
    return !!(native_buttons & (continuing ? 0xc735u : 0xc435u));
}

/* C1 40e990: ability ID0 replaces the four-second default. Negative values
 * produce a zero maximum before weapon scaling; PM_GetSprintLeft treats that
 * zero maximum as its unlimited-meter case, rather than a disabled gate. */
float CODOL_SprintAbilityDurationSeconds(const playerState_t *ps)
{
    const codol_ps_ext_t *state=CODOL_PlayerStateExtConst(ps);
    const codol_engine_table_t *table; float seconds;
    if(!state) { Com_Error(ERR_DROP,"CoDOL sprint playerState unavailable"); return 0; }
    if(!state->abilities_known || !(state->abilities.masks[0]&UINT32_C(0x80000000))) return 4.0f;
    if(CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1 ||
       CODOL_GetActiveAbilityValue(&state->abilities,table,0,&seconds)!=1) {
        Com_Error(ERR_DROP,"CoDOL sprint ability mapping unavailable"); return 0;
    }
    return seconds;
}

int CODOL_GetSprintLeft(const playerState_t *ps,int time,int maximum)
{
    const sprintState_t *sprint;
    const codol_ps_ext_t *state;
    uint32_t word; int remaining,pause=0;
    if(!ps) { Com_Error(ERR_DROP,"CoDOL sprint playerState unavailable"); return 0; }
    /* C1 40f5b7 treats a zero maximum as unlimited remaining time. */
    if(!maximum) return 0x3fff;
    sprint=&ps->sprintState;
    if(!sprint->lastSprintStart) remaining=maximum;
    else if(sprint->lastSprintStart>sprint->lastSprintEnd) {
        word=(uint32_t)sprint->sprintStartMaxLength-(uint32_t)time+
             (uint32_t)sprint->lastSprintStart;
        memcpy(&remaining,&word,sizeof(remaining));
    } else {
        /* Retain 32-bit engine arithmetic across timer wrap. C1's ordinary
         * recharge delay is zero; the explicit T5 VM override remains an
         * extension and does not reinterpret ability33 as a delay. */
        if(sprint->sprintDelay) CODOL_SprintCooldownOverrideMs(ps,&pause);
        word=(uint32_t)sprint->sprintStartMaxLength-2u*(uint32_t)sprint->lastSprintEnd+
             (uint32_t)sprint->lastSprintStart+(uint32_t)time-(uint32_t)pause;
        memcpy(&remaining,&word,sizeof(remaining));
        state=CODOL_PlayerStateExtConst(ps);
        if(!state) { Com_Error(ERR_DROP,"CoDOL sprint ability storage unavailable"); return 0; }
        if(state->abilities_known && (state->abilities.masks[1]&UINT32_C(0x40000000))) {
            const codol_engine_table_t *table; float threshold;
            if(CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1 ||
               CODOL_GetActiveAbilityValue(&state->abilities,table,33,&threshold)!=1) {
                Com_Error(ERR_DROP,"CoDOL sprint refill mapping unavailable"); return 0;
            }
            /* C1 first stores the integer meter as a float, then compares
             * against the seconds value multiplied by a double 1000. */
            if((double)(float)remaining>(double)threshold*1000.0) remaining=maximum;
        }
    }
    if(remaining<0) remaining=0;
    return remaining>maximum ? maximum : remaining;
}
#endif

/* PM_UpdateSprint gates a new sprint on this pause after the last sprint ended,
 * and PM_GetSprintLeft subtracts it from the meter's recharge, both while
 * sprintDelay is set. T5 PM_GetSprintLeft reads the per-player ps+0x498 in the
 * same subtraction (42a3fa). */
int CODOL_SprintRechargePauseMs(const playerState_t *ps)
{
    int milliseconds;
    if (CODOL_SprintCooldownOverrideMs(ps, &milliseconds)) return milliseconds;
#ifdef CODOL_SERVER
    /* C1 PM_UpdateSprint40f9ff..40fa11 compares elapsed time against zero.
     * Explicit T5 overrides remain an extension; IW3's dvar is not C1 data. */
    return 0;
#else
    return player_sprintRechargePause ? (int)(player_sprintRechargePause->value * 1000.0f) : 0;
#endif
}

static int put(codol_player_fields_t *out, unsigned offset, uint32_t value)
{
    unsigned i;
    for (i = 0; i < CODOL_PLAYER_FIELDS; ++i)
        if (CODOL_PlayerField(i)->offset == offset) { out->field[i] = value; return 1; }
    return 0;
}

/* C1 PM_GetSprintLeft 40f5a0 reads lastSprintStart/lastSprintEnd/
 * sprintStartMaxLength at 0x240/0x244/0x248 and sprintDelay at 0x23c; 0x238 is
 * the remaining one-bit sprint member, sprintButtonUpRequired. The measured
 * playerStateFields carry 0x240/0x244 as server-time deltas, 0x248 in sixteen
 * bits and 0x238/0x23c as single bits, so reject anything unrepresentable
 * instead of writing a value the delta writer would fail on. */
int CODOL_OverlayEngineSprint(codol_player_fields_t *wire, const playerState_t *ps)
{
    codol_player_fields_t out;
    const sprintState_t *sprint;
    if (!wire || !ps) return 0;
    sprint = &ps->sprintState;
    if (sprint->sprintButtonUpRequired < 0 || sprint->sprintButtonUpRequired > 1 ||
        sprint->sprintDelay < 0 || sprint->sprintDelay > 1 ||
        sprint->sprintStartMaxLength < 0 || sprint->sprintStartMaxLength > 0xffff) return 0;
    out = *wire;
    if (!put(&out, 0x238, (uint32_t)sprint->sprintButtonUpRequired) ||
        !put(&out, 0x23c, (uint32_t)sprint->sprintDelay) ||
        !put(&out, 0x240, (uint32_t)sprint->lastSprintStart) ||
        !put(&out, 0x244, (uint32_t)sprint->lastSprintEnd) ||
        !put(&out, 0x248, (uint32_t)sprint->sprintStartMaxLength)) return 0;
    *wire = out;
    return 1;
}
