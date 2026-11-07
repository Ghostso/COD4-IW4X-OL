/* Unit test for CODOL_EncodeProfilePush (C1 'K' secure-profile command). */
#include "../src/codol/stats/codol_profile_push.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static char got[64][1024];
static int ngot;

static void collect(void *ctx, const char *command)
{
    (void)ctx;
    if (ngot < 64) { strcpy(got[ngot], command); ++ngot; }
}

/* Replays commands the way C1 0x00468BD0 does, into `record`. */
static void apply(uint8_t *record, size_t size)
{
    int c;
    for (c = 0; c < ngot; ++c) {
        char buf[1024], *tok, *save = NULL;
        int argc = 0; unsigned off = 0;
        strcpy(buf, got[c]);
        for (tok = strtok_r(buf, " ", &save); tok; tok = strtok_r(NULL, " ", &save), ++argc) {
            if (argc == 0) { if (strcmp(tok, "K")) { printf("FAIL letter %s\n", tok); exit(1); } continue; }
            if (argc & 1) { off = (unsigned)atoi(tok); continue; }
            while (*tok) {
                if (off >= size) { printf("FAIL offset %u\n", off); exit(1); }
                if (*tok == 'Z') { record[off++] = 0; ++tok; }
                else if (*tok == 'O') { record[off++] = 1; ++tok; }
                else {
                    unsigned v; char h[3] = { tok[0], tok[1], 0 };
                    if (!tok[1] || sscanf(h, "%2X", &v) != 1) { printf("FAIL hex %s\n", tok); exit(1); }
                    record[off++] = (uint8_t)v; tok += 2;
                }
            }
        }
        if (!(argc & 1)) { printf("FAIL even argc in %s\n", got[c]); exit(1); }
    }
}

int main(void)
{
    enum { N = 0x7ffc };
    static uint8_t sent[N], current[N], client[N];
    char out[900];
    int n, c;

    /* Nothing changed: nothing sent. */
    ngot = 0;
    n = CODOL_EncodeProfilePush(sent, current, N, 8, out, sizeof(out), collect, NULL);
    if (n != 0 || ngot != 0) { printf("FAIL idle %d\n", n); return 1; }

    /* Rank/XP-like edits, a 0/1 pair, a near-by pair to merge, and a far edit. */
    current[0x1130] = 0xC6; current[0x1131] = 0x01;          /* experience 454 */
    current[0x13EC] = 2;                                      /* rank */
    current[0x13F0] = 0; current[0x13F3] = 1;
    current[N - 1] = 0xAB;
    memcpy(client, sent, N);
    ngot = 0;
    n = CODOL_EncodeProfilePush(sent, current, N, 8, out, sizeof(out), collect, NULL);
    apply(client, N);
    if (n < 1 || memcmp(client, current, N) || memcmp(sent, current, N)) { printf("FAIL small\n"); return 1; }
    for (c = 0; c < ngot; ++c) if (strlen(got[c]) >= sizeof(out)) { printf("FAIL length\n"); return 1; }

    /* A large block must split across commands, each within the limit. */
    for (c = 0; c < 3000; ++c) current[100 + c] = (uint8_t)(c * 7 + 3);
    memcpy(client, sent, N);
    ngot = 0;
    n = CODOL_EncodeProfilePush(sent, current, N, 8, out, sizeof(out), collect, NULL);
    apply(client, N);
    if (n < 2 || memcmp(client, current, N)) { printf("FAIL large %d\n", n); return 1; }
    for (c = 0; c < ngot; ++c) if (strlen(got[c]) >= sizeof(out)) { printf("FAIL length %zu\n", strlen(got[c])); return 1; }

    printf("test_codol_profile_push: ok (%d commands for the large block)\n", n);
    return 0;
}
