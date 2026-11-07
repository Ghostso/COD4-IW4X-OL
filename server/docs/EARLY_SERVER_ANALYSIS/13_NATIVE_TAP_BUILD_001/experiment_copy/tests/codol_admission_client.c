/* Minimal bdDTLS client for testing lobby admission against a running server.
 *
 *   codol_admission_client <host> <port> <session key hex32> <xuid hex16> <name>
 *
 * Does what C1 does on the wire: INIT with the lobby security ID, COOKIE_ECHO
 * with its own P-224 key, then -- inside the association keyed by <session key>
 * -- "getchallenge" and "connect <xuid> <userinfo>". Prints each reply. Used by
 * tests/test_codol_admission_live.sh; not part of the server.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_association.h"
#include "codol_ecdh.h"
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

static int urandom(void *ctx, unsigned char *out, size_t n)
{
    FILE *f = fopen("/dev/urandom", "rb");
    (void)ctx;
    if (!f) return -1;
    if (fread(out, 1, n, f) != n) { fclose(f); return -1; }
    fclose(f);
    return 0;
}

static int hexbytes(const char *s, uint8_t *out, size_t n)
{
    size_t i;
    unsigned v;
    if (strlen(s) != 2 * n) return 0;
    for (i = 0; i < n; ++i) {
        if (sscanf(s + 2 * i, "%2x", &v) != 1) return 0;
        out[i] = (uint8_t)v;
    }
    return 1;
}

static int receive(int fd, uint8_t *buf, size_t cap, int ms)
{
    struct timeval tv;
    tv.tv_sec = ms / 1000; tv.tv_usec = (ms % 1000) * 1000;
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    return (int)recv(fd, buf, cap, 0);
}

/* Send one sealed OOB command, then print every sealed reply for `ms`. The
 * first reply text is copied to `first` when given. */
static int exchange(int fd, codol_association_t *a, const char *command, int ms, char *first, size_t cap)
{
    uint8_t plain[2048], record[2200], in[2200], out[2048];
    size_t n = strlen(command), length, size;
    int got = 0, r;
    memset(plain, 0xff, 4);
    memcpy(plain + 4, command, n + 1);
    length = CODOL_AssociationSeal(a, record, sizeof(record), plain, n + 5);
    if (!length || send(fd, record, length, 0) != (ssize_t)length) return -1;
    while ((r = receive(fd, in, sizeof(in), ms)) > 0) {
        if (!CODOL_AssociationOpen(a, out, sizeof(out) - 1, &size, in, (size_t)r, NULL)) {
            printf("  (undecryptable %d-byte reply)\n", r);
            continue;
        }
        out[size] = 0;
        if (size > 4 && out[0] == 0xff) printf("  reply: %.120s\n", (char *)out + 4);
        if (!got && first && size > 4 && out[0] == 0xff) {
            strncpy(first, (char *)out + 4, cap - 1); first[cap - 1] = 0;
        }
        ++got;
        ms = 300;
    }
    if (got > 1) printf("  (%d sealed replies in total)\n", got);
    return got;
}

int main(int argc, char **argv)
{
    uint8_t key[16], x[28], priv[28], init[16] = {1, 2, 0, 0, 0, 0, 0x21, 0x43, 0x46, 0, 0, 0, 0, 0, 0, 0};
    uint8_t buf[512], echo[189] = {3, 2};
    struct sockaddr_in sa;
    codol_association_t a;
    char text[256], command[1024];
    int fd, r, challenge;
    uint16_t server_tag;
    if (argc != 6 || !hexbytes(argv[3], key, 16) || strlen(argv[4]) != 16) {
        fprintf(stderr, "usage: %s host port key_hex32 xuid_hex16 name\n", argv[0]);
        return 2;
    }
    memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET; sa.sin_port = htons((uint16_t)atoi(argv[2]));
    inet_pton(AF_INET, argv[1], &sa.sin_addr);
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0 || connect(fd, (struct sockaddr *)&sa, sizeof(sa))) { perror("socket"); return 2; }

    /* INIT -> INIT_ACK (38 bytes; server tag at 14..15). */
    send(fd, init, sizeof(init), 0);
    if ((r = receive(fd, buf, sizeof(buf), 2000)) != 38) { printf("association: no INIT_ACK (%d)\n", r); return 1; }
    /* COOKIE_ECHO: cookie, security ID, our public key. */
    echo[2] = buf[14]; echo[3] = buf[15];
    server_tag = (uint16_t)(buf[14] | buf[15] << 8);
    memcpy(echo + 6, buf, 38);
    memcpy(echo + 81, init + 8, 8);
    if (urandom(NULL, priv, sizeof(priv)) || (priv[0] &= 0x7f, !CODOL_ExportPublicKey(echo + 89, priv, urandom, NULL))) return 2;
    send(fd, echo, sizeof(echo), 0);
    if ((r = receive(fd, buf, sizeof(buf), 2000)) != 114) { printf("association: no COOKIE_ACK (%d)\n", r); return 1; }
    if (!CODOL_SharedSecret(x, buf + 6, priv, urandom, NULL) ||
        !CODOL_AssociationStart(&a, x, key, (uint16_t)(init[6] | init[7] << 8), server_tag)) {
        printf("association: key agreement failed\n"); return 1;
    }
    printf("association: established\n");

    text[0] = 0;
    if (exchange(fd, &a, "getchallenge", 2000, text, sizeof(text)) <= 0 ||
        sscanf(text, "challengeResponse %d", &challenge) != 1) {
        printf("challenge: none (server did not accept this session key)\n");
        return 1;
    }
    printf("challenge: %d\n", challenge);
    snprintf(command, sizeof(command), "connect %s \\challenge\\%d\\qport\\4242\\xuid\\%s\\name\\%s",
             argv[4], challenge, argv[4], argv[5]);
    text[0] = 0;
    r = exchange(fd, &a, command, 2000, text, sizeof(text));
    printf("connect: %s\n", r <= 0 ? "no reply" : text);
    close(fd);
    return 0;
}
