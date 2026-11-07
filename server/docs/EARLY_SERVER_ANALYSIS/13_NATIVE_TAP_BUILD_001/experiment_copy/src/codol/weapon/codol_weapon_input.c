/* See codol_weapon_input.h for why this is bound structurally and not by time. */
#ifdef CODOL_SERVER
#include "codol_weapon_input.h"
#include <string.h>

typedef struct {
    codol_input_kind_t kind;
    codol_usercmd_t raw;
    unsigned char raw_valid;
    unsigned raw_buttons;
    unsigned char remote_angles[2];
    unsigned char remote_angles_valid;
} codol_staged_input_t;

static codol_staged_input_t staged[MAX_CLIENTS];
static codol_weapon_input_t executed[MAX_CLIENTS];
static unsigned skipped_raw_buttons[MAX_CLIENTS];
static unsigned char skipped_raw_valid[MAX_CLIENTS];

static void stage(unsigned client, codol_input_kind_t kind, unsigned raw)
{
    if(client >= MAX_CLIENTS) return;
    staged[client].kind = kind;
    memset(&staged[client].raw, 0, sizeof(staged[client].raw));
    staged[client].raw_valid = 0;
    staged[client].raw_buttons = raw;
    memset(staged[client].remote_angles, 0, sizeof(staged[client].remote_angles));
    staged[client].remote_angles_valid = 0;
}

void CODOL_StageNetworkWeaponInput(unsigned client, unsigned raw_buttons)
{
    stage(client, CODOL_INPUT_NETWORK, raw_buttons);
}
void CODOL_StageNetworkCommandInput(unsigned client, const codol_usercmd_t *command)
{
    if(client >= MAX_CLIENTS) return;
    if(!command) { stage(client, CODOL_INPUT_NONE, 0); return; }
    stage(client, CODOL_INPUT_NETWORK, command->buttons);
    staged[client].raw = *command;
    staged[client].raw_valid = 1;
    memcpy(staged[client].remote_angles, command->remoteAngles, 2);
    staged[client].remote_angles_valid = 1;
}
void CODOL_StageBotCommandInput(unsigned client,const codol_usercmd_t *command)
{
    if(client>=MAX_CLIENTS)return;
    stage(client,CODOL_INPUT_BOT,command?command->buttons:0);
    if(command){staged[client].raw=*command;staged[client].raw_valid=1;}
}
void CODOL_StageBotWeaponInput(unsigned client)
{
    stage(client, CODOL_INPUT_BOT, 0);
}
void CODOL_StageSyntheticWeaponInput(unsigned client)
{
    /* A synthetic producer does not reach the acceptance point, so it publishes
     * its executed input directly and leaves nothing staged behind it. */
    if(client >= MAX_CLIENTS) return;
    stage(client, CODOL_INPUT_NONE, 0);
    memset(&executed[client], 0, sizeof(executed[client]));
    executed[client].kind = CODOL_INPUT_SYNTHETIC;
    executed[client].raw_buttons = 0;
    executed[client].native_buttons = 0;
    executed[client].previous_raw_buttons = 0;
    executed[client].previous_raw_valid = 0;
}

