#ifndef _SV_SNAPSHOT_H_
#define _SV_SNAPSHOT_H_
#include "player.h"
#include "codol_playerstate_ext.h"


/* ext is the caller's half of the playerState bundle: the archived (or live)
 * CoDOL extension that belongs to the playerState this call delivers. Pass
 * NULL when the caller does not carry the state onward. */
int SV_GetArchivedClientInfo(int clientNum, int *pArchiveTime, playerState_t *ps, clientState_t *cs, float *origin, int *health, int *otherFlags, codol_ps_ext_t *ext);

#endif