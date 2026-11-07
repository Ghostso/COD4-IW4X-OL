/* Which command a weapon machine is actually executing, and who produced it.
 *
 * Timestamps cannot answer this. ClientThink copies the accepted command out of
 * the server with SV_GetUsercmd (src/sv_game.c:623, a copy of
 * svs.clients[i].lastUsercmd) into client->sess.cmd, and two things then change
 * its serverTime before or during execution: G_RunClient overwrites it with
 * level.time for a synchronous client (_g_active_mp.asm G_RunClient_10 writes
 * client+0x2f90) and pmove advances it across substeps. ClientSpawn calls
 * ClientThink_real directly with a command it has just retimed
 * (src/g_client_mp.cpp:168..171). Comparing clientNum and a time to a recorded
 * wire command therefore proves nothing, and my previous pass was wrong to do
 * it: a synchronous CoDOL input would silently degrade to native-only.
 *
 * The association here is structural instead. Normal acceptance happens in
 * SV_ClientThink, where a command passes the
 * future-command guard and becomes cl->lastUsercmd -- the very object
 * SV_GetUsercmd later hands to the game. Binding at that point ties the raw
 * CoDOL command to the native command that will be executed, whatever happens
 * to its serverTime afterwards, and the binding survives substeps because
 * nothing re-derives it. The initial command becomes lastUsercmd directly in
 * SV_ClientEnterWorld, which binds its staged input before ClientBegin too.
 *
 * Each producer says what it is, so a consumer never has to guess from a zeroed
 * or stale word:
 *
 *   NETWORK    SV_UserMove staged a raw CoDOL command for this native command.
 *   BOT        Native AI may supply a full C1 command (raw_valid); legacy
 *              manual bots otherwise supply only the reduced command.
 *   SYNTHETIC  gameplay ran a pmove with a command no player produced, such as
 *              the spawn think; it carries no fire intent.
 */
#ifndef CODOL_WEAPON_INPUT_H
#define CODOL_WEAPON_INPUT_H
#include "q_shared.h"
#include "player.h"
#include "codol_usercmd.h"
#pragma pack(push, 8)

typedef enum {
    CODOL_INPUT_NONE = 0,
    CODOL_INPUT_NETWORK,
    CODOL_INPUT_BOT,
    CODOL_INPUT_SYNTHETIC
} codol_input_kind_t;

typedef struct {
    codol_input_kind_t kind;
    /* Exact C1 command accepted for this execution. Movement and weapon code
     * consume this record directly; the reduced native command exists only
     * for retained server bookkeeping. */
    codol_usercmd_t raw;
    unsigned char raw_valid;
    unsigned raw_buttons;    /* CoDOL wire buttons; meaningful only for NETWORK. */
    unsigned native_buttons; /* The accepted usercmd's buttons, every kind. */
    /* The raw word of the command executed *before* this one, so a consumer can
     * measure a rising edge on a CoDOL button the way C1 does with pm->oldcmd
     * (PM_Weapon_CheckForOffHand tests cmd.buttons & bit against
     * oldcmd.buttons & bit at 0x41cb4d/0x41cb6b/0x41cb8d). The retained
     * pmove_t carries oldcmd, but only for the *native* command: CoDOL bit
     * 0x10000 never reaches it, because CODOL_ToEngineUsercmd masks the native
     * buttons with 0xff3f and maps CoDOL 0x20000 onto native 0x10000 instead.
     * previous_raw_valid is 0 when the previously executed command had no CoDOL
     * word at all -- a bot or a synthetic pmove -- rather than a zeroed one. */
    unsigned previous_raw_buttons;
    unsigned char previous_raw_valid;
    /* Uninterpreted CoDOL remote-angle bytes from this accepted command.
     * Zero bytes are valid input; absence is represented separately. */
    unsigned char remote_angles[2];
    unsigned char remote_angles_valid;
} codol_weapon_input_t;
typedef struct {
    codol_weapon_input_t executed;
    codol_input_kind_t staged_kind;
    codol_usercmd_t staged_raw;
    unsigned char staged_raw_valid;
    unsigned staged_raw_buttons;
    unsigned char staged_remote_angles[2];
    unsigned char staged_remote_angles_valid;
} codol_weapon_input_scope_t;

#ifdef __cplusplus
extern "C" {
#endif

/* Producers. The raw word is copied, not retained by pointer. */
void CODOL_StageNetworkWeaponInput(unsigned client, unsigned raw_buttons);
void CODOL_StageNetworkCommandInput(unsigned client, const codol_usercmd_t *command);
void CODOL_StageBotWeaponInput(unsigned client);
/* Full C1 native AI command, with BOT provenance and no network masquerade. */
void CODOL_StageBotCommandInput(unsigned client,const codol_usercmd_t *command);
void CODOL_StageSyntheticWeaponInput(unsigned client);
/* Preserve accepted and pending input around a direct synthetic think. */
void CODOL_BeginSyntheticWeaponInput(unsigned client, codol_weapon_input_scope_t *saved);
void CODOL_EndSyntheticWeaponInput(unsigned client, const codol_weapon_input_scope_t *saved);
/* The acceptance point: promote whatever was staged to the executed input,
 * alongside the native command that just became cl->lastUsercmd. A client with
 * nothing staged is a bot or an internal producer, never a stale network
 * command, so the staging is consumed rather than left to age. */
void CODOL_BindExecutedWeaponInput(unsigned client, const usercmd_t *native);
/* The other half of that acceptance point: a command the guard turned away is
 * never executed, so whatever was staged for it is dropped rather than left to
 * be promoted by the next command that does get through. */
void CODOL_DiscardStagedWeaponInput(unsigned client);
/* A network command the acceptance loop skipped because its serverTime equals
 * the last accepted one. It never executes, but the client's own prediction
 * still reads it as the next command's oldcmd (CG_PredictPlayerState takes
 * command number - 1 whatever its time), so its raw buttons become the
 * previous word of whichever command is bound next. */
void CODOL_NoteSkippedNetworkCommandInput(unsigned client, const codol_usercmd_t *command);
/* What the machine running this pmove is executing. Returns 0 when the client
 * has no executed input at all. */
int CODOL_ExecutedWeaponInput(unsigned client, codol_weapon_input_t *out);
int CODOL_ExecutedUsercmd(unsigned client, codol_usercmd_t *out);
void CODOL_ResetWeaponInput(unsigned client);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
