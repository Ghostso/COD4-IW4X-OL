/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PROFILE_PUSH_H
#define CODOL_PROFILE_PUSH_H
#include <stddef.h>
#include <stdint.h>
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

/* Live delivery of a player's secure profile (rank, XP, career counters) to
 * the C1 client, through C1's own server command 'K'.
 *
 * C1 keeps the secure profile it downloaded at login ("mpdata_s") in one
 * buffer, 0x0205C598 ([crc32][record]); GetRank 0x0058EFE0 and the career
 * pages read the record at 0x0205C59C synchronously. The client re-downloads
 * it at login or after a non-bypassed disconnect (CL_HandleDisconnect
 * 0x004960E0). The normal EXE_MATCHENDED leave bypasses that refetch, so the
 * server must deliver its final edits first. The dispatcher 0x00469320 routes
 * 'K' (0x00469AD5) and
 * 'J' (0x00469ABA) to 0x00468BD0, which writes bytes straight into the live
 * record: 'K' into the secure record 0x0205C59C, 'J' into the public one.
 *
 * Argument format, read from 0x00468D20..0x00468EA2: pairs of
 *   <offset> <data>
 * <offset> is a decimal record-relative byte offset (atoi 0x00ADA2A7, refused
 * at or beyond 0x7ffc). <data> is consumed left to right, one record byte per
 * token: 'Z' writes 0x00, 'O' writes 0x01, otherwise two hex digits
 * [0-9A-F] (upper case only) write that byte. The argument count must be odd
 * (the letter plus whole pairs, 0x00468BFE). Before writing, the handler
 * snapshots the record into 0x016DC420 and compares GetRank before and after,
 * which is how C1 notices a promotion. */

/* Encodes the bytes that differ between `sent` and `current` (both `size`
 * bytes, record-relative) as "K" commands. Each command is written to `out`
 * (capacity `out_size`, at most `max_command` characters including the
 * terminator) and passed to `emit`. Unchanged gaps shorter than `merge_gap`
 * bytes between two changed runs are sent too, keeping the command count
 * down. `sent` is updated to `current` for every byte emitted. Returns the
 * number of commands emitted, or -1 on a bad argument. Pure: no engine
 * dependencies, unit-testable. */
int CODOL_EncodeProfilePush(uint8_t *sent, const uint8_t *current, size_t size,
                            size_t merge_gap, char *out, size_t max_command,
                            void (*emit)(void *ctx, const char *command), void *ctx);

/* Per server frame: pushes each connected human's secure-profile changes. */
void CODOL_PushSecureProfiles(void);
/* Send any final in-match edits before the reliable match-end leave command. */
void CODOL_FlushSecureProfiles(void);
/* Drops the per-client copy (connect, disconnect, map change). */
void CODOL_ResetProfilePush(unsigned client);
void CODOL_ResetAllProfilePush(void);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