void CODOL_BindExecutedWeaponInput(unsigned client, const usercmd_t *native)
{
    codol_weapon_input_t previous;
    if(client >= MAX_CLIENTS) return;
    /* Nothing staged means the command came from a producer that does not send
     * a CoDOL command -- the bot path, or an internal caller. It is recorded as
     * such rather than inheriting the last network command's buttons. */
    /* The command this one follows keeps its raw word here, so an edge on a
     * CoDOL-only button can be measured. A previous command that carried no
     * CoDOL word is recorded as having none, not as a zero word. */
    previous = executed[client];
    executed[client].kind = staged[client].kind == CODOL_INPUT_NETWORK ?
        CODOL_INPUT_NETWORK : CODOL_INPUT_BOT;
    executed[client].raw = staged[client].raw;
    executed[client].raw_valid =
        staged[client].raw_valid;
    executed[client].raw_buttons = (staged[client].kind == CODOL_INPUT_NETWORK || staged[client].raw_valid) ?
        staged[client].raw_buttons : 0u;
    executed[client].native_buttons = native ? (unsigned)native->buttons : 0u;
    executed[client].previous_raw_buttons =
        (previous.kind == CODOL_INPUT_NETWORK || previous.raw_valid) ? previous.raw_buttons : 0u;
    executed[client].previous_raw_valid =
        (previous.kind == CODOL_INPUT_NETWORK || previous.raw_valid) ? 1u : 0u;
    /* An equal-millisecond duplicate received after that command is the
     * newer previous word (see CODOL_NoteSkippedNetworkCommandInput). */
    if(skipped_raw_valid[client]) {
        executed[client].previous_raw_buttons = skipped_raw_buttons[client];
        executed[client].previous_raw_valid = 1u;
        skipped_raw_valid[client] = 0;
    }
    executed[client].remote_angles_valid =
        staged[client].kind == CODOL_INPUT_NETWORK && staged[client].remote_angles_valid;
    memset(executed[client].remote_angles, 0, sizeof(executed[client].remote_angles));
    if(executed[client].remote_angles_valid)
        memcpy(executed[client].remote_angles, staged[client].remote_angles, 2);
    stage(client, CODOL_INPUT_NONE, 0);
}

void CODOL_BeginSyntheticWeaponInput(unsigned client, codol_weapon_input_scope_t *saved)
{
    if(client >= MAX_CLIENTS || !saved) return;
    saved->executed = executed[client];
    saved->staged_kind = staged[client].kind;
    saved->staged_raw = staged[client].raw;
    saved->staged_raw_valid = staged[client].raw_valid;
    saved->staged_raw_buttons = staged[client].raw_buttons;
    memcpy(saved->staged_remote_angles, staged[client].remote_angles, 2);
    saved->staged_remote_angles_valid = staged[client].remote_angles_valid;
    CODOL_StageSyntheticWeaponInput(client);
}
void CODOL_EndSyntheticWeaponInput(unsigned client, const codol_weapon_input_scope_t *saved)
{
    if(client >= MAX_CLIENTS || !saved) return;
    executed[client] = saved->executed;
    staged[client].kind = saved->staged_kind;
    staged[client].raw = saved->staged_raw;
    staged[client].raw_valid = saved->staged_raw_valid;
    staged[client].raw_buttons = saved->staged_raw_buttons;
    memcpy(staged[client].remote_angles, saved->staged_remote_angles, 2);
    staged[client].remote_angles_valid = saved->staged_remote_angles_valid;
}

void CODOL_NoteSkippedNetworkCommandInput(unsigned client, const codol_usercmd_t *command)
{
    if(client >= MAX_CLIENTS || !command) return;
    skipped_raw_buttons[client] = command->buttons;
    skipped_raw_valid[client] = 1;
}

void CODOL_DiscardStagedWeaponInput(unsigned client)
{
    if(client >= MAX_CLIENTS) return;
    stage(client, CODOL_INPUT_NONE, 0);
}

int CODOL_ExecutedWeaponInput(unsigned client, codol_weapon_input_t *out)
{
    if(client >= MAX_CLIENTS || !out) return 0;
    if(executed[client].kind == CODOL_INPUT_NONE) return 0;
    *out = executed[client];
    return 1;
}

int CODOL_ExecutedUsercmd(unsigned client, codol_usercmd_t *out)
{
    if(client >= MAX_CLIENTS || !out ||
       !executed[client].raw_valid)
        return 0;
    *out = executed[client].raw;
    return 1;
}

void CODOL_ResetWeaponInput(unsigned client)
{
    if(client >= MAX_CLIENTS) return;
    memset(staged + client, 0, sizeof(staged[client]));
    memset(executed + client, 0, sizeof(executed[client]));
    skipped_raw_valid[client] = 0;
}
#endif
