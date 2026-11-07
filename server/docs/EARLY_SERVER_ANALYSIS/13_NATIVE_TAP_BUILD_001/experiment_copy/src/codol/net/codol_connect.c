/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_connect.h"
#include "codol_configstrings.h"
#include <stdio.h>
#include <string.h>

static int hex_digit(unsigned char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
static uint64_t connection_uids[CODOL_MAX_GAME_CLIENTS];
int CODOL_ReadConnectXuid(const char *xuid,uint64_t *uid)
{
    uint64_t value=0;size_t i;
    if(!xuid || !uid || strlen(xuid)!=16)return 0;
    for(i=0;i<16;++i) {
        int digit=hex_digit((unsigned char)xuid[i]);
        if(digit<0)return 0;
        value=(value<<4)|(unsigned)digit;
    }
    if(!value)return 0;
    *uid=value;return 1;
}
void CODOL_SetClientConnectIdentity(unsigned client,uint64_t uid)
{
    if(client<CODOL_MAX_GAME_CLIENTS)connection_uids[client]=uid;
}
uint64_t CODOL_ClientConnectIdentity(unsigned client)
{
    return client<CODOL_MAX_GAME_CLIENTS ? connection_uids[client] : 0;
}
int CODOL_ReadConnectUserinfo(char *out, size_t cap, const char *xuid, const char *info)
{
    const char *p, *key, *value;
    size_t n, i, key_len, value_len;
    int seen = 0;
    if (!out || !xuid || !info || strlen(xuid) != 16 || *info != '\\') return 0;
    for (i = 0; i < 16; ++i) if (hex_digit(xuid[i]) < 0) return 0;
    n = strlen(info);
    if (n >= cap) return 0;
    for (i = 0; i < n; ++i)
        if ((unsigned char)info[i] < 32 || info[i] == '"' || info[i] == ';') return 0;
    p = info;
    while (*p) {
        key = ++p;
        while (*p && *p != '\\') ++p;
        key_len = p - key;
        if (!key_len || !*p) return 0;
        value = ++p;
        while (*p && *p != '\\') ++p;
        value_len = p - value;
        if (key_len == 4 && !memcmp(key, "xuid", 4)) {
            if (seen++ || value_len != 16) return 0;
            for (i = 0; i < 16; ++i)
                if (hex_digit(value[i]) != hex_digit(xuid[i])) return 0;
        }
    }
    if (!seen) return 0;
    memmove(out, info, n + 1);
    return 1;
}

static int token(const char *s)
{
    size_t n = 0;
    if (!s || !*s) return 0;
    /* Map/gametype identifiers are single info-string tokens. */
    while (*s) {
        unsigned c = (unsigned char)*s++;
        if (++n > 255 || c <= 32 || c >= 127 || c == '\\' || c == '"' || c == ';') return 0;
    }
    return 1;
}
static size_t finish(uint8_t *out, size_t cap, const char *text, int n, size_t available)
{
    if (!out || n < 0 || (size_t)n >= available || cap < (size_t)n + 5) return 0;
    memset(out, 255, 4);
    memcpy(out + 4, text, (size_t)n + 1);
    return (size_t)n + 5;
}
size_t CODOL_WriteConnectResponse(uint8_t *out, size_t cap, const char *map,
                                  const char *gametype, unsigned max_clients)
{
    char text[640]; int n;
    if (!token(map) || !token(gametype) || !max_clients || max_clients > CODOL_MAX_GAME_CLIENTS) return 0;
    /* alpha0022 dvars.connect_response: live 2026-09-02 protocol bisect.
     * Do not replace protocol 1 with the unrelated dvar default 187. */
    n = snprintf(text, sizeof(text), "connectResponse \\mapname\\%s\\gametype\\%s\\sv_maxclients\\%u\\protocol\\1\\shortversion\\1.1.1.13",
                 map, gametype, max_clients);
    return finish(out, cap, text, n, sizeof(text));
}
size_t CODOL_WriteChallengeResponse(uint8_t *out, size_t cap, int challenge)
{
    char text[64];
    int n = snprintf(text, sizeof(text), "challengeResponse %d", challenge);
    return finish(out, cap, text, n, sizeof(text));
}
