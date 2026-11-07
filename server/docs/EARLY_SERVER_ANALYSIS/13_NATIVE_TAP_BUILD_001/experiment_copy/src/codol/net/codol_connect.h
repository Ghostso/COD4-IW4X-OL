/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_CONNECT_H
#define CODOL_CONNECT_H
#include <stddef.h>
#include <stdint.h>

/* Complete plaintext OOB packet, including four 0xff bytes and trailing NUL.
 * These response values differ from C1's protocol/shortversion dvar defaults.
 * Return zero without changing output on invalid values or insufficient room. */
size_t CODOL_WriteConnectResponse(uint8_t *, size_t, const char *map,
                                  const char *gametype, unsigned max_clients);
size_t CODOL_WriteChallengeResponse(uint8_t *, size_t, int challenge);
/* Validate connect <16-hex xuid> "<userinfo>" and copy the unquoted info string.
 * Requires its single xuid field to match the envelope. This is structural
 * consistency, not identity authentication; the association owner supplies that. */
int CODOL_ReadConnectUserinfo(char *, size_t, const char *xuid, const char *info);
int CODOL_ReadConnectXuid(const char *xuid,uint64_t *uid);
/* Connection identity survives map/profile resets, never userinfo updates.
 * Set only from the validated initial connect; clear on slot reuse/drop. */
void CODOL_SetClientConnectIdentity(unsigned client,uint64_t uid);
uint64_t CODOL_ClientConnectIdentity(unsigned client);
#endif
