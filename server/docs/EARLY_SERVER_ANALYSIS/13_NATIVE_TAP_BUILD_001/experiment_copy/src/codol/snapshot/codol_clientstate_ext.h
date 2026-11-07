#ifndef CODOL_CLIENTSTATE_EXT_H
#define CODOL_CLIENTSTATE_EXT_H
#include "codol_playerstate_ext.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Capture beside the snapshot client-ring write, before advancing its cursor.
 * NULL means reset ability state. Never resolve a
 * client number to live gameplay state while converting a retained frame. */
int CODOL_CaptureClientAbilities(int sequence, const codol_ps_ext_t *state);
/* G_UpdateClientInfo-equivalent publication, before the end-frame spectator
 * branch can replace ps. The published record belongs to the session slot. */
void CODOL_PublishClientAbilities(unsigned client, const playerState_t *ps);
void CODOL_ClearPublishedClientAbilities(unsigned client);
/* Profile appearance replaces the six-part retained clientState model set.
 * IDs must already be published in the CoDOL model/tag banks. Captured and
 * archived records retain all sixteen attachments independently of live state. */
int CODOL_PublishClientAppearance(unsigned client,const codol_client_appearance_t *);
int CODOL_CapturePublishedClientAbilities(int sequence, unsigned client);
int CODOL_OverlayCapturedClientAbilities(int sequence, codol_client_state_t *out);
void CODOL_ClearCapturedClientAbilities(void);
void CODOL_ClearArchivedClientAbilities(void);
/* Server-internal archive record, immediately after each forced client delta,
 * before its optional playerState. Full and delta archives carry this record
 * even when GetFollowPlayerStateLocal declines to archive a playerState. */
void CODOL_WriteArchivedClientAbilities(msg_t *, int client, const clientState_t *cache);
void CODOL_ReadArchivedClientAbilities(msg_t *, const clientState_t *cache);
int CODOL_CaptureArchivedClientAbilities(int sequence, const clientState_t *cache);
#ifdef __cplusplus
}
#endif
#endif
