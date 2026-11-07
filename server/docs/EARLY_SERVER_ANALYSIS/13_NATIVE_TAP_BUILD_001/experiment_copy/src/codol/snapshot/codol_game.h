/* Bridges into the retained IW3 engine; no engine structure layout changes. */
#ifndef CODOL_GAME_H
#define CODOL_GAME_H
#include "codol_usercmd.h"
#include "codol_playerstate.h"
#include "msg.h"

int CODOL_ReadUsercmdMSG(msg_t *msg, uint32_t key,
                         const codol_usercmd_t *from, codol_usercmd_t *to);
/* Whole movement payload after its count byte: zero-based command chain and
 * four-word predicted-origin trailer. Outputs and engine cursors commit only
 * after all commands/trailer validate; failure marks overflow. */
int CODOL_ReadUsermoveMSG(msg_t *,uint32_t key,unsigned count,codol_usercmd_t *commands,
                          size_t capacity,float origin[3],uint32_t *origin_time);
int CODOL_ReadUsermoveMSGFrom(msg_t *,uint32_t key,unsigned count,
                              const codol_usercmd_t *base,codol_usercmd_t *commands,
                              size_t capacity,float origin[3],uint32_t *origin_time);
int CODOL_DefaultWireUsercmd(const struct playerState_s *,codol_usercmd_t *);
/* C1's usermove delta base: T5 MSG_SetDefaultUserCmd over the wire
 * playerState the client last received (NULL -> all zero, C1's cleared
 * cl.snap before its first snapshot). */
void CODOL_DefaultWireUsercmdFromFields(const codol_player_fields_t *held,codol_usercmd_t *out);
void CODOL_ToEngineUsercmd(const codol_usercmd_t *wire, usercmd_t *engine,
                           unsigned current_weapon, unsigned current_offhand);
void CODOL_RecordUsercmd(unsigned client, const codol_usercmd_t *wire);
const codol_usercmd_t *CODOL_LastUsercmd(unsigned client);
void CODOL_ResetClientInputCore(unsigned client);
/* C1's 200 ms post-spawn stale-weapon-0 gate; returns 1 when the command was
 * rewritten to keep the held weapon. */
int CODOL_ApplySpawnWeaponGate(const struct playerState_s *ps, usercmd_t *engine);
void CODOL_ResetClientInput(unsigned client);
/* The input state this header's own translation unit owns. */
void CODOL_ResetGameInputCore(void);
/* Core plus the vision, player-builtin, remote-view, turret and HUD-icon
 * resets that live in other areas. */
void CODOL_ResetGameInput(void);
void CODOL_RecordActionSlot(unsigned client,unsigned slot,int down);
unsigned CODOL_ActionSlotButtons(unsigned client);
void CODOL_ClearActionSlotEdges(unsigned client);
void CODOL_ResetActionSlots(unsigned client);
#endif
