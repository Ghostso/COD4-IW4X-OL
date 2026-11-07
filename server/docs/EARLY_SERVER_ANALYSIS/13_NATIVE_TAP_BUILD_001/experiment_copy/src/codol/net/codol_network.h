/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_NETWORK_H
#define CODOL_NETWORK_H
#include "q_shared.h"
#include "codol_admission.h"
void CODOL_NetworkInit(void);
void CODOL_NetworkReset(void);
int CODOL_NetworkAuthenticated(netadr_t *);
/* Receive: 1 consumed, 0 plaintext diagnostic mode. Send: -1 diagnostic mode,
 * 0 failed/pending, 1 submitted. Raw handshakes bypass NET_SendPacket. */
int CODOL_NetworkReceive(netadr_t *, const void *, int);
int CODOL_NetworkSend(netadr_t *, const void *, int);
/* The lobby admission behind this source's established bdDTLS association:
 * the roster entry whose key the association authenticates with. -> 1/0. */
int CODOL_NetworkAdmission(const netadr_t *, codol_admission_entry_t *);
#endif
