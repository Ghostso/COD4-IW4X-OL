/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_stats.h"
#include "codol_profile_updates.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CLIENTS 32
static struct { uint32_t received; uint8_t bytes[CODOL_STATS_SIZE]; } stats[CLIENTS];
/* Script edits live here so that every profile reader observes them while the
 * uploaded bytes above stay intact for upload accounting and authentication. */
static uint8_t *session[CLIENTS];
static void drop_session(unsigned client)
{ if(client < CLIENTS) { free(session[client]); session[client] = NULL; } }
void CODOL_ResetClientStats(unsigned client)
{ if(client < CLIENTS) { drop_session(client); memset(&stats[client], 0, sizeof(stats[client]));
    CODOL_ResetProfileUpdates(client); } }
uint32_t CODOL_ClientStatsMissing(unsigned client)
{ return client < CLIENTS ? CODOL_STATS_MASK & ~stats[client].received : CODOL_STATS_MASK; }
const uint8_t *CODOL_ClientStatsUpload(unsigned client)
{ return client < CLIENTS && !CODOL_ClientStatsMissing(client) ? stats[client].bytes : NULL; }
const uint8_t *CODOL_ClientStats(unsigned client)
{ return client < CLIENTS && session[client] ? session[client] : CODOL_ClientStatsUpload(client); }
uint8_t *CODOL_ClientStatsWritable(unsigned client)
{
    const uint8_t *upload; uint8_t *copy;
    if(client >= CLIENTS) return NULL;
    if(session[client]) return session[client];
    upload = CODOL_ClientStatsUpload(client); if(!upload) return NULL;
    copy = malloc(CODOL_STATS_SIZE); if(!copy) return NULL;
    memcpy(copy, upload, CODOL_STATS_SIZE); session[client] = copy; return copy;
}
static uint32_t profile_word(const uint8_t *p)
{ return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24; }
int CODOL_ClientClassPerkItem(unsigned client,unsigned class_index,unsigned slot,int *out)
{
    const uint8_t *profile=CODOL_ClientStats(client); unsigned offset,value;
    if(!profile || !out || class_index>=8 || slot<1 || slot>5 ||
       profile_word(profile+4)!=220 || profile_word(profile+8)!=UINT32_C(0xe4fd5218)) return 0;
    offset=0x1511+class_index*92+(6+slot)*2;
    value=profile[offset] | (unsigned)profile[offset+1]<<8;
    *out=value>=0x8000 ? (int)value-0x10000 : (int)value;
    return 1;
}
int CODOL_AcceptClientStats(unsigned client, unsigned chunk, const uint8_t *data, size_t n)
{
    size_t offset, expected; uint32_t bit;
    if(client >= CLIENTS || chunk >= CODOL_STATS_COUNT || !data) return 0;
    offset = chunk * CODOL_STATS_CHUNK; expected = CODOL_STATS_SIZE - offset;
    if(expected > CODOL_STATS_CHUNK) expected = CODOL_STATS_CHUNK;
    if(n != expected) return 0;
    bit = UINT32_C(1) << chunk;
    if(stats[client].received & bit) return !memcmp(stats[client].bytes + offset, data, n);
    /* Fresh upload bytes supersede any script edit of this client's profile. */
    drop_session(client);
    memcpy(stats[client].bytes + offset, data, n); stats[client].received |= bit;
    if(!CODOL_ClientStatsMissing(client)) CODOL_ProfileUploadReplaced(client);
    return 1;
}
size_t CODOL_WriteStatsResponse(uint8_t *out, size_t cap, uint32_t missing)
{
    char text[64]; int n;
    if(!out || (missing & ~CODOL_STATS_MASK)) return 0;
    n = snprintf(text, sizeof(text), "statResponse %u", missing);
    if(n < 0 || (size_t)n >= sizeof(text) || cap < (size_t)n + 5) return 0;
    memset(out, 255, 4); memcpy(out + 4, text, (size_t)n + 1); return (size_t)n + 5;
}
