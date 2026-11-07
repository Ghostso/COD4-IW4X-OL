/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Live secure-profile delivery through C1's 'K' command; see the header. */
#include "codol_profile_push.h"
#include <stdio.h>
#include <string.h>

typedef struct {
    char *out;
    size_t max_command;
    size_t length;
    int commands;
    void (*emit)(void *, const char *);
    void *ctx;
} push_writer_t;

static void flush_command(push_writer_t *w)
{
    if (w->length <= 1) return;               /* only the letter */
    w->out[w->length] = 0;
    w->emit(w->ctx, w->out);
    ++w->commands;
    w->out[0] = 'K';
    w->length = 1;
}

/* Appends " <offset> <data>" for bytes [from, to) of `current`, splitting
 * across commands when the text would not fit. */
static void append_run(push_writer_t *w, const uint8_t *current, size_t from, size_t to)
{
    static const char hex[] = "0123456789ABCDEF";
    while (from < to) {
        char head[16];
        int head_len = snprintf(head, sizeof(head), " %u ", (unsigned)from);
        /* Room for the head and at least one byte (two characters). */
        if (w->length + (size_t)head_len + 2 + 1 > w->max_command) flush_command(w);
        memcpy(w->out + w->length, head, (size_t)head_len);
        w->length += (size_t)head_len;
        while (from < to && w->length + 2 + 1 <= w->max_command) {
            uint8_t b = current[from++];
            if (b == 0) w->out[w->length++] = 'Z';
            else if (b == 1) w->out[w->length++] = 'O';
            else {
                w->out[w->length++] = hex[b >> 4];
                w->out[w->length++] = hex[b & 15];
            }
        }
        if (from < to) flush_command(w);
    }
}

int CODOL_EncodeProfilePush(uint8_t *sent, const uint8_t *current, size_t size,
                            size_t merge_gap, char *out, size_t max_command,
                            void (*emit)(void *ctx, const char *command), void *ctx)
{
    push_writer_t w;
    size_t i = 0;
    /* "K" plus " 32767 " plus one byte plus the terminator must always fit. */
    if (!sent || !current || !out || !emit || max_command < 16) return -1;
    w.out = out; w.max_command = max_command; w.length = 1; w.commands = 0;
    w.emit = emit; w.ctx = ctx;
    out[0] = 'K';
    while (i < size) {
        size_t start, last, k;
        if (sent[i] == current[i]) { ++i; continue; }
        start = last = i;
        for (k = i + 1; k < size && k - last <= merge_gap; ++k)
            if (sent[k] != current[k]) last = k;
        append_run(&w, current, start, last + 1);
        memcpy(sent + start, current + start, last + 1 - start);
        i = last + 1;
    }
    flush_command(&w);
    return w.commands;
}

#ifdef CODOL_SERVER
#include "server.h"
#include "cvar.h"
#include "qcommon_io.h"
#include "codol_profile.h"
#include "codol_stats.h"
#include <stdlib.h>

/* The stored blob is [crc32(record)][record]; 'K' offsets are record-relative
 * (the handler's base is 0x0205C59C, the buffer 0x0205C598 plus 4). */
#define PUSH_RECORD_BASE 4u
#define PUSH_RECORD_SIZE 0x7ffcu
/* Well under the 1024-character reliable command limit. */
#define PUSH_MAX_COMMAND 900u
#define PUSH_MERGE_GAP 8u
#define PUSH_INTERVAL_MSEC 250

typedef struct {
    uint8_t *sent;            /* what this client's record holds, as we know it */
    const uint8_t *attached;  /* the profile the copy was taken from */
    uint64_t uid;
    int next_time;
} push_state_t;

static push_state_t push_states[MAX_CLIENTS];
static cvar_t *push_enabled;

void CODOL_ResetProfilePush(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    free(push_states[client].sent);
    memset(&push_states[client], 0, sizeof(push_states[client]));
}

void CODOL_ResetAllProfilePush(void)
{
    unsigned i;
    for (i = 0; i < MAX_CLIENTS; ++i) CODOL_ResetProfilePush(i);
}

typedef struct { int client; unsigned bytes; } push_ctx_t;

static void push_emit(void *ctx, const char *command)
{
    push_ctx_t *p = (push_ctx_t *)ctx;
    SV_GameSendServerCommand(p->client, 1, command);
}

static void push_secure_profiles(int force)
{
    int i, limit;
    char command[PUSH_MAX_COMMAND];
    if (!push_enabled)
        push_enabled = Cvar_RegisterBool("codol_pushSecureProfile", qtrue, CVAR_ARCHIVE,
            "Send in-match rank/XP changes to the C1 client with its 'K' command");
    if (!sv_maxclients) return;
    limit = sv_maxclients->integer;
    if (limit > MAX_CLIENTS) limit = MAX_CLIENTS;
    for (i = 0; i < limit; ++i) {
        client_t *client = &svs.clients[i];
        push_state_t *s = &push_states[i];
        const uint8_t *attached, *current;
        uint64_t uid = 0, attached_uid = 0;
        push_ctx_t ctx;
        int count;
        if (client->state < CS_CONNECTED || client->netchan.remoteAddress.type == NA_BOT) {
            if (s->sent) CODOL_ResetProfilePush((unsigned)i);
            continue;
        }
        attached = CODOL_ClientSecureProfileAttached((unsigned)i, &attached_uid);
        current = CODOL_ClientSecureProfile((unsigned)i, &uid);
        if (!attached || !current) {
            if (s->sent) CODOL_ResetProfilePush((unsigned)i);
            continue;
        }
        /* A (re)attached profile is what the client downloaded from the same
         * lobby file: start the copy from it, so only edits made during this
         * connection are sent. */
        if (!s->sent || s->attached != attached || s->uid != attached_uid) {
            CODOL_ResetProfilePush((unsigned)i);
            s->sent = (uint8_t *)malloc(PUSH_RECORD_SIZE);
            if (!s->sent) continue;
            memcpy(s->sent, attached + PUSH_RECORD_BASE, PUSH_RECORD_SIZE);
            s->attached = attached;
            s->uid = attached_uid;
            s->next_time = svs.time;
        }
        if (!push_enabled->boolean || client->state != CS_ACTIVE || !client->gamestateSent)
            continue;
        /* XP moves on every kill; batch at a quarter second. */
        if (!force && svs.time - s->next_time < 0) continue;
        if (!memcmp(s->sent, current + PUSH_RECORD_BASE, PUSH_RECORD_SIZE)) continue;
        s->next_time = svs.time + PUSH_INTERVAL_MSEC;
        ctx.client = i; ctx.bytes = 0;
        count = CODOL_EncodeProfilePush(s->sent, current + PUSH_RECORD_BASE, PUSH_RECORD_SIZE,
            PUSH_MERGE_GAP, command, sizeof(command), push_emit, &ctx);
        if (count > 0)
            Com_DPrintf(CON_CHANNEL_SERVER, "CoDOL profile push: client %d uid %llu, %d K command(s)\n",
                i, (unsigned long long)s->uid, count);
    }
}

void CODOL_PushSecureProfiles(void)
{
    push_secure_profiles(0);
}

void CODOL_FlushSecureProfiles(void)
{
    push_secure_profiles(1);
}
#endif
