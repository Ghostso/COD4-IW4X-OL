/* Lobby -> game server admission roster: parsing, candidate order, identification.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_admission.h"
#include "codol_crypto.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef CODOL_TEST_COARSE_STAT
#include <fcntl.h>
#include <sys/stat.h>
#endif

static int failures;
#define CHECK(name, cond) do { if (cond) printf("PASS  %s\n", name); \
    else { printf("FAIL  %s\n", name); ++failures; } } while (0)

int main(void)
{
    codol_admission_entry_t e;
    uint8_t keys[8][16], x[28], data_key[24];
    uint8_t ip_a[4] = {203, 0, 113, 7}, ip_b[4] = {198, 51, 100, 2}, ip_c[4] = {192, 0, 2, 1};
    char path[256], line[512];
    long long later = (long long)time(NULL) + 3600, earlier = (long long)time(NULL) - 10;
    size_t n, i;
    FILE *f;

    CHECK("parse full line",
        CODOL_AdmissionParseLine("203.0.113.7 000102030405060708090a0b0c0d0e0f 9d8f2a1b3c4d5e6f 1800000000 Nucleur", &e) &&
        e.ip[0] == 203 && e.ip[3] == 7 && e.key[15] == 0x0f && e.uid == UINT64_C(0x9d8f2a1b3c4d5e6f) &&
        e.expires == 1800000000LL && !strcmp(e.gamertag, "Nucleur"));
    CHECK("parse unknown uid and placeholder name",
        CODOL_AdmissionParseLine("1.2.3.4 ffffffffffffffffffffffffffffffff 0 5 -", &e) && e.uid == 0 && !e.gamertag[0]);
    CHECK("reject comment", !CODOL_AdmissionParseLine("# header", &e));
    CHECK("reject short key", !CODOL_AdmissionParseLine("1.2.3.4 00ff 0 5 a", &e));
    CHECK("reject bad ip", !CODOL_AdmissionParseLine("1.2.3.400 000102030405060708090a0b0c0d0e0f 0 5 a", &e));
    CHECK("reject unsafe gamertag", !CODOL_AdmissionParseLine("1.2.3.4 000102030405060708090a0b0c0d0e0f 0 5 a\\b", &e));
    CHECK("reject missing field", !CODOL_AdmissionParseLine("1.2.3.4 000102030405060708090a0b0c0d0e0f 0 5", &e));

    /* A roster: A (this IP), B (other IP), C expired. */
    snprintf(path, sizeof(path), "%s/codol_admission_test_%ld.txt",
             getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp", (long)time(NULL));
    f = fopen(path, "w");
    if (!f) { printf("FAIL  cannot write %s\n", path); return 1; }
    fprintf(f, "# roster\n");
    fprintf(f, "198.51.100.2 %s 0000000000000002 %lld Bee\n", "20202020202020202020202020202020", later);
    fprintf(f, "203.0.113.7 %s 0000000000000001 %lld Ay\n", "10101010101010101010101010101010", later);
    fprintf(f, "192.0.2.1 %s 0000000000000003 %lld Old\n", "30303030303030303030303030303030", earlier);
    fclose(f);
    setenv("CODOL_ADMISSION_PATH", path, 1);

    n = CODOL_AdmissionCandidates(ip_a, keys, 8);
    CHECK("two live candidates, this IP first", n == 2 && keys[0][0] == 0x10 && keys[1][0] == 0x20);
    n = CODOL_AdmissionCandidates(ip_c, keys, 8);
    CHECK("expired entry is not a candidate", n == 2 && keys[0][0] != 0x30 && keys[1][0] != 0x30);

    for (i = 0; i < sizeof(x); ++i) x[i] = (uint8_t)(i * 7 + 1);
    memset(keys[0], 0x20, 16);
    CHECK("derive", CODOL_DeriveKey(data_key, x, keys[0]));
    /* The association keyed by B's key identifies B, even from A's address. */
    CHECK("identify by key", CODOL_AdmissionIdentify(ip_a, x, data_key, &e) &&
        e.uid == 2 && !strcmp(e.gamertag, "Bee"));
    memset(keys[0], 0x30, 16);
    CODOL_DeriveKey(data_key, x, keys[0]);
    CHECK("expired key does not identify", !CODOL_AdmissionIdentify(ip_c, x, data_key, &e));
    memset(data_key, 0x55, sizeof(data_key));
    CHECK("unknown key does not identify", !CODOL_AdmissionIdentify(ip_b, x, data_key, &e));

    /* A party member on the host's key: the member is the claimed uid's
     * live entry from this same address, never another address's entry. */
    CHECK("member by uid and address", CODOL_AdmissionMember(ip_a, 1, &e) && e.uid == 1 &&
        !strcmp(e.gamertag, "Ay"));
    CHECK("member refused from another address", !CODOL_AdmissionMember(ip_b, 1, &e));
    CHECK("expired member refused", !CODOL_AdmissionMember(ip_c, 3, &e));
    CHECK("unknown member refused", !CODOL_AdmissionMember(ip_a, 9, &e));

    /* The file is re-read when it changes -- also when a replacement keeps
     * the size and lands in the same second (the lobby's createSession pair). */
    {
        FILE *g;
        char tmp[300];
        snprintf(tmp, sizeof(tmp), "%s.tmp", path);
        g = fopen(tmp, "w");
        fprintf(g, "# roster\n");
        fprintf(g, "198.51.100.2 %s 0000000000000002 %lld Bee\n", "50505050505050505050505050505050", later);
        fprintf(g, "203.0.113.7 %s 0000000000000001 %lld Ay\n", "10101010101010101010101010101010", later);
        fprintf(g, "192.0.2.1 %s 0000000000000003 %lld Old\n", "30303030303030303030303030303030", earlier);
        fclose(g);
        rename(tmp, path);
        n = CODOL_AdmissionCandidates(ip_b, keys, 8);
        CHECK("reload on same-size replacement", n == 2 && keys[0][0] == 0x50);
    }

#ifdef CODOL_TEST_COARSE_STAT
    /* Model a filesystem/CRT that reports only whole-second modification
     * times and no useful file identity. A same-size in-place refresh has
     * exactly the same stat tuple as the previously cached roster. */
    {
        struct stat before;
        struct timespec times[2];
        CHECK("stat cached roster", stat(path, &before) == 0);
        f = fopen(path, "r+");
        if (!f) { printf("FAIL  cannot refresh %s\n", path); return 1; }
        fprintf(f, "# roster\n");
        fprintf(f, "198.51.100.2 %s 0000000000000002 %lld Bee\n", "60606060606060606060606060606060", later);
        fprintf(f, "203.0.113.7 %s 0000000000000001 %lld Ay\n", "10101010101010101010101010101010", later);
        fprintf(f, "192.0.2.1 %s 0000000000000003 %lld Old\n", "30303030303030303030303030303030", earlier);
        fclose(f);
        times[0] = before.st_atim;
        times[1] = before.st_mtim;
        CHECK("restore cached roster time", utimensat(AT_FDCWD, path, times, 0) == 0);
        n = CODOL_AdmissionCandidates(ip_b, keys, 8);
        CHECK("reload with indistinguishable coarse metadata", n == 2 && keys[0][0] == 0x60);
    }
#endif

    /* The file is re-read when it changes. */
    f = fopen(path, "w");
    snprintf(line, sizeof(line), "203.0.113.7 %s 0 %lld Newcomer\n", "40404040404040404040404040404040", later);
    fputs(line, f); fputs("# padding so the size differs from the previous roster\n", f);
    fclose(f);
    n = CODOL_AdmissionCandidates(ip_a, keys, 8);
    CHECK("reload on change", n == 1 && keys[0][0] == 0x40);

    remove(path);
    n = CODOL_AdmissionCandidates(ip_a, keys, 8);
    CHECK("missing roster is empty", n == 0);

    printf("%d failure(s)\n", failures);
    return failures != 0;
}
