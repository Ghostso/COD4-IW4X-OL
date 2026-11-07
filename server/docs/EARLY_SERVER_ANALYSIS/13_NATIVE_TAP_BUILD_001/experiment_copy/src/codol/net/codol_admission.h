/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_ADMISSION_H
#define CODOL_ADMISSION_H
#include <stddef.h>
#include <stdint.h>

/* Lobby -> game server admission roster.
 *
 * Each C1 process generates its own 16-byte bdSecurityKey and hands it to the
 * lobby in its createSession descriptor; the bdDTLS association with the game
 * server is keyed from it. The lobby writes one roster line per ADMITTED
 * connection (codol_admissionPath, normally data/game_admissions.txt):
 *
 *     <ipv4> <key: 32 hex> <uid: 16 hex, 0 = not latched yet> <expires: unix s> <gamertag>
 *
 * The key is the credential: only that client and the lobby know it, and a
 * record authenticates under exactly one roster key. The source IP only orders
 * the candidates (a player behind a NAT pool may reach the lobby and the game
 * server from different addresses). The file is re-read when it changes. */

/* Explicit packing: this struct crosses into files that include server.h, whose
 * bare pack(1) otherwise gives them a smaller layout than codol_admission.c and
 * lets CODOL_AdmissionIdentify write past the caller's copy (MinGW aligns
 * 64-bit members to 8, so the uid moved and the connect xuid beside it was
 * overwritten). */
#pragma pack(push, 8)
typedef struct {
    uint8_t ip[4];
    uint8_t key[16];
    uint64_t uid;
    long long expires;
    char gamertag[33];
} codol_admission_entry_t;
#pragma pack(pop)

void CODOL_AdmissionInit(void);
/* codol_admissionRequired: refuse clients the lobby has not admitted. */
int CODOL_AdmissionRequired(void);
/* Unexpired roster keys, entries for this source IP first. -> count written. */
size_t CODOL_AdmissionCandidates(const uint8_t ip[4], uint8_t keys[][16], size_t max);
/* The roster entry whose key, combined with this association's ECDH shared X,
 * derives the association's current DATA key. -> 1 and *out, else 0. */
int CODOL_AdmissionIdentify(const uint8_t ip[4], const uint8_t shared_x[28],
                            const uint8_t data_key[24], codol_admission_entry_t *out);
/* A party member dials the game server on its HOST's association: the room's
 * READY press fans the host's StartGame record (and so the host's key) out to
 * every member, and C1 keys bdDTLS with it, so the association identifies the
 * host's seat. The key still proves a live lobby admission for that session;
 * the member is the live roster entry the lobby admitted for `uid` from this
 * same source address. -> 1 and *out, else 0. */
int CODOL_AdmissionMember(const uint8_t ip[4], uint64_t uid, codol_admission_entry_t *out);

/* Pure helpers, exposed for tests. */
int CODOL_AdmissionParseLine(const char *line, codol_admission_entry_t *out);
#endif
