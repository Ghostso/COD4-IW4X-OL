#include "server.h"
#include "netchan.h"
#include "codol_connect.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static byte sent[700];
static int sent_size, cookie;
int NET_CookieHash(netadr_t *from) { assert(from->type == NA_IP); return cookie; }
qboolean NET_SendPacket(netsrc_t sock, int length, const void *data, netadr_t *to)
{
    assert(sock == NS_SERVER && to->type == NA_IP && length <= sizeof(sent));
    memcpy(sent, data, length); sent_size = length; return qtrue;
}
int main(void)
{
    uint8_t out[700] = {0}, before[700];
    char info[1024], original[1024];
    const char *uid = "0123456789abcdef";
    const char *request = "\\name\\Test Player\\xuid\\0123456789ABCDEF\\2490\\-1157214325\\challenge\\123\\qport\\26438\\clan\\";
    const char expected[] = "connectResponse \\mapname\\mp_bog_sh\\gametype\\dm\\sv_maxclients\\18\\protocol\\1\\shortversion\\1.1.1.13";
    const char *bad[] = {"", "mp\\evil", "mp\"evil", "mp;evil", "mp evil", "mp\nevil"};
    const int challenges[] = {0, 1234567, INT_MAX, INT_MIN};
    netadr_t adr = {0};
    size_t n, i;
    adr.type = NA_IP;
    assert(CODOL_ReadConnectUserinfo(info, sizeof(info), uid, request));
    assert(!strcmp(info, request));
    memcpy(original, info, sizeof(info));
    assert(!CODOL_ReadConnectUserinfo(info, strlen(request), uid, request));
    assert(!CODOL_ReadConnectUserinfo(info, sizeof(info), "1123456789abcdef", request));
    assert(!CODOL_ReadConnectUserinfo(info, sizeof(info), "0123456789abcdeg", request));
    assert(!CODOL_ReadConnectUserinfo(info, sizeof(info), uid, "\\name\\Test"));
    assert(!CODOL_ReadConnectUserinfo(info, sizeof(info), uid, "\\xuid\\0123456789abcdef\\xuid\\0123456789abcdef"));
    assert(!CODOL_ReadConnectUserinfo(info, sizeof(info), uid, "\\xuid\\0123456789abcdef\\dangling"));
    assert(!memcmp(info, original, sizeof(info)));
    n = CODOL_WriteConnectResponse(out, sizeof(out), "mp_bog_sh", "dm", 18);
    assert(n == sizeof(expected) + 4 && !memcmp(out, "\xff\xff\xff\xff", 4));
    assert(!memcmp(out + 4, expected, sizeof(expected)));
    memcpy(before, out, sizeof(out));
    assert(!CODOL_WriteConnectResponse(out, n - 1, "mp_bog_sh", "dm", 18));
    assert(!memcmp(out, before, sizeof(out)));
    for (i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i) {
        assert(!CODOL_WriteConnectResponse(out, sizeof(out), bad[i], "dm", 18));
        assert(!CODOL_WriteConnectResponse(out, sizeof(out), "mp_bog_sh", bad[i], 18));
        assert(!memcmp(out, before, sizeof(out)));
    }
    assert(!CODOL_WriteConnectResponse(out, sizeof(out), "map", "dm", 0));
    assert(!CODOL_WriteConnectResponse(out, sizeof(out), "map", "dm", 19));
    assert(CODOL_WriteConnectResponse(out, sizeof(out), "map", "dm", 1));
    assert(strstr((char *)out + 4, "\\sv_maxclients\\1\\protocol\\1"));
    /* Exercise the actual SV_GetChallenge entry point, including socket bytes.
     * The retained cookie value is preserved, even with its sign bit set. */
    for (i = 0; i < sizeof(challenges)/sizeof(challenges[0]); ++i) {
        char text[64];
        cookie = challenges[i];
        snprintf(text, sizeof(text), "challengeResponse %d", cookie);
        SV_GetChallenge(&adr);
        assert(sent_size == strlen(text) + 5);
        assert(!memcmp(sent, "\xff\xff\xff\xff", 4));
        assert(!memcmp(sent + 4, text, strlen(text) + 1));
    }
    puts("CoDOL connect wire response and native challenge dispatch passed");
    return 0;
}
